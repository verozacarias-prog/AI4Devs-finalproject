"""The template of a test user (docs/operacion.md, section 2): cases 1 to 7."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from tests.support.doubles import FixedClock, InMemoryUnitOfWork

# 12:00 in Buenos Aires on October 12.
NOON = datetime(2026, 10, 12, 15, tzinfo=UTC)


def _create(instant: datetime = NOON) -> InMemoryUnitOfWork:
    unit_of_work = InMemoryUnitOfWork()
    CreateTestUser(FixedClock(instant)).execute(
        unit_of_work, name="Lucía", phone="+000000000001", terms_version="local-seed-1"
    )
    return unit_of_work


def test_the_template_creates_a_user_who_completed_the_onboarding() -> None:
    # Case 1.
    [user] = _create().users.added

    assert user.name == "Lucía"
    assert user.whatsapp_phone == "+000000000001"
    assert user.country == "AR"
    assert user.time_zone == "America/Argentina/Buenos_Aires"
    assert user.primary_currency == "ARS"
    assert user.exchange_rate_reference == "DOLAR_MEP"
    assert user.notifications_opt_in is False
    assert user.onboarding_status == "completed"


def test_the_template_records_the_consent_with_its_version_and_the_moment_of_creation() -> None:
    # Case 2.
    [user] = _create().users.added

    assert user.terms_version == "local-seed-1"
    assert user.terms_accepted_at == NOON


def test_the_template_creates_the_four_accounts_with_their_initial_balance() -> None:
    # Case 3.
    unit_of_work = _create()
    [user] = unit_of_work.users.added
    accounts = unit_of_work.accounts.added

    assert [
        (account.name, account.type, account.currency, account.initial_balance)
        for account in accounts
    ] == [
        ("Galicia pesos", "bank_account", "ARS", Decimal("350000.00")),
        ("Mercado Pago", "digital_wallet", "ARS", Decimal("80000.00")),
        ("Efectivo", "cash", "ARS", Decimal("25000.00")),
        ("Galicia USD", "bank_account", "USD", Decimal("500.00")),
    ]
    assert all(isinstance(account.initial_balance, Decimal) for account in accounts)
    assert all(account.user_id == user.id for account in accounts)
    assert all(account.opened_at == NOON for account in accounts)


def test_the_template_creates_the_first_period_from_today_to_the_end_of_the_month() -> None:
    # Case 4. With the clock on October 12, it goes from October 12 to October 31.
    unit_of_work = _create()
    [user] = unit_of_work.users.added
    [period] = unit_of_work.budget_periods.added

    assert period.user_id == user.id
    assert period.family_group_id is None
    assert period.status == "confirmed"
    assert period.period_type == "custom"
    assert period.primary_currency == "ARS"
    assert period.estimated_income == Decimal("0")
    assert (period.period_start, period.period_end) == (date(2026, 10, 12), date(2026, 10, 31))


def test_the_first_period_is_monthly_if_the_signup_is_on_the_first_and_custom_otherwise() -> None:
    # Case C2-58.
    [first_of_the_month] = _create(datetime(2026, 11, 1, 15, tzinfo=UTC)).budget_periods.added
    [any_other_day] = _create(datetime(2026, 11, 15, 15, tzinfo=UTC)).budget_periods.added

    assert first_of_the_month.period_type == "monthly"
    assert (first_of_the_month.period_start, first_of_the_month.period_end) == (
        date(2026, 11, 1),
        date(2026, 11, 30),
    )
    assert any_other_day.period_type == "custom"
    assert (any_other_day.period_start, any_other_day.period_end) == (
        date(2026, 11, 15),
        date(2026, 11, 30),
    )


def test_today_is_the_day_in_the_time_zone_of_the_user() -> None:
    # Case 5. At 01:00 UTC of October 13 it is still 22:00 of October 12 in Buenos Aires.
    late_at_night = datetime(2026, 10, 13, 1, tzinfo=UTC)

    [period] = _create(late_at_night).budget_periods.added

    assert (period.period_start, period.period_end) == (date(2026, 10, 12), date(2026, 10, 31))


def test_the_template_creates_the_financial_profile() -> None:
    # Case 6.
    unit_of_work = _create()
    [user] = unit_of_work.users.added
    [profile] = unit_of_work.financial_profiles.added

    assert profile.user_id == user.id
    assert profile.income_range == "range_3"
    assert profile.dependents == 1
    assert profile.has_debts is False
    assert profile.emergency_fund_months == Decimal("2.0")
    assert profile.main_goal == "save"


def test_the_template_creates_nothing_else() -> None:
    # Case 7. One user, four accounts, one period and one profile: no group, and it leaves the
    # commit to whoever called it. That no category and no limit reach the database is checked
    # with the script, against the real tables.
    unit_of_work = _create()

    assert len(unit_of_work.users.added) == 1
    assert len(unit_of_work.accounts.added) == 4
    assert len(unit_of_work.budget_periods.added) == 1
    assert len(unit_of_work.financial_profiles.added) == 1
    assert unit_of_work.family_groups.added == []
    assert unit_of_work.family_groups.memberships == []
    assert unit_of_work.commits == 0
