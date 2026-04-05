#!/usr/bin/env bash
set -euo pipefail

echo "Uninstalling Scrcpy-PyQt6 from user-local directories..."

INSTALL_DIR="$HOME/.local/share/scrcpy-pyqt6"
BIN="$HOME/.local/bin/scrcpy-pyqt6"
DESKTOP="$HOME/.local/share/applications/scrcpy-pyqt6.desktop"
AUTOSTART="$HOME/.config/autostart/scrcpy-pyqt6.desktop"

echo "Removing files from $INSTALL_DIR"
rm -rf "$INSTALL_DIR"

if [ -f "$BIN" ]; then
  echo "Removing launcher $BIN"
  rm -f "$BIN"
fi

if [ -f "$DESKTOP" ]; then
  echo "Removing desktop entry $DESKTOP"
  rm -f "$DESKTOP"
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" || true
  fi
fi

if [ -f "$AUTOSTART" ]; then
  echo "Removing autostart entry $AUTOSTART"
  rm -f "$AUTOSTART"
fi

echo "Uninstall complete."
