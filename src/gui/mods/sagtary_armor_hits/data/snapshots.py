# -*- coding: utf-8 -*-
"""Snapshots of a battle: where the vehicles the client knew were at a hit, for the minimap (Battle.snapshots).

Each hit has one, taken when the hit is made (hit_collector.py), and refers to it by its index (Hit.snapshotIndex).
It keeps only what the client knows at that moment, as the client's own minimap finds it
(gui.battle_control.matrix_factory): a vehicle the client sees, its entity in the area around the player, where it
is exactly and its hull and turret headings; else a vehicle on the minimap only (arena.positions: allies, enemies
spotted far away), where it is roughly, without height. A vehicle the client does not know of then and a destroyed
one are not in it. Its vehicles go to the battle's vehicle catalog before it, so it refers to them by their index
there (vehicle_catalog.py).

All the vehicles have the same fields, None for what is not known. Positions are in the world's metres, headings in
the world's radians, as the client has them, to 6 decimals (about all its 32-bit floats have): the minimap places
them by its map's bounding box in the client (ArenaType: the battle's mapId and gameplayId), so the snapshot keeps
none.
"""
from gui.mods.sagtary_armor_hits.data.record import Record


class PositionSource(object):
    # Where the client knew a vehicle's position from.
    VISIBLE = 'visible'     # its entity: the client sees it, the position is exact
    MINIMAP = 'minimap'     # the arena's positions: on the minimap only, rough, height 0


class SnapshotVehicle(Record):
    FIELDS = (
        ('vehicleIndex', None), # the vehicle: its index in the battle's vehicle catalog (Battle.vehicleCatalog)
        ('position', ()),       # (x, y, z) of the vehicle in the world, in metres
        ('positionSource', ''), # where the client knew the position from (PositionSource)
        ('hullYaw', None),      # radians of the hull's heading in the world; None when the client does not see it
        ('turretYaw', None),    # radians of the turret's heading in the world (the hull's and the turret's turn on
                                # it); None when the client does not see it or has not its model
        ('cameraYaw', None),    # radians of the camera's heading in the world, on the player's vehicle only; None
    )
    KINDS = {'hullYaw': 0.0, 'turretYaw': 0.0, 'cameraYaw': 0.0}
    __slots__ = tuple(name for name, _ in FIELDS)


class Snapshot(Record):
    FIELDS = (
        ('vehicles', ()),       # the vehicles the client knew, by their index in the catalog (SnapshotVehicle)
    )
    NESTED = {'vehicles': SnapshotVehicle}
    __slots__ = tuple(name for name, _ in FIELDS)
