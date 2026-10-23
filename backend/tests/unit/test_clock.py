"""Case R4: the clock of the machine always answers with its time zone."""

from __future__ import annotations

from datetime import UTC, timedelta

from app.shared.clock import SystemClock


def test_the_system_clock_answers_in_utc() -> None:
    now = SystemClock().now()

    assert now.tzinfo is UTC
    assert now.utcoffset() == timedelta(0)
