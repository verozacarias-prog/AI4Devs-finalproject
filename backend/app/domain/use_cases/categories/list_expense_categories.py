from __future__ import annotations

import uuid

from app.domain.entities.category import Category
from app.domain.entities.transaction import TransactionType
from app.domain.ports.unit_of_work_port import UnitOfWorkPort


class ListExpenseCategories:
    """The categories of expenses the user can put a limit on: the base ones and their own,
    by name, without telling capitals apart (FEAT-005, CA-12)."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, user_id: uuid.UUID) -> list[Category]:
        with self._unit_of_work as unit_of_work:
            available = unit_of_work.categories.list_available(user_id)
        return sorted(
            (category for category in available if category.kind is TransactionType.EXPENSE),
            key=lambda category: category.name.casefold(),
        )
