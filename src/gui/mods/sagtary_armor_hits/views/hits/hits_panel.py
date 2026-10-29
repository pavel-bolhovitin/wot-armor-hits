# -*- coding: utf-8 -*-
"""Hits panel of the hits screen: the hits of the selected battle, on the player's vehicle or by the player.

HitsPanelPresenter fills the view model (views/models/hits_panel_model.py) for the battle the battle selector shows:
the side (received or dealt hits), the result filters with their counts, and the hits that pass them; it keeps the
chosen hit and tells its listeners when the panel changes (onChanged, the battle, the side and the chosen hit in
selection). The hits on allies (Hit.isAllyHit) are left out, numbered without them, unless the mod's settings show
them (showFriendlyFire; the panel follows the setting at once). The icons are the client's damage log icons; the shell
kinds, the vehicle names and the "All" label are the client's texts.
"""
from Event import Event
from items.vehicles import VehicleDescr

from gui.mods.sagtary_armor_hits.data.client_names import clientText, vehicleClass, vehicleShortName
from gui.mods.sagtary_armor_hits.data.hits import HitResult, ownShellIsGold
from gui.mods.sagtary_armor_hits.views.models.hits_panel_model import HitFilterModel, HitItemModel

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


def _time(seconds):
    seconds = int(seconds)
    return '%d:%02d' % (seconds // 60, seconds % 60)


def _ownGoldKinds(battle):
    # The shell kinds of the player's gun in the battle that are only premium shells: a dealt hit recorded before the
    # mod knew the player's premium shells is gold by its kind.
    try:
        descriptor = VehicleDescr(compactDescr=battle.vehicleDescriptor.decode('hex'))
    except Exception:
        return frozenset()
    kinds = set(shot.shell.kind for shot in descriptor.gun.shots)
    return frozenset(kind for kind in kinds if ownShellIsGold(descriptor, kind))


def _fillHit(item, number, hit):
    item.setNumber(number)
    item.setTime(_time(hit.time))
    item.setResult(hit.result)
    item.setVehicleName(vehicleShortName(hit.vehicleId) or '#%s' % hit.vehicleId)
    item.setVehicleClass(_CLASS_ICONS.get(vehicleClass(hit.vehicleId), ''))
    item.setPlayerName(hit.playerName)
    if hit.shellType:
        item.setShellText(clientText(_SHELL_TEXT_KEY % hit.shellType) or '')
        item.setShellName(clientText(_SHELL_NAME_KEY % hit.shellType) or '')
    item.setDamage(hit.damage)
    item.setHasCrits(hit.critsCount > 0)
    item.setIsGoldShell(hit.isGoldShell)


class HitsPanelPresenter(object):

    def __init__(self, model, store, battleSelector, texts, modSettings=None):
        # texts: {'received', 'dealt'}: the tab labels in the client language. modSettings: settings.ModSettings, None
        # for the default settings.
        self._model = model
        self._store = store
        self._settings = modSettings
        self._battleSelector = battleSelector
        self._texts = texts
        self._battleId = None
        self._side = RECEIVED
        self._filter = ''
        # Number of the chosen hit on its side (stays chosen when the filters change while it passes them).
        self._hitNumber = None
        self.onChanged = Event()

    @property
    def shownHits(self):
        # [(number, hit)] the panel lists: the chosen side's hits that pass the filter.
        return self._shownHits()

    @property
    def selectedNumber(self):
        # Number of the chosen hit on its side, None without one.
        return self._hitNumber

    @property
    def selection(self):
        # (battle, side, chosen hit): the battle is None when there is none, the hit when its side has none.
        battle = self._store.getBattle(self._battleId) if self._battleId is not None else None
        hits = dict(self._sideHits() or ())
        return battle, self._side, hits.get(self._hitNumber)

    def init(self):
        with self._model.transaction() as model:
            model.setReceivedLabel(self._texts['received'])
            model.setDealtLabel(self._texts['dealt'])
            model.setAllLabel(clientText(_ALL_KEY) or '')
        self._model.onSide += self._onSide
        self._model.onFilter += self._onFilter
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
        self._model.onFilter -= self._onFilter
        self._model.onSide -= self._onSide
        self._model = None
        self._store = None
        self._battleSelector = None

    def _onBattleSelected(self, battle):
        self._battleId = battle.battleId if battle is not None else None
        self._filter, self._hitNumber = '', None
        self._update()

    def _onSettingChanged(self, key):
        # The hits on allies shown or hidden: the numbers change, the first hit is chosen.
        if key == 'showFriendlyFire':
            self._filter, self._hitNumber = '', None
            self._update()

    def _onSide(self, args=None):
        side = (args or {}).get('side')
        if side in _SIDES and side != self._side:
            self._side, self._filter, self._hitNumber = side, '', None
            self._update()

    def _onFilter(self, args=None):
        result = (args or {}).get('id') or ''
        self._filter = result if result in HitResult.ALL else ''
        self._update()

    def _onHit(self, args=None):
        index = int((args or {}).get('index', -1))
        shown = self._shownHits()
        if 0 <= index < len(shown):
            self._hitNumber = shown[index][0]
            self._update()

    def _onStep(self, args=None):
        shown = self._shownHits()
        if not shown:
            return
        delta = int((args or {}).get('delta', 1))
        numbers = [number for number, _ in shown]
        index = numbers.index(self._hitNumber) if self._hitNumber in numbers else 0
        self._hitNumber = numbers[(index + delta) % len(numbers)]
        self._update()

    def _sideHits(self):
        # [(number, hit)] of the battle on the chosen side, numbered from 1 in battle order; without the hits on
        # allies unless they are shown.
        battle = self._store.getBattle(self._battleId) if self._battleId is not None else None
        if battle is None:
            return None
        hits = getattr(battle, _HITS_FIELD[self._side])
        if self._settings is None or not self._settings.values.get('showFriendlyFire'):
            hits = [hit for hit in hits if not hit.isAllyHit]
        return list(enumerate(hits, 1))

    def _shownHits(self):
        hits = self._sideHits() or []
        return [(number, hit) for number, hit in hits if not self._filter or hit.result == self._filter]

    def _update(self):
        hits = self._sideHits()
        with self._model.transaction() as model:
            model.setIsVisible(hits is not None)
            model.setSide(self._side)
            filterModels = model.getFilters()
            filterModels.clear()
            for result in ('',) + HitResult.ALL:
                item = HitFilterModel()
                item.setId(result)
                item.setCount(len([hit for _, hit in hits or () if not result or hit.result == result]))
                filterModels.addViewModel(item)
            filterModels.invalidate()
            model.setSelectedFilter(self._filter)

            shown = self._shownHits()
            numbers = [number for number, _ in shown]
            if self._hitNumber not in numbers:
                self._hitNumber = numbers[0] if numbers else None
            hitModels = model.getHits()
            hitModels.clear()
            goldKinds = _ownGoldKinds(self._store.getBattle(self._battleId)) if self._side == DEALT and shown else ()
            for number, hit in shown:
                item = HitItemModel()
                _fillHit(item, number, hit.replace(isGoldShell=True) if hit.shellType in goldKinds else hit)
                hitModels.addViewModel(item)
            hitModels.invalidate()
            model.setSelectedHit(numbers.index(self._hitNumber) if self._hitNumber in numbers else -1)
        self.onChanged()
