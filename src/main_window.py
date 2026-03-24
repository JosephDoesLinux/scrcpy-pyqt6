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
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QTextEdit,
    QSplitter,
    QStyle,
    QFileDialog,
    QMessageBox,
    QDialog,
    QInputDialog,
    QScrollArea,
    QFrame,
    QMenuBar,
)
from PyQt6.QtWidgets import QBoxLayout
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, pyqtSlot, QTimer, QEvent
import subprocess
import json
from pathlib import Path
from PyQt6.QtGui import QIcon, QFont, QAction, QPalette
from adb import (
    get_devices,
    connect_device,
    disconnect_device,
    get_mdns_services,
    pair_device,
)
from profiles import (
    load_profiles,
    save_profiles,
    CONFIG_DIR,
    load_settings,
    save_settings,
)


class ScrcpyWrapper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scrcpy-PyQt6")
        self.resize(850, 650)
        self.init_ui()
        self.refresh_devices()

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
        # Use palette colors to create a subtle, theme-aware handle with thin dividers
        pal = self.palette()
        light = pal.color(QPalette.ColorRole.Light).name()
        mid = pal.color(QPalette.ColorRole.Mid).name()
        window = pal.color(QPalette.ColorRole.Window).name()
        self.splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {window}; }}"
            f"QSplitter::handle:vertical {{ border-top: 1px solid {light}; border-bottom: 1px solid {mid}; }}"
        )
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

        # Small status label for network operations
        self.network_status = QLabel("")
        self.network_status.setFont(child_font)
        # Rely on the application's palette for text color so it follows system theme changes
        device_layout.addWidget(self.network_status)

        # We'll place `device_group` into the responsive content area below

        # keep an in-memory set of discovered network addresses for health checks
        self.discovered_addresses = set()

        # Health check timer (attempt reconnects when Auto-connect is enabled)
        self.health_timer = QTimer(self)
        self.health_timer.setInterval(10_000)  # 10 seconds
        self.health_timer.timeout.connect(self.check_device_health)
        self.health_timer.start()

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
        self.profile_combo.currentTextChanged.connect(self.apply_profile)

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
                ver = proc.stdout.strip().split()[-1]
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
            pal = self.palette()
            light = pal.color(QPalette.ColorRole.Light).name()
            mid = pal.color(QPalette.ColorRole.Mid).name()
            window = pal.color(QPalette.ColorRole.Window).name()
            # Update splitter handle styling to match the new palette
            try:
                self.splitter.setStyleSheet(
                    f"QSplitter::handle {{ background: {window}; }}"
                    f"QSplitter::handle:vertical {{ border-top: 1px solid {light}; border-bottom: 1px solid {mid}; }}"
                )
            except Exception:
                pass

        # (Console is created in init_ui; changeEvent should only update palette-related styling)

    def resizeEvent(self, event):
        # Responsive layout: switch content layout direction based on width
        try:
            w = self.width()
            if w >= 1000:
                self.content_layout.setDirection(QBoxLayout.Direction.LeftToRight)
                # prefer left column narrower
                self.content_layout.setStretch(0, 1)
                self.content_layout.setStretch(1, 3)
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

    def init_video_tab(self):
        layout = QFormLayout(self.tab_video)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_bitrate = QComboBox()
        self.opt_bitrate.addItems(["Default (8M)", "16M", "24M", "2M", "4M", "32M"])
        self.opt_bitrate.setEditable(True)

        self.opt_max_fps = QSpinBox()
        self.opt_max_fps.setRange(0, 144)
        self.opt_max_fps.setValue(0)
        self.opt_max_fps.setSpecialValueText("0 (Unlimited / Default)")

        self.opt_max_size = QSpinBox()
        self.opt_max_size.setRange(0, 4000)
        self.opt_max_size.setValue(0)
        self.opt_max_size.setSpecialValueText("0 (Unlimited)")

        self.opt_codec = QComboBox()
        self.opt_codec.addItems(["h264 (Default)", "h265", "av1"])

        self.opt_video_source = QComboBox()
        self.opt_video_source.addItems(["display (Default)", "camera"])

        self.opt_display_id = QSpinBox()
        self.opt_display_id.setRange(0, 10)
        self.opt_display_id.setValue(0)

        self.opt_camera_facing = QComboBox()
        self.opt_camera_facing.addItems(["any", "front", "back", "external"])

        self.opt_new_display = QCheckBox("New Display (--new-display) (A-10+)")
        self.opt_new_display_res = QLineEdit()
        self.opt_new_display_res.setPlaceholderText("Optional: e.g. 1920x1080/420")

        self.opt_fullscreen = QCheckBox("Start in Fullscreen (-f)")
        self.opt_always_on_top = QCheckBox("Always On Top (--always-on-top)")
        self.opt_borderless = QCheckBox("Borderless Window (--window-borderless)")
        self.opt_no_window = QCheckBox("Disable Window (--no-window)")
        self.opt_no_video = QCheckBox("Disable Video (--no-video)")

        layout.addRow("Video Source:", self.opt_video_source)
        layout.addRow("Display ID (--display-id):", self.opt_display_id)
        layout.addRow("Camera Facing (--camera-facing):", self.opt_camera_facing)
        layout.addRow("New Display:", self.opt_new_display)
        layout.addRow("New Display Res:", self.opt_new_display_res)
        layout.addRow("Video Bitrate (-b):", self.opt_bitrate)
        layout.addRow("Max FPS (--max-fps):", self.opt_max_fps)
        layout.addRow("Max Size (-m):", self.opt_max_size)
        layout.addRow("Video Codec (--video-codec):", self.opt_codec)
        layout.addRow("", self.opt_fullscreen)
        layout.addRow("", self.opt_always_on_top)
        layout.addRow("", self.opt_borderless)
        layout.addRow("", self.opt_no_window)
        layout.addRow("", self.opt_no_video)

    def init_audio_tab(self):
        layout = QFormLayout(self.tab_audio)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_no_audio = QCheckBox("Disable Audio (--no-audio)")

        self.opt_audio_source = QComboBox()
        self.opt_audio_source.addItems(
            [
                "output (Default)",
                "playback",
                "mic",
                "mic-camcorder",
                "mic-voice-communication",
                "voice-call",
            ]
        )

        self.opt_audio_codec = QComboBox()
        self.opt_audio_codec.addItems(["opus (Default)", "aac", "flac", "raw"])

        self.opt_no_audio_playback = QCheckBox(
            "Disable Audio Playback (--no-audio-playback)"
        )

        layout.addRow("", self.opt_no_audio)
        layout.addRow("Audio Source (--audio-source):", self.opt_audio_source)
        layout.addRow("Audio Codec (--audio-codec):", self.opt_audio_codec)
        layout.addRow("", self.opt_no_audio_playback)

    def init_control_tab(self):
        layout = QFormLayout(self.tab_control)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_read_only = QCheckBox("Read-only (Disable control) (-n)")

        self.opt_keyboard_mode = QComboBox()
        self.opt_keyboard_mode.addItems(["sdk (Default)", "uhid", "aoa", "disabled"])

        self.opt_mouse_mode = QComboBox()
        self.opt_mouse_mode.addItems(["sdk (Default)", "uhid", "aoa", "disabled"])

        self.opt_stay_awake = QCheckBox("Stay Awake (w/ screen on) (-w)")
        self.opt_turn_screen_off = QCheckBox("Turn Screen Off (-S)")
        self.opt_show_touches = QCheckBox("Show Touches (-t)")
        self.opt_power_off_close = QCheckBox(
            "Power Off On Close (--power-off-on-close)"
        )

        self.opt_otg = QCheckBox("OTG Mode (Physical KB/Mouse via USB) (--otg)")
        self.opt_disable_screensaver = QCheckBox(
            "Disable Screensaver (--disable-screensaver)"
        )

        layout.addRow("Interaction:", self.opt_read_only)
        layout.addRow("Input:", self.opt_keyboard_mode)
        layout.addRow("", self.opt_mouse_mode)
        layout.addRow("", self.opt_otg)
        layout.addRow("Display:", self.opt_stay_awake)
        layout.addRow("", self.opt_turn_screen_off)
        layout.addRow("", self.opt_show_touches)
        layout.addRow("", self.opt_disable_screensaver)
        layout.addRow("Exit Behavior:", self.opt_power_off_close)

    def init_record_tab(self):
        layout = QFormLayout(self.tab_record)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_record_file = QLineEdit()
        self.opt_record_file.setPlaceholderText("e.g. /home/user/Videos/capture.mp4")

        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_record_file)

        record_file_layout = QHBoxLayout()
        record_file_layout.setContentsMargins(0, 0, 0, 0)
        record_file_layout.addWidget(self.opt_record_file)
        record_file_layout.addWidget(btn_browse)

        self.opt_record_format = QComboBox()
        self.opt_record_format.addItems(
            [
                "Auto (from extension)",
                "mp4",
                "mkv",
                "m4a",
                "mka",
                "opus",
                "aac",
                "flac",
                "wav",
            ]
        )

        self.opt_record_orientation = QComboBox()
        self.opt_record_orientation.addItems(["0 (Default)", "90", "180", "270"])

        self.opt_no_playback = QCheckBox(
            "Record in background (Disable video and audio playback) (-N)"
        )

        layout.addRow("Record File (-r):", record_file_layout)
        layout.addRow("Record Format (--record-format):", self.opt_record_format)
        layout.addRow("Record Orientation:", self.opt_record_orientation)
        layout.addRow("", self.opt_no_playback)

    def init_advanced_tab(self):
        layout = QFormLayout(self.tab_advanced)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_v4l2_sink = QLineEdit()
        self.opt_v4l2_sink.setPlaceholderText("e.g. /dev/video0 (Linux Only)")

        self.opt_v4l2_buffer = QSpinBox()
        self.opt_v4l2_buffer.setRange(0, 5000)
        self.opt_v4l2_buffer.setValue(0)
        self.opt_v4l2_buffer.setSpecialValueText("0 (No buffering)")

        self.opt_start_app = QLineEdit()
        self.opt_start_app.setPlaceholderText(
            "Exact package name (e.g. org.mozilla.firefox)"
        )

        self.opt_custom_args = QLineEdit()
        self.opt_custom_args.setPlaceholderText(
            "e.g. --legacy-paste --shortcut-mod=lalt"
        )

        layout.addRow("V4L2 Sink (Webcam mode):", self.opt_v4l2_sink)
        layout.addRow("V4L2 Buffer (ms):", self.opt_v4l2_buffer)
        layout.addRow("Start App on Launch:", self.opt_start_app)
        layout.addRow("Custom Arguments:", self.opt_custom_args)

    @pyqtSlot()
    def browse_record_file(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Select Recording File",
            "",
            "Video Files (*.mp4 *.mkv);;Audio Files (*.m4a *.mka *.opus *.aac *.flac *.wav);;All Files (*)",
        )
        if filepath:
            self.opt_record_file.setText(filepath)

    def log(self, text: str):
        # Non-destructive logging: classify and store entries, then refresh view
        txt = str(text)
        ltxt = txt.lower()
        level = "info"
        if "error" in ltxt or "failed" in ltxt or "exception" in ltxt:
            level = "error"
        elif "warn" in ltxt or "warning" in ltxt:
            level = "warn"

        self._log_entries.append((level, txt))
        # Keep a bounded history to avoid runaway memory usage
        if len(self._log_entries) > 5000:
            self._log_entries.pop(0)

        self.refresh_console()

    @pyqtSlot()
    def refresh_devices(self):
        self.device_combo.clear()
        self.log("Refreshing ADB device list...")
        devices = get_devices()

        if not devices:
            self.device_combo.addItem("No devices found")
            self.device_combo.setEnabled(False)
            self.btn_start.setEnabled(False)
        else:
            self.device_combo.setEnabled(True)
            self.btn_start.setEnabled(True)
            for d in devices:
                self.device_combo.addItem(
                    f"{d['serial']} [{d['state']}] - {d['model']}", userData=d["serial"]
                )
            self.log(f"Found {len(devices)} device(s).")

    @pyqtSlot()
    def scan_mdns(self):
        self.mdns_combo.clear()
        self.log("Scanning for mDNS devices on the local network...")
        services = get_mdns_services()
        if not services:
            self.mdns_combo.addItem("No network devices found (or mDNS unsupported).")
        else:
            self.mdns_combo.addItem("Select a device to pair/connect...", userData=None)
            # populate combo and record discovered addresses
            for s in services:
                self.mdns_combo.addItem(
                    f"{s['name']} ({s['address']})", userData=s["address"]
                )
                addr = s.get("address")
                if addr:
                    self.discovered_addresses.add(addr)

            self.log(f"Found {len(services)} network device(s).")

            # If auto-connect enabled, try connecting to connect-capable services
            if (
                getattr(self, "chk_auto_connect", None)
                and self.chk_auto_connect.isChecked()
            ):
                for s in services:
                    if "connect" in s.get("type", "").lower():
                        addr = s.get("address")
                        if addr:
                            self.log(f"Auto-connecting to {addr}...")
                            result = connect_device(addr)
                            self.log(result)
                            # Update quick status label
                            self.network_status.setText(
                                f"Last: {addr} -> {result.splitlines()[0] if result else ''}"
                            )
                            if (
                                "connected" in result.lower()
                                or "already connected" in result.lower()
                            ):
                                self.refresh_devices()

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

    @pyqtSlot()
    def pair_wireless(self):
        address = self.mdns_combo.currentData()
        if not address:
            address = self.ip_input.text().strip()
            if not address:
                self.log(
                    "Error: Select a network device or enter an IP address manually to pair."
                )
                return

        code, ok = QInputDialog.getText(
            self, "Pair Device", f"Enter the 6-digit pairing code for {address}:"
        )
        if ok and code:
            self.log(f"Attempting adb pair with {address}...")
            result = pair_device(address, code)
            self.log(result)
            # update quick status and refresh devices
            self.network_status.setText(
                f"Pair result: {result.splitlines()[0] if result else ''}"
            )
            self.refresh_devices()

    @pyqtSlot()
    def connect_wireless(self):
        # Allow connecting from the mDNS combo or the manual IP input
        address = self.mdns_combo.currentData()
        if not address:
            address = self.ip_input.text().strip()

        if not address:
            self.log(
                "Error: Select a network device or enter an IP address manually to connect."
            )
            return

        self.log(f"Attempting adb connect {address}...")
        result = connect_device(address)
        self.log(result)
        # update quick status and refresh
        self.network_status.setText(
            f"Connect result: {result.splitlines()[0] if result else ''}"
        )
        self.refresh_devices()

    @pyqtSlot()
    def check_device_health(self):
        # Poll adb devices and attempt reconnects for discovered network addresses
        try:
            devices = get_devices()
            serials = {d["serial"] for d in devices}
            # For each discovered address, if it's not listed in adb devices, try reconnect
            for addr in list(self.discovered_addresses):
                if addr not in serials:
                    if (
                        getattr(self, "chk_auto_connect", None)
                        and self.chk_auto_connect.isChecked()
                    ):
                        self.log(f"Health-check: attempting reconnect to {addr}...")
                        res = connect_device(addr)
                        self.log(res)
                        self.network_status.setText(
                            f"Health: {addr} -> {res.splitlines()[0] if res else ''}"
                        )
                        if (
                            "connected" in res.lower()
                            or "already connected" in res.lower()
                        ):
                            self.refresh_devices()
        except Exception as e:
            self.log(f"Health-check error: {e}")

    def build_scrcpy_args(self) -> list:
        args = ["scrcpy"]

        # Determine specific device
        serial = self.device_combo.currentData()
        if serial:
            args.extend(["-s", serial])

        # Video args
        bitrate = self.opt_bitrate.currentText()
        if not bitrate.startswith("Default"):
            # strip " (8M)" etc. No wait, it's just e.g. "16M", so we can use text directly
            # For editable, user might type "10M"
            args.extend(["-b", bitrate])

        if self.opt_max_fps.value() > 0:
            args.extend(["--max-fps", str(self.opt_max_fps.value())])

        if self.opt_max_size.value() > 0:
            args.extend(["-m", str(self.opt_max_size.value())])

        codec = self.opt_codec.currentText().split()[0]  # e.g. "h264"
        if codec != "h264":
            args.extend(["--video-codec", codec])

        if self.opt_fullscreen.isChecked():
            args.append("-f")

        if self.opt_always_on_top.isChecked():
            args.append("--always-on-top")

        if self.opt_borderless.isChecked():
            args.append("--window-borderless")

        if self.opt_no_window.isChecked():
            args.append("--no-window")

        if self.opt_no_video.isChecked():
            args.append("--no-video")

        if self.opt_new_display.isChecked():
            res = self.opt_new_display_res.text().strip()
            if res:
                args.append(f"--new-display={res}")
            else:
                args.append("--new-display")

        video_source = self.opt_video_source.currentText().split()[0]
        if video_source != "display":
            args.extend(["--video-source", video_source])
            camera_facing = self.opt_camera_facing.currentText()
            if camera_facing != "any":
                args.extend(["--camera-facing", camera_facing])
        else:
            display_id = self.opt_display_id.value()
            if display_id > 0:
                args.extend(["--display-id", str(display_id)])

        record_file = self.opt_record_file.text().strip()
        if record_file:
            args.extend(["-r", record_file])
            record_format = self.opt_record_format.currentText().split()[0]
            if record_format != "Auto":
                args.extend(["--record-format", record_format])
            record_orientation = self.opt_record_orientation.currentText().split()[0]
            if record_orientation != "0":
                args.extend(["--record-orientation", record_orientation])
            if self.opt_no_playback.isChecked():
                args.append("-N")

        # Audio args
        if self.opt_no_audio.isChecked():
            args.append("--no-audio")
        else:
            a_source = self.opt_audio_source.currentText().split()[0]
            if a_source != "output":
                args.extend(["--audio-source", a_source])

            a_codec = self.opt_audio_codec.currentText().split()[0]
            if a_codec != "opus":
                args.extend(["--audio-codec", a_codec])

            if self.opt_no_audio_playback.isChecked():
                args.append("--no-audio-playback")

        # Control args
        if self.opt_read_only.isChecked():
            args.append("-n")

        if self.opt_stay_awake.isChecked():
            args.append("-w")

        if self.opt_turn_screen_off.isChecked():
            args.append("-S")

        if self.opt_show_touches.isChecked():
            args.append("-t")

        if self.opt_power_off_close.isChecked():
            args.append("--power-off-on-close")

        if self.opt_otg.isChecked():
            args.append("--otg")

        if self.opt_disable_screensaver.isChecked():
            args.append("--disable-screensaver")

        kb_mode = self.opt_keyboard_mode.currentText().split()[0]
        if kb_mode != "sdk":
            args.extend(["--keyboard", kb_mode])

        mouse_mode = self.opt_mouse_mode.currentText().split()[0]
        if mouse_mode != "sdk":
            args.extend(["--mouse", mouse_mode])

        # Advanced custom args
        v4l2_sink = self.opt_v4l2_sink.text().strip()
        if v4l2_sink:
            args.extend(["--v4l2-sink", v4l2_sink])
            v4l2_buffer = self.opt_v4l2_buffer.value()
            if v4l2_buffer > 0:
                args.extend(["--v4l2-buffer", str(v4l2_buffer)])

        start_app = self.opt_start_app.text().strip()
        if start_app:
            args.extend(["--start-app", start_app])

        custom = self.opt_custom_args.text().strip()
        if custom:
            import shlex

            args.extend(shlex.split(custom))

        return args

    @pyqtSlot()
    def start_scrcpy(self):
        if (
            self.scrcpy_process
            and self.scrcpy_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.log("scrcpy is already running.")
            return

        args = self.build_scrcpy_args()

        self.scrcpy_process = QProcess(self)
        self.scrcpy_process.readyReadStandardOutput.connect(self.handle_stdout)
        self.scrcpy_process.readyReadStandardError.connect(self.handle_stderr)
        self.scrcpy_process.finished.connect(self.process_finished)
        self.scrcpy_process.errorOccurred.connect(self.process_error)

        # Execute Scrcpy
        cmd = args[0]
        cmd_args = args[1:]
        self.log(f"-> EXECUTING: {cmd} {' '.join(cmd_args)}")

        self.scrcpy_process.start(cmd, cmd_args)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    @pyqtSlot()
    def stop_scrcpy(self):
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

    def process_error(self, error):
        self.log(f"scrcpy process error: {error}")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def get_ui_state(self):
        return {
            "bitrate": self.opt_bitrate.currentText(),
            "max_fps": self.opt_max_fps.value(),
            "max_size": self.opt_max_size.value(),
            "codec": self.opt_codec.currentIndex(),
            "video_source": self.opt_video_source.currentIndex(),
            "display_id": self.opt_display_id.value(),
            "camera_facing": self.opt_camera_facing.currentIndex(),
            "fullscreen": self.opt_fullscreen.isChecked(),
            "always_on_top": self.opt_always_on_top.isChecked(),
            "borderless": self.opt_borderless.isChecked(),
            "no_window": self.opt_no_window.isChecked(),
            "no_video": self.opt_no_video.isChecked(),
            "new_display": self.opt_new_display.isChecked(),
            "new_display_res": self.opt_new_display_res.text(),
            "no_audio": self.opt_no_audio.isChecked(),
            "audio_source": self.opt_audio_source.currentIndex(),
            "audio_codec": self.opt_audio_codec.currentIndex(),
            "no_audio_playback": self.opt_no_audio_playback.isChecked(),
            "read_only": self.opt_read_only.isChecked(),
            "keyboard_mode": self.opt_keyboard_mode.currentIndex(),
            "mouse_mode": self.opt_mouse_mode.currentIndex(),
            "stay_awake": self.opt_stay_awake.isChecked(),
            "turn_screen_off": self.opt_turn_screen_off.isChecked(),
            "show_touches": self.opt_show_touches.isChecked(),
            "power_off_close": self.opt_power_off_close.isChecked(),
            "otg": self.opt_otg.isChecked(),
            "disable_screensaver": self.opt_disable_screensaver.isChecked(),
            "record_format": self.opt_record_format.currentIndex(),
            "record_orientation": self.opt_record_orientation.currentIndex(),
            "no_playback": self.opt_no_playback.isChecked(),
            "v4l2_sink": self.opt_v4l2_sink.text(),
            "v4l2_buffer": self.opt_v4l2_buffer.value(),
        }

    def set_ui_state(self, state):
        self.opt_bitrate.setCurrentText(state.get("bitrate", "Default (8M)"))
        self.opt_max_fps.setValue(state.get("max_fps", 0))
        self.opt_max_size.setValue(state.get("max_size", 0))
        self.opt_codec.setCurrentIndex(state.get("codec", 0))
        self.opt_video_source.setCurrentIndex(state.get("video_source", 0))
        self.opt_display_id.setValue(state.get("display_id", 0))
        self.opt_camera_facing.setCurrentIndex(state.get("camera_facing", 0))
        self.opt_fullscreen.setChecked(state.get("fullscreen", False))
        self.opt_always_on_top.setChecked(state.get("always_on_top", False))
        self.opt_borderless.setChecked(state.get("borderless", False))
        self.opt_no_window.setChecked(state.get("no_window", False))
        self.opt_no_video.setChecked(state.get("no_video", False))
        self.opt_new_display.setChecked(state.get("new_display", False))
        self.opt_new_display_res.setText(state.get("new_display_res", ""))

        self.opt_no_audio.setChecked(state.get("no_audio", False))
        self.opt_audio_source.setCurrentIndex(state.get("audio_source", 0))
        self.opt_audio_codec.setCurrentIndex(state.get("audio_codec", 0))
        self.opt_no_audio_playback.setChecked(state.get("no_audio_playback", False))

        self.opt_read_only.setChecked(state.get("read_only", False))
        self.opt_keyboard_mode.setCurrentIndex(state.get("keyboard_mode", 0))
        self.opt_mouse_mode.setCurrentIndex(state.get("mouse_mode", 0))
        self.opt_stay_awake.setChecked(state.get("stay_awake", False))
        self.opt_turn_screen_off.setChecked(state.get("turn_screen_off", False))
        self.opt_show_touches.setChecked(state.get("show_touches", False))
        self.opt_power_off_close.setChecked(state.get("power_off_close", False))
        self.opt_otg.setChecked(state.get("otg", False))
        self.opt_disable_screensaver.setChecked(state.get("disable_screensaver", False))

        self.opt_record_format.setCurrentIndex(state.get("record_format", 0))
        self.opt_record_orientation.setCurrentIndex(state.get("record_orientation", 0))
        self.opt_no_playback.setChecked(state.get("no_playback", False))

        self.opt_v4l2_sink.setText(state.get("v4l2_sink", ""))
        self.opt_v4l2_buffer.setValue(state.get("v4l2_buffer", 0))
        if (
            state.get("v4l2_sink_default", False)
            and not self.opt_v4l2_sink.text().strip()
        ):
            self.opt_v4l2_sink.setText("/dev/video0")

    @pyqtSlot(str)
    def apply_profile(self, name):
        if not name or name not in self.profiles:
            return
        self.set_ui_state(self.profiles[name])
        self.log(f"Applied profile '{name}'.")

    @pyqtSlot()
    def save_profile(self):
        name, ok = QInputDialog.getText(
            self,
            "Save Profile",
            "Enter profile name:",
            text=self.profile_combo.currentText(),
        )
        if ok and name:
            self.profiles[name] = self.get_ui_state()
            save_profiles(self.profiles)
            if self.profile_combo.findText(name) == -1:
                self.profile_combo.addItem(name)
            self.profile_combo.setCurrentText(name)
            self.log(f"Saved profile '{name}'.")

    @pyqtSlot()
    def delete_profile(self):
        name = self.profile_combo.currentText()
        if name in [
            "Default",
            "Desktop (New Display)",
            "Wireless (Low Bandwidth)",
            "Gaming (Low Latency / UHID)",
            "Audio Only",
            "Webcam (Linux V4L2)",
        ]:
            QMessageBox.warning(
                self, "Delete Profile", "Cannot delete default profiles."
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if name in self.profiles:
                del self.profiles[name]
                save_profiles(self.profiles)
                idx = self.profile_combo.findText(name)
                if idx != -1:
                    self.profile_combo.removeItem(idx)
                self.log(f"Deleted profile '{name}'.")

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
                }
            )
            save_settings(settings)
        except Exception as e:
            # non-fatal: keep running even if settings fail to write
            self.log(f"Settings save error: {e}")

    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addSeparator()
        exit_action = QAction("Quit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
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

    def open_preferences(self):
        # Preferences page removed — follow system theme by default.
        QMessageBox.information(
            self,
            "Preferences",
            "Preferences have been removed. The app follows the system theme by default.",
        )

    def apply_easy_mode(self, enabled: bool):
        # Easy mode removed — no-op
        return

    def new_profile(self):
        base = "Quick Profile"
        name = base
        i = 1
        while name in self.profiles:
            i += 1
            name = f"{base} {i}"

        name, ok = QInputDialog.getText(
            self, "New Profile", "Enter name for new profile:", text=name
        )
        if ok and name:
            if name in self.profiles:
                QMessageBox.warning(
                    self, "New Profile", "A profile with that name already exists."
                )
                return
            self.profiles[name] = self.get_ui_state()
            save_profiles(self.profiles)
            self.profile_combo.addItem(name)
            self.profile_combo.setCurrentText(name)
            self.log(f"Created new profile '{name}'.")

    def closeEvent(self, event):
        # Persist settings on close
        try:
            self.save_settings_event()
        except Exception:
            pass
        super().closeEvent(event)

    def get_ui_state(self):
        return {
            "bitrate": self.opt_bitrate.currentText(),
            "max_fps": self.opt_max_fps.value(),
            "max_size": self.opt_max_size.value(),
            "codec": self.opt_codec.currentIndex(),
            "video_source": self.opt_video_source.currentIndex(),
            "display_id": self.opt_display_id.value(),
            "camera_facing": self.opt_camera_facing.currentIndex(),
            "fullscreen": self.opt_fullscreen.isChecked(),
            "always_on_top": self.opt_always_on_top.isChecked(),
            "borderless": self.opt_borderless.isChecked(),
            "no_window": self.opt_no_window.isChecked(),
            "new_display": self.opt_new_display.isChecked(),
            "new_display_res": self.opt_new_display_res.text(),
            "no_audio": self.opt_no_audio.isChecked(),
            "audio_source": self.opt_audio_source.currentIndex(),
            "audio_codec": self.opt_audio_codec.currentIndex(),
            "no_audio_playback": self.opt_no_audio_playback.isChecked(),
            "read_only": self.opt_read_only.isChecked(),
            "keyboard_mode": self.opt_keyboard_mode.currentIndex(),
            "mouse_mode": self.opt_mouse_mode.currentIndex(),
            "stay_awake": self.opt_stay_awake.isChecked(),
            "turn_screen_off": self.opt_turn_screen_off.isChecked(),
            "show_touches": self.opt_show_touches.isChecked(),
            "power_off_close": self.opt_power_off_close.isChecked(),
            "otg": self.opt_otg.isChecked(),
            "disable_screensaver": self.opt_disable_screensaver.isChecked(),
            "record_format": self.opt_record_format.currentIndex(),
            "record_orientation": self.opt_record_orientation.currentIndex(),
            "no_playback": self.opt_no_playback.isChecked(),
            "v4l2_buffer": self.opt_v4l2_buffer.value(),
        }

    def set_ui_state(self, state):
        self.opt_bitrate.setCurrentText(state.get("bitrate", "Default (8M)"))
        self.opt_max_fps.setValue(state.get("max_fps", 0))
        self.opt_max_size.setValue(state.get("max_size", 0))
        self.opt_codec.setCurrentIndex(state.get("codec", 0))
        self.opt_video_source.setCurrentIndex(state.get("video_source", 0))
        self.opt_display_id.setValue(state.get("display_id", 0))
        self.opt_camera_facing.setCurrentIndex(state.get("camera_facing", 0))
        self.opt_fullscreen.setChecked(state.get("fullscreen", False))
        self.opt_always_on_top.setChecked(state.get("always_on_top", False))
        self.opt_borderless.setChecked(state.get("borderless", False))
        self.opt_no_window.setChecked(state.get("no_window", False))
        self.opt_new_display.setChecked(state.get("new_display", False))
        self.opt_new_display_res.setText(state.get("new_display_res", ""))

        self.opt_no_audio.setChecked(state.get("no_audio", False))
        self.opt_audio_source.setCurrentIndex(state.get("audio_source", 0))
        self.opt_audio_codec.setCurrentIndex(state.get("audio_codec", 0))
        self.opt_no_audio_playback.setChecked(state.get("no_audio_playback", False))

        self.opt_read_only.setChecked(state.get("read_only", False))
        self.opt_keyboard_mode.setCurrentIndex(state.get("keyboard_mode", 0))
        self.opt_mouse_mode.setCurrentIndex(state.get("mouse_mode", 0))
        self.opt_stay_awake.setChecked(state.get("stay_awake", False))
        self.opt_turn_screen_off.setChecked(state.get("turn_screen_off", False))
        self.opt_show_touches.setChecked(state.get("show_touches", False))
        self.opt_power_off_close.setChecked(state.get("power_off_close", False))
        self.opt_otg.setChecked(state.get("otg", False))
        self.opt_disable_screensaver.setChecked(state.get("disable_screensaver", False))

        self.opt_record_format.setCurrentIndex(state.get("record_format", 0))
        self.opt_record_orientation.setCurrentIndex(state.get("record_orientation", 0))
        self.opt_no_playback.setChecked(state.get("no_playback", False))

        self.opt_v4l2_buffer.setValue(state.get("v4l2_buffer", 0))

    @pyqtSlot(str)
    def apply_profile(self, name):
        if not name or name not in self.profiles:
            return
        self.set_ui_state(self.profiles[name])
        self.log(f"Applied profile '{name}'.")

    @pyqtSlot()
    def save_profile(self):
        name, ok = QInputDialog.getText(
            self,
            "Save Profile",
            "Enter profile name:",
            text=self.profile_combo.currentText(),
        )
        if ok and name:
            self.profiles[name] = self.get_ui_state()
            save_profiles(self.profiles)
            if self.profile_combo.findText(name) == -1:
                self.profile_combo.addItem(name)
            self.profile_combo.setCurrentText(name)
            self.log(f"Saved profile '{name}'.")

    @pyqtSlot()
    def delete_profile(self):
        name = self.profile_combo.currentText()
        if name in [
            "Default",
            "Desktop (New Display)",
            "Wireless (Low Bandwidth)",
            "Gaming (Low Latency / UHID)",
        ]:
            QMessageBox.warning(
                self, "Delete Profile", "Cannot delete default profiles."
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if name in self.profiles:
                del self.profiles[name]
                save_profiles(self.profiles)
                idx = self.profile_combo.findText(name)
                if idx != -1:
                    self.profile_combo.removeItem(idx)
                self.log(f"Deleted profile '{name}'.")
