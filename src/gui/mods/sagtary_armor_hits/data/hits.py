# -*- coding: utf-8 -*-
"""Hits of a battle: the shells that hit the player's vehicle and the shells the player hit other vehicles with.

The hits' data, as the battle files keep it (Record); hit_parser.py makes them from the server's calls,
hit_collector.py in battle.

- Hit: one hit, read from the client when the server tells about it (Vehicle.showDamageFromShot for a shell that hit,
  Vehicle.showDamageFromExplosion for a high explosive splash). It keeps what the server sent; its result is worked
  out from that, like the client's armor tooltip tells a shot: damage, not pierced, a ricochet, or no damage.
- DamagedDevice: a module or a crew member of the player's vehicle a shell damaged, by the client's own names (its
  damage info code, the vehicle's extra and the device kind), so it can be shown in any way later. The client's
  numbers for them are not kept: the extra's index depends on the vehicle type, the code's on the client version.
- HitPoint: one point a shell hit (a shell that ricochets or goes through spaced armor hits more than one): the
  vehicle part and the shell's way through its armor, as the server sends it (DamageFromShotDecoder.parseHitPoint).
  A hit keeps all its points, also those on parts other than the chassis, hull, turret and gun (the wheels of a
  wheeled vehicle); the drawing takes only those (Hit.vehiclePoints). The points are in the part's own space, so
  they are drawn on the same vehicle with the same modules, whatever the turret and the gun angles: the hit keeps
  the other vehicle's compact descriptor for that. The server packs a point to 1/255 of the part's size on each
  axis, so the direction along a short way is off by a degree or so: the hit keeps the shell's exact direction at
  its first point too (Hit.shotDirection), from the shell's tracer.
- The teams of the attacker and the target tell a hit on an ally (Hit.isAllyHit): the server sends it with no
  damage (team damage is off), its points as not pierced.
- VehiclePose: how the hit vehicle stood at the hit, as the client showed it: its turret and gun, its hull on its
  chassis when the hull moves on it, its steered wheels. Each point is in its own part's space, so it is on the same
  place of the part in any pose; the way between the points on two parts and the armor along it are as the pose was.
"""
import logging

from constants import VEHICLE_HIT_EFFECT

from gui.mods.sagtary_armor_hits.data.record import Record

_logger = logging.getLogger('sagtary.armor_hits')

# A vehicle's compact descriptor (items.vehicles.VehicleDescriptor.makeCompactDescr) starts with a header byte (the
# item type, items.ITEM_TYPES.vehicle, in the low 4 bits, the nation in the high 4 bits, this flag when the vehicle type
# id takes 2 bytes: items.vehicles.EXTENDED_VEHICLE_TYPE_ID_FLAG) and the vehicle type id.
_VEHICLE_ITEM_TYPE = 1
_EXTENDED_TYPE_ID = 2
# The parts of tankStructure.TankPartIndexes (chassis 0, hull 1, turret 2, gun 3); the client numbers the others (the
# wheels of a wheeled vehicle, below 0) after them.
_VEHICLE_PARTS = 4
# The constants.VEHICLE_HIT_EFFECT names a point keeps its effect by: a name tells what it was even when the client
# renames or renumbers its codes.
_EFFECT_NAMES = ('ARMOR_PIERCED_NO_DAMAGE', 'INTERMEDIATE_RICOCHET', 'FINAL_RICOCHET', 'ARMOR_NOT_PIERCED',
                 'ARMOR_PIERCED', 'CRITICAL_HIT', 'ARMOR_PIERCED_DEVICE_DAMAGED', 'INVALID')


class HitResult(object):
    # The hit's result: damage, then the results of the client's armor tooltip for a hit without damage (the armor
    # stopped the shell, the shell ricocheted, the shell pierced the armor but did no damage).
    DAMAGE = 'damage'
    BLOCKED = 'blocked'
    RICOCHET = 'ricochet'
    NO_DAMAGE = 'noDamage'
    ALL = (DAMAGE, BLOCKED, RICOCHET, NO_DAMAGE)


class HitPoint(Record):
    FIELDS = (
        ('tankPartIndex', 0),   # the vehicle part as the client numbers it (tankStructure.TankPartIndexes: chassis 0,
                                # hull 1, turret 2, gun 3; a wheel of a wheeled vehicle below 0)
        ('start', ()),          # (x, y, z) of the shell's way before the armor, in metres in the part's space
        ('end', ()),            # (x, y, z) of the shell's way behind the armor
        ('effect', ''),         # what the shell did there: a constants.VEHICLE_HIT_EFFECT name (ARMOR_PIERCED, ...),
                                # the code as text when the client has no name for it
        ('hitType', ''),        # the point's hit type the server sends besides the effect (in its params), by the same
                                # names: ARMOR_PIERCED, ARMOR_NOT_PIERCED, ...; '' when not known
    )
    __slots__ = tuple(name for name, _ in FIELDS)

    @property
    def effectCode(self):
        # The constants.VEHICLE_HIT_EFFECT code of the effect, None when not known.
        return effectCode(self.effect)

    @property
    def isOnVehiclePart(self):
        # On the chassis, hull, turret or gun, the parts the hangar vehicle's points are drawn on.
        return 0 <= self.tankPartIndex < _VEHICLE_PARTS


class DamagedDevice(Record):
    FIELDS = (
        ('code', ''),           # constants.DAMAGE_INFO_CODES name: DEVICE_CRITICAL_AT_SHOT, DEVICE_DESTROYED_AT_SHOT,
                                # TANKMAN_HIT_AT_SHOT, DEVICE_STARTED_FIRE_AT_SHOT, DEATH_FROM_SHOT, ...
        ('extra', ''),          # the vehicle's extra (its slot) the code is about: engineHealth, leftTrack0Health,
                                # gunner2Health, ...; '' for none
        ('device', ''),         # the extra's kind, an items.vehicles VEHICLE_DEVICE_TYPE_NAMES or VEHICLE_TANKMAN_TYPE_NAMES
                                # name: engine, track, gunner, ...; '' when it is not one
    )
    __slots__ = tuple(name for name, _ in FIELDS)


class VehiclePose(Record):
    FIELDS = (
        ('turretYaw', 0.0),     # radians the turret is turned on the hull (Vehicle.getAimParams)
        ('gunPitch', 0.0),      # radians of the gun's pitch; below 0 the gun is raised, as the client has it
    )
    __slots__ = tuple(name for name, _ in FIELDS)


class Hit(Record):
    FIELDS = (
        ('time', 0.0),          # seconds since the battle started (the arena's battle period)
        ('vehicleDescriptor', ''),
                                # the other vehicle (the shooter of a received hit, the target of a dealt one): its
                                # compact descriptor (type and modules), hex; '' when not known
        ('playerName', ''),     # the other vehicle's player
        ('attackerTeam', None), # the team of the vehicle that shot (the arena's), None when not known
        ('targetTeam', None),   # the team of the vehicle that was hit, None when not known
        ('shellType', ''),      # the shell kind, a constants.SHELL_TYPES name: ARMOR_PIERCING, HIGH_EXPLOSIVE, ...
        ('caliber', 0.0),       # the shell's caliber in millimetres, as the hit points tell it; 0 when not known
        ('damage', 0),          # hit points the hit took
        ('isSplash', False),    # a high explosive splash nearby, not a hit on the armor
        ('critsCount', 0),      # modules and crew the hit damaged, as the client's damage log counts them
        ('isGoldShell', False), # a premium shell
        ('points', ()),         # the points the shell hit, in order (HitPoint); none for a splash
        ('distance', 0.0),      # metres between the shooter and the target at the hit; 0 when not known
        ('damagedDevices', ()), # what the shell did to the player's vehicle (received hits), in order (DamagedDevice)
        ('splashCenter', ()),   # (x, y, z) where a splash's shell burst, in metres in the hit vehicle's chassis space
                                # (part 0 of the points); () when not known
        ('shotDirection', ()),  # (x, y, z) unit direction of the shell at the first point of vehiclePoints, in its part
                                # space,
                                # from the shell's tracer (exact, unlike the points); () when not known
        ('vehiclePose', None),  # how the hit vehicle stood at the hit (VehiclePose); None when not known
    )
    NESTED = {'points': HitPoint, 'damagedDevices': DamagedDevice, 'vehiclePose': VehiclePose}
    __slots__ = tuple(name for name, _ in FIELDS)

    @property
    def vehicleId(self):
        # The other vehicle's type (intCD), from its compact descriptor; 0 when not known.
        return vehicleTypeId(self.vehicleDescriptor)

    @property
    def isAllyHit(self):
        # A hit on a vehicle of the shooter's own team that took no damage (the client's team damage is off).
        return self.attackerTeam is not None and self.attackerTeam == self.targetTeam and self.damage == 0

    @property
    def hitEffects(self):
        # constants.VEHICLE_HIT_EFFECT code of each point the shell hit, in order.
        return tuple(point.effectCode for point in self.points)

    @property
    def vehiclePoints(self):
        # The points on the chassis, hull, turret and gun, in order: those that are drawn.
        return tuple(point for point in self.points if point.isOnVehiclePart)

    @property
    def result(self):
        # Without damage, the last point the shell hit tells what stopped it; a splash without damage is blocked.
        if self.damage > 0:
            return HitResult.DAMAGE
        last = self.hitEffects[-1] if self.hitEffects else VEHICLE_HIT_EFFECT.ARMOR_NOT_PIERCED
        if last in VEHICLE_HIT_EFFECT.RICOCHETS:
            return HitResult.RICOCHET
        if last in VEHICLE_HIT_EFFECT.PIERCED_HITS:
            return HitResult.NO_DAMAGE
        return HitResult.BLOCKED


def effectName(code):
    # The name a point keeps its constants.VEHICLE_HIT_EFFECT code by; the code as text without one.
    for name in _EFFECT_NAMES:
        if getattr(VEHICLE_HIT_EFFECT, name, None) == code:
            return name
    return str(code)


def effectCode(name):
    # The constants.VEHICLE_HIT_EFFECT code of a point's effect name (or of a code kept as text); None when not known.
    if name in _EFFECT_NAMES:
        return getattr(VEHICLE_HIT_EFFECT, name, None)
    return int(name) if name.isdigit() else None


def compactDescriptor(descriptor):
    # The compact descriptor of a vehicle descriptor (its type and modules) as hex, '' without one.
    if descriptor is None:
        return ''
    try:
        return descriptor.makeCompactDescr().encode('hex')
    except Exception:
        _logger.exception('hits: no compact descriptor of %s', descriptor)
        return ''


def vehicleTypeId(compactDescriptor):
    # The vehicle type's intCD (items.makeIntCompactDescrByID) from the first bytes of a compact descriptor (hex), so
    # without the client's cache; 0 without one.
    if not compactDescriptor:
        return 0
    try:
        data = bytearray(compactDescriptor.decode('hex'))
        typeId = data[1] + (data[2] << 8 if data[0] & _EXTENDED_TYPE_ID else 0)
    except (TypeError, ValueError, IndexError):
        _logger.warning('hits: not a compact descriptor: %r', compactDescriptor)
        return 0
    return (typeId << 8) + (data[0] >> 4 << 4) + _VEHICLE_ITEM_TYPE


def ownShellIsGold(descriptor, shellType, currentShellCD=None):
    # Whether the player's shell of the kind is a premium one: the gun's only shell of the kind, else its current
    # shell when of the kind; None when not known.
    shells = [shot.shell for shot in descriptor.gun.shots if shot.shell.kind == shellType]
    if len(shells) == 1:
        return bool(shells[0].isGold)
    for shell in shells:
        if shell.compactDescr == currentShellCD:
            return bool(shell.isGold)
    return None
