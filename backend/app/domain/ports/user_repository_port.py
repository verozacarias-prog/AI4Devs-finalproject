from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.user import User


class UserRepositoryPort(Protocol):
    def add(self, user: User) -> None: ...

    def find_by_phone(self, phone: str) -> User | None: ...

    def find_by_id(self, user_id: uuid.UUID) -> User | None: ...

    def list_by_phone_prefix(self, prefix: str) -> list[User]:
        """The users whose phone starts like that, ordered by name."""
        ...
