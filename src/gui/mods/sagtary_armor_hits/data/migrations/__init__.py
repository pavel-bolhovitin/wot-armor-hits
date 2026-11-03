# -*- coding: utf-8 -*-
"""The converters of the old battle file formats, so that the mod's code knows only the latest one.

A file of an old format is converted when it is read, step by step up to the latest format, in memory only: the file
stays as it is. A converter (v<N>_to_v<N+1>.py) takes the file's JSON data and gives it in the next format. It imports
nothing of the mod, so a later change of the mod's code does not touch it. What it cannot convert it leaves out: the
field gets its default when the battle is read.
"""
from gui.mods.sagtary_armor_hits.data.migrations import v1_to_v2

# {format version: the converter to the next version}
_CONVERTERS = {1: v1_to_v2.convert}


def toLatest(data):
    # The JSON data of a battle file in the latest format, with its version.
    version = data.get('formatVersion')
    while version in _CONVERTERS:
        data = _CONVERTERS[version](data)
        version += 1
        data['formatVersion'] = version
    return data
