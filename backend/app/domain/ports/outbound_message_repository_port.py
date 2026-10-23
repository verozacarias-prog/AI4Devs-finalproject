from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.entities.outbound_message import OutboundMessage


class OutboundMessageRepositoryPort(Protocol):
    def add(self, message: OutboundMessage) -> None: ...

    def exists_for_user(self, message_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Whether that message of Platita went to that user."""
        ...

    def sent_since(self, user_id: uuid.UUID, text: str, since: datetime) -> bool:
        """Whether Platita sent that text to that user from that moment on."""
        ...
