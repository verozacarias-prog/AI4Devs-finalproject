from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class IncomeRange(StrEnum):
    """A range code. The amounts of each range live in the configuration."""

    RANGE_1 = "range_1"
    RANGE_2 = "range_2"
    RANGE_3 = "range_3"
    RANGE_4 = "range_4"
    RANGE_5 = "range_5"


class MainGoal(StrEnum):
    SAVE = "save"
    PAY_DEBTS = "pay_debts"
    EMERGENCY_FUND = "emergency_fund"
    INVEST = "invest"


@dataclass(frozen=True)
class FinancialProfile:
    """Optional answers that let an advice use the real situation of the user."""

    user_id: uuid.UUID
    income_range: IncomeRange | None
    dependents: int | None
    has_debts: bool | None
    emergency_fund_months: Decimal | None
    main_goal: MainGoal | None
