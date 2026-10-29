# -*- coding: utf-8 -*-
"""Settings menu of the hits screen: the mod's settings, opened by the gear right of the battle selector.

SettingsMenuPresenter fills the view model (views/models/settings_menu_model.py) with the settings of the settings
file (settings.ModSettings), each on or off, and turns a setting over when the page tells it was clicked: ModSettings
writes the file and tells its listeners. The hits on allies are shown or hidden at once (the hits panel), the debug
record starts or stops at once (the entry module), the lobby button's place changes with the next client start (its
note). Under them, how the battles of each group of modes are kept (the battleModes setting, data/battle_modes.py):
off, for the session, in files too, from the next battle on; the page shows the groups' names only. The title is the
client's text, the labels the mod's: the client has none for the hits both on allies and by them, nor for the groups.
"""
from gui.mods.sagtary_armor_hits.data import battle_modes
from gui.mods.sagtary_armor_hits.data.client_names import clientText
from gui.mods.sagtary_armor_hits.views.models.settings_menu_model import BattleModeModel, SettingItemModel

_TITLE_KEY = '#settings:title'
# The settings in the menu's order: (key, the client's text of its label or None, whether it changes with the next
# client start).
_ITEMS = (
    ('showFriendlyFire', None, False),
    ('showButtonInModsMenu', None, True),
    ('debug', None, False),
)


class SettingsMenuPresenter(object):

    def __init__(self, model, modSettings, texts):
        # texts: {setting key: its label, 'restart': the note of a setting that changes with the next client start,
        # 'battleModes': the title of the groups of modes, a group: its label, 'off', 'session', 'file': the labels
        # of how its battles are kept} in the client language.
        self._model = model
        self._settings = modSettings
        self._texts = texts

    def init(self):
        self._model.setTitle(clientText(_TITLE_KEY) or '')
        self._model.onToggle += self._onToggle
        self._model.onBattleMode += self._onBattleMode
        self._settings.onChanged += self._update
        self._update()

    def fini(self):
        self._settings.onChanged -= self._update
        self._model.onBattleMode -= self._onBattleMode
        self._model.onToggle -= self._onToggle
        self._model = None
        self._settings = None

    def _onToggle(self, args=None):
        key = (args or {}).get('key')
        if key in [item[0] for item in _ITEMS]:
            self._settings.set(key, not self._settings.values[key])

    def _onBattleMode(self, args=None):
        group, saving = (args or {}).get('group'), (args or {}).get('saving')
        if group in battle_modes.GROUPS and saving in battle_modes.SAVINGS:
            self._settings.set('battleModes', dict(self._settings.values['battleModes'], **{str(group): str(saving)}))

    def _update(self, *args):
        with self._model.transaction() as model:
            items = model.getItems()
            items.clear()
            for key, textKey, onRestart in _ITEMS:
                item = SettingItemModel()
                item.setKey(key)
                item.setLabel((clientText(textKey) if textKey else None) or self._texts[key])
                item.setNote(self._texts['restart'] if onRestart else '')
                item.setIsOn(self._settings.values[key])
                items.addViewModel(item)
            items.invalidate()
            model.setModesTitle(self._texts['battleModes'])
            model.setOffLabel(self._texts['off'])
            model.setSessionLabel(self._texts['session'])
            model.setFileLabel(self._texts['file'])
            savings = self._settings.values['battleModes']
            modes = model.getModes()
            modes.clear()
            for group in battle_modes.GROUPS:
                mode = BattleModeModel()
                mode.setGroup(group)
                mode.setLabel(self._texts[group])
                mode.setSaving(savings[group])
                modes.addViewModel(mode)
            modes.invalidate()
