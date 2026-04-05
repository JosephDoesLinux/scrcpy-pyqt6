"""
device_panel.py — Device Connection panel widget.

A self-contained QGroupBox that owns all device-connection UI:
USB/local, mDNS scan, manual IP.  Business logic lives in the
main window; this widget talks back via Qt signals.
"""
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox, QStyle,
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import pyqtSignal


def _themed_icon(name: str, fallback: QStyle.StandardPixmap, widget) -> QIcon:
    icon = QIcon.fromTheme(name)
    return icon if not icon.isNull() else widget.style().standardIcon(fallback)


class DevicePanel(QGroupBox):
    """
    Device-connection panel (USB / mDNS / manual IP).

    Signals
    -------
    refresh_requested     – user pressed Refresh
    scan_requested        – user pressed Scan (mDNS)
    pair_requested        – user pressed Pair
    connect_requested     – user pressed Connect (manual)
    auto_connect_toggled  – auto-connect checkbox changed (bool)
    """

    refresh_requested    = pyqtSignal()
    scan_requested       = pyqtSignal()
    pair_requested       = pyqtSignal()
    connect_requested    = pyqtSignal()
    auto_connect_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("Device Connection", parent)
        bold = self.font()
        bold.setBold(True)
        self.setFont(bold)
        self._init_ui()

    # ── construction ───────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── USB / Local ───────────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>USB / Local Devices</b>"))

        usb_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(30)
        self.device_combo.setToolTip("Select a connected device (USB or paired network device)")

        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setIcon(
            _themed_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload, self)
        )
        self.btn_refresh.setMinimumHeight(30)
        self.btn_refresh.setToolTip("Refresh ADB device list")
        self.btn_refresh.clicked.connect(self.refresh_requested)

        usb_row.addWidget(self.device_combo, 1)
        usb_row.addWidget(self.btn_refresh)
        layout.addLayout(usb_row)

        # ── mDNS / Network ────────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Network Devices (mDNS)</b>"))

        mdns_row = QHBoxLayout()
        self.mdns_combo = QComboBox()
        self.mdns_combo.setMinimumHeight(30)
        self.mdns_combo.setToolTip("Devices discovered on your LAN via avahi/zeroconf")
        self.mdns_combo.addItem("Scan for network devices...")

        self.btn_scan = QPushButton(" Scan")
        self.btn_scan.setIcon(
            _themed_icon("network-wireless", QStyle.StandardPixmap.SP_DirHomeIcon, self)
        )
        self.btn_scan.setMinimumHeight(30)
        self.btn_scan.setToolTip("Scan for ADB-over-network devices via mDNS")
        self.btn_scan.clicked.connect(self.scan_requested)

        self.btn_pair = QPushButton(" Pair")
        self.btn_pair.setIcon(
            _themed_icon("network-connect", QStyle.StandardPixmap.SP_DialogApplyButton, self)
        )
        self.btn_pair.setMinimumHeight(30)
        self.btn_pair.setToolTip("Pair with selected device (first-time wireless setup)")
        self.btn_pair.clicked.connect(self.pair_requested)

        self.chk_auto_connect = QCheckBox("Auto-connect")
        self.chk_auto_connect.setToolTip(
            "Automatically adb-connect newly discovered network devices"
        )
        self.chk_auto_connect.stateChanged.connect(
            lambda _: self.auto_connect_toggled.emit(self.chk_auto_connect.isChecked())
        )

        mdns_row.addWidget(self.mdns_combo, 1)
        mdns_row.addWidget(self.btn_scan)
        mdns_row.addWidget(self.btn_pair)
        mdns_row.addWidget(self.chk_auto_connect)
        layout.addLayout(mdns_row)

        # ── Manual IP ─────────────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Manual Connect</b>"))

        manual_row = QHBoxLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("IP:Port  e.g. 192.168.1.5:5555")
        self.ip_input.setMinimumHeight(30)
        self.ip_input.setToolTip("Enter IP:Port for direct ADB connect")

        self.btn_connect = QPushButton(" Connect")
        self.btn_connect.setIcon(
            _themed_icon("network-server", QStyle.StandardPixmap.SP_DriveNetIcon, self)
        )
        self.btn_connect.setMinimumHeight(30)
        self.btn_connect.setToolTip("Connect to the device at the specified IP:Port")
        self.btn_connect.clicked.connect(self.connect_requested)

        manual_row.addWidget(self.ip_input, 1)
        manual_row.addWidget(self.btn_connect)
        layout.addLayout(manual_row)

        # ── Status line ───────────────────────────────────────────────────────
        self.network_status = QLabel("")
        layout.addWidget(self.network_status)

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def selected_serial(self) -> str | None:
        """Currently selected device serial (userData), or None."""
        return self.device_combo.currentData()

    @property
    def mdns_address(self) -> str | None:
        """Currently selected mDNS address, or None if placeholder is selected."""
        return self.mdns_combo.currentData()

    @property
    def manual_address(self) -> str:
        return self.ip_input.text().strip()

    def set_status(self, text: str):
        self.network_status.setText(text)

    def populate_devices(self, devices: list[dict]):
        """Rebuild device_combo from a list of adb device dicts."""
        self.device_combo.clear()
        if not devices:
            self.device_combo.addItem("No devices found")
            self.device_combo.setEnabled(False)
            return
        self.device_combo.setEnabled(True)
        for d in devices:
            label = f"{d['serial']} [{d['state']}] — {d['model']}"
            self.device_combo.addItem(label, userData=d["serial"])

    def populate_mdns(self, services: list[dict]):
        """Rebuild mdns_combo from a list of discovered mDNS service dicts."""
        self.mdns_combo.clear()
        if not services:
            self.mdns_combo.addItem("No network devices found (or mDNS unsupported).")
            return
        self.mdns_combo.addItem("Select a device to pair/connect...", userData=None)
        for s in services:
            self.mdns_combo.addItem(
                f"{s['name']} ({s['address']})", userData=s["address"]
            )
