# -*- coding: utf-8 -*-
"""Hooks on the client's methods the server calls (BigWorld remote methods of the entities).

ClientHooks wraps a method of a client class once, whoever listens to it: the debug record (debug_recorder.py) and
the hits (hit_collector.py) listen to the same calls. The wrapper gives each call (Call) to the method's listeners in
the order they started to listen, then calls the client's own method with the same arguments and returns what it
returns: the listeners only read the call, before the client handles it. A listener that fails is logged and the
others and the client's method still get the call. The client's method is put back when its last listener stops.

A call's arguments are known by the client's own names, each by its place in the call (_KNOWN_ARGS): the function in
the class can be a hook of another mod, with names of its own or only some of them. A call with another number of
arguments than _KNOWN_ARGS tells the client has changed them: logged once a method.
"""
import logging

_logger = logging.getLogger('sagtary.armor_hits')

# Argument names of the client 2.4.1 methods, in their order; every method listened to has its names here.
_KNOWN_ARGS = {
    'showDamageFromShot': ('attackerID', 'hitPoints', 'effectsIndex', 'prefabEffIndex', 'damage', 'damageFactor',
                           'lastMaterialIsShield', 'shellVelocity', 'gunInstallationIndex'),
    'showDamageFromExplosion': ('attackerID', 'center', 'effectsIndex', 'damage', 'damageFactor',
                                'gunInstallationIndex'),
    'onHealthChanged': ('newHealth', 'oldHealth', 'attackerID', 'attackReasonID', 'attackReasonExtID'),
    'showTracer': ('shooterID', 'shotID', 'isRicochet', 'effectsIndex', 'prefabEffIndex', 'shellTypeIdx',
                   'shellCaliber', 'refStartPoint', 'velocity', 'gravity', 'maxShotDist', 'gunIndex',
                   'gunInstallationIndex'),
    'stopTracer': ('shotID', 'endPoint'),
    'explodeProjectile': ('shotID', 'effectsIndex', 'prefabEffIndex', 'effectMaterialIndex', 'shellTypeIdx',
                          'shellCaliber', 'endPoint', 'velocityDir', 'speed', 'damagedDestructibles'),
    'showShotResults': ('results',),
    'showOwnVehicleHitDirection': ('hitDirYaw', 'attackerID', 'damage', 'crits', 'isBlocked', 'isShellHE',
                                   'damagedID', 'attackReasonID'),
    'showVehicleDamageInfo': ('vehicleID', 'damageIndex', 'extraIndex', 'entityID', 'equipmentID',
                              'ignoreMessages'),
    'showOtherVehicleDamagedDevices': ('vehicleID', 'damagedExtras', 'destroyedExtras'),
    'updateVehicleHealth': ('vehicleID', 'health', 'deathReasonID', 'isCrewActive', 'isRespawn'),
    'onBattleEvents': ('events',),
    'battleEventsSummary': ('summary',),
}


class Call(object):
    # One call of a client method: its class and name, the entity it is called on, its arguments.
    __slots__ = ('cls', 'name', 'entity', 'args', 'kwargs', 'argNames')

    def __init__(self, cls, name, entity, args, kwargs, argNames):
        self.cls, self.name, self.entity = cls, name, entity
        self.args, self.kwargs, self.argNames = args, kwargs, argNames

    def get(self, name):
        # The argument of the name, None when the call does not have it.
        if name in self.kwargs:
            return self.kwargs[name]
        index = self.argNames.index(name) if name in self.argNames else len(self.args)
        return self.args[index] if index < len(self.args) else None

    def arguments(self):
        # {name: argument}; the arguments past the known names under '*'.
        result = dict(zip(self.argNames, self.args))
        if len(self.args) > len(self.argNames):
            result['*'] = list(self.args[len(self.argNames):])
        result.update(self.kwargs)
        return result


class ClientHooks(object):

    def __init__(self):
        # {(class, method name): original function}, {(class, method name): [listener]}
        self._originals = {}
        self._listeners = {}
        # The method names already logged as called with another number of arguments than _KNOWN_ARGS.
        self._warned = set()

    def listen(self, cls, name, listener):
        # The listener gets each call of the method (Call); False when the client has no such method.
        key = (cls, name)
        if key not in self._originals:
            if name not in cls.__dict__:
                _logger.warning('hooks: %s.%s not in this client', cls.__name__, name)
                return False
            self._wrap(cls, name)
        self._listeners[key].append(listener)
        return True

    def stop(self, cls, name, listener):
        # The listener gets no more calls; the client's method is put back after its last listener.
        key = (cls, name)
        listeners = self._listeners.get(key)
        if not listeners or listener not in listeners:
            return
        listeners.remove(listener)
        if not listeners:
            setattr(cls, name, self._originals.pop(key))
            del self._listeners[key]

    def _checkArguments(self, call):
        count = len(call.args) + len(call.kwargs)
        if count != len(call.argNames) and call.name not in self._warned:
            self._warned.add(call.name)
            _logger.warning('hooks: %s.%s has %d arguments, %d expected', call.cls.__name__, call.name, count,
                            len(call.argNames))

    def _wrap(self, cls, name):
        key = (cls, name)
        original = cls.__dict__[name]
        argNames = _KNOWN_ARGS[name]
        hooks = self
        # The method is bound to the entity the way Python binds it for the client's own call: the object in the class
        # can be a hook of another mod that is no function (a staticmethod, a descriptor, a callable object).
        bind = getattr(type(original), '__get__', None)

        def wrapper(entity, *args, **kwargs):
            call = Call(cls, name, entity, args, kwargs, argNames)
            hooks._checkArguments(call)
            for listener in list(hooks._listeners.get(key, ())):
                try:
                    listener(call)
                except Exception:
                    _logger.exception('hooks: %s cannot read %s.%s', getattr(listener, '__name__', listener),
                                      cls.__name__, name)
            method = bind(original, entity, type(entity)) if bind is not None else original
            return method(*args, **kwargs)

        wrapper.__name__ = name
        self._originals[key] = original
        self._listeners[key] = []
        setattr(cls, name, wrapper)
