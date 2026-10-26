"""What a period spent and received, computed from its movements (domain rules, § 6 and § 16)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal

from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.transaction import Transaction, TransactionType
from app.domain.errors import InconsistentDataError

CENT = Decimal("0.01")
TENTH = Decimal("0.1")
HUNDRED = Decimal("100")
ZERO = Decimal("0.00")


def counts(transaction: Transaction) -> bool:
    """A deleted movement, or one marked as a duplicate, counts nowhere (§ 2 and § 7)."""
    return transaction.deleted_at is None and transaction.duplicate_of is None


def in_period_currency(transaction: Transaction, period: BudgetPeriod) -> Decimal:
    """What a movement weighs in its period, rounded on its own before any sum (§ 6).

    A movement already in the currency of the period weighs its amount, even when its rate
    converted it to its account. Rounded half away from zero, like ROUND in PostgreSQL.
    """
    if transaction.currency == period.primary_currency:
        return transaction.amount
    if transaction.exchange_rate is None:
        raise InconsistentDataError
    return (transaction.amount * transaction.exchange_rate).quantize(CENT, ROUND_HALF_UP)


def spending_category(
    transaction: Transaction, refunded: Mapping[uuid.UUID, Transaction]
) -> uuid.UUID | None:
    """The category a movement adds to or subtracts from, or None if it is no spending.

    An expense adds to its own category. A refund subtracts from the category of the expense
    it refunds, whatever period that expense is in (§ 16). Any other income is no spending.
    """
    if transaction.type is TransactionType.EXPENSE:
        return transaction.category_id
    if transaction.refund_of is not None and transaction.refund_of in refunded:
        return refunded[transaction.refund_of].category_id
    return None


def signed_weight(transaction: Transaction, period: BudgetPeriod) -> Decimal:
    """What a spending movement weighs: an expense adds and a refund subtracts."""
    weight = in_period_currency(transaction, period)
    return weight if transaction.type is TransactionType.EXPENSE else -weight


def spent_by_category(
    transactions: Iterable[Transaction],
    refunded: Mapping[uuid.UUID, Transaction],
    period: BudgetPeriod,
) -> dict[uuid.UUID, Decimal]:
    """What each category with movements in the period spent, net of its refunds.

    It can be negative, when a refund of an earlier expense is larger (§ 16).
    """
    spent: dict[uuid.UUID, Decimal] = {}
    for transaction in transactions:
        if not counts(transaction):
            continue
        category_id = spending_category(transaction, refunded)
        if category_id is None:
            continue
        spent[category_id] = spent.get(category_id, ZERO) + signed_weight(transaction, period)
    return spent


def actual_income(transactions: Iterable[Transaction], period: BudgetPeriod) -> Decimal:
    """The incomes of the period, without the refunds, which subtract from what is spent."""
    return sum(
        (
            in_period_currency(transaction, period)
            for transaction in transactions
            if counts(transaction)
            and transaction.type is TransactionType.INCOME
            and transaction.refund_of is None
        ),
        ZERO,
    )


def used_percentage(spent: Decimal, limit: Decimal) -> Decimal:
    """What is spent over the limit, times a hundred, with one decimal and the half up."""
    return (spent / limit * HUNDRED).quantize(TENTH, ROUND_HALF_UP)
