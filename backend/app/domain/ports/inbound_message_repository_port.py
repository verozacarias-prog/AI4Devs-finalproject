from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.entities.inbound_message import InboundMessage


class InboundMessageRepositoryPort(Protocol):
    def add(self, message: InboundMessage) -> None: ...

    def find_web(self, provider_message_id: str) -> InboundMessage | None:
        """The message of the web chat stored under that identifier, if any."""
        ...

    def claim_next(self, now: datetime, locked_until: datetime) -> InboundMessage | None:
        """Takes the next message to process, if any, and leaves it in process until then.

        A message is available when it is pending, or in process with its lock ended: the
        worker that took it fell. It is the earliest available message of a sender that has no
        message in process with its lock in force. Two workers never take the same one.
        """
        ...

    def any_pending_waiting_since(self, since: datetime) -> bool:
        """Whether a pending message has been due to be processed since before that moment."""
        ...

    def mark_processed(self, message_id: uuid.UUID, attempts: int, at: datetime) -> bool:
        """Marks it processed only if it is still in process by the claim with those attempts.

        False when another worker took it after that claim: then nothing of this one may be
        written (ADR 0010).
        """
        ...
