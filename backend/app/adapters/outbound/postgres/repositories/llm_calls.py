from __future__ import annotations

import uuid
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
        parameters = asdict(call)
        if call.empty_fields is not None:
            parameters["empty_fields"] = [str(field) for field in call.empty_fields]
        with self._engine.begin() as connection:
            execute_write(connection, queries.INSERT_LLM_CALL, parameters)

    def mark_blocked(self, call_id: uuid.UUID) -> None:
        with self._engine.begin() as connection:
            execute_write(connection, queries.MARK_LLM_CALL_BLOCKED, {"call_id": call_id})
