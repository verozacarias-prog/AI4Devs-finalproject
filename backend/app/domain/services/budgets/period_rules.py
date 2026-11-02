"""What the content of a budget period has to meet to be saved (docs/04-api.md)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from decimal import Decimal

from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.entities.category import Category
from app.domain.entities.transaction import TransactionType
from app.domain.errors import ConflictError, ContextField, ErrorCode, InvalidError, NotFoundError
from app.domain.services.budgets.period_dates import check_dates_can_be_compared

# Amounts are stored rounded to cents, half up, in NUMERIC(20,2): what rounds to 0 is not a limit,
# and what rounds to 10^18 does not fit (docs/03-modelo-de-datos.md).
_SMALLEST_LIMIT = Decimal("0.005")
_TOO_LARGE = Decimal("999999999999999999.995")


def check_confirmed_stays_fixed(
    stored: BudgetPeriod,
    *,
    period_type: PeriodType,
    period_start: date,
    indicated_end: date | None,
    primary_currency: str,
) -> None:
    """A confirmed period changes only its estimated income and its limits (CA-10). An end that
    was not given is not a change: it is the one of its cadence."""
    if stored.status is not PeriodStatus.CONFIRMED:
        return
    check_dates_can_be_compared(period_type, period_start, indicated_end)
    if (period_type, period_start, primary_currency) != (
        stored.period_type,
        stored.period_start,
        stored.primary_currency,
    ) or indicated_end not in (None, stored.period_end):
        raise ConflictError(ErrorCode.CONFIRMED_PERIOD_FIXED)


def check_no_overlap(period: BudgetPeriod, others: Iterable[BudgetPeriod]) -> None:
    """The periods of one owner do not overlap: a user and a group are different owners."""
    for other in others:
        if (
            other.id != period.id
            and (other.user_id, other.family_group_id) == (period.user_id, period.family_group_id)
            and other.period_start <= period.period_end
            and period.period_start <= other.period_end
        ):
            raise ConflictError(ErrorCode.BUDGET_PERIOD_OVERLAP)


def check_limits_and_income(
    user_id: uuid.UUID,
    limits: Sequence[tuple[uuid.UUID, Decimal]],
    found_categories: Iterable[Category],
    estimated_income: Decimal,
) -> None:
    """In the order of the API: a category that is not of the user answers as one that does not
    exist, before anything is said about the amounts."""
    categories = {category.id: category for category in found_categories}
    _check_categories_are_of_the_user(user_id, limits, categories)
    _check_limits_are_positive(limits)
    _check_categories_do_not_repeat(limits)
    _check_categories_are_of_expense(limits, categories)
    if estimated_income < 0:
        raise InvalidError(ErrorCode.ESTIMATED_INCOME_NEGATIVE)
    if estimated_income >= _TOO_LARGE:
        raise InvalidError(ErrorCode.AMOUNT_TOO_LARGE)
    _check_limits_fit(limits)


def _check_categories_are_of_the_user(
    user_id: uuid.UUID,
    limits: Sequence[tuple[uuid.UUID, Decimal]],
    categories: Mapping[uuid.UUID, Category],
) -> None:
    for category_id, _ in limits:
        category = categories.get(category_id)
        if category is None or category.user_id not in (None, user_id):
            raise NotFoundError(
                ErrorCode.NOT_FOUND, context={ContextField.CATEGORY_ID: category_id}
            )


def _check_limits_are_positive(limits: Sequence[tuple[uuid.UUID, Decimal]]) -> None:
    for category_id, amount in limits:
        if amount < _SMALLEST_LIMIT:
            raise _limit_error(ErrorCode.BUDGET_LIMIT_NOT_POSITIVE, category_id)


def _check_categories_do_not_repeat(limits: Sequence[tuple[uuid.UUID, Decimal]]) -> None:
    seen: set[uuid.UUID] = set()
    for category_id, _ in limits:
        if category_id in seen:
            raise _limit_error(ErrorCode.BUDGET_CATEGORY_REPEATED, category_id)
        seen.add(category_id)


def _check_categories_are_of_expense(
    limits: Sequence[tuple[uuid.UUID, Decimal]], categories: Mapping[uuid.UUID, Category]
) -> None:
    for category_id, _ in limits:
        if categories[category_id].kind is not TransactionType.EXPENSE:
            raise _limit_error(ErrorCode.BUDGET_CATEGORY_NOT_EXPENSE, category_id)


def _check_limits_fit(limits: Sequence[tuple[uuid.UUID, Decimal]]) -> None:
    for category_id, amount in limits:
        if amount >= _TOO_LARGE:
            raise _limit_error(ErrorCode.AMOUNT_TOO_LARGE, category_id)


def _limit_error(code: ErrorCode, category_id: uuid.UUID) -> InvalidError:
    return InvalidError(code, context={ContextField.CATEGORY_ID: category_id})
