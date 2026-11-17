# -*- coding: utf-8 -*-
"""Minimap of the hits screen: the map of the selected battle, at the bottom of the hits panel, and where the vehicles
were at the chosen hit.

MinimapPresenter fills the view model (views/models/minimap_model.py) for the battle and the hit the hits panel shows.
The image is the client's map seen from above, gui/maps/icons/map/<map>.png (300 x 300), the one its maps training page
shows, or the gameplay's own one in a folder of its name, which the client's lobby minimap takes first: the client has
it for the maps of the random battles, not for some maps of the events and of other modes; without it the minimap is
hidden. Its header's title is the client's: the title of the minimap settings.

The vehicles are those of the hit's snapshot (data/snapshots.py), each placed on the image by the map's bounding box,
the part of the world the image shows, as the client's lobby minimap places its points (MinimapLobby): x to the right,
z up. Each is the player's, an ally's or an enemy's, by its player and team in the battle's vehicle catalog. A battle
without snapshots (an older file) and a hit without one show none.

They look as on the battle's minimap: the icons of the client's battle atlas (gui/flash/atlases/battleAtlas: the
texture and the place of each icon in it, read once), which the page cuts out of the texture. The player's vehicle is
the battle's own arrow (VIEW_POINT's PersonalArrowEntry), turned to its hull's heading; the others are the icons of
their class and side (VehicleMinimapEntry: <class>_ally_green, <class>_enemy_red). A vehicle of an unknown class (the
fog of war) has no icon: the client draws none either; the page shows a plain mark then, as it does for all without
the atlas. They are drawn by their class, each over those before: heavy tanks first, then medium tanks, SPGs, tank
destroyers, light tanks, the player's vehicle last, on top; those of an unknown class under all. Under all the icons,
drawn before them, the heading of each turret the client saw: the mod's own corner
(gui/maps/sagtary_armor_hits/minimap/turret_<kind>.png), its apex on the vehicle, turned to the turret's heading.
"""
import logging

import ResMgr

from gui.mods.sagtary_armor_hits.data.client_names import clientText, mapArena, mapNames, vehicleClass
from gui.mods.sagtary_armor_hits.views.models.minimap_model import MinimapVehicleModel

_logger = logging.getLogger('sagtary.armor_hits')

# The map seen from above by the map folder name, and the gameplay's own one by the gameplay name too.
_MAP_PATH = 'gui/maps/icons/map/%s.png'
_GAMEPLAY_MAP_PATH = 'gui/maps/icons/map/%s/%s.png'
# "Minimap": the header of the minimap settings in the game settings.
_TITLE_KEY = '#settings:game/fieldset/headerMinimap'
# The client's battle atlas: its texture and the place of each icon in it.
_ATLAS_TEXTURE = 'gui/flash/atlases/battleAtlas.dds'
_ATLAS_ITEMS = 'gui/flash/atlases/battleAtlas.xml'
# The player's arrow in the atlas, and where its point of the map is in it: the middle of the arrow, low in its
# item (measured in the client 2.4.1.1). The other icons' point is their middle.
_PLAYER_ICON = 'PersonalArrowEntry'
_PLAYER_ICON_ANCHOR = (94.5, 201.5)
# A vehicle's icon by its class tag and its side.
_VEHICLE_ICON = '%s_%s'
_ALLY_ICON = 'ally_green'
_ENEMY_ICON = 'enemy_red'
# The order the vehicles are drawn in, by their class tag, each over those before: a vehicle of an unknown class
# first, the player's last, on top of all.
_DRAW_ORDER = ('heavyTank', 'mediumTank', 'SPG', 'AT-SPG', 'lightTank')


class VehicleKind(object):
    # Whose a vehicle on the minimap is to the player (MinimapVehicleModel.kind).
    PLAYER = 'player'
    ALLY = 'ally'
    ENEMY = 'enemy'


# {icon name: (x, y, width, height)} of the atlas, read on the first use; empty without it.
_atlasItems = None


def _atlas():
    global _atlasItems
    if _atlasItems is None:
        _atlasItems = {}
        try:
            section = ResMgr.openSection(_ATLAS_ITEMS)
            for item in (section.values() if section is not None else ()):
                _atlasItems[item.readString('name').strip()] = (
                    item.readInt('x'), item.readInt('y'), item.readInt('width'), item.readInt('height'))
            ResMgr.purge(_ATLAS_ITEMS, True)
        except Exception:
            _logger.exception('minimap: cannot read the battle atlas')
    return _atlasItems


def _mapImage(battle, gameplayName):
    # The image of the battle's map for the page, or '' when the client has none.
    names = mapNames(battle.mapId) if battle is not None else None
    if names is None:
        return ''
    paths = ([_GAMEPLAY_MAP_PATH % (gameplayName, names[1])] if gameplayName else []) + [_MAP_PATH % names[1]]
    for path in paths:
        if ResMgr.isFile(path):
            return 'img://' + path
    return ''


def _snapshot(battle, hit):
    # The hit's snapshot, None without one.
    index = hit.snapshotIndex if hit is not None else None
    if index is None or not 0 <= index < len(battle.snapshots):
        return None
    return battle.snapshots[index]


def _icon(kind, classTag):
    # The name of the vehicle's icon in the atlas; '' for a vehicle of an unknown class.
    if kind == VehicleKind.PLAYER:
        return _PLAYER_ICON
    if not classTag:
        return ''
    return _VEHICLE_ICON % (classTag, _ALLY_ICON if kind == VehicleKind.ALLY else _ENEMY_ICON)


def _layer(kind, classTag):
    # Where the vehicle is in the drawing order (_DRAW_ORDER): drawn after those of a lower layer, over them.
    if kind == VehicleKind.PLAYER:
        return len(_DRAW_ORDER) + 1
    return _DRAW_ORDER.index(classTag) + 1 if classTag in _DRAW_ORDER else 0


def _vehicles(battle, hit, bounds):
    # [(x, y, kind, icon, rotation, turret)] of the vehicles of the hit's snapshot, in the order they are drawn
    # (_DRAW_ORDER): on the map's image, x and y 0 to 1 from its top left; the name of the icon in the atlas; radians it
    # is turned (the player's arrow, by the hull); the turret's heading in radians, None when not known.
    snapshot = _snapshot(battle, hit) if bounds is not None else None
    if snapshot is None:
        return []
    (minX, minZ), (maxX, maxZ) = bounds
    if maxX <= minX or maxZ <= minZ:
        return []
    player = battle.playerVehicle
    vehicles = []
    for vehicle in snapshot.vehicles:
        if len(vehicle.position) != 3:
            continue
        x, _, z = vehicle.position
        known = battle.vehicle(vehicle.vehicleIndex)
        if known.battlePlayerId and known.battlePlayerId == player.battlePlayerId:
            kind = VehicleKind.PLAYER
        elif known.team is not None and known.team == player.team:
            kind = VehicleKind.ALLY
        else:
            kind = VehicleKind.ENEMY
        rotation = vehicle.hullYaw if kind == VehicleKind.PLAYER and vehicle.hullYaw is not None else 0.0
        classTag = vehicleClass(known.vehicleId)
        vehicles.append((_layer(kind, classTag), ((x - minX) / (maxX - minX), (maxZ - z) / (maxZ - minZ), kind,
                                                  _icon(kind, classTag), rotation, vehicle.turretYaw)))
    vehicles.sort(key=lambda layered: layered[0])
    return [vehicle for _, vehicle in vehicles]


class MinimapPresenter(object):

    def __init__(self, model, hitsPanel):
        self._model = model
        self._hitsPanel = hitsPanel

    def init(self):
        with self._model.transaction() as model:
            model.setTitle(clientText(_TITLE_KEY) or '')
            model.setAtlas('img://' + _ATLAS_TEXTURE if _atlas() else '')
        self._hitsPanel.onChanged += self._update
        self._update()

    def fini(self):
        self._hitsPanel.onChanged -= self._update
        self._hitsPanel = None
        self._model = None

    def _update(self):
        battle, _, hit = self._hitsPanel.selection
        arena = mapArena(battle.arenaTypeId) if battle is not None else None
        gameplayName, bounds = arena or ('', None)
        # A file can come from another player: a snapshot the client cannot show leaves the map without vehicles.
        try:
            vehicles = _vehicles(battle, hit, bounds)
        except Exception:
            _logger.exception('minimap: cannot show the snapshot of the hit')
            vehicles = []
        atlas = _atlas()
        with self._model.transaction() as model:
            model.setImage(_mapImage(battle, gameplayName))
            models = model.getVehicles()
            models.clear()
            for x, y, kind, icon, rotation, turret in vehicles:
                item = MinimapVehicleModel()
                item.setX(x)
                item.setY(y)
                item.setKind(kind)
                item.setHasTurret(turret is not None)
                item.setTurret(turret if turret is not None else 0.0)
                if icon in atlas:
                    iconX, iconY, width, height = atlas[icon]
                    anchorX, anchorY = _PLAYER_ICON_ANCHOR if icon == _PLAYER_ICON else (width / 2.0, height / 2.0)
                    item.setIconX(iconX)
                    item.setIconY(iconY)
                    item.setIconWidth(width)
                    item.setIconHeight(height)
                    item.setAnchorX(anchorX)
                    item.setAnchorY(anchorY)
                    item.setRotation(rotation)
                models.addViewModel(item)
            models.invalidate()
