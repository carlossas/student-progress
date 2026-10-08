#!/usr/bin/env sh
# Runs a gate command from a git hook (husky): `sh gate/hooks/run.sh precommit|prepush`.
# Uses the project's virtualenv when present; override with GATE_PYTHON.
set -e
REPO="$(git rev-parse --show-toplevel)"
GATE_HOME="$(cd "$(dirname "$0")/../.." && pwd)"

if [ -n "${GATE_PYTHON:-}" ]; then PY="$GATE_PYTHON"
elif [ -x "$GATE_HOME/.venv/bin/python" ]; then PY="$GATE_HOME/.venv/bin/python"
elif [ -x "$GATE_HOME/.venv/Scripts/python.exe" ]; then PY="$GATE_HOME/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then PY=python3
else PY=python
fi

# `python -m` puts the current directory on sys.path, which is how `gate` is found.
cd "$GATE_HOME"
exec "$PY" -m gate "$@" --repo "$REPO"
