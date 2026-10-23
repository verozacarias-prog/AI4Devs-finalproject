"""The clock. A use case receives one when it is built and never reads the time on its own,
which is what lets a test fix the instant (ADR 0001)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """The current instant, always with its time zone."""
        ...


class SystemClock:
    """The clock of the machine."""

    def now(self) -> datetime:
        return datetime.now(UTC)
