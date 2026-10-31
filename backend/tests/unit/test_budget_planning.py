"""Building and confirming a budget period (FEAT-005, docs/features/FEAT-005/spec.md).

Cases C1-05 to C1-08, C1-17 and the unit ones of C2-01 to C2-25, about the use cases: the budget
of Lucía is built in memory and the action is to create, change or confirm a period, as
POST /budget-periods, PUT /budget-periods/{period_id} and
POST /budget-periods/{period_id}/confirm do. Today is 29 October 2026.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.entities.category import Category
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.transaction import TransactionType
from app.domain.entities.user import User
from app.domain.errors import DomainError
from app.domain.use_cases.budgets.confirm_budget_period import ConfirmBudgetPeriod
from app.domain.use_cases.budgets.create_budget_period import (
    CreateBudgetPeriod,
    LimitContent,
    PeriodContent,
)
from app.domain.use_cases.budgets.update_budget_period import UpdateBudgetPeriod
from tests.support.budget_data import (
    DOLLARS,
    HEALTH,
    OPENED_AT,
    PESOS,
    SUPERMARKET,
    TRANSPORT,
    LuciaBudget,
    add_period,
    add_user,
    lucia_budget,
)
from tests.support.doubles import FixedClock

TODAY_AT_NOON = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)
OCTOBER_10 = date(2026, 10, 10)
NOVEMBER_9 = date(2026, 11, 9)
NOVEMBER_10 = date(2026, 11, 10)
DECEMBER_9 = date(2026, 12, 9)
DECEMBER_10 = date(2026, 12, 10)


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


def _casa(budget: LuciaBudget) -> tuple[User, BudgetPeriod, BudgetPeriod]:
    """Sofía, a member of "Casa" who is not its owner, and its confirmed period and its draft."""
    home = FamilyGroup(id=uuid.uuid4(), name="Casa")
    budget.unit_of_work.family_groups.add(home)
    sofia = add_user(budget.unit_of_work, "Sofía", "+000000000003")
    budget.unit_of_work.family_groups.add_membership(
        Membership(sofia.id, home.id, GroupRole.MEMBER, OPENED_AT)
    )
    confirmed = add_period(
        budget.unit_of_work, None, OCTOBER_10, NOVEMBER_9, family_group_id=home.id
    )
    draft = add_period(
        budget.unit_of_work,
        None,
        NOVEMBER_10,
        DECEMBER_9,
        family_group_id=home.id,
        status=PeriodStatus.DRAFT,
    )
    return sofia, confirmed, draft


def _assert_refused(budget: LuciaBudget, code: str, action: Callable[[], object]) -> None:
    """The use case answers with that code, and nothing is written."""
    unit_of_work = budget.unit_of_work
    before = (unit_of_work.budget_periods.writes, unit_of_work.budgets.writes, unit_of_work.commits)

    with pytest.raises(DomainError) as raised:
        action()

    assert raised.value.code == code
    assert (
        unit_of_work.budget_periods.writes,
        unit_of_work.budgets.writes,
        unit_of_work.commits,
    ) == before


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


def test_changing_or_confirming_a_period_that_does_not_exist_says_it_does_not_exist() -> None:
    # Case C2-01.
    budget = lucia_budget()
    missing = uuid.uuid4()
    content = _content(budget, NOVEMBER_10, "1500000.00", {})

    _assert_refused(
        budget,
        "not_found",
        lambda: UpdateBudgetPeriod(budget.unit_of_work, _clock()).execute(
            budget.user.id, missing, content
        ),
    )
    _assert_refused(
        budget,
        "not_found",
        lambda: ConfirmBudgetPeriod(budget.unit_of_work, _clock()).execute(budget.user.id, missing),
    )


def test_a_member_who_is_not_the_owner_neither_changes_nor_confirms_the_period_of_the_group() -> (
    None
):
    # Case C2-04.
    budget = lucia_budget()
    sofia, _, draft = _casa(budget)
    content = _content(budget, NOVEMBER_10, "1700000.00", {}, end=DECEMBER_9)

    _assert_refused(
        budget,
        "not_the_owner",
        lambda: UpdateBudgetPeriod(budget.unit_of_work, _clock()).execute(
            sofia.id, draft.id, content
        ),
    )
    _assert_refused(
        budget,
        "not_the_owner",
        lambda: ConfirmBudgetPeriod(budget.unit_of_work, _clock()).execute(sofia.id, draft.id),
    )


@pytest.mark.parametrize(
    "changed",
    [
        lambda same: replace(same, period_type=PeriodType.BIWEEKLY),
        lambda same: replace(same, period_start=date(2026, 10, 11)),
        lambda same: replace(same, period_end=date(2026, 11, 8)),
        lambda same: replace(same, primary_currency=DOLLARS),
    ],
    ids=["cadence", "start", "end", "currency"],
)
def test_in_a_confirmed_period_changing_the_cadence_the_start_the_end_or_the_currency_is_not_saved(
    changed: Callable[[PeriodContent], PeriodContent],
) -> None:
    # Case C2-07.
    budget = lucia_budget()
    same = _content(budget, OCTOBER_10, "1450000.00", {SUPERMARKET: "300000.00"}, end=NOVEMBER_9)

    _assert_refused(
        budget,
        "confirmed_period_fixed",
        lambda: UpdateBudgetPeriod(budget.unit_of_work, _clock()).execute(
            budget.user.id, budget.period.id, changed(same)
        ),
    )


def test_a_period_that_overlaps_another_of_the_same_owner_is_not_saved() -> None:
    # Case C2-09: the day after the current period ends is not an overlap.
    budget = lucia_budget()
    create = CreateBudgetPeriod(budget.unit_of_work, _clock())

    _assert_refused(
        budget,
        "budget_period_overlap",
        lambda: create.execute(
            budget.user.id, _content(budget, date(2026, 11, 1), "1500000.00", {})
        ),
    )

    created = create.execute(budget.user.id, _content(budget, NOVEMBER_10, "1500000.00", {}))
    assert _stored(budget, created.period.id).period_start == NOVEMBER_10


@pytest.mark.parametrize(
    ("code", "end", "limits"),
    [
        ("period_dates_inverted", date(2026, 11, 9), ((SUPERMARKET, "1"),)),
        ("budget_limit_not_positive", None, ((SUPERMARKET, "0"),)),
        ("budget_limit_not_positive", None, ((SUPERMARKET, "-1"),)),
        ("budget_category_repeated", None, ((SUPERMARKET, "1"), (SUPERMARKET, "2"))),
    ],
    ids=["inverted_dates", "limit_of_zero", "limit_of_minus_one", "repeated_category"],
)
def test_inverted_dates_a_limit_of_zero_or_less_and_a_repeated_category_are_not_saved(
    code: str, end: date | None, limits: tuple[tuple[str, str], ...]
) -> None:
    # Case C2-14.
    budget = lucia_budget()
    content = replace(
        _content(budget, NOVEMBER_10, "1500000.00", {}, end=end),
        limits=tuple(
            LimitContent(budget.categories[name].id, Decimal(amount)) for name, amount in limits
        ),
    )

    _assert_refused(
        budget,
        code,
        lambda: CreateBudgetPeriod(budget.unit_of_work, _clock()).execute(budget.user.id, content),
    )


def test_a_limit_on_an_income_category_is_not_saved() -> None:
    # Case C2-16: the new period goes after the draft, so that the limit is what is refused.
    budget = lucia_budget()
    draft = _november_draft(budget)
    private_classes = Category(
        id=uuid.uuid4(),
        name="Clases particulares",
        kind=TransactionType.INCOME,
        user_id=budget.user.id,
    )
    budget.unit_of_work.categories.add(private_classes)
    limit = (LimitContent(private_classes.id, Decimal("10000.00")),)

    _assert_refused(
        budget,
        "budget_category_not_expense",
        lambda: CreateBudgetPeriod(budget.unit_of_work, _clock()).execute(
            budget.user.id,
            replace(_content(budget, DECEMBER_10, "1500000.00", {}), limits=limit),
        ),
    )
    _assert_refused(
        budget,
        "budget_category_not_expense",
        lambda: UpdateBudgetPeriod(budget.unit_of_work, _clock()).execute(
            budget.user.id,
            draft.id,
            replace(_content(budget, NOVEMBER_10, "1500000.00", {}), limits=limit),
        ),
    )


def test_a_negative_estimated_income_is_not_saved_and_one_of_zero_is() -> None:
    # Case C2-18.
    budget = lucia_budget()
    create = CreateBudgetPeriod(budget.unit_of_work, _clock())

    _assert_refused(
        budget,
        "estimated_income_negative",
        lambda: create.execute(budget.user.id, _content(budget, NOVEMBER_10, "-0.01", {})),
    )

    created = create.execute(budget.user.id, _content(budget, NOVEMBER_10, "0", {}))
    assert _stored(budget, created.period.id).estimated_income == Decimal("0")


def test_with_two_errors_at_once_the_first_of_the_order_answers() -> None:
    # Case C2-25.
    budget = lucia_budget()
    sofia, confirmed, _ = _casa(budget)
    other_currency = replace(
        _content(budget, OCTOBER_10, "1450000.00", {}, end=NOVEMBER_9), primary_currency=DOLLARS
    )
    overlap_with_a_limit_of_zero = _content(
        budget, date(2026, 11, 1), "1500000.00", {SUPERMARKET: "0"}
    )

    _assert_refused(
        budget,
        "not_the_owner",
        lambda: UpdateBudgetPeriod(budget.unit_of_work, _clock()).execute(
            sofia.id, confirmed.id, other_currency
        ),
    )
    _assert_refused(
        budget,
        "budget_period_overlap",
        lambda: CreateBudgetPeriod(budget.unit_of_work, _clock()).execute(
            budget.user.id, overlap_with_a_limit_of_zero
        ),
    )
