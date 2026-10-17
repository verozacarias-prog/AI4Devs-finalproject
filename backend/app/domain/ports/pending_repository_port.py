from __future__ import annotations

from typing import Protocol

from app.domain.entities.pending_transaction import PendingBatch, PendingTransaction


class PendingRepositoryPort(Protocol):
    def add_batch(self, batch: PendingBatch) -> None: ...

    def add(self, pending: PendingTransaction) -> None:
        """Its batch must be added first."""
        ...
