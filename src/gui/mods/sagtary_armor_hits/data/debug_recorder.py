# -*- coding: utf-8 -*-
"""Debug record: every call from the server about shots and damage, written to a JSON Lines file per battle, to check
the hits against what the server sent. On only with the "debug" setting: it writes a lot while the battle goes.

The server calls methods of the entities on the client (BigWorld remote methods). Here the methods about shots,
hits and damage are listened to (hooks.py); each call is written with all its arguments before the client handles
it:

- Vehicle (called on the vehicle it is about, any vehicle the client sees):
  showDamageFromShot (a shell hit: hit points per armor plate), showDamageFromExplosion (HE splash),
  onHealthChanged (health, attacker, attack reason);
- PlayerAvatar (the player):
  showTracer / stopTracer / explodeProjectile (flight of every visible shell: start, velocity, end),
  showShotResults (result flags of the player's own shots), showOwnVehicleHitDirection (hit direction
  indicator), showVehicleDamageInfo (damage messages, crits), showOtherVehicleDamagedDevices,
  updateVehicleHealth, onBattleEvents / battleEventsSummary (the battle events feed: damage, blocked, spotting).

Argument names are those of the client's own methods (hooks.py), so a call is written in full even when a client
update adds arguments. Shell hits get the hit points decoded by the client's DamageFromShotDecoder and the state of the
victim (position, turret and gun angles, modules); explosions and health changes get the victim state too.

The file is written while the battle goes, one JSON object per line:
- "battle": the first line, the battle;
- "vehicle": a vehicle of the battle (player, team, compact descriptor with the exact modules), written when the
  client first knows it and again when it changes; calls refer to vehicles by id (attackerID, shooterID, ...).
  The client knows vehicles from the arena list (all vehicles of a random battle, from the start or as they are
  added) and from the vehicle entities it sees;
- a server call: "event" is the method name, "args" its arguments, "extra" the context read at the call;
- "shotEffects": the description of a shell (by effectsIndex), once per battle;
- "end": the last line.
Replays are recorded the same way, with "isReplay" in the first line and "_replay" in the file name.
"""
import json
import logging
import os
import time

import BattleReplay
import BigWorld
import Math
from Avatar import PlayerAvatar
from PlayerEvents import g_playerEvents
from Vehicle import Vehicle
from VehicleEffects import DamageFromShotDecoder
from items import vehicles

from gui.mods.sagtary_armor_hits.config import RECORDS_DIR

_logger = logging.getLogger('sagtary.armor_hits')

_VEHICLE_METHODS = ('showDamageFromShot', 'showDamageFromExplosion', 'onHealthChanged')
_AVATAR_METHODS = ('showTracer', 'stopTracer', 'explodeProjectile', 'showShotResults', 'showOwnVehicleHitDirection',
                   'showVehicleDamageInfo', 'showOtherVehicleDamagedDevices', 'updateVehicleHealth',
                   'onBattleEvents', 'battleEventsSummary')
_MAX_DEPTH = 8


def _plain(value, depth=0):
    # The value as JSON data: vectors as lists, matrices as translation and angles, named tuples and the client's
    # fixed dicts as objects, bytes that are not UTF-8 as hex. Anything else as its repr.
    if depth > _MAX_DEPTH:
        return repr(value)
    if value is None or isinstance(value, (bool, int, long, float, unicode)):
        return value
    if isinstance(value, str):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return {'hex': value.encode('hex')}
    if isinstance(value, (Math.Vector2, Math.Vector3, Math.Vector4)):
        return list(value)
    if isinstance(value, Math.Matrix):
        return {'translation': list(value.translation), 'yaw': value.yaw, 'pitch': value.pitch, 'roll': value.roll}
    if hasattr(value, '_asdict'):
        return _plain(dict(value._asdict()), depth + 1)
    if isinstance(value, dict):
        return {unicode(key): _plain(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item, depth + 1) for item in value]
    # The client's own containers (FixedDict and Array of the entity definitions) are C types: they have
    # keys() or len() with indexes, not always __iter__ or __getitem__ as attributes.
    try:
        return {unicode(key): _plain(value[key], depth + 1) for key in value.keys()}
    except Exception:
        pass
    try:
        return [_plain(value[index], depth + 1) for index in range(len(value))]
    except Exception:
        pass
    if hasattr(value, '__dict__'):
        return {key: _plain(item, depth + 1) for key, item in vars(value).items()
                if not key.startswith('_') and not callable(item)}
    return {'repr': repr(value), 'type': type(value).__name__}


def _compactDescr(typeDescriptor):
    return typeDescriptor.makeCompactDescr().encode('hex') if typeDescriptor is not None else None


def _vehicleState(vehicle):
    # Where the vehicle is and how it stands now. Its full descriptor goes once into a "vehicle" line.
    descriptor = getattr(vehicle, 'typeDescriptor', None)
    state = {
        'id': vehicle.id,
        'position': list(vehicle.position),
        'yaw': vehicle.yaw,
        'pitch': vehicle.pitch,
        'roll': vehicle.roll,
        'health': getattr(vehicle, 'health', None),
        'isAlive': vehicle.isAlive() if hasattr(vehicle, 'isAlive') else None,
        'aimParams': list(vehicle.getAimParams()) if hasattr(vehicle, 'getAimParams') else None,
    }
    if descriptor is not None:
        state['vehicle'] = descriptor.name
        state['modules'] = {part: getattr(descriptor, part).name for part in ('chassis', 'hull', 'turret', 'gun')}
    appearance = getattr(vehicle, 'appearance', None)
    if appearance is not None:
        try:
            state['matrix'] = _plain(Math.Matrix(vehicle.matrix))
            state['turretMatrix'] = _plain(Math.Matrix(appearance.turretMatrix))
            state['gunMatrix'] = _plain(Math.Matrix(appearance.gunMatrix))
        except Exception:
            pass
    return state


def _shotEffects(effectsIndex):
    # Values of the shot effects description: caliber, impulse, physics of the shell.
    # The visual effects per hit kind and material ({'effectsList': ..., 'keyPoints': ...}) are left out.
    effects = vehicles.g_cache.shotEffects[effectsIndex]
    result = {}
    for key, value in effects.items():
        plain = _plain(value)
        if isinstance(plain, dict) and ('effectsList' in plain or ('repr' in plain and 'type' in plain)):
            continue
        result[key] = plain
    return result


def _decodedHitPoints(vehicle, hitPoints):
    collisions = vehicle.appearance.collisions if getattr(vehicle, 'appearance', None) is not None else None
    if collisions is None:
        return None
    points = []
    for hitPoint in hitPoints:
        parsed = DamageFromShotDecoder.parseHitPoint(hitPoint, collisions)
        if parsed is None:
            points.append(None)
            continue
        compIdx, hitEffectCode, start, end, hitType, shellType, caliber = parsed
        points.append({
            'compIdx': compIdx,
            'part': DamageFromShotDecoder.getPartName(compIdx, collisions),
            'isDynCollision': compIdx > collisions.maxStaticPartIndex,
            'hitEffectCode': hitEffectCode,
            'start': list(start),
            'end': list(end),
            'hitType': hitType,
            'shellType': shellType,
            'caliber': caliber,
        })
    # The client's own full decoding: hit point and direction in the part, normal, effect group.
    shotPoints = [_plain(point) for point in DamageFromShotDecoder.parseHitPoints(hitPoints, collisions)]
    return {'points': points, 'shotPoints': shotPoints}


def _battleInfo(player):
    arena = player.arena
    info = {
        'arenaUniqueID': player.arenaUniqueID,
        'arenaTypeID': player.arenaTypeID,
        'arenaBonusType': player.arenaBonusType,
        'arenaGuiType': player.arenaGuiType,
        'map': arena.arenaType.geometryName if arena is not None else None,
        'playerVehicleID': player.playerVehicleID,
        'playerName': player.name,
        'isReplay': BattleReplay.isPlaying(),
    }
    return info


class DebugRecorder(object):

    def __init__(self, hooks):
        self._hooks = hooks
        self._file = None
        self._path = None
        self._count = 0
        self._arena = None
        # Written already in this battle: effectsIndex values, {vehicle id: compact descriptor}.
        self._effects = set()
        self._descriptors = {}

    def install(self):
        for cls, names in ((Vehicle, _VEHICLE_METHODS), (PlayerAvatar, _AVATAR_METHODS)):
            for name in names:
                self._hooks.listen(cls, name, self._onCall)
        g_playerEvents.onAvatarReady += self._start
        g_playerEvents.onAvatarBecomeNonPlayer += self._stop

    def uninstall(self):
        g_playerEvents.onAvatarReady -= self._start
        g_playerEvents.onAvatarBecomeNonPlayer -= self._stop
        for cls, names in ((Vehicle, _VEHICLE_METHODS), (PlayerAvatar, _AVATAR_METHODS)):
            for name in names:
                self._hooks.stop(cls, name, self._onCall)
        self._stop()

    def _start(self):
        if self._file is not None:
            self._stop()
        try:
            player = BigWorld.player()
            info = _battleInfo(player)
            if not os.path.isdir(RECORDS_DIR):
                os.makedirs(RECORDS_DIR)
            self._path = os.path.join(RECORDS_DIR, '%s_%s%s.jsonl' % (
                time.strftime('%Y-%m-%d_%H-%M-%S'), info['arenaUniqueID'], '_replay' if info['isReplay'] else ''))
            self._file = open(self._path, 'w')
            self._count = 0
            self._effects = set()
            self._descriptors = {}
            self._write({'event': 'battle', 'time': time.time(), 'info': info})
            self._arena = player.arena
            if self._arena is not None:
                self._arena.onNewVehicleListReceived += self._onArenaList
                self._arena.onVehicleAdded += self._onArenaVehicle
                self._arena.onVehicleUpdated += self._onArenaVehicle
                self._onArenaList()
        except Exception:
            _logger.exception('debug: cannot start the record')
            self._stop()

    def _stop(self):
        if self._file is None:
            return
        if self._arena is not None:
            self._arena.onNewVehicleListReceived -= self._onArenaList
            self._arena.onVehicleAdded -= self._onArenaVehicle
            self._arena.onVehicleUpdated -= self._onArenaVehicle
            self._arena = None
        try:
            self._write({'event': 'end', 'time': time.time(), 'calls': self._count})
            self._file.close()
        except Exception:
            _logger.exception('debug: cannot close %s', self._path)
        self._file = None

    def _write(self, data):
        self._file.write(json.dumps(data, separators=(',', ':'), sort_keys=True))
        self._file.write('\n')
        self._file.flush()

    def _onCall(self, call):
        if self._file is None:
            return
        name, entity, callArgs = call.name, call.entity, call.arguments()
        record = {
            'event': name,
            'class': call.cls.__name__,
            'entityID': entity.id,
            'time': time.time(),
            'serverTime': BigWorld.serverTime(),
            'args': _plain(callArgs),
        }
        extra = self._extra(name, entity, callArgs)
        if extra:
            record['extra'] = extra
        self._write(record)
        self._count += 1

    def _extra(self, name, entity, callArgs):
        # Context the call itself does not carry, read from the client at the moment of the call.
        extra = {}
        if isinstance(entity, Vehicle):
            extra['victim'] = self._vehicle(entity)
        for role, key in (('attacker', 'attackerID'), ('shooter', 'shooterID')):
            other = BigWorld.entity(callArgs.get(key) or 0)
            if isinstance(other, Vehicle):
                extra[role] = self._vehicle(other)
        if name == 'showDamageFromShot':
            extra['decoded'] = _decodedHitPoints(entity, callArgs.get('hitPoints', ()))
        if 'effectsIndex' in callArgs:
            self._noteShotEffects(callArgs['effectsIndex'])
        return extra

    def _vehicle(self, vehicle):
        self._noteVehicle(vehicle.id, getattr(vehicle, 'typeDescriptor', None))
        return _vehicleState(vehicle)

    def _onArenaList(self):
        for vehicleID in self._arena.vehicles.keys():
            self._onArenaVehicle(vehicleID)

    def _onArenaVehicle(self, vehicleID):
        try:
            data = self._arena.vehicles.get(vehicleID) or {}
            self._noteVehicle(vehicleID, data.get('vehicleType'))
        except Exception:
            _logger.exception('debug: cannot record arena vehicle %s', vehicleID)

    def _noteVehicle(self, vehicleID, descriptor):
        # A "vehicle" line when the vehicle is new or its descriptor changed.
        if self._file is None or descriptor is None:
            return
        compactDescr = _compactDescr(descriptor)
        if self._descriptors.get(vehicleID) == compactDescr:
            return
        self._descriptors[vehicleID] = compactDescr
        data = (self._arena.vehicles.get(vehicleID) if self._arena is not None else None) or {}
        self._write({'event': 'vehicle', 'vehicleID': vehicleID, 'vehicle': descriptor.name,
                     'compactDescr': compactDescr, 'name': data.get('name'), 'team': data.get('team'),
                     'accountDBID': data.get('accountDBID'), 'clanAbbrev': data.get('clanAbbrev')})

    def _noteShotEffects(self, effectsIndex):
        if effectsIndex in self._effects:
            return
        self._effects.add(effectsIndex)
        self._write({'event': 'shotEffects', 'effectsIndex': effectsIndex, 'effects': _shotEffects(effectsIndex)})
