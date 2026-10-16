"""The message worker: takes the stored messages and passes them to the use cases (ADR 0010).

It is the same code as the API with another entry point. It reaches the database only through
the use cases, and it is the single place where an error of a round becomes a log line.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from datetime import timedelta
from typing import NoReturn, TextIO

from app.adapters.observability.errors import log_error
from app.adapters.observability.events import Event, Field, LoggerName
from app.adapters.observability.logs import configure_logging, message_id_var
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import (
    MILLISECONDS_PER_SECOND,
    WORKER_IDLE_SECONDS,
    WORKER_LOCK_SECONDS,
    Environment,
    ProcessName,
)
from app.domain.entities.inbound_message import InboundMessage
from app.domain.use_cases.messages.process_next_message import ProcessNextMessage
from app.settings import Settings
from app.shared.clock import Clock, SystemClock

logger = logging.getLogger(LoggerName.WORKER)


class MessageWorker:
    def __init__(self, process_next: Callable[[], ProcessNextMessage], in_full: bool) -> None:
        self._process_next = process_next
        self._in_full = in_full

    def run_round(self) -> bool:
        """Takes and answers one message. True if there was one, so it asks again at once.

        An error ends the round and leaves its line, with the message it was processing: the
        worker goes on with the next round.
        """
        taken: list[InboundMessage] = []

        def follow(message: InboundMessage) -> None:
            taken.append(message)
            message_id_var.set(str(message.id))

        started = time.monotonic()
        try:
            worked = self._process_next().execute(on_claimed=follow)
        except Exception as error:
            # The message stays in process until its lock ends; then a worker takes it again.
            log_error(error, in_full=self._in_full)
            return False
        else:
            if taken:
                logger.info(
                    Event.MESSAGE_ANSWERED,
                    extra={
                        Field.USER_ID: _optional_id(taken[0]),
                        Field.DURATION_MS: round(
                            (time.monotonic() - started) * MILLISECONDS_PER_SECOND
                        ),
                    },
                )
            return worked
        finally:
            message_id_var.set(None)

    def run_forever(self) -> NoReturn:
        while True:
            if not self.run_round():
                time.sleep(WORKER_IDLE_SECONDS)


def _optional_id(message: InboundMessage) -> str | None:
    # A message of a number that is not a user yet has no user.
    return None if message.user_id is None else str(message.user_id)


def create_worker(
    settings: Settings, clock: Clock | None = None, log_stream: TextIO | None = None
) -> MessageWorker:
    configure_logging(log_stream or sys.stdout, settings.version, ProcessName.WORKER)
    if settings.dev_entry_enabled or settings.web_chat_enabled:
        # Said at every start, so that nobody leaves it on without knowing (ADR 0016).
        logger.warning(Event.DEV_SCAFFOLD_ENABLED)
    engine = create_db_engine(settings.database_url)
    worker_clock = clock or SystemClock()
    lock = timedelta(seconds=WORKER_LOCK_SECONDS)
    return MessageWorker(
        lambda: ProcessNextMessage(SqlAlchemyUnitOfWork(engine), worker_clock, lock),
        in_full=settings.environment is Environment.LOCAL,
    )
