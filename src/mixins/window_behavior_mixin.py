from pathlib import Path

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from profiles import load_settings
from tray import TrayManager


class WindowBehaviorMixin:
    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        self.action_start_in_tray = QAction("Minimize to Tray", self)
        self.action_start_in_tray.setCheckable(False)
        self.action_start_in_tray.triggered.connect(self._perform_minimize_to_tray)
        file_menu.addAction(self.action_start_in_tray)

        self.action_autostart = QAction("Start in Tray at Login", self)
        self.action_autostart.setCheckable(True)
        try:
            settings = load_settings()
            self.action_autostart.setChecked(bool(settings.get("autostart_enabled", False)))
        except Exception:
            pass
        self.action_autostart.triggered.connect(self._on_autostart_toggled)
        file_menu.addAction(self.action_autostart)

        file_menu.addSeparator()
        exit_action = QAction("Quit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self._quit_from_menu)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("About")
        layout = QVBoxLayout(dlg)
        about_text = (
            "<h3>Scrcpy-PyQt6</h3>"
            "<p>Lightweight GUI wrapper for <a href=\"https://github.com/Genymobile/scrcpy\">scrcpy</a> and adb.</p>"
            "<p>Wrapper made by <a href=\"https://github.com/JosephDoesLinux\">JosephDoesLinux</a> on GitHub.</p>"
            "<p>Repository: <a href=\"https://github.com/JosephDoesLinux/scrcpy-pyqt6\">scrcpy-pyqt6</a></p>"
        )
        lbl = QLabel(about_text)
        lbl.setOpenExternalLinks(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl)
        ok = QPushButton("OK")
        ok.clicked.connect(dlg.accept)
        layout.addWidget(ok, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    def _on_minimize_to_tray_toggled(self, checked: bool):
        try:
            if checked:
                try:
                    if not hasattr(self, "tray_manager") or getattr(self, "tray_manager") is None:
                        self.init_tray()
                    else:
                        try:
                            if getattr(self, "tray_manager") and getattr(self, "tray_manager").tray is None:
                                self.tray_manager.init_tray()
                        except Exception:
                            pass
                except Exception:
                    pass

            try:
                if hasattr(self, "tray_manager") and getattr(self, "tray_manager") is not None:
                    tm = self.tray_manager
                    if hasattr(tm, "tray_action_start_in_tray") and tm.tray_action_start_in_tray is not None:
                        try:
                            tm.tray_action_start_in_tray.setChecked(bool(checked))
                        except Exception:
                            pass
            except Exception:
                pass

        finally:
            try:
                self.save_settings_event()
            except Exception:
                pass

    def _perform_minimize_to_tray(self):
        try:
            if not hasattr(self, "tray_manager") or getattr(self, "tray_manager") is None:
                try:
                    self.init_tray()
                except Exception:
                    pass
            try:
                self.hide()
                if hasattr(self, "tray_manager") and getattr(self.tray_manager, "tray", None):
                    try:
                        self.tray_manager.tray.showMessage("Scrcpy-PyQt6", "Minimized to system tray", msecs=2000)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _quit_from_menu(self):
        try:
            self._explicit_quit = True
        except Exception:
            pass

        # Ensure tray does not keep the process alive after window closes.
        try:
            tm = getattr(self, "tray_manager", None)
            if tm and getattr(tm, "tray", None):
                try:
                    tm.tray.hide()
                except Exception:
                    pass
                try:
                    tm.tray.deleteLater()
                except Exception:
                    pass
                tm.tray = None
        except Exception:
            pass

        try:
            self.close()
        except Exception:
            try:
                super().close()
            except Exception:
                pass

        try:
            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass

    def _on_autostart_toggled(self, checked: bool):
        try:
            if checked:
                self._create_autostart_file()
            else:
                self._remove_autostart_file()
        finally:
            try:
                self.save_settings_event()
            except Exception:
                pass

    def _autostart_desktop_path(self) -> str:
        return str(Path.home() / ".config" / "autostart" / "scrcpy-pyqt6.desktop")

    def _create_autostart_file(self):
        path = Path(self._autostart_desktop_path())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            exec_path = str(Path.home() / ".local" / "bin" / "scrcpy-pyqt6")
            contents = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Scrcpy-PyQt6\n"
                "Comment=Start Scrcpy-PyQt6 at login (start in tray)\n"
                f"Exec={exec_path} --tray\n"
                "Icon=smartphone\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "Categories=Utility;System;\n"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(contents)
        except Exception as e:
            self.log(f"Failed to create autostart file: {e}")

    def _remove_autostart_file(self):
        path = Path(self._autostart_desktop_path())
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            self.log(f"Failed to remove autostart file: {e}")

    def init_tray(self):
        try:
            if not hasattr(self, "tray_manager") or self.tray_manager is None:
                self.tray_manager = TrayManager(self)
            self.tray_manager.init_tray()
        except Exception as e:
            self.log(f"Failed to initialize tray: {e}")

    def open_preferences(self):
        QMessageBox.information(
            self,
            "Preferences",
            "Preferences have been removed. The app follows the system theme by default.",
        )

    def apply_easy_mode(self, enabled: bool):
        return

    def closeEvent(self, event):
        try:
            if getattr(self, "_explicit_quit", False):
                try:
                    self.save_settings_event()
                except Exception:
                    pass

                # On explicit quit, hide tray before closing so the app exits fully.
                try:
                    tm = getattr(self, "tray_manager", None)
                    if tm and getattr(tm, "tray", None):
                        try:
                            tm.tray.hide()
                        except Exception:
                            pass
                except Exception:
                    pass

                super().closeEvent(event)

                try:
                    app = QApplication.instance()
                    if app is not None:
                        app.quit()
                except Exception:
                    pass
                return
        except Exception:
            pass

        try:
            try:
                if not hasattr(self, "tray_manager") or getattr(self, "tray_manager") is None:
                    self.init_tray()
            except Exception:
                pass

            try:
                self.hide()
                if hasattr(self, "tray_manager") and getattr(self, "tray_manager") and getattr(self.tray_manager, "tray", None):
                    try:
                        self.tray_manager.tray.showMessage("Scrcpy-PyQt6", "Minimized to system tray", msecs=2000)
                    except Exception:
                        pass
            except Exception:
                pass
            event.ignore()
            return
        except Exception:
            pass

        try:
            self.save_settings_event()
        except Exception:
            pass
        super().closeEvent(event)
