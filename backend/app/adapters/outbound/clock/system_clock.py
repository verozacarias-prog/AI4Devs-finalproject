from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Implements ClockPort with the clock of the machine."""

    def now(self) -> datetime:
        return datetime.now(UTC)
