# -*- coding: utf-8 -*-
"""Shot panel of the hits screen, on the right: the chosen hit's shooter and target, its result and its numbers.

ShotPanelPresenter fills the view model (views/models/shot_panel_model.py) for the hit the hits panel has chosen:

- the cards of the shooter and the target: the player, the vehicle (the client's name, tier, icon and nation flag)
  with its modules of the battle (the compact descriptor); beside the shooter its gun and the shell of the hit (the
  hit's shell mode, standard or calibrated, in the top right corner of the shell's icon, like the client marks a gun's
  mechanic on a module; only shown, the numbers do not count it),
  beside the target its turret when it has one (not a turretless vehicle) and its gun, as icons like the armor page's. On the
  received side the shooter is the other vehicle and the target the player's, on the dealt side the other way round.
  Over an icon the client's tooltip of the module (CONTEXT_VEHICLE_MODULE) or of the shell (ARMOR_INSPECTOR_SHELL)
  shows, for the vehicle as the hangar shows it (a maps training copy as the vehicle it copies): tooltipData;
- the sections, each with its icon (the client's damage log icons for damage and modules, the mod's for the others):
  damage (the hit's, the shell's average), penetration (the shell's, at the hit's distance when it is
  known), armor and impact angle (the vehicle's armor where the hit line meets it, counted in the garage like the
  client's armor tooltip does: getMaterialsAtCursor along the line, the shell's penetration chance there,
  calculatePenetrationInfo), distance (recorded in battle) and modules and crew. On a hit on the player's vehicle
  that damaged some, modules and crew are laid out like the battle damage panel, with its icons (gui/maps/
  sagtary_armor_hits/modules/): the vehicle's module kinds in the panel's order in two columns, an abstract tank
  between them with its tracks or wheels, the crew members in a row under them, each at the state this shot left it
  in (not what was damaged before it). The crits mask tells the kinds on every hit, at the worst state of a kind; the
  damage info tells which one of a kind, only when its state changed: without it the chassis' icon shows the damage
  and the tank does not, and all the members of a role are hurt. The client tells nothing of the kind on a hit of
  another vehicle: there the section has its count only.

The shell is the overlay panel's (overlay_panel.py: the shooter's gun and shot with the hit's shell kind); the hit
line is the hit lines presenter's (hit_lines.py: its first point and direction when drawn). The armor needs the
vehicle's collision model, which comes a few frames after the vehicle: without it the armor is counted again after
_RETRY seconds, up to _TRIES times. The panel is filled once in the frame after a change, as one change comes from
the hits panel and the hit lines together. The armor is what the line meets from _RAY / 2 before the hit point: a
part in front of it is not what the shell hit. A value counted in the garage is marked (counted) for the page.
"""
import logging
import math

import BigWorld
import nations
from helpers import dependency, int2roman
from helpers_common import computePiercingPowerAtDist
from gui import TANKMEN_ROLES_ORDER_DICT
from gui.battle_control.vehicle_getter import getCrewMainRolesWithIndexes, hasTurretRotator
from gui.impl.backport import createTooltipData
from gui.impl.gen import R
from gui.Scaleform.genConsts.TOOLTIPS_CONSTANTS import TOOLTIPS_CONSTANTS
from gui.shared.gui_items.Vehicle import Vehicle
from items import parseIntCompactDescr, vehicles
from items.components.component_constants import MODERN_HE_PIERCING_POWER_REDUCTION_FACTOR_FOR_SHIELDS
from skeletons.gui.shared.utils import IHangarSpace

from gui.mods.sagtary_armor_hits.data.client_names import (clientText, copiedName, shownVehicleDescr,
                                                           shownVehicleId, vehicleShortName)
from gui.mods.sagtary_armor_hits.data.hits import HitResult
from gui.mods.sagtary_armor_hits.views.hits.hits_panel import DEALT
from gui.mods.sagtary_armor_hits.views.models.shot_panel_model import (ShotDeviceModel, ShotModuleModel, ShotRowModel,
                                                                       ShotSectionModel, ShotTankPartModel)

_logger = logging.getLogger('sagtary.armor_hits')

_VEHICLE_ICON = 'img://gui/maps/icons/vehicle/%s.png'
_FLAG = 'img://gui/maps/icons/flags/160x100/%s.png'
_GUN_ICON = 'img://gui/maps/icons/modules/gun.png'
_TURRET_ICON = 'img://gui/maps/icons/modules/tower.png'
_SHELL_ICON = 'img://gui/maps/icons/shell/x64x64/%s.png'
# The card roles, as the page names them in a tooltip's arguments.
_SHOOTER = 'shooter'
_TARGET = 'target'
_NONE = u'—'
# The shell kind's abbreviation of the client's damage log (AP, APCR, HE, ...), as the hits panel shows it.
_SHELL_TEXT_KEY = '#ingame_gui:damageLog/shellType/%s'
# The armor tooltip's name of an armor layer's part, by VehicleArmorTags.
_PART_TEXT_KEY = '#armor_inspector:tooltip/armor/part/%s'
# The modules and crew cells: the battle damage panel's module kinds (VEHICLE_GUI_ITEMS) in its order, in two columns
# (groups 0 and 1); the chassis is a track's or, on a wheeled vehicle, a wheel's; the crew members' row.
_MODULE_COLUMNS = (('engine', 'ammoBay', 'gun', 'turretRotator'), ('chassis', 'surveyingDevice', 'radio', 'fuelTank'))
_CREW_GROUP = 2
# The chassis on the tank, (the page's name of a part, the vehicle's extra): a usual vehicle's tracks; with a track
# within a track each side has the main one outside and the reserve one, which the vehicle goes on without it, inside.
_TWO_TRACKS = (('trackLeft', 'leftTrack0Health'), ('trackRight', 'rightTrack0Health'))
_FOUR_TRACKS = (('trackLeftMain', 'leftTrack1Health'), ('trackLeftReserve', 'leftTrack0Health'),
                ('trackRightReserve', 'rightTrack0Health'), ('trackRightMain', 'rightTrack1Health'))
# A wheel's extra and its part on the tank's left and right.
_WHEEL_EXTRA = 'wheel%dHealth'
_WHEEL_LEFT = 'wheelLeft'
_WHEEL_RIGHT = 'wheelRight'
# A vehicle's extras: the name of a module kind or crew member with this at its end; the names without their numbers
# of the chassis' extras.
_EXTRA_SUFFIX = 'Health'
_CHASSIS_EXTRAS = ('leftTrack', 'rightTrack', 'wheel')
# The state a shot leaves a kind in, by its crits mask's kind (data/hits.py HitCrit); an extra, by its damage info's
# code (data/hits.py DamagedDevice); the states, the worst last; the panel icon's suffix of a state (a crew member has
# only the orange one: a hurt one is critical).
_CRIT_STATES = {'criticalDevices': 'critical', 'destroyedDevices': 'destroyed', 'destroyedTankmen': 'critical'}
_INFO_STATES = {'DEVICE_CRITICAL_AT_SHOT': 'critical', 'DEVICE_DESTROYED_AT_SHOT': 'destroyed',
                'TANKMAN_HIT_AT_SHOT': 'critical', 'DEATH_FROM_DEVICE_EXPLOSION_AT_SHOT': 'destroyed'}
_STATES = ('normal', 'critical', 'destroyed')
_ICON_SUFFIXES = {'normal': '', 'critical': '_orange', 'destroyed': '_red'}
# Metres of the hit line looked along for the armor: before and after its first point.
_RAY = 2.5
# The armor is counted again while the collision model has not come: seconds between, how many times.
_RETRY = 0.2
_TRIES = 5


def _descriptor(vehicleId, descr):
    # The vehicle descriptor with its modules (compact descriptor, hex), else with the default ones; None.
    try:
        if descr:
            return vehicles.VehicleDescr(compactDescr=descr.decode('hex'))
        nationID, typeID = parseIntCompactDescr(vehicleId)[1:]
        return vehicles.VehicleDescr(typeID=(nationID, typeID))
    except Exception:
        return None


def _vehicleImages(vehicleId):
    # (icon, flag) of the vehicle as the hangar shows it (a maps training copy as the vehicle it copies).
    try:
        vehicleType = vehicles.getVehicleType(shownVehicleId(vehicleId) or vehicleId)
        return _VEHICLE_ICON % vehicleType.name.replace(':', '-'), _FLAG % nations.NAMES[vehicleType.id[0]]
    except Exception:
        return '', ''


def _shownVehicle(vehicleId, descr):
    # The client's vehicle item as the hangar shows the vehicle, with its modules of the battle; None.
    try:
        strCD = shownVehicleDescr(vehicleId, descr)
        if strCD:
            return Vehicle(strCompactDescr=strCD)
        return Vehicle(typeCompDescr=shownVehicleId(vehicleId) or vehicleId)
    except Exception:
        return None


def _shownGun(descriptor, gun):
    # The gun of the shown vehicle that the gun is (a maps training gun copies one by name); the installed one.
    for turret in descriptor.type.turrets[0]:
        for item in turret.guns:
            if item.name == copiedName(gun.name):
                return item
    return descriptor.gun


def _worst(states):
    return max(states or ['normal'], key=_STATES.index)


def _extraKind(extra):
    # The module kind or crew role of a vehicle's extra: leftTrack1Health and wheel3Health are the chassis,
    # loader2Health a loader.
    name = extra[:-len(_EXTRA_SUFFIX)].rstrip('0123456789')
    return 'chassis' if name in _CHASSIS_EXTRAS else name


def _damage(hit):
    # ({module kind or crew role: state}, {extra: state}) of what the hit's shot damaged. The kinds are the crits
    # mask's, a track and a wheel are the chassis; the extras are those of the damage info among these kinds (its
    # shell may be another one of the same moment), and a kind is at the worst state of both.
    kinds = {}
    for crit in hit.crits:
        state = _CRIT_STATES.get(crit.kind)
        if state is not None:
            kind = 'chassis' if crit.device in ('track', 'wheel') else crit.device
            kinds[kind] = _worst([kinds.get(kind, 'normal'), state])
    extras = {}
    for device in hit.damagedDevices:
        state = _INFO_STATES.get(device.code)
        kind = _extraKind(device.extra)
        if state is not None and kind in kinds:
            extras[device.extra] = _worst([extras.get(device.extra, 'normal'), state])
            kinds[kind] = _worst([kinds[kind], state])
    return kinds, extras


def _tankParts(descriptor, extras):
    # [(name, row, rowCount, state)] of the chassis on the tank. A wheel's row counts from the front: the highest
    # numbers are there, the even ones on the left (the battle damage panel's WheelRotator).
    if descriptor.type.isWheeledVehicle:
        rowCount = descriptor.chassis.generalWheelsAnimatorConfig.getNonTrackWheelsCount() // 2
        parts = []
        for row in range(rowCount):
            left = (rowCount - row - 1) * 2
            parts.append((_WHEEL_LEFT, row, rowCount, extras.get(_WHEEL_EXTRA % left, 'normal')))
            parts.append((_WHEEL_RIGHT, row, rowCount, extras.get(_WHEEL_EXTRA % (left + 1), 'normal')))
        return parts
    tracks = _FOUR_TRACKS if descriptor.isTrackWithinTrack else _TWO_TRACKS
    return [(name, 0, 1, extras.get(extra, 'normal')) for name, extra in tracks]


def _devices(descriptor, hit):
    # ([(icon, group, state)] of the cells, the parts of the tank): the vehicle's module kinds (the turret traverse
    # when the damage panel has it), then its crew members in the client's order, each with its icon at the state the
    # hit's shot left it in: a member by its extra, all those of a role when the damage info tells none of them;
    # nothing when the shot damaged nothing.
    kinds, extras = _damage(hit)
    if not kinds:
        return [], []
    vehicleType = descriptor.type
    tiles = []
    for group, names in enumerate(_MODULE_COLUMNS):
        for kind in names:
            if kind == 'turretRotator' and not hasTurretRotator(descriptor):
                continue
            state = kinds.get(kind, 'normal')
            icon = 'wheel' if kind == 'chassis' and vehicleType.isWheeledVehicle else kind
            tiles.append((icon + _ICON_SUFFIXES[state], group, state))
    told = set(_extraKind(extra) for extra in extras)
    members = getCrewMainRolesWithIndexes(vehicleType.crewRoles)
    for member in TANKMEN_ROLES_ORDER_DICT['enum']:
        if member in members:
            extra = member + _EXTRA_SUFFIX
            role = _extraKind(extra)
            state = extras.get(extra, 'normal') if role in told else kinds.get(role, 'normal')
            tiles.append((role + _ICON_SUFFIXES[state], _CREW_GROUP, state))
    return tiles, _tankParts(descriptor, extras)


def _hasTurret(descriptor):
    # Not a turretless vehicle: the armor page's test of its turret choice.
    try:
        return len(descriptor.hull.fakeTurrets['lobby']) != len(descriptor.turrets)
    except Exception:
        return True


def _materials(entity, start, end, shellParams):
    # ([material], penetration info) of the vehicle's armor along the segment, like the client's armor tooltip; None
    # when the collision model does not meet the segment (not loaded yet).
    from helpers.collisions import SegmentCollisionResultExt
    from shared_utils.vehicle_utils import getMatinfo
    from gui.impl.lobby.vehicle_hub.sub_presenters.armor.utils import getMaterialsAtCursor, stackMaterials
    from gui.impl.lobby.vehicle_hub.sub_presenters.armor.penetration_utils import calculatePenetrationInfo
    collisions = getattr(entity.appearance, 'collisions', None)
    if collisions is None:
        return None
    found = collisions.collideAllWorld(start, end)
    # What the line meets well before the hit point (another part in front of it: a gun, a track guard) is not what
    # the shell hit there.
    found = [item for item in found or () if item[0] >= _RAY * 0.5]
    if not found or found[0][0] - _RAY > _RAY * 0.5:
        return None
    isWheeled = entity.typeDescriptor.type.isWheeledVehicle
    segments = [SegmentCollisionResultExt(distance, angleCos, getMatinfo(entity, part, kind, isWheeled), part)
                for distance, angleCos, kind, part in found]
    # The layers as the client's armor tooltip shows them: the same part's layers stacked (a track twice, x2).
    materials = stackMaterials(getMaterialsAtCursor(entity, segments, shellParams), entity.typeDescriptor.level)
    return materials, calculatePenetrationInfo(shellParams, segments)


class ShotPanelPresenter(object):
    __hangarSpace = dependency.descriptor(IHangarSpace)

    def __init__(self, model, hitsPanel, overlayPanel, hitLines, texts):
        # texts: the section titles and line labels in the client language (config TEXTS 'shot/*').
        self._model = model
        self._hitsPanel = hitsPanel
        self._overlayPanel = overlayPanel
        self._hitLines = hitLines
        self._texts = texts
        # The fill of the next frame or the next try of the armor.
        self._callbackID = None
        self._tries = 0
        # {role: (vehicle item, [(tooltip alias, compact descriptor)] of its modules in order)}
        self._tooltips = {}

    def tooltipData(self, role, index):
        # The client's tooltip of a module of a card, None when there is none.
        vehicle, modules = self._tooltips.get(role, (None, []))
        if vehicle is None or not 0 <= index < len(modules):
            return None
        alias, compactDescr = modules[index]
        return createTooltipData(isSpecial=True, specialAlias=alias, specialArgs=(compactDescr, vehicle))

    def init(self):
        with self._model.transaction() as model:
            model.setTooltipContentId(R.views.common.tooltip_window.backport_tooltip_content.BackportTooltipContent())
            model.setTooltipDecoratorId(R.views.common.tooltip_window.tooltip_window.TooltipWindow())
        self._hitsPanel.onChanged += self._update
        self._hitLines.onDrawn += self._update
        self._update()

    def fini(self):
        self._cancel()
        self._hitLines.onDrawn -= self._update
        self._hitsPanel.onChanged -= self._update
        self._model = None
        self._hitsPanel = None
        self._overlayPanel = None
        self._hitLines = None
        self._tooltips = {}

    def _cancel(self):
        if self._callbackID is not None:
            BigWorld.cancelCallback(self._callbackID)
            self._callbackID = None

    def _update(self):
        # One change of the hits panel tells it up to three times (the lines cleared, drawn, the panel changed), and
        # the overlay panel sets the hit's shell after the hit lines: filled once, in the next frame, when all of
        # them are done.
        self._cancel()
        self._tries = 0
        self._callbackID = BigWorld.callback(0.0, self._onFrame)

    def _onFrame(self):
        # The fill of the frame after a change, or the next try of the armor.
        self._callbackID = None
        _, side, hit = self._hitsPanel.selection
        if hit is None:
            self._model.setIsVisible(False)
            return
        try:
            armor = self._armor(hit)
        except Exception:
            _logger.exception('shot panel: cannot count the armor')
            armor = None
        if armor is None and self._hitLines.chosenShot is not None and self._tries < _TRIES:
            self._tries += 1
            self._callbackID = BigWorld.callback(_RETRY, self._onFrame)
        gunShot = self._overlayPanel.gunShot
        shooterModules = self._shooterModules(hit.shooter, gunShot, hit.shellMode)
        targetModules = self._targetModules(hit.target)
        with self._model.transaction() as model:
            model.setIsVisible(True)
            self._fillVehicle(model.shooter, self._texts['shooter'], hit.shooter, shooterModules)
            self._fillVehicle(model.target, self._texts['target'], hit.target, targetModules)
            model.setShellText(clientText(_SHELL_TEXT_KEY % hit.shellType) or '' if hit.shellType else '')
            # The shell shown on the shooter's card, else the hit's premium flag.
            model.setIsGoldShell(bool(gunShot[1].shell.isGold) if gunShot is not None else bool(hit.isGoldShell))
            tiles, parts = self._deviceTiles(side, hit)
            devices = model.getDevices()
            devices.clear()
            for icon, group, state in tiles:
                device = ShotDeviceModel()
                device.setIcon(icon)
                device.setGroup(group)
                device.setState(state)
                devices.addViewModel(device)
            devices.invalidate()
            tankParts = model.getTankParts()
            tankParts.clear()
            for name, row, rowCount, state in parts:
                part = ShotTankPartModel()
                part.setName(name)
                part.setRow(row)
                part.setRowCount(rowCount)
                part.setState(state)
                tankParts.addViewModel(part)
            tankParts.invalidate()
            model.setDevicesNote(self._texts['critsNote'])
            sections = model.getSections()
            sections.clear()
            for section in self._sections(hit, gunShot, armor):
                sections.addViewModel(section)
            sections.invalidate()

    @staticmethod
    def _deviceTiles(side, hit):
        # The modules and crew cells and the tank's parts of a hit on the player's vehicle that damaged some; none on
        # another vehicle.
        if side == DEALT:
            return [], []
        descriptor = _descriptor(hit.target.vehicleId, hit.target.vehicleDescriptor)
        if descriptor is None:
            return [], []
        try:
            return _devices(descriptor, hit)
        except Exception:
            _logger.exception('shot panel: no modules of %s', descriptor.type.name)
            return [], []

    @staticmethod
    def _fillVehicle(model, role, vehicle, modules):
        vehicleId = vehicle.vehicleId
        icon, flag = _vehicleImages(vehicleId)
        try:
            tier = int2roman(vehicles.getVehicleType(vehicleId).level)
        except Exception:
            tier = ''
        model.setRole(role)
        model.setPlayer(vehicle.playerName)
        model.setVehicleName(vehicleShortName(vehicleId) or '')
        model.setTier(tier)
        model.setIcon(icon)
        model.setFlag(flag)
        array = model.getModules()
        array.clear()
        for moduleIcon, moduleTier, shellMode in modules:
            item = ShotModuleModel()
            item.setIcon(moduleIcon)
            item.setTier(moduleTier)
            item.setShellMode(shellMode)
            array.addViewModel(item)
        array.invalidate()

    def _shooterModules(self, shooter, gunShot, shellMode):
        # [(icon, tier, shell mode)] of the shooter's gun and the hit's shell (with the hit's mode); their tooltips for
        # the shown vehicle.
        self._tooltips[_SHOOTER] = (None, [])
        if gunShot is None:
            return []
        gun, shot = gunShot
        vehicle = _shownVehicle(shooter.vehicleId, shooter.vehicleDescriptor)
        if vehicle is not None:
            shownGun = _shownGun(vehicle.descriptor, gun)
            shots = [item for item in shownGun.shots if item.shell.name == copiedName(shot.shell.name)] or [
                item for item in shownGun.shots if item.shell.kind == shot.shell.kind]
            self._tooltips[_SHOOTER] = (vehicle, [
                (TOOLTIPS_CONSTANTS.CONTEXT_VEHICLE_MODULE, shownGun.compactDescr),
                (TOOLTIPS_CONSTANTS.ARMOR_INSPECTOR_SHELL, (shots[0] if shots else shot).shell.compactDescr)])
        return [(_GUN_ICON, int2roman(gun.level), ''), (_SHELL_ICON % shot.shell.iconName, '', shellMode)]

    def _targetModules(self, target):
        # [(icon, tier, '')] of the target's turret (when it has one) and gun, like the armor page's modules; their
        # tooltips for the shown vehicle.
        self._tooltips[_TARGET] = (None, [])
        vehicle = _shownVehicle(target.vehicleId, target.vehicleDescriptor)
        if vehicle is None:
            return []
        descriptor = vehicle.descriptor
        modules = [descriptor.turret] if _hasTurret(descriptor) else []
        modules.append(descriptor.gun)
        self._tooltips[_TARGET] = (vehicle, [(TOOLTIPS_CONSTANTS.CONTEXT_VEHICLE_MODULE, module.compactDescr)
                                             for module in modules])
        return [(_TURRET_ICON if module is descriptor.turret else _GUN_ICON, int2roman(module.level), '')
                for module in modules]

    def _armor(self, hit):
        # ([material], penetration info) where the chosen hit's line meets the hangar vehicle, None without it.
        chosenShot = self._hitLines.chosenShot
        if chosenShot is None or not self.__hangarSpace.isModelLoaded:
            return None
        entity = self.__hangarSpace.getVehicleEntity()
        if entity is None:
            return None
        position, direction = chosenShot
        return _materials(entity, position - direction * _RAY, position + direction * _RAY,
                          self._overlayPanel.shellParams)

    def _sections(self, hit, gunShot, armor):
        texts = self._texts
        shell = gunShot[1].shell if gunShot is not None else None
        isHighExplosive = hit.shellType == 'HIGH_EXPLOSIVE'
        sections = []
        rows = [(str(int(shell.armorDamage[0])), texts['avgDamage'], False)] if shell is not None else []
        if shell is not None and hit.damage > 0 and shell.armorDamage[0] > 0:
            # How far the damage is from the shell's average, in percent of it.
            deviation = int(round((hit.damage - shell.armorDamage[0]) * 100.0 / shell.armorDamage[0]))
            rows.append((u'-%d%%' % -deviation if deviation < 0 else u'+%d%%' % deviation if deviation else u'0%',
                         texts['deviation'], True))
        sections.append(self._section('damage', texts['damage'], str(hit.damage), False, rows))
        if gunShot is not None:
            piercing = gunShot[1].piercingPower
            average = str(int(round(piercing[0])))
            rows = []
            if armor is not None and armor[1] is not None:
                rows.append(('%s%%' % armor[1].chance, texts['chance'], True))
            if hit.distance and not isHighExplosive:
                atDistance = computePiercingPowerAtDist(piercing, hit.distance)
                value = str(int(round(atDistance)))
                rows.insert(0, (average, texts['avgPenetration'], False))
                # What the distance took off the shell's penetration (the shell's average less the value).
                loss = int(round(atDistance)) - int(round(piercing[0]))
                rows.insert(1, (u'-%d' % -loss if loss < 0 else u'%d' % loss,
                                texts['distanceLoss'] % {'distance': int(round(hit.distance))}, True))
                sections.append(self._section('penetration', texts['penetration'], value, True, rows))
            else:
                sections.append(self._section('penetration', texts['penetration'], average, False, rows))
        # The armor as the client's armor tooltip counts it: all the layers on the way, each by its reduction factor
        # (a modern high explosive shell's on spaced armor): the resulting armor; the nominal one with its layers in
        # brackets ('55 nominal (25 Chassis + 30 Hull)'), and the armor the angles add.
        layers = armor[0] if armor is not None else []
        shellParams = self._overlayPanel.shellParams
        reduction = lambda layer: (MODERN_HE_PIERCING_POWER_REDUCTION_FACTOR_FOR_SHIELDS if layer.isSpacedArmor and
                                   getattr(shellParams, 'useHEShell', False) else 1)
        nominal = sum(round(layer.nominalArmor) * reduction(layer) for layer in layers)
        effective = int(round(sum(layer.resArmor * reduction(layer) for layer in layers)))
        if len(layers) > 1:
            parts = u' + '.join(u'%d %s' % (int(round(layer.nominalArmor)), self._layerText(layer)) for layer in layers)
        elif layers:
            parts = self._layerText(layers[0])
        if layers:
            sections.append(self._section('armor', texts['armor'], str(effective), True, [
                (str(int(nominal)), u'%s (%s)' % (texts['nominal'], parts), True),
                (u'+%d' % int(effective - nominal), texts['angleArmor'], True)]))
        else:
            sections.append(self._section('armor', texts['armor'], _NONE, False, []))
        # The angle of the first layer, like the tooltip, for every shell (a high explosive one does not ricochet, but
        # the angle makes its armor thicker too); the ricochet angle only beside it.
        angle = u'%d°' % int(round(layers[0].viewAngle)) if layers else _NONE
        rows = []
        if layers and shell is not None and not isHighExplosive:
            from gui.shared.utils.functions import getShellImpactParams
            ricochetCos = getShellImpactParams(shell.type)[0]
            if ricochetCos > 0.0:
                rows.append((u'> %d°' % int(round(math.degrees(math.acos(ricochetCos)))), texts['ricochet'], False))
        sections.append(self._section('angle', texts['angle'], angle, bool(layers), rows))
        distance = str(int(round(hit.distance))) if hit.distance else _NONE
        sections.append(self._section('distance', texts['distance'], distance, False, []))
        # The modules and crew themselves are the page's cells and tank (model devices, tankParts).
        sections.append(self._section('crits', texts['crits'], str(hit.critsTotal), False, []))
        return sections

    @staticmethod
    def _layerText(layer):
        # The layer's part in the client's words, and how many layers of it: 'Chassis x2'.
        name = getattr(layer.partName, 'value', layer.partName)
        text = clientText(_PART_TEXT_KEY % name) or name
        count = getattr(layer, 'count', 1) or 1
        return u'%s x%d' % (text, count) if count > 1 else text

    @staticmethod
    def _section(kind, title, value, counted, rows):
        section = ShotSectionModel()
        section.setKind(kind)
        section.setTitle(title)
        section.setValue(value)
        section.setCounted(counted)
        array = section.getRows()
        for rowValue, label, rowCounted in rows:
            row = ShotRowModel()
            row.setValue(rowValue)
            row.setLabel(label)
            row.setCounted(rowCounted)
            array.addViewModel(row)
        array.invalidate()
        return section
