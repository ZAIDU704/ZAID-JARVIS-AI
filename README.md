# JARVIS AI

**A lightweight, offline-first, voice-controlled desktop AI assistant for Windows — inspired by Jarvis.**

Created and maintained by **ZAID BILAL** · © 2026 ZAID BILAL · MIT Licensed

> Say **"Wake up Jarvis"**, then talk to your PC.

---

## Table of Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Screenshots](#screenshots)
- [Building the Windows executable](#building-the-windows-executable)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)

---

## Features

- 🎙️ **Wake-word activation** — stays silent until you say *"Wake up Jarvis"*, then listens for a command with a configurable timeout.
- 🧠 **Natural conversation** — remembers what you tell it and recalls it later ("Remember my interview is on Monday" → "When is my interview?").
- 💾 **Persistent memory** (SQLite) — notes, tasks, important dates, preferences, and custom voice shortcuts survive restarts.
- ⏰ **Reminders** — one-time or daily, with desktop notifications and spoken alerts.
- 🖥️ **Desktop automation** — open/close apps, websites, folders; keyboard & mouse control; window management; screenshots; clipboard.
- 🔊 **Offline voice output** (pyttsx3) and **offline speech recognition** (Vosk) — no cloud dependency, no API keys required for core functionality.
- 🎛️ **System control** — shutdown, restart, lock, volume, brightness (Windows).
- 🖼️ **Modern dark/cyan "glass" UI** (PySide6) with a listening waveform animation, memory/reminder panels, and live CPU/RAM stats.
- 🧊 **System tray** background operation — show/hide, sleep/wake, exit.
- 🪶 **Optimized for low-end PCs** — rule-based NLU (no heavy ML model to load), designed to run comfortably on 4GB RAM.

## How it works

```
You: "Wake up Jarvis."
Jarvis: "Yes boss. I'm listening."

You: "Open Chrome."
Jarvis: "Opening Chrome."

You: "Remember my interview is on Monday."
Jarvis: "Done. I'll remember that."

You: "Wake up Jarvis."
Jarvis: "Ready for your command."

You: "When is my interview?"
Jarvis: "Your interview is Monday."
```

This exact flow is covered by an automated test (`tests/test_brain.py ::
TestBrainConversationExample`) and was manually verified end-to-end during
development in console dev-mode.

If no command is spoken within the configured timeout (default 12
seconds, see `settings.json`), JARVIS quietly goes back to sleep.

## Architecture

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full pipeline
diagram and module-by-module breakdown. In short:

```
wake word → speech-to-text → NLU/brain (intent matching) → command
execution (apps/system/automation/memory/reminders) → text-to-speech
```

Every stage has a graceful offline/no-hardware fallback, so the assistant
is always runnable for development even without a microphone, speakers, or
GUI libraries installed (see [Known Limitations](#known-limitations)).

## Installation

```bash
git clone https://github.com/<your-username>/JARVIS-AI.git
cd JARVIS-AI
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

Try it instantly without any audio hardware, in console dev-mode:

```bash
python main.py --no-gui --dev
```

Then type `wake up jarvis`, press Enter, and type a command.

Full setup for real offline microphone/wake-word/speech (Vosk model
download, OpenWakeWord install, etc.) is in
**[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

## Configuration

All behavior is controlled by `settings.json` in the project root —
wake phrase, listening timeout, TTS voice/rate, theme, database path,
logging level, reminder check interval, and more. See the comments in
`assistant/config.py` for the full default schema; any keys you omit fall
back to sensible defaults automatically.

## Project Structure

```
JARVIS-AI/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── main.py                  # Entry point
├── settings.json            # User-editable configuration
├── jarvis.spec              # PyInstaller build spec
├── assistant/
│   ├── config.py
│   ├── logger.py
│   ├── database.py
│   ├── memory.py            # Notes, tasks, dates, preferences, shortcuts
│   ├── reminders.py          # Reminder scheduling
│   ├── wakeword.py           # "Wake up Jarvis" detection
│   ├── speech.py              # Speech-to-text (Vosk)
│   ├── voice.py               # Text-to-speech (pyttsx3)
│   ├── brain.py                # NLU / intent dispatch
│   ├── commands.py             # App/web/utility command implementations
│   ├── automation.py           # Keyboard/mouse/window/clipboard
│   ├── system.py                # CPU/RAM stats, power, volume, brightness
│   └── time_parsing.py           # Natural-language time parsing
├── ui/
│   ├── main_window.py            # PySide6 main window
│   ├── tray.py                    # System tray
│   └── theme.py                    # Dark cyan "glass" QSS theme
├── database/                        # memory.db lives here (gitignored)
├── assets/
│   └── sounds/                       # Activation sound, etc. (placeholders)
├── tests/
│   ├── test_memory.py
│   ├── test_reminders.py
│   └── test_brain.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── ROADMAP.md
│   └── CONTRIBUTING.md
└── .github/workflows/build.yml
```

## Screenshots

> _Screenshots of the running desktop UI are not included in this initial
> commit — the reference development environment used to build this
> project had no display server available to render and capture PySide6
> screenshots. Contributors running the app on Windows/macOS/Linux with a
> display are welcome to add real screenshots here via PR._

`[ Placeholder: main window — sleeping state ]`
`[ Placeholder: main window — listening / waveform active ]`
`[ Placeholder: system tray menu ]`

## Building the Windows executable

```bash
pip install pyinstaller
pyinstaller jarvis.spec
```

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for full details,
including the **honest caveat** that this build step has not yet been run
on a real Windows machine as part of this repository's automated
development (see [Known Limitations](#known-limitations)) — a GitHub
Actions workflow (`.github/workflows/build.yml`) is included to build and
validate it on `windows-latest` automatically once pushed.

## Testing

```bash
pytest tests/ -v
```

24 automated tests cover:
- Memory persistence (notes, tasks, dates, preferences, shortcuts, and
  reconnecting to an existing database file).
- Reminder scheduling (due/not-due detection, daily rescheduling,
  cancellation, sort order).
- Brain intent parsing, including the exact wake-word conversation
  example above, plus a safety test confirming the calculator can't
  execute arbitrary code.

All 24 tests pass in the reference development environment (Python 3.12,
Linux container, stdlib `unittest` runner since `pytest` itself could not
be installed offline — the test files are written to be `pytest`-
compatible as well).

## Known Limitations

This project was built and tested in a sandboxed Linux container with
**no internet access and no audio/display hardware**. In the interest of
not overclaiming, here's exactly what that means:

| Feature | Status |
|---|---|
| Core logic (memory, reminders, NLU, command dispatch) | ✅ Fully implemented and unit-tested |
| Wake-word → conversation flow | ✅ Verified end-to-end in console dev-mode |
| Offline STT (Vosk) / TTS (pyttsx3) / wake-word (OpenWakeWord) | ⚠️ Implemented with real library integrations, but **not** exercised against real audio hardware in this environment — falls back to console/dev mode automatically when unavailable |
| PySide6 GUI | ⚠️ Implemented, but not run in this environment (no display server / PySide6 install) |
| Windows-specific system control (shutdown/restart/lock/volume/brightness) | ⚠️ Implemented, gated behind platform checks; not run on real Windows |
| PyInstaller `.exe` build | ⚠️ Spec file provided and CI workflow included; **the executable itself has not been built or launched** in this environment (no Windows, no PyInstaller install available) |
| Brightness control | ⚠️ Depends on monitor/driver WMI support even on real Windows — not universal |

If you build and run this on real Windows hardware and hit issues, please
open an issue — the fallback/dev-mode paths were prioritized specifically
so the *rest* of the assistant keeps working even if one piece (say, your
particular audio driver) doesn't cooperate.

## Roadmap

See **[docs/ROADMAP.md](docs/ROADMAP.md)**.

## Contributing

See **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)**.

## License

MIT — see [LICENSE](LICENSE).

## Credits

**JARVIS AI** created and maintained by **ZAID BILAL**.
© 2026 ZAID BILAL.

Built with: Python, PySide6, Vosk, OpenWakeWord, pyttsx3, PyAutoGUI,
psutil, SQLite.
