# -*- coding: utf-8 -*-
"""View model of the minimap of the hits screen: its title, the map of the selected battle and the vehicles of the
chosen hit's snapshot on it, with their icons in the client's battle atlas."""
from frameworks.wulf import Array, ViewModel


class MinimapVehicleModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=12, commands=0):
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

    def getIconX(self):
        # The vehicle's icon in the atlas (MinimapModel.atlas): its left, top, width and height in the atlas's pixels;
        # width 0 without an icon (a plain mark of its kind then).
        return self._getNumber(3)

    def setIconX(self, value):
        self._setNumber(3, value)

    def getIconY(self):
        return self._getNumber(4)

    def setIconY(self, value):
        self._setNumber(4, value)

    def getIconWidth(self):
        return self._getNumber(5)

    def setIconWidth(self, value):
        self._setNumber(5, value)

    def getIconHeight(self):
        return self._getNumber(6)

    def setIconHeight(self, value):
        self._setNumber(6, value)

    def getAnchorX(self):
        # The point of the icon that is on the vehicle's place, from the icon's top left, in the atlas's pixels.
        return self._getReal(7)

    def setAnchorX(self, value):
        self._setReal(7, value)

    def getAnchorY(self):
        return self._getReal(8)

    def setAnchorY(self, value):
        self._setReal(8, value)

    def getRotation(self):
        # Radians the icon is turned clockwise about that point: the player's arrow to its hull's heading.
        return self._getReal(9)

    def setRotation(self, value):
        self._setReal(9, value)

    def getTurret(self):
        # Radians of the turret's heading on the map, clockwise from up; when hasTurret.
        return self._getReal(10)

    def setTurret(self, value):
        self._setReal(10, value)

    def getHasTurret(self):
        # The client saw the turret's heading: the page draws the turret's corner.
        return self._getBool(11)

    def setHasTurret(self, value):
        self._setBool(11, value)

    def _initialize(self):
        super(MinimapVehicleModel, self)._initialize()
        # Real: a number property is a whole number (ViewModel._setNumber).
        self._addRealProperty('x', 0.0)
        self._addRealProperty('y', 0.0)
        self._addStringProperty('kind', '')
        self._addNumberProperty('iconX', 0)
        self._addNumberProperty('iconY', 0)
        self._addNumberProperty('iconWidth', 0)
        self._addNumberProperty('iconHeight', 0)
        self._addRealProperty('anchorX', 0.0)
        self._addRealProperty('anchorY', 0.0)
        self._addRealProperty('rotation', 0.0)
        self._addRealProperty('turret', 0.0)
        self._addBoolProperty('hasTurret', False)


class MinimapModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=4, commands=0):
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

    def getAtlas(self):
        # The texture of the client's battle atlas the vehicles' icons are in ('img://...'); empty without it.
        return self._getString(3)

    def setAtlas(self, value):
        self._setString(3, value)

    def _initialize(self):
        super(MinimapModel, self)._initialize()
        self._addStringProperty('image', '')
        self._addStringProperty('title', '')
        self._addArrayProperty('vehicles', Array())
        self._addStringProperty('atlas', '')
