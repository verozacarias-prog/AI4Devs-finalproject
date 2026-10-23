from __future__ import annotations

from app.domain.ports.database_health_port import DatabaseHealthPort


class CheckReadiness:
    """Whether the process can serve requests: today, whether it reaches the database."""

    def __init__(self, database: DatabaseHealthPort) -> None:
        self._database = database

    def execute(self) -> bool:
        return self._database.is_reachable()
