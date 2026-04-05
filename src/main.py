import sys
import argparse
from PyQt6.QtWidgets import QApplication
from main_window import ScrcpyWrapper


def main():
    parser = argparse.ArgumentParser(description="GUI Wrapper for scrcpy and adb")
    parser.add_argument("--tray", action="store_true", help="Create system tray icon and start in tray")
    parser.add_argument("--start-minimized", action="store_true", help="Start minimized (window hidden)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (use -v or -vv for more)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Scrcpy-PyQt6")
    # Use desktop file name without suffix (Qt appends/handles .desktop internally)
    app.setDesktopFileName("scrcpy-pyqt6")

    # Rely completely on the default Desktop Environment theme

    window = ScrcpyWrapper(start_in_tray=args.tray, start_minimized=args.start_minimized, verbose_level=args.verbose)
    # If not starting minimized/tray, show window immediately
    if not args.tray and not args.start_minimized:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
