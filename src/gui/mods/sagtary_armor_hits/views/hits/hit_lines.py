# -*- coding: utf-8 -*-
"""Hit lines of the hits screen: the shells' ways of the hits, drawn in the 3D scene over the hangar vehicle, and
the shooter view.

HitLinesPresenter draws on the vehicle the hangar shows (hangar_vehicle.py) the way of the hit the hits panel has
chosen and, when the scene panel asks for all lines, the ways of the other hits the panel shows. A way (Way) is drawn
as hit_way.py tells, the chosen hit's more marked than the others'. The shapes are drawn with the client's debug
drawer (scene_lines.py): over the client's armor overlay, hidden behind the vehicle.

With the shooter view on, the hangar camera looks along the chosen hit's shell at its first point
(HangarCameraSystem.moveCamera); turned off, the camera goes back to its place (resetCameraTarget). The scene panel's
reset puts the camera back the same way: behind the shell with the shooter view on, else to its place. Closing the
screen with the shooter view on puts the camera back to its place at once, else the hangar keeps turning around the hit.

When it draws: a hit is chosen and the hangar already shows its vehicle, loaded: at once; otherwise the hangar
vehicle presenter has asked for the vehicle, and the lines are drawn when the hangar tells it has loaded it
(HangarSpace.onVehicleChanged; the parts of the vehicle are in their places then). The lines are removed when the
hangar starts to change the vehicle (onVehicleChangeStarted) and drawn again when the hits or the choices change.

Before the lines are drawn, the hangar vehicle turns its turret and gun as the chosen hit's vehicle had them at the hit
(Hit.vehiclePose), the way the client's armor screen turns them (armor_sub_presenter: the turret rotator, the gun's
angle); without a chosen hit or its pose they go back to the hangar's own pose. A fixed turret or gun stays. A point
and the shell's direction are in their part's space and are drawn by the part's node: they turn with it. The parts'
nodes take the new pose when a next frame is drawn, sometimes after the lines are first put, so the lines are put
again on every frame by the nodes as they are then (SceneLines.follow): they follow the parts. When the chosen hit's
first point moves so, the shot panel is told again (onDrawn) and the shooter view's camera flies to it. The other
hits' lines are drawn in the chosen hit's pose.

The way of a shell, from its points on the vehicle's own parts (Hit.vehiclePoints): a piece of _LEAD metres before
the first point, along the shell's direction there; a piece to the next point after a ricochet or spaced armor,
where the shell goes on (it hits the vehicle again, or its main armor behind the spaced one); after a ricochet that
is the last point, a piece of _RICOCHET metres in the mirrored direction (the client does not tell where the shell
went). The way after a penetration is not drawn. A high explosive shell bursts at its first point: its other points
are what the burst hit, not its way, so only the way to the first point is drawn. A splash (Hit.splashCenter) has no
points: a sphere where the shell burst and a line from there down (or up) to the level of the vehicle's tracks, the
chassis space's ground, when it is more than _GROUND metres away: the shell burst on a slope, in a hole or on a rock
or a wall, while the hangar's floor is flat. The explosion radius is not drawn: about 10 m for a big gun, it covers
the hangar.

A point is the middle of the shell's way through the part the server sends, and the shell's direction is along that
way, like the Battle Hits mod places its hits: data only, so a point does not wait for the vehicle's collision model.
At the first point the direction is the shell's exact one from its tracer when the hit has it (Hit.shotDirection):
the server packs the way to 1/255 of the part on each axis, a degree or so off along a short way.
The model is needed only for the armor's normal at a last ricochet; it comes a few frames after the vehicle, so
without it the lines are drawn again after _NORMAL_RETRY seconds, up to _NORMAL_TRIES times, and then without the
ricochet's way out.
"""
import logging

import BigWorld
import CGF
from Event import Event
import Math
from cgf_components.hangar_camera_manager import HangarCameraSystem
from constants import SHELL_TYPES, VEHICLE_HIT_EFFECT
from helpers import dependency
from skeletons.gui.shared.utils import IHangarSpace
from vehicle_systems.tankStructure import TankPartIndexes, TankPartNames

from gui.mods.sagtary_armor_hits.views.hits.hangar_vehicle import hitsVehicle
from gui.mods.sagtary_armor_hits.views.hits.hit_way import drawWay
from gui.mods.sagtary_armor_hits.views.hits.scene_lines import SceneLines

_logger = logging.getLogger('sagtary.armor_hits')

# The colors (ARGB) of the hits' results.
# Metres: the way drawn before the first point and after a ricochet.
_LEAD = 2.5
_RICOCHET = 1.5
# Metres: a splash this close to the tracks' level has no line to it.
_GROUND = 0.02
_NORMAL_RETRY = 0.2
_NORMAL_TRIES = 5
# Metres the chosen hit's first point (or its shell direction, a unit vector) may move and be at the same place.
_SHOT_EPS = 1e-3
# The shooter view: the camera's distance to the hit point in metres and its flight in seconds.
_SHOOTER_DISTANCE = 6.0
_CAMERA_FLIGHT = 0.5
_RICOCHETS = (VEHICLE_HIT_EFFECT.INTERMEDIATE_RICOCHET, VEHICLE_HIT_EFFECT.FINAL_RICOCHET)
# The points after which the shell goes on to the next one.
_GOES_ON = _RICOCHETS + (VEHICLE_HIT_EFFECT.ARMOR_PIERCED_NO_DAMAGE,)


def _unit(vector):
    vector = Math.Vector3(vector)
    vector.normalise()
    return vector


def _partNode(compoundModel, part):
    # The world matrix of the node the client puts the hit effects of the part on (the part's space), or None.
    nodeName = TankPartNames.getActualNodeNameByPartName(TankPartIndexes.getName(part))
    try:
        return Math.Matrix(compoundModel.node(nodeName))
    except Exception:
        return None


def _armorNormal(collisions, point):
    # The armor's normal at the point in the part's space from the collision model, or None when the model does not
    # have the point (not loaded yet, other modules): the collision must lie on the shell's way.
    if collisions is None:
        return None
    start, end = Math.Vector3(*point.start), Math.Vector3(*point.end)
    try:
        distance, _, normal, _ = collisions.collideLocal(point.tankPartIndex, start, end)
    except Exception:
        return None
    if distance < 0.0 or distance > (end - start).length + 0.01 or not 0.5 < Math.Vector3(normal).length < 1.5:
        return None
    return _unit(normal)


def _setPose(entity, pose):
    # Turns the hangar vehicle's turret and gun as a hit's vehicle had them (VehiclePose), or back to the hangar's own
    # pose for None.
    appearance = getattr(entity, 'appearance', None)
    rotator = getattr(appearance, 'turretRotator', None) if appearance is not None else None
    if rotator is None:
        return
    gun = entity.typeDescriptor.gun
    if pose is None:
        appearance.rotateTurretForAnchor(None, 0.0)
        appearance.rotateGunToDefault()
        return
    if gun.staticTurretYaw is None:
        rotator.start(pose.turretYaw, 0.0)
    if gun.staticPitch is None:
        appearance.rotateGunForAngle(pose.gunPitch)


def _drawn(hit):
    # The hit has something to draw: its points or where its splash burst.
    return bool(hit.vehiclePoints or hit.splashCenter)


def _splashWay(hit, compoundModel):
    # ((burst, the chassis' axes, the line's foot on the tracks' level or None), (burst, the direction to the
    # vehicle)); (None, None) without the chassis.
    chassis = _partNode(compoundModel, TankPartIndexes.CHASSIS)
    if chassis is None:
        return None, None
    x, y, z = hit.splashCenter
    center = chassis.applyPoint(Math.Vector3(x, y, z))
    foot = chassis.applyPoint(Math.Vector3(x, 0.0, z)) if abs(y) > _GROUND else None
    axes = tuple(_unit(chassis.applyVector(axis)) for axis in (
        Math.Vector3(1, 0, 0), Math.Vector3(0, 1, 0), Math.Vector3(0, 0, 1)))
    direction = chassis.translation - center
    if direction.length < 1e-3:
        direction = chassis.applyVector(Math.Vector3(0, 0, 1))
    return (center, axes, foot), (center, _unit(direction))


class Way(object):
    # A hit's way in the scene (drawn by hit_way.py): the lead to the first point, the pieces on to the next points
    # (after a ricochet or spaced armor), a ricochet's way out, the first point and the shell's direction there, a
    # splash's mark (_splashWay).
    __slots__ = ('lead', 'links', 'out', 'first', 'splash')

    def __init__(self):
        self.lead = None
        self.links = []
        self.out = None
        self.first = None
        self.splash = None


def _wayPoints(hit):
    # The points of the hit's way: a high explosive shell bursts at its first one.
    return hit.vehiclePoints[:1] if hit.shellType == SHELL_TYPES.HIGH_EXPLOSIVE else hit.vehiclePoints


def _ricochetNormals(hits, collisions):
    # ({id of a point: the armor's normal there in its part's space} for the hits' last points that are ricochets,
    # whether one of them waits for the collision model).
    normals, waits = {}, False
    for hit in hits:
        points = _wayPoints(hit)
        if not points or points[-1].effectCode not in _RICOCHETS:
            continue
        normal = _armorNormal(collisions, points[-1])
        if normal is None:
            waits = True
        else:
            normals[id(points[-1])] = normal
    return normals, waits


def _shotMoved(old, new):
    # Whether the chosen hit's (first point, shell direction) is not where it was.
    if old is None or new is None:
        return old is not new
    return (old[0] - new[0]).length > _SHOT_EPS or (old[1] - new[1]).length > _SHOT_EPS


def _hitWay(hit, compoundModel, normals):
    # The hit's Way by the parts' nodes as they are now; normals: the armor's normals of _ricochetNormals.
    way = Way()
    if not hit.vehiclePoints and hit.splashCenter:
        way.splash, way.first = _splashWay(hit, compoundModel)
        return way
    points = []
    for point in _wayPoints(hit):
        start, end = Math.Vector3(*point.start), Math.Vector3(*point.end)
        matrix = _partNode(compoundModel, point.tankPartIndex)
        if matrix is None or (end - start).length < 1e-6:
            continue
        points.append((point, matrix, matrix.applyPoint((start + end) * 0.5), _unit(matrix.applyVector(end - start))))
    if not points:
        return way
    if hit.shotDirection:
        point, matrix, position, _ = points[0]
        points[0] = (point, matrix, position, _unit(matrix.applyVector(Math.Vector3(*hit.shotDirection))))
    way.lead = (points[0][2] - points[0][3] * _LEAD, points[0][2])
    way.first = (points[0][2], points[0][3])
    for previous, current in zip(points, points[1:]):
        if previous[0].effectCode not in _GOES_ON:
            break
        way.links.append((previous[2], current[2]))
    else:
        point, matrix, position, direction = points[-1]
        normal = normals.get(id(point))
        if point.effectCode in _RICOCHETS and normal is not None:
            normal = _unit(matrix.applyVector(normal))
            mirrored = _unit(direction - normal * (2 * direction.dot(normal)))
            way.out = (position, position + mirrored * _RICOCHET)
    return way


class HitLinesPresenter(object):
    __hangarSpace = dependency.descriptor(IHangarSpace)

    def __init__(self, hitsPanel, scenePanel):
        self._hitsPanel = hitsPanel
        self._scenePanel = scenePanel
        # (vehicle, chosen hit, other hits) to draw: the hangar vehicle the hits are on (hangar_vehicle.hitsVehicle),
        # the chosen hit or None, the other shown hits when all lines are asked for.
        self._target = None
        self._lines = SceneLines()
        # The next drawing while the collision model has not come, and how many were done for that.
        self._callbackID = None
        self._normalTries = 0
        # onDrawn was told while the lines were put (the chosen hit's first point moved).
        self._told = False
        # The camera was moved for the shooter view.
        self._cameraMoved = False
        # (first point, shell direction) of the chosen hit as last drawn, None without it; told by onDrawn.
        self.chosenShot = None
        self.onDrawn = Event()

    def init(self):
        self.__hangarSpace.onVehicleChangeStarted += self._onVehicleChangeStarted
        self.__hangarSpace.onVehicleChanged += self._onVehicleChanged
        self._hitsPanel.onChanged += self._update
        self._scenePanel.onChanged += self._onScenePanelChanged
        self._scenePanel.onResetCamera += self._onResetCamera
        self._update()

    def fini(self):
        self._scenePanel.onResetCamera -= self._onResetCamera
        self._scenePanel.onChanged -= self._onScenePanelChanged
        self._hitsPanel.onChanged -= self._update
        self.__hangarSpace.onVehicleChanged -= self._onVehicleChanged
        self.__hangarSpace.onVehicleChangeStarted -= self._onVehicleChangeStarted
        if self._cameraMoved:
            self._resetCamera(0)
        self._clear()
        self._resetPose()
        self.onDrawn.clear()
        self._hitsPanel = None
        self._scenePanel = None

    def _update(self):
        # The hits or the choices changed: drawn at once when the hangar shows their vehicle, else when it has loaded.
        battle, side, hit = self._hitsPanel.selection
        vehicle = hitsVehicle(battle, side, hit)
        others = ()
        if self._scenePanel.showsAllLines:
            selected = self._hitsPanel.selectedNumber
            others = tuple(other for number, other in self._hitsPanel.shownHits if number != selected and _drawn(other))
        chosen = hit if hit is not None and _drawn(hit) else None
        target = (vehicle, chosen, others) if isinstance(vehicle, tuple) and (chosen or others) else None
        if target == self._target:
            return
        self._target = target
        self._clear()
        if target is not None:
            self._draw()
        else:
            self._resetPose()

    def _onScenePanelChanged(self):
        if not self._scenePanel.shooterView and self._cameraMoved:
            self._resetCamera()
        self._target = None
        self._update()

    def _onResetCamera(self):
        if self._scenePanel.shooterView and self.chosenShot is not None:
            self._moveCamera(*self.chosenShot)
        else:
            self._resetCamera()

    def _onVehicleChangeStarted(self, *args):
        self._clear()

    def _onVehicleChanged(self, *args):
        if self._target is not None:
            self._clear()
            self._draw()

    def _hangarModel(self):
        # (compound model, collisions) of the hangar vehicle when it is the vehicle of the hits and has loaded.
        if not self.__hangarSpace.isModelLoaded:
            return None
        entity = self.__hangarSpace.getVehicleEntity()
        descriptor = getattr(entity, 'typeDescriptor', None) if entity is not None else None
        if descriptor is None or descriptor.type.compactDescr != self._target[0][0]:
            return None
        appearance = getattr(entity, 'appearance', None)
        compoundModel = getattr(appearance, 'compoundModel', None) if appearance is not None else None
        if compoundModel is None:
            return None
        return compoundModel, getattr(appearance, 'collisions', None)

    def _draw(self):
        hangarModel = self._hangarModel()
        if hangarModel is None:
            return
        try:
            self._drawOn(*hangarModel)
        except Exception:
            _logger.exception('hit lines: cannot draw')

    def _resetPose(self):
        # The hangar vehicle back in the hangar's own pose, when it has loaded.
        if not self.__hangarSpace.isModelLoaded:
            return
        try:
            _setPose(self.__hangarSpace.getVehicleEntity(), None)
        except Exception:
            _logger.exception('hit lines: cannot reset the vehicle pose')

    def _drawOn(self, compoundModel, collisions):
        _, chosen, others = self._target
        pose = chosen.vehiclePose if chosen is not None else None
        _setPose(self.__hangarSpace.getVehicleEntity(), pose)
        normals, waitsNormal = _ricochetNormals(list(others) + ([chosen] if chosen is not None else []), collisions)
        self._told = False
        self._lines.follow(lambda lines: self._putWays(lines, chosen, others, compoundModel, normals))
        if waitsNormal and self._normalTries < _NORMAL_TRIES:
            self._normalTries += 1
            self._callbackID = BigWorld.callback(_NORMAL_RETRY, self._onNormalRetry)
        if not self._told:
            self.onDrawn()

    def _putWays(self, lines, chosen, others, compoundModel, normals):
        # The hits' ways into the lines by the parts' nodes as they are now (on every frame); when the chosen hit's
        # first point moves, it tells onDrawn and the shooter view's camera flies there.
        for hit in others:
            drawWay(lines, _hitWay(hit, compoundModel, normals), False)
        if chosen is None:
            return
        way = _hitWay(chosen, compoundModel, normals)
        drawWay(lines, way, True)
        if not _shotMoved(self.chosenShot, way.first):
            return
        self.chosenShot = way.first
        self._told = True
        if way.first is not None and self._scenePanel.shooterView:
            self._moveCamera(*way.first)
        self.onDrawn()

    def _onNormalRetry(self):
        self._callbackID = None
        self._lines.clear()
        self._draw()

    def _cameraSystem(self):
        # The hangar camera, None when the hangar space is gone (the client closes it before the screen on exit).
        spaceID = self.__hangarSpace.spaceID
        return CGF.getSystem(spaceID, HangarCameraSystem) if spaceID is not None else None

    def _moveCamera(self, position, direction):
        # The shooter view: the camera behind the shell, looking along it at its first point.
        camera = self._cameraSystem()
        if camera is None:
            return
        camera.moveCamera(targetPos=position, yaw=direction.yaw, pitch=-direction.pitch, distance=_SHOOTER_DISTANCE,
                          duration=_CAMERA_FLIGHT)
        self._cameraMoved = True

    def _resetCamera(self, duration=_CAMERA_FLIGHT):
        self._cameraMoved = False
        camera = self._cameraSystem()
        if camera is not None:
            camera.resetCameraTarget(duration=duration)

    def _clear(self):
        # Removes the lines and forgets the drawing that waits for the collision model.
        if self._callbackID is not None:
            BigWorld.cancelCallback(self._callbackID)
            self._callbackID = None
        self._normalTries = 0
        self._lines.clear()
        if self.chosenShot is not None:
            self.chosenShot = None
            self.onDrawn()
