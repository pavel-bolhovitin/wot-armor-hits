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
"""
import logging

import ResMgr

from gui.mods.sagtary_armor_hits.data.client_names import clientText, mapArena, mapNames
from gui.mods.sagtary_armor_hits.views.models.minimap_model import MinimapVehicleModel

_logger = logging.getLogger('sagtary.armor_hits')

# The map seen from above by the map folder name, and the gameplay's own one by the gameplay name too.
_MAP_PATH = 'gui/maps/icons/map/%s.png'
_GAMEPLAY_MAP_PATH = 'gui/maps/icons/map/%s/%s.png'
# "Minimap": the header of the minimap settings in the game settings.
_TITLE_KEY = '#settings:game/fieldset/headerMinimap'


class VehicleKind(object):
    # Whose a vehicle on the minimap is to the player (MinimapVehicleModel.kind).
    PLAYER = 'player'
    ALLY = 'ally'
    ENEMY = 'enemy'


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


def _vehicles(battle, hit, bounds):
    # [(x, y, kind)] of the vehicles of the hit's snapshot on the map's image, x and y 0 to 1 from its top left.
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
        vehicles.append(((x - minX) / (maxX - minX), (maxZ - z) / (maxZ - minZ), kind))
    return vehicles


class MinimapPresenter(object):

    def __init__(self, model, hitsPanel):
        self._model = model
        self._hitsPanel = hitsPanel

    def init(self):
        self._model.setTitle(clientText(_TITLE_KEY) or '')
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
        with self._model.transaction() as model:
            model.setImage(_mapImage(battle, gameplayName))
            models = model.getVehicles()
            models.clear()
            for x, y, kind in vehicles:
                item = MinimapVehicleModel()
                item.setX(x)
                item.setY(y)
                item.setKind(kind)
                models.addViewModel(item)
            models.invalidate()
