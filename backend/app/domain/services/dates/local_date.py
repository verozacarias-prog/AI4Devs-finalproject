from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app import messages


def local_today(now: datetime, time_zone: str) -> date:
    """Which day it is at that instant in that time zone, given by its IANA name.

    "Today" for a user is always this, never the day of the machine (domain rules).
    """
    if now.tzinfo is None:
        # Python would silently assume the zone of the machine.
        raise ValueError(messages.NAIVE_INSTANT)
    return now.astimezone(ZoneInfo(time_zone)).date()
