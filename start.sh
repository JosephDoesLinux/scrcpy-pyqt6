#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/.venv/bin/activate"
export PYTHONPATH="$DIR/src"
exec python3 "$DIR/src/main.py" "$@"
