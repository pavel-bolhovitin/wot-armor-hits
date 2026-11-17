# -*- coding: utf-8 -*-
"""View model of the minimap of the hits screen: its title, the map of the selected battle and the vehicles of the
chosen hit's snapshot on it."""
from frameworks.wulf import Array, ViewModel


class MinimapVehicleModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=3, commands=0):
        super(MinimapVehicleModel, self).__init__(properties=properties, commands=commands)

    def getX(self):
        # Where the vehicle is on the map's image from its left edge, 0 to 1 of its width.
        return self._getReal(0)

    def setX(self, value):
        self._setReal(0, value)

    def getY(self):
        # Where the vehicle is on the map's image from its top edge, 0 to 1 of its height.
        return self._getReal(1)

    def setY(self, value):
        self._setReal(1, value)

    def getKind(self):
        # Whose vehicle it is to the player: 'player', 'ally', 'enemy'.
        return self._getString(2)

    def setKind(self, value):
        self._setString(2, value)

    def _initialize(self):
        super(MinimapVehicleModel, self)._initialize()
        # Real: a number property is a whole number (ViewModel._setNumber).
        self._addRealProperty('x', 0.0)
        self._addRealProperty('y', 0.0)
        self._addStringProperty('kind', '')


class MinimapModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=3, commands=0):
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

    def getVehicles(self):
        # The vehicles of the chosen hit's snapshot on the map; none without one.
        return self._getArray(2)

    def setVehicles(self, value):
        self._setArray(2, value)

    @staticmethod
    def getVehiclesType():
        return MinimapVehicleModel

    def _initialize(self):
        super(MinimapModel, self)._initialize()
        self._addStringProperty('image', '')
        self._addStringProperty('title', '')
        self._addArrayProperty('vehicles', Array())
