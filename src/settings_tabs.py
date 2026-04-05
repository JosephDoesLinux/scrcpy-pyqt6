"""
settings_tabs.py — Scrcpy options tabs + profile bar + launch controls.

SettingsTabs owns:
  • the profile combo (selecting applies the profile immediately)
  • five option tabs (Video, Audio, Control, Recording, Advanced)
  • Launch / Stop buttons

State is serialised via get_ui_state() / set_ui_state() and the full
scrcpy argument list is built by build_scrcpy_args(serial).
"""
import shlex

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QLineEdit, QTabWidget,
    QCheckBox, QSpinBox, QScrollArea, QFrame, QFileDialog,
    QStyle, QMessageBox, QInputDialog,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from profiles import save_profiles


class SettingsTabs(QWidget):
    """
    Scrcpy options widget: profile bar + tabs + launch buttons.

    Signals
    -------
    launch_requested   – user clicked Launch (main window calls start_scrcpy)
    stop_requested     – user clicked Stop
    profile_saved      – profile was saved/created  (str: name)
    profile_deleted    – profile was deleted         (str: name)
    """

    launch_requested = pyqtSignal()
    stop_requested   = pyqtSignal()
    profile_saved    = pyqtSignal(str)
    profile_deleted  = pyqtSignal(str)

    def __init__(self, profiles: dict, parent=None):
        super().__init__(parent)
        # SettingsTabs is the authoritative owner of the profiles dict
        self._profiles = dict(profiles)
        self._active_profile: str | None = None
        self._is_running = False
        self._has_devices = False
        self._init_ui()

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def active_profile(self) -> str | None:
        return self._active_profile

    def set_profiles(self, profiles: dict):
        """Replace the profiles dict and rebuild the combo."""
        self._profiles = dict(profiles)
        current = self.profile_combo.currentText()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(list(self._profiles.keys()))
        idx = self.profile_combo.findText(current)
        self.profile_combo.setCurrentIndex(idx if idx != -1 else 0)
        self.profile_combo.blockSignals(False)

    def apply_profile(self, name: str):
        """Load a named profile into the UI controls (no-op if unknown)."""
        if not name or name not in self._profiles:
            return
        self._active_profile = name
        # Update combo without triggering the signal (avoid recursion)
        self.profile_combo.blockSignals(True)
        idx = self.profile_combo.findText(name)
        if idx != -1:
            self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)
        self.set_ui_state(self._profiles[name])

    def set_running(self, running: bool):
        """Reflect scrcpy running state in button enabled/disabled."""
        self._is_running = running
        self._sync_launch_btn()
        self.btn_stop.setEnabled(running)

    def set_has_devices(self, has_devices: bool):
        """Reflect whether any ADB device is available."""
        self._has_devices = has_devices
        self._sync_launch_btn()

    def _sync_launch_btn(self):
        self.btn_start.setEnabled(self._has_devices and not self._is_running)

    # ── UI construction ────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self._build_profile_bar())
        layout.addWidget(self._build_tabs())
        layout.addWidget(self._build_action_bar())

    def _build_profile_bar(self) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        row.addWidget(QLabel("Profile:"))

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumHeight(30)
        self.profile_combo.addItems(list(self._profiles.keys()))
        # Selecting from the combo applies the profile immediately
        self.profile_combo.currentTextChanged.connect(self._on_profile_combo_changed)
        row.addWidget(self.profile_combo, 1)

        for label, px, slot in (
            (" Save",   QStyle.StandardPixmap.SP_DialogSaveButton,   self._save_profile),
            (" New",    QStyle.StandardPixmap.SP_FileDialogNewFolder, self._new_profile),
            (" Delete", QStyle.StandardPixmap.SP_TrashIcon,           self._delete_profile),
        ):
            btn = QPushButton(label)
            btn.setIcon(self.style().standardIcon(px))
            btn.setMinimumHeight(30)
            btn.clicked.connect(slot)
            row.addWidget(btn)

        return w

    def _build_tabs(self) -> QTabWidget:
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        def _scroll_tab(label: str) -> QWidget:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            content = QWidget()
            scroll.setWidget(content)
            self.tabs.addTab(scroll, label)
            return content

        self.tab_video    = _scroll_tab("Video & Display")
        self.tab_audio    = _scroll_tab("Audio")
        self.tab_control  = _scroll_tab("Control & Behavior")
        self.tab_record   = _scroll_tab("Recording")
        self.tab_advanced = _scroll_tab("Advanced Options")

        self._init_video_tab()
        self._init_audio_tab()
        self._init_control_tab()
        self._init_record_tab()
        self._init_advanced_tab()

        return self.tabs

    def _build_action_bar(self) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 12)
        row.setSpacing(10)

        af = QFont()
        af.setPointSize(11)
        af.setBold(True)

        self.btn_start = QPushButton(" Launch scrcpy")
        self.btn_start.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setFont(af)
        self.btn_start.setEnabled(False)   # enabled once devices are found
        self.btn_start.clicked.connect(self.launch_requested)

        self.btn_stop = QPushButton(" Stop")
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setFont(af)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_requested)

        row.addWidget(self.btn_start, 3)
        row.addWidget(self.btn_stop,  1)
        return w

    # ── Tab content ────────────────────────────────────────────────────────────

    def _init_video_tab(self):
        layout = QFormLayout(self.tab_video)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_video_source = QComboBox()
        self.opt_video_source.addItems(["display (Default)", "camera"])

        self.opt_display_id = QSpinBox()
        self.opt_display_id.setRange(0, 10)
        self.opt_display_id.setSpecialValueText("0 (Default)")

        self.opt_camera_facing = QComboBox()
        self.opt_camera_facing.addItems(["any", "front", "back", "external"])

        self.opt_new_display = QCheckBox("New Display (--new-display) (Android 10+)")
        self.opt_new_display_res = QLineEdit()
        self.opt_new_display_res.setPlaceholderText("Optional: e.g. 1920x1080/420")

        self.opt_bitrate = QComboBox()
        self.opt_bitrate.addItems(["Default (8M)", "2M", "4M", "16M", "24M", "32M"])
        self.opt_bitrate.setEditable(True)

        self.opt_max_fps = QSpinBox()
        self.opt_max_fps.setRange(0, 144)
        self.opt_max_fps.setSpecialValueText("0 (Unlimited / Default)")

        self.opt_max_size = QSpinBox()
        self.opt_max_size.setRange(0, 4000)
        self.opt_max_size.setSpecialValueText("0 (Unlimited)")

        self.opt_codec = QComboBox()
        self.opt_codec.addItems(["h264 (Default)", "h265", "av1"])

        self.opt_fullscreen      = QCheckBox("Start in Fullscreen (-f)")
        self.opt_always_on_top   = QCheckBox("Always On Top (--always-on-top)")
        self.opt_borderless      = QCheckBox("Borderless Window (--window-borderless)")
        self.opt_no_window       = QCheckBox("Disable Window (--no-window)")
        self.opt_no_video        = QCheckBox("Disable Video (--no-video)")

        layout.addRow("Video Source:",        self.opt_video_source)
        layout.addRow("Display ID:",          self.opt_display_id)
        layout.addRow("Camera Facing:",       self.opt_camera_facing)
        layout.addRow("New Display:",         self.opt_new_display)
        layout.addRow("New Display Res:",     self.opt_new_display_res)
        layout.addRow("Video Bitrate (-b):",  self.opt_bitrate)
        layout.addRow("Max FPS:",             self.opt_max_fps)
        layout.addRow("Max Size (-m):",       self.opt_max_size)
        layout.addRow("Video Codec:",         self.opt_codec)
        layout.addRow("", self.opt_fullscreen)
        layout.addRow("", self.opt_always_on_top)
        layout.addRow("", self.opt_borderless)
        layout.addRow("", self.opt_no_window)
        layout.addRow("", self.opt_no_video)

    def _init_audio_tab(self):
        layout = QFormLayout(self.tab_audio)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_no_audio = QCheckBox("Disable Audio (--no-audio)")

        self.opt_audio_source = QComboBox()
        self.opt_audio_source.addItems([
            "output (Default)", "playback", "mic",
            "mic-camcorder", "mic-voice-communication", "voice-call",
        ])

        self.opt_audio_codec = QComboBox()
        self.opt_audio_codec.addItems(["opus (Default)", "aac", "flac", "raw"])

        self.opt_no_audio_playback = QCheckBox("Disable Audio Playback (--no-audio-playback)")

        layout.addRow("",               self.opt_no_audio)
        layout.addRow("Audio Source:",  self.opt_audio_source)
        layout.addRow("Audio Codec:",   self.opt_audio_codec)
        layout.addRow("",               self.opt_no_audio_playback)

    def _init_control_tab(self):
        layout = QFormLayout(self.tab_control)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_read_only           = QCheckBox("Read-only (disable control) (-n)")
        self.opt_keyboard_mode       = QComboBox()
        self.opt_keyboard_mode.addItems(["sdk (Default)", "uhid", "aoa", "disabled"])
        self.opt_mouse_mode          = QComboBox()
        self.opt_mouse_mode.addItems(["sdk (Default)", "uhid", "aoa", "disabled"])
        self.opt_otg                 = QCheckBox("OTG Mode (physical KB/mouse via USB) (--otg)")
        self.opt_stay_awake          = QCheckBox("Stay Awake (keep screen on) (-w)")
        self.opt_turn_screen_off     = QCheckBox("Turn Screen Off (-S)")
        self.opt_show_touches        = QCheckBox("Show Touches (-t)")
        self.opt_disable_screensaver = QCheckBox("Disable Screensaver (--disable-screensaver)")
        self.opt_power_off_close     = QCheckBox("Power Off On Close (--power-off-on-close)")

        layout.addRow("Interaction:",   self.opt_read_only)
        layout.addRow("Keyboard:",      self.opt_keyboard_mode)
        layout.addRow("Mouse:",         self.opt_mouse_mode)
        layout.addRow("",               self.opt_otg)
        layout.addRow("Display:",       self.opt_stay_awake)
        layout.addRow("",               self.opt_turn_screen_off)
        layout.addRow("",               self.opt_show_touches)
        layout.addRow("",               self.opt_disable_screensaver)
        layout.addRow("Exit:",          self.opt_power_off_close)

    def _init_record_tab(self):
        layout = QFormLayout(self.tab_record)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_record_file = QLineEdit()
        self.opt_record_file.setPlaceholderText("e.g. /home/user/Videos/capture.mp4")
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_record_file)
        rec_row = QHBoxLayout()
        rec_row.setContentsMargins(0, 0, 0, 0)
        rec_row.addWidget(self.opt_record_file)
        rec_row.addWidget(btn_browse)

        self.opt_record_format = QComboBox()
        self.opt_record_format.addItems([
            "Auto (from extension)", "mp4", "mkv",
            "m4a", "mka", "opus", "aac", "flac", "wav",
        ])

        self.opt_record_orientation = QComboBox()
        self.opt_record_orientation.addItems(["0 (Default)", "90", "180", "270"])

        self.opt_no_playback = QCheckBox(
            "Record in background (disable video/audio playback) (-N)"
        )

        layout.addRow("Record File (-r):",   rec_row)
        layout.addRow("Record Format:",      self.opt_record_format)
        layout.addRow("Record Orientation:", self.opt_record_orientation)
        layout.addRow("",                    self.opt_no_playback)

    def _init_advanced_tab(self):
        layout = QFormLayout(self.tab_advanced)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.opt_v4l2_sink = QLineEdit()
        self.opt_v4l2_sink.setPlaceholderText("e.g. /dev/video0 (Linux only)")

        self.opt_v4l2_buffer = QSpinBox()
        self.opt_v4l2_buffer.setRange(0, 5000)
        self.opt_v4l2_buffer.setSpecialValueText("0 (no buffering)")

        self.opt_start_app = QLineEdit()
        self.opt_start_app.setPlaceholderText("Package name e.g. org.mozilla.firefox")

        self.opt_custom_args = QLineEdit()
        self.opt_custom_args.setPlaceholderText("e.g. --legacy-paste --shortcut-mod=lalt")

        layout.addRow("V4L2 Sink (webcam mode):", self.opt_v4l2_sink)
        layout.addRow("V4L2 Buffer (ms):",        self.opt_v4l2_buffer)
        layout.addRow("Start App:",               self.opt_start_app)
        layout.addRow("Custom Arguments:",        self.opt_custom_args)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_profile_combo_changed(self, name: str):
        """User selected a profile from the combo — apply it immediately."""
        self.apply_profile(name)

    @pyqtSlot()
    def _browse_record_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Recording File", "",
            "Video Files (*.mp4 *.mkv);;"
            "Audio Files (*.m4a *.mka *.opus *.aac *.flac *.wav);;"
            "All Files (*)",
        )
        if path:
            self.opt_record_file.setText(path)

    def _save_profile(self):
        name, ok = QInputDialog.getText(
            self, "Save Profile", "Profile name:",
            text=self.profile_combo.currentText(),
        )
        if not (ok and name.strip()):
            return
        name = name.strip()
        self._profiles[name] = self.get_ui_state()
        save_profiles(self._profiles)
        self._active_profile = name
        # Update combo without re-triggering apply
        self.profile_combo.blockSignals(True)
        if self.profile_combo.findText(name) == -1:
            self.profile_combo.addItem(name)
        self.profile_combo.setCurrentText(name)
        self.profile_combo.blockSignals(False)
        self.profile_saved.emit(name)

    def _new_profile(self):
        base, i = "Quick Profile", 1
        candidate = base
        while candidate in self._profiles:
            i += 1
            candidate = f"{base} {i}"
        name, ok = QInputDialog.getText(
            self, "New Profile", "Profile name:", text=candidate
        )
        if not (ok and name.strip()):
            return
        name = name.strip()
        if name in self._profiles:
            QMessageBox.warning(self, "New Profile", "A profile with that name already exists.")
            return
        self._profiles[name] = self.get_ui_state()
        save_profiles(self._profiles)
        self._active_profile = name
        self.profile_combo.blockSignals(True)
        self.profile_combo.addItem(name)
        self.profile_combo.setCurrentText(name)
        self.profile_combo.blockSignals(False)
        self.profile_saved.emit(name)

    def _delete_profile(self):
        name = self.profile_combo.currentText()
        _protected = {
            "Default", "Desktop (New Display)", "Wireless (Low Bandwidth)",
            "Gaming (Low Latency / UHID)", "Audio Only", "Webcam (Linux V4L2)",
        }
        if name in _protected:
            QMessageBox.warning(self, "Delete Profile", "Cannot delete built-in profiles.")
            return
        reply = QMessageBox.question(
            self, "Delete Profile", f"Delete profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._profiles.pop(name, None)
        save_profiles(self._profiles)
        self.profile_combo.blockSignals(True)
        idx = self.profile_combo.findText(name)
        if idx != -1:
            self.profile_combo.removeItem(idx)
        self.profile_combo.blockSignals(False)
        if self._active_profile == name:
            self._active_profile = self.profile_combo.currentText() or None
        self.profile_deleted.emit(name)

    # ── State serialisation ────────────────────────────────────────────────────

    def get_ui_state(self) -> dict:
        """Return a dict that fully describes the current UI option state."""
        return {
            # Video
            "video_source":       self.opt_video_source.currentIndex(),
            "display_id":         self.opt_display_id.value(),
            "camera_facing":      self.opt_camera_facing.currentIndex(),
            "new_display":        self.opt_new_display.isChecked(),
            "new_display_res":    self.opt_new_display_res.text(),
            "bitrate":            self.opt_bitrate.currentText(),
            "max_fps":            self.opt_max_fps.value(),
            "max_size":           self.opt_max_size.value(),
            "codec":              self.opt_codec.currentIndex(),
            "fullscreen":         self.opt_fullscreen.isChecked(),
            "always_on_top":      self.opt_always_on_top.isChecked(),
            "borderless":         self.opt_borderless.isChecked(),
            "no_window":          self.opt_no_window.isChecked(),
            "no_video":           self.opt_no_video.isChecked(),
            # Audio
            "no_audio":           self.opt_no_audio.isChecked(),
            "audio_source":       self.opt_audio_source.currentIndex(),
            "audio_codec":        self.opt_audio_codec.currentIndex(),
            "no_audio_playback":  self.opt_no_audio_playback.isChecked(),
            # Control
            "read_only":          self.opt_read_only.isChecked(),
            "keyboard_mode":      self.opt_keyboard_mode.currentIndex(),
            "mouse_mode":         self.opt_mouse_mode.currentIndex(),
            "otg":                self.opt_otg.isChecked(),
            "stay_awake":         self.opt_stay_awake.isChecked(),
            "turn_screen_off":    self.opt_turn_screen_off.isChecked(),
            "show_touches":       self.opt_show_touches.isChecked(),
            "disable_screensaver": self.opt_disable_screensaver.isChecked(),
            "power_off_close":    self.opt_power_off_close.isChecked(),
            # Recording (format/orientation saved; file path is session-specific)
            "record_format":      self.opt_record_format.currentIndex(),
            "record_orientation": self.opt_record_orientation.currentIndex(),
            "no_playback":        self.opt_no_playback.isChecked(),
            # Advanced
            "v4l2_sink":          self.opt_v4l2_sink.text(),
            "v4l2_buffer":        self.opt_v4l2_buffer.value(),
            "start_app":          self.opt_start_app.text(),
            "custom_args":        self.opt_custom_args.text(),
        }

    def set_ui_state(self, state: dict):
        """Apply a state dict to the UI controls (missing keys use defaults)."""
        g = state.get

        # Video
        self.opt_video_source.setCurrentIndex(g("video_source", 0))
        self.opt_display_id.setValue(g("display_id", 0))
        self.opt_camera_facing.setCurrentIndex(g("camera_facing", 0))
        self.opt_new_display.setChecked(g("new_display", False))
        self.opt_new_display_res.setText(g("new_display_res", ""))
        self.opt_bitrate.setCurrentText(g("bitrate", "Default (8M)"))
        self.opt_max_fps.setValue(g("max_fps", 0))
        self.opt_max_size.setValue(g("max_size", 0))
        self.opt_codec.setCurrentIndex(g("codec", 0))
        self.opt_fullscreen.setChecked(g("fullscreen", False))
        self.opt_always_on_top.setChecked(g("always_on_top", False))
        self.opt_borderless.setChecked(g("borderless", False))
        self.opt_no_window.setChecked(g("no_window", False))
        self.opt_no_video.setChecked(g("no_video", False))
        # V4L2 sink: honour explicit "use default device" flag from built-in profiles
        v4l2_sink = g("v4l2_sink", "")
        if not v4l2_sink and g("v4l2_sink_default", False):
            v4l2_sink = "/dev/video0"
        self.opt_v4l2_sink.setText(v4l2_sink)

        # Audio
        self.opt_no_audio.setChecked(g("no_audio", False))
        self.opt_audio_source.setCurrentIndex(g("audio_source", 0))
        self.opt_audio_codec.setCurrentIndex(g("audio_codec", 0))
        self.opt_no_audio_playback.setChecked(g("no_audio_playback", False))

        # Control
        self.opt_read_only.setChecked(g("read_only", False))
        self.opt_keyboard_mode.setCurrentIndex(g("keyboard_mode", 0))
        self.opt_mouse_mode.setCurrentIndex(g("mouse_mode", 0))
        self.opt_otg.setChecked(g("otg", False))
        self.opt_stay_awake.setChecked(g("stay_awake", False))
        self.opt_turn_screen_off.setChecked(g("turn_screen_off", False))
        self.opt_show_touches.setChecked(g("show_touches", False))
        self.opt_disable_screensaver.setChecked(g("disable_screensaver", False))
        self.opt_power_off_close.setChecked(g("power_off_close", False))

        # Recording
        self.opt_record_format.setCurrentIndex(g("record_format", 0))
        self.opt_record_orientation.setCurrentIndex(g("record_orientation", 0))
        self.opt_no_playback.setChecked(g("no_playback", False))

        # Advanced
        self.opt_v4l2_buffer.setValue(g("v4l2_buffer", 0))
        self.opt_start_app.setText(g("start_app", ""))
        self.opt_custom_args.setText(g("custom_args", ""))

    # ── Args builder ───────────────────────────────────────────────────────────

    def build_scrcpy_args(self, serial: str | None = None) -> list[str]:
        """Build the full scrcpy command-line argument list."""
        args = ["scrcpy"]

        if serial:
            args += ["-s", serial]

        # ── Video ──────────────────────────────────────────────────────────────
        bitrate = self.opt_bitrate.currentText()
        if not bitrate.startswith("Default"):
            args += ["-b", bitrate]

        if self.opt_max_fps.value() > 0:
            args += ["--max-fps", str(self.opt_max_fps.value())]

        if self.opt_max_size.value() > 0:
            args += ["-m", str(self.opt_max_size.value())]

        codec = self.opt_codec.currentText().split()[0]
        if codec != "h264":
            args += ["--video-codec", codec]

        if self.opt_fullscreen.isChecked():       args.append("-f")
        if self.opt_always_on_top.isChecked():    args.append("--always-on-top")
        if self.opt_borderless.isChecked():       args.append("--window-borderless")
        if self.opt_no_window.isChecked():        args.append("--no-window")
        if self.opt_no_video.isChecked():         args.append("--no-video")

        if self.opt_new_display.isChecked():
            res = self.opt_new_display_res.text().strip()
            args.append(f"--new-display={res}" if res else "--new-display")

        video_src = self.opt_video_source.currentText().split()[0]
        if video_src != "display":
            args += ["--video-source", video_src]
            facing = self.opt_camera_facing.currentText()
            if facing != "any":
                args += ["--camera-facing", facing]
        else:
            did = self.opt_display_id.value()
            if did > 0:
                args += ["--display-id", str(did)]

        # ── Recording ──────────────────────────────────────────────────────────
        record_file = self.opt_record_file.text().strip()
        if record_file:
            args += ["-r", record_file]
            fmt = self.opt_record_format.currentText().split()[0]
            if fmt != "Auto":
                args += ["--record-format", fmt]
            orient = self.opt_record_orientation.currentText().split()[0]
            if orient != "0":
                args += ["--record-orientation", orient]
            if self.opt_no_playback.isChecked():
                args.append("-N")

        # ── Audio ──────────────────────────────────────────────────────────────
        if self.opt_no_audio.isChecked():
            args.append("--no-audio")
        else:
            a_src = self.opt_audio_source.currentText().split()[0]
            if a_src != "output":
                args += ["--audio-source", a_src]
            a_codec = self.opt_audio_codec.currentText().split()[0]
            if a_codec != "opus":
                args += ["--audio-codec", a_codec]
            if self.opt_no_audio_playback.isChecked():
                args.append("--no-audio-playback")

        # ── Control ────────────────────────────────────────────────────────────
        if self.opt_read_only.isChecked():         args.append("-n")
        if self.opt_stay_awake.isChecked():        args.append("-w")
        if self.opt_turn_screen_off.isChecked():   args.append("-S")
        if self.opt_show_touches.isChecked():      args.append("-t")
        if self.opt_power_off_close.isChecked():   args.append("--power-off-on-close")
        if self.opt_otg.isChecked():               args.append("--otg")
        if self.opt_disable_screensaver.isChecked(): args.append("--disable-screensaver")

        kb = self.opt_keyboard_mode.currentText().split()[0]
        if kb != "sdk":
            args += ["--keyboard", kb]
        mouse = self.opt_mouse_mode.currentText().split()[0]
        if mouse != "sdk":
            args += ["--mouse", mouse]

        # ── Advanced ───────────────────────────────────────────────────────────
        v4l2 = self.opt_v4l2_sink.text().strip()
        if v4l2:
            args += ["--v4l2-sink", v4l2]
            buf = self.opt_v4l2_buffer.value()
            if buf > 0:
                args += ["--v4l2-buffer", str(buf)]

        app = self.opt_start_app.text().strip()
        if app:
            args += ["--start-app", app]

        custom = self.opt_custom_args.text().strip()
        if custom:
            args += shlex.split(custom)

        return args
