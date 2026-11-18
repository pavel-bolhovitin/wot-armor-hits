# -*- coding: utf-8 -*-
"""Hits panel of the hits screen: the hits of the selected battle, on the player's vehicle and by the player.

HitsPanelPresenter fills the view model (views/models/hits_panel_model.py) for the battle the battle selector shows:
both sides' hits in one list in the battle's order (by their time), those that pass the filter; it keeps the chosen
hit and tells its listeners when the panel changes (onChanged; the battle, the chosen hit's side and the hit in
selection). The filter chooses the sides (received, dealt) and the results: in each, all of them or some, each with how
many hits it has under the other one's choice. A click on 'All' chooses all of them; on a line while all are chosen,
only that one; else it turns that one over, and when none or all are left all of them are chosen. The filter is kept
for the session: the screen opened again and another battle show the same. The hits on allies (Battle.isAllyHit) are
left out unless the mod's settings show them (showFriendlyFire; the panel follows the setting at once). The icons are
the client's damage log icons; the shell kinds, the vehicle names, the results' names and the "All" label are the
client's texts; an SPG's shell has its plate inverted, like in the client's damage log (isSpgShell). A hit with a known
shell mode (Hit.shellMode, the shell params switcher of a few vehicles) gets the mod's icon of the mode in a column of
its own, which the list has only for a battle with such a hit (hasShellModes). A row without an icon is a hit of an
unknown mode.
"""
import logging

from Event import Event

from gui.mods.sagtary_armor_hits.data.client_names import clientText, vehicleClass, vehicleShortName
from gui.mods.sagtary_armor_hits.data.hits import HitResult
from gui.mods.sagtary_armor_hits.views.models.hits_panel_model import HitFilterModel, HitItemModel

_logger = logging.getLogger('sagtary.armor_hits')

RECEIVED = 'received'
DEALT = 'dealt'
_SIDES = (RECEIVED, DEALT)
_HITS_FIELD = {RECEIVED: 'receivedHits', DEALT: 'dealtHits'}

# The class icons of the client's damage log by the vehicle class tag.
_CLASS_ICONS = {'lightTank': 'light', 'mediumTank': 'middle', 'heavyTank': 'heavy', 'AT-SPG': 'destroyer',
                'SPG': 'art'}
_ALL_KEY = '#menu:carousel_tank_filter/all'
_SHELL_TEXT_KEY = '#ingame_gui:damageLog/shellType/%s'
_SHELL_NAME_KEY = '#item_types:shell/kinds/%s'
# The client's names of the results: the battle results' damage, the hit markers' blocked and ricochet, the armor
# page's no damage.
_RESULT_KEYS = {
    HitResult.DAMAGE: '#battle_results:common/tooltip/damage/header',
    HitResult.BLOCKED: '#ingame_gui:hitMarker/blocked',
    HitResult.RICOCHET: '#ingame_gui:hitMarker/ricochet',
    HitResult.NO_DAMAGE: '#armor_inspector:armorValues/title/no_damage',
}

# The filter of the session, while the client runs: the chosen sides and results.
_sessionFilter = {'sides': _SIDES, 'results': HitResult.ALL}


def _time(seconds):
    seconds = int(seconds)
    return '%d:%02d' % (seconds // 60, seconds % 60)


def isSpgShell(battle, hit):
    # The hit's shell is an SPG's: the shell plate is inverted then, like the client's damage log shows it.
    return vehicleClass(battle.vehicle(hit.shooterVehicleIndex).vehicleId) == 'SPG'


def _pressed(chosen, item, items):
    # The chosen items after a click on item's line ('' for 'All'): all of them on 'All'; only the item while all are
    # chosen; else the item turned over, all of them again when none or all are left.
    if not item:
        return items
    if len(chosen) == len(items):
        return (item,)
    left = set(chosen) ^ {item}
    if not left or len(left) == len(items):
        return items
    return tuple(each for each in items if each in left)


def _count(hits, sides, results):
    # How many of the [(side, index, hit)] are of the sides and the results.
    return len([hit for side, _, hit in hits if side in sides and hit.result in results])


def _fillHit(item, battle, side, hit):
    item.setSide(side)
    item.setTime(_time(hit.time))
    item.setResult(hit.result)
    other = battle.vehicle(hit.otherVehicleIndex)
    item.setVehicleName(vehicleShortName(other.vehicleId) or '#%s' % other.vehicleId)
    item.setVehicleClass(_CLASS_ICONS.get(vehicleClass(other.vehicleId), ''))
    item.setPlayerName(other.playerName)
    if hit.shellType:
        item.setShellText(clientText(_SHELL_TEXT_KEY % hit.shellType) or '')
        item.setShellName(clientText(_SHELL_NAME_KEY % hit.shellType) or '')
    item.setDamage(hit.damage)
    item.setHasCrits(hit.critsTotal > 0)
    item.setIsGoldShell(hit.isGoldShell)
    item.setIsSpgShell(isSpgShell(battle, hit))
    item.setShellMode(hit.shellMode)


def _fillFilters(filters, items, chosen, labels, counts):
    # The menu's lines of a group: 'All' first, then its items; 'All' alone on while all of them are chosen.
    filters.clear()
    isAll = len(chosen) == len(items)
    for item in ('',) + items:
        model = HitFilterModel()
        model.setId(item)
        model.setLabel(labels.get(item) or '')
        model.setCount(counts[item])
        model.setIsOn(isAll if not item else not isAll and item in chosen)
        filters.addViewModel(model)
    filters.invalidate()


class HitsPanelPresenter(object):

    def __init__(self, model, store, battleSelector, texts, modSettings=None):
        # texts: {'received', 'dealt': the sides' names, 'allHits': what the filter says when it shows all hits} in
        # the client language. modSettings: settings.ModSettings, None for the default settings.
        self._model = model
        self._store = store
        self._settings = modSettings
        self._battleSelector = battleSelector
        self._texts = texts
        self._battleId = None
        self._sides = _sessionFilter['sides']
        self._results = _sessionFilter['results']
        # (side, index among the battle's hits of its side) of the chosen hit, None for the first shown one: it stays
        # chosen when the filter changes while it passes it.
        self._chosen = None
        self.onChanged = Event()

    @property
    def shownHits(self):
        # [(side, hit)] the panel lists: the hits that pass the filter, in the battle's order.
        return [(side, hit) for side, _, hit in self._shownHits()]

    @property
    def selectedIndex(self):
        # Index of the chosen hit in shownHits, None without one.
        keys = [(side, index) for side, index, _ in self._shownHits()]
        return keys.index(self._chosen) if self._chosen in keys else None

    @property
    def selection(self):
        # (battle, side, chosen hit): the battle is None when there is none; without a hit, the received side when the
        # filter has it, else the dealt one.
        battle = self._battle()
        for side, index, hit in self._shownHits():
            if (side, index) == self._chosen:
                return battle, side, hit
        return battle, RECEIVED if RECEIVED in self._sides else DEALT, None

    def init(self):
        with self._model.transaction() as model:
            model.setAllHitsLabel(self._texts['allHits'])
        self._model.onSideFilter += self._onSideFilter
        self._model.onResultFilter += self._onResultFilter
        self._model.onHit += self._onHit
        self._model.onStep += self._onStep
        self._battleSelector.onBattleSelected += self._onBattleSelected
        self._store.onChanged += self._update
        if self._settings is not None:
            self._settings.onChanged += self._onSettingChanged
        battle = self._battleSelector.selectedBattle
        self._battleId = battle.battleId if battle is not None else None
        self._update()

    def fini(self):
        if self._settings is not None:
            self._settings.onChanged -= self._onSettingChanged
        self._settings = None
        self._store.onChanged -= self._update
        self._battleSelector.onBattleSelected -= self._onBattleSelected
        self.onChanged.clear()
        self._model.onStep -= self._onStep
        self._model.onHit -= self._onHit
        self._model.onResultFilter -= self._onResultFilter
        self._model.onSideFilter -= self._onSideFilter
        self._model = None
        self._store = None
        self._battleSelector = None

    def _onBattleSelected(self, battle):
        self._battleId = battle.battleId if battle is not None else None
        self._chosen = None
        self._update()

    def _onSettingChanged(self, key):
        # The hits on allies shown or hidden: the first hit is chosen.
        if key == 'showFriendlyFire':
            self._chosen = None
            self._update()

    def _onSideFilter(self, args=None):
        side = (args or {}).get('id') or ''
        if side in ('',) + _SIDES:
            self._sides = _sessionFilter['sides'] = _pressed(self._sides, side, _SIDES)
            self._update()

    def _onResultFilter(self, args=None):
        result = (args or {}).get('id') or ''
        if result in ('',) + HitResult.ALL:
            self._results = _sessionFilter['results'] = _pressed(self._results, result, HitResult.ALL)
            self._update()

    def _onHit(self, args=None):
        index = int((args or {}).get('index', -1))
        shown = self._shownHits()
        if 0 <= index < len(shown):
            self._chosen = shown[index][:2]
            self._update()

    def _onStep(self, args=None):
        keys = [(side, index) for side, index, _ in self._shownHits()]
        if not keys:
            return
        delta = int((args or {}).get('delta', 1))
        position = keys.index(self._chosen) if self._chosen in keys else 0
        self._chosen = keys[(position + delta) % len(keys)]
        self._update()

    def _battle(self):
        return self._store.getBattle(self._battleId) if self._battleId is not None else None

    def _battleHits(self):
        # [(side, index among the battle's hits of its side, hit)] of both sides in the battle's order, without the
        # hits on allies unless they are shown; None without a battle. Hits at the same time keep the received first.
        battle = self._battle()
        if battle is None:
            return None
        showsAllies = self._settings is not None and self._settings.values.get('showFriendlyFire')
        hits = [(side, index, hit) for side in _SIDES for index, hit in enumerate(getattr(battle, _HITS_FIELD[side]))
                if showsAllies or not battle.isAllyHit(hit)]
        return sorted(hits, key=lambda each: each[2].time)

    def _shownHits(self):
        return [(side, index, hit) for side, index, hit in self._battleHits() or ()
                if side in self._sides and hit.result in self._results]

    def _update(self):
        hits = self._battleHits()
        with self._model.transaction() as model:
            model.setIsVisible(hits is not None)
            # Each group's counts under the other group's choice.
            hits = hits or []
            sideCounts = dict((side, _count(hits, (side,), self._results)) for side in _SIDES)
            sideCounts[''] = _count(hits, _SIDES, self._results)
            resultCounts = dict((result, _count(hits, self._sides, (result,))) for result in HitResult.ALL)
            resultCounts[''] = _count(hits, self._sides, HitResult.ALL)
            allLabel = clientText(_ALL_KEY) or ''
            _fillFilters(model.getSides(), _SIDES, self._sides,
                         {'': allLabel, RECEIVED: self._texts['received'], DEALT: self._texts['dealt']}, sideCounts)
            _fillFilters(model.getResults(), HitResult.ALL, self._results,
                         dict([('', allLabel)] + [(result, clientText(key)) for result, key in _RESULT_KEYS.items()]),
                         resultCounts)
            # The column of the shell mode's icon: for a battle with a known mode, whatever the filter shows.
            model.setHasShellModes(any(hit.shellMode for _, _, hit in hits))

            shown = self._shownHits()
            keys = [(side, index) for side, index, _ in shown]
            if self._chosen not in keys:
                self._chosen = keys[0] if keys else None
            battle = self._battle()
            hitModels = model.getHits()
            hitModels.clear()
            for side, index, hit in shown:
                item = HitItemModel()
                # A file can come from another player: a hit the client cannot show stays a row without its data, so
                # the list keeps its rows and the screen stays open.
                try:
                    _fillHit(item, battle, side, hit)
                except Exception:
                    _logger.exception('hits panel: cannot show the %s hit %s', side, index)
                hitModels.addViewModel(item)
            hitModels.invalidate()
            model.setSelectedHit(keys.index(self._chosen) if self._chosen in keys else -1)
        self.onChanged()
