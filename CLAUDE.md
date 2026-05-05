# CLAUDE.md — norma-robot-bridge (Python 2.7)

Sub-repo af Norma-Chat-2.0. Eksponerer NAOqi-funktionalitet for Pepper/NAO via et HTTP-API. Læs også workspace-roden's `CLAUDE.md` og `README.md` for det store billede.

## Kritisk: Python 2.7-grænser

NAOqi-SDK'et kører kun på Python 2.7. Det er den eneste grund til at vi holder os her — vi flygter ikke til Py 3 før NAOqi-bindingerne (qi) er beviseligt stabile på vores robot.

**Hvad du IKKE må bruge:**
- f-strings (`f"hej {name}"`) — brug `"hej %s" % name` eller `.format()`
- `pathlib` — brug `os.path`
- `typing`-annotationer — brug docstrings eller kommentarer
- `dataclasses` — brug almindelige `class`-definitioner
- `async`/`await`
- Walrus-operator (`:=`)
- Dictionary-merge-operator (`{**a, **b}` virker, men `a | b` gør ikke)

**Brug i toppen af hver fil:**
```python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
```

**Verificér før commit:**
```bash
./.venv27/Scripts/python.exe -m py_compile src/norma_bridge/**/*.py
./.venv27/Scripts/python.exe -m pytest tests/
```

**NAOqi-bundlet Python 2.7-faldgrube:** SDK'ets `python2.exe` (typisk på `C:\tools\python27-nao\bin\`) har en usædvanlig mappe-struktur og kan ikke finde sit `site`-modul uden hjælp. Brug `PYTHONHOME` **inline pr. kommando** når du opretter eller bootstrapper venv'en — aldrig `export`/`$env:`. Når venv'en først er på plads, har den sit eget `pyvenv.cfg` og virker uden tricks. Detaljer i `README.md`. Brug aldrig `export PYTHONHOME=...` — det vil bryde Python 3 i samme shell-session.

## Mappestruktur (nuværende)

```
src/norma_bridge/
├── __init__.py
├── _legacy.py                     # original monolit (læsbar reference; slettes efter smoketest)
├── config.py                      # ENV + INI loader
├── main.py                        # entry point med argparse
├── robot/
│   ├── __init__.py
│   ├── service.py                 # NormaRobotService — ren constructor, RLock-beskyttet
│   ├── tablet.py                  # samlet data-URI/HTML-helpers
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
tests/                             # 164 tests, alle grønne på Py 2.7 + Py 3.12
└── manual.md                      # smoketest-checkliste mod fysisk robot
```

Status: refaktoreringen er færdig pånær smoketesten mod fysisk robot. Når den er bestået, kan `_legacy.py` slettes.

## Threading-mønster

Bridge-serveren er threaded. Alle metoder på `NormaRobotService` der rører ved NAOqi-proxies skal være beskyttet af `self._lock` (en `threading.RLock`). Mønster:

```python
def say(self, text, gesture=None):
    with self._lock:
        # ... NAOqi-kald
        return result
```

RLock er reentrant — én tråd kan tage den flere gange uden deadlock. Det betyder at metoder må kalde hinanden indenfor samme `with`-blok.

## Tilføj en ny kommando — opskrift

1. Tilføj public method på `NormaRobotService` (med `with self._lock:`).
2. Registrér en command-handler i `api/commands.py`:
   ```python
   @registry.register('din_kommando')
   def cmd_din_kommando(service, params):
       arg = params.get('arg')
       if arg is None:
           raise ValueError('params.arg mangler')
       return service.din_kommando(arg)
   ```
3. Tilføj endpoint til `api-spec/openapi.yaml` i samme commit.
4. Skriv test i `tests/test_commands.py` (mod `FakeRobotService`).
5. Tilføj kontrakttest i `tests/test_contract.py`.

**Eksempel — `show_tablet_url`** (planlagt kommando der gør det muligt at pege Norma's tablet på en lokal `norma-ui`-side i stedet for at sende base64-encoded HTML):
```python
@registry.register('show_tablet_url')
def cmd_show_tablet_url(service, params):
    url = params.get('url')
    if not url:
        raise ValueError('params.url mangler')
    return service.show_tablet_url(url)
```
Service-metoden kalder `self._tablet.showWebview(url)` direkte — ingen data-URI-konvertering.

## API-versionering

Endpoints lever på `/api/...` uden versions-prefix. Hvis vi en dag laver en breaking change, indfører vi `/api/v2/...` parallelt med de uversionerede endpoints, så klienter kan migrere kontrolleret. Indtil da: YAGNI — versions-prefix tilføjer kun friktion uden modydelse mens vi har én klient.

## Fejlhåndtering

- `ValueError` fra command-handler → HTTP 400 (klient-fejl)
- Andre exceptions → HTTP 500 (intern fejl)
- Logning skal route gennem stdlib `logging` — ikke `print()`. Stille `try/except: pass` er ikke tilladt undtagen i `intro.py` hvor det er bevidst (ét intro-trin må ikke vælte de andre).

## Hvad ligger i `_legacy.py`?

Den oprindelige monolit, uændret. Brug den som kildeangivelse når du ekstraherer kode til de nye moduler. Slet den ikke før refaktoreringen er fuldført og alle dens funktioner er flyttet ud.
