"""The summary of a budget period (FEAT-004, docs/features/FEAT-004/spec.md).

Cases C1-12 to C1-15, the unit ones about the whole period: the data is built in memory and
the action is to read the summary, as GET /budget-periods/{period_id}/summary does. The budget
of Lucía is the one of tests/support/budget_data.py.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.use_cases.budgets.get_period_summary import (
    CategorySpending,
    GetPeriodSummary,
    PeriodSummary,
)
from tests.support.budget_data import (
    EATING_OUT,
    HEALTH,
    OTHER_INCOME,
    SALARY,
    SUPERMARKET,
    TRANSPORT,
    LuciaBudget,
    lucia_budget,
)

OCTOBER_12 = date(2026, 10, 12)
OCTOBER_15 = date(2026, 10, 15)
OCTOBER_20 = date(2026, 10, 20)


def _summary(budget: LuciaBudget) -> PeriodSummary:
    return GetPeriodSummary(budget.unit_of_work).execute(budget.user.id, budget.period.id)


def _category(summary: PeriodSummary, name: str) -> CategorySpending:
    return next(category for category in summary.categories if category.category == name)


def test_a_category_without_a_limit_has_no_percentage() -> None:
    # Case C1-12.
    budget = lucia_budget()
    budget.expense(EATING_OUT, "38500.00", OCTOBER_12)

    eating_out = _category(_summary(budget), EATING_OUT)

    assert eating_out.spent_amount == Decimal("38500.00")
    assert eating_out.limit_amount is None
    assert eating_out.budget_id is None
    assert eating_out.used_percentage is None


def test_the_actual_income_does_not_count_refunds() -> None:
    # Case C1-13: 1.200.000 + 100 × 1.200, without the refund.
    budget = lucia_budget()
    budget.income(SALARY, "1200000.00", OCTOBER_12)
    budget.income(OTHER_INCOME, "100.00", OCTOBER_15, account=budget.dollars, exchange_rate="1200")
    expense = budget.expense(SUPERMARKET, "100000.00", OCTOBER_12)
    budget.refund(expense, "30000.00", OCTOBER_20)

    summary = _summary(budget)

    assert summary.actual_income == Decimal("1320000.00")
    assert summary.estimated_income == Decimal("1450000.00")


def test_which_categories_the_summary_brings_and_in_what_order() -> None:
    # Case C1-14: the ones with a limit always, the ones without only with movements, by name
    # without telling capitals apart.
    budget = lucia_budget()
    budget.own_category("café")
    budget.expense(HEALTH, "8000.00", OCTOBER_12)
    budget.expense("café", "5000.00", OCTOBER_12)

    categories = _summary(budget).categories

    assert [
        (category.category, category.spent_amount, category.limit_amount, category.used_percentage)
        for category in categories
    ] == [
        ("café", Decimal("5000.00"), None, None),
        (HEALTH, Decimal("8000.00"), None, None),
        (SUPERMARKET, Decimal("0"), Decimal("300000.00"), Decimal("0.0")),
        (TRANSPORT, Decimal("0"), Decimal("80000.00"), Decimal("0.0")),
    ]


def test_the_total_spent_adds_the_categories_net_of_refunds() -> None:
    # Case C1-15: 70.000 + 12.000 + 8.000.
    budget = lucia_budget()
    expense = budget.expense(SUPERMARKET, "100000.00", OCTOBER_12)
    budget.refund(expense, "30000.00", OCTOBER_20)
    budget.expense(TRANSPORT, "12000.00", OCTOBER_12)
    budget.expense(HEALTH, "8000.00", OCTOBER_12)

    assert _summary(budget).total_spent == Decimal("90000.00")
