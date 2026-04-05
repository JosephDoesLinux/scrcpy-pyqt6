import shlex

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog, QFormLayout, QComboBox, QSpinBox, QCheckBox, QLineEdit, QPushButton, QHBoxLayout


class ScrcpyOptionsMixin:
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

    def build_scrcpy_args(self) -> list:
        args = ["scrcpy"]

        serial = self.device_combo.currentData()
        if serial:
            args.extend(["-s", serial])

        bitrate = self.opt_bitrate.currentText()
        if not bitrate.startswith("Default"):
            args.extend(["-b", bitrate])

        if self.opt_max_fps.value() > 0:
            args.extend(["--max-fps", str(self.opt_max_fps.value())])

        if self.opt_max_size.value() > 0:
            args.extend(["-m", str(self.opt_max_size.value())])

        codec = self.opt_codec.currentText().split()[0]
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
            args.extend(shlex.split(custom))

        return args

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
        if state.get("v4l2_sink_default", False) and not self.opt_v4l2_sink.text().strip():
            self.opt_v4l2_sink.setText("/dev/video0")
