from __future__ import annotations

from datetime import date, datetime, time, timedelta
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


def start_of_next_day(now: datetime, time_zone: str) -> datetime:
    """The first instant of the day after `now`, in that time zone: when a user's day renews."""
    zone = ZoneInfo(time_zone)
    tomorrow = local_today(now, time_zone) + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=zone)


def start_of_day(now: datetime, time_zone: str) -> datetime:
    """The first instant of the day of `now`, in that time zone."""
    return datetime.combine(local_today(now, time_zone), time.min, tzinfo=ZoneInfo(time_zone))
