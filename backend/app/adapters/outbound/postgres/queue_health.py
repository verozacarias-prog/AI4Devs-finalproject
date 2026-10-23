from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import Engine, text

from app.adapters.observability.events import Event, Field, LoggerName
from app.adapters.outbound.postgres.queries import INBOUND_MESSAGE_WAITING_SINCE_EXISTS

logger = logging.getLogger(LoggerName.POSTGRES)


class PostgresQueueHealth:
    """Implements QueueHealthPort by reading the inbound table."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_keeping_up(self, since: datetime) -> bool:
        try:
            with self._engine.connect() as connection:
                waiting = connection.execute(
                    text(INBOUND_MESSAGE_WAITING_SINCE_EXISTS), {"since": since}
                ).scalar_one()
        except Exception as error:  # the port promises never to raise
            # Only the class: the message of a connection error carries the database URL.
            logger.warning(
                Event.DATABASE_UNREACHABLE, extra={Field.ERROR_TYPE: type(error).__name__}
            )
            return False
        return not waiting
