#!/usr/bin/env python3
"""
main.py
JARVIS AI - Entry point.

Wires together configuration, logging, the SQLite-backed memory store,
reminders, wake-word detection, speech recognition, the brain (NLU +
dispatch), and text-to-speech output into the wake -> listen -> respond
loop described in the project README.

Usage:
    python main.py                # normal run: GUI if PySide6 is
                                   # available, console otherwise
    python main.py --no-gui       # force console-only mode
    python main.py --dev          # force dev mode (typed input instead of
                                   # microphone/wake-word hardware)

Created and maintained by ZAID BILAL. (c) 2026 ZAID BILAL.
"""

from __future__ import annotations

import argparse
import sys
import threading
from typing import Optional

from assistant.brain import Brain
from assistant.config import Config
from assistant.database import Database
from assistant.logger import get_logger, setup_logging
from assistant.memory import MemoryStore
from assistant.reminders import Reminder, ReminderManager
from assistant.voice import TextToSpeech
from assistant.wakeword import WakeWordDetector
from assistant.speech import SpeechRecognizer

APP_NAME = "JARVIS AI"
APP_OWNER = "ZAID BILAL"


class JarvisApp:
    """Orchestrates the full wake -> listen -> understand -> respond loop."""

    def __init__(self, config: Config, dev_mode: Optional[bool] = None):
        self.config = config
        self.log = get_logger("main")

        self.db = Database(config.get("database.path", "database/memory.db"))
        self.memory = MemoryStore(self.db)

        self.tts = TextToSpeech(
            engine=config.get("text_to_speech.engine", "pyttsx3"),
            rate=config.get("text_to_speech.rate", 180),
            volume=config.get("text_to_speech.volume", 1.0),
            voice_id=config.get("text_to_speech.voice_id"),
        )

        self.reminders = ReminderManager(
            self.db,
            on_due=self._on_reminder_due,
            check_interval_seconds=config.get("reminders.check_interval_seconds", 30),
        )

        self.brain = Brain(self.memory, self.reminders)

        self.wakeword = WakeWordDetector(
            phrase=config.get("wake_word.phrase", "wake up jarvis"),
            engine=config.get("wake_word.engine", "openwakeword"),
            dev_mode=dev_mode,
        )
        self.speech = SpeechRecognizer(
            model_path=config.get("speech_recognition.model_path", "models/vosk-model-small-en-us"),
            dev_mode=dev_mode,
        )

        self._running = True

    # ------------------------------------------------------------- callbacks
    def _on_reminder_due(self, reminder: Reminder) -> None:
        self.tts.speak(f"Reminder: {reminder.message}")

    # ---------------------------------------------------------------- loop
    def on_wake(self) -> None:
        greeting = self.brain.wake_greeting()
        self.tts.speak(greeting)

        timeout = self.config.get("wake_word.listen_timeout_seconds", 12)
        heard = self.speech.listen(timeout_seconds=timeout)

        if not heard:
            self.tts.speak("Going back to sleep.")
            return

        self.log.info("Heard command: %s", heard)
        reply = self.brain.handle(heard)
        self.tts.speak(reply)

    def stop_check(self) -> bool:
        return not self._running

    def shutdown(self) -> None:
        self._running = False
        self.reminders.stop()
        self.db.close()

    def run_console(self) -> None:
        self.reminders.start()
        self.log.info("%s is running (console mode). Press Ctrl+C to exit.", APP_NAME)
        try:
            self.wakeword.run_forever(self.on_wake, self.stop_check)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def run_gui(self) -> int:
        """Run with the PySide6 desktop UI + system tray, listening for the
        wake word on a background thread."""
        from PySide6.QtWidgets import QApplication

        from ui.main_window import MainWindow
        from ui.tray import JarvisTray

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        window = MainWindow(APP_NAME, APP_OWNER)
        if not self.config.get("ui.start_minimized", False):
            window.show()

        def handle_wake() -> None:
            window.set_listening(True)
            window.append_log(f"{APP_NAME}: {self.brain.wake_greeting()}")
            self.on_wake()
            window.set_listening(False)
            window.refresh_memory_list(
                [n.content for n in self.memory.all_notes()[:20]]
            )
            window.refresh_reminders_list(
                [f"{r.message} @ {r.due_at}" for r in self.reminders.list_upcoming()]
            )

        tray = JarvisTray(window, on_wake=handle_wake, on_sleep=lambda: window.set_listening(False))
        tray.show()

        self.reminders.start()

        wake_thread = threading.Thread(
            target=self.wakeword.run_forever,
            args=(handle_wake, self.stop_check),
            daemon=True,
        )
        wake_thread.start()

        exit_code = app.exec()
        self.shutdown()
        return exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - by {APP_OWNER}")
    parser.add_argument("--no-gui", action="store_true", help="Force console-only mode")
    parser.add_argument("--dev", action="store_true", help="Force dev mode (typed input)")
    parser.add_argument("--settings", default="settings.json", help="Path to settings.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = Config.load(args.settings)

    setup_logging(
        level=config.get("logging.level", "INFO"),
        log_file=config.get("logging.file", "jarvis.log"),
        max_bytes=config.get("logging.max_bytes", 1_048_576),
        backup_count=config.get("logging.backup_count", 3),
    )
    log = get_logger("main")
    log.info("Starting %s v%s by %s", APP_NAME, config.get("app.version"), APP_OWNER)

    app = JarvisApp(config, dev_mode=True if args.dev else None)

    if not args.no_gui:
        try:
            import PySide6  # noqa: F401

            return app.run_gui()
        except ImportError:
            log.warning("PySide6 not installed; falling back to console mode. "
                        "Install PySide6 for the full graphical interface.")

    app.run_console()
    return 0


if __name__ == "__main__":
    sys.exit(main())
