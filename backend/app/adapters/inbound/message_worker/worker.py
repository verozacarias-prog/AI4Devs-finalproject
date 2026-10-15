"""The message worker: takes the stored messages and passes them to the use cases (ADR 0010).

It is the same code as the API with another entry point. It reaches the database only through
the use cases, and it is the single place where an error of a round becomes a log line.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from datetime import timedelta
from typing import NoReturn, TextIO

from app.adapters.observability.errors import log_error
from app.adapters.observability.logs import configure_logging
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import WORKER_IDLE_SECONDS, WORKER_LOCK_SECONDS, Environment, ProcessName
from app.domain.use_cases.messages.process_next_message import ProcessNextMessage
from app.settings import Settings
from app.shared.clock import Clock, SystemClock


class MessageWorker:
    def __init__(self, process_next: Callable[[], ProcessNextMessage], in_full: bool) -> None:
        self._process_next = process_next
        self._in_full = in_full

    def run_round(self) -> bool:
        """Takes and answers one message. True if there was one, so it asks again at once."""
        return self._process_next().execute()

    def run_forever(self) -> NoReturn:
        while True:
            try:
                worked = self.run_round()
            except Exception as error:
                # The message stays in process until its lock ends, and is taken again then.
                log_error(error, in_full=self._in_full)
                worked = False
            if not worked:
                time.sleep(WORKER_IDLE_SECONDS)


def create_worker(
    settings: Settings, clock: Clock | None = None, log_stream: TextIO | None = None
) -> MessageWorker:
    configure_logging(log_stream or sys.stdout, settings.version, ProcessName.WORKER)
    engine = create_db_engine(settings.database_url)
    worker_clock = clock or SystemClock()
    lock = timedelta(seconds=WORKER_LOCK_SECONDS)
    return MessageWorker(
        lambda: ProcessNextMessage(SqlAlchemyUnitOfWork(engine), worker_clock, lock),
        in_full=settings.environment is Environment.LOCAL,
    )
