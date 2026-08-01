"""
time_parsing.py
Small, dependency-free natural language time parser used by brain.py to
turn phrases like "8pm", "9:30 am", "tomorrow at 6pm", or "every day at
7am" into a concrete datetime + repeat rule for the reminder system.

This deliberately covers a practical subset of everyday phrasing rather
than being a full NLP date parser (e.g. dateparser/duckling), keeping the
assistant dependency-light and fast on low-end machines. Unsupported
phrases return (None, "none") so callers can respond gracefully.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

WEEKDAYS = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
]

TIME_RE = re.compile(
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)?", re.IGNORECASE
)


def _parse_time_part(text: str, now: datetime) -> Optional[datetime]:
    match = TIME_RE.search(text)
    if not match:
        return None
    hour = int(match["hour"])
    minute = int(match["minute"] or 0)
    ampm = (match["ampm"] or "").lower()

    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0

    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return candidate


def parse_when(text: str, now: Optional[datetime] = None) -> Tuple[Optional[datetime], str]:
    """Parse a natural-language time expression.

    Returns (due_datetime, repeat) where repeat is 'none' or 'daily'.
    Returns (None, 'none') if the expression can't be understood.
    """
    now = now or datetime.now()
    text = text.strip().lower()

    repeat = "daily" if re.search(r"\bevery ?day\b|\bdaily\b", text) else "none"

    # "tomorrow at 6pm" / "tomorrow"
    day_offset = 0
    if "tomorrow" in text:
        day_offset = 1

    # "on monday" / "monday at 9am"
    for i, day in enumerate(WEEKDAYS):
        if day in text:
            today_idx = now.weekday()
            offset = (i - today_idx) % 7
            offset = offset or 7  # if it's the same day, assume next week
            day_offset = offset
            break

    candidate = _parse_time_part(text, now)
    if candidate is None:
        # No explicit time found; if a day-only phrase was given, default to 9am.
        if day_offset or repeat == "daily":
            candidate = now.replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            return None, "none"

    candidate += timedelta(days=day_offset)

    if day_offset == 0 and repeat == "none" and candidate <= now:
        # Time already passed today with no explicit day -> assume tomorrow.
        candidate += timedelta(days=1)

    return candidate, repeat
