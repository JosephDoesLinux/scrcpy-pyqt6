from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtCore import pyqtSlot, QProcess, QTimer, QThreadPool
import time

from adb import get_devices, get_mdns_services, connect_device, pair_device
from async_task import BackgroundTask


class DeviceOpsMixin:
    def _ensure_async_runtime(self):
        if not hasattr(self, "_thread_pool") or self._thread_pool is None:
            self._thread_pool = QThreadPool.globalInstance()
        if not hasattr(self, "_active_background_tasks"):
            self._active_background_tasks = set()

    def _run_background(self, work_fn, on_result=None, on_error=None, on_done=None):
        self._ensure_async_runtime()
        task = BackgroundTask(work_fn)
        self._active_background_tasks.add(task)

        if on_result:
            task.signals.result.connect(on_result)

        if on_error:
            task.signals.error.connect(on_error)

        def _cleanup():
            self._active_background_tasks.discard(task)
            if on_done:
                on_done()

        task.signals.finished.connect(_cleanup)
        self._thread_pool.start(task)

    def _get_selected_serial(self):
        try:
            if not hasattr(self, "device_combo") or self.device_combo is None:
                return None
            serial = self.device_combo.currentData()
            if not serial:
                return None
            return str(serial)
        except Exception:
            return None

    def _update_recovery_controls(self):
        if not hasattr(self, "btn_restart_systemui") or self.btn_restart_systemui is None:
            return

        has_serial = bool(self._get_selected_serial())
        is_running = bool(getattr(self, "_recovery_running", False))
        in_cooldown = bool(getattr(self, "_recovery_cooldown_active", False))
        enabled = has_serial and not is_running and not in_cooldown
        self.btn_restart_systemui.setEnabled(enabled)

        if is_running:
            self.btn_restart_systemui.setText(" Restarting SystemUI...")
        elif in_cooldown:
            self.btn_restart_systemui.setText(" Emergency Restart SystemUI (Cooldown)")
        else:
            self.btn_restart_systemui.setText(" Emergency Restart SystemUI")

    def _begin_recovery_cooldown(self, seconds: int = 10):
        duration = max(1, int(seconds or 1))
        self._recovery_cooldown_active = True
        self._recovery_cooldown_deadline = time.monotonic() + float(duration)
        self._update_recovery_controls()
        QTimer.singleShot(duration * 1000, self._end_recovery_cooldown)

    def _end_recovery_cooldown(self):
        deadline = float(getattr(self, "_recovery_cooldown_deadline", 0.0) or 0.0)
        if deadline and time.monotonic() < deadline:
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            QTimer.singleShot(max(50, remaining_ms), self._end_recovery_cooldown)
            return

        self._recovery_cooldown_active = False
        self._recovery_cooldown_deadline = 0.0
        self._update_recovery_controls()

    @pyqtSlot()
    def emergency_restart_systemui(self):
        serial = self._get_selected_serial()
        if not serial:
            self.log("Recovery action requires a selected connected device.", level=1)
            self._update_recovery_controls()
            return

        proc = getattr(self, "_systemui_recovery_process", None)
        if proc and proc.state() != QProcess.ProcessState.NotRunning:
            self.log("Recovery command is already running.", level=1)
            return

        reply = QMessageBox.warning(
            self,
            "Emergency Restart SystemUI",
            (
                "This will force-restart Android SystemUI on the selected device.\n\n"
                "Device: "
                f"{serial}\n\n"
                "Use this only when Android UI is frozen. Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self.log("Emergency SystemUI restart cancelled.")
            return

        typed, ok = QInputDialog.getText(
            self,
            "Confirm Emergency Action",
            f"Type RESTART to confirm for:\n{serial}",
        )
        if not ok or (typed or "").strip().upper() != "RESTART":
            self.log("Emergency SystemUI restart cancelled (confirmation mismatch).", level=1)
            return

        self._recovery_running = True
        self._recovery_target_serial = serial
        self._update_recovery_controls()

        cmd = "pkill -f com.android.systemui || killall com.android.systemui || am crash com.android.systemui"
        self.log(f"Recovery: restarting SystemUI on {serial}...")
        self.network_status.setText(f"Recovery: restarting SystemUI on {serial}...")

        proc = QProcess(self)
        self._systemui_recovery_process = proc
        proc.readyReadStandardOutput.connect(self._on_recovery_stdout)
        proc.readyReadStandardError.connect(self._on_recovery_stderr)
        proc.finished.connect(self._on_recovery_finished)
        proc.errorOccurred.connect(self._on_recovery_error)
        proc.start("adb", ["-s", serial, "shell", "sh", "-c", cmd])

    def _on_recovery_stdout(self):
        proc = getattr(self, "_systemui_recovery_process", None)
        if not proc:
            return

        output = proc.readAllStandardOutput().data().decode("utf8", "replace")
        for line in output.splitlines():
            line = line.strip()
            if line:
                self.log(f"Recovery stdout: {line}")

    def _on_recovery_stderr(self):
        proc = getattr(self, "_systemui_recovery_process", None)
        if not proc:
            return

        output = proc.readAllStandardError().data().decode("utf8", "replace")
        for line in output.splitlines():
            line = line.strip()
            if line:
                self.log(f"Recovery stderr: {line}", level=1)

    def _on_recovery_finished(self, exit_code, _exit_status):
        serial = getattr(self, "_recovery_target_serial", "selected device")
        self._recovery_running = False

        if int(exit_code) == 0:
            self.log(f"Recovery: SystemUI restart command completed for {serial}.")
            self.network_status.setText(f"Recovery: command sent to {serial}.")
        else:
            self.log(
                f"Recovery: SystemUI restart command exited with code {exit_code} for {serial}.",
                level=1,
            )
            self.network_status.setText(
                f"Recovery: command failed for {serial} (exit {exit_code})."
            )

        self._begin_recovery_cooldown(10)

    def _on_recovery_error(self, error):
        self._recovery_running = False
        self.log(f"Recovery command error: {error}", level=2)
        self.network_status.setText("Recovery: command failed to start.")
        self._update_recovery_controls()

    def _apply_devices_to_combo(self, devices, previous_serial):
        self.device_combo.clear()

        has_devices = bool(devices)
        if hasattr(self, "settings_tabs") and self.settings_tabs:
            try:
                self.settings_tabs.set_has_devices(has_devices)
            except Exception:
                pass

        if not devices:
            self.device_combo.addItem("No devices found")
            self.device_combo.setEnabled(False)
        else:
            self.device_combo.setEnabled(True)
            for d in devices:
                self.device_combo.addItem(
                    f"{d['serial']} [{d['state']}] - {d['model']}", userData=d["serial"]
                )

            if previous_serial:
                for i in range(self.device_combo.count()):
                    if self.device_combo.itemData(i) == previous_serial:
                        self.device_combo.setCurrentIndex(i)
                        break

            self.log(f"Found {len(devices)} device(s).")

        try:
            if hasattr(self, "tray_manager") and self.tray_manager:
                self.tray_manager.rebuild_devices_menu()
        except Exception:
            pass

        try:
            self._update_recovery_controls()
        except Exception:
            pass

    @pyqtSlot()
    def refresh_devices(self):
        if getattr(self, "_refresh_in_progress", False):
            return

        previous_serial = self.device_combo.currentData()
        self._refresh_in_progress = True
        try:
            if hasattr(self, "btn_refresh") and self.btn_refresh:
                self.btn_refresh.setEnabled(False)
        except Exception:
            pass

        self.log("Refreshing ADB device list...")

        def _work():
            return get_devices()

        def _on_result(devices):
            self._apply_devices_to_combo(devices, previous_serial)

        def _on_error(msg):
            self.log(f"Device refresh failed: {msg}", level=2)
            self._apply_devices_to_combo([], previous_serial)

        def _on_done():
            self._refresh_in_progress = False
            try:
                if hasattr(self, "btn_refresh") and self.btn_refresh:
                    self.btn_refresh.setEnabled(True)
            except Exception:
                pass

        self._run_background(_work, _on_result, _on_error, _on_done)

    def _start_auto_connect_for_services(self, services):
        addresses = [
            s.get("address")
            for s in services
            if "connect" in s.get("type", "").lower() and s.get("address")
        ]
        if not addresses:
            return

        if getattr(self, "_auto_connect_in_progress", False):
            return

        self._auto_connect_in_progress = True
        self.network_status.setText("Auto-connect in progress...")

        for addr in addresses:
            self.log(f"Auto-connecting to {addr}...")

        def _work():
            results = []
            for addr in addresses:
                result = connect_device(addr)
                is_connected = (
                    "connected" in result.lower()
                    or "already connected" in result.lower()
                )
                results.append(
                    {
                        "address": addr,
                        "result": result,
                        "connected": is_connected,
                    }
                )
            return results

        def _on_result(results):
            any_connected = False
            last_line = ""
            for item in results:
                addr = item.get("address")
                result = item.get("result") or ""
                is_connected = bool(item.get("connected"))
                self.log(result)
                first_line = result.splitlines()[0] if result else ""
                last_line = f"Last: {addr} -> {first_line}"
                if is_connected:
                    any_connected = True

            if last_line:
                self.network_status.setText(last_line)

            if any_connected:
                self.refresh_devices()

        def _on_error(msg):
            self.log(f"Auto-connect failed: {msg}", level=2)

        def _on_done():
            self._auto_connect_in_progress = False

        self._run_background(_work, _on_result, _on_error, _on_done)

    @pyqtSlot()
    def scan_mdns(self):
        if getattr(self, "_scan_in_progress", False):
            return

        self._scan_in_progress = True
        try:
            if hasattr(self, "btn_scan") and self.btn_scan:
                self.btn_scan.setEnabled(False)
        except Exception:
            pass

        self.mdns_combo.clear()
        self.mdns_combo.addItem("Scanning for network devices...")
        self.log("Scanning for mDNS devices on the local network...")

        def _work():
            return get_mdns_services()

        def _on_result(services):
            self.mdns_combo.clear()
            if not services:
                self.mdns_combo.addItem("No network devices found (or mDNS unsupported).")
                return

            self.mdns_combo.addItem("Select a device to pair/connect...", userData=None)
            for s in services:
                self.mdns_combo.addItem(
                    f"{s['name']} ({s['address']})", userData=s["address"]
                )
                addr = s.get("address")
                # Health-check reconnects should only target connect-capable services.
                if addr and "connect" in s.get("type", "").lower():
                    self.discovered_addresses.add(addr)

            self.log(f"Found {len(services)} network device(s).")

            if getattr(self, "chk_auto_connect", None) and self.chk_auto_connect.isChecked():
                self._start_auto_connect_for_services(services)

        def _on_error(msg):
            self.mdns_combo.clear()
            self.mdns_combo.addItem("mDNS scan failed.")
            self.log(f"mDNS scan failed: {msg}", level=2)

        def _on_done():
            self._scan_in_progress = False
            try:
                if hasattr(self, "btn_scan") and self.btn_scan:
                    self.btn_scan.setEnabled(True)
            except Exception:
                pass

        self._run_background(_work, _on_result, _on_error, _on_done)

    @pyqtSlot()
    def pair_wireless(self):
        if getattr(self, "_pair_in_progress", False):
            return

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
            self._pair_in_progress = True
            try:
                if hasattr(self, "btn_pair") and self.btn_pair:
                    self.btn_pair.setEnabled(False)
            except Exception:
                pass

            self.log(f"Attempting adb pair with {address}...")

            def _work():
                return pair_device(address, code)

            def _on_result(result):
                self.log(result)
                self.network_status.setText(
                    f"Pair result: {result.splitlines()[0] if result else ''}"
                )
                self.refresh_devices()

            def _on_error(msg):
                self.log(f"Pair failed for {address}: {msg}", level=2)

            def _on_done():
                self._pair_in_progress = False
                try:
                    if hasattr(self, "btn_pair") and self.btn_pair:
                        self.btn_pair.setEnabled(True)
                except Exception:
                    pass

            self._run_background(_work, _on_result, _on_error, _on_done)

    @pyqtSlot()
    def connect_wireless(self):
        if getattr(self, "_connect_in_progress", False):
            return

        address = self.mdns_combo.currentData()
        if not address:
            address = self.ip_input.text().strip()

        if not address:
            self.log(
                "Error: Select a network device or enter an IP address manually to connect."
            )
            return

        self._connect_in_progress = True
        try:
            if hasattr(self, "btn_connect") and self.btn_connect:
                self.btn_connect.setEnabled(False)
        except Exception:
            pass

        self.log(f"Attempting adb connect {address}...")

        def _work():
            return connect_device(address)

        def _on_result(result):
            self.log(result)
            self.network_status.setText(
                f"Connect result: {result.splitlines()[0] if result else ''}"
            )
            self.refresh_devices()

        def _on_error(msg):
            self.log(f"Connect failed for {address}: {msg}", level=2)

        def _on_done():
            self._connect_in_progress = False
            try:
                if hasattr(self, "btn_connect") and self.btn_connect:
                    self.btn_connect.setEnabled(True)
            except Exception:
                pass

        self._run_background(_work, _on_result, _on_error, _on_done)

    @pyqtSlot()
    def check_device_health(self):
        if not (
            getattr(self, "chk_auto_connect", None)
            and self.chk_auto_connect.isChecked()
        ):
            return

        if getattr(self, "_health_check_in_progress", False):
            return

        addresses = list(getattr(self, "discovered_addresses", set()))
        if not addresses:
            return

        self._health_check_in_progress = True

        def _work():
            devices = get_devices()
            serials = {d["serial"] for d in devices}
            reconnect_results = []
            for addr in addresses:
                if addr not in serials:
                    res = connect_device(addr)
                    reconnect_results.append(
                        {
                            "address": addr,
                            "result": res,
                            "connected": (
                                "connected" in res.lower()
                                or "already connected" in res.lower()
                            ),
                        }
                    )
            return reconnect_results

        def _on_result(reconnect_results):
            now = time.monotonic()
            if not hasattr(self, "_health_fail_log_ts"):
                self._health_fail_log_ts = {}

            any_connected = False
            for item in reconnect_results:
                addr = item.get("address")
                res = item.get("result") or ""
                first_line = res.splitlines()[0] if res else ""
                is_connected = bool(item.get("connected"))

                if is_connected:
                    any_connected = True
                    self.log(f"Health-check: reconnected to {addr}.")
                    self.network_status.setText(f"Health: {addr} -> {first_line}")
                    self._health_fail_log_ts.pop(addr, None)
                else:
                    # Keep health-check failures quiet to avoid log spam.
                    self._health_fail_log_ts[addr] = now

            if any_connected:
                self.refresh_devices()

        def _on_error(msg):
            self.log(f"Health-check error: {msg}", level=1)

        def _on_done():
            self._health_check_in_progress = False

        self._run_background(_work, _on_result, _on_error, _on_done)
