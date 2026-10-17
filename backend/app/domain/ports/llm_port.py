from __future__ import annotations

from typing import Protocol

from app.domain.entities.classification import Classification, ClassificationRequest


class LLMPort(Protocol):
    """The language model. It never reaches the database and never writes (ADR 0013)."""

    def classify(self, request: ClassificationRequest) -> Classification:
        """Which class the message is and, for a registration, what to register (ADR 0018)."""
        ...
