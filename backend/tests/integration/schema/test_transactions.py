"""TRANSACTION: cases 39 to 62, and cases 134 and 136."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tests.integration.schema.names import (
    AUTOMATIC,
    DOLLARS,
    DRAFT,
    EUROS,
    EXPENSE,
    INCOME,
    OUTSIDE_THE_SET,
    OWNER,
    PESOS_PER_DOLLAR,
)
from tests.integration.schema.rows import MOVEMENT_DATE, Home, Rows

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "column", ["account_id", "budget_period_id", "category_id"], ids=["39", "40", "134"]
)
def test_a_movement_always_has_account_period_and_category(rows: Rows, column: str) -> None:
    # Cases 39, 40 and 134.
    home = rows.home()
    rows.transaction(home)

    with rows.rejected_null(column):
        rows.transaction(home, **{column: None})


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("-3500.00")])
def test_the_amount_of_a_movement_is_positive(rows: Rows, amount: Decimal) -> None:
    # Case 41.
    home = rows.home()
    rows.transaction(home, amount=Decimal("0.01"))

    with rows.rejected_by("ck_transaction_amount"):
        rows.transaction(home, amount=amount)


@pytest.mark.parametrize("column", ["type", "source"], ids=["42", "43"])
def test_the_type_and_the_source_of_a_movement_come_from_a_closed_set(
    rows: Rows, column: str
) -> None:
    # Cases 42 and 43.
    home = rows.home()
    rows.transaction(home, source=AUTOMATIC)

    with rows.rejected_by(f"ck_transaction_{column}"):
        rows.transaction(home, **{column: OUTSIDE_THE_SET})


def test_a_movement_is_not_charged_to_a_draft_period(rows: Rows) -> None:
    # Case 44.
    home = rows.home()
    rows.transaction(home)
    draft = rows.period(
        user=home.user,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        status=DRAFT,
    )

    with rows.rejected_by("tg_transaction_period_confirmed"):
        rows.transaction(home, budget_period_id=draft)


def test_a_movement_does_not_use_the_account_of_another_user(rows: Rows) -> None:
    # Case 45.
    home = rows.home()
    rows.transaction(home)
    foreign = rows.account(rows.user())

    with rows.rejected_by("fk_transaction_account_user"):
        rows.transaction(home, account_id=foreign)


def test_a_broker_account_takes_no_movements(rows: Rows) -> None:
    # Case 46.
    home = rows.home()
    rows.transaction(home)
    broker = rows.account(home.user, type="broker")

    with rows.rejected_by("tg_transaction_broker_account"):
        rows.transaction(home, account_id=broker)


def test_the_category_of_a_movement_is_of_its_same_type(rows: Rows) -> None:
    # Case 47.
    home = rows.home()
    income = rows.category(home.user, kind=INCOME)
    rows.transaction(home, type=INCOME, category_id=income)

    with rows.rejected_by("fk_transaction_category_kind"):
        rows.transaction(home, category_id=income)


def test_a_movement_is_not_dated_before_its_account_was_opened(rows: Rows) -> None:
    # Case 48. The opening day is counted in the time zone of the user: 01:00 UTC of January 1
    # is still December 31 in Buenos Aires.
    home = rows.home()
    opened_at_night = rows.account(home.user, created_at=datetime(2026, 1, 1, 1, tzinfo=UTC))
    rows.transaction(home, account_id=opened_at_night, transaction_date=date(2025, 12, 31))

    with rows.rejected_by("tg_transaction_before_account"):
        rows.transaction(home, account_id=opened_at_night, transaction_date=date(2025, 12, 30))


@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("-1200")])
def test_the_exchange_rate_of_a_movement_is_positive(rows: Rows, rate: Decimal) -> None:
    # Case 49.
    home = rows.home()
    rows.transaction(home, currency=DOLLARS, exchange_rate=PESOS_PER_DOLLAR)

    with rows.rejected_by("ck_transaction_exchange_rate"):
        rows.transaction(home, currency=DOLLARS, exchange_rate=rate)


def test_a_movement_in_another_currency_needs_its_exchange_rate(rows: Rows) -> None:
    # Case 50.
    home = rows.home()
    rows.transaction(home, currency=DOLLARS, exchange_rate=PESOS_PER_DOLLAR)

    with rows.rejected_by("tg_transaction_rate_missing"):
        rows.transaction(home, currency=DOLLARS)


def test_a_movement_whose_three_currencies_match_carries_no_exchange_rate(rows: Rows) -> None:
    # Case 51.
    home = rows.home()
    rows.transaction(home)

    with rows.rejected_by("tg_transaction_rate_unexpected"):
        rows.transaction(home, exchange_rate=Decimal("1"))


def test_a_movement_does_not_involve_three_different_currencies(rows: Rows) -> None:
    # Case 52. The movement, its account and its period: at most two currencies.
    home = rows.home()
    dollars = rows.account(home.user, currency=DOLLARS)
    rows.transaction(home, account_id=dollars, currency=DOLLARS, exchange_rate=PESOS_PER_DOLLAR)

    with rows.rejected_by("tg_transaction_three_currencies"):
        rows.transaction(home, account_id=dollars, currency=EUROS, exchange_rate=Decimal("1300"))


def test_duplicate_of_points_to_a_movement_of_the_same_user(rows: Rows) -> None:
    # Case 53.
    home, other = rows.home(), rows.home()
    rows.transaction(home, duplicate_of=rows.transaction(home))
    foreign = rows.transaction(other)

    with rows.rejected_by("fk_transaction_duplicate_of"):
        rows.transaction(home, duplicate_of=foreign)


def _income(rows: Rows, home: Home, **overrides: object) -> uuid.UUID:
    category = rows.category(home.user, kind=INCOME)
    return rows.transaction(home, **{"type": INCOME, "category_id": category, **overrides})


def test_only_an_income_refunds_another_movement(rows: Rows) -> None:
    # Case 54.
    home = rows.home()
    expense = rows.transaction(home)
    _income(rows, home, refund_of=expense)

    with rows.rejected_by("ck_transaction_refund_only_income"):
        rows.transaction(home, refund_of=expense)


def test_a_refund_points_to_an_expense(rows: Rows) -> None:
    # Case 55.
    home = rows.home()
    _income(rows, home, refund_of=rows.transaction(home))
    income = _income(rows, home)

    with rows.rejected_by("tg_transaction_refund_target"):
        _income(rows, home, refund_of=income)


def test_a_refund_points_to_a_movement_of_the_same_user(rows: Rows) -> None:
    # Case 56.
    home, other = rows.home(), rows.home()
    _income(rows, home, refund_of=rows.transaction(home))
    foreign = rows.transaction(other)

    with rows.rejected_by("fk_transaction_refund_of"):
        _income(rows, home, refund_of=foreign)


@dataclass(frozen=True)
class PairSetting:
    """A user who owns a group: one confirmed period of the group and one individual."""

    home: Home
    group_period: uuid.UUID
    income_category: uuid.UUID


@pytest.fixture
def setting(rows: Rows) -> PairSetting:
    home = rows.home()
    group = rows.group()
    rows.membership(home.user, group, role=OWNER)
    return PairSetting(
        home=home,
        group_period=rows.period(group=group),
        income_category=rows.category(home.user, kind=INCOME),
    )


def _pair(
    rows: Rows,
    setting: PairSetting,
    expense: dict[str, object] | None = None,
    income: dict[str, object] | None = None,
) -> None:
    """A withdrawal: an expense in the group period and an income in the individual one."""
    expense_id, income_id = uuid.uuid4(), uuid.uuid4()
    first: dict[str, object] = {
        "id": expense_id,
        "paired_with": income_id,
        "budget_period_id": setting.group_period,
        **(expense or {}),
    }
    second: dict[str, object] = {
        "id": income_id,
        "paired_with": expense_id,
        "type": INCOME,
        "category_id": setting.income_category,
        **(income or {}),
    }
    rows.transaction(setting.home, **first)
    rows.transaction(setting.home, **second)


PAIR_MISMATCHES: dict[str, tuple[dict[str, object], dict[str, object]]] = {
    "amount": ({}, {"amount": Decimal("1.00")}),
    "date": ({}, {"transaction_date": date(2026, 3, 11)}),
    "currency and rate": ({"currency": DOLLARS, "exchange_rate": PESOS_PER_DOLLAR}, {}),
}


@pytest.mark.parametrize("difference", list(PAIR_MISMATCHES))
def test_the_two_halves_of_a_pair_share_amount_currency_date_and_rate(
    rows: Rows, setting: PairSetting, difference: str
) -> None:
    # Case 57. The halves are inserted together and checked at the commit.
    _pair(rows, setting)
    rows.check_deferred()
    expense, income = PAIR_MISMATCHES[difference]

    with rows.rejected_by("tg_transaction_pair_mismatch"):
        _pair(rows, setting, expense, income)


def test_a_pair_is_an_expense_and_an_income(rows: Rows, setting: PairSetting) -> None:
    # Case 58.
    _pair(rows, setting)
    rows.check_deferred()
    second_expense: dict[str, object] = {
        "type": EXPENSE,
        "category_id": setting.home.category,
    }

    with rows.rejected_by("tg_transaction_pair_types"):
        _pair(rows, setting, income=second_expense)


def test_a_pair_has_one_half_in_a_group_period_and_the_other_in_the_individual(
    rows: Rows, setting: PairSetting
) -> None:
    # Case 59. The contribution, the opposite direction, is as valid as the withdrawal.
    _pair(
        rows,
        setting,
        expense={"budget_period_id": setting.home.period},
        income={"budget_period_id": setting.group_period},
    )
    rows.check_deferred()

    with rows.rejected_by("tg_transaction_pair_periods"):
        _pair(rows, setting, expense={"budget_period_id": setting.home.period})
    with rows.rejected_by("tg_transaction_pair_periods"):
        _pair(rows, setting, income={"budget_period_id": setting.group_period})


def test_each_half_of_a_pair_points_to_the_other(rows: Rows, setting: PairSetting) -> None:
    # Case 136.
    _pair(rows, setting)
    rows.check_deferred()
    income = rows.transaction(setting.home, type=INCOME, category_id=setting.income_category)

    with rows.rejected_by("tg_transaction_pair_mutual"):
        rows.transaction(setting.home, budget_period_id=setting.group_period, paired_with=income)


def _occurrence(rule: uuid.UUID, day: date = MOVEMENT_DATE) -> dict[str, object]:
    return {"recurring_rule_id": rule, "occurrence_date": day, "source": AUTOMATIC}


def test_a_recurring_rule_generates_one_movement_per_occurrence(rows: Rows) -> None:
    # Case 60. Movements that come from no rule do not collide with each other.
    home = rows.home()
    rule = rows.rule(home)
    rows.transaction(home)
    rows.transaction(home)
    rows.transaction(home, **_occurrence(rule))
    rows.transaction(home, **_occurrence(rule, date(2026, 4, 10)))

    with rows.rejected_by("uq_transaction_rule_occurrence"):
        rows.transaction(home, **_occurrence(rule))


def test_a_movement_has_a_rule_and_an_occurrence_date_or_neither(rows: Rows) -> None:
    # Case 61.
    home = rows.home()
    rule = rows.rule(home)
    rows.transaction(home, **_occurrence(rule))

    with rows.rejected_by("ck_transaction_rule_occurrence_together"):
        rows.transaction(home, recurring_rule_id=rule, source=AUTOMATIC)
    with rows.rejected_by("ck_transaction_rule_occurrence_together"):
        rows.transaction(home, occurrence_date=MOVEMENT_DATE, source=AUTOMATIC)


def test_a_repeated_dashboard_request_does_not_create_a_second_movement(rows: Rows) -> None:
    # Case 62. The same key from another user is another request.
    home, other = rows.home(), rows.home()
    key = uuid.uuid4()
    rows.transaction(home, client_request_id=key)
    rows.transaction(other, client_request_id=key)

    with rows.rejected_by("uq_transaction_user_client_request"):
        rows.transaction(home, client_request_id=key)
