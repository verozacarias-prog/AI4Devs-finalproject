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
        """The batch of the user that awaits a reply, and its pending: there is one at most.

        A batch of delivery 2 holds one pending; more than one comes with the final delivery.
        """
        ...

    def update(self, pending: PendingTransaction) -> None:
        """Stores what changed: what was understood, what is missing, its status and result."""
        ...

    def update_batch(self, batch: PendingBatch) -> None:
        """Stores whether it awaits a reply, its question and confirmation, and its status."""
        ...
