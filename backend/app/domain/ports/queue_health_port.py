from __future__ import annotations

from datetime import datetime
from typing import Protocol


class QueueHealthPort(Protocol):
    def is_keeping_up(self, since: datetime) -> bool:
        """False if a pending message has been due since before that moment, or if the
        database does not answer: either way, nobody can say the messages are being processed.
        Never raises."""
        ...
