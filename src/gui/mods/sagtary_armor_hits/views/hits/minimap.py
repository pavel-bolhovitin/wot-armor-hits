# -*- coding: utf-8 -*-
"""Minimap of the hits screen: the map of the selected battle, at the bottom of the hits panel.

MinimapPresenter fills the view model (views/models/minimap_model.py) for the battle the battle selector shows. The
image is the client's map seen from above, gui/maps/icons/map/<map>.png (300 x 300), the one its maps training page
shows: the client has it for the maps of the random battles, not for some maps of the events and of other modes;
without it the minimap is hidden. Its header's title is the client's: the title of the minimap settings.
"""
import ResMgr

from gui.mods.sagtary_armor_hits.data.client_names import clientText, mapNames

# The map seen from above by the map folder name.
_MAP_PATH = 'gui/maps/icons/map/%s.png'
# "Minimap": the header of the minimap settings in the game settings.
_TITLE_KEY = '#settings:game/fieldset/headerMinimap'


def _mapImage(battle):
    # The image of the battle's map for the page, or '' when the client has none.
    names = mapNames(battle.mapId) if battle is not None else None
    if names is None:
        return ''
    path = _MAP_PATH % names[1]
    return 'img://' + path if ResMgr.isFile(path) else ''


class MinimapPresenter(object):

    def __init__(self, model, battleSelector):
        self._model = model
        self._battleSelector = battleSelector

    def init(self):
        self._model.setTitle(clientText(_TITLE_KEY) or '')
        self._battleSelector.onBattleSelected += self._onBattleSelected
        self._onBattleSelected(self._battleSelector.selectedBattle)

    def fini(self):
        self._battleSelector.onBattleSelected -= self._onBattleSelected
        self._battleSelector = None
        self._model = None

    def _onBattleSelected(self, battle):
        self._model.setImage(_mapImage(battle))
