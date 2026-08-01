# JARVIS AI — Architecture

`JARVIS AI` is organized as a small pipeline of independent, swappable
modules rather than one monolithic script. Each stage degrades gracefully
if its preferred backend/library isn't installed, so the assistant is
always runnable — even headless, even without a microphone.

```
┌──────────────┐     ┌───────────────┐     ┌───────────┐     ┌──────────────┐
│  wakeword.py │ --> │   speech.py   │ --> │ brain.py  │ --> │   voice.py   │
│ "Wake up     │     │  (STT: Vosk)  │     │ (NLU +    │     │ (TTS:        │
│  Jarvis"     │     │               │     │ dispatch) │     │  pyttsx3)    │
└──────────────┘     └───────────────┘     └─────┬─────┘     └──────────────┘
                                                   │
                     ┌─────────────────────────────┼─────────────────────────┐
                     ▼                             ▼                         ▼
              ┌─────────────┐             ┌────────────────┐         ┌──────────────┐
              │  memory.py  │             │  commands.py   │         │ reminders.py │
              │ (SQLite:    │             │ (apps, web,    │         │ (background  │
              │ notes,      │             │  media, utils) │         │  scheduler)  │
              │ tasks,      │             └────────┬───────┘         └──────────────┘
              │ dates,      │                      │
              │ prefs,      │             ┌────────▼───────┐
              │ shortcuts)  │             │ automation.py  │
              └─────────────┘             │  system.py     │
                                          │ (PyAutoGUI,     │
                                          │  psutil, OS)    │
                                          └────────────────┘
```

## Module responsibilities

| Module | Responsibility |
|---|---|
| `assistant/config.py` | Loads `settings.json`, merges with safe defaults. |
| `assistant/logger.py` | Rotating file + console logging. |
| `assistant/database.py` | Owns the SQLite connection and schema only. |
| `assistant/memory.py` | CRUD for notes, tasks, important dates, preferences, shortcuts. |
| `assistant/reminders.py` | Schedules and polls due reminders (daily or one-time) on a background thread. |
| `assistant/wakeword.py` | Detects the wake phrase; hardware engine (OpenWakeWord/Porcupine) or console dev-mode fallback. |
| `assistant/speech.py` | Converts spoken audio to text (Vosk); falls back to typed stdin in dev mode. |
| `assistant/brain.py` | Pattern-matches recognized text to an intent and dispatches to a handler. |
| `assistant/commands.py` | Concrete actions: open apps/websites, search, calculator, time/date, media keys. |
| `assistant/automation.py` | Keyboard/mouse/window/clipboard/screenshot automation (PyAutoGUI/pygetwindow/pyperclip). |
| `assistant/system.py` | CPU/RAM stats (psutil), shutdown/restart/lock, volume/brightness (Windows). |
| `assistant/voice.py` | Text-to-speech output (pyttsx3), console fallback. |
| `assistant/time_parsing.py` | Small dependency-free natural-language time parser for reminders. |
| `ui/main_window.py` | PySide6 dark/cyan "glass" main window: status, waveform, memory/reminder panels, system stats, logs. |
| `ui/tray.py` | System tray icon, show/hide, sleep/wake, exit. |
| `main.py` | Wires the pipeline together; GUI or console mode. |

## Why rule-based NLU instead of an ML model?

The brief calls for a lightweight assistant that stays responsive on a
4GB-RAM machine with no GPU. A regex/keyword intent table:

- Starts instantly (no model load time).
- Uses effectively zero extra RAM/CPU beyond the Python interpreter.
- Is fully transparent and easy for contributors to extend — add one
  `Intent(name, pattern, handler)` entry to `Brain._build_intents()`.

The trade-off is reduced flexibility in phrasing compared to an LLM-based
NLU. The roadmap (see `ROADMAP.md`) proposes an optional, swappable
LLM-based intent layer for anyone who wants heavier NLU and has the
hardware for it.

## Data flow: "Wake up Jarvis" → response

1. `wakeword.py` detects the phrase (or, in dev mode, matches typed input).
2. `main.py` calls `brain.wake_greeting()` and speaks it via `voice.py`.
3. `speech.py` listens for one utterance (timeout from `settings.json`).
4. `brain.handle(text)` matches the first intent whose pattern fits, or
   falls back to a learned shortcut, or a generic "not sure how" reply.
5. The handler calls into `commands.py`, `memory.py`, `reminders.py`,
   `automation.py`, or `system.py` as needed, and returns a plain-English
   reply string.
6. `voice.py` speaks the reply; the GUI (if active) logs it and refreshes
   the memory/reminders panels.

## Persistence

All durable state lives in a single SQLite file at `database/memory.db`
(path configurable in `settings.json`). This file is deliberately excluded
from version control (`.gitignore`) since it is personal, machine-specific
data — every user gets a fresh, empty database on first run.
