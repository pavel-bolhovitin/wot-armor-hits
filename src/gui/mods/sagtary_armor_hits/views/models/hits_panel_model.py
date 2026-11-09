# -*- coding: utf-8 -*-
"""View models of the hits panel, written like the client's generated view models (typed getters and setters by
property index). A new field is a new property at the end of _initialize, with its getter and setter.
"""
from frameworks.wulf import Array, ViewModel


class HitItemModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=12, commands=0):
        super(HitItemModel, self).__init__(properties=properties, commands=commands)

    def getNumber(self):
        # The hit's number in the battle, on its side (received or dealt), from 1.
        return self._getNumber(0)

    def setNumber(self, value):
        self._setNumber(0, value)

    def getTime(self):
        # Time in the battle, "m:ss".
        return self._getString(1)

    def setTime(self, value):
        self._setString(1, value)

    def getResult(self):
        # data.hits.HitResult: 'damage', 'blocked', 'ricochet', 'noDamage'.
        return self._getString(2)

    def setResult(self, value):
        self._setString(2, value)

    def getVehicleName(self):
        return self._getString(3)

    def setVehicleName(self, value):
        self._setString(3, value)

    def getVehicleClass(self):
        # The class icon of the client's damage log: 'light', 'middle', 'heavy', 'destroyer', 'art', or ''.
        return self._getString(4)

    def setVehicleClass(self, value):
        self._setString(4, value)

    def getPlayerName(self):
        return self._getString(5)

    def setPlayerName(self, value):
        self._setString(5, value)

    def getShellText(self):
        # The shell kind as the client's damage log shows it ("AP", "HE", ...).
        return self._getString(6)

    def setShellText(self, value):
        self._setString(6, value)

    def getShellName(self):
        # The shell kind in full, for the tooltip.
        return self._getString(7)

    def setShellName(self, value):
        self._setString(7, value)

    def getDamage(self):
        return self._getNumber(8)

    def setDamage(self, value):
        self._setNumber(8, value)

    def getIsGoldShell(self):
        return self._getBool(9)

    def setIsGoldShell(self, value):
        self._setBool(9, value)

    def getHasCrits(self):
        # The hit damaged modules or crew.
        return self._getBool(10)

    def setHasCrits(self, value):
        self._setBool(10, value)

    def getShellMode(self):
        # data.hits.ShellMode of the shell: 'standard', 'calibrated', or '' when not known.
        return self._getString(11)

    def setShellMode(self, value):
        self._setString(11, value)

    def _initialize(self):
        super(HitItemModel, self)._initialize()
        self._addNumberProperty('number', 0)
        self._addStringProperty('time', '')
        self._addStringProperty('result', '')
        self._addStringProperty('vehicleName', '')
        self._addStringProperty('vehicleClass', '')
        self._addStringProperty('playerName', '')
        self._addStringProperty('shellText', '')
        self._addStringProperty('shellName', '')
        self._addNumberProperty('damage', 0)
        self._addBoolProperty('isGoldShell', False)
        self._addBoolProperty('hasCrits', False)
        self._addStringProperty('shellMode', '')


class HitFilterModel(ViewModel):
    # A result filter: the result ('' for all hits) and how many hits it has.
    __slots__ = ()

    def __init__(self, properties=2, commands=0):
        super(HitFilterModel, self).__init__(properties=properties, commands=commands)

    def getId(self):
        return self._getString(0)

    def setId(self, value):
        self._setString(0, value)

    def getCount(self):
        return self._getNumber(1)

    def setCount(self, value):
        self._setNumber(1, value)

    def _initialize(self):
        super(HitFilterModel, self)._initialize()
        self._addStringProperty('id', '')
        self._addNumberProperty('count', 0)


class HitsPanelModel(ViewModel):
    __slots__ = ('onSide', 'onFilter', 'onHit', 'onStep')

    def __init__(self, properties=10, commands=4):
        super(HitsPanelModel, self).__init__(properties=properties, commands=commands)

    def getIsVisible(self):
        return self._getBool(0)

    def setIsVisible(self, value):
        self._setBool(0, value)

    def getSide(self):
        # 'received' (hits on the player's vehicle) or 'dealt' (the player's hits).
        return self._getString(1)

    def setSide(self, value):
        self._setString(1, value)

    def getReceivedLabel(self):
        return self._getString(2)

    def setReceivedLabel(self, value):
        self._setString(2, value)

    def getDealtLabel(self):
        return self._getString(3)

    def setDealtLabel(self, value):
        self._setString(3, value)

    def getAllLabel(self):
        return self._getString(4)

    def setAllLabel(self, value):
        self._setString(4, value)

    def getFilters(self):
        return self._getArray(5)

    def setFilters(self, value):
        self._setArray(5, value)

    @staticmethod
    def getFiltersType():
        return HitFilterModel

    def getSelectedFilter(self):
        # The chosen result, '' for all hits.
        return self._getString(6)

    def setSelectedFilter(self, value):
        self._setString(6, value)

    def getHits(self):
        return self._getArray(7)

    def setHits(self, value):
        self._setArray(7, value)

    @staticmethod
    def getHitsType():
        return HitItemModel

    def getSelectedHit(self):
        # Index of the chosen hit in hits, -1 when there are none.
        return self._getNumber(8)

    def setSelectedHit(self, value):
        self._setNumber(8, value)

    def getHasShellModes(self):
        # A hit of the side in the battle has a known shell mode: the list has the column of its icon.
        return self._getBool(9)

    def setHasShellModes(self, value):
        self._setBool(9, value)

    def _initialize(self):
        super(HitsPanelModel, self)._initialize()
        self._addBoolProperty('isVisible', False)
        self._addStringProperty('side', '')
        self._addStringProperty('receivedLabel', '')
        self._addStringProperty('dealtLabel', '')
        self._addStringProperty('allLabel', '')
        self._addArrayProperty('filters', Array())
        self._addStringProperty('selectedFilter', '')
        self._addArrayProperty('hits', Array())
        self._addNumberProperty('selectedHit', -1)
        self._addBoolProperty('hasShellModes', False)
        # {side}, {id}, {index}, {delta}: the page's tabs, filters, list rows, arrows.
        self.onSide = self._addCommand('onSide')
        self.onFilter = self._addCommand('onFilter')
        self.onHit = self._addCommand('onHit')
        self.onStep = self._addCommand('onStep')
