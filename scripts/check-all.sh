#!/usr/bin/env sh
# One command to check your work before opening a PR (see PIPELINE_README.md).
# Usage: sh scripts/check-all.sh [--fix] [--no-ai] [--base origin/main]
set -e
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then PY=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
elif command -v python3 >/dev/null 2>&1; then PY=python3
else PY=python
fi
exec "$PY" -m gate all "$@"
