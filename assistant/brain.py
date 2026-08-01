"""
brain.py
JARVIS AI's natural language understanding and dispatch layer.

Uses lightweight, explainable rule/regex-based intent matching rather than
a heavyweight NLU model, which keeps the assistant fast and usable on
low-end 4GB-RAM machines with no GPU. Each intent is a (pattern -> handler)
pair; the first matching pattern wins. This is intentionally simple and
easy for contributors to extend with new commands.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Pattern, Tuple

from assistant import commands, system
from assistant.automation import take_screenshot, read_clipboard, copy_to_clipboard
from assistant.logger import get_logger
from assistant.memory import MemoryStore
from assistant.reminders import ReminderManager

log = get_logger("brain")

GREETING_RESPONSES = [
    "Yes boss.",
    "I'm listening.",
    "How can I help you today?",
    "Ready for your command.",
]

ACKNOWLEDGEMENTS = ["Done.", "Got it.", "Okay.", "Sure thing."]


@dataclass
class Intent:
    name: str
    pattern: Pattern
    handler: Callable[["Brain", re.Match], str]


class Brain:
    """Parses recognized text into an intent and executes it."""

    def __init__(self, memory: MemoryStore, reminders: ReminderManager):
        self.memory = memory
        self.reminders = reminders
        self.intents: List[Intent] = self._build_intents()

    # ------------------------------------------------------------- greeting
    def wake_greeting(self) -> str:
        return random.choice(GREETING_RESPONSES)

    # -------------------------------------------------------------- dispatch
    def handle(self, text: str) -> str:
        """Parse `text` and return JARVIS's spoken reply."""
        text = text.strip().rstrip(".!?")
        if not text:
            return "I didn't catch that."

        for intent in self.intents:
            # Patterns are compiled with re.IGNORECASE, so matching against
            # the original (not lower-cased) text preserves the user's
            # original casing in captured groups - e.g. "Monday" instead of
            # "monday" when recalling it back to them later.
            match = intent.pattern.match(text)
            if match:
                log.info("Matched intent '%s' for input: %s", intent.name, text)
                try:
                    return intent.handler(self, match)
                except Exception:  # noqa: BLE001
                    log.exception("Handler for intent '%s' failed", intent.name)
                    return "Something went wrong while doing that."

        # Fall back to a shortcut lookup before giving up.
        shortcut_reply = self._try_shortcut(text)
        if shortcut_reply:
            return shortcut_reply

        return "I'm not sure how to do that yet."

    def _try_shortcut(self, text: str) -> Optional[str]:
        shortcut = self.memory.get_shortcut(text.lower())
        if not shortcut:
            return None
        action, target = shortcut["action"], shortcut["target"]
        if action == "open_folder":
            return commands.open_folder(target)
        if action == "open_website":
            return commands.open_website(target)
        if action == "open_app":
            return commands.open_app(target)
        return f"I have a shortcut for '{text}' but don't know how to run action '{action}'."

    # ---------------------------------------------------------- intent table
    def _build_intents(self) -> List[Intent]:
        def rx(pattern: str) -> Pattern:
            return re.compile(pattern, re.IGNORECASE)

        return [
            # ---- memory: remembering things ----
            Intent(
                "remember_date",
                rx(r"^remember (?:that )?my (?P<label>.+?) is (?:on |this )?(?P<date>.+)$"),
                lambda b, m: b._handle_remember_date(m["label"], m["date"]),
            ),
            Intent(
                "recall_date",
                rx(r"^when is my (?P<label>.+?)\??$"),
                lambda b, m: b._handle_recall_date(m["label"]),
            ),
            Intent(
                "remember_note",
                rx(r"^remember (?:that )?(?P<content>.+)$"),
                lambda b, m: b._handle_remember_note(m["content"]),
            ),
            Intent(
                "add_task",
                rx(r"^(?:add|create) (?:a )?task(?: to)? (?P<task>.+)$"),
                lambda b, m: b._handle_add_task(m["task"]),
            ),
            Intent(
                "list_tasks",
                rx(r"^(?:what are my|list my|show my) tasks\??$"),
                lambda b, m: b._handle_list_tasks(),
            ),
            Intent(
                "add_shortcut",
                rx(r"^(?:learn|add) shortcut (?P<name>.+?) (?:to )?open (?:folder |website |app )?(?P<target>.+)$"),
                lambda b, m: b._handle_add_shortcut(m["name"], m["target"]),
            ),

            # ---- reminders ----
            Intent(
                "set_reminder",
                rx(r"^remind me to (?P<message>.+?) (?:at|on) (?P<when>.+)$"),
                lambda b, m: b._handle_set_reminder(m["message"], m["when"]),
            ),
            Intent(
                "list_reminders",
                rx(r"^(?:what are my|list my|show my) reminders\??$"),
                lambda b, m: b._handle_list_reminders(),
            ),

            # ---- apps / web ----
            Intent("open_app", rx(r"^open (?P<name>.+)$"), lambda b, m: commands.open_app(m["name"])),
            Intent("close_app", rx(r"^close (?P<name>.+)$"), lambda b, m: commands.close_app(m["name"])),
            Intent(
                "search_google",
                rx(r"^search(?: google)? for (?P<query>.+)$"),
                lambda b, m: commands.search_google(m["query"]),
            ),
            Intent(
                "open_folder",
                rx(r"^open folder (?P<path>.+)$"),
                lambda b, m: commands.open_folder(m["path"]),
            ),

            # ---- system control ----
            Intent("shutdown", rx(r"^shut ?down(?: the)?(?: pc| computer)?$"), lambda b, m: system.shutdown()),
            Intent("restart", rx(r"^restart(?: the)?(?: pc| computer)?$"), lambda b, m: system.restart()),
            Intent("cancel_shutdown", rx(r"^cancel shutdown$"), lambda b, m: system.cancel_shutdown()),
            Intent("lock", rx(r"^lock(?: the)?(?: pc| computer| screen)?$"), lambda b, m: system.lock_pc()),
            Intent(
                "set_volume",
                rx(r"^set volume to (?P<value>\d+)(?:\s*%|\s*percent)?$"),
                lambda b, m: system.set_volume(int(m["value"])),
            ),
            Intent("volume_up", rx(r"^volume up$"), lambda b, m: commands.media_control("volume_up")),
            Intent("volume_down", rx(r"^volume down$"), lambda b, m: commands.media_control("volume_down")),
            Intent("mute", rx(r"^mute$"), lambda b, m: commands.media_control("mute")),
            Intent(
                "set_brightness",
                rx(r"^set brightness to (?P<value>\d+)(?:\s*%|\s*percent)?$"),
                lambda b, m: system.set_brightness(int(m["value"])),
            ),

            # ---- media ----
            Intent("play_pause", rx(r"^(?:play|pause)(?: music)?$"), lambda b, m: commands.media_control("play_pause")),
            Intent("next_track", rx(r"^next(?: track| song)?$"), lambda b, m: commands.media_control("next")),
            Intent("prev_track", rx(r"^previous(?: track| song)?$"), lambda b, m: commands.media_control("previous")),

            # ---- utility ----
            Intent("take_screenshot", rx(r"^(?:take a )?screenshot$"), lambda b, m: take_screenshot()),
            Intent("read_clipboard", rx(r"^what(?:'s| is) (?:on |in )?(?:my |the )?clipboard\??$"), lambda b, m: read_clipboard()),
            Intent("copy_clipboard", rx(r"^copy (?P<text>.+)$"), lambda b, m: copy_to_clipboard(m["text"])),
            Intent("calculate", rx(r"^(?:calculate|what is|what's) (?P<expr>[\d\s\+\-\*\/\(\)\.%]+)$"),
                   lambda b, m: commands.calculate(m["expr"])),
            Intent("get_time", rx(r"^what(?:'s| is) the time\??$"), lambda b, m: commands.get_time()),
            Intent("get_date", rx(r"^what(?:'s| is) (?:today'?s date|the date)\??$"), lambda b, m: commands.get_date()),
            Intent("get_weather", rx(r"^(?:what(?:'s| is) the )?weather(?: in (?P<city>.+))?\??$"),
                   lambda b, m: commands.get_weather(m["city"])),
        ]

    # ------------------------------------------------------- intent handlers
    def _handle_remember_date(self, label: str, date_value: str) -> str:
        self.memory.remember_date(label.strip(), date_value.strip())
        return f"{random.choice(ACKNOWLEDGEMENTS)} I'll remember that."

    def _handle_recall_date(self, label: str) -> str:
        result = self.memory.find_date(label.strip())
        if result is None:
            return f"I don't have anything remembered about your {label.strip()}."
        return f"Your {result.label} is {result.date_value}."

    def _handle_remember_note(self, content: str) -> str:
        self.memory.remember_note(content.strip())
        return f"{random.choice(ACKNOWLEDGEMENTS)} I'll remember that."

    def _handle_add_task(self, task: str) -> str:
        self.memory.add_task(task.strip())
        return f"Added '{task.strip()}' to your tasks."

    def _handle_list_tasks(self) -> str:
        tasks = self.memory.list_tasks()
        if not tasks:
            return "You have no pending tasks."
        listing = "; ".join(t["description"] for t in tasks)
        return f"You have {len(tasks)} task(s): {listing}."

    def _handle_add_shortcut(self, name: str, target: str) -> str:
        action = "open_folder" if os_path_like(target) else "open_website"
        self.memory.add_shortcut(name.strip(), action, target.strip())
        return f"Learned a new shortcut: '{name.strip()}'."

    def _handle_set_reminder(self, message: str, when_text: str) -> str:
        from assistant.time_parsing import parse_when

        due_at, repeat = parse_when(when_text)
        if due_at is None:
            return f"I couldn't understand the time '{when_text}'."
        self.reminders.add_reminder(message.strip(), due_at, repeat)
        return f"I'll remind you to {message.strip()} at {due_at.strftime('%I:%M %p on %B %d')}."

    def _handle_list_reminders(self) -> str:
        upcoming = self.reminders.list_upcoming()
        if not upcoming:
            return "You have no upcoming reminders."
        listing = "; ".join(f"{r.message} at {r.due_at}" for r in upcoming)
        return f"You have {len(upcoming)} reminder(s): {listing}."


def os_path_like(target: str) -> bool:
    """Rough heuristic: does this look like a filesystem path rather than a
    website/app name?"""
    return bool(re.match(r"^[a-zA-Z]:\\|^/|^~", target.strip()))
