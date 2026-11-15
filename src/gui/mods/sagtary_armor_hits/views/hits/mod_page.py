# -*- coding: utf-8 -*-
"""Mod page card of the hits screen: the one link of the mod in the game, to its page on WGMods.

The red bug right of the settings opens a card: a line with the bug (a bug or an idea: the links are on the mod
page), a line with a like (the like button is there too) and a button with the action and the site's domain
under it, so the player sees that it opens a website. ModPagePresenter fills the view model
(views/models/mod_page_model.py) and opens MOD_PAGE_URL in the system browser when the button is clicked, as the
client opens its own external links (IExternalLinksController.open). The texts are the mod's: the client has none
for them.
"""
import urlparse

from helpers import dependency
from skeletons.gui.game_control import IExternalLinksController

from gui.mods.sagtary_armor_hits.config import MOD_PAGE_URL


class ModPagePresenter(object):
    _links = dependency.descriptor(IExternalLinksController)

    def __init__(self, model, texts):
        # texts: {'bugs', 'like', 'open'} in the client language.
        self._model = model
        self._texts = texts

    def init(self):
        with self._model.transaction() as model:
            model.setBugsText(self._texts['bugs'])
            model.setLikeText(self._texts['like'])
            model.setOpenLabel(self._texts['open'])
            model.setDomain(urlparse.urlparse(MOD_PAGE_URL).netloc)
        self._model.onOpen += self._onOpen

    def fini(self):
        self._model.onOpen -= self._onOpen
        self._model = None

    def _onOpen(self, *args):
        self._links.open(MOD_PAGE_URL)
