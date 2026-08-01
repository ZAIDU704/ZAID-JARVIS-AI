"""
speech.py
Offline speech-to-text for JARVIS AI, built around Vosk.

Vosk is preferred because it is fully offline, lightweight, and works well
on low-end 4GB-RAM machines (unlike Whisper, which is far more accurate but
much heavier). Whisper can be swapped in by installing `openai-whisper` and
setting speech_recognition.engine to "whisper" in settings.json.

If neither engine nor a microphone is available (e.g. this is running in a
CI/dev/headless container), the recognizer falls back to reading typed
text from stdin so the rest of the pipeline (wake word -> brain -> voice)
remains fully testable without audio hardware.
"""

from __future__ import annotations

from typing import Optional

from assistant.logger import get_logger

log = get_logger("speech")

try:
    import sounddevice as sd  # type: ignore

    _SOUNDDEVICE_AVAILABLE = True
except Exception:  # noqa: BLE001  (raises OSError if no audio backend/hardware)
    _SOUNDDEVICE_AVAILABLE = False

try:
    import vosk  # type: ignore

    _VOSK_AVAILABLE = True
except Exception:  # noqa: BLE001
    _VOSK_AVAILABLE = False


class SpeechRecognizer:
    """Converts spoken audio into text.

    In "hardware" mode (Vosk + sounddevice + a downloaded model all
    present) this listens on the microphone. Otherwise it transparently
    degrades to a console/dev mode driven by typed input, which is used
    automatically in headless environments and can be forced for testing.
    """

    def __init__(self, model_path: str = "models/vosk-model-small-en-us",
                 sample_rate: int = 16000, dev_mode: Optional[bool] = None):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self._model = None

        if dev_mode is None:
            dev_mode = not (_VOSK_AVAILABLE and _SOUNDDEVICE_AVAILABLE)
        self.dev_mode = dev_mode

        if not self.dev_mode:
            try:
                self._model = vosk.Model(model_path)
                log.info("Vosk model loaded from %s", model_path)
            except Exception:  # noqa: BLE001
                log.exception(
                    "Could not load Vosk model at '%s'. Falling back to "
                    "console dev mode. Download a model from "
                    "https://alphacephei.com/vosk/models and update "
                    "settings.json to enable real microphone input.",
                    model_path,
                )
                self.dev_mode = True

    def listen(self, timeout_seconds: int = 12) -> Optional[str]:
        """Listen for one utterance and return the recognized text, or None
        on timeout / silence. In dev mode, reads a line from stdin instead."""
        if self.dev_mode:
            return self._listen_dev_mode(timeout_seconds)
        return self._listen_microphone(timeout_seconds)

    def _listen_dev_mode(self, timeout_seconds: int) -> Optional[str]:
        try:
            print(f"[dev-mode] Type a command (waiting up to {timeout_seconds}s), "
                  f"or press Enter with nothing to time out:")
            text = input("> ").strip()
            return text or None
        except (EOFError, KeyboardInterrupt):
            return None

    def _listen_microphone(self, timeout_seconds: int) -> Optional[str]:
        assert self._model is not None
        recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
        result_text = ""

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            nonlocal result_text
            if recognizer.AcceptWaveform(bytes(indata)):
                import json as _json

                result_text = _json.loads(recognizer.Result()).get("text", "")

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=callback,
            ):
                sd.sleep(int(timeout_seconds * 1000))
        except Exception:  # noqa: BLE001
            log.exception("Microphone capture failed")
            return None

        return result_text or None
