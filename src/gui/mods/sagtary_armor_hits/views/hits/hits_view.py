# -*- coding: utf-8 -*-
"""Gameface view and window of the hits screen.

HitsWindow is the class of the Scaleform view setting of the screen: a Gameface window (WindowImpl) in the sub view
layer. Its content, HitsView, is a Gameface view with the layout R.mods.sagtary_armor_hits.views.HitsView, declared in
res/gui/gen_resources/sagtary_armor_hits.json.

The lobby draws its header and footer as opaque bars ("old style") around a sub view in a frame. A view is out of the
frame when it supports the full screen mode: the page tells it with viewEnv.setFullscreenModeSupported(true) in
HitsView.js, like the client's armor page, and places its content by the external paddings the lobby gives for the
header and the footer.

The page passes mouse drags and the wheel over the 3D scene (onMoveSpace, onMouseOver3dScene) to the hangar camera
(hangar_camera.py), so the camera turns around the vehicle. The panels, the hangar camera and vehicle and the hit
lines in the scene have presenters of their own, made here with the data they show. The file buttons (save the
chosen battle to its file, load the battle files) are there when the view is given the battle files, the settings
menu when it is given the mod's settings.

The presenters stop when the screen's lobby state is left (SCREEN_LEFT_EVENT), before the state puts the hangar
back; the view itself closes later. Else the hit lines, which follow the vehicle on every frame, would see the
vehicle on its way back to the garage and fly the garage camera after the hit.
"""
from frameworks.wulf import WindowFlags
from gui.impl.gen import R
from gui.impl.lobby.common.view_wrappers import createBackportTooltipDecorator
from gui.impl.pub import WindowImpl
from gui.impl.pub.view_component import ViewComponent
from gui.shared import EVENT_BUS_SCOPE, g_eventBus

from gui.mods.sagtary_armor_hits.lang import text
from gui.mods.sagtary_armor_hits.views.hits.armor_tooltip import ArmorTooltipPresenter
from gui.mods.sagtary_armor_hits.views.hits.battle_selector import BattleSelectorPresenter
from gui.mods.sagtary_armor_hits.views.hits.file_buttons import FileButtonsPresenter
from gui.mods.sagtary_armor_hits.views.hits.hangar_camera import HangarCamera
from gui.mods.sagtary_armor_hits.views.hits.hangar_vehicle import HangarVehiclePresenter
from gui.mods.sagtary_armor_hits.views.hits.hit_lines import HitLinesPresenter
from gui.mods.sagtary_armor_hits.views.hits.hits_panel import HitsPanelPresenter
from gui.mods.sagtary_armor_hits.views.hits.overlay_panel import OverlayPanelPresenter
from gui.mods.sagtary_armor_hits.views.hits.scene_panel import ScenePanelPresenter
from gui.mods.sagtary_armor_hits.views.hits.settings_menu import SettingsMenuPresenter
from gui.mods.sagtary_armor_hits.views.hits.shot_panel import ShotPanelPresenter
from gui.mods.sagtary_armor_hits.views.models.hits_view_model import HitsViewModel

# Alias of the Scaleform view setting of the screen.
VIEW_ALIAS = 'sagtaryArmorHitsView'
# The event the screen's lobby state sends when it is left, before it puts the hangar back.
SCREEN_LEFT_EVENT = 'sagtaryArmorHitsScreenLeft'


# The shot panel's texts.
_SHOT_TEXTS = ('shot/shooter', 'shot/target', 'shot/damage', 'shot/penetration', 'shot/armor', 'shot/angle',
               'shot/distance', 'shot/crits', 'shot/avgDamage', 'shot/avgPenetration',
               'shot/chance', 'shot/nominal', 'shot/angleArmor', 'shot/ricochet', 'shot/distanceLoss', 'shot/deviation')
# The settings menu's texts.
_SETTINGS_TEXTS = ('settings/showFriendlyFire', 'settings/showButtonInModsMenu', 'settings/debug', 'settings/restart',
                   'settings/battleModes', 'settings/random', 'settings/competitive', 'settings/training',
                   'settings/fun', 'settings/other', 'settings/off', 'settings/session', 'settings/file')


class HitsView(ViewComponent):

    def __init__(self, battleStore, battleFiles=None, modSettings=None):
        super(HitsView, self).__init__(R.mods.sagtary_armor_hits.views.HitsView(), HitsViewModel)
        self._battleStore = battleStore
        self._battleFiles = battleFiles
        self._settings = modSettings
        self._presenters = []
        self._shotPanel = None
        self._camera = None

    @createBackportTooltipDecorator()
    def createToolTip(self, event):
        return super(HitsView, self).createToolTip(event)

    def getTooltipData(self, event):
        # The client's tooltip of a module or the shell of the shot panel's cards (the page tells the card's role and
        # the module's index).
        if self._shotPanel is None:
            return None
        return self._shotPanel.tooltipData(event.getArgument('role'), int(event.getArgument('index', -1)))

    def _getEvents(self):
        model = self.getViewModel()
        return ((model.onMoveSpace, self.__onMoveSpace), (model.onMouseOver3dScene, self.__onMouseOver3dScene))

    def _onLoading(self, *args, **kwargs):
        super(HitsView, self)._onLoading(*args, **kwargs)
        model = self.getViewModel()
        battleSelector = BattleSelectorPresenter(model.battleSelector, self._battleStore, {
            'empty': text('battles/empty')})
        self._presenters.append(battleSelector)
        # The hits panel shows the battle the selector shows, so it is made and set up after the selector.
        hitsPanel = HitsPanelPresenter(model.hitsPanel, self._battleStore, battleSelector, {
            'received': text('hits/received'), 'dealt': text('hits/dealt')}, self._settings)
        self._presenters.append(hitsPanel)
        # The hangar shows the vehicle the hits panel shows the hits on.
        self._presenters.append(HangarVehiclePresenter(hitsPanel))
        # The hangar camera, free to look from under the vehicle; the hit lines move it for the shooter view.
        self._camera = HangarCamera()
        self._presenters.append(self._camera)
        # The scene panel's choices: which lines are drawn over that vehicle, the shooter view.
        scenePanel = ScenePanelPresenter(model.scenePanel, {
            'lines': text('lines/title'), 'allHits': text('lines/all'), 'shooter': text('camera/shooter'),
            'reset': text('camera/reset')}, hitsPanel)
        self._presenters.append(scenePanel)
        hitLines = HitLinesPresenter(hitsPanel, scenePanel, self._camera)
        self._presenters.append(hitLines)
        overlayPanel = OverlayPanelPresenter(model.overlayPanel, hitsPanel)
        self._presenters.append(overlayPanel)
        self._presenters.append(ArmorTooltipPresenter(overlayPanel))
        # The chosen hit's details: its shell from the overlay panel, its line from the hit lines.
        self._shotPanel = ShotPanelPresenter(model.shotPanel, hitsPanel, overlayPanel, hitLines, dict(
            (key.split('/')[1], text(key)) for key in _SHOT_TEXTS))
        self._presenters.append(self._shotPanel)
        if self._battleFiles is not None:
            self._presenters.append(FileButtonsPresenter(model.fileButtons, self._battleStore, self._battleFiles,
                                                         hitsPanel, {
                'save': text('file/save'), 'delete': text('file/delete'), 'deleteConfirm': text('file/deleteConfirm'),
                'deleted': text('file/deleted'), 'exported': text('file/exported'), 'failed': text('file/failed')}))
        if self._settings is not None:
            self._presenters.append(SettingsMenuPresenter(model.settingsMenu, self._settings, dict(
                (key.split('/')[1], text(key)) for key in _SETTINGS_TEXTS)))
        for presenter in self._presenters:
            presenter.init()
        g_eventBus.addListener(SCREEN_LEFT_EVENT, self.__onScreenLeft, EVENT_BUS_SCOPE.LOBBY)

    def _finalize(self):
        g_eventBus.removeListener(SCREEN_LEFT_EVENT, self.__onScreenLeft, EVENT_BUS_SCOPE.LOBBY)
        self._finiPresenters()
        self._battleStore = None
        self._battleFiles = None
        self._settings = None
        super(HitsView, self)._finalize()

    def _finiPresenters(self):
        # Once: when the screen is left, or when the view closes without that.
        for presenter in reversed(self._presenters):
            presenter.fini()
        self._presenters = []
        self._shotPanel = None
        self._camera = None

    def __onScreenLeft(self, event):
        self._finiPresenters()

    def __onMoveSpace(self, args=None):
        if not args or self._camera is None:
            return
        self._camera.moveByMouse(args.get('dx'), args.get('dy'), args.get('dz'))

    def __onMouseOver3dScene(self, args=None):
        if self._camera is not None:
            self._camera.setMouseOverScene(bool(args.get('isOver3dScene')) if args else False)


class HitsWindow(WindowImpl):

    def __init__(self, layer, battleStore, battleFiles=None, modSettings=None, **kwargs):
        # The client's view loader makes the window with the keyword arguments of App.loadView: HitsScreen gives the
        # battleStore, the battleFiles and the modSettings there, the lobby state gives its ctx.
        super(HitsWindow, self).__init__(content=HitsView(battleStore, battleFiles, modSettings),
                                         wndFlags=WindowFlags.WINDOW, layer=layer)
