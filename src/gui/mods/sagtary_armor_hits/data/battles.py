# -*- coding: utf-8 -*-
"""Battles of the current game session: the data of the hits screen's battle selector.

- Battle: what is known about one battle, read from the client when the battle starts, and its hits (hits.py).
  A record (record.py): a new field is a line in FIELDS with a default. It is also all that its file has
  (battle_file.py): a file is the fields of one Battle.
- BattleStore: the battles of this session in memory, newest first, up to BATTLES_LIMIT. It tells its listeners
  when the list changes (onChanged). The store is not saved by itself; battle_file.py writes and reads it on demand.
- BattleCollector: adds a Battle to the store when the player enters a battle or starts a replay, with the vehicle
  the player enters it with; adds each vehicle the player gets later in the battle (a respawn, another one chosen
  before the battle starts) to its vehicle catalog, and writes the winner to it when the round finishes. A battle the
  player left before its end gets its winner later, from the battle results the server puts into the service channel
  when the battle ends (onResultReceived); until then it has none (result UNKNOWN). It tells its listeners when the
  player leaves the battle (onBattleLeft, with the battle as it is in the store). A battle that is not to be kept
  (isKept: the battleModes setting) is not added, so its hits are not collected.
"""
import logging
import time

import BattleReplay
import BigWorld
from Event import Event
from PlayerEvents import g_playerEvents
from chat_shared import SYS_MESSAGE_TYPE
from messenger.proto.events import g_messengerEvents

from gui.mods.sagtary_armor_hits.config import BATTLES_LIMIT
from gui.mods.sagtary_armor_hits.data import vehicle_catalog
from gui.mods.sagtary_armor_hits.data.hits import DealtHit, ReceivedHit
from gui.mods.sagtary_armor_hits.data.record import Record
from gui.mods.sagtary_armor_hits.data.vehicle_catalog import CatalogVehicle

_logger = logging.getLogger('sagtary.armor_hits')


class BattleResult(object):
    # The battle's result for the player.
    UNKNOWN = ''
    WIN = 'win'
    DEFEAT = 'defeat'
    DRAW = 'draw'


# Battle.winnerTeam of a draw.
DRAW_TEAM = 0
# The two teams of a battle.
_TEAMS = (1, 2)

# The client's arenaTypeID is (gameplayID << 16) | geometryID.
_GAMEPLAY_ID_SHIFT = 16
_MAP_ID_MASK = (1 << _GAMEPLAY_ID_SHIFT) - 1


# The latest format of the battle files (battle_file.py, migrations/).
FORMAT_VERSION = 4


class Battle(Record):
    # A battle keeps ids only: the names and images of the map and the vehicle are found by the ids in the client
    # (client_names.py).
    FIELDS = (
        ('formatVersion', FORMAT_VERSION),
                                # the format its file has, as the file tells it (an old one is converted in memory:
                                # migrations/); the latest for a battle of this session
        ('appVersion', ''),     # the version of the mod that wrote its file; '' when not saved yet
        ('exportTime', 0.0),    # when its file was written, Unix time; 0 when not saved yet
        ('battleId', 0),        # id of the battle on the server (the client's arenaUniqueID); the key of the battle
        ('mapId', 0),           # the map (the client's geometryID: the low 16 bits of arenaTypeID)
        ('gameplayId', 0),      # the gameplay on the map: standard, encounter, assault, ... (the high bits)
        ('battleType', 0),      # kind of battle: random, training, ... (constants.ARENA_GUI_TYPE)
        ('playerVehicleIndex', None),
                                # the vehicle the player entered the battle with (in a replay, the recorded player):
                                # its index in vehicleCatalog, which has the player's name and team; None when not
                                # known. The player's later vehicles are in vehicleCatalog too; each hit has the
                                # vehicles it was on
        ('startedAt', 0.0),     # when the player entered the battle, Unix time in seconds
        ('isReplay', False),    # a replay watched, not a battle played
        ('winnerTeam', None),   # the team that won, 1 or 2, DRAW_TEAM for a draw; None when not known
        ('endReason', None),    # how the battle ended (constants.FINISH_REASON); None when not known
        ('vehicleCatalog', ()), # each vehicle of each player the battle met (the player's own ones, the hits' ones),
                                # once, in the order they were met (vehicle_catalog.CatalogVehicle)
        ('receivedHits', ()),   # hits on the player's vehicle, in battle order (hits.ReceivedHit)
        ('dealtHits', ()),      # the player's hits on other vehicles, in battle order (hits.DealtHit)
    )
    NESTED = {'vehicleCatalog': CatalogVehicle, 'receivedHits': ReceivedHit, 'dealtHits': DealtHit}
    __slots__ = tuple(name for name, _ in FIELDS)

    @property
    def isOldFormat(self):
        # Read from a file of an old format: its file is never written over.
        return self.formatVersion < FORMAT_VERSION

    def vehicle(self, index):
        # The vehicle of vehicleCatalog at the index (playerVehicleIndex, a hit's shooterVehicleIndex or
        # targetVehicleIndex); one with nothing known for None and for an index the catalog has not (a broken file).
        if index is None or not 0 <= index < len(self.vehicleCatalog):
            return CatalogVehicle()
        return self.vehicleCatalog[index]

    @property
    def playerVehicle(self):
        # The vehicle the player entered the battle with (CatalogVehicle).
        return self.vehicle(self.playerVehicleIndex)

    @property
    def vehicleIds(self):
        # The types (intCD) of the player's vehicles of the battle, in the order of their first hits; without hits, the
        # type of the vehicle the player entered the battle with.
        hits = [(hit.time, self.vehicle(hit.targetVehicleIndex).vehicleId) for hit in self.receivedHits]
        hits.extend((hit.time, self.vehicle(hit.shooterVehicleIndex).vehicleId) for hit in self.dealtHits)
        vehicleIds = []
        for _, vehicleId in sorted(hits):
            if vehicleId and vehicleId not in vehicleIds:
                vehicleIds.append(vehicleId)
        return vehicleIds or [self.playerVehicle.vehicleId]

    def isAllyHit(self, hit):
        # A hit on a vehicle of the shooter's own team that took no damage (the client's team damage is off).
        shooter, target = self.vehicle(hit.shooterVehicleIndex), self.vehicle(hit.targetVehicleIndex)
        return shooter.team is not None and shooter.team == target.team and hit.damage == 0

    @property
    def result(self):
        # Not known while the battle is still going, or after the player left it before its end until its results come.
        if self.winnerTeam is None:
            return BattleResult.UNKNOWN
        if self.winnerTeam == DRAW_TEAM:
            return BattleResult.DRAW
        return BattleResult.WIN if self.winnerTeam == self.playerVehicle.team else BattleResult.DEFEAT


def _winnerTeam(isWinner, playerTeam):
    # Battle.winnerTeam from the battle results' isWinner: 1 the player's team won, -1 it lost, 0 a draw; None when
    # not known.
    if isWinner == 0:
        return DRAW_TEAM
    if playerTeam not in _TEAMS or isWinner not in (1, -1):
        return None
    if isWinner == 1:
        return playerTeam
    return _TEAMS[0] if playerTeam == _TEAMS[1] else _TEAMS[1]


def battleFromAvatar(player):
    # The battle the player has just entered, read from the client: its vehicle catalog starts with the player's
    # vehicle, its team and name from the avatar too, which knows them also before the arena's list has the vehicle.
    vehicle = vehicle_catalog.playerVehicle(player.arena, player.playerVehicleID)
    vehicle = vehicle.replace(playerName=vehicle.playerName or getattr(player, 'name', '') or '', team=player.team)
    return Battle(
        battleId=player.arenaUniqueID,
        mapId=player.arenaTypeID & _MAP_ID_MASK,
        gameplayId=player.arenaTypeID >> _GAMEPLAY_ID_SHIFT,
        battleType=player.arenaGuiType,
        playerVehicleIndex=0,
        startedAt=time.time(),
        isReplay=BattleReplay.isPlaying(),
        vehicleCatalog=(vehicle,),
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
        # Id of the battle the player is in, None out of battle or in a battle not kept; the arena of that battle.
        self._battleId = None
        self._arena = None
        self.onBattleLeft = Event()
        self.onResultReceived = Event()

    def install(self):
        g_playerEvents.onAvatarReady += self._onAvatarReady
        g_playerEvents.onRoundFinished += self._onRoundFinished
        g_playerEvents.onAvatarBecomeNonPlayer += self._onAvatarBecomeNonPlayer
        g_messengerEvents.serviceChannel.onChatMessageReceived += self._onServiceMessage

    def uninstall(self):
        self._stopFollowing()
        g_messengerEvents.serviceChannel.onChatMessageReceived -= self._onServiceMessage
        g_playerEvents.onAvatarBecomeNonPlayer -= self._onAvatarBecomeNonPlayer
        g_playerEvents.onRoundFinished -= self._onRoundFinished
        g_playerEvents.onAvatarReady -= self._onAvatarReady

    def _onServiceMessage(self, clientID, message):
        # The battle results the server puts into the service channel when a battle ends, also of a battle the player
        # has left before its end (its round's end did not come); the client's AwardController reads them the same
        # way. They give the winner of a battle in the store that has none yet.
        if message is None or message.type != SYS_MESSAGE_TYPE.battleResults.index() or not message.data:
            return
        try:
            data = message.data
            battle = self._store.getBattle(data.get('arenaUniqueID'))
            if battle is None or battle.winnerTeam is not None:
                return
            winnerTeam = _winnerTeam(data.get('isWinner'), battle.playerVehicle.team or data.get('team'))
            if winnerTeam is None:
                return
            battle = battle.replace(winnerTeam=winnerTeam)
        except Exception:
            _logger.exception('battles: cannot read the battle results')
            return
        # The service channel's event passes an error on to the client and its other listeners miss the message.
        try:
            self._store.update(battle)
            self.onResultReceived(battle)
        except Exception:
            _logger.exception('battles: cannot keep the battle results')

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
        self._arena = BigWorld.player().arena
        if self._arena is not None:
            self._arena.onVehicleUpdated += self._onVehicleUpdated

    def _onVehicleUpdated(self, vehicleID):
        # The arena tells the player's new vehicle before the client shows it: one more vehicle in the catalog; the
        # player's vehicle (playerVehicleIndex) stays the one the player entered the battle with.
        battle = self._store.getBattle(self._battleId) if self._battleId is not None else None
        if battle is None or vehicleID != getattr(BigWorld.player(), 'playerVehicleID', None):
            return
        catalog, _ = vehicle_catalog.withVehicle(battle.vehicleCatalog,
                                                 vehicle_catalog.playerVehicle(self._arena, vehicleID))
        if catalog != battle.vehicleCatalog:
            self._store.update(battle.replace(vehicleCatalog=catalog))

    def _stopFollowing(self):
        if self._arena is not None:
            self._arena.onVehicleUpdated -= self._onVehicleUpdated
            self._arena = None

    def _onRoundFinished(self, winnerTeam, reason, *args):
        battle = self._store.getBattle(self._battleId) if self._battleId is not None else None
        if battle is None:
            return
        battle = battle.replace(winnerTeam=winnerTeam, endReason=reason)
        self._store.update(battle)

    def _onAvatarBecomeNonPlayer(self, *args):
        self._stopFollowing()
        battle = self._store.getBattle(self._battleId) if self._battleId is not None else None
        self._battleId = None
        if battle is not None:
            self.onBattleLeft(battle)
