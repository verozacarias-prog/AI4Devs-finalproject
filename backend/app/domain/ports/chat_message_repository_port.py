from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.chat_message import ChatMessage


class ChatMessageRepositoryPort(Protocol):
    def contains(self, user_id: uuid.UUID, message_id: uuid.UUID) -> bool:
        """Whether that message is in the web chat of the user, and not purged."""
        ...

    def list_by_user(self, user_id: uuid.UUID, after: uuid.UUID | None) -> list[ChatMessage]:
        """The web chat of the user, in order: what the user wrote and what Platita replied.

        With `after`, only the messages that come after that one. Without the purged ones.
        """
        ...
