# -*- coding: utf-8 -*-
"""The hits (hits.py) from the server's calls about them: what the calls carry and what the client knows at them.

Nothing here reads the client: hit_collector.py reads it in battle (the decoded hit points, the vehicles, the times)
and gives it here, so the same rules can make the hits from any source of the same data.

- hitSide: whose hit it is: receivedHits (the player's vehicle was hit), dealtHits (the player's vehicle hit another
  one), none for the other vehicles' hits.
- shotHit, splashHit: a shell's hit from its hit points as the client decodes them (DamageFromShotDecoder.
  parseHitPoint), a high explosive splash from where it burst.
- eventInfo, shotDevice, withInfo: what more the client's battle events (PlayerAvatar.onBattleEvents, the source of its
  damage log) and its damage info of the player's vehicle (PlayerAvatar.showVehicleDamageInfo) tell about a hit:
  crits, a premium shell, the modules and crew the shell damaged.
- HitPairing: the events and the hit of the same vehicle within _PAIRING_TIME before or after it are one hit.
- vehiclePose: the hit vehicle's pose from what the client shows of it.
- Tracers, shotDirection: the shooter's tracer (PlayerAvatar.showTracer: where the shell starts, its velocity and
  gravity, as floats) gives the shell's direction at the first point: the tracer whose way passes the point nearest,
  within _TRACER_MISS metres; none when there was no such tracer.
"""
import math

import Math
from BattleFeedbackCommon import BATTLE_EVENT_TYPE, NONE_SHELL_TYPE
from constants import SHELL_TYPES, SHELL_TYPES_LIST
from items.vehicles import DEVICE_TANKMAN_NAMES_TO_VEHICLE_EXTRA_NAMES

from gui.mods.sagtary_armor_hits.data.hits import DamagedDevice, Hit, HitPoint, VehiclePose, effectName

# Decimals of the hit point coordinates in metres: the server sends them to about 1 cm; of a direction's; of a caliber
# in millimetres: the server sends it to 0.1 mm; of an angle in radians.
_POINT_DECIMALS = 3
_DIRECTION_DECIMALS = 4
_CALIBER_DECIMALS = 1
_ANGLE_DECIMALS = 4
# The client's battle events (BattleFeedbackCommon.BATTLE_EVENT_TYPE) that tell more about a hit: the side of the
# hit; the event's targetID is the other vehicle (the target of the player's hit, the attacker of a received one).
_EVENT_SIDES = {
    BATTLE_EVENT_TYPE.DAMAGE: 'dealtHits',
    BATTLE_EVENT_TYPE.CRIT: 'dealtHits',
    BATTLE_EVENT_TYPE.RECEIVED_DAMAGE: 'receivedHits',
    BATTLE_EVENT_TYPE.RECEIVED_CRIT: 'receivedHits',
    BATTLE_EVENT_TYPE.TANKING: 'receivedHits',
}
_CRIT_EVENTS = (BATTLE_EVENT_TYPE.CRIT, BATTLE_EVENT_TYPE.RECEIVED_CRIT)
# The client's damage info codes of a shell have this in their names (DEVICE_CRITICAL_AT_SHOT, DEATH_FROM_SHOT, ...).
_SHOT_CODE = 'SHOT'
# {vehicle extra name: device or crew kind}
_EXTRA_DEVICES = dict((extra, device) for device, extras in DEVICE_TANKMAN_NAMES_TO_VEHICLE_EXTRA_NAMES.items()
                      for extra in extras)
# The server tells the event and the client shows the shell hit at about the same time, either one first (the hit
# waits for the shell's flight): an event and a hit of the same vehicle within this many seconds are one hit.
_PAIRING_TIME = 1.5
# Seconds a shooter's tracer is kept for its hit (an artillery shell flies a few seconds); metres its way may pass the
# hit point by (the point is packed to about 1-4 cm, the vehicle moves) and still be the hit's shell.
_TRACER_TIME = 10.0
_TRACER_MISS = 2.5


def vector(value):
    # (x, y, z) of a vector, rounded as the hits keep points.
    return tuple(round(item, _POINT_DECIMALS) for item in (value.x, value.y, value.z))


def _shellType(index):
    # SHELL_TYPES_LIST index of a decoded hit point, as the shell kind name.
    return SHELL_TYPES_LIST[index] if 0 <= index < len(SHELL_TYPES_LIST) else ''


def hitSide(vehicleID, attackerID, playerVehicleID):
    # (the Battle field of the hit of the attacker on the vehicle, the other vehicle's id); None when it is not the
    # player's.
    if vehicleID == playerVehicleID:
        return 'receivedHits', attackerID
    if attackerID == playerVehicleID:
        return 'dealtHits', vehicleID
    return None


def shotHit(damage, decodedPoints):
    # A shell's hit from its points as DamageFromShotDecoder.parseHitPoint gives them: (part index, hit effect,
    # start, end, hit type, shell type index, caliber). All of them, on any part; the shell type and the caliber are
    # the same at all the points of a shell, but for those without them.
    points, shellType, caliber = [], '', 0.0
    for part, effect, start, end, hitType, shellTypeIndex, pointCaliber in decodedPoints:
        shellType = shellType or _shellType(shellTypeIndex)
        caliber = caliber or round(pointCaliber, _CALIBER_DECIMALS)
        points.append(HitPoint(tankPartIndex=part, start=vector(start), end=vector(end), effect=effectName(effect),
                               hitType=effectName(hitType)))
    return Hit(damage=damage or 0, shellType=shellType, caliber=caliber, points=tuple(points))


def splashHit(damage, center):
    # A high explosive splash; center: where it burst in the hit vehicle's chassis space, () when not known.
    return Hit(shellType=SHELL_TYPES.HIGH_EXPLOSIVE, damage=damage or 0, isSplash=True, splashCenter=center)


def vehiclePose(aimParams):
    # The hit vehicle's pose. aimParams: (turret yaw, gun pitch) as Vehicle.getAimParams gives them.
    turretYaw, gunPitch = aimParams
    return VehiclePose(turretYaw=round(turretYaw, _ANGLE_DECIMALS), gunPitch=round(gunPitch, _ANGLE_DECIMALS))


def eventSide(eventType):
    # The Battle field of the hits a battle event tells about, None for an event about none.
    return _EVENT_SIDES.get(eventType)


def eventInfo(eventType, details):
    # {Hit field: value} of a battle event: crits, a premium shell. The events of the player's own hits do not tell
    # the shell (NONE_SHELL_TYPE): no premium flag from them.
    if eventType in _CRIT_EVENTS:
        critsCount, _, shellTypeID, isGold = BATTLE_EVENT_TYPE.unpackCrits(details)[:4]
        info = {'critsCount': critsCount}
    else:
        shellTypeID, isGold = BATTLE_EVENT_TYPE.unpackDamage(details)[3:5]
        info = {}
    if shellTypeID != NONE_SHELL_TYPE:
        info['isGoldShell'] = bool(isGold)
    return info


def isShotCode(code):
    # The damage info code (a constants.DAMAGE_INFO_CODES name) is about a shell.
    return _SHOT_CODE in code


def shotDevice(code, extra):
    # The module or crew member of the vehicle's extra (its name, '' for none) the code tells about.
    return DamagedDevice(code=code, extra=extra, device=_EXTRA_DEVICES.get(extra, ''))


def withInfo(hit, info):
    # The hit with the info of an event: the damaged devices are added to those it has, the others replaced.
    devices = info.get('damagedDevices')
    if devices:
        info = dict(info, damagedDevices=hit.damagedDevices + devices)
    return hit.replace(**info)


class HitPairing(object):
    # The hits and the events of each (Battle field, other vehicle id) key, by their server times.

    def __init__(self):
        # {key: (server time, battle id, hit index)}: the last hit, for the events after it.
        self._lastHits = {}
        # {key: [(server time, info)]}: events that came before their hit.
        self._pendingEvents = {}

    def reset(self):
        self._lastHits = {}
        self._pendingEvents = {}

    def withPending(self, key, hit, now):
        # The hit with the info of the key's events that came within _PAIRING_TIME before it.
        for eventTime, info in self._pendingEvents.pop(key, ()):
            if now - eventTime <= _PAIRING_TIME:
                hit = withInfo(hit, info)
        return hit

    def noteHit(self, key, now, battleID, index):
        self._lastHits[key] = (now, battleID, index)

    def lastHit(self, key, now):
        # (battle id, hit index) of the key's hit within _PAIRING_TIME before, None.
        last = self._lastHits.get(key)
        if last is None or now - last[0] > _PAIRING_TIME:
            return None
        return last[1], last[2]

    def keep(self, key, now, info):
        # An event's info for the key's hit to come.
        self._pendingEvents.setdefault(key, []).append((now, info))


class Tracers(object):
    # The shells in flight by shooter: their tracers.

    def __init__(self):
        # {shooter id: [(server time, start, velocity, gravity)]}
        self._tracers = {}

    def reset(self):
        self._tracers = {}

    def add(self, shooterID, now, start, velocity, gravity):
        # A tracer (start and velocity: Math.Vector3); those older than _TRACER_TIME are dropped.
        for otherID in list(self._tracers):
            tracers = [tracer for tracer in self._tracers[otherID] if now - tracer[0] <= _TRACER_TIME]
            if tracers:
                self._tracers[otherID] = tracers
            else:
                del self._tracers[otherID]
        self._tracers.setdefault(shooterID, []).append((now, start, velocity, gravity))

    def nearest(self, shooterID, target):
        # (metres the way passes the world point by, the shell's velocity there) of the shooter's tracer whose way
        # passes the point nearest; None without one. The shell flies on a parabola: its horizontal velocity stays,
        # gravity bends it down.
        best = None
        for _, origin, velocity, gravity in self._tracers.get(shooterID, ()):
            flat = math.hypot(velocity.x, velocity.z)
            if flat < 1e-3:
                continue
            flight = math.hypot(target.x - origin.x, target.z - origin.z) / flat
            position = origin + velocity * flight - Math.Vector3(0.0, gravity * flight * flight * 0.5, 0.0)
            miss = (target - position).length
            if best is None or miss < best[0]:
                best = (miss, Math.Vector3(velocity.x, velocity.y - gravity * flight, velocity.z))
        return best


def shotDirection(tracers, attackerID, matrix, point):
    # The shell's direction at the point (HitPoint) in the point's part space, from the attacker's tracer whose way
    # passes the point nearest (within _TRACER_MISS); () without one. matrix: the part's world matrix (Math.Matrix,
    # inverted here).
    start, end = Math.Vector3(*point.start), Math.Vector3(*point.end)
    best = tracers.nearest(attackerID, matrix.applyPoint((start + end) * 0.5))
    if best is None or best[0] > _TRACER_MISS:
        return ()
    matrix.invert()
    direction = matrix.applyVector(best[1])
    direction.normalise()
    return tuple(round(value, _DIRECTION_DECIMALS) for value in (direction.x, direction.y, direction.z))
