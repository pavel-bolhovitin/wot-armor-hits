# -*- coding: utf-8 -*-
"""The hangar camera of the hits screen: the one place of the mod that works with the camera.

The camera of the screen is the armor page's camera (Armor_Inspector_Camera). The screen's lobby state gives the
client's SubhangarObserver the subhangar groups of armorCameraConfig, like the client's ArmorState: VehicleHub and
the armor group for the size of the vehicle in the hangar when the screen opens (it stays when the vehicle changes);
the armor group switches the camera to the armor camera, at once, like the first move of the client's
VehicleHubCameraMover (a smooth move would fly it from the hangar up to the customization place).

HangarCamera keeps the client's camera manager (HangarCameraSystem, one a hangar space; the client calls it
cameraManager too): it takes it the first time it is needed and keeps it until the screen closes or the hangar space
goes (the client closes the space before the screen when it quits). The other parts of the screen ask HangarCamera to
move the camera; they do not take the camera manager themselves. The page's mouse over the scene goes to the camera
like the client's SceneWrapper: drags and wheel steps (moveByMouse) as CameraRelatedEvents.LOBBY_VIEW_MOUSE_MOVE, the
mouse over the scene (setMouseOverScene) as NOTIFY_CURSOR_OVER_3DSCENE.

Shells often come from below, but the hangar camera stops at the floor (its collisions) and does not look from under
the vehicle (its orbit's pitch limits, about -80 to -4 degrees). While the screen is open the camera's collisions are
off and its pitch limits are widened to _PITCH both ways. The camera manager sets them again when it sets a camera up
(another vehicle, a camera switch), so they are set again then; when the screen closes they are put back as they
were. The camera is the engine's current one (BigWorld.camera()), the camera manager's own while it does not fly
between two cameras (isCameraSwitching); the pitch limits are in the camera manager's private mouse params, as the
client has no API for them (the mouse and moveCamera keep the camera within them).

The shooter view (lookAlong): the camera looks along a shell at a point, _SHOOTER_DISTANCE metres behind it, and flies
there in _FLIGHT seconds (HangarCameraSystem.moveCamera). reset puts the camera back to its place
(resetCameraTarget). Closing the screen after the shooter view puts the camera back at once, else the hangar keeps
turning around the hit.

The hangar itself stays: the space items' visibility mask hides only the items tagged with a hangar's layers and
regions, not the hangar; taking the hangar's geometry mapping out of the space (BigWorld.delSpaceGeometryMapping)
hides it, but the hangar then waits for its space forever and the client crashes when it leaves the space.
"""
import logging

import BigWorld
import CGF
import Math
from cgf_components.hangar_camera_manager import HangarCameraSystem
from gui.hangar_cameras.hangar_camera_common import CameraRelatedEvents
from gui.shared import EVENT_BUS_SCOPE, events, g_eventBus
from gui.subhangar.subhangar_observer import selectItemByTankSize
from gui.subhangar.subhangar_state_groups import CameraMover, SubhangarStateGroupConfig, SubhangarStateGroups
from helpers import dependency
from skeletons.gui.shared.utils import IHangarSpace

_logger = logging.getLogger('sagtary.armor_hits')

# The armor page's subhangar groups by the vehicle size (the client's ArmorState), and the size bounds in metres.
_TANK_SIZE_LOWER_BOUNDS = (float('-inf'), 5.0, 8.0)
_ARMOR_GROUPS_BY_TANK_SIZE = (SubhangarStateGroups.VehicleHubArmorSmallTank,
                              SubhangarStateGroups.VehicleHubArmorMediumTank,
                              SubhangarStateGroups.VehicleHubArmorLargeTank)
# Radians of the camera's pitch limits both ways while the screen is open: almost straight up and down.
_PITCH = 1.5
# The shooter view: the camera's distance to the point in metres and its flight in seconds.
_SHOOTER_DISTANCE = 6.0
_FLIGHT = 0.5


def armorCameraConfig():
    # The subhangar groups of the screen, which switch the camera to the armor camera at once.
    armorGroup = selectItemByTankSize(_TANK_SIZE_LOWER_BOUNDS, _ARMOR_GROUPS_BY_TANK_SIZE,
                                      SubhangarStateGroups.VehicleHubArmorMediumTank)
    return SubhangarStateGroupConfig((SubhangarStateGroups.VehicleHub, armorGroup), CameraMover())


class HangarCamera(object):
    __hangarSpace = dependency.descriptor(IHangarSpace)

    def __init__(self):
        # The client's camera manager: None until it is first needed, and after the screen or the hangar space.
        self.__cameraManager = None
        # The camera manager's pitch limits before the screen; None before they are set.
        self._pitch = None
        # The camera was moved by lookAlong and not put back since.
        self.moved = False

    def init(self):
        _logger.info('hangar camera: screen opened')
        self.__hangarSpace.onVehicleChanged += self._onVehicleChanged
        self.__hangarSpace.onSpaceDestroy += self._onSpaceDestroy
        self._freeCamera()

    def fini(self):
        _logger.info('hangar camera: screen closes, moved %s, pitch limits to put back %s', self.moved, self._pitch)
        self.__hangarSpace.onSpaceDestroy -= self._onSpaceDestroy
        self.__hangarSpace.onVehicleChanged -= self._onVehicleChanged
        cameraManager = self.__cameraManager
        if cameraManager is not None:
            if self.moved:
                cameraManager.resetCameraTarget(duration=0)
            self._setCamera(cameraManager, True, self._pitch)
        self._forget()
        self._pitch = None
        self.moved = False

    def lookAlong(self, position, direction):
        # The shooter view: the camera behind the shell, looking along it at the point.
        cameraManager = self._getCameraManager()
        _logger.info('hangar camera: look along the shell at (%.2f, %.2f, %.2f), camera manager %s', position.x,
                     position.y, position.z, cameraManager is not None)
        if cameraManager is None:
            return
        cameraManager.moveCamera(targetPos=position, yaw=direction.yaw, pitch=-direction.pitch,
                                 distance=_SHOOTER_DISTANCE, duration=_FLIGHT)
        self.moved = True

    def reset(self, duration=_FLIGHT):
        # The camera back to its place.
        self.moved = False
        cameraManager = self._getCameraManager()
        _logger.info('hangar camera: back to its place in %.1f s, camera manager %s', duration,
                     cameraManager is not None)
        if cameraManager is not None:
            cameraManager.resetCameraTarget(duration=duration)

    @staticmethod
    def moveByMouse(dx, dy, dz):
        # Same as the client's Vehicle Hub view: the camera turns and zooms by these deltas.
        g_eventBus.handleEvent(CameraRelatedEvents(CameraRelatedEvents.LOBBY_VIEW_MOUSE_MOVE, ctx={
            'dx': dx, 'dy': dy, 'dz': dz}), EVENT_BUS_SCOPE.GLOBAL)

    @staticmethod
    def setMouseOverScene(isOver):
        g_eventBus.handleEvent(events.LobbySimpleEvent(events.LobbySimpleEvent.NOTIFY_CURSOR_OVER_3DSCENE, ctx={
            'isOver3dScene': isOver}))

    def _getCameraManager(self):
        # The client's camera manager, taken the first time and kept; None without the hangar space.
        if self.__cameraManager is None:
            spaceID = self.__hangarSpace.spaceID
            cameraManager = CGF.getSystem(spaceID, HangarCameraSystem) if spaceID is not None else None
            _logger.info('hangar camera: camera manager taken: %s', cameraManager is not None)
            if cameraManager is not None:
                cameraManager.onCameraSwitched += self._onCameraSwitched
                self.__cameraManager = cameraManager
        return self.__cameraManager

    def _forget(self):
        cameraManager, self.__cameraManager = self.__cameraManager, None
        if cameraManager is not None:
            _logger.info('hangar camera: camera manager forgotten')
            cameraManager.onCameraSwitched -= self._onCameraSwitched

    def _onSpaceDestroy(self, *args):
        # The camera manager goes with the space: not used after that.
        _logger.info('hangar camera: hangar space destroyed')
        self._forget()

    def _onCameraSwitched(self, cameraName):
        _logger.info('hangar camera: switched to %s', cameraName)
        self._freeCamera()

    def _onVehicleChanged(self, *args):
        _logger.info('hangar camera: vehicle changed')
        self._freeCamera()

    def _freeCamera(self):
        cameraManager = self._getCameraManager()
        if cameraManager is None:
            return
        params = getattr(cameraManager, '_HangarCameraSystem__mouseMoveParams', None)
        if params is not None and self._pitch is None:
            self._pitch = Math.Vector2(params.pitchConstraints)
        self._setCamera(cameraManager, False, Math.Vector2(-_PITCH, _PITCH))

    @staticmethod
    def _setCamera(cameraManager, collisions, pitch):
        # The camera's collisions on or off, its pitch limits (None: as they are).
        camera = None if cameraManager.isCameraSwitching() else BigWorld.camera()
        params = getattr(cameraManager, '_HangarCameraSystem__mouseMoveParams', None)
        _logger.info('hangar camera: collisions %s on %s, pitch limits %s -> %s', collisions,
                     type(camera).__name__ if camera is not None else 'none: flying',
                     params.pitchConstraints if params is not None else None, pitch)
        try:
            if camera is not None:
                camera.setDynamicCollisions(collisions)
                camera.enableCollisions(collisions)
            if params is not None and pitch is not None:
                params.pitchConstraints = Math.Vector2(pitch)
        except Exception:
            _logger.exception('hangar camera: cannot set the camera')
