# norma-robot-bridge

HTTP-bridge der eksponerer NAOqi-funktionalitet (TTS, animationer, tablet) for Pepper/NAO via et JSON-API på port 8080. Skrevet i **Python 2.7** fordi NAOqi-SDK'et kræver det.

Dette repo er et sub-repo af Norma-Chat-2.0-workspace'et. Se workspace-roden for det store billede.

## Status

Refaktorering færdig: monolitten fra `src/norma_bridge/_legacy.py` er erstattet af modulerne under `robot/` og `api/`. Bridge er fuldt funktionel i `--fake`-mode (lokal udvikling uden NAOqi) og klar til smoketest mod fysisk robot — se [tests/manual.md](tests/manual.md).

`_legacy.py` ligger stadig som læsbar reference indtil smoketesten er bestået; derefter kan den slettes.

**164 tests grønne** på både Python 2.7 og Python 3.12.

## Forudsætninger

- Python 2.7 (NAOqi-krav)
- NAOqi SDK installeret og importerbar (`from naoqi import ALProxy`)
- Netværksforbindelse til robotten (default port 9559)

## Installation

Brug setup-scripts'ne i [scripts/](scripts/) — de opretter `.venv27/`, installerer pakken med `pip install -e ".[test]"` og genererer en `activate-with-naoqi.{sh,bat}`-helper der sætter både venv og pynaoqi-`PYTHONPATH`. Se [scripts/README.md](scripts/README.md) for forudsætninger (Python 2.7, pip, NAOqi-SDK) og platform-specifikke kald.

```bash
# Linux
./scripts/setup-linux.sh --naoqi-sdk /opt/aldebaran/pynaoqi-python2.7-2.5.5.5-linux64

# Windows cmd
scripts\setup-windows.bat C:\tools\pynaoqi
```

NAOqi-SDK'ets bundlede Python 2.7 har et usædvanligt layout der kræver `PYTHONHOME` inline ved venv-oprettelsen — `setup-windows.bat` håndterer det automatisk via et tredje positionsargument. Detaljer i [scripts/README.md](scripts/README.md).

## Kør

Aktivér først miljøet (helperen oprettes af setup-scriptet):

```bash
# Linux
source ./activate-with-naoqi.sh

# Windows cmd
activate-with-naoqi.bat
```

Så:

```bash
# Mod ægte robot (kræver config-fil med din robots IP)
python -m norma_bridge.main --config config/local.ini

# Lokal udvikling med FakeRobotService (ingen NAOqi påkrævet)
python -m norma_bridge.main --fake --port 8080

# Spring intro over (hurtig genstart under udvikling)
python -m norma_bridge.main --fake --no-intro
```

For ren fake-mode (uden NAOqi-import) er plain venv-aktivering nok — `source .venv27/bin/activate` på Linux, `.\.venv27\Scripts\Activate.ps1` i PowerShell. Det er det `scripts/dev-up.{ps1,sh}` bruger.

CLI-args overstyrer config-fil overstyrer ENV-vars overstyrer kodede defaults. Se `python -m norma_bridge.main --help` for komplet liste.

## API

API'et eksponeres på `http://<host>:8080/api/...`. Kontrakten ligger i [api-spec/openapi.yaml](api-spec/openapi.yaml) — alle 7 kommandoer dokumenteret med præcise request/response-skemaer, fejl-koder og eksempler. `tests/test_openapi_consistency.py` verificerer at spec og kode forbliver synkrone.

Endpoints:
- `GET /api/status` — server- og robot-status
- `POST /api/command` — udfør en kommando

Kommandoer (v1):
- `say` — TTS, evt. med gesture
- `play_gesture` — afspil named gesture
- `show_tablet_image` — vis lokalt billede på tablet (legacy, base64 data-URI)
- `show_tablet_html` — vis HTML-streng på tablet (legacy, base64 data-URI)
- `show_tablet_url` — peg tablet-WebView på en URL (foretrukket for `norma-ui`-integration)
- `hide_tablet`
- `get_status`

`show_tablet_image` og `show_tablet_html` beholdes for bagudkompatibilitet og lokale eksperimenter, men det normale flow i den nye arkitektur er at peg tabletten på `norma-ui` via `show_tablet_url`.

### Request/response-format

Kommandoer sendes som JSON på `POST /api/command`:
```json
{"command": "<navn>", "params": {...}}
```

Svar er enten succes eller fejl:
```json
{"status": "success", "data": {...}}
{"status": "error",   "message": "<beskrivelse>"}
```

HTTP-koder: `200` ved succes, `400` ved klient-fejl (manglende parameter, ukendt kommando), `500` ved intern/NAOqi-fejl.

### Eksempler (curl)

```bash
# Status
curl http://<host>:8080/api/status

# Sig noget med gesture
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"say","params":{"text":"Hej","gesture":"animations/Stand/Gestures/Hey_1"}}'

# Afspil gesture
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"play_gesture","params":{"gesture_name":"animations/Stand/Gestures/BowShort_1"}}'

# Peg tablet på norma-ui
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_url","params":{"url":"http://norma-ui.local:8000/dialog"}}'

# Vis lokalt billede (legacy)
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_image","params":{"image_path":"C:\\path\\to\\image.png"}}'

# Skjul tablet-webview
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"hide_tablet","params":{}}'
```

### Hurtig integration fra Python 3

Eksempel — sådan kalder `norma-input` (eller en hvilken som helst Py 3-klient) bridge'en:

```python
import requests

BASE = "http://<host>:8080/api"

def cmd(name, **params):
    r = requests.post(f"{BASE}/command",
                      json={"command": name, "params": params},
                      timeout=10)
    r.raise_for_status()
    return r.json()["data"]

# Sig noget
cmd("say", text="Hej fra Python 3", gesture="hello")

# Peg tablet på norma-ui
cmd("show_tablet_url", url="http://norma-ui.local:8000/dialog")

# Status
print(requests.get(f"{BASE}/status").json())
```

Klient-koden i `norma-input/src/norma_input/robot_client.py` (kommer i Fase 3) er en pænere indpakning af præcis dette mønster.

### Fejlfinding

- **`{"status":"error","message":"NAOqi ALProxy ikke tilgængelig"}`** — NAOqi SDK er ikke installeret eller ikke importerbar i Py 2.7-miljøet. Verificér med `python2 -c "from naoqi import ALProxy; print('OK')"`.
- **Forbindelse nægtes til robot** — tjek `ROBOT_IP`/`ROBOT_PORT` i config, og at robotten kan ping'es fra værtsmaskinen.
- **`Connection refused` på port 8080** — bridge kører ikke, eller en anden proces holder porten. Skift port i config eller stop den anden proces.
- **Tablet viser intet** — billedstien skal være eksisterende på *bridge-maskinen* (ikke klientens). Tjek logs for `Billedfil ikke fundet`.
- **`æøå` virker forkert** — alle requests skal være UTF-8. `requests` i Py 3 sender automatisk UTF-8.
- **Samtidige kald** — bridge er threaded og alle robotkald er beskyttet med en re-entrant lock; flere klienter må gerne kalde samtidig.

## Konfiguration

Defaults er kodede i [src/norma_bridge/config.py](src/norma_bridge/config.py). Se [config/default.ini](config/default.ini) for en kommenteret reference med alle nøgler og deres ENV-overrides.

Precedence: kodede defaults < INI-fil (`--config`) < ENV-vars (`NORMA_*`) < CLI-args.

Vigtigste nøgler:
- `[robot]` `ip`, `port` — adresse på Pepper/NAO
- `[server]` `host`, `port` — hvor bridge lytter
- `[gestures]` `list` — komma-separeret liste af tags brugt af cycling-logikken
- `[intro]` `animation_tag`, `image_url`, `image_path`, `welcome_text` — opstarts-flow (alle valgfrie)
- `[logging]` `level` — DEBUG/INFO/WARNING/ERROR

For lokal udvikling: kopiér `config/default.ini` til `config/local.ini` og redigér. `local.ini` er gitignored.

## Test

Med miljøet aktiveret:

```bash
pytest tests/
```

164 tests, ingen NAOqi påkrævet — alle bruger `FakeRobotService` eller mockede ALProxies. Kører rent på både Python 2.7 og Python 3.12.

For end-to-end test mod fysisk robot, se [tests/manual.md](tests/manual.md) — en udfyldelig checkliste der dækker alle 7 kommandoer plus fejl-paths.

## Py 2.7-faldgruber

Se `CLAUDE.md` for komplet liste. Vigtigste:
- Ingen f-strings, ingen `pathlib`, ingen `typing`-annotationer, ingen `dataclasses`
- Brug `from __future__ import print_function, unicode_literals`
- Brug `% (...)` eller `.format()` til streng-formatering
- Bekræft før commit: `python2 -m py_compile src/norma_bridge/**/*.py`
