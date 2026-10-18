from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class LlmPurpose(StrEnum):
    """Which method of the port was called (ADR 0023)."""

    CLASSIFICATION = "classification"
    INTERPRETATION = "interpretation"
    QUERY = "query"
    ADVICE = "advice"
    EMBEDDING = "embedding"


class LlmOutcome(StrEnum):
    OK = "ok"
    INVALID_OUTPUT = "invalid_output"
    BLOCKED = "blocked"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"


class OutputField(StrEnum):
    """A field of the output of a classification that may come empty (CA-34)."""

    REGISTRATION_TYPE = "registration_type"
    AMOUNT = "amount"
    ACCOUNT = "account"
    CATEGORY = "category"
    CURRENCY = "currency"
    TRANSACTION_DATE = "transaction_date"


@dataclass(frozen=True)
class LlmCall:
    """One call to the model, with what it cost and how it ended, and never its content."""

    id: uuid.UUID
    # The message being processed, if the call was born from one.
    inbound_message_id: uuid.UUID | None
    purpose: LlmPurpose
    provider: str
    model: str
    prompt_version: str | None
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int
    estimated_cost_usd: Decimal | None
    outcome: LlmOutcome
    # For a classification that is a registration, the fields of its output that came empty,
    # by their names and never with a value (CA-34). None for any other call.
    empty_fields: tuple[OutputField, ...] | None = None
