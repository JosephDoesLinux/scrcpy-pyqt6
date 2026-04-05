#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$DIR/.venv/bin/python"

export PYTHONPATH="$DIR/src"

if [[ -x "$VENV_PYTHON" ]]; then
	exec "$VENV_PYTHON" "$DIR/src/main.py" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
	echo "Warning: .venv not found at $DIR/.venv; using system python3." >&2
	exec python3 "$DIR/src/main.py" "$@"
fi

echo "Error: python3 not found and no virtual environment at $DIR/.venv." >&2
exit 1
