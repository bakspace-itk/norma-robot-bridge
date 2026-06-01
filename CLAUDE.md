# CLAUDE.md — pepper-robot-bridge (Python 2.7)

Generisk HTTP-bridge der eksponerer NAOqi-funktionalitet (TTS, animationer, tablet) for Pepper/NAO via et JSON-API. Pakken er pip-installerbar fra source eller git (`pip install -e .` eller `pip install git+https://.../pepper-robot-bridge.git`) men er **ikke publiceret på offentlig PyPI** — NAOqi kan ikke deklareres som pip-dependency, og pip-økosystemet droppede Py 2.7 i 2021. Kerne-koden skal alligevel være neutral og genbrugelig på tværs af projekter. Projekt-specifik logik (fraser, intro-tekster, gesture-valg) hører hjemme i klienten eller i konfigurationen, ikke i `src/`.

## Kritisk: Python 2.7-grænser

NAOqi-SDK'et kører kun på Python 2.7. Det er den eneste grund til at vi holder os her — vi flygter ikke til Py 3 før NAOqi-bindingerne (qi) er beviseligt stabile på vores robotter.

**Hvad du IKKE må bruge:**
- f-strings (`f"hej {name}"`) — brug `"hej %s" % name` eller `.format()`
- `pathlib` — brug `os.path`
- `typing`-annotationer — brug docstrings eller kommentarer
- `dataclasses` — brug almindelige `class`-definitioner
- `async`/`await`
- Walrus-operator (`:=`)
- Dictionary-merge-operator (`a | b` virker ikke; `{**a, **b}` gør)

**Brug i toppen af hver fil:**
```python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
```

**Verificér før commit** (med miljøet aktiveret via `activate-with-naoqi.{sh,bat}` eller plain venv):
```bash
python -m py_compile src/pepper_bridge/**/*.py
pytest tests/
```

**NAOqi-bundlet Python 2.7:** SDK'ets `python2.exe` har et usædvanligt layout der kræver `PYTHONHOME` inline ved venv-oprettelsen. `scripts/setup-windows.bat` håndterer det via et tredje positionsargument — kør aldrig `export PYTHONHOME=...` / `$env:PYTHONHOME=...` uden for den scope, det vil bryde Python 3 i samme shell-session. Detaljer i `scripts/README.md`.

## Mappestruktur

```
src/pepper_bridge/
├── __init__.py
├── config.py                      # ENV + INI loader
├── main.py                        # entry point med argparse
├── robot/
│   ├── __init__.py
│   ├── service.py                 # PepperRobotService — RLock-beskyttet NAOqi-wrapper
│   ├── tablet.py                  # data-URI/HTML-helpers
│   ├── gestures.py                # cycling-logik + DEFAULT_GESTURES
│   ├── intro.py                   # IntroConfig + run_intro(service, config)
│   └── fakes.py                   # FakeRobotService til tests/dev
└── api/
    ├── __init__.py
    ├── dispatcher.py              # CommandRegistry med @register decorator
    ├── commands.py                # @registry.register('say') osv. (7 kommandoer)
    ├── handlers.py                # make_handler(service) factory + 400/500-routing
    └── server.py                  # ThreadedHTTPServer + serve()

config/default.ini                 # kommenteret reference for alle config-nøgler
api-spec/openapi.yaml              # API-kontrakt
tests/                             # 187 tests, grønne på Py 2.7 + Py 3.12
└── manual.md                      # smoketest-checkliste mod fysisk robot
```

## Threading-mønster

Bridge-serveren er threaded. Alle metoder på `PepperRobotService` der rører ved NAOqi-proxies skal være beskyttet af `self._lock` (en `threading.RLock`). Mønster:

```python
def say(self, text, gesture=None):
    with self._lock:
        # ... NAOqi-kald
        return result
```

RLock er reentrant — én tråd kan tage den flere gange uden deadlock. Det betyder at metoder må kalde hinanden indenfor samme `with`-blok.

## Tilføj en ny kommando — opskrift

1. Tilføj public method på `PepperRobotService` (med `with self._lock:`).
2. Tilføj samme metode på `FakeRobotService` med samme return-kontrakt — testene afhænger af 1:1-paritet.
3. Registrér en command-handler i `api/commands.py`:
   ```python
   @registry.register('din_kommando')
   def cmd_din_kommando(service, params):
       arg = params.get('arg')
       if arg is None:
           raise ValueError('params.arg mangler')
       return service.din_kommando(arg)
   ```
4. Tilføj endpoint til `api-spec/openapi.yaml` i samme commit.
5. Skriv test i `tests/test_commands.py` (mod `FakeRobotService`) og i `tests/test_service.py` (mod mockede ALProxies).

## API-versionering

Endpoints lever på `/api/...` uden versions-prefix. Hvis en breaking change bliver nødvendig, indfører vi `/api/v2/...` parallelt med de uversionerede endpoints, så klienter kan migrere kontrolleret. Indtil da: YAGNI.

## Fejlhåndtering

- `ValueError` fra command-handler → HTTP 400 (klient-fejl)
- `IOError`/`OSError` (klient-angivet sti findes ikke) → HTTP 400
- Andre exceptions → HTTP 500 (intern fejl)
- Logning skal route gennem stdlib `logging` — ikke `print()`. Stille `try/except: pass` er ikke tilladt undtagen i `intro.py` hvor det er bevidst (ét intro-trin må ikke vælte de andre).

## Hold pakken generisk

Kerne-koden under `src/` skal kunne installeres via `pip install pepper-robot-bridge` og bruges på en fabriksny Pepper uden at vide hvad det specifikke projekt hedder. Brand-specifikke fraser, tekster og workflow-detaljer hører hjemme i:

- `config/local.ini` (per-deployment)
- klient-koden der kalder bridge'en
- separate eksempel-projekter

Hvis du finder dig selv i færd med at tilføje en hilsen eller en projektreference i `src/`, så stop og overvej om det ikke hører hjemme et andet sted.
