from __future__ import annotations

import logging

from sqlalchemy import Engine, text

from app.adapters.observability.events import Event, Field, LoggerName
from app.adapters.outbound.postgres.queries import PING

logger = logging.getLogger(LoggerName.POSTGRES)


class PostgresDatabaseHealth:
    """Implements DatabaseHealthPort with a trivial query."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_reachable(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text(PING))
        except Exception as error:  # the port promises never to raise
            # Only the class: the message of a connection error carries the database URL.
            logger.warning(
                Event.DATABASE_UNREACHABLE, extra={Field.ERROR_TYPE: type(error).__name__}
            )
            return False
        return True
