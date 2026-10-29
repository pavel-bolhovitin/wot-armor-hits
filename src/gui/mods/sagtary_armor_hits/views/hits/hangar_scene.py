# -*- coding: utf-8 -*-
"""The hangar camera while the hits screen is open: free to go under the floor and to look from below.

Shells often come from below, but the hangar camera stops at the floor (its collisions) and does not look from under
the vehicle (its orbit's pitch limits, about -80 to -4 degrees). HangarScenePresenter, while the screen is open, turns
the camera's collisions off and widens its pitch limits to _PITCH both ways (HangarCameraSystem's camera and mouse
params). The camera system sets them again when it sets a camera up (another vehicle, a camera switch), so they are
set again then; when the screen closes they are put back as they were.

The hangar itself stays: the space items' visibility mask hides only the items tagged with a hangar's layers and
regions, not the hangar; taking the hangar's geometry mapping out of the space (BigWorld.delSpaceGeometryMapping)
hides it, but the hangar then waits for its space forever and the client crashes when it leaves the space.
"""
import logging

import CGF
import Math
from cgf_components.hangar_camera_manager import HangarCameraSystem
from helpers import dependency
from skeletons.gui.shared.utils import IHangarSpace

_logger = logging.getLogger('sagtary.armor_hits')

# Radians of the camera's pitch limits both ways while the screen is open: almost straight up and down.
_PITCH = 1.5


class HangarScenePresenter(object):
    __hangarSpace = dependency.descriptor(IHangarSpace)

    def __init__(self):
        # The camera system's pitch limits before the screen; None before they are set.
        self._pitch = None
        self._cameraSystem = None

    def init(self):
        spaceID = self.__hangarSpace.spaceID
        if spaceID is None:
            return
        self._cameraSystem = CGF.getSystem(spaceID, HangarCameraSystem)
        if self._cameraSystem is not None:
            self._cameraSystem.onCameraSwitched += self._freeCamera
        self.__hangarSpace.onVehicleChanged += self._freeCamera
        self._freeCamera()

    def fini(self):
        self.__hangarSpace.onVehicleChanged -= self._freeCamera
        cameraSystem, self._cameraSystem = self._cameraSystem, None
        if cameraSystem is not None:
            cameraSystem.onCameraSwitched -= self._freeCamera
            self._setCamera(cameraSystem, True, self._pitch)
        self._pitch = None

    def _freeCamera(self, *args):
        cameraSystem = self._cameraSystem
        if cameraSystem is None:
            return
        params = getattr(cameraSystem, '_HangarCameraSystem__mouseMoveParams', None)
        if params is not None and self._pitch is None:
            self._pitch = Math.Vector2(params.pitchConstraints)
        self._setCamera(cameraSystem, False, Math.Vector2(-_PITCH, _PITCH))

    @staticmethod
    def _setCamera(cameraSystem, collisions, pitch):
        # The camera's collisions on or off, its pitch limits (None: as they are); the client's private fields.
        camera = getattr(cameraSystem, '_HangarCameraSystem__cam', None)
        params = getattr(cameraSystem, '_HangarCameraSystem__mouseMoveParams', None)
        try:
            if camera is not None:
                camera.setDynamicCollisions(collisions)
                camera.enableCollisions(collisions)
            if params is not None and pitch is not None:
                params.pitchConstraints = Math.Vector2(pitch)
        except Exception:
            _logger.exception('hangar scene: cannot set the camera')
