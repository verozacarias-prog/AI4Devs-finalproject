from __future__ import annotations

import uuid
from dataclasses import replace

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.budgets.period_dates import period_end
from app.domain.services.dates.local_date import local_today
from app.domain.use_cases.budgets.create_budget_period import PeriodContent, find_user
from app.domain.use_cases.budgets.list_budget_periods import ReadablePeriod, describe_period
from app.shared.clock import Clock


def stored_period(unit_of_work: UnitOfWorkPort, period_id: uuid.UUID) -> BudgetPeriod:
    """The period with that id. Who may change it, and the 404 of one that is not there, are
    of the second cut (FEAT-005)."""
    period = unit_of_work.budget_periods.find_by_id(period_id)
    if period is None:
        raise ValueError
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
            period = stored_period(unit_of_work, period_id)
            changed = replace(
                period,
                period_type=content.period_type,
                period_start=content.period_start,
                period_end=period_end(
                    content.period_type, content.period_start, content.period_end
                ),
                primary_currency=content.primary_currency,
                estimated_income=content.estimated_income,
            )
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
