# -*- coding: utf-8 -*-
"""HitCollector: adds the hits of the battle the player is in to its Battle in the BattleStore.

It listens to the server's calls (hooks.py), reads what the client knows at each of them and makes the hits by the
rules of hit_parser.py: receivedHits (the player's vehicle was hit) and dealtHits (the player's vehicle hit another
one). The client knows the hits on the vehicles it sees, so all the player's hits are there, and the hits on the
player's vehicle; not those on a vehicle already destroyed (a wreck takes no damage, the server tells it as pierced
without damage).

- Vehicle.showDamageFromShot, showDamageFromExplosion: a hit. The client decodes its points
  (DamageFromShotDecoder.parseHitPoint, by the parts of the vehicle's collision model); the hit gets the other
  vehicle (player, compact descriptor) from the arena, the distance between the two vehicles when the client sees
  the shooter, the battle time, the teams of the shooter and the hit vehicle, the hit vehicle's pose (its turret,
  gun, hull on its chassis and steered wheels, as the client shows them). A splash keeps where the shell burst, in
  the hit vehicle's chassis space (like the points), even when it burst on the ground nearby. The premium flag of the
  player's own shell is the player's current shell's.
- PlayerAvatar.onBattleEvents, showVehicleDamageInfo: more about the hit of the same vehicle (hit_parser.HitPairing).
  The client tells which modules it damaged only on the player's own vehicle.
- PlayerAvatar.showTracer: the shells in flight, for the shell's direction at the first point.
"""
import logging

import BigWorld
import Math
from Avatar import PlayerAvatar
from constants import ARENA_PERIOD, DAMAGE_INFO_CODES
from PlayerEvents import g_playerEvents
from Vehicle import Vehicle
from VehicleEffects import DamageFromShotDecoder
from vehicle_systems.tankStructure import TankPartIndexes, TankPartNames

from gui.mods.sagtary_armor_hits.data import hit_parser
from gui.mods.sagtary_armor_hits.data.hits import compactDescriptor, ownShellIsGold

_logger = logging.getLogger('sagtary.armor_hits')


def _chassisPoint(vehicle, point):
    # A point of the scene in the vehicle's chassis space (the node the client puts the chassis hit effects on, else
    # the vehicle's own matrix), () when not known.
    try:
        nodeName = TankPartNames.getActualNodeNameByPartName(TankPartNames.CHASSIS)
        matrix = Math.Matrix(vehicle.appearance.compoundModel.node(nodeName))
    except Exception:
        try:
            matrix = Math.Matrix(vehicle.matrix)
        except Exception:
            return ()
    matrix.invert()
    return hit_parser.vector(matrix.applyPoint(Math.Vector3(point)))


def _battleTime(arena):
    # Seconds since the battle period started; 0 before it.
    if arena is None or arena.period != ARENA_PERIOD.BATTLE:
        return 0.0
    return max(0.0, BigWorld.serverTime() - (arena.periodEndTime - arena.periodLength))


def _partMatrix(vehicle, part):
    # The world matrix of the node the client puts the hit effects of the vehicle's part on (its points' space); None.
    try:
        nodeName = TankPartNames.getActualNodeNameByPartName(TankPartIndexes.getName(part))
        return Math.Matrix(vehicle.appearance.compoundModel.node(nodeName))
    except Exception:
        return None


def _vehiclePose(vehicle):
    # The vehicle's pose as the client shows it; None without its model.
    if getattr(vehicle, 'appearance', None) is None:
        return None
    try:
        return hit_parser.vehiclePose(vehicle.getAimParams())
    except Exception:
        _logger.exception('hits: no pose of vehicle %s', vehicle.id)
        return None


def _team(arena, vehicleID):
    # The vehicle's team in the arena, None when the arena does not have the vehicle.
    return (arena.vehicles.get(vehicleID) or {}).get('team')


def _distance(vehicleID, otherID):
    # Metres between two vehicles the client sees, 0 when it does not see one of them.
    vehicle, other = BigWorld.entities.get(vehicleID), BigWorld.entities.get(otherID)
    if vehicle is None or other is None:
        return 0.0
    return round((vehicle.position - other.position).length, 1)


def _decodedPoints(vehicle, hitPoints):
    # The hit points as the client decodes them by the vehicle's collision model; none without the model.
    collisions = vehicle.appearance.collisions if getattr(vehicle, 'appearance', None) is not None else None
    if collisions is None:
        return []
    decoded = (DamageFromShotDecoder.parseHitPoint(hitPoint, collisions) for hitPoint in hitPoints or ())
    return [point for point in decoded if point is not None]


def _ownShellIsGold(player, shellType):
    # The player's shell of a dealt hit: the server does not tell whether it was a premium one.
    try:
        ammo = player.guiSessionProvider.shared.ammo
        isGold = ownShellIsGold(player.vehicleTypeDescriptor, shellType, ammo.getCurrentShellCD())
    except Exception:
        isGold = None
    return bool(isGold)


class HitCollector(object):

    def __init__(self, store, hooks):
        self._store = store
        self._hooks = hooks
        self._pairing = hit_parser.HitPairing()
        self._tracers = hit_parser.Tracers()
        # (class, method name, listener) of the calls listened to.
        self._listened = (
            (Vehicle, 'showDamageFromShot', self._onVehicleHit),
            (Vehicle, 'showDamageFromExplosion', self._onVehicleHit),
            (PlayerAvatar, 'onBattleEvents', self._onBattleEvents),
            (PlayerAvatar, 'showVehicleDamageInfo', self._onDamageInfo),
            (PlayerAvatar, 'showTracer', self._onTracer),
        )

    def install(self):
        for cls, name, listener in self._listened:
            self._hooks.listen(cls, name, listener)
        g_playerEvents.onAvatarBecomeNonPlayer += self._reset

    def uninstall(self):
        g_playerEvents.onAvatarBecomeNonPlayer -= self._reset
        for cls, name, listener in self._listened:
            self._hooks.stop(cls, name, listener)
        self._reset()

    def _reset(self, *args):
        self._pairing.reset()
        self._tracers.reset()

    def _onVehicleHit(self, call):
        vehicle, player = call.entity, BigWorld.player()
        attackerID = call.get('attackerID')
        side = hit_parser.hitSide(vehicle.id, attackerID, getattr(player, 'playerVehicleID', None))
        if side is None:
            return
        field, otherID = side
        # A shell on a destroyed vehicle does nothing: not a hit. The shell that destroys it comes while it is alive.
        if not vehicle.isAlive():
            return
        battle = self._store.getBattle(player.arenaUniqueID)
        if battle is None:
            return
        if call.name == 'showDamageFromShot':
            hit = hit_parser.shotHit(call.get('damage'), _decodedPoints(vehicle, call.get('hitPoints')))
            if hit.vehiclePoints:
                hit = hit.replace(shotDirection=self._shotDirection(vehicle, attackerID, hit.vehiclePoints[0]))
            if field == 'dealtHits':
                hit = hit.replace(isGoldShell=_ownShellIsGold(player, hit.shellType))
        else:
            center = call.get('center')
            hit = hit_parser.splashHit(call.get('damage'), _chassisPoint(vehicle, center) if center is not None else ())
        arenaVehicle = player.arena.vehicles.get(otherID) or {}
        descriptor = arenaVehicle.get('vehicleType')
        hit = hit.replace(time=_battleTime(player.arena), playerName=arenaVehicle.get('name') or '',
                          attackerTeam=_team(player.arena, attackerID), targetTeam=_team(player.arena, vehicle.id),
                          vehicleDescriptor=compactDescriptor(descriptor),
                          distance=_distance(vehicle.id, attackerID), vehiclePose=_vehiclePose(vehicle))
        key, now = (field, otherID), BigWorld.serverTime()
        hit = self._pairing.withPending(key, hit, now)
        hits = getattr(battle, field) + (hit,)
        self._pairing.noteHit(key, now, battle.battleId, len(hits) - 1)
        self._store.update(battle.replace(**{field: hits}))

    def _shotDirection(self, vehicle, attackerID, point):
        matrix = _partMatrix(vehicle, point.tankPartIndex)
        if matrix is None:
            return ()
        return hit_parser.shotDirection(self._tracers, attackerID, matrix, point)

    def _onTracer(self, call):
        # A shell in flight, not one going on after a ricochet: where it starts and its velocity.
        if call.get('isRicochet'):
            return
        self._tracers.add(call.get('shooterID'), BigWorld.serverTime(), Math.Vector3(call.get('refStartPoint')),
                          Math.Vector3(call.get('velocity')), call.get('gravity') or 0.0)

    def _onBattleEvents(self, call):
        for event in call.get('events') or ():
            field = hit_parser.eventSide(event['eventType'])
            if field is not None:
                self._addInfo((field, event['targetID']), hit_parser.eventInfo(event['eventType'], event['details']))

    def _onDamageInfo(self, call):
        # What a shell of the attacker (entityID) did to the player's vehicle: a module or a crew member damaged, a
        # fire, the vehicle destroyed. The extra index 0 is none.
        avatar = call.entity
        vehicleID, damageIndex = call.get('vehicleID'), call.get('damageIndex')
        extraIndex, attackerID = call.get('extraIndex'), call.get('entityID')
        if vehicleID != getattr(avatar, 'playerVehicleID', None):
            return
        code = DAMAGE_INFO_CODES[damageIndex]
        if not hit_parser.isShotCode(code):
            return
        extra = avatar.vehicleTypeDescriptor.extras[extraIndex].name if extraIndex else ''
        self._addInfo(('receivedHits', attackerID), {'damagedDevices': (hit_parser.shotDevice(code, extra),)})

    def _addInfo(self, key, info):
        # Adds the info to the last hit of the key within the pairing time, or keeps it for the hit to come.
        now = BigWorld.serverTime()
        last = self._pairing.lastHit(key, now)
        battle = self._store.getBattle(last[0]) if last is not None else None
        if battle is None:
            self._pairing.keep(key, now, info)
            return
        field = key[0]
        hits, index = getattr(battle, field), last[1]
        hits = hits[:index] + (hit_parser.withInfo(hits[index], info),) + hits[index + 1:]
        self._store.update(battle.replace(**{field: hits}))
