"""
system.py
System-level information and control for JARVIS AI: CPU/RAM stats, power
actions (shutdown/restart/lock), volume, and brightness.

Power/volume/brightness actions are Windows-specific (as requested by the
project brief) and are guarded so they fail safely with a clear message on
other platforms instead of raising unhandled exceptions.
"""

from __future__ import annotations

import ctypes
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

from assistant.logger import get_logger

log = get_logger("system")

try:
    import psutil  # type: ignore

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

IS_WINDOWS = platform.system() == "Windows"


@dataclass
class SystemStats:
    cpu_percent: float
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float


def get_system_stats() -> SystemStats:
    """Return current CPU and RAM usage. Requires psutil; returns zeros with
    a logged warning if psutil isn't installed."""
    if not _PSUTIL_AVAILABLE:
        log.warning("psutil not installed; system stats unavailable")
        return SystemStats(0.0, 0.0, 0.0, 0.0)

    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    return SystemStats(
        cpu_percent=cpu,
        ram_percent=mem.percent,
        ram_used_mb=mem.used / (1024 * 1024),
        ram_total_mb=mem.total / (1024 * 1024),
    )


def _require_windows(action: str) -> Optional[str]:
    if not IS_WINDOWS:
        msg = f"'{action}' is only implemented for Windows in this build."
        log.warning(msg)
        return msg
    return None


def shutdown(delay_seconds: int = 5) -> str:
    if (err := _require_windows("shutdown")) is not None:
        return err
    subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)], check=False)
    return f"Shutting down in {delay_seconds} seconds."


def restart(delay_seconds: int = 5) -> str:
    if (err := _require_windows("restart")) is not None:
        return err
    subprocess.run(["shutdown", "/r", "/t", str(delay_seconds)], check=False)
    return f"Restarting in {delay_seconds} seconds."


def cancel_shutdown() -> str:
    if (err := _require_windows("cancel shutdown")) is not None:
        return err
    subprocess.run(["shutdown", "/a"], check=False)
    return "Scheduled shutdown/restart cancelled."


def lock_pc() -> str:
    if (err := _require_windows("lock")) is not None:
        return err
    try:
        ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
        return "PC locked."
    except Exception:  # noqa: BLE001
        log.exception("Failed to lock workstation")
        return "I couldn't lock the PC."


def set_volume(percent: int) -> str:
    """Set system volume (0-100). Uses pycaw if available; otherwise
    reports that the feature requires an extra dependency."""
    percent = max(0, min(100, percent))
    if (err := _require_windows("volume control")) is not None:
        return err
    try:
        from ctypes import POINTER, cast  # type: ignore

        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        return f"Volume set to {percent} percent."
    except ImportError:
        msg = "Volume control requires 'pycaw' and 'comtypes' (pip install pycaw comtypes)."
        log.warning(msg)
        return msg
    except Exception:  # noqa: BLE001
        log.exception("Failed to set volume")
        return "I couldn't change the volume."


def set_brightness(percent: int) -> str:
    """Set screen brightness (0-100). Uses screen_brightness_control if
    available. Not all monitors/drivers support this (documented limitation)."""
    percent = max(0, min(100, percent))
    try:
        import screen_brightness_control as sbc  # type: ignore

        sbc.set_brightness(percent)
        return f"Brightness set to {percent} percent."
    except ImportError:
        msg = "Brightness control requires 'screen-brightness-control' (pip install screen-brightness-control)."
        log.warning(msg)
        return msg
    except Exception:  # noqa: BLE001
        log.exception("Failed to set brightness")
        return "I couldn't change the brightness. Your monitor/driver may not support software brightness control."
