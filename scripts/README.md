# Setup-scripts for norma-robot-bridge

Automatiserer venv-opsætning på en frisk maskine. Et script per platform.

## Hvilket script?

| Platform | Script |
|---|---|
| Linux / macOS / WSL | `setup-linux.sh` |
| Windows cmd | `setup-windows.bat` |

Scripts'ene er idempotente — kør dem så mange gange du vil. De ødelægger ikke eksisterende `.venv27/` og overskriver kun `activate-with-naoqi.*`-helperen.

---

## Før du kører scriptet

### 1. Installer Python 2.7

**Linux:**
Denne fremgangsmåde er teste på en frisk Linux Mint. Vi skal bruge både 2.7 og 3+, så pyenv er at foretrække.
```bash
sudo apt install build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev curl \
libncurses5-dev libncursesw5-dev xz-utils tk-dev \
libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

```bash
curl https://pyenv.run | bash
# Kopier dette ind i din .bashrc, ligesom pyenv beskriver
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

```bash
pyenv install 2.7.18
pyenv install 3.12.3
pyenv rehash
```

**Windows:**
- Standard: download [Python 2.7.18 Windows x86-64 MSI](https://www.python.org/ftp/python/2.7.18/python-2.7.18.amd64.msi)
- Eller brug NAOqi-SDK'ets bundlede `python2.exe` (typisk `C:\tools\python27-nao\bin\python2.exe`)

### 2. Installer pip til Python 2.7

Py 2.7's bundled pip er for gammel til moderne TLS — installer en frisk via `get-pip.py`:

**Linux:**
```bash
wget https://bootstrap.pypa.io/pip/2.7/get-pip.py
sudo python2 get-pip.py
```

**Windows cmd (standard Python 2.7):**
```cmd
curl -o get-pip.py https://bootstrap.pypa.io/pip/2.7/get-pip.py
python get-pip.py
```

**Windows cmd (NAOqi-bundlet Python 2.7):**
```cmd
curl -o get-pip.py https://bootstrap.pypa.io/pip/2.7/get-pip.py
set PYTHONHOME=C:\tools\python27-nao\lib\python2.7
C:\tools\python27-nao\bin\python2.exe get-pip.py
set PYTHONHOME=
```

### 3. Download og udpak NAOqi pynaoqi-SDK

https://maxtronics.com/en/software-development-kit/

Hent fra Aldebaran/Softbank Developer Portal (kræver login). Eksempel-filnavn: `pynaoqi-python2.7-2.5.5.5-linux64.tar.gz` eller `-win64-vs2013.zip`.

Pak ud et **permanent** sted — ikke i `Downloads/`.

**Linux:**
```bash
sudo mkdir -p /opt/aldebaran
sudo tar -xzf pynaoqi-python2.7-2.5.5.5-linux64.tar.gz -C /opt/aldebaran/
ls /opt/aldebaran/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages/naoqi.py
```

**Windows:**
- Højreklik → "Pak ud" til fx `C:\tools\pynaoqi\`
- Verificér: `dir C:\tools\pynaoqi\lib\python2.7\site-packages\naoqi.py`

---

## Kør scriptet

### Linux bash

```bash
cd norma-robot-bridge
./scripts/setup-linux.sh --naoqi-sdk /opt/aldebaran/pynaoqi-python2.7-2.5.5.5-linux64
```

Hvis Python 2.7 hedder noget andet end `python2`:
```bash
./scripts/setup-linux.sh \
    --naoqi-sdk /opt/aldebaran/pynaoqi-python2.7-2.5.5.5-linux64 \
    --python2 /usr/bin/python2.7
```

### Windows cmd — standard Python 2.7

```cmd
cd norma-robot-bridge
scripts\setup-windows.bat C:\tools\pynaoqi
```

### Windows cmd — NAOqi-bundlet Python 2.7

```cmd
scripts\setup-windows.bat C:\tools\pynaoqi C:\tools\python27-nao\bin\python2.exe C:\tools\python27-nao\lib\python2.7
```

Det tredje argument (PYTHONHOME-stien) er **kun** nødvendigt når du bruger NAOqi-SDK'ets bundlede Python 2.7, der har et usædvanligt mappe-layout. Standard-installationer fra python.org behøver det ikke.

---

## Hvad scriptet gør

1. **Validerer** at NAOqi-SDK-stien indeholder `lib/python2.7/site-packages/naoqi.py`
2. **Tjekker** at `python2` (eller den specificerede binær) er Python 2.7
3. **Installerer** `virtualenv<20.22` hvis det mangler (20.22+ droppede Py 2.7-støtte)
4. **Opretter** `.venv27/` hvis den ikke findes (bevarer eksisterende)
5. **Installerer** bridge i venv'en med `pip install -e ".[test]"`
6. **Genererer** `activate-with-naoqi.sh`/`.bat` i bridge-roden
7. **Verificerer** at `from naoqi import ALProxy` virker
8. **Verificerer** at `pytest tests/` består

Hvis et trin fejler, stopper scriptet med en klar fejlbesked og non-zero exit-kode.

---

## Efter scriptet er kørt

### 1. Lav din lokale config

**Linux bash:**
```bash
cp config/default.ini config/local.ini
${EDITOR:-nano} config/local.ini
```

**Windows cmd:**
```cmd
copy config\default.ini config\local.ini
notepad config\local.ini
```

Sæt `[robot] ip = <din-robots-IP>`. Tryk på Norma's maveknap for at høre IP'en højt. `config/local.ini` er gitignored.

### 2. Aktivér miljøet

**Linux bash:**
```bash
source ./activate-with-naoqi.sh
```

**Windows cmd:**
```cmd
activate-with-naoqi.bat
```

`PYTHONPATH` indeholder nu både `pynaoqi` og bridgens `src/`. Du behøver ikke længere skrive `PYTHONPATH=src` foran kommandoer.

### 3. Start bridge

Mod fysisk robot:
```bash
python -m norma_bridge.main --config config/local.ini
```

Eller i fake-mode (uden NAOqi/robot — til lokal udvikling):
```bash
python -m norma_bridge.main --fake --no-intro
```

### 4. Smoketest

Når bridge'en kører mod fysisk robot, åbn `tests/manual.md` og arbejd dig gennem checklisten. 50+ check-bokse, 10–15 minutter, dækker alle 7 kommandoer + fejl-paths.

---

## Genereret aktiverings-helper

Scriptet genererer `activate-with-naoqi.sh` (Linux) eller `activate-with-naoqi.bat` (Windows) i bridge-roden. De er **per-maskine** — indeholder absolutte stier til din NAOqi-SDK-installation — og er gitignored.

Hvis du flytter SDK eller skifter venv: kør setup-scriptet igen. Det overskriver helperen.

---

## Fejlfinding

| Symptom | Sandsynlig årsag | Fix |
|---|---|---|
| `naoqi.py ikke fundet` | NAOQI_SDK-stien peger forkert | Skal være SDK-roden, ikke en undermappe. Tjek at `<sti>/lib/python2.7/site-packages/naoqi.py` findes |
| `er ikke Python 2.7` | Standard `python` peger på Py 3 | Brug `--python2 /sti/til/python2` (Linux) eller andet positionsarg (Windows) |
| `import naoqi` fejler i verifikation | SDK-mappestruktur ødelagt eller ufuldstændig udpakning | Pak SDK ud igen fra arkivet |
| `kunne ikke installere virtualenv` | Pip ikke installeret eller netværksfejl | Installer pip via `get-pip.py` (se "Før du kører") |
| `ImportError: DLL load failed` (kun Windows) | Manglende Visual C++ Redistributable | Installer VC++ 2013 Redistributable x64 |
| Setup virker, men `from naoqi import ALProxy` fejler senere | Glemt at aktivere miljøet | `source activate-with-naoqi.sh` / `activate-with-naoqi.bat` før du kører bridge |

---

## Hvad scriptet IKKE gør

- Installerer **ikke** Python 2.7 (kræver root/admin på de fleste systemer)
- Installerer **ikke** pip eller får-pip.py (samme grund)
- Henter **ikke** NAOqi-SDK (kræver Aldebaran-login)
- Konfigurerer **ikke** robot-IP (skal vælges per setup)
- Tester **ikke** mod fysisk robot (det er `tests/manual.md`-jobbet)
