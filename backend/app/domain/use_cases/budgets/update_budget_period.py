from __future__ import annotations

import uuid
from dataclasses import replace

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.family_group import Membership
from app.domain.entities.user import User
from app.domain.errors import ErrorCode, ForbiddenError, NotFoundError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.budgets.period_access import can_edit, can_read
from app.domain.services.budgets.period_dates import checked_period_end
from app.domain.services.budgets.period_rules import check_confirmed_stays_fixed, check_no_overlap
from app.domain.services.dates.local_date import local_today
from app.domain.use_cases.budgets.create_budget_period import (
    PeriodContent,
    check_content,
    find_user,
)
from app.domain.use_cases.budgets.list_budget_periods import ReadablePeriod, describe_period
from app.shared.clock import Clock


def editable_period(
    unit_of_work: UnitOfWorkPort,
    user: User,
    period_id: uuid.UUID,
    memberships: list[Membership],
) -> BudgetPeriod:
    """The period, if the user can change it. One they cannot read answers as one that does not
    exist; a member who is not the owner can read it, so for them it exists (CA-16)."""
    period = unit_of_work.budget_periods.find_by_id(period_id)
    if period is None or not can_read(period, user.id, memberships, user.time_zone):
        raise NotFoundError(ErrorCode.NOT_FOUND)
    if not can_edit(period, user.id, memberships):
        raise ForbiddenError(ErrorCode.NOT_THE_OWNER)
    return period


class UpdateBudgetPeriod:
    """Replaces the content of a period: its dates, currency, estimated income and limits
    (FEAT-005, CA-4 and CA-10)."""

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(
        self, user_id: uuid.UUID, period_id: uuid.UUID, content: PeriodContent
    ) -> ReadablePeriod:
        with self._unit_of_work as unit_of_work:
            user = find_user(unit_of_work, user_id)
            memberships = unit_of_work.family_groups.list_memberships(user_id)
            period = editable_period(unit_of_work, user, period_id, memberships)
            changed = replace(
                period,
                period_type=content.period_type,
                period_start=content.period_start,
                period_end=checked_period_end(
                    content.period_type, content.period_start, content.period_end
                ),
                primary_currency=content.primary_currency,
                estimated_income=content.estimated_income,
            )
            check_confirmed_stays_fixed(period, changed)
            group_ids = {period.family_group_id} if period.family_group_id is not None else set()
            check_no_overlap(changed, unit_of_work.budget_periods.list_owned_by(user_id, group_ids))
            check_content(unit_of_work, user_id, content)
            unit_of_work.budget_periods.update(changed)
            # A limit that stays keeps its id: the dashboard reads its detail by it.
            kept = {
                budget.category_id: budget.id
                for budget in unit_of_work.budgets.list_by_period(period_id)
            }
            unit_of_work.budgets.replace_for_period(
                period_id,
                [
                    Budget(
                        kept.get(limit.category_id, uuid.uuid4()),
                        period_id,
                        limit.category_id,
                        limit.limit_amount,
                    )
                    for limit in content.limits
                ],
            )
            unit_of_work.commit()
            today = local_today(self._clock.now(), user.time_zone)
            return describe_period(unit_of_work, changed, user_id, memberships, today)
