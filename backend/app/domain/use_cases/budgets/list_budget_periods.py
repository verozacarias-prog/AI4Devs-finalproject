from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.errors import ErrorCode, NotFoundError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.budgets.period_access import can_edit, can_read, covers
from app.domain.services.dates.local_date import local_today
from app.shared.clock import Clock


@dataclass(frozen=True)
class BudgetLimit:
    budget: Budget
    category: str


@dataclass(frozen=True)
class ReadablePeriod:
    period: BudgetPeriod
    # None in an individual period: the name tells the budgets apart (domain rules, § 10).
    family_group_name: str | None
    can_edit: bool
    # Whether it covers today, in the time zone of the user.
    is_current: bool
    budgets: list[BudgetLimit]


class ListBudgetPeriods:
    """The periods the user can read, with their limits and the one that covers today marked.

    The one that starts latest first, and with the same start the individual one before those
    of groups, by name. The limits by category name, without telling capitals apart
    (FEAT-004, CA-5).
    """

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, user_id: uuid.UUID) -> list[ReadablePeriod]:
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            if user is None:
                raise NotFoundError(ErrorCode.NOT_FOUND)
            memberships = unit_of_work.family_groups.list_memberships(user_id)
            owned = unit_of_work.budget_periods.list_owned_by(
                user_id, {membership.family_group_id for membership in memberships}
            )
            periods = [
                period for period in owned if can_read(period, user_id, memberships, user.time_zone)
            ]
            group_names: dict[uuid.UUID, str] = {}
            for period in periods:
                if period.family_group_id is not None:
                    group = unit_of_work.family_groups.find_by_id(period.family_group_id)
                    if group is not None:
                        group_names[group.id] = group.name
            budgets = {
                period.id: unit_of_work.budgets.list_by_period(period.id) for period in periods
            }
            category_ids = {budget.category_id for listed in budgets.values() for budget in listed}
            category_names = {
                category.id: category.name
                for category in unit_of_work.categories.list_by_ids(category_ids)
            }
        today = local_today(self._clock.now(), user.time_zone)
        readable = [
            ReadablePeriod(
                period=period,
                family_group_name=(
                    group_names.get(period.family_group_id)
                    if period.family_group_id is not None
                    else None
                ),
                can_edit=can_edit(period, user_id, memberships),
                is_current=covers(period, today),
                budgets=sorted(
                    (
                        BudgetLimit(budget, category_names[budget.category_id])
                        for budget in budgets[period.id]
                    ),
                    key=lambda limit: limit.category.casefold(),
                ),
            )
            for period in periods
        ]
        readable.sort(key=lambda item: (item.family_group_name or "").casefold())
        readable.sort(key=lambda item: item.period.family_group_id is not None)
        readable.sort(key=lambda item: item.period.period_start, reverse=True)
        return readable
