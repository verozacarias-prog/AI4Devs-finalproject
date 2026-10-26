"""Which budget period covers today (FEAT-004, docs/features/FEAT-004/spec.md).

Cases C1-16 to C1-18, the unit ones about the list of periods: the data is built in memory and
the action is to list the periods the user can read, as GET /budget-periods does. "Today" is
the day of the user, in their time zone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.use_cases.budgets.list_budget_periods import ListBudgetPeriods, ReadablePeriod
from tests.support.budget_data import OPENED_AT, TODAY_AT_NOON, add_period, add_user
from tests.support.doubles import FixedClock, InMemoryUnitOfWork

SEPTEMBER = (date(2026, 9, 10), date(2026, 10, 9))
OCTOBER = (date(2026, 10, 10), date(2026, 11, 9))
NOVEMBER = (date(2026, 11, 10), date(2026, 12, 9))


def _current(listed: list[ReadablePeriod]) -> list[BudgetPeriod]:
    return [item.period for item in listed if item.is_current]


def _lucia_with_three_periods() -> tuple[InMemoryUnitOfWork, uuid.UUID, BudgetPeriod]:
    unit_of_work = InMemoryUnitOfWork()
    lucia = add_user(unit_of_work, "Lucía", "+000000000001")
    add_period(unit_of_work, lucia.id, *SEPTEMBER)
    october = add_period(unit_of_work, lucia.id, *OCTOBER)
    add_period(unit_of_work, lucia.id, *NOVEMBER, status=PeriodStatus.DRAFT)
    return unit_of_work, lucia.id, october


def test_the_period_that_covers_today_comes_marked() -> None:
    # Case C1-16: today is 25 October.
    unit_of_work, lucia, october = _lucia_with_three_periods()

    listed = ListBudgetPeriods(unit_of_work, FixedClock(TODAY_AT_NOON)).execute(lucia)

    assert len(listed) == 3
    assert _current(listed) == [october]


def test_today_is_the_day_of_the_user_not_of_the_server() -> None:
    # Case C1-17: 10 November at 01:00 UTC is 9 November at 22:00 in Buenos Aires, the last
    # day of the October period.
    unit_of_work, lucia, october = _lucia_with_three_periods()
    late_on_the_ninth = datetime(2026, 11, 10, 1, 0, tzinfo=UTC)

    listed = ListBudgetPeriods(unit_of_work, FixedClock(late_on_the_ninth)).execute(lucia)

    assert _current(listed) == [october]


def test_with_a_group_one_period_is_marked_for_each_owner() -> None:
    # Case C1-18: one is his own and the other one is of the group.
    unit_of_work = InMemoryUnitOfWork()
    pablo = add_user(unit_of_work, "Pablo", "+000000000002")
    home = FamilyGroup(id=uuid.uuid4(), name="Casa")
    unit_of_work.family_groups.add(home)
    unit_of_work.family_groups.add_membership(
        Membership(pablo.id, home.id, GroupRole.OWNER, OPENED_AT)
    )
    own = add_period(unit_of_work, pablo.id, *OCTOBER)
    of_home = add_period(
        unit_of_work, None, date(2026, 10, 1), date(2026, 10, 31), family_group_id=home.id
    )

    listed = ListBudgetPeriods(unit_of_work, FixedClock(TODAY_AT_NOON)).execute(pablo.id)

    assert sorted(period.id for period in _current(listed)) == sorted([own.id, of_home.id])
