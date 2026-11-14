# -*- coding: utf-8 -*-
"""Battle modes: the client's battle types (Battle.battleType, constants.ARENA_GUI_TYPE) in groups by how much the
battle asks of the player's skill, and how the battles of each group are kept (the battleModes setting).

The groups, in the settings menu's order:
- random: battles by the usual rules (random, grand battles, Mapbox);
- competitive: rated and team battles (ranked, Onslaught, team battles, Stronghold);
- training: not real battles (training rooms, the modes' trainings, map training, the new player's onboarding);
- fun: farm and event modes, where skill matters little (Frontline, Steel Hunter, special modes, events, ...);
- other: every type of no group: the special battle, and the modes a client update adds.

The lists hold every type of the WG clients (EU, NA, ASIA) since 2021, also the events gone from the current client:
an event comes back under its old name.

A group's battles are kept:
- OFF: not at all, the hits screen does not get them;
- SESSION: until the game closes;
- FILE: until the game closes, and in their battle files from the moment the player leaves them.
By default every group's battles are kept for the session (config.DEFAULT_SETTINGS).

The types are looked up by their names when needed: the game modes (comp7, fun_random, ...) add theirs to
ARENA_GUI_TYPE while the client starts, after the mod is imported.
"""
import constants

from gui.mods.sagtary_armor_hits.config import DEFAULT_SETTINGS

OFF = 'off'
SESSION = 'session'
FILE = 'file'
SAVINGS = (OFF, SESSION, FILE)

RANDOM = 'random'
COMPETITIVE = 'competitive'
TRAINING = 'training'
FUN = 'fun'
OTHER = 'other'
GROUPS = (RANDOM, COMPETITIVE, TRAINING, FUN, OTHER)

DEFAULT_SAVINGS = DEFAULT_SETTINGS['battleModes']

_TYPE_NAMES = {
    RANDOM: ('RANDOM', 'EPIC_RANDOM', 'MAPBOX'),
    COMPETITIVE: ('RANKED', 'COMP7', 'TOURNAMENT_COMP7', 'COMP7_LIGHT', 'CYBERSPORT', 'SORTIE_2', 'FORT_BATTLE_2'),
    TRAINING: ('TRAINING', 'EPIC_RANDOM_TRAINING', 'EPIC_TRAINING', 'TRAINING_COMP7', 'MAPS_TRAINING', 'RTS_TRAINING',
               'RTS_BOOTCAMP', 'STORY_MODE_ONBOARDING'),
    FUN: ('EPIC_BATTLE', 'BATTLE_ROYALE', 'FUN_RANDOM', 'EVENT_BATTLES', 'WINBACK', 'RTS', 'STORY_MODE_REGULAR',
          'FALLOUT', 'FALLOUT_CLASSIC', 'FALLOUT_MULTITEAM', 'HALLOWEEN', 'HALLOWEEN_DEFENCE', 'LAST_STAND', 'FORT_RUSH',
          'GRINCH', 'LUNAR_POSSESSION', 'COSMIC_EVENT', 'WHITE_TIGER', 'FALL_TANKS'),
}


def groupOf(battleType):
    # The group of a battle type; OTHER for a type of no group.
    for group, names in _TYPE_NAMES.items():
        if battleType in [getattr(constants.ARENA_GUI_TYPE, name, None) for name in names]:
            return group
    return OTHER


def savingOf(savings, battleType):
    # How a battle of the type is kept, by the battleModes setting.
    group = groupOf(battleType)
    return savings.get(group, DEFAULT_SAVINGS[group])


def normalized(savings):
    # The setting with each group's value: one of SAVINGS from savings, else the group's default.
    savings = savings if isinstance(savings, dict) else {}
    return dict((group, savings[group] if savings.get(group) in SAVINGS else DEFAULT_SAVINGS[group])
                for group in GROUPS)
