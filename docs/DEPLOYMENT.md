# JARVIS AI — Deployment Guide

## 1. Development setup (any OS)

```bash
git clone https://github.com/<your-username>/JARVIS-AI.git
cd JARVIS-AI
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
python main.py --dev          # console mode, typed commands instead of mic/wake-word hardware
```

`--dev` mode is the fastest way to try the assistant on *any* machine — it
lets you type `wake up jarvis` and then type commands, without needing a
microphone, wake-word model, or GUI library installed. This is exactly how
the project was tested during development (see `README.md` → Testing).

## 2. Full offline voice setup (Windows, recommended target platform)

1. **Speech recognition model (Vosk):** download a small English model
   (~50MB) from https://alphacephei.com/vosk/models, e.g.
   `vosk-model-small-en-us-0.15`, and unzip it to
   `models/vosk-model-small-en-us/` (or update
   `speech_recognition.model_path` in `settings.json`).
2. **Wake word:** install `openwakeword` (`pip install openwakeword`). Out
   of the box it ships several pretrained keywords; a custom "Wake up
   Jarvis" keyword model needs to be trained separately with
   OpenWakeWord's training tools (see their repo) and referenced from
   `assistant/wakeword.py`'s hardware integration point (clearly marked in
   the source with a `NOTE:` comment).
3. **Text-to-speech:** `pip install pyttsx3` — uses Windows SAPI5 voices
   out of the box, no extra setup.
4. Run normally: `python main.py`

## 3. Building a Windows executable

```bash
pip install pyinstaller
pyinstaller jarvis.spec
```

This produces `dist/JARVIS-AI/JARVIS-AI.exe` plus its supporting files
(a one-folder build, not one-file — recommended so `settings.json` and
`assets/` can be edited/inspected without unpacking an archive).

**Known limitation of this repository as delivered:** the executable build
step above has **not** been run or confirmed on a real Windows machine as
part of this project's automated development, because the development
environment used to generate this codebase had no internet access and was
not running Windows (Linux container, no PyInstaller/PySide6/Vosk
available to install). The core Python logic was fully tested with
Python's built-in `unittest` framework instead (24 passing tests — see
`tests/`). Before relying on the executable, please:

1. Run `pyinstaller jarvis.spec` yourself on Windows 10/11.
2. Launch `dist/JARVIS-AI/JARVIS-AI.exe` and confirm it starts.
3. Open an issue if you hit a PyInstaller hidden-import error — the most
   common cause is a TTS/STT backend needing an extra `--hidden-import`
   flag, which varies by exact library version.

The included `.github/workflows/build.yml` CI pipeline runs the test suite
on every push and (on `windows-latest`) builds the executable with
PyInstaller automatically, so once pushed to GitHub, Actions will validate
the Windows build for you.

## 4. Running at Windows startup (optional)

To start JARVIS AI automatically when Windows boots:

1. Press `Win + R`, type `shell:startup`, press Enter.
2. Create a shortcut to `JARVIS-AI.exe` (or a `.bat` file that runs
   `python main.py`) inside that folder.
3. Set `startup.start_in_tray: true` in `settings.json` so it launches
   directly to the system tray instead of popping up the main window.

`startup.run_on_windows_startup` in `settings.json` is a placeholder flag
for a future installer/registry-based implementation (see `ROADMAP.md`) —
currently, the Startup-folder shortcut method above is the supported way
to enable this.

## 5. Permissions & platform notes

- **Microphone access:** Windows will prompt for microphone permission the
  first time an app captures audio (Settings → Privacy → Microphone).
- **Shutdown/restart/lock/volume/brightness:** implemented via Windows-only
  APIs (`shutdown.exe`, `ctypes.windll`, `pycaw`, `screen-brightness-control`).
  These intentionally no-op with a clear spoken/logged message on
  macOS/Linux rather than silently failing.
- **Brightness control** depends on your monitor/driver exposing WMI
  brightness controls; external monitors connected via HDMI/DisplayPort
  often don't support this even on Windows — this is a hardware/driver
  limitation, not a bug in JARVIS AI.
- **Antivirus/SmartScreen:** freshly built PyInstaller executables are
  unsigned and commonly flagged by Windows SmartScreen or antivirus
  heuristics on first run. This is expected for an unsigned open-source
  binary; code-signing is out of scope for this project.
