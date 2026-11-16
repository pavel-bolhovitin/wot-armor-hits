# -*- coding: utf-8 -*-
"""Record: a plain data object with named fields and their defaults, the base of Battle and Hit.

A record class lists its fields in FIELDS as (name, default) and, in NESTED, the fields that hold other records
({name: record class}): a tuple of them, or one (None for none). A new field is a new line in FIELDS with a default,
so the code that makes or reads a record keeps working, and a record read from a file without the field gets the
default. A field that is None until known holds a whole number then (an index, a team); one that holds another kind
names it in KINDS ({name: a value of that kind}), for the checks of a file (battle_file_check.py).
"""
from collections import OrderedDict


class Record(object):
    FIELDS = ()
    NESTED = {}
    KINDS = {}
    __slots__ = ()

    def __init__(self, **values):
        names = set(name for name, _ in self.FIELDS)
        unknown = set(values) - names
        if unknown:
            raise TypeError('unknown %s fields: %s' % (type(self).__name__, ', '.join(sorted(unknown))))
        for name, default in self.FIELDS:
            setattr(self, name, values.get(name, default))

    @classmethod
    def fromDict(cls, data):
        # The fields the record knows; missing ones get their defaults, unknown ones are skipped.
        values = {}
        for name, _ in cls.FIELDS:
            if name not in data:
                continue
            value = data[name]
            if name in cls.NESTED and isinstance(value, dict):
                value = cls.NESTED[name].fromDict(value)
            elif name in cls.NESTED and value is not None:
                value = tuple(cls.NESTED[name].fromDict(item) for item in value or () if isinstance(item, dict))
            elif isinstance(value, list):
                value = tuple(value)
            values[name] = value
        return cls(**values)

    def toDict(self):
        data = OrderedDict()
        for name, _ in self.FIELDS:
            value = getattr(self, name)
            if isinstance(value, Record):
                value = value.toDict()
            elif name in self.NESTED and value is not None:
                value = [item.toDict() for item in value]
            elif isinstance(value, tuple):
                value = list(value)
            data[name] = value
        return data

    def replace(self, **values):
        data = dict((name, getattr(self, name)) for name, _ in self.FIELDS)
        data.update(values)
        return type(self)(**data)

    def __eq__(self, other):
        return type(other) is type(self) and all(
            getattr(self, name) == getattr(other, name) for name, _ in self.FIELDS)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, ', '.join(
            '%s=%r' % (name, getattr(self, name)) for name, _ in self.FIELDS))
