# -*- coding: utf-8 -*-
"""Battle file format 1 to format 2.

Format 1 keeps a list of battles (battles); format 2 is one battle a file: the fields of the file and of the battle
together. Of the list only the first battle is read, no battle gives a file without one.

Format 2 keeps a hit on the player's vehicle with its crits mask (crits) and without the count of its battle event
(critsCount); a hit of the player keeps that count and no damaged devices (damagedDevices).

A hit of format 1 has no mask: its crits come from its damaged devices. The server tells a device only when its state
changes, so a hit that has only the count gets no crits. Format 1 may also not know that a player's shell was a premium
one: a dealt hit is one when the player's gun has only a premium shell of its kind.
"""
from items.vehicles import VehicleDescr

# The crits mask's kind of a damage info code.
_CRIT_KINDS = {
    'DEVICE_CRITICAL_AT_SHOT': 'criticalDevices',
    'DEVICE_DESTROYED_AT_SHOT': 'destroyedDevices',
    'TANKMAN_HIT_AT_SHOT': 'destroyedTankmen',
    'DEATH_FROM_DEVICE_EXPLOSION_AT_SHOT': 'destroyedDevices',
}


def _records(value):
    # The records of a JSON list, nothing of anything else.
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _crits(hit):
    # The hit's crits, as the mask's would be: one for each kind of device, in a fixed order.
    found = set()
    for device in _records(hit.get('damagedDevices')):
        kind = _CRIT_KINDS.get(device.get('code'))
        if kind is not None and device.get('device'):
            found.add((kind, device['device']))
    return [{'kind': kind, 'device': name} for kind, name in sorted(found)]


def _premiumKinds(vehicleDescriptor):
    # The shell kinds of the player's gun (a compact descriptor, hex) that are only a premium shell; none if not known.
    try:
        shells = [shot.shell for shot in VehicleDescr(compactDescr=vehicleDescriptor.decode('hex')).gun.shots]
    except Exception:
        return frozenset()
    kinds = [shell.kind for shell in shells]
    return frozenset(shell.kind for shell in shells if shell.isGold and kinds.count(shell.kind) == 1)


def convert(data):
    battles = _records(data.get('battles'))
    battle = battles[0] if battles else {}
    receivedHits = _records(battle.get('receivedHits'))
    for hit in receivedHits:
        hit['crits'] = _crits(hit)
        hit.pop('critsCount', None)
    dealtHits = _records(battle.get('dealtHits'))
    premiumKinds = _premiumKinds(battle.get('vehicleDescriptor'))
    for hit in dealtHits:
        hit.pop('damagedDevices', None)
        if hit.get('shellType') in premiumKinds:
            hit['isGoldShell'] = True
    converted = dict(battle, receivedHits=receivedHits, dealtHits=dealtHits)
    for name in ('appVersion', 'exportTime'):
        if name in data:
            converted[name] = data[name]
    return converted
