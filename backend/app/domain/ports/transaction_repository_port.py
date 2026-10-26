from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.transaction import Transaction


class TransactionRepositoryPort(Protocol):
    def add(self, transaction: Transaction) -> None:
        """A new movement, with its period, its category and its source."""
        ...

    def list_by_user(self, user_id: uuid.UUID) -> list[Transaction]:
        """Every movement of the user, deleted and duplicated ones included."""
        ...

    def list_by_period(self, period_id: uuid.UUID) -> list[Transaction]:
        """Every movement imputed to the period, by any user, deleted and duplicated included."""
        ...

    def list_by_ids(self, transaction_ids: set[uuid.UUID]) -> list[Transaction]:
        """Those movements, deleted and duplicated ones included."""
        ...
