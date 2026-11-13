from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.entities.transaction import TransactionType


@dataclass(frozen=True)
class Category:
    """A category of expenses or of incomes: of the base catalog, or of one user."""

    id: uuid.UUID
    name: str
    kind: TransactionType
    # None for the base catalog, which every user has (domain rules, § 4).
    user_id: uuid.UUID | None
    # True only for the base catalog: the database keeps it equal to an empty user_id.
    is_base: bool
