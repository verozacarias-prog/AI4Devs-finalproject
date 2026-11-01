"""The group of the local test data (docs/operacion.md, section 2): case 8."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.constants import Environment
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from app.domain.use_cases.test_data.seed_test_data import SeedTestData
from tests.support.doubles import FixedClock, InMemoryUnitOfWork

# 12:00 in Buenos Aires on October 12.
NOON = datetime(2026, 10, 12, 15, tzinfo=UTC)


def test_the_group_has_its_owner_its_member_and_its_first_confirmed_period() -> None:
    # Case 8.
    unit_of_work = InMemoryUnitOfWork()
    clock = FixedClock(NOON)

    SeedTestData(unit_of_work, clock, CreateTestUser(clock), Environment.LOCAL).execute()

    users = {user.name: user for user in unit_of_work.users.added}
    [group] = unit_of_work.family_groups.added
    assert group.name == "Casa"
    assert {
        (membership.user_id, membership.role, membership.joined_at)
        for membership in unit_of_work.family_groups.memberships
        if membership.family_group_id == group.id
    } == {
        (users["Pablo"].id, "owner", NOON),
        (users["Sofía"].id, "member", NOON),
    }
    [period] = [
        period for period in unit_of_work.budget_periods.added if period.family_group_id == group.id
    ]
    assert period.user_id is None
    assert period.status == "confirmed"
    assert period.period_type == "custom"
    assert period.primary_currency == users["Pablo"].primary_currency
    assert period.estimated_income == Decimal("0")
    assert (period.period_start, period.period_end) == (date(2026, 10, 12), date(2026, 10, 31))
