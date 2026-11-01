from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.entities.user import User
from app.domain.errors import ErrorCode, InvalidError, NotFoundError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.budgets.period_dates import checked_period_end
from app.domain.services.budgets.period_rules import check_limits_and_income, check_no_overlap
from app.domain.services.dates.local_date import local_today
from app.domain.services.transactions.movement_resolution import rounded
from app.domain.use_cases.budgets.list_budget_periods import ReadablePeriod, describe_period
from app.shared.clock import Clock


@dataclass(frozen=True)
class LimitContent:
    category_id: uuid.UUID
    limit_amount: Decimal


@dataclass(frozen=True)
class PeriodContent:
    """What the user gives a period when building or changing it (FEAT-005)."""

    period_type: PeriodType
    period_start: date
    # None in a monthly period: it is computed from its start (domain rules, § 3).
    period_end: date | None
    primary_currency: str
    estimated_income: Decimal
    limits: tuple[LimitContent, ...]


def find_user(unit_of_work: UnitOfWorkPort, user_id: uuid.UUID) -> User:
    user = unit_of_work.users.find_by_id(user_id)
    if user is None:
        raise NotFoundError(ErrorCode.NOT_FOUND)
    return user


def check_content(unit_of_work: UnitOfWorkPort, user_id: uuid.UUID, content: PeriodContent) -> None:
    """The limits, the estimated income and the currency, the last validations of the API."""
    limits = [(limit.category_id, limit.limit_amount) for limit in content.limits]
    check_limits_and_income(
        user_id,
        limits,
        unit_of_work.categories.list_by_ids({category_id for category_id, _ in limits}),
        content.estimated_income,
    )
    if not unit_of_work.currencies.exists(content.primary_currency):
        raise InvalidError(ErrorCode.CURRENCY_NOT_FOUND)


class CreateBudgetPeriod:
    """A draft of an individual period of the user, with its limits (FEAT-005, CA-1)."""

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(
        self,
        user_id: uuid.UUID,
        content: PeriodContent,
        family_group_id: uuid.UUID | None = None,
    ) -> ReadablePeriod:
        if family_group_id is not None:
            # Building a period of a group arrives with the groups, in the second version.
            raise InvalidError(ErrorCode.GROUP_PERIOD_NOT_SUPPORTED)
        with self._unit_of_work as unit_of_work:
            user = find_user(unit_of_work, user_id)
            period = BudgetPeriod(
                id=uuid.uuid4(),
                user_id=user_id,
                family_group_id=None,
                period_type=content.period_type,
                period_start=content.period_start,
                period_end=checked_period_end(
                    content.period_type, content.period_start, content.period_end
                ),
                primary_currency=content.primary_currency,
                estimated_income=content.estimated_income,
                status=PeriodStatus.DRAFT,
            )
            check_no_overlap(period, unit_of_work.budget_periods.list_owned_by(user_id, set()))
            check_content(unit_of_work, user_id, content)
            period = replace(period, estimated_income=rounded(content.estimated_income))
            unit_of_work.budget_periods.add(period)
            unit_of_work.budgets.replace_for_period(
                period.id,
                [
                    Budget(uuid.uuid4(), period.id, limit.category_id, rounded(limit.limit_amount))
                    for limit in content.limits
                ],
            )
            unit_of_work.commit()
            memberships = unit_of_work.family_groups.list_memberships(user_id)
            today = local_today(self._clock.now(), user.time_zone)
            return describe_period(unit_of_work, period, user_id, memberships, today)
