"""
voice.py
Text-to-speech output for JARVIS AI.

Prefers pyttsx3 (fully offline, cross-platform SAPI5/NSSpeech/espeak) and
falls back to Piper if configured. If no TTS engine is installed (for
example, during headless development or CI), falls back to printing the
line to the console/log so the rest of the assistant still works.
"""

from __future__ import annotations

from typing import Optional

from assistant.logger import get_logger

log = get_logger("voice")

try:
    import pyttsx3  # type: ignore

    _PYTTSX3_AVAILABLE = True
except Exception:  # noqa: BLE001  (may raise non-ImportError with no audio backend)
    _PYTTSX3_AVAILABLE = False


class TextToSpeech:
    """Speaks text aloud using the best available offline engine."""

    def __init__(self, engine: str = "pyttsx3", rate: int = 180,
                 volume: float = 1.0, voice_id: Optional[str] = None):
        self.engine_name = engine
        self.rate = rate
        self.volume = volume
        self.voice_id = voice_id
        self._engine = None

        if engine == "pyttsx3" and _PYTTSX3_AVAILABLE:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", rate)
                self._engine.setProperty("volume", volume)
                if voice_id:
                    self._engine.setProperty("voice", voice_id)
                log.info("pyttsx3 TTS engine initialized")
            except Exception:  # noqa: BLE001
                log.exception("Failed to initialize pyttsx3; falling back to console output")
                self._engine = None
        else:
            log.warning(
                "TTS engine '%s' not available (pyttsx3 installed=%s). "
                "Falling back to console output. Install pyttsx3 for real speech.",
                engine, _PYTTSX3_AVAILABLE,
            )

    def speak(self, text: str) -> None:
        """Speak `text` aloud, or print it if no engine is available."""
        log.info("JARVIS says: %s", text)
        if self._engine is not None:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return
            except Exception:  # noqa: BLE001
                log.exception("TTS playback failed; printing instead")
        print(f"[JARVIS]: {text}")

    def list_voices(self):
        """Return available system voices, if the engine supports it."""
        if self._engine is not None:
            try:
                return self._engine.getProperty("voices")
            except Exception:  # noqa: BLE001
                log.exception("Could not list voices")
        return []
