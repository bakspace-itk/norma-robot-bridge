# pepper-robot-bridge

HTTP-bridge der eksponerer NAOqi-funktionalitet (TTS, animationer, tablet) for Pepper/NAO via et JSON-API. Skrevet i **Python 2.7** fordi NAOqi-SDK'et kræver det — men klienter kan tale med den fra et hvilket som helst sprog over HTTP.

## Hvorfor

NAOqi-SDK'et er låst til Python 2.7, men resten af verden er på Py 3. `pepper-robot-bridge` kører som en lille HTTP-server tæt på robotten og lader alt andet — Python 3-apps, JavaScript i en tablet-side, en hvilken som helst HTTP-klient — sende kommandoer til Pepper/NAO uden at skulle håndtere Py 2.7 selv.

# Quickstart

Efter setup (se herunder) kan du starte broen med følgende kommandoer:

Aktiver naoqi i din terminal:
```bash
# Linux / macOS / WSL
source ./activate-with-naoqi.sh

# Windows cmd
activate-with-naoqi.bat
```

Start pepper-bridge:
```bash
pepper-bridge
```

# Forudsætninger

- Python 2.7 (NAOqi-krav)
- NAOqi SDK fra SoftBank Robotics — installeres separat, kan ikke hentes via pip
- Netværksforbindelse til robotten (default port 9559)

For lokal udvikling og tests er kun Python 2.7 (eller Py 3) påkrævet — NAOqi kan undværes via `--fake`-mode.

> **Hvorfor ikke `pip install pepper-robot-bridge`?** Pakken er ikke publiceret på offentlig PyPI: NAOqi er ikke pip-installerbar, og pip-økosystemet droppede Py 2.7 i 2021. Brug setup-scriptsne nedenfor eller `pip install git+https://github.com/bakspace-itk/pepper-robot-bridge.git` med `pip<21`/`pip2`.

## Setup (én gang per maskine)

Setup-scriptsne under [scripts/](scripts/) opretter `.venv27/`, installerer pakken (`pip install -e ".[test]"`) og **genererer en aktiverings-helper** `activate-with-naoqi.{sh,bat}` med absolutte stier til din NAOqi-SDK-installation. Detaljer i [scripts/README.md](scripts/README.md).

```bash
# Linux / macOS / WSL
git clone https://github.com/bakspace-itk/pepper-robot-bridge
cd pepper-robot-bridge
./scripts/setup-linux.sh --naoqi-sdk /opt/aldebaran/pynaoqi-python2.7-2.5.5.5-linux64

# Windows cmd
scripts\setup-windows.bat C:\tools\pynaoqi
```

NAOqi-SDK'ets bundlede Python 2.7 har et usædvanligt layout der kræver `PYTHONHOME` inline ved venv-oprettelsen — `setup-windows.bat` håndterer det automatisk. Detaljer i [scripts/README.md](scripts/README.md).

Kør kun setup-scriptet **igen** hvis:
- du flytter eller opdaterer din NAOqi-SDK
- du sletter `.venv27/`
- `setup.py` ændrer entry-points eller pakke-navn (så `pepper-bridge.exe` skal regenereres)

## Daglig brug (hver shell-session)

Aktiverings-helperen er **ikke** noget setup-scriptet kalder for dig — du skal kalde den hver gang du åbner en ny terminal:

```bash
# Linux / macOS / WSL
source ./activate-with-naoqi.sh

# Windows cmd
activate-with-naoqi.bat

# Windows PowerShell
& cmd /c "activate-with-naoqi.bat & powershell"
```

Den sætter både venv'et og `PYTHONPATH` for NAOqi i den nuværende shell. For ren `--fake`-mode (uden NAOqi-import) er plain venv-aktivering nok — `source .venv27/bin/activate` / `.\.venv27\Scripts\Activate.ps1`.

Når miljøet er aktivt kan du starte bridge'en:

```bash
# Mod ægte robot — auto-loader config/local.ini hvis den findes
pepper-bridge

# Eller eksplicit IP (overstyrer config og ENV)
pepper-bridge --robot-ip 192.168.1.42

# Eksplicit config-fil
pepper-bridge --config /sti/til/config.ini

# Lokal udvikling med FakeRobotService (ingen NAOqi påkrævet)
pepper-bridge --fake --port 8080

# Spring intro over (hurtig genstart under udvikling)
pepper-bridge --fake --no-intro
```

`pepper-bridge` er den genererede CLI-entry-point. Hvis den ikke findes i din `PATH` (typisk fordi venv'et ikke er aktiveret, eller `setup.py develop` ikke er kørt), kan du altid bruge det fuldt kvalificerede modul-kald i stedet:

```bash
python -m pepper_bridge.main [args...]
```

Begge starter præcis det samme program. Hvis `pepper-bridge` mangler efter en `git pull`, kør `.venv27/Scripts/python.exe setup.py develop` (Windows) eller `.venv27/bin/python setup.py develop` (Linux) for at regenerere.

CLI-args overstyrer config-fil overstyrer ENV-vars overstyrer kodede defaults. Se `pepper-bridge --help` for komplet liste.

Hvis `--config` udelades, ledes der automatisk efter `config/local.ini` ved siden af pakken; hvis den ikke findes, prøves `config/default.ini`. Hvis ingen robot-IP er sat (hverken via CLI, ENV eller INI), fejler bridge'en hurtigt med en hjælpsom besked.

## API

API'et eksponeres på `http://<host>:8080/api/...`. Kontrakten ligger i [api-spec/openapi.yaml](api-spec/openapi.yaml) — alle 7 kommandoer dokumenteret med præcise request/response-skemaer, fejl-koder og eksempler. `tests/test_openapi_consistency.py` verificerer at spec og kode forbliver synkrone.

Endpoints:
- `GET /api/status` — server- og robot-status
- `POST /api/command` — udfør en kommando

Kommandoer:

| Kommando | Formål |
|---|---|
| `say` | TTS, evt. med gesture |
| `play_gesture` | Afspil named gesture |
| `show_tablet_image` | Vis lokalt billede på tablet (base64 data-URI) |
| `show_tablet_html` | Vis HTML-streng på tablet (base64 data-URI) |
| `show_tablet_url` | Peg tablet-WebView på en URL (foretrukken metode) |
| `hide_tablet` | Skjul webview |
| `get_status` | Hent status |

`show_tablet_url` er det foretrukne flow når du har en webside at vise — den undgår base64-encoding helt. `show_tablet_image` og `show_tablet_html` bevares for enkle eksperimenter og bagudkompatibilitet.

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
     -d '{"command":"say","params":{"text":"Hello","gesture":"hello"}}'

# Afspil gesture
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"play_gesture","params":{"gesture_name":"animations/Stand/Gestures/BowShort_1"}}'

# Peg tablet på en URL
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_url","params":{"url":"http://ui.example.local:8000/"}}'

# Vis lokalt billede (data-URI)
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"show_tablet_image","params":{"image_path":"/sti/til/image.png"}}'

# Skjul tablet-webview
curl -X POST http://<host>:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"command":"hide_tablet","params":{}}'
```

### Hurtig integration fra Python 3

```python
import requests

BASE = "http://<host>:8080/api"

def cmd(name, **params):
    r = requests.post(f"{BASE}/command",
                      json={"command": name, "params": params},
                      timeout=10)
    r.raise_for_status()
    return r.json()["data"]

cmd("say", text="Hello from Python 3", gesture="hello")
cmd("show_tablet_url", url="http://ui.example.local:8000/")
print(requests.get(f"{BASE}/status").json())
```

### Fejlfinding

- **`NAOqi ALProxy ikke tilgængelig`** — NAOqi SDK er ikke installeret eller ikke importerbar i Py 2.7-miljøet. Verificér med `python2 -c "from naoqi import ALProxy; print('OK')"`.
- **`Robot-IP mangler`** — bridge'en kan ikke finde en robot-IP. Sæt den med `--robot-ip <IP>`, eksportér `PEPPER_ROBOT_IP=<IP>`, eller læg den i `config/local.ini` under `[robot] ip = ...`.
- **Forbindelse nægtes til robot** — tjek `[robot] ip`/`port` i config, og at robotten kan ping'es fra værtsmaskinen.
- **`Connection refused` på port 8080** — bridge kører ikke, eller en anden proces holder porten. Skift port i config eller stop den anden proces.
- **Tablet viser intet** — billedstien skal eksistere på *bridge-maskinen* (ikke klientens). Tjek logs for `Billedfil ikke fundet`.
- **`æøå` virker forkert** — alle requests skal være UTF-8. `requests` i Py 3 sender UTF-8 automatisk.
- **Samtidige kald** — bridge er threaded og alle robotkald er beskyttet med en re-entrant lock; flere klienter må gerne kalde samtidig.

## Konfiguration

Defaults er kodede i [src/pepper_bridge/config.py](src/pepper_bridge/config.py). Se [config/default.ini](config/default.ini) for en kommenteret reference med alle nøgler og deres ENV-overrides.

Precedence: kodede defaults < INI-fil (auto-loaded eller `--config`) < ENV-vars (`PEPPER_*`) < CLI-args.

Vigtigste nøgler:

| Sektion | Felt | Beskrivelse |
|---|---|---|
| `[robot]` | `ip`, `port` | Adresse på Pepper/NAO |
| `[server]` | `host`, `port` | Hvor bridge lytter (default `:8080`) |
| `[gestures]` | `list` | Komma-separeret liste af tags brugt af cycling-logikken |
| `[intro]` | `animation_tag`, `image_url`, `image_path`, `welcome_text` | Opstarts-flow (alle valgfrie) |
| `[logging]` | `level` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |

ENV-overrides: `PEPPER_ROBOT_IP`, `PEPPER_ROBOT_PORT`, `PEPPER_BRIDGE_HOST`, `PEPPER_BRIDGE_PORT`, `PEPPER_LOG_LEVEL`.

For lokal udvikling: kopiér `config/default.ini` til `config/local.ini` og redigér. `local.ini` er gitignored.

## Test

Med miljøet aktiveret:

```bash
pytest tests/
```

187 tests, ingen NAOqi påkrævet — alle bruger `FakeRobotService` eller mockede ALProxies. Kører rent på både Python 2.7 og Python 3.12.

For end-to-end test mod fysisk robot, se [tests/manual.md](tests/manual.md) — en udfyldelig checkliste der dækker alle 7 kommandoer plus fejl-paths.

## Py 2.7-faldgruber

Se [CLAUDE.md](CLAUDE.md) for komplet liste. Vigtigste:

- Ingen f-strings, `pathlib`, `typing`-annotationer, eller `dataclasses`
- Brug `from __future__ import print_function, unicode_literals`
- Brug `%`-formatering eller `.format()` til strenge
- Bekræft før commit: `python2 -m py_compile src/pepper_bridge/**/*.py`

## Licens

MIT — se [LICENSE](LICENSE).
