from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.category import Category


class CategoryRepositoryPort(Protocol):
    def list_available(self, user_id: uuid.UUID) -> list[Category]:
        """The base catalog and the categories of the user, of both kinds."""
        ...
