"""
config.py
Loads and provides typed access to JARVIS AI's settings.json configuration file.

Falls back to sane defaults if the settings file is missing or malformed so
the assistant never fails to start purely because of a bad config file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict

DEFAULT_SETTINGS: Dict[str, Any] = {
    "app": {
        "name": "JARVIS AI",
        "owner": "ZAID BILAL",
        "version": "1.0.0",
        "copyright": "© 2026 ZAID BILAL",
    },
    "wake_word": {
        "phrase": "wake up jarvis",
        "engine": "openwakeword",
        "listen_timeout_seconds": 12,
        "activation_sound": "assets/sounds/activate.wav",
    },
    "speech_recognition": {
        "engine": "vosk",
        "model_path": "models/vosk-model-small-en-us",
        "language": "en-us",
        "energy_threshold": 300,
    },
    "text_to_speech": {
        "engine": "pyttsx3",
        "voice_id": None,
        "rate": 180,
        "volume": 1.0,
    },
    "ui": {
        "theme": "dark_cyan_glass",
        "start_minimized": False,
        "show_waveform": True,
    },
    "startup": {
        "run_on_windows_startup": False,
        "start_in_tray": True,
    },
    "database": {
        "path": "database/memory.db",
    },
    "logging": {
        "level": "INFO",
        "file": "jarvis.log",
        "max_bytes": 1048576,
        "backup_count": 3,
    },
    "reminders": {
        "check_interval_seconds": 30,
        "desktop_notifications": True,
        "voice_notifications": True,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class Config:
    """Typed wrapper around the JARVIS settings dictionary."""

    path: str
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str = "settings.json") -> "Config":
        data = dict(DEFAULT_SETTINGS)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    user_data = json.load(fh)
                data = _deep_merge(DEFAULT_SETTINGS, user_data)
            except (json.JSONDecodeError, OSError):
                # Corrupt or unreadable settings file -> fall back to defaults.
                data = dict(DEFAULT_SETTINGS)
        return cls(path=path, data=data)

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Access a nested setting using a dotted path, e.g. 'ui.theme'."""
        node: Any = self.data
        for part in dotted_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        node = self.data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
