# -*- coding: utf-8 -*-
"""Names and classes of vehicles and names of maps by their ids, read from the client's caches, and texts of the
client, in the client language.

A Battle keeps only the ids (vehicleId, mapId), so a battle read from a file is shown in the current client language.
None when the client does not have the vehicle or the map (removed in an update).
"""
import ArenaType
from helpers import i18n
from items import vehicles


# The maps training dummies ('ussr:R72_T150_MapsTraining_Dummy_HT_2') are named by their class only ("Heavy Tank");
# the vehicle they copy ('ussr:R72_T150') has the name.
_MAPS_TRAINING_MARK = '_MapsTraining_'


def _shownVehicleType(vehicleId):
    # The vehicle type of the vehicle (intCD) to show: the copied vehicle for a maps training dummy.
    vehicleType = vehicles.getVehicleType(vehicleId)
    if _MAPS_TRAINING_MARK in vehicleType.name:
        try:
            nationID, typeID = vehicles.g_list.getIDsByName(copiedName(vehicleType.name))
            vehicleType = vehicles.g_cache.vehicle(nationID, typeID)
        except Exception:
            pass
    return vehicleType


def vehicleShortName(vehicleId):
    # The short name of the vehicle (intCD), or None.
    if not vehicleId:
        return None
    try:
        return _shownVehicleType(vehicleId).shortUserString
    except Exception:
        return None


def shownVehicleId(vehicleId):
    # The intCD of the vehicle to show in the hangar for the vehicle (intCD), or None: the copied vehicle for a maps
    # training dummy.
    if not vehicleId:
        return None
    try:
        return _shownVehicleType(vehicleId).compactDescr
    except Exception:
        return None


def copiedName(name):
    # The name of the vehicle's or module's original: a maps training copy's module 'PzVI_Porsche_Turm_MapsTraining_
    # Player_HT_2' copies 'PzVI_Porsche_Turm'.
    return name.split(_MAPS_TRAINING_MARK)[0]


def shownVehicleDescr(vehicleId, descr):
    # The compact descriptor (bytes) of the vehicle to show in the hangar for the vehicle (intCD) with its modules
    # (compact descriptor, hex), or None for the default modules. A maps training copy is shown as the vehicle it
    # copies with the modules its own modules copy (the same models, so the hit points fit).
    if not descr:
        return None
    try:
        descr = descr.decode('hex')
        shownType = _shownVehicleType(vehicleId)
        if shownType.compactDescr == vehicleId:
            return descr
        copy = vehicles.VehicleDescr(compactDescr=descr)
        shown = vehicles.VehicleDescr(typeID=shownType.id)
    except Exception:
        return None
    for module, choices in ((copy.chassis, shownType.chassis), (copy.engine, shownType.engines),
                            (copy.fuelTank, shownType.fuelTanks), (copy.radio, shownType.radios)):
        for choice in choices:
            if choice.name == copiedName(module.name):
                try:
                    shown.installComponent(choice.compactDescr)
                except Exception:
                    pass
    for turret in shownType.turrets[0]:
        if turret.name != copiedName(copy.turret.name):
            continue
        for gun in turret.guns:
            if gun.name == copiedName(copy.gun.name):
                try:
                    shown.installTurret(turret.compactDescr, gun.compactDescr)
                except Exception:
                    pass
    return shown.makeCompactDescr()


def mapNames(mapId):
    # (map name, map folder name) of the map (geometryID), or None. The folder names the map images.
    if not mapId or mapId not in ArenaType.g_geometryCache:
        return None
    try:
        geometry = ArenaType.g_geometryCache[mapId]
        return i18n.makeString(geometry.name), geometry.geometryName
    except Exception:
        return None


def vehicleClass(vehicleId):
    # The vehicle class tag ('lightTank', 'mediumTank', 'heavyTank', 'AT-SPG', 'SPG'), or None.
    if not vehicleId:
        return None
    try:
        return vehicles.getVehicleClass(vehicleId)
    except Exception:
        return None


def clientText(key):
    # The client's translation of a '#file:key' text, or None when the client does not have it.
    text = i18n.makeString(key)
    return text if text and text != key else None
