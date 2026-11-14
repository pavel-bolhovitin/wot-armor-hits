# -*- coding: utf-8 -*-
"""View model of the mod page card of the hits screen: its two lines (bugs and ideas, the like), the button's label
and the site's domain under it."""
from frameworks.wulf import ViewModel


class ModPageModel(ViewModel):
    __slots__ = ('onOpen',)

    def __init__(self, properties=4, commands=1):
        super(ModPageModel, self).__init__(properties=properties, commands=commands)

    def getBugsText(self):
        return self._getString(0)

    def setBugsText(self, value):
        self._setString(0, value)

    def getLikeText(self):
        return self._getString(1)

    def setLikeText(self, value):
        self._setString(1, value)

    def getOpenLabel(self):
        return self._getString(2)

    def setOpenLabel(self, value):
        self._setString(2, value)

    def getDomain(self):
        return self._getString(3)

    def setDomain(self, value):
        self._setString(3, value)

    def _initialize(self):
        super(ModPageModel, self)._initialize()
        self._addStringProperty('bugsText', '')
        self._addStringProperty('likeText', '')
        self._addStringProperty('openLabel', '')
        self._addStringProperty('domain', '')
        # The page's click on the button, which opens the mod page in the browser.
        self.onOpen = self._addCommand('onOpen')
