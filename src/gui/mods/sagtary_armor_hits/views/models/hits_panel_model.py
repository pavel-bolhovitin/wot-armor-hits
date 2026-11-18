# -*- coding: utf-8 -*-
"""View models of the hits panel, written like the client's generated view models (typed getters and setters by
property index). A new field is a new property at the end of _initialize, with its getter and setter.
"""
from frameworks.wulf import Array, ViewModel


class HitItemModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=13, commands=0):
        super(HitItemModel, self).__init__(properties=properties, commands=commands)

    def getTime(self):
        # Time in the battle, "m:ss".
        return self._getString(0)

    def setTime(self, value):
        self._setString(0, value)

    def getResult(self):
        # data.hits.HitResult: 'damage', 'blocked', 'ricochet', 'noDamage'.
        return self._getString(1)

    def setResult(self, value):
        self._setString(1, value)

    def getVehicleName(self):
        return self._getString(2)

    def setVehicleName(self, value):
        self._setString(2, value)

    def getVehicleClass(self):
        # The class icon of the client's damage log: 'light', 'middle', 'heavy', 'destroyer', 'art', or ''.
        return self._getString(3)

    def setVehicleClass(self, value):
        self._setString(3, value)

    def getPlayerName(self):
        return self._getString(4)

    def setPlayerName(self, value):
        self._setString(4, value)

    def getShellText(self):
        # The shell kind as the client's damage log shows it ("AP", "HE", ...).
        return self._getString(5)

    def setShellText(self, value):
        self._setString(5, value)

    def getShellName(self):
        # The shell kind in full, for the tooltip.
        return self._getString(6)

    def setShellName(self, value):
        self._setString(6, value)

    def getDamage(self):
        return self._getNumber(7)

    def setDamage(self, value):
        self._setNumber(7, value)

    def getIsGoldShell(self):
        return self._getBool(8)

    def setIsGoldShell(self, value):
        self._setBool(8, value)

    def getHasCrits(self):
        # The hit damaged modules or crew.
        return self._getBool(9)

    def setHasCrits(self, value):
        self._setBool(9, value)

    def getShellMode(self):
        # data.hits.ShellMode of the shell: 'standard', 'calibrated', or '' when not known.
        return self._getString(10)

    def setShellMode(self, value):
        self._setString(10, value)

    def getIsSpgShell(self):
        # A shell of an SPG: the plate is inverted, like the client's damage log shows it.
        return self._getBool(11)

    def setIsSpgShell(self, value):
        self._setBool(11, value)

    def getSide(self):
        # 'received' (a hit on the player's vehicle) or 'dealt' (a hit by the player).
        return self._getString(12)

    def setSide(self, value):
        self._setString(12, value)

    def _initialize(self):
        super(HitItemModel, self)._initialize()
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
        self._addBoolProperty('isSpgShell', False)
        self._addStringProperty('side', '')


class HitFilterModel(ViewModel):
    # A line of the filter's menu: a side or a result ('' for all of them), its name, how many hits it has, whether it
    # is on.
    __slots__ = ()

    def __init__(self, properties=4, commands=0):
        super(HitFilterModel, self).__init__(properties=properties, commands=commands)

    def getId(self):
        return self._getString(0)

    def setId(self, value):
        self._setString(0, value)

    def getLabel(self):
        return self._getString(1)

    def setLabel(self, value):
        self._setString(1, value)

    def getCount(self):
        return self._getNumber(2)

    def setCount(self, value):
        self._setNumber(2, value)

    def getIsOn(self):
        return self._getBool(3)

    def setIsOn(self, value):
        self._setBool(3, value)

    def _initialize(self):
        super(HitFilterModel, self)._initialize()
        self._addStringProperty('id', '')
        self._addStringProperty('label', '')
        self._addNumberProperty('count', 0)
        self._addBoolProperty('isOn', False)


class HitsPanelModel(ViewModel):
    __slots__ = ('onSideFilter', 'onResultFilter', 'onHit', 'onStep')

    def __init__(self, properties=7, commands=4):
        super(HitsPanelModel, self).__init__(properties=properties, commands=commands)

    def getIsVisible(self):
        return self._getBool(0)

    def setIsVisible(self, value):
        self._setBool(0, value)

    def getAllHitsLabel(self):
        # What the filter says when it shows all hits.
        return self._getString(1)

    def setAllHitsLabel(self, value):
        self._setString(1, value)

    def getSides(self):
        # The filter's sides: all, received, dealt.
        return self._getArray(2)

    def setSides(self, value):
        self._setArray(2, value)

    @staticmethod
    def getSidesType():
        return HitFilterModel

    def getResults(self):
        # The filter's results: all, then data.hits.HitResult.ALL.
        return self._getArray(3)

    def setResults(self, value):
        self._setArray(3, value)

    @staticmethod
    def getResultsType():
        return HitFilterModel

    def getHits(self):
        return self._getArray(4)

    def setHits(self, value):
        self._setArray(4, value)

    @staticmethod
    def getHitsType():
        return HitItemModel

    def getSelectedHit(self):
        # Index of the chosen hit in hits, -1 when there are none.
        return self._getNumber(5)

    def setSelectedHit(self, value):
        self._setNumber(5, value)

    def getHasShellModes(self):
        # A hit of the battle has a known shell mode: the list has the column of its icon.
        return self._getBool(6)

    def setHasShellModes(self, value):
        self._setBool(6, value)

    def _initialize(self):
        super(HitsPanelModel, self)._initialize()
        self._addBoolProperty('isVisible', False)
        self._addStringProperty('allHitsLabel', '')
        self._addArrayProperty('sides', Array())
        self._addArrayProperty('results', Array())
        self._addArrayProperty('hits', Array())
        self._addNumberProperty('selectedHit', -1)
        self._addBoolProperty('hasShellModes', False)
        # {id}, {id}, {index}, {delta}: the filter's lines of a side and of a result, list rows, arrows.
        self.onSideFilter = self._addCommand('onSideFilter')
        self.onResultFilter = self._addCommand('onResultFilter')
        self.onHit = self._addCommand('onHit')
        self.onStep = self._addCommand('onStep')
