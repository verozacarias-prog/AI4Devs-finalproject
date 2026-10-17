from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class MessageClass(StrEnum):
    """What a message asks for: the first thing the model decides (ADR 0018)."""

    REGISTRATION = "registration"
    QUERY = "query"
    ADVICE = "advice"
    # A greeting, or anything the model cannot place: it gets a request for details.
    NONE = "none"


class RegistrationType(StrEnum):
    """What a registration wants to register. Only an expense and an income have code yet."""

    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    CARD_PURCHASE = "card_purchase"
    RECURRING_RULE = "recurring_rule"
    # A correction, a deletion or a restoration of a movement already confirmed.
    CHANGE = "change"


@dataclass(frozen=True)
class ClassificationRequest:
    """What the model gets to classify a message: the task data and no identifier (ADR 0013)."""

    text: str
    accounts: tuple[str, ...]
    expense_categories: tuple[str, ...]
    income_categories: tuple[str, ...]
    # The day the user wrote, in their time zone: what "today" and "ayer" mean.
    today: date


@dataclass(frozen=True)
class ModelUsage:
    """What a call to the model cost, as the provider reports it. It never holds content."""

    provider: str
    model: str
    prompt_version: str
    # None when the provider did not report them.
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class Classification:
    """What the model understood of a message. Names are as the model wrote them."""

    message_class: MessageClass
    registration_type: RegistrationType | None = None
    amount: Decimal | None = None
    # How the message names the account, in its own words: the code decides which it is.
    account: str | None = None
    category: str | None = None
    # Only when the message says it, as "pesos", "lucas" or "dólares": an ISO code.
    currency: str | None = None
    # Only when the message says which day; otherwise it is the day the user wrote.
    transaction_date: date | None = None
    usage: ModelUsage | None = None
    # The row the call left in LLM_CALL, once the wrapper recorded it (ADR 0023).
    call_id: uuid.UUID | None = None
