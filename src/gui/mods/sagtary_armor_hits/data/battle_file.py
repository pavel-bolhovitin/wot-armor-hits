# -*- coding: utf-8 -*-
"""A battle saved to a JSON file and read back: a player sends a battle's file with a report, and the hits screen shows
the battle on another client.

BattleFiles keeps one file per battle in its folder, named by the battle id (FILE_NAME), so a battle saved again
writes over its own file. Loading reads every file of the folder that has the name pattern (FILE_PATTERN): the files
other players sent, put into the folder; deleting removes them all. A file is the fields of one Battle:
    {
      "formatVersion": 2,         # version of this layout; a file of a newer layout is not read
      "appVersion": "0.1.0",      # version of the mod that wrote the file
      "exportTime": 1760781180.0, # when it was written, Unix time
      "battleId": 49612174051990431,
      ...                         # the other Battle fields
    }
A file of an old format is converted to the latest one when it is read (migrations/), in memory only: the file stays
as it is, also when its battle is saved again, and the battle keeps the format its file has (Battle.isOldFormat). A
battle is read with the fields Battle knows: a field the file does not have gets its default, a field Battle does not
know is skipped.

A file can come from another player and its battle id names the battle's file, so a text there could be a path out of
the folder: a file whose id is not a number is not read, and a battle's file is written only inside the folder.
"""
import glob
import io
import json
import os
import time
from collections import OrderedDict

from gui.mods.sagtary_armor_hits.data import migrations
from gui.mods.sagtary_armor_hits.data.battles import FORMAT_VERSION, Battle

# The file of a battle by its id, and the names of the files loaded.
FILE_NAME = 'hits_%s.json'
FILE_PATTERN = 'hits_*.json'


class BattleFileError(Exception):
    pass


def _text(value):
    # The client gives texts as UTF-8 byte strings or as unicode; json needs one kind to write them as they are.
    if isinstance(value, str):
        return value.decode('utf-8', 'replace')
    if isinstance(value, dict):
        return OrderedDict((key, _text(item)) for key, item in value.items())
    if isinstance(value, list):
        return [_text(item) for item in value]
    return value


def _isBattleId(value):
    # The server's id of a battle: a positive whole number.
    return isinstance(value, (int, long)) and not isinstance(value, bool) and value > 0


def writeBattle(path, battle, appVersion):
    data = _text(battle.replace(formatVersion=FORMAT_VERSION, appVersion=appVersion, exportTime=time.time()).toDict())
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        # separators: Python 2 puts a space at the line ends after the commas by default.
        content = json.dumps(data, indent=2, separators=(',', ': '), ensure_ascii=False)
        if isinstance(content, str):
            # Only ASCII texts: json gives a byte string.
            content = content.decode('ascii')
        with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
    except (IOError, OSError, TypeError, ValueError) as error:
        raise BattleFileError('cannot write %s: %s' % (path, error))


def readBattle(path):
    # The battle of the file, in the latest format; it keeps the format its file has.
    if not os.path.isfile(path):
        raise BattleFileError('no file %s' % path)
    try:
        with io.open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, OSError, ValueError) as error:
        raise BattleFileError('cannot read %s: %s' % (path, error))
    if not isinstance(data, dict):
        raise BattleFileError('%s is not a battle file' % path)
    formatVersion = data.get('formatVersion')
    if not isinstance(formatVersion, int) or formatVersion > FORMAT_VERSION:
        raise BattleFileError('%s has format version %r, this mod reads up to %d' % (
            path, formatVersion, FORMAT_VERSION))
    battle = Battle.fromDict(migrations.toLatest(data))
    if not _isBattleId(battle.battleId):
        raise BattleFileError('%s is not a battle file' % path)
    return battle.replace(formatVersion=formatVersion)


class BattleFiles(object):

    def __init__(self, folder, appVersion):
        self._folder = folder
        self._appVersion = appVersion

    @property
    def folder(self):
        return self._folder

    def pathOf(self, battle):
        # The battle's file, right in the folder; an error for anything else.
        if not _isBattleId(battle.battleId):
            raise BattleFileError('not a battle id: %r' % (battle.battleId,))
        path = os.path.join(self._folder, FILE_NAME % battle.battleId)
        if os.path.dirname(os.path.realpath(path)) != os.path.realpath(self._folder):
            raise BattleFileError('%s is not in %s' % (path, self._folder))
        return path

    def save(self, battle):
        # Writes the battle to its file, over the one saved before, but for a battle of a file of an old format: the
        # file stays as it is. The file's path.
        path = self.pathOf(battle)
        if not battle.isOldFormat:
            writeBattle(path, battle, self._appVersion)
        return path

    def loadAll(self):
        # ([battle] of the folder's files, [(path, error)] of the files not read); an error without any file.
        paths = sorted(glob.glob(os.path.join(self._folder, FILE_PATTERN)))
        if not paths:
            raise BattleFileError('no files %s in %s' % (FILE_PATTERN, os.path.abspath(self._folder)))
        battles, errors = [], []
        for path in paths:
            try:
                battles.append(readBattle(path))
            except BattleFileError as error:
                errors.append((path, error))
        return battles, errors

    def deleteAll(self):
        # Removes all the folder's files: [error] of the files not removed.
        errors = []
        paths = glob.glob(os.path.join(self._folder, FILE_PATTERN))
        for path in paths:
            try:
                os.remove(path)
            except OSError as error:
                errors.append(BattleFileError('cannot delete %s: %s' % (path, error)))
        return errors
