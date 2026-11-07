# -*- coding: utf-8 -*-
"""Battle file format 2 to format 3.

Format 3 keeps the shell's mode of a hit, for a gun that changes some of its shell's parameters before the shot
(standard or calibrated shells): the mode the hit's battle event tells (shotMode) and the shooter's shell params
switcher at the hit (shooterSwitcher). Format 2 has neither, so its hits get their defaults: no mode known.
"""


def convert(data):
    return dict(data)
