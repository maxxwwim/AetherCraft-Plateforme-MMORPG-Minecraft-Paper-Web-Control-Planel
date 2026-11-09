#!/usr/bin/env bash
# ==============================================================================
# AetherCraft - Lanceur Plateforme Web (Flask + Waitress)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/web"

echo "==================================================================="
echo "  AETHERCRAFT // WEB PLATFORM (Linux Waitress)"
echo "  URL locale : http://127.0.0.1:5000"
echo "==================================================================="

if [ -f "venv/bin/python" ]; then
    PYTHON_BIN="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

exec "$PYTHON_BIN" -u app.py
