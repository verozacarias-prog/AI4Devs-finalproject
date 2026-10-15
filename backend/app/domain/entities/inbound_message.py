from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

# Between the user and the key the browser generated, in the identifier of a web message.
WEB_MESSAGE_ID_SEPARATOR = ":"


class Provider(StrEnum):
    """The channel a message came in by, or goes out by."""

    META = "meta"
    TWILIO = "twilio"
    # The chat of the dashboard, for development and demonstration (ADR 0002).
    WEB = "web"


class InboundStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass(frozen=True)
class InboundMessage:
    """A message a person wrote to Platita, stored before it is processed (ADR 0010).

    It is at once the work of the worker and the record of what came in by the channel.
    """

    id: uuid.UUID
    provider: Provider
    provider_message_id: str
    # None while the sender is not a registered user; never on the web chat.
    user_id: uuid.UUID | None
    from_phone: str
    text: str
    # The reply of Platita the user quoted, if any.
    quoted_outbound_message_id: uuid.UUID | None
    # When the provider says it was sent; on the web chat, when the server received it. It
    # orders the messages of one sender.
    sent_at: datetime
    status: InboundStatus
    # Set by every claim: the claim that took it last is the only one that may complete it.
    attempts: int
    locked_until: datetime | None
    processed_at: datetime | None


def web_message_id(user_id: uuid.UUID, idempotency_key: str) -> str:
    """The user goes first, so a key the browser repeats is unique for that user only."""
    return f"{user_id}{WEB_MESSAGE_ID_SEPARATOR}{idempotency_key}"
