from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.llm_usage import UsageCounter


class PostgresLlmUsageRepository:
    """Implements LlmUsageRepositoryPort: the daily counters of each user in LLM_USAGE."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def count(self, user_id: uuid.UUID, day: date, counter: UsageCounter) -> int:
        found: int | None = self._connection.execute(
            text(queries.SELECT_LLM_USAGE_COUNT),
            {"user_id": user_id, "day": day, "counter": counter},
        ).scalar_one_or_none()
        return found or 0

    def add(
        self,
        user_id: uuid.UUID,
        day: date,
        counter: UsageCounter,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        execute_write(
            self._connection,
            queries.ADD_LLM_USAGE,
            {
                "user_id": user_id,
                "day": day,
                "counter": counter,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )
