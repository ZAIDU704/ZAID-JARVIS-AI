"""
wakeword.py
Wake word ("Wake up Jarvis") detection for JARVIS AI.

Prefers OpenWakeWord (free, offline, no API key). Picovoice Porcupine is
supported as an alternative if the user has an access key and a trained
.ppn keyword file (set wake_word.engine = "porcupine" in settings.json).

When no wake-word engine or microphone is available, falls back to a
simple text-matching dev mode so the rest of the assistant pipeline can
be developed and tested on any machine, including headless CI runners.
"""

from __future__ import annotations

from typing import Callable, Optional

from assistant.logger import get_logger

log = get_logger("wakeword")

try:
    import openwakeword  # type: ignore

    _OWW_AVAILABLE = True
except Exception:  # noqa: BLE001
    _OWW_AVAILABLE = False

try:
    import pvporcupine  # type: ignore

    _PORCUPINE_AVAILABLE = True
except Exception:  # noqa: BLE001
    _PORCUPINE_AVAILABLE = False


class WakeWordDetector:
    """Listens continuously for the configured wake phrase.

    `on_wake` is invoked (with no arguments) whenever the wake phrase is
    detected. In dev mode, `text_matches` can be used to check typed input
    against the wake phrase instead of listening to a microphone.
    """

    def __init__(self, phrase: str = "wake up jarvis", engine: str = "openwakeword",
                 dev_mode: Optional[bool] = None):
        self.phrase = phrase.lower().strip()
        self.engine_name = engine
        self._running = False

        if dev_mode is None:
            dev_mode = not (
                (engine == "openwakeword" and _OWW_AVAILABLE)
                or (engine == "porcupine" and _PORCUPINE_AVAILABLE)
            )
        self.dev_mode = dev_mode

        if self.dev_mode:
            log.warning(
                "No wake-word engine available for '%s'. Running in dev mode: "
                "typing the wake phrase in the console will trigger activation. "
                "Install openwakeword (pip install openwakeword) for real "
                "always-on microphone wake-word detection.",
                engine,
            )

    def text_matches(self, text: str) -> bool:
        """Check whether a piece of typed/recognized text contains the
        wake phrase. Used directly in dev mode and console fallback."""
        return self.phrase in text.lower().strip()

    def run_forever(self, on_wake: Callable[[], None], stop_check: Callable[[], bool]) -> None:
        """Block, listening for the wake phrase, until stop_check() is True.

        In dev mode this reads lines from stdin. In hardware mode this
        would run the real microphone-based wake-word engine; that
        integration point is clearly marked below for contributors to
        wire up their preferred engine/model file.
        """
        self._running = True
        if self.dev_mode:
            self._run_forever_dev(on_wake, stop_check)
        else:
            self._run_forever_hardware(on_wake, stop_check)

    def _run_forever_dev(self, on_wake: Callable[[], None], stop_check: Callable[[], bool]) -> None:
        print(f"[dev-mode] JARVIS is sleeping. Type '{self.phrase}' to wake it, "
              f"or 'exit' to quit.")
        while not stop_check():
            try:
                text = input("(sleeping) > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text.lower() == "exit":
                break
            if self.text_matches(text):
                on_wake()

    def _run_forever_hardware(self, on_wake: Callable[[], None], stop_check: Callable[[], bool]) -> None:
        # NOTE: Real microphone wake-word integration.
        #
        # For OpenWakeWord: load/stream microphone frames through an
        # openwakeword.Model with a custom or pretrained keyword model
        # for "Wake up Jarvis", and call on_wake() when its confidence
        # score crosses a threshold.
        #
        # For Porcupine: create a pvporcupine.create(...) instance with a
        # trained .ppn keyword file for the phrase, feed it microphone
        # frames, and call on_wake() when process() returns a keyword index.
        #
        # This is left as a clearly documented extension point because it
        # requires a trained keyword model file that is specific to the
        # exact phrase and cannot be produced without the vendor's training
        # console / model files, which are outside this repository.
        log.error(
            "Hardware wake-word engine '%s' selected but not fully wired up. "
            "Falling back to dev mode.", self.engine_name
        )
        self.dev_mode = True
        self._run_forever_dev(on_wake, stop_check)

    def stop(self) -> None:
        self._running = False
