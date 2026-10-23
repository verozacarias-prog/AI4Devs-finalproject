from __future__ import annotations

import uuid
from datetime import date
from typing import Protocol

from app.domain.entities.budget_period import BudgetPeriod


class BudgetPeriodRepositoryPort(Protocol):
    def add(self, period: BudgetPeriod) -> None: ...

    def list_covering(self, user_id: uuid.UUID, day: date) -> list[BudgetPeriod]:
        """The periods that day can go to: the user's own and those of the groups they are in.

        Drafts included: whether a period is confirmed is for the use case to weigh.
        """
        ...

    def confirm(self, period_id: uuid.UUID) -> None:
        """A draft becomes confirmed, as it is: nothing else of it changes (domain rules, § 3)."""
        ...
