# -*- coding: utf-8 -*-
"""Armor tooltip of the hits screen: the armor under the mouse on the hangar vehicle, like on the client's armor page.

ArmorTooltipPresenter does what the armor page presenter does for its tooltip (ArmorSubPresenter): on every mouse
event of the game (gui.g_mouseEventHandlers) it looks whether the mouse is over the 3D scene
(HangarSpace.isCursorOver3DScene, which the page tells the client) and finds the armor under the mouse
(getCollisionsAtCursor). Over the armor it makes the client's tooltip window (ArmorTooltipWindow: the armor layers,
their nominal and resulting armor, the angle, the penetration chance of the shell), places it at the mouse, fills it
and loads it; every mouse event places and fills it again. The window shows itself when the client has laid it out.

The window's page tells the client its size only if its first drawing has armor layers: it watches its size from
then on (a ResizeObserver set up once), and draws nothing without layers. A window loaded empty and filled later is
laid out only when the client gives up waiting for its size, 3 s later ("Size calculation timeout"). So the window is
filled before it loads, and made only where the mouse ray meets armor (a collision with a material); it goes when
the ray meets none, or the mouse is away from the scene for _AWAY seconds: the page tells the mouse left the scene
for a frame now and then. The client's armor cursor is on while there is a window; the page's scene shows the
client's grab cursor, which the armor cursor replaces. As on the armor page, the window is there only while the client
has the mouse over the hangar vehicle (HangarSpace.onMouseEnter, onMouseExit), the vehicle selectable while the
screen is open (lockVehicleSelectable). The shell and the overlay type are the overlay panel's (overlay_panel.py):
the chosen hit's shell.
"""
import logging

import BigWorld
import GUI
from frameworks.wulf import WindowStatus
from gui import g_mouseEventHandlers
from helpers import dependency
from skeletons.account_helpers.settings_core import ISettingsCore
from skeletons.gui.shared.utils import IHangarSpace

_logger = logging.getLogger('sagtary.armor_hits')

# Seconds the mouse is away from the scene before the tooltip goes.
_AWAY = 0.15


def _hasArmor(collisions):
    # The mouse ray meets armor: a collision with a material, which the window shows as a layer. A window is made only
    # then: without layers its page draws nothing and the client waits 3 s for its size.
    return bool(collisions) and any(collision.matInfo is not None for collision in collisions)


class ArmorTooltipPresenter(object):
    __hangarSpace = dependency.descriptor(IHangarSpace)
    __settingsCore = dependency.descriptor(ISettingsCore)

    def __init__(self, overlayPanel):
        self._overlayPanel = overlayPanel
        self._tooltip = None
        # The presenter follows the mouse events.
        self._isOn = False
        # The callback that destroys the window when the mouse has been away from the scene for _AWAY seconds; None
        # without it.
        self._awayID = None
        # The vehicle entity the window was made for.
        self._entity = None
        # The client has the mouse over the hangar vehicle.
        self._isMouseOver = False

    def init(self):
        self._isOn = True
        g_mouseEventHandlers.add(self._onMouseEvent)
        self.__hangarSpace.onNotifyCursorOver3dScene += self._onCursorOverScene
        self.__hangarSpace.onVehicleChangeStarted += self._onVehicleChangeStarted
        self.__hangarSpace.onMouseEnter += self._onMouseEnter
        self.__hangarSpace.onMouseExit += self._onMouseExit
        if self.__hangarSpace.space is not None:
            self.__hangarSpace.lockVehicleSelectable(self)

    def fini(self):
        if self.__hangarSpace.space is not None:
            self.__hangarSpace.unlockVehicleSelectable(self)
        self.__hangarSpace.onMouseExit -= self._onMouseExit
        self.__hangarSpace.onMouseEnter -= self._onMouseEnter
        self.__hangarSpace.onVehicleChangeStarted -= self._onVehicleChangeStarted
        self.__hangarSpace.onNotifyCursorOver3dScene -= self._onCursorOverScene
        self._stop()
        self._destroy()
        self._overlayPanel = None

    def _stop(self):
        self._isOn = False
        g_mouseEventHandlers.discard(self._onMouseEvent)
        self._cancelAway()

    def _onMouseEvent(self, _):
        self._run(self._update)
        # Not handled: the other handlers get it too.
        return False

    def _onCursorOverScene(self, *args):
        self._run(self._update)

    def _onVehicleChangeStarted(self, *args):
        self._run(self._destroy)

    def _onMouseEnter(self, entity):
        if entity != self.__hangarSpace.getVehicleEntity():
            return
        self._isMouseOver = True
        self._run(self._update)

    def _onMouseExit(self, entity):
        if entity != self.__hangarSpace.getVehicleEntity():
            return
        self._isMouseOver = False
        self._run(self._destroy)

    def _onAway(self):
        self._awayID = None
        self._run(self._update if self._isOverScene() else self._destroy)

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

    def _update(self):
        if not self._isOverScene():
            if self._tooltip is not None and self._awayID is None:
                self._awayID = BigWorld.callback(_AWAY, self._onAway)
            return
        self._cancelAway()
        isOver = self._isMouseOver and self.__hangarSpace.isModelLoaded
        entity = self.__hangarSpace.getVehicleEntity() if isOver else None
        collisions = None
        if entity is not None:
            from gui.impl.lobby.vehicle_hub.sub_presenters.armor.utils import getCollisionsAtCursor
            collisions = getCollisionsAtCursor(entity)
        if not _hasArmor(collisions):
            self._destroy()
            return
        if self._tooltip is not None and entity is not self._entity:
            self._destroy()
        if self._tooltip is None:
            self._make(entity, collisions)
            return
        self._fill(collisions)

    def _make(self, entity, collisions):
        # Filled with armor before load(), never after: a window loaded empty waits 3 s for its size (the client's
        # "Size calculation timeout"; see the module's text).
        from gui.impl.lobby.vehicle_hub.sub_presenters.armor.armor_tooltip import ArmorTooltipWindow
        self._tooltip = ArmorTooltipWindow(entity)
        self._entity = entity
        self._tooltip.onStatusChanged += self._onStatusChanged
        self._fill(collisions)
        self._tooltip.load()
        GUI.switchArmorInspectorCursor(True)

    def _fill(self, collisions):
        # The window at the mouse in pixels of the interface, as the armor page places its tooltip, with the armor
        # under the mouse.
        from gui.impl.lobby.vehicle_hub.sub_presenters.armor.utils import getCursorPositionInPixels
        x, y = getCursorPositionInPixels()
        scale = self.__settingsCore.interfaceScale.get()
        if scale != 1:
            x, y = int(x // scale), int(y // scale)
        self._tooltip.move(x, y)
        self._tooltip.update(self._overlayPanel.selected, self._overlayPanel.shellParams, collisions)

    def _onStatusChanged(self, status):
        if status == WindowStatus.DESTROYED:
            self._destroy(isDestroyed=True)

    def _destroy(self, isDestroyed=False):
        # isDestroyed: the window is gone already (the client destroyed it).
        self._cancelAway()
        tooltip, self._tooltip = self._tooltip, None
        self._entity = None
        if tooltip is None:
            return
        tooltip.onStatusChanged -= self._onStatusChanged
        if not isDestroyed:
            tooltip.destroy()
        GUI.switchArmorInspectorCursor(False)
