"""Tests for assistant.reminders.ReminderManager (scheduling logic only,
no real-time sleeping)."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.database import Database
from assistant.reminders import ReminderManager


class TestReminderManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = Database(os.path.join(self.tmpdir, "reminders.db"))
        self.fired = []
        self.manager = ReminderManager(self.db, on_due=self.fired.append)

    def tearDown(self):
        self.db.close()

    def test_reminder_not_due_yet(self):
        future = datetime.now() + timedelta(hours=1)
        self.manager.add_reminder("Take a break", future)
        due = self.manager.check_due_reminders(now=datetime.now())
        self.assertEqual(len(due), 0)

    def test_one_time_reminder_fires_once(self):
        past = datetime.now() - timedelta(minutes=1)
        self.manager.add_reminder("Call mom", past)

        due_first = self.manager.check_due_reminders()
        self.assertEqual(len(due_first), 1)
        self.assertEqual(due_first[0].message, "Call mom")

        # Second check should not re-fire a one-time reminder.
        due_second = self.manager.check_due_reminders()
        self.assertEqual(len(due_second), 0)

    def test_daily_reminder_reschedules(self):
        past = datetime.now() - timedelta(minutes=1)
        self.manager.add_reminder("Morning stretch", past, repeat="daily")

        due_first = self.manager.check_due_reminders()
        self.assertEqual(len(due_first), 1)

        upcoming = self.manager.list_upcoming()
        self.assertEqual(len(upcoming), 1)
        next_due = datetime.strptime(upcoming[0].due_at, "%Y-%m-%d %H:%M")
        self.assertGreater(next_due, datetime.now())

    def test_cancel_reminder(self):
        future = datetime.now() + timedelta(hours=2)
        reminder_id = self.manager.add_reminder("Team meeting", future)
        cancelled = self.manager.cancel_reminder(reminder_id)
        self.assertTrue(cancelled)
        self.assertEqual(len(self.manager.list_upcoming()), 0)

    def test_list_upcoming_sorted(self):
        now = datetime.now()
        self.manager.add_reminder("Later", now + timedelta(hours=5))
        self.manager.add_reminder("Sooner", now + timedelta(hours=1))
        upcoming = self.manager.list_upcoming()
        self.assertEqual(upcoming[0].message, "Sooner")
        self.assertEqual(upcoming[1].message, "Later")


if __name__ == "__main__":
    unittest.main()
