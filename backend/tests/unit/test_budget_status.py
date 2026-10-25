"""How much a category with a limit has spent in a period (FEAT-004, docs/features/FEAT-004).

Cases C1-01 to C1-11, the unit ones about one limit: the data is built in memory and the action
is to read the status of the limit, as GET /budgets/{budget_id} does. The budget of Lucía is the
one of tests/support/budget_data.py.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.use_cases.budgets.get_budget_status import BudgetStatus, GetBudgetStatus
from tests.support.budget_data import (
    DELETED_AT,
    PESOS,
    SUPERMARKET,
    TRANSPORT,
    LuciaBudget,
    lucia_budget,
)

SEPTEMBER_20 = date(2026, 9, 20)
OCTOBER_5 = date(2026, 10, 5)
OCTOBER_12 = date(2026, 10, 12)
OCTOBER_15 = date(2026, 10, 15)
OCTOBER_18 = date(2026, 10, 18)
OCTOBER_20 = date(2026, 10, 20)


def _status(budget: LuciaBudget, category: str = SUPERMARKET) -> BudgetStatus:
    return GetBudgetStatus(budget.unit_of_work).execute(budget.user.id, budget.limits[category].id)


def test_what_is_spent_adds_the_expenses_of_the_category() -> None:
    # Case C1-01: 154.500 + 60.000, and 214.500 / 300.000 × 100.
    budget = lucia_budget()
    budget.expense(SUPERMARKET, "154500.00", OCTOBER_12)
    budget.expense(SUPERMARKET, "60000.00", OCTOBER_18)

    status = _status(budget)

    assert status.spent_amount == Decimal("214500.00")
    assert status.used_percentage == Decimal("71.5")


def test_an_expense_in_dollars_weighs_converted() -> None:
    # Case C1-02: 50 × 1.200.
    budget = lucia_budget()
    budget.expense(SUPERMARKET, "50.00", OCTOBER_18, account=budget.dollars, exchange_rate="1200")

    status = _status(budget)

    assert status.primary_currency == PESOS
    assert status.spent_amount == Decimal("60000.00")


def test_each_expense_is_rounded_before_adding() -> None:
    # Case C1-03: 10,01 × 1.234,5678 = 12.358,023678 → 12.358,02, twice. Adding first would
    # give 24.716,05.
    budget = lucia_budget()
    for _ in range(2):
        budget.expense(
            SUPERMARKET, "10.01", OCTOBER_18, account=budget.dollars, exchange_rate="1234.5678"
        )

    assert _status(budget).spent_amount == Decimal("24716.04")


def test_an_expense_in_pesos_with_an_account_in_dollars_weighs_its_amount() -> None:
    # Case C1-04: the rate converted the debit to the account, not to the budget.
    budget = lucia_budget()
    budget.expense(
        SUPERMARKET,
        "50000.00",
        OCTOBER_18,
        account=budget.dollars,
        currency=PESOS,
        exchange_rate="0.0008333333",
    )

    assert _status(budget).spent_amount == Decimal("50000.00")


def test_a_refund_subtracts_in_the_period_it_arrives() -> None:
    # Case C1-05: 100.000 − 30.000, and 70.000 / 300.000 × 100 = 23,33…
    budget = lucia_budget()
    expense = budget.expense(SUPERMARKET, "100000.00", OCTOBER_12)
    budget.refund(expense, "30000.00", OCTOBER_20)

    status = _status(budget)

    assert status.spent_amount == Decimal("70000.00")
    assert status.used_percentage == Decimal("23.3")


def test_the_refund_of_an_earlier_expense_can_leave_what_is_spent_negative() -> None:
    # Case C1-06: −20.000, and −20.000 / 300.000 × 100 = −6,66…
    budget = lucia_budget()
    september = budget.other_period(date(2026, 9, 10), date(2026, 10, 9))
    expense = budget.expense(SUPERMARKET, "45000.00", SEPTEMBER_20, period=september)
    budget.refund(expense, "20000.00", OCTOBER_15)

    status = _status(budget)

    assert status.spent_amount == Decimal("-20000.00")
    assert status.used_percentage == Decimal("-6.7")


def test_what_is_deleted_neither_adds_nor_subtracts() -> None:
    # Case C1-07.
    budget = lucia_budget()
    expense = budget.expense(SUPERMARKET, "100000.00", OCTOBER_12)
    budget.expense(SUPERMARKET, "40000.00", OCTOBER_12, deleted_at=DELETED_AT)
    budget.refund(expense, "10000.00", OCTOBER_15, deleted_at=DELETED_AT)

    assert _status(budget).spent_amount == Decimal("100000.00")


def test_a_duplicated_expense_adds_only_once() -> None:
    # Case C1-08.
    budget = lucia_budget()
    original = budget.expense(SUPERMARKET, "25000.00", OCTOBER_12)
    budget.expense(SUPERMARKET, "25000.00", OCTOBER_12, duplicate_of=original.id)

    assert _status(budget).spent_amount == Decimal("25000.00")


def test_an_expense_of_another_category_or_another_period_does_not_add() -> None:
    # Case C1-09.
    budget = lucia_budget()
    september = budget.other_period(date(2026, 9, 10), date(2026, 10, 9))
    budget.expense(SUPERMARKET, "30000.00", OCTOBER_12)
    budget.expense(TRANSPORT, "12000.00", OCTOBER_12)
    budget.expense(SUPERMARKET, "50000.00", OCTOBER_5, period=september)

    assert _status(budget).spent_amount == Decimal("30000.00")


def test_the_percentage_is_rounded_to_one_decimal() -> None:
    # Case C1-10: 100.000 / 300.000 × 100 = 33,33…, without going through a float.
    budget = lucia_budget()
    budget.expense(SUPERMARKET, "100000.00", OCTOBER_12)

    percentage = _status(budget).used_percentage

    assert isinstance(percentage, Decimal)
    assert percentage == Decimal("33.3")


def test_the_half_is_rounded_up_and_it_can_go_past_one_hundred() -> None:
    # Case C1-11: 80.040 / 80.000 × 100 = 100,05, and the half goes up. Rounding to even
    # would give 100,0.
    budget = lucia_budget()
    budget.expense(TRANSPORT, "80040.00", OCTOBER_12)

    assert _status(budget, TRANSPORT).used_percentage == Decimal("100.1")
