from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.entities.outbound_message import ResponseKind


class Direction(StrEnum):
    """Who wrote a message of the conversation: the user, or Platita."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass(frozen=True)
class ChatMessage:
    """One message of the conversation of the web chat, as the dashboard shows it."""

    id: uuid.UUID
    direction: Direction
    text: str
    # Only a message of the user quotes; only a reply of Platita has a kind.
    quoted_message_id: uuid.UUID | None
    response_kind: ResponseKind | None
    # When it was received or written. It orders the conversation.
    created_at: datetime
