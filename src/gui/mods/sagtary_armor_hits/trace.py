# -*- coding: utf-8 -*-
"""Call counts and checks for the log: to find calls made more often than needed, and why a hit's numbers do not
match what the screen shows.

calls(name, details) logs a call with the prefix "calls:", its number and the milliseconds since the last call of the
same name; a quiet call (every shell hit in battle) is only counted. summary(title) logs the counts since the last
summary and starts again: the hits screen logs one when it opens (the battle's calls) and one when it closes. The
checks of a hit log with the prefix "check:" (shot_panel.py, hit_lines.py); hitText and modulesText are their texts of
a hit and of a vehicle's modules.

The mod's info lines are written only with the debug setting (setVerbose); warnings and errors always. A few lines go
to every log through mainLogger: the start, the battle files written, read and deleted.
"""
import logging

import BigWorld

_logger = logging.getLogger('sagtary.armor_hits')
# Its own level: its info lines pass whatever the level of the mod's logger is.
mainLogger = logging.getLogger('sagtary.armor_hits.main')
mainLogger.setLevel(logging.INFO)

# {name: calls since the last summary}, {name: BigWorld.time() of the last call}
_counts = {}
_lastTimes = {}
# constants.VEHICLE_HIT_EFFECT names by their values.
_EFFECT_NAMES = {0: 'piercedNoDamage', 1: 'ricochet', 2: 'finalRicochet', 3: 'notPierced', 4: 'pierced',
                 5: 'critical', 6: 'piercedDeviceDamaged'}


def setVerbose(isOn):
    _logger.setLevel(logging.INFO if isOn else logging.WARNING)


def calls(name, details='', quiet=False):
    now = BigWorld.time()
    count = _counts.get(name, 0) + 1
    _counts[name] = count
    last = _lastTimes.get(name)
    _lastTimes[name] = now
    if quiet or not _logger.isEnabledFor(logging.INFO):
        return
    since = '+%.0f ms' % ((now - last) * 1000) if last is not None else 'first'
    _logger.info('calls: %s #%d (%s)%s', name, count, since, ': ' + details if details else '')


def summary(title):
    if _counts:
        _logger.info('calls: %s: %s', title, ', '.join('%s %d' % item for item in sorted(_counts.items())))
    _counts.clear()
    _lastTimes.clear()


def modulesText(descriptor):
    # The vehicle and its chassis, turret and gun names.
    if descriptor is None:
        return 'none'
    try:
        return '%s (chassis %s, turret %s, gun %s)' % (descriptor.type.name, descriptor.chassis.name,
                                                       descriptor.turret.name, descriptor.gun.name)
    except Exception:
        return 'unknown modules of %r' % descriptor


def effectsText(effects):
    return '[%s]' % ', '.join(_EFFECT_NAMES.get(effect, str(effect)) for effect in effects)


def poseText(pose):
    if pose is None:
        return 'none'
    return 'turret %s, gun %s' % (pose.turretYaw, pose.gunPitch)


def hitText(hit):
    # All the hit's data as recorded.
    points = ', '.join('part %s %s hit type %s %s-%s' % (
        point.tankPartIndex, _EFFECT_NAMES.get(point.effectCode, point.effect),
        _EFFECT_NAMES.get(point.hitTypeCode, point.hitType), point.start, point.end) for point in hit.points)
    devices = ', '.join('%s %s' % (device.extra or device.device, device.code) for device in hit.damagedDevices)
    return ('time %.2f, vehicle %s, player %s, teams %s-%s, shell %s%s %s mm, damage %s, crits %s, effects %s, '
            'splash %s, distance %s, compact descriptor %s, points [%s], devices [%s], splash center %s, '
            'shot direction %s, pose [%s]') % (
        hit.time, hit.vehicleId, hit.playerName, hit.attackerTeam, hit.targetTeam, hit.shellType,
        ' gold' if hit.isGoldShell else '', hit.caliber, hit.damage, hit.critsCount, effectsText(hit.hitEffects),
        hit.isSplash, hit.distance, 'yes' if hit.vehicleDescriptor else 'no', points, devices, hit.splashCenter or None,
        hit.shotDirection or None, poseText(hit.vehiclePose))
