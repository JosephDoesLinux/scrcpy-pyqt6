#!/bin/bash
set -e

echo "Uninstalling Scrcpy-PyQt6 from user-local directories..."

INSTALL_DIR="$HOME/.local/share/scrcpy-pyqt6"
BIN="$HOME/.local/bin/scrcpy-pyqt6"
DESKTOP="$HOME/.local/share/applications/scrcpy-pyqt6.desktop"

echo "Removing files from $INSTALL_DIR"
rm -rf "$INSTALL_DIR"

if [ -f "$BIN" ]; then
  echo "Removing launcher $BIN"
  rm -f "$BIN"
fi

if [ -f "$DESKTOP" ]; then
  echo "Removing desktop entry $DESKTOP"
  rm -f "$DESKTOP"
  update-desktop-database "$HOME/.local/share/applications" || true
fi

# No legacy artifacts to remove

echo "Uninstall complete."
