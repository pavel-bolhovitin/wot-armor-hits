# -*- coding: utf-8 -*-
"""View models of the battle selector, written like the client's generated view models (typed getters and setters by
property index). A new field is a new property at the end of _initialize, with its getter and setter.
"""
from frameworks.wulf import Array, ViewModel


class BattleItemModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=9, commands=0):
        super(BattleItemModel, self).__init__(properties=properties, commands=commands)

    def getId(self):
        return self._getString(0)

    def setId(self, value):
        self._setString(0, value)

    def getMapName(self):
        return self._getString(1)

    def setMapName(self, value):
        self._setString(1, value)

    def getMapImage(self):
        return self._getString(2)

    def setMapImage(self, value):
        self._setString(2, value)

    def getVehicleName(self):
        return self._getString(3)

    def setVehicleName(self, value):
        self._setString(3, value)

    def getDay(self):
        # The date of the battle in the client format: the group of the list it is in.
        return self._getString(4)

    def setDay(self, value):
        self._setString(4, value)

    def getTime(self):
        return self._getString(5)

    def setTime(self, value):
        self._setString(5, value)

    def getResult(self):
        # data.battles.BattleResult: '' (not known), 'win', 'defeat', 'draw'.
        return self._getString(6)

    def setResult(self, value):
        self._setString(6, value)

    def getResultText(self):
        return self._getString(7)

    def setResultText(self, value):
        self._setString(7, value)

    def getIsOldFormat(self):
        # From a file of an old format: the page shows its note.
        return self._getBool(8)

    def setIsOldFormat(self, value):
        self._setBool(8, value)

    def _initialize(self):
        super(BattleItemModel, self)._initialize()
        self._addStringProperty('id', '')
        self._addStringProperty('mapName', '')
        self._addStringProperty('mapImage', '')
        self._addStringProperty('vehicleName', '')
        self._addStringProperty('day', '')
        self._addStringProperty('time', '')
        self._addStringProperty('result', '')
        self._addStringProperty('resultText', '')
        self._addBoolProperty('isOldFormat', False)


class BattleSelectorModel(ViewModel):
    __slots__ = ('onSelect',)

    def __init__(self, properties=4, commands=1):
        super(BattleSelectorModel, self).__init__(properties=properties, commands=commands)

    def getBattles(self):
        return self._getArray(0)

    def setBattles(self, value):
        self._setArray(0, value)

    @staticmethod
    def getBattlesType():
        return BattleItemModel

    def getSelectedId(self):
        return self._getString(1)

    def setSelectedId(self, value):
        self._setString(1, value)

    def getEmptyTitle(self):
        return self._getString(2)

    def setEmptyTitle(self, value):
        self._setString(2, value)

    def getOldFormatText(self):
        return self._getString(3)

    def setOldFormatText(self, value):
        self._setString(3, value)

    def _initialize(self):
        super(BattleSelectorModel, self)._initialize()
        self._addArrayProperty('battles', Array())
        self._addStringProperty('selectedId', '')
        self._addStringProperty('emptyTitle', '')
        self._addStringProperty('oldFormatText', '')
        # {id}: the battle the player picked in the list.
        self.onSelect = self._addCommand('onSelect')
