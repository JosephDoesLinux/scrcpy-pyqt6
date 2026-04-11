from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QTabWidget,
    QCheckBox,
    QGroupBox,
    QTextEdit,
    QSplitter,
    QStyle,
    QScrollArea,
    QFrame,
)
from PyQt6.QtWidgets import QBoxLayout
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment, pyqtSlot, QTimer, QEvent
import os
import subprocess
import re
import time
from PyQt6.QtGui import QIcon, QFont, QPalette
import sys
from profiles import (
    load_profiles,
    load_settings,
    save_settings,
)
from adb import get_display_ids
from mixins.scrcpy_options_mixin import ScrcpyOptionsMixin
from mixins.device_ops_mixin import DeviceOpsMixin
from mixins.profile_mixin import ProfileMixin
from mixins.window_behavior_mixin import WindowBehaviorMixin


HOOK_TIMEOUT_SECONDS = 20
ADB_COMMAND_TIMEOUT_SECONDS = 8


class ScrcpyWrapper(
    ScrcpyOptionsMixin,
    DeviceOpsMixin,
    ProfileMixin,
    WindowBehaviorMixin,
    QMainWindow,
):
    def __init__(self, start_in_tray: bool = False, start_minimized: bool = False, verbose_level: int = 0):
        super().__init__()
        self.setWindowTitle("Scrcpy-PyQt6")
        self.resize(850, 650)
        self._explicit_quit = False
        # runtime flags
        self._start_in_tray_flag = bool(start_in_tray)
        self._start_minimized_flag = bool(start_minimized)
        self.active_profile = None
        self._applying_profile = False
        # verbosity: 0 = quiet (console suppressed), 1 = info, 2+ = debug
        try:
            self._verbose_level = int(verbose_level or 0)
        except Exception:
            self._verbose_level = 0

        self.init_ui()
        self.refresh_devices()

        # Load settings and apply startup behavior
        try:
            settings = load_settings()
        except Exception:
            settings = {}

        start_in_tray = self._start_in_tray_flag or bool(settings.get("start_in_tray", False))
        start_minimized = self._start_minimized_flag or bool(settings.get("start_minimized", False))

        # Always initialize tray for native Linux app behavior
        try:
            self.init_tray()
        except Exception:
            pass

        # Restore last-used profile if available; otherwise apply current combo profile
        try:
            last_profile = settings.get("last_profile")
            if isinstance(last_profile, str) and last_profile in self.profiles:
                self.apply_profile(last_profile)
            else:
                current_profile = self.profile_combo.currentText()
                if current_profile in self.profiles:
                    self.apply_profile(current_profile)
        except Exception:
            pass

        # If requested, hide the main window after creating tray
        if start_in_tray or start_minimized:
            try:
                self.hide()
            except Exception:
                pass

    def _apply_theme_aware_splitter_style(self):
        """Update splitter handle styling from the active desktop palette."""
        try:
            if not hasattr(self, "splitter") or self.splitter is None:
                return
            pal = self.palette()
            light = pal.color(QPalette.ColorRole.Light).name()
            mid = pal.color(QPalette.ColorRole.Mid).name()
            window = pal.color(QPalette.ColorRole.Window).name()
            self.splitter.setStyleSheet(
                f"QSplitter::handle {{ background: {window}; }}"
                f"QSplitter::handle:vertical {{ border-top: 1px solid {light}; border-bottom: 1px solid {mid}; }}"
            )
        except Exception:
            pass

    def _apply_landscape_pane_constraints(self):
        """Keep utility pane narrow by default and never wider than content pane."""
        try:
            if not hasattr(self, "left_col") or not hasattr(self, "right_col"):
                return
            total_width = max(1, self.width())
            # 4-unit grid target: left=1, right=3
            self.content_layout.setStretch(0, 1)
            self.content_layout.setStretch(1, 3)
            # Hard cap for narrow-landscape: left can be at most half (2/2)
            self.left_col.setMaximumWidth(total_width // 2)
            self.left_col.setMinimumWidth(0)
            self.right_col.setMinimumWidth(0)
        except Exception:
            pass

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Splitter to separate controls from console output
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        # make the handle a little wider so it's easier to grab
        self.splitter.setHandleWidth(10)
        self.splitter.setOpaqueResize(True)
        # Use palette colors so splitter follows KDE/desktop theme updates.
        self._apply_theme_aware_splitter_style()
        main_layout.addWidget(self.splitter)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        # add a bit of bottom margin so the control area doesn't touch the splitter
        top_layout.setContentsMargins(0, 0, 0, 12)
        top_layout.setSpacing(16)

        # --- ADB Device Management Section ---
        device_group = QGroupBox("Device Connection")
        font = device_group.font()
        font.setBold(True)
        device_group.setFont(font)
        child_font = QFont()
        child_font.setBold(False)
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(10)
        device_layout.setContentsMargins(16, 16, 16, 16)

        # Section: USB/Local Devices
        usb_header = QLabel("<b>USB / Local Devices</b>")
        usb_header.setToolTip(
            "Devices connected via USB or already paired over network."
        )
        device_layout.addWidget(usb_header)
        dev_row1 = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.setFont(child_font)
        self.device_combo.setMinimumHeight(30)
        self.device_combo.setToolTip(
            "Select a connected device (USB or paired network device)"
        )
        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setFont(child_font)
        refresh_icon = QIcon.fromTheme("view-refresh")
        if refresh_icon.isNull():
            refresh_icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_BrowserReload
            )
        self.btn_refresh.setIcon(refresh_icon)
        self.btn_refresh.setToolTip("Refresh device list")
        self.btn_refresh.setMinimumHeight(30)
        self.btn_refresh.clicked.connect(self.refresh_devices)
        self.device_combo.currentIndexChanged.connect(
            lambda _: self.tray_manager.rebuild_devices_menu()
            if hasattr(self, "tray_manager") and self.tray_manager
            else None
        )
        self.device_combo.currentIndexChanged.connect(
            lambda _: self._update_recovery_controls()
        )
        usb_icon_label = QLabel()
        usb_icon = QIcon.fromTheme("usb").pixmap(16, 16)
        if not usb_icon.isNull():
            usb_icon_label.setPixmap(usb_icon)
        dev_row1.addWidget(usb_icon_label)
        dev_row1.addWidget(self.device_combo, 1)
        dev_row1.addWidget(self.btn_refresh)
        help_usb = QPushButton("?")
        help_usb.setFixedWidth(24)
        help_usb.setToolTip("Show all devices detected by 'adb devices'.")
        help_usb.setFlat(True)
        dev_row1.addWidget(help_usb)
        device_layout.addLayout(dev_row1)

        # Section: Network Devices (mDNS)
        net_header = QLabel("<b>Network Devices (mDNS)</b>")
        net_header.setToolTip(
            "Scan for Android devices advertising ADB over the network (mDNS/zeroconf)"
        )
        device_layout.addWidget(net_header)
        dev_row2 = QHBoxLayout()
        self.mdns_combo = QComboBox()
        self.mdns_combo.setFont(child_font)
        self.mdns_combo.setMinimumHeight(30)
        self.mdns_combo.setToolTip(
            "Discovered devices on your LAN (via avahi/zeroconf)"
        )
        self.mdns_combo.addItem("Scan for network devices...")
        self.btn_scan = QPushButton(" Scan")
        self.btn_scan.setFont(child_font)
        scan_icon = QIcon.fromTheme("network-wireless")
        if scan_icon.isNull():
            scan_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon)
        self.btn_scan.setIcon(scan_icon)
        self.btn_scan.setToolTip("Scan for network ADB devices")
        self.btn_scan.setMinimumHeight(30)
        self.btn_scan.clicked.connect(self.scan_mdns)

        self.btn_pair = QPushButton(" Pair")
        self.btn_pair.setFont(child_font)
        pair_icon = QIcon.fromTheme("network-connect")
        if pair_icon.isNull():
            pair_icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_DialogApplyButton
            )
        self.btn_pair.setIcon(pair_icon)
        self.btn_pair.setToolTip(
            "Pair with selected device (requires pairing code from device)"
        )
        self.btn_pair.setMinimumHeight(30)
        self.btn_pair.clicked.connect(self.pair_wireless)
        net_icon_label = QLabel()
        net_icon = QIcon.fromTheme("network-wireless").pixmap(16, 16)
        if not net_icon.isNull():
            net_icon_label.setPixmap(net_icon)
        dev_row2.addWidget(net_icon_label)
        dev_row2.addWidget(self.mdns_combo, 1)
        dev_row2.addWidget(self.btn_scan)
        dev_row2.addWidget(self.btn_pair)
        # Auto-connect toggle
        self.chk_auto_connect = QCheckBox("Auto-connect")
        self.chk_auto_connect.setToolTip(
            "Automatically attempt to adb connect discovered network devices"
        )
        dev_row2.addWidget(self.chk_auto_connect)
        # persist auto-connect state when changed
        self.chk_auto_connect.stateChanged.connect(lambda _: self.save_settings_event())
        help_net = QPushButton("?")
        help_net.setFixedWidth(24)
        help_net.setToolTip(
            "Scan for devices using avahi-browse. Pairing is required for first-time wireless use."
        )
        help_net.setFlat(True)
        dev_row2.addWidget(help_net)
        device_layout.addLayout(dev_row2)

        # Section: Manual IP Connect
        manual_header = QLabel("<b>Manual Connect</b>")
        manual_header.setToolTip("Directly connect to a device by IP:Port (advanced)")
        device_layout.addWidget(manual_header)
        dev_row3 = QHBoxLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setFont(child_font)
        self.ip_input.setPlaceholderText("IP Address e.g., 192.168.1.5:5555")
        self.ip_input.setMinimumHeight(30)
        self.ip_input.setToolTip("Enter IP:Port for manual ADB connect")
        self.btn_connect = QPushButton(" Connect")
        self.btn_connect.setFont(child_font)
        connect_icon = QIcon.fromTheme("network-server")
        if connect_icon.isNull():
            connect_icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_DriveNetIcon
            )
        self.btn_connect.setIcon(connect_icon)
        self.btn_connect.setToolTip("Connect to device at specified IP:Port")
        self.btn_connect.setMinimumHeight(30)
        self.btn_connect.clicked.connect(self.connect_wireless)
        wired_icon_label = QLabel()
        wired_icon = QIcon.fromTheme("network-wired").pixmap(16, 16)
        if not wired_icon.isNull():
            wired_icon_label.setPixmap(wired_icon)
        dev_row3.addWidget(wired_icon_label)
        dev_row3.addWidget(self.ip_input, 1)
        dev_row3.addWidget(self.btn_connect)
        help_manual = QPushButton("?")
        help_manual.setFixedWidth(24)
        help_manual.setToolTip(
            "Use this if you know the device's IP and port. Usually not needed if mDNS works."
        )
        help_manual.setFlat(True)
        dev_row3.addWidget(help_manual)
        device_layout.addLayout(dev_row3)

        # Section: Recovery Actions
        recovery_group = QGroupBox("Recovery")
        recovery_layout = QVBoxLayout(recovery_group)
        recovery_layout.setContentsMargins(12, 10, 12, 10)
        recovery_layout.setSpacing(8)

        self.btn_restart_systemui = QPushButton(" Emergency Restart SystemUI")
        self.btn_restart_systemui.setFont(child_font)
        recovery_icon = QIcon.fromTheme("process-stop")
        if recovery_icon.isNull():
            recovery_icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_MessageBoxWarning
            )
        self.btn_restart_systemui.setIcon(recovery_icon)
        self.btn_restart_systemui.setMinimumHeight(34)
        self.btn_restart_systemui.setToolTip(
            "Force-restart Android SystemUI on the selected device if the UI is frozen."
        )
        self.btn_restart_systemui.setEnabled(False)
        self.btn_restart_systemui.clicked.connect(self.emergency_restart_systemui)
        recovery_layout.addWidget(self.btn_restart_systemui)

        recovery_hint = QLabel(
            "Use only for frozen Android UI. Requires a selected connected device."
        )
        recovery_hint.setWordWrap(True)
        recovery_hint.setFont(child_font)
        recovery_layout.addWidget(recovery_hint)

        device_layout.addWidget(recovery_group)

        # Small status label for network operations
        self.network_status = QLabel("")
        self.network_status.setFont(child_font)
        # Rely on the application's palette for text color so it follows system theme changes
        device_layout.addWidget(self.network_status)

        # We'll place `device_group` into the responsive content area below

        # keep an in-memory set of discovered network addresses for health checks
        self.discovered_addresses = set()

        # Recovery action state
        self._recovery_running = False
        self._recovery_cooldown_active = False
        self._recovery_cooldown_deadline = 0.0
        self._systemui_recovery_process = None

        # Health check timer (attempt reconnects when Auto-connect is enabled)
        self.health_timer = QTimer(self)
        self.health_timer.setInterval(10_000)  # 10 seconds
        self.health_timer.timeout.connect(self.check_device_health)
        self.health_timer.start()

        try:
            self._update_recovery_controls()
        except Exception:
            pass

        # --- Responsive content container ---
        content_widget = QWidget()
        self.content_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        content_widget.setLayout(self.content_layout)

        # Left column: device_group + profile controls
        self.left_col = QWidget()
        self.left_vlayout = QVBoxLayout(self.left_col)
        self.left_vlayout.setContentsMargins(0, 0, 0, 0)
        self.left_vlayout.setSpacing(8)

        # add the device group to the left column so it remains parented
        try:
            self.left_vlayout.addWidget(device_group)
        except Exception:
            # device_group might not be present if init order changed; ignore
            pass

        # Right column: tabs + actions
        self.right_col = QWidget()
        self.right_vlayout = QVBoxLayout(self.right_col)
        self.right_vlayout.setContentsMargins(0, 0, 0, 0)
        self.right_vlayout.setSpacing(8)

        # add columns to content layout
        self.content_layout.addWidget(self.left_col)
        self.content_layout.addWidget(self.right_col)

        # place content widget into top layout
        top_layout.addWidget(content_widget)

        # --- Profiles Section ---
        self.profiles = load_profiles()

        profile_layout = QHBoxLayout()
        profile_layout.setContentsMargins(16, 0, 16, 0)

        lbl_profile = QLabel("Profile:")
        lbl_profile.setFont(child_font)

        self.profile_combo = QComboBox()
        self.profile_combo.setFont(child_font)
        self.profile_combo.addItems(list(self.profiles.keys()))
        self.profile_combo.setMinimumHeight(30)
        self.profile_combo.currentTextChanged.connect(self._on_profile_combo_changed)
        # initialize active_profile to the combo's current selection so tray can reflect it
        try:
            self.active_profile = self.profile_combo.currentText()
        except Exception:
            self.active_profile = None

        self.btn_save_profile = QPushButton(" Save")
        self.btn_save_profile.setFont(child_font)
        self.btn_save_profile.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.btn_save_profile.setMinimumHeight(30)
        self.btn_save_profile.clicked.connect(self.save_profile)

        self.btn_delete_profile = QPushButton(" Delete")
        self.btn_delete_profile.setFont(child_font)
        self.btn_delete_profile.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        )
        self.btn_delete_profile.setMinimumHeight(30)
        self.btn_delete_profile.clicked.connect(self.delete_profile)

        self.btn_new_profile = QPushButton(" New")
        self.btn_new_profile.setFont(child_font)
        self.btn_new_profile.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        )
        self.btn_new_profile.setMinimumHeight(30)
        self.btn_new_profile.clicked.connect(self.new_profile)

        profile_layout.addWidget(lbl_profile)
        profile_layout.addWidget(self.profile_combo, 1)
        profile_layout.addWidget(self.btn_save_profile)
        profile_layout.addWidget(self.btn_new_profile)
        profile_layout.addWidget(self.btn_delete_profile)

        # add profile controls into left column
        profile_widget = QWidget()
        profile_widget.setLayout(profile_layout)
        self.left_vlayout.addWidget(profile_widget)

        # --- Scrcpy Settings Tabs ---
        self.tabs = QTabWidget()
        self.tabs.setFont(child_font)
        self.tabs.setDocumentMode(True)  # Cleaner look

        def create_scroll_tab(label):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            content = QWidget()
            scroll.setWidget(content)
            self.tabs.addTab(scroll, label)
            return content

        self.tab_video = create_scroll_tab("Video & Display")
        self.tab_audio = create_scroll_tab("Audio")
        self.tab_control = create_scroll_tab("Control & Behavior")
        self.tab_record = create_scroll_tab("Recording")
        self.tab_advanced = create_scroll_tab("Advanced Options")

        self.init_video_tab()
        self.init_audio_tab()
        self.init_control_tab()
        self.init_record_tab()
        self.init_advanced_tab()

        # add tabs into right column
        self.right_vlayout.addWidget(self.tabs)

        # --- Launch Button ---
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        # add bottom padding so buttons don't butt against the splitter handle
        action_layout.setContentsMargins(0, 0, 0, 12)

        # Define a consistent font structure for primary actions
        action_font = QFont()
        action_font.setPointSize(11)
        action_font.setBold(True)

        self.btn_start = QPushButton(" Launch scrcpy")
        self.btn_start.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setFont(action_font)
        # We rely on the desktop's native GTK / KDE Plasma Qt engine to style this properly
        self.btn_start.clicked.connect(self.start_scrcpy)

        self.btn_stop = QPushButton(" Stop")
        self.btn_stop.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        )
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setFont(action_font)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_scrcpy)

        action_layout.addWidget(self.btn_start, stretch=3)
        action_layout.addWidget(self.btn_stop, stretch=1)
        # add action buttons into right column
        action_widget = QWidget()
        action_widget.setLayout(action_layout)
        self.right_vlayout.addWidget(action_widget)

        self.splitter.addWidget(top_widget)

        # --- Console Output Log ---
        self.console_widget = QWidget()
        console_layout = QVBoxLayout(self.console_widget)
        console_layout.setContentsMargins(0, 8, 0, 0)

        lbl_console = QLabel("Activity Log")
        # Bold label
        lbl_font = lbl_console.font()
        lbl_font.setBold(True)
        lbl_console.setFont(lbl_font)
        console_layout.addWidget(lbl_console)

        # Log filter controls (non-destructive view filtering)
        filter_row = QHBoxLayout()
        self.chk_show_info = QCheckBox("Info")
        self.chk_show_warn = QCheckBox("Warnings")
        self.chk_show_error = QCheckBox("Errors")
        # wire filters to a combined handler (saves settings + refreshes view)
        self.chk_show_info.stateChanged.connect(lambda _: self.on_filter_changed())
        self.chk_show_warn.stateChanged.connect(lambda _: self.on_filter_changed())
        self.chk_show_error.stateChanged.connect(lambda _: self.on_filter_changed())
        filter_row.addWidget(QLabel("Filter:"))
        filter_row.addWidget(self.chk_show_info)
        filter_row.addWidget(self.chk_show_warn)
        filter_row.addWidget(self.chk_show_error)
        filter_row.addStretch(1)
        console_layout.addLayout(filter_row)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText(
            "ADB and scrcpy output logs will appear here..."
        )
        # Monospace font for console
        console_font = QFont("monospace")
        console_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.console.setFont(console_font)
        console_layout.addWidget(self.console)

        # internal log storage (level, text)
        self._log_entries = []  # list of (level, text)

        # add console to splitter by default (will be moved on resize)
        self.splitter.addWidget(self.console_widget)
        self.splitter.setSizes([600, 250])  # Give more space to controls

        self.scrcpy_process = None

        # Load persisted UI settings (auto-connect and filters)
        try:
            settings = load_settings()
            self.chk_auto_connect.setChecked(bool(settings.get("auto_connect", False)))
            self.chk_show_info.setChecked(bool(settings.get("show_info", True)))
            self.chk_show_warn.setChecked(bool(settings.get("show_warn", True)))
            self.chk_show_error.setChecked(bool(settings.get("show_error", True)))
            # initialize menu
            self.init_menu()
        except Exception:
            # If loading fails, keep current defaults
            pass

        # Show scrcpy repo link + installed version in the status bar (permanent, right-aligned)
        try:
            ver = None
            proc = subprocess.run(["scrcpy", "--version"], capture_output=True, text=True, timeout=1)
            if proc.returncode == 0 and proc.stdout:
                m = re.search(r"\d+\.\d+(?:\.\d+)?", proc.stdout)
                if m:
                    ver = m.group(0)
        except Exception:
            ver = None

        ver_text = f" - v{ver} installed" if ver else " - not found"
        scrcpy_label = QLabel(f'<a href="https://github.com/Genymobile/scrcpy">scrcpy</a>{ver_text}')
        scrcpy_label.setOpenExternalLinks(True)
        self.statusBar().addPermanentWidget(scrcpy_label)

    def changeEvent(self, event):
        super().changeEvent(event)
        # Recompute theme-aware styles when the application palette or style changes
        if event.type() in (
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        ):
            # Update splitter handle styling to match the new palette
            self._apply_theme_aware_splitter_style()

        # (Console is created in init_ui; changeEvent should only update palette-related styling)

    def resizeEvent(self, event):
        # Responsive layout: switch content layout direction based on width
        try:
            w = self.width()
            if w >= 1000:
                self.content_layout.setDirection(QBoxLayout.Direction.LeftToRight)
                self._apply_landscape_pane_constraints()
                try:
                    self.right_vlayout.setContentsMargins(0, 0, 0, 0)
                except Exception:
                    pass
                # move console into left column under profiles if not already
                try:
                    if (
                        self.console_widget
                        and self.console_widget.parent() is not self.left_col
                    ):
                        # remove from current parent
                        try:
                            parent = self.console_widget.parent()
                            if isinstance(parent, QWidget) and parent.layout():
                                parent.layout().removeWidget(self.console_widget)
                        except Exception:
                            pass
                        self.left_vlayout.addWidget(self.console_widget)
                except Exception:
                    pass
            else:
                self.content_layout.setDirection(QBoxLayout.Direction.TopToBottom)
                self.content_layout.setStretch(0, 0)
                self.content_layout.setStretch(1, 0)
                try:
                    # remove landscape cap in portrait mode
                    self.left_col.setMaximumWidth(16777215)
                except Exception:
                    pass
                try:
                    # Tiny gap between profile section (left column) and tab bar (right column).
                    self.right_vlayout.setContentsMargins(0, 6, 0, 0)
                except Exception:
                    pass
                # ensure console is in the splitter (bottom area)
                try:
                    if (
                        self.console_widget
                        and self.console_widget.parent() is not self.centralWidget()
                    ):
                        # remove from left column if present
                        try:
                            if self.left_vlayout:
                                self.left_vlayout.removeWidget(self.console_widget)
                        except Exception:
                            pass
                        # re-add to splitter bottom
                        # find splitter (it's the first widget in main_layout)
                        splitter = None
                        try:
                            splitter = self.centralWidget().layout().itemAt(0).widget()
                        except Exception:
                            splitter = None
                        if splitter and hasattr(splitter, "addWidget"):
                            splitter.addWidget(self.console_widget)
                except Exception:
                    pass
        except Exception:
            pass
        super().resizeEvent(event)

    def log(self, text: str, level: int | None = None):
        # Non-destructive logging: classify and store entries, then refresh view
        txt = str(text)
        # If caller provided numeric level, map it to named level
        if level is not None:
            try:
                lv = int(level)
            except Exception:
                lv = 0
            if lv >= 2:
                named = "error"
            elif lv == 1:
                named = "warn"
            else:
                named = "info"
        else:
            ltxt = txt.lower()
            named = "info"
            if "error" in ltxt or "failed" in ltxt or "exception" in ltxt:
                named = "error"
            elif "warn" in ltxt or "warning" in ltxt:
                named = "warn"

        # store entry
        self._log_entries.append((named, txt))
        # echo to terminal when verbosity enabled
        try:
            if getattr(self, "_verbose_level", 0) >= 1:
                import datetime

                ts = datetime.datetime.now().isoformat(timespec="seconds")
                out = f"[{ts}] [{named.upper()}] {txt}"
                # debug verbosity prints to stderr for visibility
                if getattr(self, "_verbose_level", 0) >= 2 or named == "error":
                    print(out, file=sys.stderr)
                else:
                    print(out)
        except Exception:
            pass
        # Keep a bounded history to avoid runaway memory usage
        if len(self._log_entries) > 5000:
            self._log_entries.pop(0)

        self.refresh_console()

    def refresh_console(self):
        # Rebuild console view based on filters and stored log entries
        show_info = self.chk_show_info.isChecked()
        show_warn = self.chk_show_warn.isChecked()
        show_error = self.chk_show_error.isChecked()

        self.console.clear()
        for level, txt in self._log_entries:
            if level == "info" and not show_info:
                continue
            if level == "warn" and not show_warn:
                continue
            if level == "error" and not show_error:
                continue

            # Color-code levels for readability, keep full text
            if level == "error":
                self.console.append(f"<b>[ERROR]</b> {txt}")
            elif level == "warn":
                self.console.append(f"<b>[WARN]</b> {txt}")
            else:
                self.console.append(f"[INFO] {txt}")

        # Scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _parse_env_vars(self, raw_text: str) -> dict[str, str]:
        env: dict[str, str] = {}
        text = (raw_text or "").strip()
        if not text:
            return env

        for idx, line in enumerate(text.splitlines(), 1):
            item = line.strip()
            if not item or item.startswith("#"):
                continue

            if item.startswith("export "):
                item = item[7:].strip()

            if "=" not in item:
                self.log(f"Skipping environment line {idx}: expected KEY=VALUE", level=1)
                continue

            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                self.log(f"Skipping environment line {idx}: empty key", level=1)
                continue

            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                self.log(f"Skipping environment line {idx}: invalid key '{key}'", level=1)
                continue

            env[key] = value

        return env

    def _emit_log_messages(self, messages):
        for level, text in messages or []:
            self.log(text, level=level)

    def _run_shell_hook_blocking(
        self,
        label: str,
        command: str,
        env_overrides: dict[str, str] | None = None,
    ):
        logs = []
        cmd = (command or "").strip()
        if not cmd:
            return logs

        logs.append((0, f"Running {label} command: {cmd}"))
        try:
            merged_env = os.environ.copy()
            if env_overrides:
                merged_env.update(env_overrides)

            result = subprocess.run(
                ["bash", "-lc", cmd],
                capture_output=True,
                text=True,
                check=False,
                env=merged_env,
                timeout=HOOK_TIMEOUT_SECONDS,
            )

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            if stdout:
                for line in stdout.splitlines():
                    logs.append((0, f"{label} stdout: {line}"))

            if stderr:
                for line in stderr.splitlines():
                    logs.append((0, f"{label} stderr: {line}"))

            if result.returncode != 0:
                logs.append((1, f"{label} command exited with code {result.returncode}."))
        except subprocess.TimeoutExpired:
            logs.append((1, f"{label} command timed out after {HOOK_TIMEOUT_SECONDS}s."))
        except Exception as e:
            logs.append((2, f"{label} command failed: {e}"))

        return logs

    def _run_adb_overlay_command_blocking(
        self,
        value: str,
        serial: str | None,
        env_overrides: dict[str, str] | None = None,
    ):
        cmd = ["adb"]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(["shell", "settings", "put", "global", "overlay_display_devices", value])

        logs = [(0, f"ADB overlay command: {' '.join(cmd)}")]
        try:
            merged_env = os.environ.copy()
            if env_overrides:
                merged_env.update(env_overrides)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=merged_env,
                timeout=ADB_COMMAND_TIMEOUT_SECONDS,
            )

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            if stdout:
                for line in stdout.splitlines():
                    logs.append((0, f"ADB overlay stdout: {line}"))
            if stderr:
                for line in stderr.splitlines():
                    logs.append((0, f"ADB overlay stderr: {line}"))

            if result.returncode != 0:
                logs.append((1, f"ADB overlay command exited with code {result.returncode}."))
                return {"ok": False, "logs": logs}
            return {"ok": True, "logs": logs}
        except subprocess.TimeoutExpired:
            logs.append((1, f"ADB overlay command timed out after {ADB_COMMAND_TIMEOUT_SECONDS}s."))
            return {"ok": False, "logs": logs}
        except Exception as e:
            logs.append((2, f"ADB overlay command failed: {e}"))
            return {"ok": False, "logs": logs}

    def _detect_virtual_display_id_blocking(
        self,
        serial: str | None,
        retries: int = 1,
        delay_seconds: float = 0.25,
    ):
        attempts = max(1, int(retries or 1))
        ids = []
        for attempt in range(attempts):
            ids = get_display_ids(serial=serial, non_default_only=True)
            if ids:
                return max(ids), ids
            if attempt < attempts - 1:
                time.sleep(max(0.0, float(delay_seconds or 0.0)))

        return None, []

    def _prepare_launch_context_blocking(self, prep):
        logs = []
        try:
            logs.extend(
                self._run_shell_hook_blocking(
                    "Pre-launch",
                    prep.get("pre_launch_cmd", ""),
                    prep.get("env_overrides", {}),
                )
            )

            detected_display_id = None
            launch_serial = prep.get("launch_serial")
            env_overrides = prep.get("env_overrides", {})

            if prep.get("use_adb_overlay_mode"):
                existing_ids = get_display_ids(serial=launch_serial, non_default_only=True)
                if existing_ids:
                    detected_display_id = max(existing_ids)
                    ids_text = ", ".join(str(i) for i in existing_ids)
                    logs.append(
                        (
                            0,
                            f"ADB workaround: reusing existing non-default display IDs: {ids_text}. "
                            f"Using display ID {detected_display_id}.",
                        )
                    )
                else:
                    overlay_spec = prep.get("overlay_spec", "")
                    if not overlay_spec:
                        logs.append(
                            (
                                1,
                                "ADB workaround selected, but New Display Res is empty. "
                                "Provide WIDTHxHEIGHT/DPI (example: 1920x1080/160).",
                            )
                        )
                        return {
                            "ok": False,
                            "logs": logs,
                            "request_cleanup": False,
                        }

                    overlay_result = self._run_adb_overlay_command_blocking(
                        overlay_spec,
                        launch_serial,
                        env_overrides,
                    )
                    logs.extend(overlay_result["logs"])
                    if not overlay_result["ok"]:
                        logs.append((1, "Failed to create ADB overlay display. Launch cancelled."))
                        return {
                            "ok": False,
                            "logs": logs,
                            "request_cleanup": False,
                        }

                    detected_display_id, ids = self._detect_virtual_display_id_blocking(
                        launch_serial,
                        retries=20,
                        delay_seconds=0.25,
                    )

                    if detected_display_id is None:
                        logs.append(
                            (
                                1,
                                "No non-default display IDs detected via adb dumpsys display.",
                            )
                        )
                        logs.append(
                            (
                                1,
                                "ADB workaround created overlay but no non-default display ID was detected. "
                                "Launch cancelled.",
                            )
                        )
                        return {
                            "ok": False,
                            "logs": logs,
                            "request_cleanup": bool(prep.get("adb_overlay_reset_on_close")),
                        }

                    ids_text = ", ".join(str(i) for i in ids)
                    logs.append(
                        (
                            0,
                            f"Detected non-default display IDs: {ids_text}. Using display ID {detected_display_id}.",
                        )
                    )

            if prep.get("auto_detect_display"):
                detected_display_id, ids = self._detect_virtual_display_id_blocking(
                    launch_serial,
                    retries=20,
                    delay_seconds=0.25,
                )
                if detected_display_id is None:
                    logs.append(
                        (
                            1,
                            "No non-default display IDs detected via adb dumpsys display.",
                        )
                    )
                    logs.append(
                        (
                            1,
                            "Auto-detect display ID is enabled, but no non-default display ID was found after pre-launch. "
                            "Launch cancelled to avoid using display 0.",
                        )
                    )
                    return {
                        "ok": False,
                        "logs": logs,
                        "request_cleanup": bool(prep.get("cleanup_on_close_armed")),
                    }

                ids_text = ", ".join(str(i) for i in ids)
                logs.append(
                    (
                        0,
                        f"Detected non-default display IDs: {ids_text}. Using display ID {detected_display_id}.",
                    )
                )

            return {
                "ok": True,
                "logs": logs,
                "detected_display_id": detected_display_id,
                "request_cleanup": False,
            }
        except Exception as e:
            logs.append((2, f"Launch preparation failed: {e}"))
            return {
                "ok": False,
                "logs": logs,
                "request_cleanup": bool(prep.get("cleanup_on_close_armed")),
            }

    def _run_shell_hook(self, label: str, command: str, env_overrides: dict[str, str] | None = None):
        self._emit_log_messages(
            self._run_shell_hook_blocking(label, command, env_overrides)
        )

    def _run_adb_overlay_command(self, value: str, serial: str | None, env_overrides: dict[str, str] | None = None) -> bool:
        result = self._run_adb_overlay_command_blocking(value, serial, env_overrides)
        self._emit_log_messages(result.get("logs", []))
        return bool(result.get("ok"))

    def _cleanup_adb_overlay_if_needed(self):
        if not getattr(self, "_adb_overlay_cleanup_on_close", False):
            return

        serial = getattr(self, "_last_launch_serial", None)
        env_overrides = getattr(self, "_last_launch_env_overrides", {})
        result = self._run_adb_overlay_command_blocking("none", serial, env_overrides)
        self._emit_log_messages(result.get("logs", []))

        if result.get("ok"):
            self.log("ADB overlay cleanup complete (overlay_display_devices=none).")
        else:
            self.log("ADB overlay cleanup failed.", level=1)

        self._adb_overlay_cleanup_on_close = False
        self._adb_overlay_mode_active = False

    def _cleanup_adb_overlay_if_needed_async(self):
        if not getattr(self, "_adb_overlay_cleanup_on_close", False):
            return

        serial = getattr(self, "_last_launch_serial", None)
        env_overrides = getattr(self, "_last_launch_env_overrides", {})
        self._adb_overlay_cleanup_on_close = False
        self._adb_overlay_mode_active = False

        def _work():
            return self._run_adb_overlay_command_blocking("none", serial, env_overrides)

        def _on_result(result):
            self._emit_log_messages(result.get("logs", []))
            if result.get("ok"):
                self.log("ADB overlay cleanup complete (overlay_display_devices=none).")
            else:
                self.log("ADB overlay cleanup failed.", level=1)

        def _on_error(msg):
            self.log(f"ADB overlay cleanup failed: {msg}", level=2)

        self._run_background(_work, _on_result, _on_error)

    def _run_post_close_hook_async(self):
        cmd = self.opt_post_close_cmd.text() if hasattr(self, "opt_post_close_cmd") else ""
        env_overrides = getattr(self, "_last_launch_env_overrides", {})
        if not (cmd or "").strip():
            return

        def _work():
            return self._run_shell_hook_blocking("Post-close", cmd, env_overrides)

        def _on_result(logs):
            self._emit_log_messages(logs)

        def _on_error(msg):
            self.log(f"Post-close hook failed: {msg}", level=2)

        self._run_background(_work, _on_result, _on_error)

    @pyqtSlot()
    def start_scrcpy(self):
        if (
            self.scrcpy_process
            and self.scrcpy_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.log("scrcpy is already running.")
            return

        if getattr(self, "_launch_prepare_in_progress", False):
            self.log("scrcpy launch is already being prepared.")
            return

        auto_detect_display = False
        auto_detect_requested = False
        new_display_enabled = False
        use_adb_overlay_mode = False
        adb_overlay_reset_on_close = False
        overlay_spec = ""
        launch_serial = None
        pre_launch_cmd_text = ""
        manual_overlay_create_cmd = False
        try:
            launch_serial = self.device_combo.currentData()
        except Exception:
            launch_serial = None

        try:
            new_display_enabled = (
                hasattr(self, "opt_new_display")
                and self.opt_new_display.isChecked()
            )
            use_adb_overlay_mode = (
                new_display_enabled
                and hasattr(self, "opt_new_display_mode_adb")
                and self.opt_new_display_mode_adb.isChecked()
            )
            adb_overlay_reset_on_close = (
                hasattr(self, "opt_adb_overlay_reset_on_close")
                and self.opt_adb_overlay_reset_on_close.isChecked()
            )
            overlay_spec = (
                self.opt_new_display_res.text().strip()
                if hasattr(self, "opt_new_display_res")
                else ""
            )
            pre_launch_cmd_text = (
                self.opt_pre_launch_cmd.text().strip()
                if hasattr(self, "opt_pre_launch_cmd")
                else ""
            )

            lowered = pre_launch_cmd_text.lower()
            manual_overlay_create_cmd = (
                "settings put global" in lowered
                and "overlay_display_devices" in lowered
                and "overlay_display_devices none" not in lowered
            )
        except Exception:
            new_display_enabled = False
            use_adb_overlay_mode = False
            adb_overlay_reset_on_close = False
            overlay_spec = ""
            pre_launch_cmd_text = ""
            manual_overlay_create_cmd = False

        try:
            auto_detect_requested = (
                hasattr(self, "opt_auto_virtual_display")
                and self.opt_auto_virtual_display.isChecked()
            )
        except Exception:
            auto_detect_requested = False

        auto_detect_display = bool(
            auto_detect_requested
            and (new_display_enabled or manual_overlay_create_cmd)
        )
        if auto_detect_requested and not auto_detect_display:
            self.log(
                "Auto-detect display ID is enabled but inactive because New Display is off and no overlay-creation pre-launch command is set.",
                level=1,
            )

        if use_adb_overlay_mode:
            # ADB workaround mode has its own display detection workflow.
            auto_detect_display = False

        env_overrides: dict[str, str] = {}
        try:
            env_overrides = self._parse_env_vars(self.opt_env_vars.toPlainText())
        except Exception:
            env_overrides = {}

        if launch_serial and "ANDROID_SERIAL" not in env_overrides:
            env_overrides["ANDROID_SERIAL"] = str(launch_serial)
            self.log(
                f"Using selected device for hook commands via ANDROID_SERIAL={launch_serial}"
            )

        self._last_launch_env_overrides = dict(env_overrides)
        self._last_launch_serial = launch_serial
        self._adb_overlay_mode_active = False
        self._adb_overlay_cleanup_on_close = bool(
            adb_overlay_reset_on_close
            and (use_adb_overlay_mode or manual_overlay_create_cmd)
        )
        if self._adb_overlay_cleanup_on_close:
            self.log("Overlay cleanup on close is enabled (overlay_display_devices=none).")
        if env_overrides:
            self.log(
                "Applying environment variables: "
                + ", ".join(sorted(env_overrides.keys()))
            )

        prep_context = {
            "pre_launch_cmd": self.opt_pre_launch_cmd.text() if hasattr(self, "opt_pre_launch_cmd") else "",
            "env_overrides": dict(env_overrides),
            "launch_serial": launch_serial,
            "use_adb_overlay_mode": bool(use_adb_overlay_mode),
            "adb_overlay_reset_on_close": bool(adb_overlay_reset_on_close),
            "overlay_spec": overlay_spec,
            "auto_detect_display": bool(auto_detect_display),
            "cleanup_on_close_armed": bool(self._adb_overlay_cleanup_on_close),
            "base_args": list(self.build_scrcpy_args()),
        }

        self._launch_prepare_in_progress = True
        self.log("Preparing scrcpy launch...")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)

        def _work():
            return self._prepare_launch_context_blocking(prep_context)

        def _on_result(result):
            self._launch_prepare_in_progress = False
            self._emit_log_messages(result.get("logs", []))

            if not result.get("ok"):
                if result.get("request_cleanup"):
                    self._cleanup_adb_overlay_if_needed_async()
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
                return

            detected_display_id = result.get("detected_display_id")
            args = list(prep_context.get("base_args", []))

            if (
                prep_context.get("use_adb_overlay_mode")
                and detected_display_id is not None
                and "--display-id" not in args
            ):
                args.extend(["--display-id", str(detected_display_id)])
                self.opt_display_id.setValue(int(detected_display_id))
                self._adb_overlay_mode_active = True
                self._adb_overlay_cleanup_on_close = bool(
                    prep_context.get("adb_overlay_reset_on_close")
                )

            if (
                prep_context.get("auto_detect_display")
                and detected_display_id is not None
                and "--display-id" not in args
            ):
                args.extend(["--display-id", str(detected_display_id)])

            self._start_scrcpy_process(args, prep_context.get("env_overrides", {}))

        def _on_error(msg):
            self._launch_prepare_in_progress = False
            self.log(f"Launch preparation failed: {msg}", level=2)
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self._cleanup_adb_overlay_if_needed_async()

        self._run_background(_work, _on_result, _on_error)

    def _start_scrcpy_process(self, args, env_overrides):
        if not args:
            self.log("Unable to start scrcpy: command arguments are empty.", level=2)
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            return

        self.scrcpy_process = QProcess(self)
        self.scrcpy_process.readyReadStandardOutput.connect(self.handle_stdout)
        self.scrcpy_process.readyReadStandardError.connect(self.handle_stderr)
        self.scrcpy_process.finished.connect(self.process_finished)
        self.scrcpy_process.errorOccurred.connect(self.process_error)

        if env_overrides:
            proc_env = QProcessEnvironment.systemEnvironment()
            for key, value in env_overrides.items():
                proc_env.insert(key, value)
            self.scrcpy_process.setProcessEnvironment(proc_env)

        cmd = args[0]
        cmd_args = args[1:]
        self.log(f"-> EXECUTING: {cmd} {' '.join(cmd_args)}")

        self.scrcpy_process.start(cmd, cmd_args)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    @pyqtSlot()
    def stop_scrcpy(self):
        if getattr(self, "_launch_prepare_in_progress", False):
            self.log("Launch preparation is in progress.", level=1)
            return

        if (
            self.scrcpy_process
            and self.scrcpy_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.log("Terminating scrcpy process...")
            self.scrcpy_process.terminate()
            # fallback to kill if not dying?
            # self.scrcpy_process.kill()

    @pyqtSlot()
    def handle_stdout(self):
        output = (
            self.scrcpy_process.readAllStandardOutput().data().decode("utf8", "replace")
        )
        for line in output.split("\n"):
            if line:
                self.log(line)

    @pyqtSlot()
    def handle_stderr(self):
        output = (
            self.scrcpy_process.readAllStandardError().data().decode("utf8", "replace")
        )
        for line in output.split("\n"):
            if line:
                self.log(f"ERROR: {line}")

    def process_finished(self, exit_code, exit_status):
        self.log(f"scrcpy exited with code {exit_code}.")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._launch_prepare_in_progress = False

        try:
            self._cleanup_adb_overlay_if_needed_async()
        except Exception:
            pass

        try:
            self._run_post_close_hook_async()
        except Exception:
            pass

    def process_error(self, error):
        self.log(f"scrcpy process error: {error}")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._launch_prepare_in_progress = False

        try:
            self._cleanup_adb_overlay_if_needed_async()
        except Exception:
            pass

    def on_filter_changed(self):
        # Refresh console view and persist filter settings
        try:
            self.refresh_console()
        finally:
            self.save_settings_event()

    def save_settings_event(self):
        try:
            # merge with existing settings so we don't drop unknown keys
            settings = load_settings()
            settings.update(
                {
                    "auto_connect": bool(self.chk_auto_connect.isChecked()),
                    "show_info": bool(self.chk_show_info.isChecked()),
                    "show_warn": bool(self.chk_show_warn.isChecked()),
                    "show_error": bool(self.chk_show_error.isChecked()),
                    "start_in_tray": bool(getattr(self, "action_start_in_tray", False) and self.action_start_in_tray.isChecked()),
                    "autostart_enabled": bool(getattr(self, "action_autostart", False) and self.action_autostart.isChecked()),
                }
            )
            save_settings(settings)
        except Exception as e:
            # non-fatal: keep running even if settings fail to write
            self.log(f"Settings save error: {e}")

