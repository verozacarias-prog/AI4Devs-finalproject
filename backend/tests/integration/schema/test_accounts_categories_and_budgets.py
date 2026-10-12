"""Accounts, categories, budget periods, budgets and alerts: cases 22 to 38, and block D."""

from __future__ import annotations

from datetime import date

import pytest

from tests.integration.schema.names import (
    CONFIRMED,
    DOLLARS,
    DRAFT,
    INCOME,
    MONTHLY,
    OUTSIDE_THE_SET,
    Table,
)
from tests.integration.schema.rows import Rows

pytestmark = pytest.mark.integration

APRIL_START = date(2026, 4, 1)
APRIL_END = date(2026, 4, 30)


def test_the_currency_of_an_account_never_changes(rows: Rows) -> None:
    # Case 22.
    account = rows.account(rows.user())
    rows.update(Table.ACCOUNT, account, name="Otro nombre")

    with rows.rejected_by("tg_account_currency_immutable"):
        rows.update(Table.ACCOUNT, account, currency=DOLLARS)


def test_an_account_type_comes_from_a_closed_set_that_includes_receivable(rows: Rows) -> None:
    # Case 23.
    user = rows.user()
    rows.account(user, type="receivable")

    with rows.rejected_by("ck_account_type"):
        rows.account(user, type="savings")


def test_only_a_digital_wallet_says_whether_it_uses_linked_cards(rows: Rows) -> None:
    # Case 24.
    user = rows.user()
    rows.account(user, type="digital_wallet", uses_linked_cards=True)

    with rows.rejected_by("ck_account_uses_linked_cards"):
        rows.account(user, uses_linked_cards=True)


def test_a_user_has_no_two_accounts_with_the_same_name_ignoring_case(rows: Rows) -> None:
    # Case 25. Another user may use the same name.
    user = rows.user()
    rows.account(user, name="Galicia")
    rows.account(rows.user(), name="Galicia")

    with rows.rejected_by("uq_account_user_name"):
        rows.account(user, name="GALICIA")


def test_closing_and_due_days_belong_to_a_credit_card_and_only_to_it(rows: Rows) -> None:
    # Case 119.
    user = rows.user()
    rows.card(user)

    with rows.rejected_by("ck_account_card_days"):
        rows.card(user, closing_day=None)
    with rows.rejected_by("ck_account_card_days"):
        rows.card(user, due_day=None)
    with rows.rejected_by("ck_account_card_days"):
        rows.account(user, closing_day=20, due_day=5)


def test_a_user_has_no_two_categories_with_the_same_name_ignoring_case(rows: Rows) -> None:
    # Case 26.
    user = rows.user()
    rows.category(user, name="Prepaga")
    rows.category(rows.user(), name="Prepaga")

    with rows.rejected_by("uq_category_user_name"):
        rows.category(user, name="PREPAGA")


def test_the_base_catalog_has_no_two_categories_with_the_same_name(rows: Rows) -> None:
    # Case 27.
    rows.category(None, name="Base de prueba")

    with rows.rejected_by("uq_category_base_name"):
        rows.category(None, name="BASE DE PRUEBA")


def test_a_category_of_a_user_cannot_take_the_name_of_a_base_one(rows: Rows) -> None:
    # Case 28.
    user = rows.user()
    rows.category(user, name="Prepaga")

    with rows.rejected_by("tg_category_name_not_base"):
        rows.category(user, name="salud")


def test_a_category_is_of_expense_or_of_income(rows: Rows) -> None:
    # Case 133.
    user = rows.user()
    rows.category(user, kind=INCOME)

    with rows.rejected_by("ck_category_kind"):
        rows.category(user, kind="transfer")


def test_a_budget_period_belongs_to_a_user_or_to_a_group_never_to_none(rows: Rows) -> None:
    # Case 29.
    rows.period(user=rows.user())
    rows.period(group=rows.group())

    with rows.rejected_by("ck_budget_period_one_owner"):
        rows.period()


def test_a_budget_period_does_not_belong_to_a_user_and_a_group_at_once(rows: Rows) -> None:
    # Case 30.
    with rows.rejected_by("ck_budget_period_one_owner"):
        rows.period(user=rows.user(), group=rows.group())


@pytest.mark.parametrize("column", ["period_type", "status"], ids=["31", "32"])
def test_the_type_and_the_status_of_a_period_come_from_a_closed_set(
    rows: Rows, column: str
) -> None:
    # Cases 31 and 32.
    rows.period(user=rows.user(), period_type="biweekly", status=DRAFT)

    values = {"period_type": MONTHLY, "status": CONFIRMED, column: OUTSIDE_THE_SET}

    with rows.rejected_by(f"ck_budget_period_{column}"):
        rows.period(user=rows.user(), period_type=values["period_type"], status=values["status"])


def test_a_period_does_not_end_before_it_starts(rows: Rows) -> None:
    # Case 33. A period of a single day is valid.
    rows.period(user=rows.user(), period_start=date(2026, 3, 1), period_end=date(2026, 3, 1))

    with rows.rejected_by("ck_budget_period_dates"):
        rows.period(user=rows.user(), period_start=date(2026, 3, 2), period_end=date(2026, 3, 1))


def test_the_periods_of_a_user_do_not_overlap(rows: Rows) -> None:
    # Case 34. The next period starts the day after, and another user is not affected.
    user = rows.user()
    rows.period(user=user)
    rows.period(user=user, period_start=APRIL_START, period_end=APRIL_END)
    rows.period(user=rows.user())

    with rows.rejected_by("ex_budget_period_user_overlap"):
        rows.period(user=user, period_start=date(2026, 3, 31), period_end=date(2026, 3, 31))


def test_the_periods_of_a_group_do_not_overlap(rows: Rows) -> None:
    # Case 35.
    group = rows.group()
    rows.period(group=group)
    rows.period(group=group, period_start=APRIL_START, period_end=APRIL_END)

    with rows.rejected_by("ex_budget_period_group_overlap"):
        rows.period(group=group, period_start=date(2026, 3, 15), period_end=date(2026, 4, 14))


def test_the_currency_of_a_confirmed_period_does_not_change(rows: Rows) -> None:
    # Case 36. While it is a draft it can.
    user = rows.user()
    confirmed = rows.period(user=user)
    draft = rows.period(user=user, status=DRAFT, period_start=APRIL_START, period_end=APRIL_END)
    rows.update(Table.BUDGET_PERIOD, draft, primary_currency=DOLLARS)

    with rows.rejected_by("tg_budget_period_currency_fixed"):
        rows.update(Table.BUDGET_PERIOD, confirmed, primary_currency=DOLLARS)


def test_a_period_with_movements_does_not_go_back_to_draft(rows: Rows) -> None:
    # Case 37. One without movements can.
    empty = rows.period(user=rows.user())
    rows.update(Table.BUDGET_PERIOD, empty, status=DRAFT)
    home = rows.home()
    rows.transaction(home)

    with rows.rejected_by("tg_budget_period_draft_with_transactions"):
        rows.update(Table.BUDGET_PERIOD, home.period, status=DRAFT)


def test_a_period_has_one_limit_per_category(rows: Rows) -> None:
    # Case 38.
    home = rows.home()
    rows.budget(home.period, home.category)
    rows.budget(home.period, rows.category(home.user))

    with rows.rejected_by("uq_budget_period_category"):
        rows.budget(home.period, home.category)


def test_each_recipient_gets_one_alert_per_threshold_of_a_budget(rows: Rows) -> None:
    # Case 105. Another threshold, or another recipient, is another alert.
    home = rows.home()
    budget = rows.budget(home.period, home.category)
    message = rows.outbound(home.user)
    rows.sent_alert(budget, home.user, message)
    rows.sent_alert(budget, home.user, message, threshold=100)
    rows.sent_alert(budget, rows.user(), message)

    with rows.rejected_by("uq_sent_alert_budget_threshold_user"):
        rows.sent_alert(budget, home.user, message)


@pytest.mark.parametrize("threshold", [0, 101])
def test_an_alert_threshold_is_a_percentage_from_1_to_100(rows: Rows, threshold: int) -> None:
    # Case 130.
    home = rows.home()
    budget = rows.budget(home.period, home.category)
    message = rows.outbound(home.user)
    rows.sent_alert(budget, home.user, message, threshold=100)

    with rows.rejected_by("ck_sent_alert_threshold"):
        rows.sent_alert(budget, home.user, message, threshold=threshold)
