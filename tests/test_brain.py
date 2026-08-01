"""Tests for assistant.brain.Brain - intent parsing and dispatch, including
the exact wake-word conversation example from the project README."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.brain import Brain
from assistant.database import Database
from assistant.memory import MemoryStore
from assistant.reminders import ReminderManager
from assistant.wakeword import WakeWordDetector


class TestBrainConversationExample(unittest.TestCase):
    """Reproduces the exact example conversation from the README."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = Database(os.path.join(self.tmpdir, "brain.db"))
        self.memory = MemoryStore(self.db)
        self.reminders = ReminderManager(self.db)
        self.brain = Brain(self.memory, self.reminders)

    def tearDown(self):
        self.db.close()

    def test_wake_word_detected(self):
        detector = WakeWordDetector(phrase="wake up jarvis", dev_mode=True)
        self.assertTrue(detector.text_matches("Wake up Jarvis"))
        self.assertTrue(detector.text_matches("wake up jarvis please"))
        self.assertFalse(detector.text_matches("open chrome"))

    def test_remember_interview_then_recall(self):
        reply1 = self.brain.handle("Remember my interview is on Monday.")
        self.assertIn("remember", reply1.lower())

        reply2 = self.brain.handle("When is my interview?")
        self.assertIn("monday", reply2.lower())

    def test_open_chrome(self):
        # We don't actually launch a browser in the test environment; we
        # only verify the intent is correctly matched and produces the
        # expected conversational reply shape.
        reply = self.brain.handle("Open Chrome.")
        self.assertIn("chrome", reply.lower())

    def test_unknown_command_gives_graceful_fallback(self):
        reply = self.brain.handle("do a barrel roll please")
        self.assertTrue(len(reply) > 0)


class TestBrainIntents(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = Database(os.path.join(self.tmpdir, "brain2.db"))
        self.memory = MemoryStore(self.db)
        self.reminders = ReminderManager(self.db)
        self.brain = Brain(self.memory, self.reminders)

    def tearDown(self):
        self.db.close()

    def test_add_and_list_tasks(self):
        self.brain.handle("Add a task to finish the report")
        reply = self.brain.handle("What are my tasks?")
        self.assertIn("finish the report", reply.lower())

    def test_get_time_and_date(self):
        time_reply = self.brain.handle("What's the time?")
        self.assertIn("it's", time_reply.lower())

        date_reply = self.brain.handle("What's today's date?")
        self.assertIn("today is", date_reply.lower())

    def test_calculate(self):
        reply = self.brain.handle("What is 12 * 7 + 3")
        self.assertIn("87", reply)

    def test_calculate_rejects_unsafe_input(self):
        # Should never execute arbitrary code. Non-arithmetic text doesn't
        # even match the calculate intent, and calculate() itself only
        # supports numeric operators via ast - either way nothing unsafe runs.
        reply = self.brain.handle("what is __import__('os').system('echo hi')")
        self.assertNotIn("hi", reply.lower())
        self.assertTrue(
            "couldn't calculate" in reply.lower() or "not sure how" in reply.lower()
        )

    def test_set_reminder_intent(self):
        reply = self.brain.handle("Remind me to drink water at 8pm")
        self.assertIn("drink water", reply.lower())
        upcoming = self.reminders.list_upcoming()
        self.assertEqual(len(upcoming), 1)

    def test_remember_note_generic(self):
        reply = self.brain.handle("Remember that the wifi password is sunshine123")
        self.assertIn("remember", reply.lower())
        notes = self.memory.find_notes("wifi")
        self.assertEqual(len(notes), 1)


if __name__ == "__main__":
    unittest.main()
