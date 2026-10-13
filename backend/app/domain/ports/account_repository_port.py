from __future__ import annotations

from typing import Protocol

from app.domain.entities.account import Account


class AccountRepositoryPort(Protocol):
    def add(self, account: Account) -> None: ...
