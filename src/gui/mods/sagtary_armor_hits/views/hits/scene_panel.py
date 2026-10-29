# -*- coding: utf-8 -*-
"""Scene panel of the hits screen, at the bottom: which hit lines the scene draws and the shooter view.

ScenePanelPresenter fills the view model (views/models/scene_panel_model.py) and keeps the choices: the lines of all
the hits the hits panel shows or of the chosen hit only (allLines), and the shooter view, the camera looking along
the chosen hit's shell (shooterView). All the lines are only for the hits on the player's vehicle: the dealt hits are
on other vehicles each, and the hangar shows one, so on the dealt side the panel offers the chosen hit's line only
(showsAllLines is False there, the page hides the choice of lines) and keeps the choice for the received side. It
tells its listeners when the choices change (onChanged); the hit lines presenter draws by them. The reset button
asks for the camera's start (onResetCamera): the hit lines presenter puts it back, or behind the shell when the shooter
view is on. The page shows two groups: the lines (a check box) and the camera (the shooter view's check box and the
reset). The camera's title and the reset's label are the client's texts, the others the mod's.
"""
from Event import Event

from gui.mods.sagtary_armor_hits.data.client_names import clientText
from gui.mods.sagtary_armor_hits.views.hits.hits_panel import DEALT

_CAMERA_KEY = '#settings:keyboard/keysBlocks/group/camera'
_RESET_KEY = '#settings:colorSettings/view/resetBtn'


class ScenePanelPresenter(object):

    def __init__(self, model, texts, hitsPanel):
        # texts: {'lines', 'allHits', 'shooter', 'reset'} in the client language.
        self._model = model
        self._texts = texts
        self._hitsPanel = hitsPanel
        self.allLines = False
        self.shooterView = False
        self.onChanged = Event()
        self.onResetCamera = Event()

    @property
    def canShowAllLines(self):
        return self._hitsPanel.selection[1] != DEALT

    @property
    def showsAllLines(self):
        # The lines of all the shown hits are drawn: chosen, and on the received side.
        return self.allLines and self.canShowAllLines

    def init(self):
        with self._model.transaction() as model:
            model.setLinesTitle(self._texts['lines'])
            model.setAllLabel(self._texts['allHits'])
            model.setCameraTitle(clientText(_CAMERA_KEY) or '')
            model.setShooterLabel(self._texts['shooter'])
            model.setResetLabel(clientText(_RESET_KEY) or self._texts['reset'])
        self._model.onLines += self._onLines
        self._model.onShooterView += self._onShooterView
        self._model.onResetCamera += self._onResetCamera
        self._hitsPanel.onChanged += self._update
        self._update()

    def fini(self):
        self._hitsPanel.onChanged -= self._update
        self._model.onResetCamera -= self._onResetCamera
        self._model.onShooterView -= self._onShooterView
        self._model.onLines -= self._onLines
        self.onChanged.clear()
        self.onResetCamera.clear()
        self._model = None
        self._hitsPanel = None

    def _onLines(self, args=None):
        allLines = bool((args or {}).get('all'))
        if allLines and not self.canShowAllLines:
            return
        if allLines != self.allLines:
            self.allLines = allLines
            self._update()
            self.onChanged()

    def _onShooterView(self, args=None):
        self.shooterView = not self.shooterView
        self._update()
        self.onChanged()

    def _onResetCamera(self, *args):
        self.onResetCamera()

    def _update(self, *args):
        with self._model.transaction() as model:
            model.setAllLines(self.showsAllLines)
            model.setAllLinesEnabled(self.canShowAllLines)
            model.setShooterView(self.shooterView)
