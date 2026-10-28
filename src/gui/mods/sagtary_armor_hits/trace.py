# -*- coding: utf-8 -*-
"""Call counts, timings and checks for the log: to find calls made more often than needed, calls that take too long,
and why a hit's numbers do not match what the screen shows.

calls(name, details) logs a call with the prefix "calls:", its number and the milliseconds since the last call of the
same name; a quiet call (every shell hit in battle) is only counted. timed(name) times a function (@timed(name)) or a
block (with timed(name):), with the prefix "timing:": a call of _SLOW seconds or more is logged as it happens (it makes
a frame late), and every _BUDGET seconds the time all the outermost timed calls took then, which is also their share
of every frame's time. summary(title) logs the counts and the timings (calls, total, average, longest) since the last
summary and starts again: the hits screen logs one when it opens (the battle's calls) and one when it closes. The
checks of a hit log with the prefix "check:" (shot_panel.py, hit_lines.py); hitText and modulesText are their texts of
a hit and of a vehicle's modules.

The mod's info lines are written only with the debug setting (setVerbose), and only then the calls are timed;
warnings and errors always. A few lines go to every log through mainLogger: the start, the battle files written, read
and deleted.
"""
import logging
import time
from functools import wraps

import BigWorld

_logger = logging.getLogger('sagtary.armor_hits')
# Its own level: its info lines pass whatever the level of the mod's logger is.
mainLogger = logging.getLogger('sagtary.armor_hits.main')
mainLogger.setLevel(logging.INFO)

# {name: calls since the last summary}, {name: BigWorld.time() of the last call}
_counts = {}
_lastTimes = {}
# Seconds of one timed call logged as slow; seconds between the logs of the time the timed calls took.
_SLOW = 0.005
_BUDGET = 1.0
# The calls are timed (the debug setting); {name: [calls, total seconds, longest seconds]} since the last summary;
# the timed calls running now, one inside another; time.clock() the budget started at, seconds its outermost calls
# took, their number.
_isTiming = False
_timings = {}
_depth = 0
_budgetSince = None
_budgetSeconds = 0.0
_budgetCalls = 0
# constants.VEHICLE_HIT_EFFECT names by their values.
_EFFECT_NAMES = {0: 'piercedNoDamage', 1: 'ricochet', 2: 'finalRicochet', 3: 'notPierced', 4: 'pierced',
                 5: 'critical', 6: 'piercedDeviceDamaged'}


def setVerbose(isOn):
    global _isTiming
    _logger.setLevel(logging.INFO if isOn else logging.WARNING)
    _isTiming = bool(isOn)


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
    if _timings:
        _logger.info('timing: %s: %s', title, '; '.join(
            '%s %d calls, total %.1f ms, average %.3f ms, longest %.2f ms' % (
                name, count, total * 1000, total * 1000 / count, longest * 1000)
            for name, (count, total, longest) in sorted(_timings.items())))
    _timings.clear()


class timed(object):
    """Times a function, @timed(name), or a block, with timed(name):; only with the debug setting."""
    __slots__ = ('_name', '_start')

    def __init__(self, name):
        self._name = name
        self._start = None

    def __call__(self, function):
        name = self._name

        @wraps(function)
        def wrapper(*args, **kwargs):
            if not _isTiming:
                return function(*args, **kwargs)
            start = _begin()
            try:
                return function(*args, **kwargs)
            finally:
                _end(name, start)

        return wrapper

    def __enter__(self):
        if _isTiming:
            self._start = _begin()
        return self

    def __exit__(self, *exception):
        if self._start is not None:
            _end(self._name, self._start)
            self._start = None
        return False


def _begin():
    global _depth
    _depth += 1
    return time.clock()


def _end(name, start):
    global _depth, _budgetSince, _budgetSeconds, _budgetCalls
    now = time.clock()
    seconds = now - start
    _depth -= 1
    timing = _timings.get(name)
    if timing is None:
        _timings[name] = [1, seconds, seconds]
    else:
        timing[0] += 1
        timing[1] += seconds
        if seconds > timing[2]:
            timing[2] = seconds
    if seconds >= _SLOW:
        _logger.warning('timing: SLOW %s took %.1f ms', name, seconds * 1000)
    if _depth:
        return
    # The outermost calls only: the inner ones are in their time.
    if _budgetSince is None:
        _budgetSince = start
    _budgetSeconds += seconds
    _budgetCalls += 1
    elapsed = now - _budgetSince
    if elapsed >= _BUDGET:
        _logger.info('timing: in %.1f s the timed calls took %.2f ms (%.2f%% of every frame), %d calls', elapsed,
                     _budgetSeconds * 1000, _budgetSeconds * 100 / elapsed, _budgetCalls)
        _budgetSince = now
        _budgetSeconds = 0.0
        _budgetCalls = 0


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
