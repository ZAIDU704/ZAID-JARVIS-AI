"""Tests for assistant.memory.MemoryStore, using a temporary SQLite file."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.database import Database
from assistant.memory import MemoryStore


class TestMemoryStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_memory.db")
        self.db = Database(self.db_path)
        self.memory = MemoryStore(self.db)

    def tearDown(self):
        self.db.close()

    def test_remember_and_recall_date(self):
        self.memory.remember_date("interview", "Monday")
        result = self.memory.find_date("interview")
        self.assertIsNotNone(result)
        self.assertEqual(result.date_value, "Monday")

    def test_recall_date_partial_match(self):
        self.memory.remember_date("job interview", "next Friday")
        result = self.memory.find_date("interview")
        self.assertIsNotNone(result)
        self.assertEqual(result.date_value, "next Friday")

    def test_recall_missing_date_returns_none(self):
        result = self.memory.find_date("birthday")
        self.assertIsNone(result)

    def test_remember_note_and_find(self):
        self.memory.remember_note("Buy milk and eggs")
        notes = self.memory.find_notes("milk")
        self.assertEqual(len(notes), 1)
        self.assertIn("milk", notes[0].content)

    def test_tasks_lifecycle(self):
        task_id = self.memory.add_task("Finish the report")
        tasks = self.memory.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["description"], "Finish the report")

        completed = self.memory.complete_task(task_id)
        self.assertTrue(completed)

        remaining = self.memory.list_tasks()
        self.assertEqual(len(remaining), 0)

        all_tasks = self.memory.list_tasks(include_done=True)
        self.assertEqual(len(all_tasks), 1)
        self.assertEqual(all_tasks[0]["done"], 1)

    def test_preferences_roundtrip(self):
        self.memory.set_preference("wake_phrase", "wake up jarvis")
        value = self.memory.get_preference("wake_phrase")
        self.assertEqual(value, "wake up jarvis")

    def test_preference_default(self):
        value = self.memory.get_preference("nonexistent", default="fallback")
        self.assertEqual(value, "fallback")

    def test_shortcuts_roundtrip(self):
        self.memory.add_shortcut("project x", "open_folder", "/home/user/project-x")
        shortcut = self.memory.get_shortcut("Project X")  # case-insensitive
        self.assertIsNotNone(shortcut)
        self.assertEqual(shortcut["action"], "open_folder")
        self.assertEqual(shortcut["target"], "/home/user/project-x")

    def test_persistence_across_reconnect(self):
        self.memory.remember_note("Persisted note")
        self.db.close()

        # Reopen the same file and confirm the note survived.
        db2 = Database(self.db_path)
        memory2 = MemoryStore(db2)
        notes = memory2.find_notes("Persisted")
        self.assertEqual(len(notes), 1)
        db2.close()
        # Reassign self.db to a fresh connection so tearDown doesn't double-close.
        self.db = Database(self.db_path)


if __name__ == "__main__":
    unittest.main()
