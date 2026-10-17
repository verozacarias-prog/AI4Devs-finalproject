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
from app.adapters.observability.llm_calls import RecordedLLM
from app.adapters.observability.logs import configure_logging, message_id_var, user_id_var
from app.adapters.outbound.llm_client.openai_llm import OpenAILLM
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.repositories.llm_calls import PostgresLlmCallLog
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import MILLISECONDS_PER_SECOND, WORKER_IDLE_SECONDS, Environment, ProcessName
from app.domain.entities.inbound_message import InboundMessage
from app.domain.ports.llm_port import LLMPort
from app.domain.use_cases.messages.process_next_message import ProcessNextMessage, RoundOutcome
from app.settings import Settings, require_openai_api_key
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

        def follow(message: InboundMessage) -> None:
            # Every line written while it is processed says which message and whose.
            message_id_var.set(str(message.id))
            if message.user_id is not None:
                user_id_var.set(str(message.user_id))

        started = time.monotonic()
        try:
            outcome = self._process_next().execute(on_claimed=follow)
        except Exception as error:
            # The message stays in process until its lock ends; then a worker takes it again.
            log_error(error, in_full=self._in_full)
            return False
        else:
            if outcome is RoundOutcome.ANSWERED:
                elapsed = round((time.monotonic() - started) * MILLISECONDS_PER_SECOND)
                logger.info(Event.MESSAGE_ANSWERED, extra={Field.DURATION_MS: elapsed})
            return outcome is not RoundOutcome.NOTHING_TO_TAKE
        finally:
            message_id_var.set(None)
            user_id_var.set(None)

    def run_forever(self) -> NoReturn:
        while True:
            if not self.run_round():
                time.sleep(WORKER_IDLE_SECONDS)


def create_worker(
    settings: Settings,
    clock: Clock | None = None,
    log_stream: TextIO | None = None,
    llm: LLMPort | None = None,
) -> MessageWorker:
    """Only a test passes `llm`, to replace the provider: it is wrapped all the same."""
    configure_logging(log_stream or sys.stdout, settings.version, ProcessName.WORKER)
    if settings.dev_entry_enabled or settings.web_chat_enabled:
        # Said at every start, so that nobody leaves it on without knowing (ADR 0016).
        logger.warning(Event.DEV_SCAFFOLD_ENABLED)
    model = llm or OpenAILLM(require_openai_api_key(settings))
    engine = create_db_engine(settings.database_url)
    # Every call is recorded: no entry point injects the model without its wrapper (ADR 0023).
    recorded = RecordedLLM(model, PostgresLlmCallLog(engine))
    worker_clock = clock or SystemClock()
    lock = timedelta(seconds=settings.worker_lock_seconds)
    return MessageWorker(
        lambda: ProcessNextMessage(SqlAlchemyUnitOfWork(engine), worker_clock, lock, recorded),
        in_full=settings.environment is Environment.LOCAL,
    )
