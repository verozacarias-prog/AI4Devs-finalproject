from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class PeriodType(StrEnum):
    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"


class PeriodStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class BudgetPeriod:
    """The budget of a month or a fortnight. It belongs to a user or to a group, never both."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    family_group_id: uuid.UUID | None
    period_type: PeriodType
    period_start: date
    period_end: date
    primary_currency: str
    estimated_income: Decimal
    status: PeriodStatus


def first_period(
    *,
    user_id: uuid.UUID | None = None,
    family_group_id: uuid.UUID | None = None,
    currency: str,
    today: date,
) -> BudgetPeriod:
    """The period a user or a group is born with (domain rules, § 3 and § 10).

    Already confirmed, because it already started: monthly, with no estimated income and no
    limits, from today to the last day of this month.
    """
    last_day = calendar.monthrange(today.year, today.month)[1]
    return BudgetPeriod(
        id=uuid.uuid4(),
        user_id=user_id,
        family_group_id=family_group_id,
        period_type=PeriodType.MONTHLY,
        period_start=today,
        period_end=today.replace(day=last_day),
        primary_currency=currency,
        estimated_income=Decimal("0"),
        status=PeriodStatus.CONFIRMED,
    )
