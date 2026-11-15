# -*- coding: utf-8 -*-
"""Battle file format 3 to format 4.

Format 4 keeps each vehicle of each player the battle met once, in its vehicle catalog (vehicleCatalog: battlePlayerId,
playerName, team, vehicleDescriptor), and refers to them by their index there: the vehicle the player entered the
battle with (playerVehicleIndex) and the two vehicles of a hit (shooterVehicleIndex, targetVehicleIndex). Format 3
keeps the vehicles themselves: the player's (vehicleDescriptor, playerName, playerTeam) and a hit's (shooter, target:
vehicleDescriptor, playerName, team).

The catalog is made of them: the same player, team and descriptor are one vehicle. Format 3 does not know the
client's id of a player (battlePlayerId, the arena's vehicleID), so each player gets one here, -1, -2, ... in the
order met (the client's are above 0): a player is a name and a team, a vehicle without a name is a player of its own.
Format 3 keeps the player's last vehicle, not the one the player entered the battle with: it is the player's vehicle
here. A vehicle with nothing known (a shooter the client did not know) gets no index: the default.
"""

# The two vehicles of a hit in format 3 and their index fields in format 4.
_HIT_VEHICLES = (('shooter', 'shooterVehicleIndex'), ('target', 'targetVehicleIndex'))


def _text(value):
    return value if isinstance(value, basestring) else ''


def _team(value):
    return value if isinstance(value, (int, long)) and not isinstance(value, bool) else None


class _Catalog(object):

    def __init__(self):
        self.vehicles = []
        # {(name, team, descriptor): index in vehicles}
        self._indexes = {}
        # {(name, team) of a player, (name, team, descriptor) of a vehicle without a name: battlePlayerId}
        self._playerIds = {}

    def index(self, name, team, descriptor):
        # The vehicle's index, added when new; None when nothing of it is known.
        key = (_text(name), _team(team), _text(descriptor))
        if key == ('', None, ''):
            return None
        if key not in self._indexes:
            player = key[:2] if key[0] else key
            if player not in self._playerIds:
                self._playerIds[player] = -(len(self._playerIds) + 1)
            self._indexes[key] = len(self.vehicles)
            self.vehicles.append({'battlePlayerId': self._playerIds[player], 'playerName': key[0], 'team': key[1],
                                  'vehicleDescriptor': key[2]})
        return self._indexes[key]


def _hit(hit, catalog):
    hit = dict(hit)
    for name, indexName in _HIT_VEHICLES:
        vehicle = hit.pop(name, None)
        if isinstance(vehicle, dict):
            hit[indexName] = catalog.index(vehicle.get('playerName'), vehicle.get('team'),
                                           vehicle.get('vehicleDescriptor'))
    return hit


def convert(data):
    data = dict(data)
    catalog = _Catalog()
    data['playerVehicleIndex'] = catalog.index(data.pop('playerName', None), data.pop('playerTeam', None),
                                               data.pop('vehicleDescriptor', None))
    for field in ('receivedHits', 'dealtHits'):
        hits = data.get(field)
        if isinstance(hits, list):
            data[field] = [_hit(hit, catalog) if isinstance(hit, dict) else hit for hit in hits]
    data['vehicleCatalog'] = catalog.vehicles
    return data
