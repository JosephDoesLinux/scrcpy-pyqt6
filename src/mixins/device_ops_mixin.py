from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtCore import pyqtSlot

from adb import get_devices, get_mdns_services, connect_device, pair_device


class DeviceOpsMixin:
    @pyqtSlot()
    def refresh_devices(self):
        previous_serial = self.device_combo.currentData()
        self.device_combo.clear()
        self.log("Refreshing ADB device list...")
        devices = get_devices()

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

    @pyqtSlot()
    def scan_mdns(self):
        self.mdns_combo.clear()
        self.log("Scanning for mDNS devices on the local network...")
        services = get_mdns_services()
        if not services:
            self.mdns_combo.addItem("No network devices found (or mDNS unsupported).")
        else:
            self.mdns_combo.addItem("Select a device to pair/connect...", userData=None)
            for s in services:
                self.mdns_combo.addItem(
                    f"{s['name']} ({s['address']})", userData=s["address"]
                )
                addr = s.get("address")
                if addr:
                    self.discovered_addresses.add(addr)

            self.log(f"Found {len(services)} network device(s).")

            if getattr(self, "chk_auto_connect", None) and self.chk_auto_connect.isChecked():
                for s in services:
                    if "connect" in s.get("type", "").lower():
                        addr = s.get("address")
                        if addr:
                            self.log(f"Auto-connecting to {addr}...")
                            result = connect_device(addr)
                            self.log(result)
                            self.network_status.setText(
                                f"Last: {addr} -> {result.splitlines()[0] if result else ''}"
                            )
                            if (
                                "connected" in result.lower()
                                or "already connected" in result.lower()
                            ):
                                self.refresh_devices()

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
            self.network_status.setText(
                f"Pair result: {result.splitlines()[0] if result else ''}"
            )
            self.refresh_devices()

    @pyqtSlot()
    def connect_wireless(self):
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
        self.network_status.setText(
            f"Connect result: {result.splitlines()[0] if result else ''}"
        )
        self.refresh_devices()

    @pyqtSlot()
    def check_device_health(self):
        try:
            devices = get_devices()
            serials = {d["serial"] for d in devices}
            for addr in list(self.discovered_addresses):
                if addr not in serials:
                    if getattr(self, "chk_auto_connect", None) and self.chk_auto_connect.isChecked():
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
