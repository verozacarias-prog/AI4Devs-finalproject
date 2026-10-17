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
