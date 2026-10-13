from __future__ import annotations

from typing import Protocol

from app.domain.entities.budget_period import BudgetPeriod


class BudgetPeriodRepository(Protocol):
    def add(self, period: BudgetPeriod) -> None: ...
