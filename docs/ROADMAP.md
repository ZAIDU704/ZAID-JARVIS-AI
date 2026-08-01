# Roadmap

## Near-term
- [ ] Train and ship a dedicated "Wake up Jarvis" OpenWakeWord keyword model.
- [ ] Bundle a small Vosk model download step into a first-run setup wizard.
- [ ] Confirm and publish a signed PyInstaller Windows build via CI.
- [ ] Add a Settings UI panel (currently config is JSON-only).
- [ ] Wire up a real weather provider (Open-Meteo has a free, no-key tier).

## Mid-term
- [ ] Optional Whisper backend for higher-accuracy STT on machines with
      more RAM/GPU (toggle via `speech_recognition.engine`).
- [ ] Piper TTS integration for more natural offline voices than SAPI5.
- [ ] Cross-platform automation/system-control parity for macOS and Linux
      (currently Windows-first per the project brief).
- [ ] Encrypted memory database option for sensitive notes.
- [ ] Plugin system so contributors can add commands without editing
      `brain.py`/`commands.py` directly.

## Long-term / exploratory
- [ ] Optional local-LLM-based intent parsing layer as an alternative to
      the rule-based `brain.py`, for more flexible phrasing — kept
      optional to preserve low-RAM usability as the default.
- [ ] Mobile companion app for remote reminders/notes sync.
- [ ] Multi-language wake word + speech recognition support.
