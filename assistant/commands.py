"""
commands.py
Concrete command implementations for JARVIS AI.

brain.py decides *which* command to run from natural language; this module
implements *what happens* when that command runs: launching apps, opening
websites, controlling media, checking time/date, etc.

App paths are looked up from a small cross-platform table plus common
Windows install locations, then fall back to just calling the executable
name (relying on PATH) so the assistant is still useful without hardcoded
paths for every machine.
"""

from __future__ import annotations

import datetime
import os
import platform
import subprocess
import webbrowser
from typing import Dict, Optional

from assistant import automation, system
from assistant.logger import get_logger

log = get_logger("commands")

IS_WINDOWS = platform.system() == "Windows"

# Common application launch targets. Values are Windows executable names
# that rely on PATH/registry app-path resolution (works out of the box on
# most Windows installs for these particular apps); on other platforms we
# try a reasonable equivalent.
APP_LAUNCH_TABLE: Dict[str, Dict[str, str]] = {
    "chrome": {"windows": "chrome", "darwin": "open -a 'Google Chrome'", "linux": "google-chrome"},
    "google chrome": {"windows": "chrome", "darwin": "open -a 'Google Chrome'", "linux": "google-chrome"},
    "firefox": {"windows": "firefox", "darwin": "open -a Firefox", "linux": "firefox"},
    "edge": {"windows": "msedge", "darwin": "open -a 'Microsoft Edge'", "linux": "microsoft-edge"},
    "notepad": {"windows": "notepad", "darwin": "open -a TextEdit", "linux": "gedit"},
    "calculator": {"windows": "calc", "darwin": "open -a Calculator", "linux": "gnome-calculator"},
    "vs code": {"windows": "code", "darwin": "open -a 'Visual Studio Code'", "linux": "code"},
    "visual studio code": {"windows": "code", "darwin": "open -a 'Visual Studio Code'", "linux": "code"},
    "vscode": {"windows": "code", "darwin": "open -a 'Visual Studio Code'", "linux": "code"},
    "word": {"windows": "winword", "darwin": "open -a 'Microsoft Word'", "linux": "libreoffice --writer"},
    "excel": {"windows": "excel", "darwin": "open -a 'Microsoft Excel'", "linux": "libreoffice --calc"},
    "spotify": {"windows": "spotify", "darwin": "open -a Spotify", "linux": "spotify"},
    "file explorer": {"windows": "explorer", "darwin": "open .", "linux": "nautilus ."},
    "explorer": {"windows": "explorer", "darwin": "open .", "linux": "nautilus ."},
    "terminal": {"windows": "cmd", "darwin": "open -a Terminal", "linux": "gnome-terminal"},
    "cmd": {"windows": "cmd", "darwin": "open -a Terminal", "linux": "gnome-terminal"},
}

WEBSITE_TABLE: Dict[str, str] = {
    "github": "https://github.com",
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "stack overflow": "https://stackoverflow.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
}


def _platform_key() -> str:
    return {"Windows": "windows", "Darwin": "darwin", "Linux": "linux"}.get(
        platform.system(), "linux"
    )


def open_app(name: str) -> str:
    """Open a known desktop application by name."""
    key = name.strip().lower()
    entry = APP_LAUNCH_TABLE.get(key)
    if entry is None:
        # Best-effort: try launching the raw name via the OS.
        try:
            subprocess.Popen(key, shell=True)
            log.info("Attempted best-effort launch of '%s'", key)
            return f"Trying to open {name}."
        except Exception:  # noqa: BLE001
            log.exception("Failed to open unknown app '%s'", name)
            return f"I don't know how to open '{name}' yet. You can add it as a custom shortcut."

    launch_cmd = entry[_platform_key()]
    try:
        if IS_WINDOWS:
            os.startfile(launch_cmd)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(launch_cmd, shell=True)
        log.info("Opened app '%s' via '%s'", name, launch_cmd)
        return f"Opening {name.title()}."
    except Exception:  # noqa: BLE001
        log.exception("Failed to open app '%s'", name)
        return f"I couldn't open {name}. It might not be installed."


def close_app(name: str) -> str:
    """Close a running application by (partial, case-insensitive) window title
    or process name."""
    result = automation.close_window(name)
    if "requires" not in result and "No open window" not in result:
        return result

    key = name.strip().lower()
    process_name = {
        "chrome": "chrome.exe", "google chrome": "chrome.exe",
        "firefox": "firefox.exe", "edge": "msedge.exe",
        "notepad": "notepad.exe", "vs code": "Code.exe",
        "visual studio code": "Code.exe", "word": "winword.exe",
        "excel": "excel.exe", "spotify": "spotify.exe",
    }.get(key)

    if process_name and IS_WINDOWS:
        try:
            subprocess.run(["taskkill", "/IM", process_name, "/F"], check=False)
            return f"Closed {name.title()}."
        except Exception:  # noqa: BLE001
            log.exception("Failed to close app '%s'", name)
    return f"I couldn't find '{name}' running to close it."


def open_website(url_or_name: str) -> str:
    key = url_or_name.strip().lower()
    url = WEBSITE_TABLE.get(key)
    if url is None:
        url = url_or_name if url_or_name.startswith("http") else f"https://{url_or_name}"
    webbrowser.open(url)
    log.info("Opened website %s", url)
    return f"Opening {url}."


def search_google(query: str) -> str:
    import urllib.parse

    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Searching Google for {query}."


def open_folder(path: str) -> str:
    expanded = os.path.expanduser(os.path.expandvars(path))
    if not os.path.exists(expanded):
        return f"I couldn't find the folder '{path}'."
    try:
        if IS_WINDOWS:
            os.startfile(expanded)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", expanded])
        else:
            subprocess.Popen(["xdg-open", expanded])
        return f"Opening folder {path}."
    except Exception:  # noqa: BLE001
        log.exception("Failed to open folder '%s'", path)
        return f"I couldn't open the folder '{path}'."


def get_time() -> str:
    return datetime.datetime.now().strftime("It's %I:%M %p.")


def get_date() -> str:
    return datetime.datetime.now().strftime("Today is %A, %B %d, %Y.")


def calculate(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression (no arbitrary code exec)."""
    import ast
    import operator as op

    allowed_ops = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
        ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg,
        ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")

    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return f"{expression} equals {result}."
    except Exception:  # noqa: BLE001
        return "I couldn't calculate that. Try something like '12 * 7 + 3'."


def media_control(action: str) -> str:
    """Play/pause/next/previous/volume up/down via virtual media keys."""
    key_map = {
        "play": "playpause", "pause": "playpause", "play_pause": "playpause",
        "next": "nexttrack", "previous": "prevtrack",
        "volume_up": "volumeup", "volume_down": "volumedown", "mute": "volumemute",
    }
    key = key_map.get(action)
    if key is None:
        return f"Unknown media action '{action}'."
    result = automation.press_key(key)
    if "requires" in result:
        return result
    return f"Media: {action.replace('_', ' ')}."


def get_weather(city: Optional[str] = None) -> str:
    """Weather is intentionally left as an optional, clearly-documented stub:
    a real implementation needs a live internet connection and a weather API
    key, which is out of scope for an offline-first assistant core. Wire
    this up to a provider such as Open-Meteo or OpenWeatherMap and read the
    API key from settings.json / an environment variable."""
    location = city or "your area"
    return (
        f"Weather lookups aren't configured yet for {location}. "
        f"Add a weather API key in settings.json to enable this feature."
    )
