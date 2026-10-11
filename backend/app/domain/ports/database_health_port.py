from __future__ import annotations

from typing import Protocol


class DatabaseHealthPort(Protocol):
    def is_reachable(self) -> bool:
        """Whether the database answers right now. Never raises."""
        ...
