"""What the content of a budget period has to meet to be saved (docs/04-api.md)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from decimal import Decimal

from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus
from app.domain.entities.category import Category
from app.domain.entities.transaction import TransactionType
from app.domain.errors import ConflictError, ErrorCode, InvalidError, NotFoundError


def check_confirmed_stays_fixed(stored: BudgetPeriod, changed: BudgetPeriod) -> None:
    """A confirmed period changes only its estimated income and its limits (CA-10)."""
    if stored.status is PeriodStatus.CONFIRMED and (
        changed.period_type,
        changed.period_start,
        changed.period_end,
        changed.primary_currency,
    ) != (
        stored.period_type,
        stored.period_start,
        stored.period_end,
        stored.primary_currency,
    ):
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
    for category_id, _ in limits:
        category = categories.get(category_id)
        if category is None or category.user_id not in (None, user_id):
            raise NotFoundError(ErrorCode.NOT_FOUND)
    if any(amount <= 0 for _, amount in limits):
        raise InvalidError(ErrorCode.BUDGET_LIMIT_NOT_POSITIVE)
    if len({category_id for category_id, _ in limits}) != len(limits):
        raise InvalidError(ErrorCode.BUDGET_CATEGORY_REPEATED)
    if any(
        categories[category_id].kind is not TransactionType.EXPENSE for category_id, _ in limits
    ):
        raise InvalidError(ErrorCode.BUDGET_CATEGORY_NOT_EXPENSE)
    if estimated_income < 0:
        raise InvalidError(ErrorCode.ESTIMATED_INCOME_NEGATIVE)
