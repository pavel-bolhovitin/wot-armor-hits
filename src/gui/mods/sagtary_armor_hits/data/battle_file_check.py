# -*- coding: utf-8 -*-
"""The checks of a battle file: it can come from another player, so what it has is checked before the mod's code gets it.

There is one check, of the latest format: a file of an old format is converted first (migrations/), so a new format
needs no checks of its own. The check goes by the fields of the records (Record.FIELDS, NESTED): a value of a file is
taken only when it is of the kind of the field's default, else it is left out and the field gets its default. The
kinds: a bool, a number (0.0), a whole number (0), a text (''), a position or a direction (x, y, z) or none of it (()),
a whole number not known yet (None). So a new field with such a default is checked with no more code; another kind
needs a line in _fits.
"""

# The largest file read: a battle's file has about 1 KB a hit, and all the files are read when the hangar shows.
FILE_SIZE_LIMIT = 5 * 1024 * 1024
# The end of a battle's start time, Unix time in seconds: the client's date formats are not to get more than 32 bits.
_TIME_LIMIT = 2 ** 31
# The most items a list of a file can have: far above the hits of any battle, and the hits screen has a row for each.
_LIST_LIMIT = 5000
# The largest number of a file: a battle id takes 64 bits.
_NUMBER_LIMIT = 2 ** 64
# The largest coordinate of a position of a file, in metres: beyond any map.
_POSITION_LIMIT = 1e4


def _isNumber(value):
    # A bool is not a number here; NaN and Infinity, which JSON reads too, fail the comparison.
    return (isinstance(value, (int, long, float)) and not isinstance(value, bool)
            and -_NUMBER_LIMIT <= value <= _NUMBER_LIMIT)


def _isWhole(value):
    return _isNumber(value) and not isinstance(value, float)


def _isPosition(value):
    return isinstance(value, list) and len(value) in (0, 3) and all(
        _isNumber(item) and abs(item) <= _POSITION_LIMIT for item in value)


def _fits(value, default):
    # Whether a value of a file is of the kind of the field's default.
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, float):
        return _isNumber(value)
    if isinstance(default, (int, long)):
        return _isWhole(value)
    if isinstance(default, basestring):
        return isinstance(value, basestring)
    if isinstance(default, tuple):
        return _isPosition(value)
    return value is None or _isWhole(value)


def validFields(data, record):
    # What a file's data has for a record class (Record), to make the record from: the values of its fields of the
    # kinds of their defaults, also in its nested records. Fields it does not know and a list's items that are no
    # records are left out too.
    fields = {}
    for name, default in record.FIELDS:
        value = data.get(name)
        nested = record.NESTED.get(name)
        if nested is None:
            if _fits(value, default):
                fields[name] = value
        elif isinstance(default, tuple):
            if isinstance(value, list) and len(value) <= _LIST_LIMIT:
                fields[name] = [validFields(item, nested) for item in value if isinstance(item, dict)]
        elif isinstance(value, dict):
            fields[name] = validFields(value, nested)
    return fields


def isBattleId(value):
    # The server's id of a battle: a positive whole number. It names the battle's file, so a text could be a path.
    return isinstance(value, (int, long)) and not isinstance(value, bool) and value > 0


def isStartTime(value):
    return 0 <= value < _TIME_LIMIT
