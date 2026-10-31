# -*- coding: utf-8 -*-
"""Hangar vehicle of the hits screen: the vehicle the hits panel shows the hits on.

HangarVehiclePresenter puts the vehicle into the hangar like the client's Vehicle Hub does, as the preview vehicle
(g_currentPreviewVehicle): on the received side the player's vehicle of the battle, on the dealt side the vehicle of
the chosen hit. The vehicle has the modules it had in the battle (its compact descriptor), as the hit points are on
them; a battle recorded without it shows the default modules. No vehicle has cosmetics, the player's own neither: no
camouflage, paint, decals or style, only the national emblems (the client's empty outfit; without an outfit the
client puts a style locked on the vehicle), and no marks of excellence on the gun: the client draws there the
player's own marks of the vehicle type, so while the screen is open the hangar vehicle's method that gives them
(HangarVehicleAppearance._getThisVehicleDossierInsigniaRank) gives none. Without a vehicle to show (no battles, no
hits on the dealt side, a vehicle the client does not have) the hangar is empty (HangarSpace.removeVehicle, as the
client's vehicle preview does before it loads its own). When the screen closes, the hangar shows the current vehicle
again.
"""
import logging

from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from helpers import dependency
from skeletons.gui.customization import ICustomizationService
from skeletons.gui.shared import IItemsCache
from skeletons.gui.shared.utils import IHangarSpace

from gui.mods.sagtary_armor_hits.data.client_names import shownVehicleDescr, shownVehicleId
from gui.mods.sagtary_armor_hits.views.hits.hits_panel import DEALT

_logger = logging.getLogger('sagtary.armor_hits')

# What the presenter shows instead of a vehicle id: no vehicle at all.
_NO_VEHICLE = 'none'
# The hangar vehicle's method that gives the marks of excellence on its gun.
_MARKS_ON_GUN = '_getThisVehicleDossierInsigniaRank'


def _noMarksOnGun(appearance):
    return 0


def _shownVehicle(vehicleId, descr):
    # (intCD, compact descriptor or None) to show; a maps training copy is shown as the vehicle it copies, with the
    # modules its own modules copy.
    shownId = shownVehicleId(vehicleId)
    if shownId is None:
        return None
    return shownId, shownVehicleDescr(vehicleId, descr)


def hitsVehicle(battle, side, hit):
    # The vehicle the hits are on: (intCD, compact descriptor or None); _NO_VEHICLE without one: no battle, no hits on
    # the dealt side, a vehicle the client does not have.
    if battle is None:
        return _NO_VEHICLE
    if side == DEALT:
        if hit is None:
            return _NO_VEHICLE
        return _shownVehicle(hit.vehicleId, hit.vehicleDescriptor) or _NO_VEHICLE
    return _shownVehicle(battle.vehicleId, battle.vehicleDescriptor) or _NO_VEHICLE


class HangarVehiclePresenter(object):
    __itemsCache = dependency.descriptor(IItemsCache)
    __hangarSpace = dependency.descriptor(IHangarSpace)
    __customizationService = dependency.descriptor(ICustomizationService)

    def __init__(self, hitsPanel):
        self._hitsPanel = hitsPanel
        # What the presenter shows: (intCD, compact descriptor or None), _NO_VEHICLE, or None before it has shown
        # anything (the hangar shows the current vehicle).
        self._vehicle = None
        # The last vehicle put into the hangar.
        self._lastShown = None
        # The client's method of the marks on the gun, while the screen puts none there.
        self._marksOnGun = None

    def init(self):
        marksOnGun = vars(HangarVehicleAppearance).get(_MARKS_ON_GUN)
        if marksOnGun is not None and marksOnGun is not _noMarksOnGun:
            self._marksOnGun = marksOnGun
            setattr(HangarVehicleAppearance, _MARKS_ON_GUN, _noMarksOnGun)
        self._hitsPanel.onChanged += self._update
        self._update()

    def fini(self):
        # The marks come back before the hangar loads the current vehicle again.
        if self._marksOnGun is not None and vars(HangarVehicleAppearance).get(_MARKS_ON_GUN) is _noMarksOnGun:
            setattr(HangarVehicleAppearance, _MARKS_ON_GUN, self._marksOnGun)
        self._marksOnGun = None
        self._hitsPanel.onChanged -= self._update
        self._hitsPanel = None
        if self._vehicle is None:
            return
        self._vehicle = None
        try:
            if g_currentPreviewVehicle.isPresent():
                g_currentPreviewVehicle.selectNoVehicle()
            else:
                g_currentVehicle.refreshModel()
        except Exception:
            _logger.exception('hangar vehicle: cannot show the current vehicle')

    def _update(self):
        vehicle = hitsVehicle(*self._hitsPanel.selection)
        if vehicle == self._vehicle:
            return
        previous, self._vehicle = self._vehicle, vehicle
        try:
            if vehicle == _NO_VEHICLE:
                self.__hangarSpace.removeVehicle()
            else:
                self._show(vehicle, previous)
        except Exception:
            _logger.exception('hangar vehicle: cannot show %s', vehicle)

    def _show(self, vehicle, previous):
        # The client's Vehicle Hub (_VehicleHubStatesObserver.__setupPreviewTank); no dark background behind the
        # loading spinner, as the screen stays.
        vehicleId, strCD = vehicle
        item = self.__itemsCache.items.getItemByCD(vehicleId)
        if item.isInInventory:
            strCD = strCD or item.strCD
        outfit = self.__customizationService.getEmptyOutfitWithNationalEmblems(
            vehicleCD=strCD or item.descriptor.makeCompactDescr())
        if g_currentPreviewVehicle.intCD == vehicleId:
            if previous == _NO_VEHICLE and self._lastShown == vehicle:
                # Still the preview vehicle, its model removed for no hits: the client does not load the same
                # vehicle again by itself.
                self.__hangarSpace.updatePreviewVehicle(g_currentPreviewVehicle.item, outfit, showWaitingBg=False)
                return
            # The same vehicle with other modules: the client loads it again only after another selection.
            g_currentPreviewVehicle.selectNoVehicle()
        self._lastShown = vehicle
        g_currentPreviewVehicle.selectVehicle(vehicleId, vehicleStrCD=strCD, outfit=outfit, showWaitingBg=False)
