from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtGui import QAction, QIcon
from profiles import load_settings


class TrayManager:
    def __init__(self, window):
        self.window = window
        self.tray = None
        self.profiles_menu = None
        self.devices_menu = None

    def init_tray(self):
        if self.tray is not None:
            try:
                self.rebuild_profiles_menu()
                self.rebuild_devices_menu()
                self.tray.show()
            except Exception:
                pass
            return

        self.window.log("Initializing system tray...")
        if not QSystemTrayIcon.isSystemTrayAvailable():
            try:
                self.window.log("System tray not available on this platform")
            except Exception:
                pass
            return

        icon = QIcon.fromTheme("smartphone")
        if icon.isNull():
            icon = self.window.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        self.tray = QSystemTrayIcon(icon, self.window)
        menu = QMenu()

        act_show = QAction("Show", self.window)
        act_show.triggered.connect(self.show)
        menu.addAction(act_show)

        act_hide = QAction("Hide", self.window)
        act_hide.triggered.connect(self.hide)
        menu.addAction(act_hide)

        self.window.log("Tray menu base actions added")

        menu.addSeparator()

        act_launch = QAction("Launch scrcpy", self.window)
        act_launch.triggered.connect(self.window.start_scrcpy)
        menu.addAction(act_launch)

        act_stop = QAction("Stop scrcpy", self.window)
        act_stop.triggered.connect(self.window.stop_scrcpy)
        menu.addAction(act_stop)

        menu.addSeparator()

        self.profiles_menu = QMenu("Profiles")
        menu.addMenu(self.profiles_menu)
        self.rebuild_profiles_menu()
        self.window.log("Profiles menu created")

        self.devices_menu = QMenu("Devices")
        menu.addMenu(self.devices_menu)
        self.rebuild_devices_menu()
        self.window.log("Devices menu created")

        # Auto-connect toggle in tray (mirrors main window checkbox)
        self.tray_action_autoconnect = QAction("Auto-connect Network Devices", self.window)
        self.tray_action_autoconnect.setCheckable(True)
        try:
            checked = False
            if getattr(self.window, "chk_auto_connect", None):
                checked = bool(self.window.chk_auto_connect.isChecked())
        except Exception:
            checked = False
        try:
            self.tray_action_autoconnect.setChecked(checked)
        except Exception:
            pass
        self.tray_action_autoconnect.triggered.connect(lambda checked: self._on_autoconnect_toggled(checked))
        menu.addAction(self.tray_action_autoconnect)

        # Quick scan action for network devices
        act_scan = QAction("Scan Network Devices", self.window)
        act_scan.triggered.connect(self.window.scan_mdns)
        menu.addAction(act_scan)

        menu.addSeparator()

        # Settings toggles
        self.tray_action_start_in_tray = QAction("Minimize to Tray", self.window)
        self.tray_action_start_in_tray.setCheckable(False)
        self.tray_action_start_in_tray.triggered.connect(lambda: self.window.hide())
        menu.addAction(self.tray_action_start_in_tray)

        self.tray_action_autostart = QAction("Autostart at Login", self.window)
        self.tray_action_autostart.setCheckable(True)
        try:
            settings = load_settings()
            self.tray_action_autostart.setChecked(bool(settings.get("autostart_enabled", False)))
        except Exception:
            pass
        self.tray_action_autostart.triggered.connect(lambda checked: self.window._on_autostart_toggled(checked))
        menu.addAction(self.tray_action_autostart)

        menu.addSeparator()

        act_refresh = QAction("Refresh Devices", self.window)
        act_refresh.triggered.connect(self.window.refresh_devices)
        menu.addAction(act_refresh)

        menu.addSeparator()

        act_quit = QAction("Quit", self.window)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()
        self.window.log("System tray shown")

    def _on_activated(self, reason):
        try:
            # Left click / primary click: show the application
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                try:
                    self.window.log("Tray icon activated (Trigger)")
                    if self.window.isVisible():
                        self.window.hide()
                    else:
                        self.show()
                except Exception:
                    pass
        except Exception:
            pass

    def _toggle_start_in_tray(self, checked: bool):
        try:
            # keep main menu action in sync if present
            if hasattr(self.window, "action_start_in_tray"):
                try:
                    self.window.action_start_in_tray.setChecked(bool(checked))
                except Exception:
                    pass
            self.window.log(f"Tray: set Minimize-to-Tray = {bool(checked)}")
            self.window.save_settings_event()
        except Exception:
            pass
    def _on_autoconnect_toggled(self, checked: bool):
        try:
            # Mirror the main window checkbox state
            try:
                if getattr(self.window, "chk_auto_connect", None):
                    self.window.chk_auto_connect.setChecked(bool(checked))
            except Exception:
                pass

            # If enabling, perform an immediate scan so the user sees discovered devices
            if checked:
                try:
                    self.window.scan_mdns()
                except Exception:
                    pass

            # persist change
            try:
                self.window.save_settings_event()
            except Exception:
                pass
        except Exception:
            pass

    def rebuild_profiles_menu(self):
        try:
            if not self.profiles_menu:
                return
            self.profiles_menu.clear()
            # Prefer authoritative active_profile if set; fallback to combobox
            active = None
            try:
                ap = getattr(self.window, "active_profile", None)
                if isinstance(ap, str) and ap.strip():
                    active = ap.strip()
                else:
                    combo = getattr(self.window, "profile_combo", None)
                    if combo and combo.currentIndex() != -1:
                        active = combo.currentText()
                        if isinstance(active, str):
                            active = active.strip()
            except Exception:
                active = None

            profiles = list(getattr(self.window, "profiles", {}).keys())

            for name in profiles:
                pname = str(name).strip()
                display = pname
                try:
                    if active and pname == active:
                        display = f"{pname}  ✓"
                except Exception:
                    pass

                a = QAction(display, self.window)

                def _on_profile_triggered(n=pname):
                    try:
                        # apply profile and refresh menu
                        self.window.apply_profile(n)
                    finally:
                        try:
                            self.rebuild_profiles_menu()
                        except Exception:
                            pass

                a.triggered.connect(lambda checked=False, fn=_on_profile_triggered: fn())
                self.profiles_menu.addAction(a)
        except Exception:
            pass

    def rebuild_devices_menu(self):
        try:
            if not self.devices_menu:
                return
            self.devices_menu.clear()
            items = []
            try:
                combo = getattr(self.window, "device_combo", None)
                if combo:
                    items = [combo.itemText(i) for i in range(combo.count())]
            except Exception:
                items = []
            current = None
            try:
                current = getattr(self.window, "device_combo", None).currentText()
            except Exception:
                current = None

            # iterate with userData so we only tick real devices (userData not None)
            try:
                combo = getattr(self.window, "device_combo", None)
                if combo:
                    current_data = combo.currentData()
                    for i in range(combo.count()):
                        text = combo.itemText(i)
                        data = combo.itemData(i)
                        display = text
                        try:
                            # only show tick when the item represents a real device (userData not None)
                            if data is not None and current_data is not None and data == current_data:
                                display = f"{text}  ✓"
                        except Exception:
                            pass

                        a = QAction(display, self.window)

                        def _on_device_triggered(idx=i, d=data, txt=text):
                            try:
                                try:
                                    if getattr(self.window, "device_combo", None):
                                        self.window.device_combo.setCurrentIndex(idx)
                                except Exception:
                                    try:
                                        self._select_device(txt)
                                    except Exception:
                                        pass
                                self.window.log(f"Tray: device selected -> {txt} (data={d})")
                            finally:
                                try:
                                    self.rebuild_devices_menu()
                                except Exception:
                                    pass

                        a.triggered.connect(lambda checked=False, fn=_on_device_triggered: fn())
                        self.devices_menu.addAction(a)
            except Exception:
                # fallback: add plain items
                for it in items:
                    a = QAction(it, self.window)
                    a.triggered.connect(lambda checked=False, txt=it: self._select_device(txt))
                    self.devices_menu.addAction(a)
        except Exception:
            pass

    def _select_device(self, label: str):
        try:
            combo = getattr(self.window, "device_combo", None)
            if combo:
                idx = combo.findText(label)
                if idx != -1:
                    combo.setCurrentIndex(idx)
        except Exception:
            pass

    def show(self):
        try:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
        except Exception:
            pass

    def hide(self):
        try:
            self.window.hide()
        except Exception:
            pass

    def quit(self):
        try:
            self.window._quit_from_menu()
        except Exception:
            try:
                if self.tray:
                    self.tray.hide()
            except Exception:
                pass
            try:
                self.window._explicit_quit = True
                self.window.close()
            except Exception:
                pass
