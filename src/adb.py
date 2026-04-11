import subprocess
import re
from typing import List, Dict, Optional


ADB_TIMEOUT_SECONDS = 8
AVAHI_TIMEOUT_SECONDS = 6


def get_devices() -> List[Dict[str, str]]:
    """
    Returns a list of connected ADB devices.
    Each device is a dict with 'serial', 'state', and optional 'model'.
    """
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            check=False,
            timeout=ADB_TIMEOUT_SECONDS,
        )
    except Exception as e:
        print(f"Error running adb: {e}")
        return []

    devices = []
    lines = result.stdout.strip().split("\n")
    for line in lines[1:]:  # Skip the first line 'List of devices attached'
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            serial = parts[0]
            state = parts[1]

            # Try to extract model if available (e.g., model:Pixel_6)
            model = "Unknown"
            model_match = re.search(r"model:([^\s]+)", line)
            if model_match:
                model = model_match.group(1).replace("_", " ")

            devices.append({"serial": serial, "state": state, "model": model})

    return devices


def connect_device(address: str) -> str:
    """
    Connects to a network ADB device (IP:Port).
    Returns the output message from adb.
    """
    try:
        result = subprocess.run(
            ["adb", "connect", address],
            capture_output=True,
            text=True,
            check=False,
            timeout=ADB_TIMEOUT_SECONDS,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error connecting to {address}: {str(e)}"


def disconnect_device(address: str) -> str:
    try:
        result = subprocess.run(
            ["adb", "disconnect", address],
            capture_output=True,
            text=True,
            check=False,
            timeout=ADB_TIMEOUT_SECONDS,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error disconnecting: {str(e)}"


def get_mdns_services() -> List[Dict[str, str]]:
    """
    Parses 'avahi-browse' to find wireless devices on the local network.
    """
    services = []
    try:
        # Check both connect and pairing services
        for service_type in ["_adb-tls-connect._tcp", "_adb-tls-pairing._tcp"]:
            result = subprocess.run(
                ["avahi-browse", "-r", "-t", "-p", service_type],
                capture_output=True,
                text=True,
                check=False,
                timeout=AVAHI_TIMEOUT_SECONDS,
            )

            lines = result.stdout.strip().split("\n")
            for line in lines:
                if line.startswith("="):
                    parts = line.split(";")
                    # Format: =;eth0;IPv4;name;type;domain;hostname;ip;port;txt
                    if len(parts) >= 9:
                        ip = parts[7]
                        port = parts[8]
                        txt = parts[9] if len(parts) > 9 else ""

                        # Extract friendly name from txt record if possible (e.g. "name=Pixel 8 Pro")
                        name_match = re.search(r'"name=([^\"]+)"', txt)
                        friendly_name = name_match.group(1) if name_match else parts[3]

                        # Only add IPv4 to avoid adb ipv6 confusion, and deduplicate
                        if parts[2] == "IPv4":
                            # Simplify the type name for user interface
                            simple_type = (
                                "Connect" if "connect" in service_type else "Pairing"
                            )
                            addr = f"{ip}:{port}"

                            # Avoid duplicates
                            if not any(s["address"] == addr for s in services):
                                services.append(
                                    {
                                        "name": f"{friendly_name} ({simple_type})",
                                        "type": service_type,
                                        "address": addr,
                                    }
                                )

    except Exception as e:
        print(f"Error running avahi-browse: {e}")

    return services


def pair_device(address: str, code: str) -> str:
    """
    Runs adb pair <address> [code]
    """
    try:
        # We need to pass the pairing code to the command or using pexpect/stdin,
        # but modern adb allows `adb pair <ip:port> <code>` as args.
        result = subprocess.run(
            ["adb", "pair", address, code],
            capture_output=True,
            text=True,
            check=False,
            timeout=ADB_TIMEOUT_SECONDS,
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"Error pairing with {address}: {str(e)}"


def get_display_ids(serial: Optional[str] = None, non_default_only: bool = False) -> List[int]:
    """
    Parse `adb shell dumpsys display` and return unique display IDs.
    If non_default_only is True, filter out display 0.
    """
    cmd = ["adb"]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["shell", "dumpsys", "display"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=ADB_TIMEOUT_SECONDS,
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    ids = [int(m.group(1)) for m in re.finditer(r"mDisplayId=(\d+)", result.stdout)]
    unique_ids = sorted(set(ids))

    if non_default_only:
        unique_ids = [d for d in unique_ids if d != 0]

    return unique_ids
