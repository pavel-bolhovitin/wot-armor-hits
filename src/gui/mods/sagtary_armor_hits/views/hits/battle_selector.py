# -*- coding: utf-8 -*-
"""Battle selector of the hits screen: the selected battle card and the list of the session's battles.

BattleSelectorPresenter fills the view model (views/models/battle_selector_model.py) from the BattleStore, keeps the
selected battle and tells its listeners when the selection changes (onBattleSelected). A new field of a battle is a
property of BattleItemModel and a line in _fillItem.

The card and the items show the map, the result when it is known, the vehicle and the time; the list is grouped by
the date. All these texts are the client's, in the client language: the map and the vehicle by their ids
(data/client_names.py), the result from the client's strings, the date and the time in the client format. The battle
id goes to the page as a string, as it does not fit a JavaScript number.
"""
import logging

from Event import Event
from gui.impl import backport
from helpers import i18n

from gui.mods.sagtary_armor_hits.data.battles import BattleResult
from gui.mods.sagtary_armor_hits.data.client_names import mapNames, vehicleShortName
from gui.mods.sagtary_armor_hits.views.models.battle_selector_model import BattleItemModel

_logger = logging.getLogger('sagtary.armor_hits')

# Map preview, 100 x 60, by the map folder name.
_MAP_IMAGE = 'img://gui/maps/icons/map/small/%s.png'


# The client's texts of the results, by their translation keys (the event boards summary: "Victory", "Defeat",
# "Draw", without "!"); R.strings does not declare these strings, so they are read with i18n.makeString.
_RESULT_KEYS = {
    BattleResult.WIN: '#event_boards:summary/result/win',
    BattleResult.DEFEAT: '#event_boards:summary/result/loss',
    BattleResult.DRAW: '#event_boards:summary/result/draw',
}


def _resultText(result):
    key = _RESULT_KEYS.get(result)
    if key is None:
        return ''
    text = i18n.makeString(key)
    if not text or text == key:
        _logger.warning('battle selector: no client text %s', key)
        return ''
    return text


def _fillItem(item, battle):
    # Names by the ids, in the client language; the ids themselves when the client does not have them.
    mapName, mapFolder = mapNames(battle.mapId) or ('#%s' % battle.mapId, '')
    item.setId(str(battle.battleId))
    item.setMapName(mapName)
    item.setMapImage(_MAP_IMAGE % mapFolder if mapFolder else '')
    item.setVehicleName(vehicleShortName(battle.vehicleId) or '#%s' % battle.vehicleId)
    item.setDay(backport.getShortDateFormat(battle.startedAt))
    item.setTime(backport.getShortTimeFormat(battle.startedAt))
    item.setResult(battle.result)
    item.setResultText(_resultText(battle.result))


class BattleSelectorPresenter(object):

    def __init__(self, model, store, texts):
        # texts: {'empty'} in the client language.
        self._model = model
        self._store = store
        self._texts = texts
        self._selectedID = None
        self.onBattleSelected = Event()

    @property
    def selectedBattle(self):
        return self._store.getBattle(self._selectedID) if self._selectedID is not None else None

    def init(self):
        self._model.setEmptyTitle(self._texts['empty'])
        self._model.onSelect += self._onSelect
        self._store.onChanged += self._onStoreChanged
        self._update()

    def fini(self):
        self._store.onChanged -= self._onStoreChanged
        self._model.onSelect -= self._onSelect
        self.onBattleSelected.clear()
        self._model = None
        self._store = None

    def select(self, battleId):
        if self._store.getBattle(battleId) is None or battleId == self._selectedID:
            return
        # The page draws the selector again when its battles change, not when only selectedId does: the list is
        # filled again with the new selection.
        self._update(battleId)

    def _onStoreChanged(self):
        self._update()

    def _update(self, selectedID=None):
        battles = self._store.getBattles()
        previous = self._selectedID
        if selectedID is not None:
            self._selectedID = selectedID
        elif self._store.getBattle(previous) is None:
            # Nothing selected yet, or the selected battle is gone: the newest one.
            self._selectedID = battles[0].battleId if battles else None
        with self._model.transaction() as model:
            items = model.getBattles()
            items.clear()
            for battle in battles:
                item = BattleItemModel()
                _fillItem(item, battle)
                items.addViewModel(item)
            items.invalidate()
            model.setSelectedId(str(self._selectedID) if self._selectedID is not None else '')
        if self._selectedID != previous:
            self.onBattleSelected(self.selectedBattle)

    def _onSelect(self, args=None):
        battleId = (args or {}).get('id')
        for battle in self._store.getBattles():
            if str(battle.battleId) == battleId:
                self.select(battle.battleId)
                return
        _logger.warning('battle selector: unknown battle %r', battleId)
