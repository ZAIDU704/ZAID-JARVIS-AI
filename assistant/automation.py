"""
automation.py
Desktop automation for JARVIS AI: keyboard/mouse control, window
management, screenshots, and clipboard access.

Built on PyAutoGUI (keyboard/mouse/screenshot) and pygetwindow (window
management), both optional so the rest of the assistant still runs on
machines/CI where GUI automation libraries or a display aren't available.
"""

from __future__ import annotations

import datetime
import os
from typing import Optional

from assistant.logger import get_logger

log = get_logger("automation")

try:
    import pyautogui  # type: ignore

    _PYAUTOGUI_AVAILABLE = True
except Exception:  # noqa: BLE001  (pyautogui raises on import w/o a display)
    _PYAUTOGUI_AVAILABLE = False

try:
    import pygetwindow as gw  # type: ignore

    _PYGETWINDOW_AVAILABLE = True
except Exception:  # noqa: BLE001
    _PYGETWINDOW_AVAILABLE = False

try:
    import pyperclip  # type: ignore

    _PYPERCLIP_AVAILABLE = True
except Exception:  # noqa: BLE001  (may raise non-ImportError with no clipboard backend)
    _PYPERCLIP_AVAILABLE = False


def _unavailable(feature: str, dependency: str) -> str:
    msg = f"{feature} requires '{dependency}', which isn't installed/available here."
    log.warning(msg)
    return msg


# --------------------------------------------------------------- keyboard
def type_text(text: str) -> str:
    if not _PYAUTOGUI_AVAILABLE:
        return _unavailable("Typing text", "pyautogui")
    pyautogui.write(text, interval=0.02)
    return f"Typed: {text}"


def press_key(key: str) -> str:
    if not _PYAUTOGUI_AVAILABLE:
        return _unavailable("Key press", "pyautogui")
    pyautogui.press(key)
    return f"Pressed {key}."


def hotkey(*keys: str) -> str:
    if not _PYAUTOGUI_AVAILABLE:
        return _unavailable("Hotkey", "pyautogui")
    pyautogui.hotkey(*keys)
    return f"Pressed {'+'.join(keys)}."


# ------------------------------------------------------------------ mouse
def move_mouse(x: int, y: int) -> str:
    if not _PYAUTOGUI_AVAILABLE:
        return _unavailable("Mouse move", "pyautogui")
    pyautogui.moveTo(x, y, duration=0.2)
    return f"Moved mouse to ({x}, {y})."


def click_mouse(x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> str:
    if not _PYAUTOGUI_AVAILABLE:
        return _unavailable("Mouse click", "pyautogui")
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button)
    else:
        pyautogui.click(button=button)
    return "Clicked."


# -------------------------------------------------------------- windows
def list_windows() -> list:
    if not _PYGETWINDOW_AVAILABLE:
        log.warning("Window management requires 'pygetwindow'.")
        return []
    return [w.title for w in gw.getAllWindows() if w.title]


def focus_window(title_substring: str) -> str:
    if not _PYGETWINDOW_AVAILABLE:
        return _unavailable("Window focus", "pygetwindow")
    matches = [w for w in gw.getAllWindows() if title_substring.lower() in w.title.lower()]
    if not matches:
        return f"No open window matching '{title_substring}'."
    win = matches[0]
    try:
        win.activate()
    except Exception:  # noqa: BLE001
        log.exception("Failed to focus window")
        return f"Found '{win.title}' but couldn't bring it to focus."
    return f"Focused '{win.title}'."


def minimize_window(title_substring: str) -> str:
    if not _PYGETWINDOW_AVAILABLE:
        return _unavailable("Window management", "pygetwindow")
    matches = [w for w in gw.getAllWindows() if title_substring.lower() in w.title.lower()]
    if not matches:
        return f"No open window matching '{title_substring}'."
    matches[0].minimize()
    return f"Minimized '{matches[0].title}'."


def close_window(title_substring: str) -> str:
    if not _PYGETWINDOW_AVAILABLE:
        return _unavailable("Window management", "pygetwindow")
    matches = [w for w in gw.getAllWindows() if title_substring.lower() in w.title.lower()]
    if not matches:
        return f"No open window matching '{title_substring}'."
    matches[0].close()
    return f"Closed '{matches[0].title}'."


# --------------------------------------------------------------- screenshot
def take_screenshot(output_dir: str = "screenshots") -> str:
    if not _PYAUTOGUI_AVAILABLE:
        return _unavailable("Screenshot", "pyautogui")
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(
        output_dir, f"screenshot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
    )
    image = pyautogui.screenshot()
    image.save(filename)
    log.info("Saved screenshot to %s", filename)
    return f"Screenshot saved to {filename}."


# ---------------------------------------------------------------- clipboard
def copy_to_clipboard(text: str) -> str:
    if not _PYPERCLIP_AVAILABLE:
        return _unavailable("Clipboard access", "pyperclip")
    pyperclip.copy(text)
    return "Copied to clipboard."


def read_clipboard() -> str:
    if not _PYPERCLIP_AVAILABLE:
        return _unavailable("Clipboard access", "pyperclip")
    return pyperclip.paste()
