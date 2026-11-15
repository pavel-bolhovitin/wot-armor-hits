# -*- coding: utf-8 -*-
"""View model of the scene panel of the hits screen, at the bottom: which hit lines are drawn (all the shown hits or
the chosen one), the shooter view (the camera looks along the chosen hit's shell) and the camera reset. The panel shows
icons; their names are in the client's tooltips (HitsView.getTooltipData).
"""
from frameworks.wulf import ViewModel


class ScenePanelModel(ViewModel):
    __slots__ = ('onLines', 'onShooterView', 'onResetCamera')

    def __init__(self, properties=3, commands=3):
        super(ScenePanelModel, self).__init__(properties=properties, commands=commands)

    def getAllLines(self):
        # The lines of all the shown hits are drawn, not only the chosen hit's.
        return self._getBool(0)

    def setAllLines(self, value):
        self._setBool(0, value)

    def getShooterView(self):
        return self._getBool(1)

    def setShooterView(self, value):
        self._setBool(1, value)

    def getAllLinesEnabled(self):
        # False on the dealt side: only the chosen hit's line, the lines toggle hidden.
        return self._getBool(2)

    def setAllLinesEnabled(self, value):
        self._setBool(2, value)

    def _initialize(self):
        super(ScenePanelModel, self)._initialize()
        self._addBoolProperty('allLines', False)
        self._addBoolProperty('shooterView', False)
        self._addBoolProperty('allLinesEnabled', True)
        # onLines: {'all': bool}.
        self.onLines = self._addCommand('onLines')
        self.onShooterView = self._addCommand('onShooterView')
        self.onResetCamera = self._addCommand('onResetCamera')
