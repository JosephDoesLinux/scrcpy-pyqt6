#!/bin/bash
set -e

echo "Integrating Scrcpy-PyQt6 into the user's local environment..."

INSTALL_DIR="$HOME/.local/share/scrcpy-pyqt6"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

echo "Copying application source files to $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r src/* "$INSTALL_DIR/"

echo "Creating user-local executable launcher in $BIN_DIR..."
mkdir -p "$BIN_DIR"
cat <<'EOF' > "$BIN_DIR/scrcpy-pyqt6"
#!/bin/bash
# Determine installation dir relative to this script (assumes ~/.local/bin -> ~/.local/share)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPT_DIR/../share/scrcpy-pyqt6" && pwd)"
SYS_PKGS=$(/usr/bin/python3 -c "import site; print(':'.join([p for p in site.getsitepackages() if not p.startswith('/usr/local')]))")
export PYTHONPATH="${SYS_PKGS}:${INSTALL_DIR}:${PYTHONPATH}"
exec /usr/bin/python3 "${INSTALL_DIR}/main.py" "$@"
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
update-desktop-database "$APP_DIR" || true

echo "Installation complete: application installed to $INSTALL_DIR using the system Python environment."
echo "You can launch the application from your desktop environment menu or by running: $BIN_DIR/scrcpy-pyqt6"
