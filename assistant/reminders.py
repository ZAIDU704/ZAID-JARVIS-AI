"""
reminders.py
Reminder scheduling for JARVIS AI.

Supports one-time and daily-repeating reminders. A lightweight background
thread polls the database at a configurable interval and fires a callback
(used by main.py to trigger voice output + desktop notifications) whenever
a reminder becomes due.

Deliberately avoids third-party scheduler dependencies (e.g. APScheduler)
so reminders work with only the Python standard library plus SQLite.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from assistant.database import Database
from assistant.logger import get_logger

log = get_logger("reminders")

DATETIME_FORMAT = "%Y-%m-%d %H:%M"


@dataclass
class Reminder:
    id: int
    message: str
    due_at: str  # "YYYY-MM-DD HH:MM"
    repeat: str  # "none" | "daily"
    triggered: bool


class ReminderManager:
    """Stores and periodically checks reminders, invoking a callback when due."""

    def __init__(
        self,
        db: Database,
        on_due: Optional[Callable[[Reminder], None]] = None,
        check_interval_seconds: int = 30,
    ):
        self.db = db
        self.on_due = on_due
        self.check_interval_seconds = check_interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------- CRUD API
    def add_reminder(self, message: str, due_at: datetime, repeat: str = "none") -> int:
        """Schedule a reminder. `repeat` is 'none' for a one-time reminder or
        'daily' for a reminder that re-fires every day at the same time."""
        due_str = due_at.strftime(DATETIME_FORMAT)
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO reminders (message, due_at, repeat) VALUES (?, ?, ?)",
                (message, due_str, repeat),
            )
            reminder_id = cur.lastrowid
        log.info("Scheduled reminder #%s at %s (repeat=%s): %s",
                  reminder_id, due_str, repeat, message)
        return reminder_id

    def cancel_reminder(self, reminder_id: int) -> bool:
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            return cur.rowcount > 0

    def list_upcoming(self) -> List[Reminder]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT id, message, due_at, repeat, triggered FROM reminders "
                "WHERE triggered = 0 ORDER BY due_at ASC"
            )
            rows = cur.fetchall()
        return [
            Reminder(r["id"], r["message"], r["due_at"], r["repeat"], bool(r["triggered"]))
            for r in rows
        ]

    # ------------------------------------------------------------ scheduler
    def check_due_reminders(self, now: Optional[datetime] = None) -> List[Reminder]:
        """Return reminders that are due as of `now`, marking one-time ones
        as triggered and rescheduling daily ones for the next day."""
        now = now or datetime.now()
        now_str = now.strftime(DATETIME_FORMAT)
        due: List[Reminder] = []

        with self.db.cursor() as cur:
            cur.execute(
                "SELECT id, message, due_at, repeat, triggered FROM reminders "
                "WHERE triggered = 0 AND due_at <= ?",
                (now_str,),
            )
            rows = cur.fetchall()

        for r in rows:
            reminder = Reminder(r["id"], r["message"], r["due_at"], r["repeat"], False)
            due.append(reminder)
            if r["repeat"] == "daily":
                next_due = datetime.strptime(r["due_at"], DATETIME_FORMAT) + timedelta(days=1)
                with self.db.cursor() as cur:
                    cur.execute(
                        "UPDATE reminders SET due_at = ? WHERE id = ?",
                        (next_due.strftime(DATETIME_FORMAT), r["id"]),
                    )
            else:
                with self.db.cursor() as cur:
                    cur.execute("UPDATE reminders SET triggered = 1 WHERE id = ?", (r["id"],))

        return due

    def start(self) -> None:
        """Start the background polling thread (daemon, safe to leave running)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info("Reminder polling thread started (interval=%ss)", self.check_interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        log.info("Reminder polling thread stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                due = self.check_due_reminders()
                for reminder in due:
                    log.info("Reminder due: %s", reminder.message)
                    if self.on_due:
                        try:
                            self.on_due(reminder)
                        except Exception:  # noqa: BLE001
                            log.exception("Error in reminder callback")
            except Exception:  # noqa: BLE001
                log.exception("Error while checking reminders")
            self._stop_event.wait(self.check_interval_seconds)
