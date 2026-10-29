# -*- coding: utf-8 -*-
"""Shot panel of the hits screen, on the right: the chosen hit's shooter and target, its result and its numbers.

ShotPanelPresenter fills the view model (views/models/shot_panel_model.py) for the hit the hits panel has chosen:

- the cards of the shooter and the target: the player, the vehicle (the client's name, tier, icon and nation flag)
  with its modules of the battle (the compact descriptor); beside the shooter its gun and the shell of the hit,
  beside the target its turret when it has one (not a turretless vehicle) and its gun, as icons like the armor page's. On the
  received side the shooter is the other vehicle and the target the player's, on the dealt side the other way round.
  Over an icon the client's tooltip of the module (CONTEXT_VEHICLE_MODULE) or of the shell (ARMOR_INSPECTOR_SHELL)
  shows, for the vehicle as the hangar shows it (a maps training copy as the vehicle it copies): tooltipData;
- the sections, each with its icon (the client's damage log icons for damage and modules, the mod's for the others):
  damage (the hit's, the shell's average), penetration (the shell's, at the hit's distance when it is
  known), armor and impact angle (the vehicle's armor where the hit line meets it, counted in the garage like the
  client's armor tooltip does: getMaterialsAtCursor along the line, the shell's penetration chance there,
  calculatePenetrationInfo), distance (recorded in battle) and modules and crew. On a hit on the player's vehicle
  that damaged some, modules and crew are the battle damage panel's icons (gui/maps/sagtary_armor_hits/modules/) of
  what this shot damaged (not what was damaged before it), in the grid's order: a tile per module kind, its icon at
  the worst state of its damaged parts (a track of two, a wheel of eight), then a tile per crew role; under a tile's
  icon the client's name of each damaged part or crew member (two loaders under one icon), in its state's color; a
  fire it started is a line of the section. The client tells nothing of the kind on a hit of another vehicle: there
  the section has its count only.

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
                                                                       ShotSectionModel)

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
# The modules section's tiles: the battle damage panel's module kinds, in its order; the chassis is a track's or, on
# a wheeled vehicle, a wheel's.
_MODULE_KINDS = ('engine', 'ammoBay', 'fuelTank', 'chassis', 'gun', 'turretRotator', 'surveyingDevice', 'radio')
# The state a shot leaves a part in, by its damage info code (data/hits.py DamagedDevice); the states, the worst last;
# the panel icon's suffix of a state (a crew member has only the orange one).
_CODE_STATES = {
    'DEVICE_CRITICAL_AT_SHOT': 'critical',
    'DEVICE_DESTROYED_AT_SHOT': 'destroyed',
    'TANKMAN_HIT_AT_SHOT': 'destroyed',
    'DEATH_FROM_DEVICE_EXPLOSION_AT_SHOT': 'destroyed',
}
_STATES = ('normal', 'critical', 'destroyed')
_ICON_SUFFIXES = {'normal': '', 'critical': '_orange', 'destroyed': '_red'}
_FIRE_CODE = 'DEVICE_STARTED_FIRE_AT_SHOT'
# The client's texts: a module's name (by its devices key), a part's name, a crew member's name (the damage panel's,
# 'Loader 2'), a role's name, a fire started.
_DEVICE_NAME_KEY = '#ingame_gui:devices/%s'
_DEVICE_KEYS = {'engine': 'engine', 'ammoBay': 'ammo_bay', 'fuelTank': 'fuel_tank', 'radio': 'radio', 'gun': 'gun',
                'turretRotator': 'turret_rotator', 'surveyingDevice': 'surveing_device', 'track': 'chassis',
                'wheel': 'wheel'}
_PART_NAME_KEYS = {'leftTrack': '#ingame_gui:devices/left_track', 'rightTrack': '#ingame_gui:devices/right_track',
                   'wheel': '#ingame_gui:devices/wheel'}
_CREW_STATE_KEY = '#ingame_gui:damage_panel/crew/%s/%s'
_CREW_NAME_KEY = '#ingame_gui:tankmen/%s'
_FIRE_KEY = '#ingame_gui:efficiencyRibbons/burn'
_HEALTH_SUFFIX = 'Health'
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


def _part(extraName):
    # (kind, name, number) of a device's extra: 'leftTrack0Health' -> ('track', 'leftTrack', 0).
    name = extraName[:-len(_HEALTH_SUFFIX)] if extraName.endswith(_HEALTH_SUFFIX) else extraName
    base = name.rstrip('0123456789')
    return ('track' if base in ('leftTrack', 'rightTrack') else base), base, int(name[len(base):] or 0)


def _worst(states):
    return max(states or ['normal'], key=_STATES.index)


def _sentence(text):
    # The first letter capital, the rest small: the client's names come in either case ('engine', 'Fuel Tank').
    return text[:1].upper() + text[1:].lower()


def _devices(descriptor, hit):
    # [(icon, is crew, text)] of the module parts and crew members the hit's shot damaged, in the battle damage panel's
    # order: a part's icon at its state and its client name; a crew member's role icon and its roles, '\n' between.
    states = {}
    for device in hit.damagedDevices:
        state = _CODE_STATES.get(device.code)
        if state is not None and device.extra:
            states[device.extra] = _worst([states.get(device.extra, 'normal'), state])
    vehicleType = descriptor.type
    parts = {}
    for extra in vehicleType.devices:
        parts.setdefault(_part(extra.name)[0], []).append(extra.name)
    tiles = []
    for kind in _MODULE_KINDS:
        if kind == 'chassis':
            kind = 'wheel' if vehicleType.isWheeledVehicle else 'track'
        names = sorted(parts.get(kind, ()), key=lambda name: _part(name)[1:])
        damaged = [(name, states[name]) for name in names if states.get(name, 'normal') != 'normal']
        if not damaged:
            continue
        for name, state in damaged:
            _, base, number = _part(name)
            label = clientText(_PART_NAME_KEYS.get(base) or _DEVICE_NAME_KEY % _DEVICE_KEYS.get(base, base)) or base
            if base == 'wheel':
                label = u'%s %d' % (label, number + 1)
            icon = ('chassis' if kind == 'track' else kind) + _ICON_SUFFIXES[state]
            tiles.append((icon, False, _sentence(label)))
    # The crew in the vehicle's order, a member a tile.
    for memberRoles, extra in zip(vehicleType.crewRoles, vehicleType.tankmen):
        if states.get(extra.name, 'normal') == 'normal':
            continue
        name = extra.name[:-len(_HEALTH_SUFFIX)]
        label = clientText(_CREW_STATE_KEY % (name, 'normal')) or clientText(_CREW_NAME_KEY % memberRoles[0]) or name
        # A member in several roles (a commander who is the radio operator too): all of them.
        others = [clientText(_CREW_NAME_KEY % role) for role in memberRoles[1:]]
        roles = [_sentence(text) for text in [label] + others if text]
        tiles.append((memberRoles[0] + '_orange', True, u'\n'.join(roles)))
    return tiles


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
        battle, side, hit = self._hitsPanel.selection
        if battle is None or hit is None:
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
        # The name of the player who played the battle, not of the one who watches it.
        myName = battle.playerName
        if side == DEALT:
            shooter = (battle.vehicleId, battle.vehicleDescriptor, myName)
            target = (hit.vehicleId, hit.vehicleDescriptor, hit.playerName)
        else:
            shooter = (hit.vehicleId, hit.vehicleDescriptor, hit.playerName)
            target = (battle.vehicleId, battle.vehicleDescriptor, myName)
        shooterModules = self._shooterModules(shooter, gunShot)
        targetModules = self._targetModules(target)
        with self._model.transaction() as model:
            model.setIsVisible(True)
            self._fillVehicle(model.shooter, self._texts['shooter'], shooter, shooterModules)
            self._fillVehicle(model.target, self._texts['target'], target, targetModules)
            model.setShellText(clientText(_SHELL_TEXT_KEY % hit.shellType) or '' if hit.shellType else '')
            # The shell shown on the shooter's card, else the hit's premium flag.
            model.setIsGoldShell(bool(gunShot[1].shell.isGold) if gunShot is not None else bool(hit.isGoldShell))
            devices = model.getDevices()
            devices.clear()
            for icon, isCrew, text in self._deviceTiles(battle, side, hit):
                device = ShotDeviceModel()
                device.setIcon(icon)
                device.setIsCrew(isCrew)
                device.setText(text)
                devices.addViewModel(device)
            devices.invalidate()
            sections = model.getSections()
            sections.clear()
            for section in self._sections(hit, gunShot, armor):
                sections.addViewModel(section)
            sections.invalidate()

    @staticmethod
    def _deviceTiles(battle, side, hit):
        # The modules and crew tiles of a hit on the player's vehicle that damaged some; none on another vehicle.
        if side == DEALT or not any(device.extra and device.code in _CODE_STATES for device in hit.damagedDevices):
            return []
        descriptor = _descriptor(battle.vehicleId, battle.vehicleDescriptor)
        if descriptor is None:
            return []
        try:
            tiles = _devices(descriptor, hit)
        except Exception:
            _logger.exception('shot panel: no modules of %s', descriptor.type.name)
            return []
        return tiles

    @staticmethod
    def _fillVehicle(model, role, vehicle, modules):
        vehicleId, _, player = vehicle
        icon, flag = _vehicleImages(vehicleId)
        try:
            tier = int2roman(vehicles.getVehicleType(vehicleId).level)
        except Exception:
            tier = ''
        model.setRole(role)
        model.setPlayer(player or '')
        model.setVehicleName(vehicleShortName(vehicleId) or '')
        model.setTier(tier)
        model.setIcon(icon)
        model.setFlag(flag)
        array = model.getModules()
        array.clear()
        for moduleIcon, moduleTier in modules:
            item = ShotModuleModel()
            item.setIcon(moduleIcon)
            item.setTier(moduleTier)
            array.addViewModel(item)
        array.invalidate()

    def _shooterModules(self, shooter, gunShot):
        # [(icon, tier)] of the shooter's gun and the hit's shell; their tooltips for the shown vehicle.
        self._tooltips[_SHOOTER] = (None, [])
        if gunShot is None:
            return []
        gun, shot = gunShot
        vehicle = _shownVehicle(*shooter[:2])
        if vehicle is not None:
            shownGun = _shownGun(vehicle.descriptor, gun)
            shots = [item for item in shownGun.shots if item.shell.name == copiedName(shot.shell.name)] or [
                item for item in shownGun.shots if item.shell.kind == shot.shell.kind]
            self._tooltips[_SHOOTER] = (vehicle, [
                (TOOLTIPS_CONSTANTS.CONTEXT_VEHICLE_MODULE, shownGun.compactDescr),
                (TOOLTIPS_CONSTANTS.ARMOR_INSPECTOR_SHELL, (shots[0] if shots else shot).shell.compactDescr)])
        return [(_GUN_ICON, int2roman(gun.level)), (_SHELL_ICON % shot.shell.iconName, '')]

    def _targetModules(self, target):
        # [(icon, tier)] of the target's turret (when it has one) and gun, like the armor page's modules; their
        # tooltips for the shown vehicle.
        self._tooltips[_TARGET] = (None, [])
        vehicle = _shownVehicle(*target[:2])
        if vehicle is None:
            return []
        descriptor = vehicle.descriptor
        modules = [descriptor.turret] if _hasTurret(descriptor) else []
        modules.append(descriptor.gun)
        self._tooltips[_TARGET] = (vehicle, [(TOOLTIPS_CONSTANTS.CONTEXT_VEHICLE_MODULE, module.compactDescr)
                                             for module in modules])
        return [(_TURRET_ICON if module is descriptor.turret else _GUN_ICON, int2roman(module.level))
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
        # The modules and crew themselves are the page's tiles (model devices); a fire the shot started is a line.
        rows = [('', clientText(_FIRE_KEY), False)] if any(device.code == _FIRE_CODE
                                                          for device in hit.damagedDevices) else []
        sections.append(self._section('crits', texts['crits'], str(hit.critsCount), False, rows))
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
