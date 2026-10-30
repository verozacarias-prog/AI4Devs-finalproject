"""Building and confirming a budget period (FEAT-005, docs/features/FEAT-005/spec.md).

Cases C1-05 to C1-08 and C1-17, the unit ones about the use cases: the budget of Lucía is built
in memory and the action is to create, change or confirm a period, as POST /budget-periods,
PUT /budget-periods/{period_id} and POST /budget-periods/{period_id}/confirm do. Today is
29 October 2026.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.use_cases.budgets.confirm_budget_period import ConfirmBudgetPeriod
from app.domain.use_cases.budgets.create_budget_period import (
    CreateBudgetPeriod,
    LimitContent,
    PeriodContent,
)
from app.domain.use_cases.budgets.update_budget_period import UpdateBudgetPeriod
from tests.support.budget_data import (
    HEALTH,
    PESOS,
    SUPERMARKET,
    TRANSPORT,
    LuciaBudget,
    add_period,
    lucia_budget,
)
from tests.support.doubles import FixedClock

TODAY_AT_NOON = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)
NOVEMBER_10 = date(2026, 11, 10)
DECEMBER_9 = date(2026, 12, 9)


def _clock() -> FixedClock:
    return FixedClock(TODAY_AT_NOON)


def _limits(budget: LuciaBudget, period_id: uuid.UUID) -> set[tuple[str, Decimal]]:
    names = {category.id: name for name, category in budget.categories.items()}
    return {
        (names[limit.category_id], limit.limit_amount)
        for limit in budget.unit_of_work.budgets.list_by_period(period_id)
    }


def _stored(budget: LuciaBudget, period_id: uuid.UUID) -> BudgetPeriod:
    found = budget.unit_of_work.budget_periods.find_by_id(period_id)
    assert found is not None
    return found


def _content(
    budget: LuciaBudget,
    start: date,
    income: str,
    limits: dict[str, str],
    *,
    end: date | None = None,
) -> PeriodContent:
    return PeriodContent(
        period_type=PeriodType.MONTHLY,
        period_start=start,
        period_end=end,
        primary_currency=PESOS,
        estimated_income=Decimal(income),
        limits=tuple(
            LimitContent(category_id=budget.categories[name].id, limit_amount=Decimal(amount))
            for name, amount in limits.items()
        ),
    )


def _november_draft(budget: LuciaBudget) -> BudgetPeriod:
    """The draft of Lucía from 10 November to 9 December, with its two limits."""
    draft = add_period(
        budget.unit_of_work,
        budget.user.id,
        NOVEMBER_10,
        DECEMBER_9,
        status=PeriodStatus.DRAFT,
        estimated_income="1500000.00",
    )
    for name, amount in ((SUPERMARKET, "320000.00"), (TRANSPORT, "90000.00")):
        budget.unit_of_work.budgets.add(
            Budget(
                id=uuid.uuid4(),
                budget_period_id=draft.id,
                category_id=budget.categories[name].id,
                limit_amount=Decimal(amount),
            )
        )
    return draft


def test_creating_leaves_a_draft_of_the_user_with_its_limits() -> None:
    # Case C1-05.
    budget = lucia_budget()
    content = _content(
        budget,
        NOVEMBER_10,
        "1500000.00",
        {SUPERMARKET: "320000.00", TRANSPORT: "90000.00"},
    )

    CreateBudgetPeriod(budget.unit_of_work, _clock()).execute(budget.user.id, content)

    created = [
        period
        for period in budget.unit_of_work.budget_periods.added
        if period.id != budget.period.id
    ]
    assert len(created) == 1
    period = created[0]
    assert period.status is PeriodStatus.DRAFT
    assert period.user_id == budget.user.id
    assert period.family_group_id is None
    assert period.period_type is PeriodType.MONTHLY
    assert (period.period_start, period.period_end) == (NOVEMBER_10, DECEMBER_9)
    assert period.primary_currency == PESOS
    assert period.estimated_income == Decimal("1500000.00")
    assert _limits(budget, period.id) == {
        (SUPERMARKET, Decimal("320000.00")),
        (TRANSPORT, Decimal("90000.00")),
    }


def test_changing_a_draft_replaces_its_whole_content() -> None:
    # Case C1-06: Transporte no longer has a limit, and Salud has one.
    budget = lucia_budget()
    draft = _november_draft(budget)
    content = _content(
        budget,
        date(2026, 11, 15),
        "1600000.00",
        {SUPERMARKET: "350000.00", HEALTH: "50000.00"},
    )

    UpdateBudgetPeriod(budget.unit_of_work, _clock()).execute(budget.user.id, draft.id, content)

    changed = _stored(budget, draft.id)
    assert changed.status is PeriodStatus.DRAFT
    assert (changed.period_start, changed.period_end) == (date(2026, 11, 15), date(2026, 12, 14))
    assert changed.estimated_income == Decimal("1600000.00")
    assert _limits(budget, draft.id) == {
        (SUPERMARKET, Decimal("350000.00")),
        (HEALTH, Decimal("50000.00")),
    }


def test_confirming_a_draft_changes_nothing_else_of_it() -> None:
    # Case C1-07.
    budget = lucia_budget()
    draft = _november_draft(budget)

    ConfirmBudgetPeriod(budget.unit_of_work, _clock()).execute(budget.user.id, draft.id)

    confirmed = _stored(budget, draft.id)
    assert confirmed.status is PeriodStatus.CONFIRMED
    assert (confirmed.period_start, confirmed.period_end) == (NOVEMBER_10, DECEMBER_9)
    assert confirmed.primary_currency == PESOS
    assert confirmed.estimated_income == Decimal("1500000.00")
    assert _limits(budget, draft.id) == {
        (SUPERMARKET, Decimal("320000.00")),
        (TRANSPORT, Decimal("90000.00")),
    }


def test_confirming_one_already_confirmed_writes_nothing() -> None:
    # Case C1-08.
    budget = lucia_budget()
    periods = budget.unit_of_work.budget_periods
    limits = budget.unit_of_work.budgets
    writes_before = (periods.writes, limits.writes)

    ConfirmBudgetPeriod(budget.unit_of_work, _clock()).execute(budget.user.id, budget.period.id)

    assert (periods.writes, limits.writes) == writes_before
    assert budget.unit_of_work.commits == 0
    assert _stored(budget, budget.period.id) == budget.period


def test_changing_a_confirmed_one_changes_its_income_and_its_limits_and_nothing_else() -> None:
    # Case C1-17: the same dates and the same currency; Transporte no longer has a limit.
    budget = lucia_budget()
    content = _content(
        budget,
        date(2026, 10, 10),
        "1520000.00",
        {SUPERMARKET: "310000.00", HEALTH: "40000.00"},
        end=date(2026, 11, 9),
    )

    UpdateBudgetPeriod(budget.unit_of_work, _clock()).execute(
        budget.user.id, budget.period.id, content
    )

    changed = _stored(budget, budget.period.id)
    assert changed.status is PeriodStatus.CONFIRMED
    assert (changed.period_start, changed.period_end) == (date(2026, 10, 10), date(2026, 11, 9))
    assert changed.primary_currency == PESOS
    assert changed.estimated_income == Decimal("1520000.00")
    assert _limits(budget, budget.period.id) == {
        (SUPERMARKET, Decimal("310000.00")),
        (HEALTH, Decimal("40000.00")),
    }
