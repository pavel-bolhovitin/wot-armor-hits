# -*- coding: utf-8 -*-
"""Battles of the current game session: the data of the hits screen's battle selector.

- Battle: what is known about one battle, read from the client when the battle starts, and its hits (hits.py).
  A record (record.py): a new field is a line in FIELDS with a default.
- BattleStore: the battles of this session in memory, newest first, up to BATTLES_LIMIT. It tells its listeners
  when the list changes (onChanged). The store is not saved by itself; battle_file.py writes and reads it on demand.
- BattleCollector: adds a Battle to the store when the player enters a battle or starts a replay, and writes the
  winner to it when the round finishes. A battle the player left before its end has no winner (result UNKNOWN). It
  tells its listeners when the player leaves the battle (onBattleLeft, with the battle as it is in the store). A
  battle that is not to be kept (isKept: the battleModes setting) is not added, so its hits are not collected.
"""
import logging
import time

import BattleReplay
import BigWorld
from Event import Event
from PlayerEvents import g_playerEvents

from gui.mods.sagtary_armor_hits.config import BATTLES_LIMIT
from gui.mods.sagtary_armor_hits.data.hits import Hit, compactDescriptor, vehicleTypeId
from gui.mods.sagtary_armor_hits.data.record import Record

_logger = logging.getLogger('sagtary.armor_hits')


class BattleResult(object):
    # The battle's result for the player.
    UNKNOWN = ''
    WIN = 'win'
    DEFEAT = 'defeat'
    DRAW = 'draw'


# Battle.winnerTeam of a draw.
DRAW_TEAM = 0

# The client's arenaTypeID is (gameplayID << 16) | geometryID.
_GAMEPLAY_ID_SHIFT = 16
_MAP_ID_MASK = (1 << _GAMEPLAY_ID_SHIFT) - 1


class Battle(Record):
    # A battle keeps ids only: the names and images of the map and the vehicle are found by the ids in the client
    # (client_names.py).
    FIELDS = (
        ('battleId', 0),        # id of the battle on the server (the client's arenaUniqueID); the key of the battle
        ('mapId', 0),           # the map (the client's geometryID: the low 16 bits of arenaTypeID)
        ('gameplayId', 0),      # the gameplay on the map: standard, encounter, assault, ... (the high bits)
        ('battleType', 0),      # kind of battle: random, training, ... (constants.ARENA_GUI_TYPE)
        ('vehicleDescriptor', ''),
                                # the player's vehicle compact descriptor (type and modules), hex; '' when not known
        ('startedAt', 0.0),     # when the player entered the battle, Unix time in seconds
        ('isReplay', False),    # a replay watched, not a battle played
        ('playerName', ''),     # the name of the player who played the battle (in a replay, the recorded one)
        ('playerTeam', None),   # the player's team, 1 or 2; None when not known
        ('winnerTeam', None),   # the team that won, 1 or 2, DRAW_TEAM for a draw; None when not known
        ('endReason', None),    # how the battle ended (constants.FINISH_REASON); None when not known
        ('receivedHits', ()),   # hits on the player's vehicle, in battle order (hits.Hit)
        ('dealtHits', ()),      # the player's hits on other vehicles, in battle order (hits.Hit)
    )
    NESTED = {'receivedHits': Hit, 'dealtHits': Hit}
    __slots__ = tuple(name for name, _ in FIELDS)

    @property
    def vehicleId(self):
        # The player's vehicle type (intCD), from its compact descriptor; 0 when not known.
        return vehicleTypeId(self.vehicleDescriptor)

    @property
    def result(self):
        # Not known when the player left before the end or the battle is still going.
        if self.winnerTeam is None:
            return BattleResult.UNKNOWN
        if self.winnerTeam == DRAW_TEAM:
            return BattleResult.DRAW
        return BattleResult.WIN if self.winnerTeam == self.playerTeam else BattleResult.DEFEAT


def battleFromAvatar(player):
    # The battle the player has just entered, read from the client.
    arena = player.arena
    vehicleInfo = (arena.vehicles.get(player.playerVehicleID) or {}) if arena is not None else {}
    descriptor = getattr(player, 'vehicleTypeDescriptor', None)
    if descriptor is None:
        descriptor = vehicleInfo.get('vehicleType')
    return Battle(
        battleId=player.arenaUniqueID,
        mapId=player.arenaTypeID & _MAP_ID_MASK,
        gameplayId=player.arenaTypeID >> _GAMEPLAY_ID_SHIFT,
        battleType=player.arenaGuiType,
        startedAt=time.time(),
        isReplay=BattleReplay.isPlaying(),
        playerName=vehicleInfo.get('name') or getattr(player, 'name', '') or '',
        playerTeam=player.team,
        vehicleDescriptor=compactDescriptor(descriptor),
    )


class BattleStore(object):

    def __init__(self, limit=BATTLES_LIMIT):
        self._limit = limit
        self._battles = []
        self.onChanged = Event()

    def getBattles(self):
        # Newest first.
        return list(self._battles)

    def getBattle(self, battleId):
        for battle in self._battles:
            if battle.battleId == battleId:
                return battle
        return None

    def add(self, battle):
        # A battle with the same id (a reconnect to the same battle) is replaced and moves to the top.
        self._battles = [item for item in self._battles if item.battleId != battle.battleId]
        self._battles.insert(0, battle)
        del self._battles[self._limit:]
        self.onChanged()

    def update(self, battle):
        # New data of a battle in the store (its result): it keeps its place in the list.
        for index, item in enumerate(self._battles):
            if item.battleId == battle.battleId:
                self._battles[index] = battle
                self.onChanged()
                return True
        return False

    def addAll(self, battles):
        # Battles from elsewhere (a battle file): each replaces a battle with the same id; the list is then sorted by
        # the start time, newest first.
        ids = set(battle.battleId for battle in battles)
        merged = list(battles) + [item for item in self._battles if item.battleId not in ids]
        self._battles = sorted(merged, key=lambda battle: battle.startedAt, reverse=True)[:self._limit]
        self.onChanged()

    def clear(self):
        self._battles = []
        self.onChanged()


class BattleCollector(object):

    def __init__(self, store, isKept=None):
        # isKept(battle): whether a battle is added to the store; None: every battle.
        self._store = store
        self._isKept = isKept
        # Id of the battle the player is in, None out of battle or in a battle not kept.
        self._battleId = None
        self.onBattleLeft = Event()

    def install(self):
        g_playerEvents.onAvatarReady += self._onAvatarReady
        g_playerEvents.onRoundFinished += self._onRoundFinished
        g_playerEvents.onAvatarBecomeNonPlayer += self._onAvatarBecomeNonPlayer

    def uninstall(self):
        g_playerEvents.onAvatarBecomeNonPlayer -= self._onAvatarBecomeNonPlayer
        g_playerEvents.onRoundFinished -= self._onRoundFinished
        g_playerEvents.onAvatarReady -= self._onAvatarReady

    def _onAvatarReady(self):
        try:
            battle = battleFromAvatar(BigWorld.player())
        except Exception:
            _logger.exception('battles: cannot read the battle')
            return
        if self._isKept is not None and not self._isKept(battle):
            return
        self._battleId = battle.battleId
        self._store.add(battle)

    def _onRoundFinished(self, winnerTeam, reason, *args):
        battle = self._store.getBattle(self._battleId) if self._battleId is not None else None
        if battle is None:
            return
        battle = battle.replace(winnerTeam=winnerTeam, endReason=reason)
        self._store.update(battle)

    def _onAvatarBecomeNonPlayer(self, *args):
        battle = self._store.getBattle(self._battleId) if self._battleId is not None else None
        self._battleId = None
        if battle is not None:
            self.onBattleLeft(battle)
