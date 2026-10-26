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

    def list_by_ids(self, category_ids: set[uuid.UUID]) -> list[Category]:
        """Those categories, whoever they belong to: a group period has those of its members."""
        ...
