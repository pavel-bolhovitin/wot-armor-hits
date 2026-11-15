# -*- coding: utf-8 -*-
"""Battle file format 3 to format 4.

Format 4 keeps the battle's vehicle catalog (vehicleCatalog): each vehicle of each player the hits met, once. Format 3
does not have it, so its battles get the default: an empty catalog.
"""


def convert(data):
    return dict(data)
