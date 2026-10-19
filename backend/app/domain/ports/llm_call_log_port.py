from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.llm_call import LlmCall


class LlmCallLogPort(Protocol):
    def record(self, call: LlmCall) -> None:
        """Stores the row in a short transaction of its own (ADR 0023).

        It stays even if the transaction that answers the message is undone: the call cost
        the same.
        """
        ...

    def mark_blocked(self, call_id: uuid.UUID) -> None:
        """The validation rejected what the call returned (ADR 0023, point 6).

        In a short transaction of its own too, so it stays whatever happens to the message.
        """
        ...
