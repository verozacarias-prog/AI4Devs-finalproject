from __future__ import annotations

import uuid

from app.domain.entities.budget_period import PeriodStatus
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.dates.local_date import local_today
from app.domain.use_cases.budgets.create_budget_period import find_user
from app.domain.use_cases.budgets.list_budget_periods import ReadablePeriod, describe_period
from app.domain.use_cases.budgets.update_budget_period import editable_period
from app.shared.clock import Clock


class ConfirmBudgetPeriod:
    """A draft becomes confirmed, and nothing else of it changes. One already confirmed
    answers the same, without writing anything (FEAT-005, CA-7 and CA-9)."""

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, user_id: uuid.UUID, period_id: uuid.UUID) -> ReadablePeriod:
        with self._unit_of_work as unit_of_work:
            user = find_user(unit_of_work, user_id)
            memberships = unit_of_work.family_groups.list_memberships(user_id)
            period = editable_period(unit_of_work, user, period_id, memberships)
            if period.status is PeriodStatus.DRAFT:
                unit_of_work.budget_periods.confirm(period_id)
                unit_of_work.commit()
                period = editable_period(unit_of_work, user, period_id, memberships)
            today = local_today(self._clock.now(), user.time_zone)
            return describe_period(unit_of_work, period, user_id, memberships, today)
