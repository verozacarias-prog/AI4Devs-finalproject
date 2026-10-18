from __future__ import annotations

import uuid
from datetime import date
from typing import Protocol

from app.domain.entities.llm_usage import UsageCounter


class LlmUsageRepositoryPort(Protocol):
    def count(self, user_id: uuid.UUID, day: date, counter: UsageCounter) -> int:
        """How many the user used that day, their own day: zero if none yet."""
        ...

    def add(
        self,
        user_id: uuid.UUID,
        day: date,
        counter: UsageCounter,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """One more that day, with the tokens it took, in the transaction of the message."""
        ...
