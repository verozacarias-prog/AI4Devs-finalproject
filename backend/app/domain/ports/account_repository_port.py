from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.account import Account


class AccountRepositoryPort(Protocol):
    def add(self, account: Account) -> None: ...

    def list_by_user(self, user_id: uuid.UUID) -> list[Account]: ...
