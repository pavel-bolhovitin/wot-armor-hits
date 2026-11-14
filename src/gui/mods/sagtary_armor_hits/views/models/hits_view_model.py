# -*- coding: utf-8 -*-
"""View model of the hits screen: the battle selector, the hits panel, the file buttons, the overlay panel, the
scene panel, the shot panel, the settings menu, the mod page card, and the commands of the mouse over the 3D scene.
"""
from frameworks.wulf import ViewModel

from gui.mods.sagtary_armor_hits.views.models.battle_selector_model import BattleSelectorModel
from gui.mods.sagtary_armor_hits.views.models.file_buttons_model import FileButtonsModel
from gui.mods.sagtary_armor_hits.views.models.hits_panel_model import HitsPanelModel
from gui.mods.sagtary_armor_hits.views.models.mod_page_model import ModPageModel
from gui.mods.sagtary_armor_hits.views.models.overlay_panel_model import OverlayPanelModel
from gui.mods.sagtary_armor_hits.views.models.scene_panel_model import ScenePanelModel
from gui.mods.sagtary_armor_hits.views.models.settings_menu_model import SettingsMenuModel
from gui.mods.sagtary_armor_hits.views.models.shot_panel_model import ShotPanelModel


class HitsViewModel(ViewModel):

    def __init__(self, properties=8, commands=2):
        super(HitsViewModel, self).__init__(properties=properties, commands=commands)

    @property
    def battleSelector(self):
        return self._getViewModel(0)

    @staticmethod
    def getBattleSelectorType():
        return BattleSelectorModel

    @property
    def fileButtons(self):
        return self._getViewModel(1)

    @staticmethod
    def getFileButtonsType():
        return FileButtonsModel

    @property
    def hitsPanel(self):
        return self._getViewModel(2)

    @staticmethod
    def getHitsPanelType():
        return HitsPanelModel

    @property
    def overlayPanel(self):
        return self._getViewModel(3)

    @staticmethod
    def getOverlayPanelType():
        return OverlayPanelModel

    @property
    def scenePanel(self):
        return self._getViewModel(4)

    @staticmethod
    def getScenePanelType():
        return ScenePanelModel

    @property
    def shotPanel(self):
        return self._getViewModel(5)

    @staticmethod
    def getShotPanelType():
        return ShotPanelModel

    @property
    def settingsMenu(self):
        return self._getViewModel(6)

    @staticmethod
    def getSettingsMenuType():
        return SettingsMenuModel

    @property
    def modPage(self):
        return self._getViewModel(7)

    @staticmethod
    def getModPageType():
        return ModPageModel

    def _initialize(self):
        super(HitsViewModel, self)._initialize()
        self._addViewModelProperty('battleSelector', BattleSelectorModel())
        self._addViewModelProperty('fileButtons', FileButtonsModel())
        self._addViewModelProperty('hitsPanel', HitsPanelModel())
        self._addViewModelProperty('overlayPanel', OverlayPanelModel())
        self._addViewModelProperty('scenePanel', ScenePanelModel())
        self._addViewModelProperty('shotPanel', ShotPanelModel())
        self._addViewModelProperty('settingsMenu', SettingsMenuModel())
        self._addViewModelProperty('modPage', ModPageModel())
        # Mouse over the scene, from the page: {dx, dy, dz} of a drag or the wheel, {isOver3dScene}.
        self.onMoveSpace = self._addCommand('onMoveSpace')
        self.onMouseOver3dScene = self._addCommand('onMouseOver3dScene')
