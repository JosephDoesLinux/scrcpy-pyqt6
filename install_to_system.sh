#!/usr/bin/env bash
set -euo pipefail

echo "Integrating Scrcpy-PyQt6 into the user's local environment..."

INSTALL_DIR="$HOME/.local/share/scrcpy-pyqt6"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

echo "Copying application source files to $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -a src/. "$INSTALL_DIR/"

echo "Creating user-local executable launcher in $BIN_DIR..."
mkdir -p "$BIN_DIR"
cat <<'EOF' > "$BIN_DIR/scrcpy-pyqt6"
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPT_DIR/../share/scrcpy-pyqt6" && pwd)"
export PYTHONPATH="$INSTALL_DIR"

if command -v python3 >/dev/null 2>&1; then
	exec python3 "$INSTALL_DIR/main.py" "$@"
fi

echo "Error: python3 not found in PATH." >&2
exit 1
EOF
chmod +x "$BIN_DIR/scrcpy-pyqt6"

echo "Creating desktop entry in $APP_DIR for launcher integration..."
mkdir -p "$APP_DIR"
cat <<EOF > "$APP_DIR/scrcpy-pyqt6.desktop"
[Desktop Entry]
Name=Scrcpy-PyQt6
Comment=Native GUI for managing ADB and scrcpy
Exec=$BIN_DIR/scrcpy-pyqt6
Icon=smartphone
Terminal=false
Type=Application
Categories=Utility;System;
Keywords=android;adb;scrcpy;screen;mirror;
EOF
chmod +x "$APP_DIR/scrcpy-pyqt6.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
	update-desktop-database "$APP_DIR" || true
fi

echo "Installation complete: application installed to $INSTALL_DIR using the system Python environment."
echo "You can launch the application from your desktop environment menu or by running: $BIN_DIR/scrcpy-pyqt6"
