from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.budget import Budget


class BudgetRepositoryPort(Protocol):
    def list_by_period(self, period_id: uuid.UUID) -> list[Budget]:
        """The limits of that period, one per category that has one."""
        ...

    def find_by_id(self, budget_id: uuid.UUID) -> Budget | None:
        """The limit, whoever its period belongs to."""
        ...
