# -*- coding: utf-8 -*-
"""The vehicle catalog of a battle: each vehicle of each player the battle met, once (Battle.vehicleCatalog).

A player of a battle is its battlePlayerId, the client's arena vehicleID: the only key of a player that is unique in
a battle, and the same through the player's deaths, respawns and vehicle changes (.claude/rules/battle-modes.md). A
vehicle of a player is one CatalogVehicle: the player's id and the vehicle's compact descriptor. The descriptor is
always taken from the same place, the arena's list, and from the vehicle entity only when the list has none
(playerVehicle): so a vehicle has one descriptor, and the player's own one has its optional devices, which only the
arena's list has.

In the fog of war the client does not know an enemy's vehicle until it is spotted, so the vehicle can be met without
a descriptor: it is the player's vehicle met last, or a new one when the player was not met yet. Once the client tells
the descriptor, the player's vehicle without one gets it, instead of a new one; the hits that refer to it with it.

The battle and its hits refer to the vehicles by their index in the catalog (Battle.playerVehicleIndex,
Hit.shooterVehicleIndex and targetVehicleIndex; Battle.vehicle gives the vehicle of an index). A vehicle goes to the
catalog before what refers to it: the player's vehicle when the battle starts and when it changes (battles.py), the
two vehicles of a hit before the hit is made (hit_collector.py).
"""
import BigWorld

from gui.mods.sagtary_armor_hits.data.hits import compactDescriptor, vehicleTypeId
from gui.mods.sagtary_armor_hits.data.record import Record


class CatalogVehicle(Record):
    FIELDS = (
        ('battlePlayerId', 0),  # the player in the battle: the client's arena vehicleID; 0 when not known; below 0
                                # in a battle read from an older file, which did not keep it
        ('playerName', ''),     # the player's name; '' when not known
        ('team', None),         # the player's team (the arena's), None when not known
        ('vehicleDescriptor', ''),
                                # the vehicle's compact descriptor (type, modules; the player's own one also its
                                # optional devices), hex; '' when not known yet
    )
    __slots__ = tuple(name for name, _ in FIELDS)

    @property
    def vehicleId(self):
        # The vehicle's type (intCD), from its compact descriptor; 0 when not known.
        return vehicleTypeId(self.vehicleDescriptor)


def playerVehicle(arena, vehicleID):
    # The vehicle of a player (the client's arena vehicleID) as it is now: its descriptor from the arena's list (the
    # player's own one with its optional devices), from the vehicle the client sees only when the list has none (the
    # fog of war).
    arenaVehicle = (arena.vehicles.get(vehicleID) or {}) if arena is not None else {}
    descriptor = arenaVehicle.get('vehicleType') or getattr(BigWorld.entities.get(vehicleID), 'typeDescriptor', None)
    return CatalogVehicle(battlePlayerId=vehicleID, playerName=arenaVehicle.get('name') or '',
                          team=arenaVehicle.get('team'), vehicleDescriptor=compactDescriptor(descriptor))


def withVehicle(catalog, vehicle):
    # (catalog, index): the catalog (a tuple of CatalogVehicle) with the vehicle as met now, and its index there.
    playerIndexes = [index for index, known in enumerate(catalog) if known.battlePlayerId == vehicle.battlePlayerId]
    if not vehicle.vehicleDescriptor:
        # The vehicle is not known now: the player's vehicle met last.
        if playerIndexes:
            return catalog, playerIndexes[-1]
        return catalog + (vehicle,), len(catalog)
    for index in playerIndexes:
        if catalog[index].vehicleDescriptor == vehicle.vehicleDescriptor:
            return catalog, index
    for index in playerIndexes:
        if not catalog[index].vehicleDescriptor:
            # The player's vehicle met before it was known.
            known = catalog[index].replace(vehicleDescriptor=vehicle.vehicleDescriptor)
            return catalog[:index] + (known,) + catalog[index + 1:], index
    return catalog + (vehicle,), len(catalog)
