import json
from pathlib import Path
from typing import Dict
CONFIG_DIR = Path.home() / ".config" / "scrcpy-pyqt6"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


DEFAULT_PROFILES = {
    "Default": {},  # Empty means base defaults
    "Desktop (New Display)": {
        "new_display": True,
        "new_display_res": "1920x1080/160",
        "stay_awake": True,
        "turn_screen_off": True,
        "audio_source": 0,
    },
    "Wireless (Low Bandwidth)": {
        "bitrate": "2M",
        "max_size": 1024,
        "max_fps": 30,
        "codec": 0,
        "audio_codec": 0,
    },
    "Gaming (Low Latency / UHID)": {
        "bitrate": "32M",
        "codec": 0,
        "keyboard_mode": 1,
        "mouse_mode": 1,
        "disable_screensaver": True,
        "show_touches": False,
    },
    "Audio Only": {
        "no_video": True,
        "no_window": True,
        "audio_source": 0,
    },
    "Webcam (Linux V4L2)": {
        "video_source": 1,
        "v4l2_buffer": 50,
        "no_window": True,
        "no_audio": True,
        "no_control": True,
        "v4l2_sink_default": True,
    },
}


DEFAULT_SETTINGS = {
    "auto_connect": False,
    "show_info": True,
    "show_warn": True,
    "show_error": True,
}


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)



def load_profiles() -> Dict[str, dict]:
    _ensure_dir()
    if not PROFILES_FILE.exists():
        save_profiles(DEFAULT_PROFILES)
        return DEFAULT_PROFILES.copy()

    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure defaults are always there
            for k, v in DEFAULT_PROFILES.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return DEFAULT_PROFILES.copy()


def save_profiles(profiles_dict):
    try:
        _ensure_dir()
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles_dict, f, indent=4)
    except Exception:
        pass


def load_settings():
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # ensure defaults present
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings_dict):
    try:
        _ensure_dir()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, indent=4)
    except Exception:
        pass
