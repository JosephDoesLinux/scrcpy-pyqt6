#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$DIR/.venv/bin/python"

get_distro_pyqt_site_packages() {
	if [[ -x /usr/bin/python3 ]]; then
		/usr/bin/python3 - <<'PY'
import os
import site

paths = []
for p in site.getsitepackages():
    if p.startswith('/usr/lib') and os.path.isdir(os.path.join(p, 'PyQt6')):
        paths.append(p)
print(':'.join(paths))
PY
		return
	fi

	echo ""
}

DISTRO_SITE_PKGS="$(get_distro_pyqt_site_packages)"
if [[ -n "$DISTRO_SITE_PKGS" ]]; then
	export PYTHONPATH="$DISTRO_SITE_PKGS:$DIR/src${PYTHONPATH:+:$PYTHONPATH}"
else
	export PYTHONPATH="$DIR/src${PYTHONPATH:+:$PYTHONPATH}"
fi

if [[ -x "$VENV_PYTHON" ]]; then
	exec "$VENV_PYTHON" "$DIR/src/main.py" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
	echo "Warning: .venv not found at $DIR/.venv; using system python3." >&2
	exec python3 "$DIR/src/main.py" "$@"
fi

echo "Error: python3 not found and no virtual environment at $DIR/.venv." >&2
exit 1
