from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.pending_transaction import PendingBatch, PendingTransaction


class PendingRepositoryPort(Protocol):
    def add_batch(self, batch: PendingBatch) -> None: ...

    def add(self, pending: PendingTransaction) -> None:
        """Its batch must be added first."""
        ...

    def find_awaiting_reply(
        self, user_id: uuid.UUID
    ) -> tuple[PendingBatch, PendingTransaction] | None:
        """The batch of the user that awaits a reply, and its first open pending: there is one
        batch at most.
        """
        ...

    def list_in_batch(self, batch_id: uuid.UUID, user_id: uuid.UUID) -> list[PendingTransaction]:
        """Every pending of the batch of that user, whatever its status, by position; none if
        the batch is of another user (FEAT-007, CA-23).
        """
        ...

    def update(self, pending: PendingTransaction) -> None:
        """Stores what changed: what was understood, what is missing, its status and result."""
        ...

    def update_batch(self, batch: PendingBatch) -> None:
        """Stores whether it awaits a reply, its question and confirmation, and its status."""
        ...
