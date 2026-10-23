from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.entities.inbound_message import Provider


class OutboundStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ResponseKind(StrEnum):
    """What kind of reply a message was (docs/03-modelo-de-datos.md, OUTBOUND_MESSAGE)."""

    REGISTRATION = "registration"
    QUERY = "query"
    ADVICE_INFORMATION = "advice_information"
    ADVICE_EDUCATION = "advice_education"
    ADVICE_DECISION = "advice_decision"
    ADVICE_LIMIT_EXPLAINED = "advice_limit_explained"
    ADVICE_LIMIT_FIXED = "advice_limit_fixed"
    FIXED_TEXT = "fixed_text"
    PROACTIVE = "proactive"


@dataclass(frozen=True)
class OutboundMessage:
    """A message Platita sends. It is written in the same transaction as what caused it.

    A reply goes out by the channel of the message it answers: on the web chat it is born
    sent, and the dashboard reads it.
    """

    id: uuid.UUID
    provider: Provider
    user_id: uuid.UUID | None
    to_phone: str
    # The message it answers; None for an alert or a reminder.
    inbound_message_id: uuid.UUID | None
    text: str
    response_kind: ResponseKind
    status: OutboundStatus
    sent_at: datetime | None
    created_at: datetime


def reply_to(
    message_id: uuid.UUID,
    provider: Provider,
    user_id: uuid.UUID | None,
    phone: str,
    text: str,
    response_kind: ResponseKind,
    now: datetime,
) -> OutboundMessage:
    """A reply to a message, by its channel. One for the web chat has nothing left to send."""
    on_web = provider is Provider.WEB
    return OutboundMessage(
        id=uuid.uuid4(),
        provider=provider,
        user_id=user_id,
        to_phone=phone,
        inbound_message_id=message_id,
        text=text,
        response_kind=response_kind,
        status=OutboundStatus.SENT if on_web else OutboundStatus.PENDING,
        sent_at=now if on_web else None,
        created_at=now,
    )
