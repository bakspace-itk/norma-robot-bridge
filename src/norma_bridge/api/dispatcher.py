# -*- coding: utf-8 -*-
"""Command-dispatcher med decorator-baseret registry.

Erstatter ``_legacy.py:_dispatch`` (linjer 294-319), der havde dispatch-logikken
som en if/elif-kaede der voksede ukontrollabelt med antallet af kommandoer.

Registry-moenstret giver:

- Hver kommando er en self-contained funktion der kan unit-testes uafhaengigt.
- At tilfoeje en ny kommando er en enkelt ``@registry.register(...)`` - ingen
  aendringer til dispatcher eller handler.
- Klare 400 vs 500 fejl-koder via konsekvent ``ValueError``-konvention.
"""

from __future__ import print_function, unicode_literals


class CommandRegistry(object):
    """Mapping fra kommando-navn til handler-funktion.

    En handler har signaturen ``handler(service, params) -> dict``. Den maa
    hejse:

    - ``ValueError`` for klient-fejl (manglende parametre, ugyldigt format) ->
      converteres til HTTP 400 af handler-laget.
    - Andre exceptions for intern/NAOqi-fejl -> HTTP 500.
    """

    def __init__(self):
        self._commands = {}

    def register(self, name):
        """Decorator der registrerer en handler under ``name``.

        Brug:
            @registry.register('say')
            def cmd_say(service, params): ...
        """
        key = (name or "").strip().lower()
        if not key:
            raise ValueError("kommando-navn maa ikke vaere tomt")

        def deco(fn):
            if key in self._commands:
                raise ValueError(
                    "Kommando '%s' er allerede registreret" % key
                )
            self._commands[key] = fn
            return fn

        return deco

    def dispatch(self, service, name, params):
        """Slaa ``name`` op og kald den med ``(service, params or {})``.

        Hejser ``ValueError`` hvis kommandoen ikke findes - handler-laget
        skal converte det til HTTP 400.
        """
        key = (name or "").strip().lower()
        if not key:
            raise ValueError("command mangler")
        handler = self._commands.get(key)
        if handler is None:
            raise ValueError("Ukendt kommando: %s" % name)
        return handler(service, params or {})

    def names(self):
        """Returner en sorteret liste over registrerede kommando-navne.

        Anvendes af ``get_status`` og fejlmeddelelser.
        """
        return sorted(self._commands.keys())


# Modul-globalen som ``commands.py`` registrerer paa og handler-laget bruger.
# Hvis du har brug for en isoleret registry (fx i tests), instantier
# ``CommandRegistry()`` direkte i stedet.
registry = CommandRegistry()
