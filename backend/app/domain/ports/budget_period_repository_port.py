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

    def find_by_id(self, period_id: uuid.UUID) -> BudgetPeriod | None:
        """The period, whoever it belongs to: whether the user may read it is for the use case."""
        ...

    def list_owned_by(self, user_id: uuid.UUID, group_ids: set[uuid.UUID]) -> list[BudgetPeriod]:
        """The individual periods of the user and every period of those groups."""
        ...

    def confirm(self, period_id: uuid.UUID) -> None:
        """A draft becomes confirmed, as it is: nothing else of it changes (domain rules, § 3)."""
        ...
