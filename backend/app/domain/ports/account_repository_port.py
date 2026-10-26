from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.account import Account


class AccountRepositoryPort(Protocol):
    def add(self, account: Account) -> None: ...

    def list_by_user(self, user_id: uuid.UUID) -> list[Account]: ...

    def list_by_ids(self, account_ids: set[uuid.UUID]) -> list[Account]:
        """Those accounts, whoever they belong to: a group period has those of its members."""
        ...
