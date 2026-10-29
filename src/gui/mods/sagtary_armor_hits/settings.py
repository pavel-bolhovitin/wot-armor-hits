# -*- coding: utf-8 -*-
"""User settings: a JSON file in the game folder, written with the defaults when it is not there.

ModSettings keeps the settings in memory for the mod: the hits screen's settings menu changes them (set), which
writes the file and tells the listeners (onChanged, with the key).
"""
import json
import logging
import os

from Event import Event

from gui.mods.sagtary_armor_hits.config import DEFAULT_SETTINGS, SETTINGS_PATH
from gui.mods.sagtary_armor_hits.data import battle_modes

_logger = logging.getLogger('sagtary.armor_hits')


def _write(path, settings):
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, 'w') as f:
        json.dump(settings, f, indent=4, sort_keys=True, separators=(',', ': '))
        f.write('\n')


def load():
    # The settings: values from the file over DEFAULT_SETTINGS. A missing, unreadable or wrong value keeps its default.
    settings = dict(DEFAULT_SETTINGS)
    if not os.path.isfile(SETTINGS_PATH):
        try:
            _write(SETTINGS_PATH, settings)
        except (IOError, OSError):
            _logger.exception('settings: cannot write %s', SETTINGS_PATH)
        return settings
    try:
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
    except (IOError, OSError, ValueError):
        _logger.exception('settings: cannot read %s, using the defaults', SETTINGS_PATH)
        return settings
    if not isinstance(data, dict):
        _logger.warning('settings: %s is not a JSON object, using the defaults', SETTINGS_PATH)
        return settings
    for key, value in data.items():
        if key not in DEFAULT_SETTINGS:
            _logger.warning('settings: unknown key %r', key)
        elif type(value) is not type(DEFAULT_SETTINGS[key]):
            _logger.warning('settings: %r must be %s, using the default', key, type(DEFAULT_SETTINGS[key]).__name__)
        else:
            settings[key] = value
    # A group of battleModes missing or of a wrong value keeps its default.
    settings['battleModes'] = battle_modes.normalized(settings['battleModes'])
    return settings


class ModSettings(object):

    def __init__(self):
        self.values = dict(DEFAULT_SETTINGS)
        self.onChanged = Event()

    def load(self):
        self.values = load()
        return self.values

    def set(self, key, value):
        # Changes a setting and writes the file; a key or a value of a wrong type is not taken.
        if key not in DEFAULT_SETTINGS or type(value) is not type(DEFAULT_SETTINGS[key]):
            _logger.warning('settings: %r cannot be %r', key, value)
            return
        if self.values.get(key) == value:
            return
        self.values = dict(self.values, **{key: value})
        try:
            _write(SETTINGS_PATH, self.values)
        except (IOError, OSError):
            _logger.exception('settings: cannot write %s', SETTINGS_PATH)
        self.onChanged(key)
