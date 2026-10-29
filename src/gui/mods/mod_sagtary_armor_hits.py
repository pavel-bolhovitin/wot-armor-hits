# -*- coding: utf-8 -*-
"""Armor Hits by Sagtary: hangar viewer of hits received and dealt in battle.

Entry point loaded by the game; the code is in the gui.mods.sagtary_armor_hits package.
"""
import logging

from PlayerEvents import g_playerEvents

from gui.mods.sagtary_armor_hits import settings
from gui.mods.sagtary_armor_hits.config import BATTLE_FILES_DIR
from gui.mods.sagtary_armor_hits.data import battle_modes
from gui.mods.sagtary_armor_hits.data.battle_file import BattleFileError, BattleFiles
from gui.mods.sagtary_armor_hits.data.battles import BattleCollector, BattleStore
from gui.mods.sagtary_armor_hits.data.debug_recorder import DebugRecorder
from gui.mods.sagtary_armor_hits.data.hit_collector import HitCollector
from gui.mods.sagtary_armor_hits.data.hooks import ClientHooks
from gui.mods.sagtary_armor_hits.views.hits.hits_screen import HitsScreen
from gui.mods.sagtary_armor_hits.trace import mainLogger, setVerbose
from gui.mods.sagtary_armor_hits.views.lobby_button.lobby_button import LobbyButton

__version__ = '1.2.0'

_logger = logging.getLogger('sagtary.armor_hits')


def _openViewer():
    # The mod's own hits screen; only the layout of its panels for now.
    _logger.info('lobby button clicked')
    _hitsScreen.open()


# The settings, changed by the hits screen's settings menu too.
_settings = settings.ModSettings()
# The client's methods the debug record and the hit collector listen to, each wrapped once.
_hooks = ClientHooks()
# On only with the "debug" setting.
_debugRecorder = DebugRecorder(_hooks)


def _saving(battle):
    # How the battle is kept, by the battleModes setting of its mode's group.
    return battle_modes.savingOf(_settings.values['battleModes'], battle.battleType)


def _isKept(battle):
    # A battle is kept unless its group's setting is off; a replay always, to look at its hits.
    return battle.isReplay or _saving(battle) != battle_modes.OFF


_battleStore = BattleStore()
_battleCollector = BattleCollector(_battleStore, _isKept)
_hitCollector = HitCollector(_battleStore, _hooks)
# The battle files of the hits screen's save and load buttons.
_battleFiles = BattleFiles(BATTLE_FILES_DIR, __version__)
_hitsScreen = HitsScreen(_battleStore, _battleFiles, _settings)
_button = LobbyButton(_openViewer)
# The battle files are loaded once a client session.
_isImported = False


def _onSettingChanged(key):
    # The debug record and the info lines of the log start and stop with their setting; the lobby button's place
    # changes with the next client start.
    if key == 'debug':
        setVerbose(_settings.values['debug'])
        if _settings.values['debug']:
            _debugRecorder.install()
        else:
            _debugRecorder.uninstall()


def _onBattleLeft(battle):
    # The battle's file when the player leaves a battle of a group kept in files (battleModes); a replay is not saved
    # (it would write over the file of the battle played).
    if battle.isReplay or _saving(battle) != battle_modes.FILE:
        return
    try:
        _battleFiles.save(battle)
    except BattleFileError as error:
        _logger.warning('auto save: %s', error)


def _onAccountShowGUI(*args):
    # The battle files of the folder when the hangar shows the first time: the battles saved before and the files
    # other players sent. Not again after a battle: the battles of the session are in the store already.
    global _isImported
    if _isImported:
        return
    _isImported = True
    try:
        battles, errors = _battleFiles.loadAll()
    except BattleFileError as error:
        _logger.info('import: %s', error)
        return
    for _, error in errors:
        _logger.warning('import: %s', error)
    if battles:
        _battleStore.addAll(battles)


def init():
    # Called by gui.mods after all mods are imported.
    values = _settings.load()
    setVerbose(values['debug'])
    _settings.onChanged += _onSettingChanged
    if values['debug']:
        _debugRecorder.install()
    _battleCollector.onBattleLeft += _onBattleLeft
    g_playerEvents.onAccountShowGUI += _onAccountShowGUI
    _battleCollector.install()
    _hitCollector.install()
    _hitsScreen.install()
    _button.add(values['showButtonInModsMenu'])
    mainLogger.info('init v%s%s', __version__, ', debug on' if values['debug'] else '')


def fini():
    # Called by gui.mods when the client shuts down.
    _settings.onChanged -= _onSettingChanged
    _button.remove()
    _debugRecorder.uninstall()
    _hitCollector.uninstall()
    _battleCollector.uninstall()
    _battleCollector.onBattleLeft -= _onBattleLeft
    g_playerEvents.onAccountShowGUI -= _onAccountShowGUI
    _hitsScreen.uninstall()
