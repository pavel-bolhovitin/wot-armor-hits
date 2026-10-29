# -*- coding: utf-8 -*-
"""Lobby state of the hits screen: a page of the client's lobby navigation that loads the screen's view by its alias.

The state has no LobbyStateFlags.HANGAR flag, so the lobby shows the page header (the hangar button, the page title,
the wallet) and not the full hangar header. The header's hangar button closes the screen.

The 3D scene is set like on the armor page (VehicleHubState and ArmorState of the client): the hangar vehicle moves
to the customization place (HangarCustomizationEvent.CHANGE_VEHICLE_MODEL_TRANSFORM), and the state, a subhangar
state group config provider, makes the client's SubhangarObserver activate the armor subhangar group for the size of
the vehicle, which switches the camera to the armor page camera. The view puts the vehicle of the shown hits into the
hangar (hangar_vehicle.py); the armor group is chosen for the vehicle in the hangar when the screen opens and stays
when the vehicle changes.
"""
import logging
import math

import BigWorld
from gui.Scaleform.framework.entities.View import ViewKey
from gui.lobby_state_machine.states import LobbyStateDescription, SFViewLobbyState, SubScopeSubLayerState
from gui.shared import EVENT_BUS_SCOPE, events, g_eventBus
from gui.subhangar.subhangar_observer import selectItemByTankSize
from gui.subhangar.subhangar_state_groups import CameraMover, SubhangarStateGroupConfig, \
    SubhangarStateGroupConfigProvider, SubhangarStateGroups
from helpers import dependency
from skeletons.gui.shared.utils import IHangarSpace

from gui.mods.sagtary_armor_hits.lang import text
from gui.mods.sagtary_armor_hits.views.hits.hits_view import VIEW_ALIAS

_logger = logging.getLogger('sagtary.armor_hits')

# The armor page's subhangar groups by the vehicle size (the client's ArmorState), and the size bounds in metres.
_TANK_SIZE_LOWER_BOUNDS = (float('-inf'), 5.0, 8.0)
_ARMOR_GROUPS_BY_TANK_SIZE = (SubhangarStateGroups.VehicleHubArmorSmallTank,
                              SubhangarStateGroups.VehicleHubArmorMediumTank,
                              SubhangarStateGroups.VehicleHubArmorLargeTank)


def _moveVehicleToCustomizationPlace():
    # The client's VehicleHubState.__setupTankTransformation.
    from gui.ClientHangarSpace import customizationHangarCFG
    cfg = customizationHangarCFG()
    isForwardPipeline = BigWorld.getGraphicsSetting('RENDER_PIPELINE') == 1
    yaw, pitch, roll = (math.radians(angle) for angle in cfg['v_start_angles'][:3])
    shadowYOffset = cfg['shadow_forward_y_offset'] if isForwardPipeline else cfg['shadow_deferred_y_offset']
    g_eventBus.handleEvent(events.HangarCustomizationEvent(
        events.HangarCustomizationEvent.CHANGE_VEHICLE_MODEL_TRANSFORM,
        ctx={'targetPos': cfg['v_start_pos'], 'rotateYPR': (yaw, pitch, roll), 'shadowYOffset': shadowYOffset}),
        scope=EVENT_BUS_SCOPE.LOBBY)


@SubScopeSubLayerState.parentOf
class HitsState(SFViewLobbyState, SubhangarStateGroupConfigProvider):
    STATE_ID = 'sagtaryArmorHits'
    VIEW_KEY = ViewKey(VIEW_ALIAS)
    __hangarSpace = dependency.descriptor(IHangarSpace)

    def getNavigationDescription(self):
        return LobbyStateDescription(title=text('lobbyButton/name'))

    def getSubhangarStateGroupConfig(self):
        armorGroup = selectItemByTankSize(_TANK_SIZE_LOWER_BOUNDS, _ARMOR_GROUPS_BY_TANK_SIZE,
                                          SubhangarStateGroups.VehicleHubArmorMediumTank)
        # The camera goes to the armor camera at once, like the first move of the client's VehicleHubCameraMover;
        # a smooth move would fly it from the hangar up to the customization place.
        return SubhangarStateGroupConfig((SubhangarStateGroups.VehicleHub, armorGroup), CameraMover())

    def _onEntered(self, event):
        super(HitsState, self)._onEntered(event)
        try:
            _moveVehicleToCustomizationPlace()
        except Exception:
            _logger.exception('hits screen: cannot move the vehicle')

    def _onExited(self):
        try:
            g_eventBus.handleEvent(events.HangarCustomizationEvent(
                events.HangarCustomizationEvent.RESET_VEHICLE_MODEL_TRANSFORM), scope=EVENT_BUS_SCOPE.LOBBY)
            if self.__hangarSpace.spaceInited:
                self.__hangarSpace.space.turretAndGunAngles.reset()
        except Exception:
            _logger.exception('hits screen: cannot put the vehicle back')
        super(HitsState, self)._onExited()
