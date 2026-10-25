#!/usr/bin/env bash
set -u
cd "$(dirname "$0")" || { echo "Projektordner nicht erreichbar"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
BAD=0
PORTABLE=0
case "${1:-}" in
    --portable) PORTABLE=1 ;;
    "") ;;
    *) echo "Usage: bash run-tests.sh [--portable]"; exit 2 ;;
esac

echo "=== Python-Syntax ==="
python3 - <<'PY'
import ast
from pathlib import Path
p = Path("macos-control-center")
ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
print("SYNTAX-OK")
PY
[ "$?" -eq 0 ] || BAD=1

echo
echo "=== Projekt-/Konfigurationstests ==="
python3 tests/test_contract.py || BAD=1
python3 tests/test_quick_actions_plus.py || BAD=1
python3 tests/test_product_features.py || BAD=1
python3 tests/test_utilities.py || BAD=1
python3 tests/test_dynamic_layout.py || BAD=1
python3 tests/test_focus_toggle.py || BAD=1
python3 tests/test_v2.py || BAD=1

echo
echo "=== Shell-Syntax ==="
for f in run.sh install.sh update.sh status.sh doctor.sh uninstall.sh macos-control-center-toggle scripts/daemon-lifecycle.sh; do
    if bash -n "$f"; then echo "OK  $f"; else BAD=1; fi
done

echo
echo
echo "=== Runtime-Versionsstatus ==="
python3 tests/test_runtime_state.py || BAD=1

echo
echo "=== Installer-/Update-Lebenszyklus ==="
if [ "$PORTABLE" -eq 1 ]; then
    echo "SKIP (--portable): Installer-Prozessintegration und Signal-/Starterintegration"
else
    python3 tests/test_install_lifecycle.py || BAD=1
    python3 tests/test_toggle_launcher.py || BAD=1
fi

echo "=== LocalSend-Sandbox ==="
grep -F 'LOCALSEND_CMD = ["flatpak", "run", "--nofilesystem=/mnt/medien",' macos-control-center >/dev/null \
  && echo "LOCALSEND-SANDBOX-OK" || { echo "LOCALSEND-SANDBOX-FEHLT"; BAD=1; }

echo
if [ "$BAD" -ne 0 ]; then
    echo "TESTS FEHLGESCHLAGEN"
elif [ "$PORTABLE" -eq 1 ]; then
    echo "PORTABLE TESTS BESTANDEN; ZWEI PROZESS-INTEGRATIONSTESTS AUSGELASSEN"
else
    echo "ALLE PROJEKTTESTS BESTANDEN"
fi
exit "$BAD"
