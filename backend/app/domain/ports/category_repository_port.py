from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.category import Category


class CategoryRepositoryPort(Protocol):
    def add(self, category: Category) -> None:
        """A category of a user, which the user confirmed (domain rules, § 4)."""
        ...

    def list_available(self, user_id: uuid.UUID) -> list[Category]:
        """The base catalog and the categories of the user, of both kinds."""
        ...
