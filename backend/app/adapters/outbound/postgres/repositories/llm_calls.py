from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import Engine

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.llm_call import LlmCall


class PostgresLlmCallLog:
    """Implements LlmCallLogPort, with a connection and a transaction of its own per row.

    Outside the transaction that answers the message, so the row stays even if that one is
    undone (ADR 0023, point 5).
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(self, call: LlmCall) -> None:
        with self._engine.begin() as connection:
            execute_write(connection, queries.INSERT_LLM_CALL, asdict(call))
