# -*- coding: utf-8 -*-
"""The hangar button that opens the viewer.

ModsList API is optional. When it is installed (and the showButtonInModsMenu setting is on), the button is an entry in its
mods list. Otherwise it is a button of its own in the hangar footer next to the game menu button; that needs
OpenWG Gameface.
"""
import logging

from gui.mods.sagtary_armor_hits.optional_mods import gfModInject, modsListApi
from gui.mods.sagtary_armor_hits.views.lobby_button.footer_button import FooterButton
from gui.mods.sagtary_armor_hits.views.lobby_button.mods_list_entry import ModsListEntry

_logger = logging.getLogger('sagtary.armor_hits')


class LobbyButton(object):

    def __init__(self, onClick):
        self._onClick = onClick
        self._button = None

    def add(self, inModsMenu):
        api = modsListApi() if inModsMenu else None
        if api is not None:
            self._button = ModsListEntry(api, self._click)
        elif gfModInject() is not None:
            self._button = FooterButton(self._click)
        else:
            _logger.warning('no lobby button: it needs OpenWG Gameface (or ModsList API with showButtonInModsMenu on)')
            return
        self._button.add()

    def remove(self):
        if self._button is not None:
            self._button.remove()
            self._button = None

    def _click(self):
        try:
            self._onClick()
        except Exception:
            _logger.exception('lobby button click failed')
