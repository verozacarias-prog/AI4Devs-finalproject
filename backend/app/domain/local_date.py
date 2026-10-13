from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

NAIVE_INSTANT = "An instant needs its time zone to say which day it is"


def local_today(now: datetime, time_zone: str) -> date:
    """Which day it is at that instant in that time zone, given by its IANA name.

    "Today" for a user is always this, never the day of the machine (domain rules).
    """
    if now.tzinfo is None:
        # Python would silently assume the zone of the machine.
        raise ValueError(NAIVE_INSTANT)
    return now.astimezone(ZoneInfo(time_zone)).date()
