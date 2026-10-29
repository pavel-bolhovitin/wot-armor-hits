# -*- coding: utf-8 -*-
"""Button in the hangar footer, next to the game menu button.

The view and its layout are the client's own Gameface API: the layout is declared in
res/gui/gen_resources/sagtary_armor_hits.json and found as R.mods.sagtary_armor_hits.views.FooterButton.
The footer draws only its own children, so the button gets into the footer page by a script:
OpenWG Gameface (gf_mod_inject) loads it into the page, and the script puts the button before the menu button.
"""
import importlib
import logging

from gui.impl.gen import R
from gui.impl.pub.view_component import ViewComponent

from gui.mods.sagtary_armor_hits.lang import text
from gui.mods.sagtary_armor_hits.views.models.footer_button_model import FooterButtonModel

_logger = logging.getLogger('sagtary.armor_hits')

# The footer of each hangar: the default one and those of the modes with their own footer.
_FOOTERS = (
    ('gui.impl.lobby.page.lobby_footer', 'LobbyFooter'),
    ('comp7.gui.impl.lobby.page.lobby_footer', 'Comp7LobbyFooter'),
    ('comp7_light.gui.impl.lobby.page.lobby_footer', 'Comp7LightLobbyFooter'),
    ('last_stand.gui.impl.lobby.page.ls_lobby_footer', 'LSLobbyFooter'),
    ('battle_royale.gui.Scaleform.daapi.view.lobby.footer.battle_royale_lobby_footer', 'BattleRoyaleLobbyFooter'),
)


class _FooterButtonView(ViewComponent[FooterButtonModel]):

    def __init__(self, onClick):
        super(_FooterButtonView, self).__init__(layoutID=R.mods.sagtary_armor_hits.views.FooterButton(),
                                                model=FooterButtonModel)
        self._onClick = onClick

    def _getEvents(self):
        return ((self.getViewModel().onClick, self.__onClick),)

    def _onLoading(self, *args, **kwargs):
        super(_FooterButtonView, self)._onLoading(*args, **kwargs)
        with self.getViewModel().transaction() as model:
            model.setTitle(text('lobbyButton/name'))
            model.setDescription(text('lobbyButton/description'))

    def __onClick(self, *args):
        self._onClick()


class FooterButton(object):
    # Adds the button view to every footer when the footer creates its children.

    def __init__(self, onClick):
        self._onClick = onClick
        # [(footer class, original _initChildren)]
        self._patched = []

    def add(self):
        for path, name in _FOOTERS:
            try:
                cls = getattr(importlib.import_module(path), name)
            except (ImportError, AttributeError):
                # A mode that is not in this client.
                continue
            self._patch(cls)

    def remove(self):
        for cls, original in self._patched:
            cls._initChildren = original
        self._patched = []

    def _patch(self, cls):
        original = cls._initChildren
        onClick = self._onClick

        def _initChildren(footer):
            original(footer)
            try:
                footer.setChildView(R.mods.sagtary_armor_hits.views.FooterButton(), _FooterButtonView(onClick))
            except Exception:
                _logger.exception('cannot add the footer button to %s', cls.__name__)

        cls._initChildren = _initChildren
        self._patched.append((cls, original))
