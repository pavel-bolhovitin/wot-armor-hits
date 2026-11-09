# -*- coding: utf-8 -*-
"""Battle file format 2 to format 3.

Format 3 keeps the state of the gun's mechanic at the shot (mechanicShotMode), for a gun that changes some of its
shell's parameters before the shot (standard or calibrated shells). Format 2 does not have it, so its hits get the
default: not known.
"""


def convert(data):
    return dict(data)
