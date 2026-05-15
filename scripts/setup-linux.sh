#!/usr/bin/env bash
#
# setup-linux.sh - opsaet norma-robot-bridge paa en Linux-maskine.
#
# Forudsaetninger (kan ikke automatiseres - laes scripts/README.md):
#   1. Python 2.7 + pip + virtualenv installeret
#   2. NAOqi pynaoqi-SDK pakket ud et permanent sted
#
# Brug:
#   ./scripts/setup-linux.sh --naoqi-sdk PATH [--python2 BIN]
#
# Eksempel:
#   ./scripts/setup-linux.sh --naoqi-sdk /opt/aldebaran/pynaoqi-python2.7-2.5.5.5-linux64
#
# Idempotent: kan koeres flere gange.

set -euo pipefail

# ---------- arg-parsing ----------
NAOQI_SDK=""
PYTHON2_BIN="python2"

print_help() {
    cat <<EOF
setup-linux.sh - opsaet norma-robot-bridge paa Linux

Brug:
  ./scripts/setup-linux.sh --naoqi-sdk PATH [--python2 BIN] [-h|--help]

Argumenter:
  --naoqi-sdk PATH    Sti til pynaoqi-SDK-mappen.
                      Skal indeholde lib/python2.7/site-packages/naoqi.py
  --python2 BIN       Sti til python2-binaeren. Default: python2 paa PATH
  -h, --help          Vis denne hjaelp

Se scripts/README.md for fuld kontekst og hvad der skal goeres bagefter.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --naoqi-sdk)
            NAOQI_SDK="${2:-}"
            shift 2
            ;;
        --python2)
            PYTHON2_BIN="${2:-}"
            shift 2
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            echo "FEJL: ukendt argument: $1" >&2
            print_help
            exit 1
            ;;
    esac
done

# ---------- validering ----------
if [[ -z "$NAOQI_SDK" ]]; then
    echo "FEJL: --naoqi-sdk er paakraevet." >&2
    print_help
    exit 1
fi

if [[ ! -d "$NAOQI_SDK" ]]; then
    echo "FEJL: NAOqi-SDK-mappen findes ikke: $NAOQI_SDK" >&2
    exit 1
fi

# Stoetter to layouts:
#   1. Standalone pynaoqi-SDK:    <sdk>/lib/python2.7/site-packages/naoqi.py
#   2. NAOqi-bundlet runtime:     <sdk>/lib/naoqi.py  (SDK og Python i samme mappe)
if [[ -f "$NAOQI_SDK/lib/python2.7/site-packages/naoqi.py" ]]; then
    NAOQI_SITE="$NAOQI_SDK/lib/python2.7/site-packages"
elif [[ -f "$NAOQI_SDK/lib/naoqi.py" ]]; then
    NAOQI_SITE="$NAOQI_SDK/lib"
else
    echo "FEJL: naoqi.py ikke fundet i hverken:" >&2
    echo "       $NAOQI_SDK/lib/python2.7/site-packages/naoqi.py   (pynaoqi-SDK)" >&2
    echo "       $NAOQI_SDK/lib/naoqi.py                           (NAOqi-bundlet runtime)" >&2
    echo "       Tjek at --naoqi-sdk peger paa SDK-roden eller den bundlede runtime-mappe." >&2
    exit 1
fi

# Find bridge-roden (script lever i scripts/ underbridge-roden)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BRIDGE_DIR"

# ---------- Python 2.7-tjek ----------
if ! command -v "$PYTHON2_BIN" >/dev/null 2>&1; then
    echo "FEJL: '$PYTHON2_BIN' findes ikke paa PATH." >&2
    echo "       Installer Python 2.7 foerst eller brug --python2 til at pege paa binaeren." >&2
    exit 1
fi

PY_VERSION="$("$PYTHON2_BIN" --version 2>&1 || true)"
if ! echo "$PY_VERSION" | grep -q "Python 2.7"; then
    echo "FEJL: $PYTHON2_BIN er ikke Python 2.7. Fik: $PY_VERSION" >&2
    exit 1
fi

echo "[1/6] Python: $PY_VERSION"
echo "[1/6] NAOqi-SDK: $NAOQI_SDK"
echo "[1/6] Bridge-rod: $BRIDGE_DIR"
echo

# ---------- virtualenv ----------
echo "[2/6] Verificer virtualenv..."
if ! "$PYTHON2_BIN" -m virtualenv --version >/dev/null 2>&1; then
    echo "       virtualenv mangler - installerer..."
    "$PYTHON2_BIN" -m pip install --user "virtualenv<20.22"
fi
echo "       virtualenv: $("$PYTHON2_BIN" -m virtualenv --version 2>&1)"
echo

# ---------- venv ----------
if [[ -d ".venv27" ]]; then
    echo "[3/6] .venv27 eksisterer allerede - genbruger."
else
    echo "[3/6] Opretter .venv27..."
    "$PYTHON2_BIN" -m virtualenv .venv27
fi
echo

VENV_PY=".venv27/bin/python"
VENV_PIP=".venv27/bin/pip"

# ---------- installer bridge ----------
echo "[4/6] Installerer bridge i venv'en (pip install -e \".[test]\")..."
"$VENV_PIP" install --quiet -e ".[test]"
echo "       OK"
echo

# ---------- generer aktiverings-helper ----------
ACTIVATE_HELPER="$BRIDGE_DIR/activate-with-naoqi.sh"
echo "[5/6] Genererer $ACTIVATE_HELPER ..."
cat > "$ACTIVATE_HELPER" <<EOF
#!/usr/bin/env bash
# Genereret af scripts/setup-linux.sh - skal IKKE commites.
# Aktivér venv og tilfoej pynaoqi til PYTHONPATH.
#
# Brug:
#     source ./activate-with-naoqi.sh
THIS_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
source "\$THIS_DIR/.venv27/bin/activate"
export PYTHONPATH="$NAOQI_SITE:\${PYTHONPATH:-}"
echo "norma-bridge venv + NAOqi klar (PYTHONPATH inkluderer pynaoqi)."
EOF
chmod +x "$ACTIVATE_HELPER"
echo "       OK"
echo

# ---------- verifikation ----------
echo "[6/6] Verificerer..."
if "$VENV_PY" -c "import sys; sys.path.insert(0, '$NAOQI_SITE'); from naoqi import ALProxy; print('       NAOqi-import OK')"; then
    :
else
    echo "FEJL: 'from naoqi import ALProxy' fejlede - tjek SDK-installationen." >&2
    exit 1
fi

if "$VENV_PY" -m pytest tests/ -q; then
    echo "       Tests OK"
else
    echo "FEJL: pytest fejlede." >&2
    exit 1
fi

echo
echo "===================================================================="
echo "  Setup faerdig. Naeste skridt:"
echo
echo "    1. cp config/default.ini config/local.ini"
echo "    2. Redigér config/local.ini og saet [robot] ip = <din-robots-IP>"
echo "    3. source ./activate-with-naoqi.sh"
echo "    4. python -m norma_bridge.main --config config/local.ini"
echo
echo "  Smoketest mod fysisk robot: tests/manual.md"
echo "===================================================================="
