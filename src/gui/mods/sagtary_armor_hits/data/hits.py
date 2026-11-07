# -*- coding: utf-8 -*-
"""Hits of a battle: the shells that hit the player's vehicle and the shells the player hit other vehicles with.

The hits' data, as the battle files keep it (Record); hit_parser.py makes them from the server's calls,
hit_collector.py in battle.

- Hit: what a hit of either side has, read from the client when the server tells about it (Vehicle.showDamageFromShot
  for a shell that hit, Vehicle.showDamageFromExplosion for a high explosive splash). It keeps what the server sent;
  its result is worked out from that, like the client's armor tooltip tells a shot: damage, not pierced, a ricochet,
  or no damage.
- HitVehicle: the shooter or the target of a hit, as it was at the hit: a player's vehicle can change within a battle
  (a respawn, another one chosen before the battle starts), so each hit keeps both.
- ReceivedHit: a hit on the player's vehicle: the modules and crew the shell damaged (DamagedDevice, HitCrit).
- DealtHit: a hit of the player on another vehicle: the client tells only how many modules and crew it damaged.
- DamagedDevice: a module or a crew member of the player's vehicle a shell damaged, by the client's own names (its
  damage info code and the vehicle's extra), so it can be shown in any way later. The client's
  numbers for them are not kept: the extra's index depends on the vehicle type, the code's on the client version.
  The server tells a module only when its state changes: not when the shell hits one damaged before, not on the
  shot that destroys the vehicle.
- HitCrit: a kind of module or crew member of the player's vehicle a shell damaged, as the hit's crits mask tells it
  (PlayerAvatar.showOwnVehicleHitDirection): every hit has it, one for each kind, as the client counts crits in battle.
  The mask is kept by the client's names too, its bits' order depends on the client version.
- HitPoint: one point a shell hit (a shell that ricochets or goes through spaced armor hits more than one): the
  vehicle part and the shell's way through its armor, as the server sends it (DamageFromShotDecoder.parseHitPoint).
  A hit keeps all its points, also those on parts other than the chassis, hull, turret and gun (the wheels of a
  wheeled vehicle); the drawing takes only those (Hit.vehiclePoints). The points are in the part's own space, so
  they are drawn on the same vehicle with the same modules, whatever the turret and the gun angles: the hit keeps
  the target's compact descriptor for that. The server packs a point to 1/255 of the part's size on each
  axis, so the direction along a short way is off by a degree or so: the hit keeps the shell's exact direction at
  its first point too (Hit.shotDirection), from the shell's tracer.
- The teams of the shooter and the target tell a hit on an ally (Hit.isAllyHit): the server sends it with no
  damage (team damage is off), its points as not pierced.
- VehiclePose: how the hit vehicle stood at the hit, as the client showed it: its turret and gun, its hull on its
  chassis when the hull moves on it, its steered wheels. Each point is in its own part's space, so it is on the same
  place of the part in any pose; the way between the points on two parts and the armor along it are as the pose was.
- The shell's mode, for a gun that changes some of its shell's parameters before the shot (the client's shell params
  switcher mechanic: standard or calibrated shells), kept two ways, each as the client tells it:
  - Hit.shotMode: the mode the server puts into the battle event of the hit (the client's damage log shows it), so
    only for a hit with an event: a hit of the player with damage or crits, a hit on the player's vehicle.
  - Hit.shooterSwitcher (ShellSwitcherState): the shooter's switcher as the client knows it at the hit, for any
    shooter the client sees with the mechanic. The hit comes after the shot, so its state may already be the next
    shot's; the time of the shooter's last calibrated shot tells the hit's shell.
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
                                # TANKMAN_HIT_AT_SHOT, DEATH_FROM_SHOT, ...
        ('extra', ''),          # the vehicle's extra (its slot) the code is about: engineHealth, leftTrack0Health,
                                # gunner2Health, ...; '' for none
    )
    __slots__ = tuple(name for name, _ in FIELDS)


class HitCrit(Record):
    FIELDS = (
        ('kind', ''),           # a gui.shared.crits_mask_parser.CRIT_MASK_SUB_TYPES name: criticalDevices,
                                # destroyedDevices, destroyedTankmen (a crew member hurt)
        ('device', ''),         # the kind of module or crew member, an items.vehicles VEHICLE_DEVICE_TYPE_NAMES or
                                # VEHICLE_TANKMAN_TYPE_NAMES name: track, fuelTank, commander, ...
    )
    __slots__ = tuple(name for name, _ in FIELDS)


class VehiclePose(Record):
    FIELDS = (
        ('turretYaw', 0.0),     # radians the turret is turned on the hull (Vehicle.getAimParams)
        ('gunPitch', 0.0),      # radians of the gun's pitch; below 0 the gun is raised, as the client has it
    )
    __slots__ = tuple(name for name, _ in FIELDS)


class ShellSwitcherState(Record):
    FIELDS = (
        ('state', ''),          # the switcher's state: a constants.SHELL_PARAMS_SWITCHER_STATE name (NOT_CHARGED:
                                # standard shells, CHARGED: calibrated, SWITCHING_ON, SWITCHING_OFF), the code as text
                                # when the client has no name for it
        ('isActive', False),    # calibrated shells on, as the other players' clients see it
        ('lastActiveShotTime', 0.0),
                                # seconds since the battle started of the shooter's last shot with calibrated shells;
                                # 0 when there was none
    )
    __slots__ = tuple(name for name, _ in FIELDS)


class HitVehicle(Record):
    FIELDS = (
        ('vehicleDescriptor', ''),
                                # its compact descriptor (type and modules), hex; '' when not known
        ('playerName', ''),     # its player
        ('team', None),         # its team (the arena's), None when not known
    )
    __slots__ = tuple(name for name, _ in FIELDS)

    @property
    def vehicleId(self):
        # The vehicle's type (intCD), from its compact descriptor; 0 when not known.
        return vehicleTypeId(self.vehicleDescriptor)


class Hit(Record):
    FIELDS = (
        ('time', 0.0),          # seconds since the battle started (the arena's battle period)
        ('shooter', HitVehicle()),
                                # the vehicle that shot
        ('target', HitVehicle()),
                                # the vehicle that was hit
        ('shellType', ''),      # the shell kind, a constants.SHELL_TYPES name: ARMOR_PIERCING, HIGH_EXPLOSIVE, ...
        ('caliber', 0.0),       # the shell's caliber in millimetres, as the hit points tell it; 0 when not known
        ('damage', 0),          # hit points the hit took
        ('isSplash', False),    # a high explosive splash nearby, not a hit on the armor
        ('isGoldShell', False), # a premium shell
        ('points', ()),         # the points the shell hit, in order (HitPoint); none for a splash
        ('distance', 0.0),      # metres between the shooter and the target at the hit; 0 when not known
        ('splashCenter', ()),   # (x, y, z) where a splash's shell burst, in metres in the hit vehicle's chassis space
                                # (part 0 of the points); () when not known
        ('shotDirection', ()),  # (x, y, z) unit direction of the shell at the first point of vehiclePoints, in its part
                                # space,
                                # from the shell's tracer (exact, unlike the points); () when not known
        ('targetPose', None),   # how the target stood at the hit (VehiclePose); None when not known
        ('shotMode', ''),       # the shell's mode by the hit's battle event: a constants.BATTLE_LOG_MECHANIC_SHOT name
                                # (NOT_DEFINED: a gun without such a mechanic or a shell it does not change,
                                # SHELL_SWITCHER_NOT_CHARGED: standard shell, SHELL_SWITCHER_CHARGED: calibrated shell,
                                # BUSTLE_FEED_ACTIVE), the code as text when the client has no name for it; '' without
                                # an event
        ('shooterSwitcher', None),
                                # the shooter's shell params switcher at the hit (ShellSwitcherState); None when the
                                # client does not see one
    )
    NESTED = {'shooter': HitVehicle, 'target': HitVehicle, 'points': HitPoint, 'targetPose': VehiclePose,
              'shooterSwitcher': ShellSwitcherState}
    __slots__ = tuple(name for name, _ in FIELDS)

    @property
    def isAllyHit(self):
        # A hit on a vehicle of the shooter's own team that took no damage (the client's team damage is off).
        return self.shooter.team is not None and self.shooter.team == self.target.team and self.damage == 0

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


class ReceivedHit(Hit):
    FIELDS = Hit.FIELDS + (
        ('damagedDevices', ()), # what the shell did to the player's vehicle, in order (DamagedDevice)
        ('crits', ()),          # the kinds of modules and crew of the player's vehicle the shell damaged, as its crits
                                # mask tells them (HitCrit)
    )
    NESTED = dict(Hit.NESTED, damagedDevices=DamagedDevice, crits=HitCrit)
    __slots__ = ('damagedDevices', 'crits')

    @property
    def other(self):
        # The vehicle that is not the player's.
        return self.shooter

    @property
    def critsTotal(self):
        # The modules and crew the shell damaged, as the client counts them in battle.
        return len(self.crits)


class DealtHit(Hit):
    FIELDS = Hit.FIELDS + (
        ('critsCount', 0),      # modules and crew the hit damaged, as the client's damage log counts them
    )
    __slots__ = ('critsCount',)

    @property
    def other(self):
        # The vehicle that is not the player's.
        return self.target

    @property
    def critsTotal(self):
        # The modules and crew the hit damaged, as the client counts them in battle.
        return self.critsCount


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
    try:
        return int(name)
    except ValueError:
        return None


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
