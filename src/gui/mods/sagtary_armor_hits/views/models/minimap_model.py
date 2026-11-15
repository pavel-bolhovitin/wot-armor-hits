# -*- coding: utf-8 -*-
"""View model of the minimap of the hits screen: its title and the map of the selected battle."""
from frameworks.wulf import ViewModel


class MinimapModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=2, commands=0):
        super(MinimapModel, self).__init__(properties=properties, commands=commands)

    def getImage(self):
        # The map image ('img://...'); empty without a battle or an image of its map: the page hides the minimap.
        return self._getString(0)

    def setImage(self, value):
        self._setString(0, value)

    def getTitle(self):
        # The header's title, the client's text.
        return self._getString(1)

    def setTitle(self, value):
        self._setString(1, value)

    def _initialize(self):
        super(MinimapModel, self)._initialize()
        self._addStringProperty('image', '')
        self._addStringProperty('title', '')
