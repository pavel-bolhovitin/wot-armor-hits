# -*- coding: utf-8 -*-
"""Armor tooltip of the hits screen: the armor under the mouse on the hangar vehicle, like on the client's armor page.

ArmorTooltipPresenter does what the armor page presenter does for its tooltip (ArmorSubPresenter): on every mouse
event of the game (gui.g_mouseEventHandlers) it looks whether the mouse is over the 3D scene
(HangarSpace.isCursorOver3DScene, which the page tells the client), finds the armor under the mouse
(getCollisionsAtCursor) and shows the client's tooltip window (ArmorTooltipWindow: the armor layers, their nominal and
resulting armor, the angle, the penetration chance of the shell) at the mouse, with the client's armor cursor; the
page's scene shows the client's grab cursor, which the armor cursor replaces. Without mouse events nothing is done,
except when the page tells the mouse came over the scene, when the window is ready and when the vehicle has loaded.
The tooltip goes when the mouse leaves the vehicle, or the scene for _AWAY seconds: the page tells the mouse left the
scene for a frame now and then. The armor page shows the tooltip only over the vehicle the client has focused
(HangarSpace.onMouseEnter, onMouseExit), but the focus comes late and goes early at the vehicle's edges; this one
shows it wherever the mouse ray hits the vehicle's armor. The shell and the overlay type are the overlay panel's
(overlay_panel.py): the chosen hit's shell.

The window is made before the mouse comes to the vehicle and kept hidden, so that it shows at once: the client lays a
new window out before it is ready, and refuses to show it before. It is shown when the tooltip comes, hidden when it
goes. The client's window shows itself when it is ready, where it is (the top left when not moved); this one
(_makeWindow) does not, it shows only when the presenter shows it. The client lays out only a page with content: once
the page has loaded and the vehicle is there, it is filled with the armor along the camera's ray to the vehicle; an
empty page waits for seconds. The client has one tooltip window at a time, loading one destroys the other: a tooltip
of the shot panel's module icons destroys this window, and a new window of this one would destroy that tooltip. So the
window is made only while the mouse is over the scene, where the client shows no tooltip. The window keeps the
hangar's vehicle entity, which stays the same for another vehicle: the window stays too, made again only for another
entity.
"""
import logging

import BigWorld
import GUI
import Math
from frameworks.wulf import WindowStatus
from gui import g_mouseEventHandlers
from helpers import dependency
from skeletons.account_helpers.settings_core import ISettingsCore
from skeletons.gui.shared.utils import IHangarSpace

from gui.mods.sagtary_armor_hits.trace import calls, timed

_logger = logging.getLogger('sagtary.armor_hits')

# Seconds the mouse is away from the scene before the tooltip goes.
_AWAY = 0.15
# The class of the window, made with the first window: the client's armor modules are imported when used.
_windowClass = None


def _makeWindow(entity):
    # The client's armor tooltip window that does not show itself when it is ready.
    global _windowClass
    if _windowClass is None:
        from gui.impl.lobby.vehicle_hub.sub_presenters.armor.armor_tooltip import ArmorTooltipWindow

        class HiddenArmorTooltipWindow(ArmorTooltipWindow):
            __slots__ = ()

            def _onReady(self):
                pass

        _windowClass = HiddenArmorTooltipWindow
    return _windowClass(entity)


class ArmorTooltipPresenter(object):
    __hangarSpace = dependency.descriptor(IHangarSpace)
    __settingsCore = dependency.descriptor(ISettingsCore)

    def __init__(self, overlayPanel):
        self._overlayPanel = overlayPanel
        self._tooltip = None
        # The presenter follows the mouse events.
        self._isOn = False
        # The callbacks that hide the tooltip when the mouse has been away from the scene for _AWAY seconds, and that
        # update it on the next frame (not in the window's own events); None without them.
        self._awayID = None
        self._laterID = None
        # The vehicle entity the window was made for; its page is filled; BigWorld.time() it was made at, for the log
        # of its loading; the client's armor cursor is on.
        self._entity = None
        self._isFilled = False
        self._madeAt = 0.0
        self._isCursorOn = False

    def init(self):
        self._isOn = True
        g_mouseEventHandlers.add(self._onMouseEvent)
        self.__hangarSpace.onNotifyCursorOver3dScene += self._onCursorOverScene
        self.__hangarSpace.onVehicleChangeStarted += self._onVehicleChangeStarted
        self.__hangarSpace.onVehicleChanged += self._onVehicleChanged

    def fini(self):
        self.__hangarSpace.onVehicleChanged -= self._onVehicleChanged
        self.__hangarSpace.onVehicleChangeStarted -= self._onVehicleChangeStarted
        self.__hangarSpace.onNotifyCursorOver3dScene -= self._onCursorOverScene
        self._stop()
        self._destroy()
        self._overlayPanel = None

    def _stop(self):
        self._isOn = False
        g_mouseEventHandlers.discard(self._onMouseEvent)
        self._cancelAway()
        if self._laterID is not None:
            BigWorld.cancelCallback(self._laterID)
            self._laterID = None

    @timed('armor tooltip: mouse event')
    def _onMouseEvent(self, _):
        self._run(self._update)
        # Not handled: the other handlers get it too.
        return False

    def _onCursorOverScene(self, isOver):
        calls('armor tooltip: cursor over scene', '%s' % isOver)
        self._run(self._update)

    def _onVehicleChangeStarted(self, *args):
        self._run(self._hide)

    def _onVehicleChanged(self):
        self._run(self._fill)
        self._updateLater()

    def _updateLater(self):
        if self._isOn and self._laterID is None:
            self._laterID = BigWorld.callback(0.0, self._onLater)

    def _onLater(self):
        self._laterID = None
        self._run(self._update)

    def _onAway(self):
        self._awayID = None
        self._run(self._hide if not self._isOverScene() else self._update)

    def _cancelAway(self):
        if self._awayID is not None:
            BigWorld.cancelCallback(self._awayID)
            self._awayID = None

    def _run(self, method):
        # A failing tooltip stops for the rest of the screen, rather than failing on every mouse event.
        if not self._isOn:
            return
        try:
            method()
        except Exception:
            _logger.exception('armor tooltip: cannot update')
            self._stop()
            self._destroy()

    def _isOverScene(self):
        cursor = GUI.mcursor()
        return cursor.inWindow and cursor.inFocus and self.__hangarSpace.isCursorOver3DScene

    @timed('armor tooltip: update')
    def _update(self):
        self._fill()
        if not self._isOverScene():
            if self._awayID is None:
                self._awayID = BigWorld.callback(_AWAY, self._onAway)
            return
        self._cancelAway()
        entity = self.__hangarSpace.getVehicleEntity() if self.__hangarSpace.isModelLoaded else None
        if entity is not None and entity is not self._entity:
            # Over the scene only: elsewhere a new window would destroy a tooltip of the client.
            self._destroy()
            self._make(entity)
        collisions = None
        if entity is not None and self._canShow():
            from gui.impl.lobby.vehicle_hub.sub_presenters.armor.utils import getCollisionsAtCursor
            with timed('armor tooltip: collisions at the mouse'):
                collisions = getCollisionsAtCursor(entity)
        if not collisions:
            self._hide()
            return
        with timed('armor tooltip: window move and update'):
            self._move()
            self._tooltip.update(self._overlayPanel.selected, self._overlayPanel.shellParams, collisions)
        if self._tooltip.isHidden():
            calls('armor tooltip: show')
            with timed('armor tooltip: window show'):
                self._tooltip.show(focus=False)
        self._switchCursor(True)

    @timed('armor tooltip: make')
    def _make(self, entity):
        # The tooltip window of the vehicle, hidden; shown at the mouse when there is armor under it.
        calls('armor tooltip: create')
        self._tooltip = _makeWindow(entity)
        self._entity = entity
        self._isFilled = False
        self._tooltip.onStatusChanged += self._onStatusChanged
        self._tooltip.onReady += self._onWindowReady
        self._tooltip.content.onStatusChanged += self._onViewStatusChanged
        self._madeAt = BigWorld.time()
        self._tooltip.load()

    def _canShow(self):
        # The window has loaded and the client has laid it out.
        tooltip = self._tooltip
        return tooltip is not None and tooltip.windowStatus == WindowStatus.LOADED and tooltip.isReady

    def _move(self):
        # The mouse in pixels of the interface, as the armor page places its tooltip.
        from gui.impl.lobby.vehicle_hub.sub_presenters.armor.utils import getCursorPositionInPixels
        x, y = getCursorPositionInPixels()
        scale = self.__settingsCore.interfaceScale.get()
        if scale != 1:
            x, y = int(x // scale), int(y // scale)
        self._tooltip.move(x, y)

    @timed('armor tooltip: fill')
    def _fill(self):
        # The loaded window's page filled once with the armor along the camera's ray to the vehicle's middle, while
        # the vehicle it was made for is there.
        tooltip = self._tooltip
        entity = self._entity
        if (self._isFilled or tooltip is None or tooltip.windowStatus != WindowStatus.LOADED
                or not self.__hangarSpace.isModelLoaded or entity is not self.__hangarSpace.getVehicleEntity()):
            return
        collisions = entity.appearance.collisions
        if not collisions:
            return
        from helpers.collisions import SegmentCollisionResultExt
        from shared_utils.vehicle_utils import getMatinfo
        start = Math.Matrix(BigWorld.camera().invViewMatrix).translation
        end = entity.position + Math.Vector3(0.0, 1.0, 0.0)
        found = collisions.collideAllWorld(start, start + (end - start) * 2.0)
        if not found:
            return
        isWheeled = entity.typeDescriptor.type.isWheeledVehicle
        segments = [SegmentCollisionResultExt(distance, angleCos, getMatinfo(entity, part, kind, isWheeled), part)
                    for distance, angleCos, kind, part in found]
        tooltip.update(self._overlayPanel.selected, self._overlayPanel.shellParams, segments)
        self._isFilled = True
        _logger.info('armor tooltip: filled with %d layers at %.0f ms', len(segments), self._since())

    def _since(self):
        return (BigWorld.time() - self._madeAt) * 1000

    def _onStatusChanged(self, status):
        _logger.info('armor tooltip: window status %s at %.0f ms', status, self._since())
        if status == WindowStatus.LOADED:
            self._run(self._fill)
        elif status == WindowStatus.DESTROYED:
            self._destroy(isDestroyed=True)

    def _onWindowReady(self):
        # The mouse may be over the armor already, without moving.
        _logger.info('armor tooltip: window ready at %.0f ms', self._since())
        self._updateLater()

    def _onViewStatusChanged(self, status):
        _logger.info('armor tooltip: page status %s at %.0f ms', status, self._since())

    @timed('armor tooltip: hide')
    def _hide(self):
        if self._canShow() and not self._tooltip.isHidden():
            calls('armor tooltip: hide')
            self._tooltip.hide()
        self._switchCursor(False)

    def _switchCursor(self, isOn):
        if self._isCursorOn != isOn:
            self._isCursorOn = isOn
            from gui.impl.lobby.vehicle_hub.sub_presenters.armor.utils import getCursorPositionInPixels
            calls('armor tooltip: armor cursor', '%s at %s pixels' % ('on' if isOn else 'off',
                                                                      getCursorPositionInPixels()))
            GUI.switchArmorInspectorCursor(isOn)

    def _destroy(self, isDestroyed=False):
        # isDestroyed: the window is gone already (the client destroyed it), its page with it.
        tooltip, self._tooltip = self._tooltip, None
        if tooltip is None:
            return
        calls('armor tooltip: destroy', 'by the client' if isDestroyed else '')
        tooltip.onStatusChanged -= self._onStatusChanged
        tooltip.onReady -= self._onWindowReady
        if tooltip.content is not None:
            tooltip.content.onStatusChanged -= self._onViewStatusChanged
        if not isDestroyed:
            tooltip.destroy()
        self._entity = None
        self._switchCursor(False)
