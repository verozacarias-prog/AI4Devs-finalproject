from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PendingSource(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class BatchStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class PendingStatus(StrEnum):
    OPEN = "open"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PendingIntent(StrEnum):
    """What a pending becomes once complete."""

    TRANSACTION = "transaction"
    TRANSFER = "transfer"
    RECURRING_RULE = "recurring_rule"
    CHANGE = "change"


@dataclass(frozen=True)
class PendingBatch:
    """The unit of conversation: the pendings the assistant asks about, or confirmed, together.

    A movement that arrives complete is a batch of one, closed at once with its confirmation,
    so quoting that confirmation finds the movement (domain rules, § 5).
    """

    id: uuid.UUID
    user_id: uuid.UUID
    source: PendingSource
    awaiting_reply: bool
    question_message_id: uuid.UUID | None
    confirmation_message_id: uuid.UUID | None
    status: BatchStatus
    created_at: datetime


@dataclass(frozen=True)
class PendingTransaction:
    """What was interpreted of one movement, until it is promoted, rejected or expires."""

    id: uuid.UUID
    user_id: uuid.UUID
    intent: PendingIntent
    # What was understood so far, as text: amounts never go through float.
    parsed_data: Mapping[str, str | None]
    missing_fields: tuple[str, ...]
    source: PendingSource
    batch_id: uuid.UUID
    # The number the user sees inside the batch, from 1 to 10.
    position: int
    resulting_transaction_id: uuid.UUID | None
    status: PendingStatus
    resolved_by: uuid.UUID | None
    expires_at: datetime | None
    created_at: datetime
    # How many fields the model had interpreted the user changed before it was confirmed: it
    # changes nothing the user sees, and only the quality metric reads it (domain rules, § 5).
    corrected_fields_count: int = 0
