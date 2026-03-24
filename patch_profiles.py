def add_profile_methods():
    with open('src/main_window.py', 'r') as f:
        content = f.read()

    methods = """
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
        if not name or name not in self.profiles: return
        self.set_ui_state(self.profiles[name])
        self.log(f"Applied profile '{name}'.")

    @pyqtSlot()
    def save_profile(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Enter profile name:", text=self.profile_combo.currentText())
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
        if name in ["Default", "Desktop (New Display)", "Wireless (Low Bandwidth)", "Gaming (Low Latency / UHID)"]:
            QMessageBox.warning(self, "Delete Profile", "Cannot delete default profiles.")
            return
            
        reply = QMessageBox.question(self, "Delete Profile", f"Are you sure you want to delete '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if name in self.profiles:
                del self.profiles[name]
                save_profiles(self.profiles)
                idx = self.profile_combo.findText(name)
                if idx != -1:
                    self.profile_combo.removeItem(idx)
                self.log(f"Deleted profile '{name}'.")
                
"""
    # Simply appending methods to the end of the file for simplicity, 
    # but maintaining matching indentation.
    with open('src/main_window.py', 'a') as f:
        f.write(methods)

add_profile_methods()
