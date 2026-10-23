#!/usr/bin/env python3
"""
tools/diagnose.py  -  JARVIS AI beginner-friendly diagnostics (stage A1).

READ-ONLY. This script:
  * never installs packages or changes any setting (Windows or otherwise),
  * never makes a network request (a guard blocks sockets, and it never
    contacts Gemini or any other service),
  * never opens the microphone or plays any sound,
  * never writes files (save its output yourself if you want a copy),
  * never prints API keys, setting values that look secret, your user name,
    computer name, or home-folder path (these are replaced with <user>,
    <host>, ~ and <project>).

Usage (Windows PowerShell, from the project folder):
    python tools\\diagnose.py
Options:
    --skip-audio     do not list audio input devices
    --skip-tts       do not initialise text-to-speech
    --skip-pipcheck  do not run `python -m pip check`

Exit code: 0 if there is no [FAIL] line, 1 otherwise.
Passing this script does NOT prove the microphone, speakers or GUI work;
it only reports what can be checked safely. See the summary at the end.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.metadata as importlib_metadata
import importlib.util
import json
import logging
import os
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DIAG_VERSION = "A1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROBE_PREFIX = "JARVIS_DIAG_JSON:"
PROBE_TIMEOUT_SECONDS = 30
MAX_LINE = 200


# --------------------------------------------------------------------------
# Safety helpers: no network, redaction, ASCII-only output
# --------------------------------------------------------------------------
def _block_network() -> None:
    """Make any accidental socket use fail loudly instead of connecting."""

    def _blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("network access is disabled in diagnose.py")

    socket.socket.connect = _blocked  # type: ignore[method-assign]
    socket.socket.connect_ex = _blocked  # type: ignore[method-assign]
    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.getaddrinfo = _blocked  # type: ignore[assignment]


def _build_redactions() -> List[Tuple[re.Pattern, str]]:
    pairs: List[Tuple[re.Pattern, str]] = []

    def add(value: Optional[str], replacement: str) -> None:
        if value and len(value) >= 3:
            for variant in {value, value.replace("\\", "/")}:
                pairs.append((re.compile(re.escape(variant), re.IGNORECASE), replacement))

    add(str(PROJECT_ROOT), "<project>")
    try:
        add(str(Path.home()), "~")
    except Exception:  # noqa: BLE001
        pass
    add(os.environ.get("USERPROFILE"), "~")
    for env_name, replacement in (
        ("USERNAME", "<user>"), ("USER", "<user>"),
        ("COMPUTERNAME", "<host>"), ("HOSTNAME", "<host>"),
    ):
        add(os.environ.get(env_name), replacement)
    try:
        add(socket.gethostname(), "<host>")  # local call, no network
    except Exception:  # noqa: BLE001
        pass
    pairs.sort(key=lambda p: len(p[0].pattern), reverse=True)
    return pairs


_REDACTIONS = _build_redactions()
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
_SECRET_NAME_RE = re.compile(r"key|token|secret|passw|credential|cookie|auth", re.IGNORECASE)


def clean(text: Any, limit: int = MAX_LINE) -> str:
    """Single-line, ASCII-only, redacted text that is safe to paste."""
    s = str(text)
    for pattern, replacement in _REDACTIONS:
        s = pattern.sub(replacement, s)
    s = _LONG_TOKEN_RE.sub("[hidden]", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.encode("ascii", "replace").decode("ascii")
    return s if len(s) <= limit else s[: limit - 3] + "..."


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
_results: List[Tuple[str, str, str]] = []
_section = ""


def section(title: str) -> None:
    global _section
    _section = title
    print(f"\n== {title} ==")


def emit(level: str, text: str, detail: Optional[List[str]] = None) -> None:
    _results.append((level, _section, clean(text)))
    print(f"  [{level:<4}] {clean(text)}")
    for line in detail or []:
        print(f"         {clean(line)}")


# --------------------------------------------------------------------------
# Probes: run risky native-library checks in a child process so a crash or
# hang cannot take the diagnostic down. Probes only LIST things; they never
# record audio, play sound, or use the network.
# --------------------------------------------------------------------------
def _probe_audio() -> Dict[str, Any]:
    import sounddevice as sd  # type: ignore

    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    try:
        default_in = int(sd.default.device[0])
    except Exception:  # noqa: BLE001
        default_in = -1
    inputs = []
    for index, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0:
            inputs.append({
                "index": index,
                "name": str(dev.get("name", "?")),
                "api": str(hostapis[dev["hostapi"]]["name"]),
                "channels": int(dev["max_input_channels"]),
                "rate": int(dev.get("default_samplerate", 0)),
            })
    return {"default_input": default_in, "inputs": inputs}


def _probe_tts() -> Dict[str, Any]:
    import pyttsx3  # type: ignore

    engine = pyttsx3.init()
    voices = [{"id": str(v.id), "name": str(v.name)} for v in engine.getProperty("voices")]
    info = {
        "voices": voices,
        "rate": engine.getProperty("rate"),
        "volume": engine.getProperty("volume"),
    }
    try:
        engine.stop()
    except Exception:  # noqa: BLE001
        pass
    return info


def _probe_qt() -> Dict[str, Any]:
    from PySide6 import QtCore  # type: ignore  # no QApplication, no window

    return {"qt": QtCore.qVersion(), "pyside": QtCore.__version__}


_PROBES = {"audio": _probe_audio, "tts": _probe_tts, "qt": _probe_qt}


def _probe_main(name: str) -> int:
    _block_network()
    try:
        payload: Dict[str, Any] = {"ok": True, **_PROBES[name]()}
    except BaseException as exc:  # noqa: BLE001
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    print(PROBE_PREFIX + json.dumps(payload, ensure_ascii=True))
    return 0


def run_probe(name: str) -> Dict[str, Any]:
    """Run a probe in a child interpreter; always returns a dict."""
    cmd = [sys.executable, "-I", str(Path(__file__).resolve()), "--probe", name]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=PROBE_TIMEOUT_SECONDS, cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out after {PROBE_TIMEOUT_SECONDS}s"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"could not start probe: {type(exc).__name__}"}
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(PROBE_PREFIX):
            try:
                return json.loads(line[len(PROBE_PREFIX):])
            except ValueError:
                break
    return {"ok": False, "error": f"probe crashed (exit code {proc.returncode})"}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def _ver_tuple(text: str) -> Tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", text)[:4])


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def check_python_and_system() -> None:
    section("1. Python and system")
    v = sys.version_info
    version_text = f"{v.major}.{v.minor}.{v.micro}"
    bits = "64-bit" if sys.maxsize > 2**32 else "32-bit"
    if (v.major, v.minor) == (3, 13):
        emit("OK", f"Python {version_text} ({bits}) matches the target (3.13)")
    elif (v.major, v.minor) < (3, 9):
        emit("FAIL", f"Python {version_text} is too old for this project (needs 3.9+, target 3.13)")
    else:
        emit("WARN", f"Python {version_text} ({bits}); your target is 3.13 so results may differ")
    if bits == "32-bit":
        emit("WARN", "32-bit Python: many speech/UI wheels are 64-bit only")

    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_venv:
        emit("OK", "Running inside a virtual environment")
    else:
        emit("WARN", "NOT inside a virtual environment (recommended: python -m venv venv)")

    system = platform.system()
    emit("INFO", f"OS: {system} {platform.release()} ({platform.machine()}), build {platform.version()}")
    if system == "Windows":
        if platform.release() == "10":
            emit("OK", "Windows 10 detected (matches target)")
        else:
            emit("INFO", f"Windows release is {platform.release()}; target is Windows 10")
    else:
        emit("INFO", "Not Windows: Windows-only checks are reported as SKIP and prove nothing about your laptop")

    if importlib.util.find_spec("psutil") is not None:
        try:
            import psutil  # type: ignore

            gb = psutil.virtual_memory().total / (1024 ** 3)
            level = "OK" if gb >= 3.5 else "WARN"
            emit(level, f"Installed RAM: {gb:.1f} GB (target machine has 4 GB)")
        except Exception as exc:  # noqa: BLE001
            emit("WARN", f"psutil is installed but RAM query failed: {type(exc).__name__}")
    else:
        emit("INFO", "RAM size unknown (psutil not installed)")

    cwd_ok = Path.cwd().resolve() == PROJECT_ROOT
    if cwd_ok:
        emit("OK", "Current folder is the project folder")
    else:
        emit("WARN", "Current folder is NOT the project folder; the app uses relative paths "
                     "(settings.json, database/, models/), so start it from the project folder")
    if len(str(PROJECT_ROOT)) > 120:
        emit("WARN", "Project path is long; Windows path limits can break deep model folders")
    if "onedrive" in str(PROJECT_ROOT).lower():
        emit("WARN", "Project is inside a OneDrive folder; sync can lock or conflict with the SQLite database")
    if not (PROJECT_ROOT / "main.py").exists():
        emit("FAIL", "main.py not found next to tools/; run this script from inside the project")


PACKAGES = [
    # (pip name, import name, kind, what it is for, windows_only)
    ("psutil", "psutil", "core", "CPU/RAM statistics", False),
    ("PySide6", "PySide6", "feature", "desktop window (console mode works without it)", False),
    ("vosk", "vosk", "feature", "offline speech recognition", False),
    ("sounddevice", "sounddevice", "feature", "microphone capture", False),
    ("openwakeword", "openwakeword", "feature", "wake-word engine", False),
    ("pyttsx3", "pyttsx3", "feature", "spoken replies", False),
    ("pyautogui", "pyautogui", "feature", "keyboard/mouse/screenshots", False),
    ("pygetwindow", "pygetwindow", "feature", "window management", False),
    ("pyperclip", "pyperclip", "feature", "clipboard", False),
    ("pycaw", "pycaw", "feature", "Windows volume control", True),
    ("comtypes", "comtypes", "feature", "Windows COM support", True),
    ("screen-brightness-control", "screen_brightness_control", "feature", "brightness", False),
    ("plyer", "plyer", "feature", "desktop notifications", False),
    ("pyinstaller", "PyInstaller", "dev", "building an .exe", False),
    ("pytest", "pytest", "dev", "test runner", False),
]


def read_requirement_minimums() -> Dict[str, str]:
    path = PROJECT_ROOT / "requirements.txt"
    minimums: Dict[str, str] = {}
    if not path.exists():
        emit("WARN", "requirements.txt not found")
        return minimums
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*>=\s*([0-9][0-9A-Za-z.]*)", line)
        if m:
            minimums[_normalize(m.group(1))] = m.group(2)
    return minimums


def check_packages(skip_pipcheck: bool) -> None:
    section("2. Python packages (checked without importing them)")
    minimums = read_requirement_minimums()
    is_windows = platform.system() == "Windows"
    for pip_name, import_name, kind, purpose, windows_only in PACKAGES:
        if windows_only and not is_windows:
            emit("SKIP", f"{pip_name}: Windows-only package ({purpose})")
            continue
        try:
            found = importlib.util.find_spec(import_name) is not None
        except Exception:  # noqa: BLE001
            found = False
        if not found:
            level = {"core": "FAIL", "feature": "WARN", "dev": "INFO"}[kind]
            emit(level, f"{pip_name}: NOT installed - needed for {purpose}")
            continue
        try:
            installed = importlib_metadata.version(pip_name)
        except Exception:  # noqa: BLE001
            installed = "unknown"
        minimum = minimums.get(_normalize(pip_name))
        if installed != "unknown" and minimum and _ver_tuple(installed) < _ver_tuple(minimum):
            emit("WARN", f"{pip_name} {installed} is older than requirements.txt minimum {minimum}")
        else:
            emit("OK", f"{pip_name} {installed} installed ({purpose})")

    if skip_pipcheck:
        emit("SKIP", "pip check skipped by option")
        return
    env = dict(os.environ, PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INPUT="1")
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-m", "pip", "check"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60, env=env, cwd=str(PROJECT_ROOT),
        )
        output = proc.stdout.strip().splitlines()
        if proc.returncode == 0:
            emit("OK", "pip check: no broken or conflicting dependencies")
        elif "No module named pip" in (proc.stderr or ""):
            emit("SKIP", "pip is not available in this Python")
        else:
            emit("WARN", "pip check reported dependency conflicts:", output[:8])
    except Exception as exc:  # noqa: BLE001
        emit("SKIP", f"pip check could not run: {type(exc).__name__}")


EXPECTED_SETTINGS: Dict[str, Dict[str, Any]] = {
    "wake_word": {"phrase": str, "engine": str, "listen_timeout_seconds": (int, float)},
    "speech_recognition": {"engine": str, "model_path": str, "language": str},
    "text_to_speech": {"engine": str, "rate": (int, float), "volume": (int, float)},
    "ui": {"start_minimized": bool},
    "database": {"path": str},
    "logging": {"level": str, "file": str, "max_bytes": int, "backup_count": int},
    "reminders": {"check_interval_seconds": (int, float)},
}


def _find_secret_fields(node: Any, path: str = "") -> List[str]:
    hits: List[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if isinstance(value, (dict, list)):
                hits += _find_secret_fields(value, child)
            elif isinstance(value, str) and value.strip() and _SECRET_NAME_RE.search(str(key)):
                hits.append(child)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            hits += _find_secret_fields(value, f"{path}[{i}]")
    return hits


def load_settings() -> Optional[Dict[str, Any]]:
    path = PROJECT_ROOT / "settings.json"
    if not path.exists():
        emit("WARN", "settings.json not found; the app will use built-in defaults")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        emit("WARN", f"settings.json is unreadable ({type(exc).__name__}); the app silently falls back "
                     "to defaults without telling you")
        return None
    if not isinstance(data, dict):
        emit("WARN", "settings.json must contain a JSON object at the top level")
        return None
    return data


def check_config() -> Optional[Dict[str, Any]]:
    """Validate settings.json and return the parsed data (or None)."""
    section("3. Configuration (settings.json) - secret values are never printed")
    data = load_settings()
    if data is None:
        return None
    emit("OK", "settings.json is valid JSON")
    problems = 0
    for sect, keys in EXPECTED_SETTINGS.items():
        block = data.get(sect)
        if not isinstance(block, dict):
            emit("INFO", f"section '{sect}' missing; defaults will be used")
            continue
        for key, expected in keys.items():
            if key not in block:
                emit("INFO", f"{sect}.{key} missing; default will be used")
                continue
            value = block[key]
            numeric = expected == (int, float)
            ok = isinstance(value, expected) and not (numeric and isinstance(value, bool))
            if not ok:
                emit("WARN", f"{sect}.{key} has the wrong type ({type(value).__name__})")
                problems += 1

    def _num(sect: str, key: str) -> Optional[float]:
        value = (data.get(sect) or {}).get(key) if isinstance(data.get(sect), dict) else None
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    for sect, key, low, high in (
        ("wake_word", "listen_timeout_seconds", 1, 60),
        ("text_to_speech", "rate", 50, 400),
        ("text_to_speech", "volume", 0, 1),
        ("reminders", "check_interval_seconds", 1, 3600),
    ):
        value = _num(sect, key)
        if value is not None and not (low <= value <= high):
            emit("WARN", f"{sect}.{key} = {value:g} is outside the sensible range {low}-{high}")
            problems += 1
    level_name = (data.get("logging") or {}).get("level") if isinstance(data.get("logging"), dict) else None
    if isinstance(level_name, str) and not isinstance(logging.getLevelName(level_name.upper()), int):
        emit("WARN", "logging.level is not a valid level name")
        problems += 1
    if problems == 0:
        emit("OK", "Known settings have sensible types and ranges")

    secrets = _find_secret_fields(data)
    if secrets:
        emit("WARN", "Secret-like fields found in settings.json (values hidden): " + ", ".join(secrets[:6]),
             ["Do not keep API keys in files inside the project folder or ZIP."])
    else:
        emit("OK", "No secret-like values found in settings.json")
    return data


def _resolve_project_path(value: str) -> Path:
    p = Path(os.path.expandvars(os.path.expanduser(value)))
    return p if p.is_absolute() else PROJECT_ROOT / p


def _dir_size_mb(root: Path, max_files: int = 20000) -> Optional[float]:
    total = count = 0
    try:
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                count += 1
                if count > max_files:
                    return None
                try:
                    total += os.path.getsize(os.path.join(dirpath, name))
                except OSError:
                    pass
    except OSError:
        return None
    return total / (1024 * 1024)


def check_vosk_model(data: Optional[Dict[str, Any]]) -> None:
    section("4. Vosk speech model (files only; the model is not loaded)")
    model_value = "models/vosk-model-small-en-us"
    if data and isinstance(data.get("speech_recognition"), dict):
        configured = data["speech_recognition"].get("model_path")
        if isinstance(configured, str) and configured.strip():
            model_value = configured
    model_dir = _resolve_project_path(model_value)
    emit("INFO", f"Configured model folder: {model_value}")

    if not model_dir.is_dir():
        models_root = PROJECT_ROOT / "models"
        found = sorted(p.name for p in models_root.iterdir() if p.is_dir())[:10] if models_root.is_dir() else []
        emit("WARN", "Vosk model folder not found; speech recognition will use typed input instead",
             [f"Folders inside models/: {', '.join(found)}" if found else "models/ is missing or empty.",
              "Download is NOT done by this script; see docs/DEPLOYMENT.md."])
        return

    if not (model_dir / "am").is_dir():
        nested = [p for p in model_dir.iterdir() if p.is_dir() and (p / "am").is_dir()]
        if nested:
            emit("WARN", "Model looks nested one folder too deep",
                 [f"Point model_path at: {Path(model_value) / nested[0].name}"])
            return

    required = [("am/final.mdl", (model_dir / "am" / "final.mdl").is_file()),
                ("conf/mfcc.conf", (model_dir / "conf" / "mfcc.conf").is_file()),
                ("graph/ (not empty)", (model_dir / "graph").is_dir() and any((model_dir / "graph").iterdir()))]
    missing = [name for name, present in required if not present]
    if missing:
        emit("FAIL", "Vosk model folder is incomplete; missing: " + ", ".join(missing))
    else:
        emit("OK", "Required Vosk model files are present (am, conf, graph)")
    if not (model_dir / "ivector").is_dir():
        emit("INFO", "No ivector/ folder (normal for some models)")
    size = _dir_size_mb(model_dir)
    emit("INFO", f"Model size on disk: {size:.0f} MB" if size is not None else "Model size not measured")
    emit("INFO", "Model language is not detected automatically; check the folder name matches your language")


def check_audio(skip: bool) -> None:
    section("5. Audio input devices (listing only; the microphone is NOT opened)")
    if skip:
        emit("SKIP", "skipped by option")
        return
    if importlib.util.find_spec("sounddevice") is None:
        emit("SKIP", "sounddevice is not installed, so devices cannot be listed")
        return
    result = run_probe("audio")
    if not result.get("ok"):
        emit("WARN", f"Could not list audio devices: {result.get('error', 'unknown error')}",
             ["The app would fall back to typed input."])
        return
    inputs = result.get("inputs", [])
    if not inputs:
        emit("WARN", "No audio INPUT devices found (no microphone detected by PortAudio)")
        return
    emit("OK", f"{len(inputs)} input device entries found (the same microphone can appear under several drivers)")
    default_index = result.get("default_input", -1)
    for dev in inputs[:12]:
        mark = " (default)" if dev.get("index") == default_index else ""
        emit("INFO", f"#{dev.get('index')} {clean(dev.get('name'), 60)} [{clean(dev.get('api'), 24)}] "
                     f"{dev.get('channels')}ch {dev.get('rate')}Hz{mark}")
    if len(inputs) > 12:
        emit("INFO", f"... and {len(inputs) - 12} more")
    if default_index in (-1, None):
        emit("WARN", "No default input device is set in Windows/PortAudio")
    emit("INFO", "LAPTOP CHECK: listing devices does not prove capture works; Windows microphone "
                 "permission (Settings > Privacy > Microphone) cannot be checked here")


LANG_HINTS = ("hindi", "urdu", "india", "pakistan")


def check_tts(skip: bool, data: Optional[Dict[str, Any]]) -> None:
    section("6. Text-to-speech (initialises the engine; nothing is spoken)")
    if skip:
        emit("SKIP", "skipped by option")
        return
    if importlib.util.find_spec("pyttsx3") is None:
        emit("SKIP", "pyttsx3 is not installed; replies would be printed as text")
        return
    result = run_probe("tts")
    if not result.get("ok"):
        emit("WARN", f"pyttsx3 failed to initialise: {result.get('error', 'unknown error')}",
             ["The app would print replies instead of speaking them."])
        return
    voices = result.get("voices", [])
    emit("OK", f"pyttsx3 initialised; {len(voices)} voice(s) installed")
    for voice in voices[:10]:
        emit("INFO", f"voice: {clean(voice.get('name'), 70)}")
    hits = [v["name"] for v in voices if any(h in str(v.get("name", "")).lower() for h in LANG_HINTS)]
    if hits:
        emit("INFO", "Voices whose NAME suggests Hindi/Urdu/India/Pakistan: " + clean(", ".join(hits), 120)
             + " (name-based guess, not a language test)")
    else:
        emit("INFO", "No installed voice name suggests Hindi or Urdu (name-based guess)")
    configured = None
    if data and isinstance(data.get("text_to_speech"), dict):
        configured = data["text_to_speech"].get("voice_id")
    if configured:
        if configured in {v.get("id") for v in voices}:
            emit("OK", "Configured text_to_speech.voice_id is installed")
        else:
            emit("WARN", "Configured text_to_speech.voice_id is NOT among installed voices")
    emit("INFO", "LAPTOP CHECK: audible output through your speakers is not tested here")


def check_ui_and_assets(data: Optional[Dict[str, Any]]) -> None:
    section("7. UI files, assets and build files")
    for rel in ("ui/__init__.py", "ui/main_window.py", "ui/theme.py", "ui/tray.py"):
        emit("OK" if (PROJECT_ROOT / rel).is_file() else "FAIL", f"{rel} {'present' if (PROJECT_ROOT / rel).is_file() else 'MISSING'}")
    if importlib.util.find_spec("PySide6") is None:
        emit("SKIP", "PySide6 not installed; GUI cannot start (console mode would be used)")
    else:
        result = run_probe("qt")
        if result.get("ok"):
            emit("OK", f"PySide6 {result.get('pyside')} loads (Qt {result.get('qt')})")
        else:
            emit("WARN", f"PySide6 is installed but failed to load: {result.get('error')}")
        emit("INFO", "LAPTOP CHECK: no window is opened here, so the GUI itself is untested")
    for rel in ("assets/logo.png", "assets/logo.ico"):
        emit("OK" if (PROJECT_ROOT / rel).is_file() else "INFO",
             f"{rel} {'present' if (PROJECT_ROOT / rel).is_file() else 'not found (no logo bundled)'}")
    sound = None
    if data and isinstance(data.get("wake_word"), dict):
        sound = data["wake_word"].get("activation_sound")
    if isinstance(sound, str) and sound:
        exists = _resolve_project_path(sound).is_file()
        emit("OK" if exists else "INFO", f"activation sound file {'present' if exists else 'not found (optional)'}")
    spec = (PROJECT_ROOT / "jarvis.spec").is_file()
    emit("OK" if spec else "INFO",
         "jarvis.spec present" if spec else "jarvis.spec not found (needed only for building the .exe, not for running)")
    db_dir = PROJECT_ROOT / "database"
    emit("OK" if db_dir.is_dir() else "WARN", "database/ folder " + ("present" if db_dir.is_dir() else "missing"))
    if platform.system() != "Windows":
        emit("SKIP", "Windows-only checks (shutdown, lock, volume, brightness) are not run on this OS")


GEMINI_ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _has_gemini_code() -> bool:
    pattern = re.compile(r"gemini|genai", re.IGNORECASE)
    candidates = [PROJECT_ROOT / "main.py"]
    for folder in ("assistant", "ui"):
        candidates += sorted((PROJECT_ROOT / folder).glob("*.py"))
    for path in candidates:
        try:
            if pattern.search(path.read_text(encoding="utf-8", errors="replace")):
                return True
        except OSError:
            continue
    return False


def check_gemini(data: Optional[Dict[str, Any]]) -> None:
    section("8. Gemini status (NO request is ever sent by this script)")
    code = _has_gemini_code()
    present_vars = [name for name in GEMINI_ENV_VARS if os.environ.get(name, "").strip()]
    in_settings = bool(data and "gemini" in data)
    for name in GEMINI_ENV_VARS:
        emit("INFO", f"Environment variable {name}: {'set (value hidden)' if name in present_vars else 'not set'}")
    for pkg in ("google-genai", "google-generativeai"):
        try:
            emit("INFO", f"Package {pkg} {importlib_metadata.version(pkg)} installed")
        except Exception:  # noqa: BLE001
            emit("INFO", f"Package {pkg}: not installed")
    emit("INFO", f"'gemini' section in settings.json: {'present' if in_settings else 'absent'}")
    if not code:
        state, why = "DISABLED", "this build contains no Gemini integration code"
    elif not present_vars and not in_settings:
        state, why = "AWAITING_CONFIGURATION", "integration code exists but no credentials are configured"
    else:
        state, why = "READY_FOR_EXPLICIT_TEST", "credentials seem configured; a test must be requested explicitly"
    emit("INFO", f"Gemini state: {state} ({why})")
    emit("INFO", "Free-tier eligibility, model availability and billing status are NOT checked here "
                 "and remain unverified until you confirm them in Google AI Studio")


def print_summary() -> int:
    counts = {level: 0 for level in ("OK", "INFO", "WARN", "FAIL", "SKIP")}
    for level, _sec, _text in _results:
        counts[level] += 1
    print("\n== Summary ==")
    print("  " + "  ".join(f"{k}={v}" for k, v in counts.items()))
    attention = [(lvl, sec, txt) for lvl, sec, txt in _results if lvl in ("FAIL", "WARN")]
    if attention:
        print("  Needs attention:")
        for lvl, sec, txt in attention:
            print(f"   - [{lvl}] ({sec.split('.')[0]}) {clean(txt, 150)}")
    print("\n  This script did NOT: contact the network or Gemini, install anything, change settings,")
    print("  open the microphone, play sound, open a window, or write any file.")
    print("  Passing here does not prove microphone, speaker or GUI behaviour on your laptop.")
    print("  Please copy this whole output and send it back.")
    return 1 if counts["FAIL"] else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="JARVIS AI read-only diagnostics")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--skip-tts", action="store_true")
    parser.add_argument("--skip-pipcheck", action="store_true")
    parser.add_argument("--probe", choices=sorted(_PROBES), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.probe:
        return _probe_main(args.probe)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    _block_network()

    print(f"JARVIS AI diagnostics {DIAG_VERSION} (read-only) - "
          f"{datetime.datetime.now().isoformat(timespec='seconds')}")
    check_python_and_system()
    check_packages(args.skip_pipcheck)
    data = check_config()
    check_vosk_model(data)
    check_audio(args.skip_audio)
    check_tts(args.skip_tts, data)
    check_ui_and_assets(data)
    check_gemini(data)
    return print_summary()


if __name__ == "__main__":
    sys.exit(main())
