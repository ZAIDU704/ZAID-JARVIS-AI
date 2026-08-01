"""
memory.py
JARVIS AI's long-term memory system.

Stores personal notes, tasks, reminders' supporting data, important dates,
user preferences, and custom voice shortcuts in SQLite so the assistant
remembers things between sessions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from assistant.database import Database
from assistant.logger import get_logger

log = get_logger("memory")


@dataclass
class Note:
    id: int
    key: Optional[str]
    content: str
    created_at: str


@dataclass
class ImportantDate:
    id: int
    label: str
    date_value: str
    created_at: str


class MemoryStore:
    """High-level API over the database for durable assistant memory."""

    def __init__(self, db: Database):
        self.db = db

    # ---------------------------------------------------------------- notes
    def remember_note(self, content: str, key: Optional[str] = None) -> int:
        """Store a free-form note, optionally tagged with a lookup key."""
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO notes (key, content) VALUES (?, ?)",
                (key, content),
            )
            note_id = cur.lastrowid
        log.info("Stored note #%s: %s", note_id, content)
        return note_id

    def find_notes(self, query: str) -> List[Note]:
        """Return notes whose key or content contains the query text."""
        like = f"%{query.lower()}%"
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT id, key, content, created_at FROM notes "
                "WHERE lower(content) LIKE ? OR lower(coalesce(key, '')) LIKE ? "
                "ORDER BY id DESC",
                (like, like),
            )
            rows = cur.fetchall()
        return [Note(r["id"], r["key"], r["content"], r["created_at"]) for r in rows]

    def all_notes(self) -> List[Note]:
        with self.db.cursor() as cur:
            cur.execute("SELECT id, key, content, created_at FROM notes ORDER BY id DESC")
            rows = cur.fetchall()
        return [Note(r["id"], r["key"], r["content"], r["created_at"]) for r in rows]

    # ---------------------------------------------------------------- tasks
    def add_task(self, description: str) -> int:
        with self.db.cursor() as cur:
            cur.execute("INSERT INTO tasks (description) VALUES (?)", (description,))
            task_id = cur.lastrowid
        log.info("Added task #%s: %s", task_id, description)
        return task_id

    def complete_task(self, task_id: int) -> bool:
        with self.db.cursor() as cur:
            cur.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def list_tasks(self, include_done: bool = False) -> List[dict]:
        query = "SELECT id, description, done, created_at FROM tasks"
        if not include_done:
            query += " WHERE done = 0"
        query += " ORDER BY id ASC"
        with self.db.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ---------------------------------------------------------- important dates
    def remember_date(self, label: str, date_value: str) -> int:
        """Store an important date, e.g. label='interview', date_value='Monday'."""
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO important_dates (label, date_value) VALUES (?, ?)",
                (label, date_value),
            )
            row_id = cur.lastrowid
        log.info("Remembered date '%s' -> %s", label, date_value)
        return row_id

    def find_date(self, label_query: str) -> Optional[ImportantDate]:
        """Find the most recently stored date whose label matches the query."""
        like = f"%{label_query.lower()}%"
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT id, label, date_value, created_at FROM important_dates "
                "WHERE lower(label) LIKE ? ORDER BY id DESC LIMIT 1",
                (like,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return ImportantDate(row["id"], row["label"], row["date_value"], row["created_at"])

    # ----------------------------------------------------------------- prefs
    def set_preference(self, key: str, value: str) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.db.cursor() as cur:
            cur.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cur.fetchone()
        return row["value"] if row else default

    # -------------------------------------------------------------- shortcuts
    def add_shortcut(self, name: str, action: str, target: str) -> None:
        """Create a custom voice shortcut, e.g. name='project x',
        action='open_folder', target='C:/Users/zaid/Projects/x'."""
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO shortcuts (name, action, target) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET action = excluded.action, "
                "target = excluded.target",
                (name.lower(), action, target),
            )
        log.info("Registered shortcut '%s' -> %s(%s)", name, action, target)

    def get_shortcut(self, name: str) -> Optional[dict]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT name, action, target FROM shortcuts WHERE name = ?",
                (name.lower(),),
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def all_shortcuts(self) -> List[dict]:
        with self.db.cursor() as cur:
            cur.execute("SELECT name, action, target FROM shortcuts ORDER BY name")
            rows = cur.fetchall()
        return [dict(r) for r in rows]
