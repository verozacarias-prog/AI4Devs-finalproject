"""Cases R1 to R3: which day it is for a user, in the time zone of that user."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.domain.local_date import local_today

# Half past one in the morning of March 1, in UTC.
INSTANT = datetime(2031, 3, 1, 1, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("time_zone", "today"),
    [("America/Argentina/Buenos_Aires", date(2031, 2, 28)), ("Asia/Tokyo", date(2031, 3, 1))],
    ids=["R1", "R2"],
)
def test_today_is_the_day_in_the_time_zone_of_the_user(time_zone: str, today: date) -> None:
    assert local_today(INSTANT, time_zone) == today


def test_an_instant_without_a_time_zone_is_refused() -> None:
    """Case R3."""
    with pytest.raises(ValueError, match="time zone"):
        local_today(datetime(2031, 3, 1, 1, 30), "America/Argentina/Buenos_Aires")  # noqa: DTZ001
