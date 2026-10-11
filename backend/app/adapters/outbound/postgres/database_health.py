from __future__ import annotations

import logging

from sqlalchemy import Engine, text

from app.adapters.outbound.observability.logs import LOGGER_NAME

logger = logging.getLogger(f"{LOGGER_NAME}.postgres")


class PostgresDatabaseHealth:
    """Implements DatabaseHealthPort with a trivial query."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_reachable(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as error:  # the port promises never to raise
            # Only the class: the message of a connection error carries the database URL.
            logger.warning("database.unreachable", extra={"error_type": type(error).__name__})
            return False
        return True
