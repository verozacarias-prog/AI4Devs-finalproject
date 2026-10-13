from __future__ import annotations

from typing import Protocol

from app.domain.entities.user import User


class UserRepositoryPort(Protocol):
    def add(self, user: User) -> None: ...

    def find_by_phone(self, phone: str) -> User | None: ...
