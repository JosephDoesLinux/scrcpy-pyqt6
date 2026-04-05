from PyQt6.QtWidgets import QMessageBox, QInputDialog
from PyQt6.QtCore import pyqtSlot

from profiles import save_profiles, load_settings, save_settings


class ProfileMixin:
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
        try:
            if hasattr(self, "tray_manager") and self.tray_manager:
                self.tray_manager.rebuild_profiles_menu()
        except Exception:
            pass

    def _on_profile_combo_changed(self, text: str):
        if not text or self._applying_profile:
            return
        self.apply_profile(text)

    @pyqtSlot(str)
    def apply_profile(self, name):
        if not name or name not in self.profiles:
            return

        self._applying_profile = True
        try:
            self.set_ui_state(self.profiles[name])
            self.active_profile = name

            idx = self.profile_combo.findText(name)
            if idx != -1 and idx != self.profile_combo.currentIndex():
                self.profile_combo.setCurrentIndex(idx)

            settings = load_settings()
            settings["last_profile"] = name
            save_settings(settings)
        except Exception as e:
            self.log(f"Error applying profile: {e}", level=2)
        finally:
            self._applying_profile = False

        self.log(f"Applied profile '{name}'.")
        try:
            if hasattr(self, "tray_manager") and self.tray_manager:
                self.tray_manager.rebuild_profiles_menu()
        except Exception:
            pass

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
                try:
                    if hasattr(self, "tray_manager") and self.tray_manager:
                        self.tray_manager.rebuild_profiles_menu()
                except Exception:
                    pass

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
