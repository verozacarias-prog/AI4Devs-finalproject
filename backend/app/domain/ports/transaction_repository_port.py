from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.transaction import Transaction


class TransactionRepositoryPort(Protocol):
    def list_by_user(self, user_id: uuid.UUID) -> list[Transaction]:
        """Every movement of the user, deleted and duplicated ones included."""
        ...
