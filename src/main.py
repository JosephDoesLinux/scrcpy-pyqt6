import sys
import argparse
from PyQt6.QtWidgets import QApplication
from main_window import ScrcpyWrapper


def main():
    parser = argparse.ArgumentParser(description="GUI Wrapper for scrcpy and adb")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Scrcpy-PyQt6")
    # Ensure the desktop portal can find the app info by using the full .desktop filename
    app.setDesktopFileName("scrcpy-pyqt6.desktop")

    # Rely completely on the default Desktop Environment theme

    window = ScrcpyWrapper()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
