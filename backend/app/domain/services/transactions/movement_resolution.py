"""Whether an interpreted expense or income can be registered without asking (domain rules, § 1).

It can when everything is in sight: the amount, one account of the user by its name, one of
the categories of its kind, and one possible period for its day, already confirmed. What is
missing or ambiguous is asked in a pending, which comes in the next cut of FEAT-003.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.entities.account import Account, AccountType
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus
from app.domain.entities.category import Category
from app.domain.entities.classification import Classification, RegistrationType
from app.domain.entities.transaction import TransactionType
from app.domain.services.dates.local_date import local_today
from app.domain.services.transactions.account_resolution import named_account

_TRANSACTION_TYPES = {
    RegistrationType.EXPENSE: TransactionType.EXPENSE,
    RegistrationType.INCOME: TransactionType.INCOME,
}
# Where an expense or an income can be registered. A card purchase is another registration
# type, and an investment account moves only by transfers.
_ACCOUNT_TYPES_FOR_MOVEMENTS = frozenset(
    {AccountType.BANK_ACCOUNT, AccountType.DIGITAL_WALLET, AccountType.CASH}
)
# Two decimals, as the database stores an amount.
_CENTS_EXPONENT = -2


@dataclass(frozen=True)
class ResolvedMovement:
    type: TransactionType
    amount: Decimal
    account: Account
    category: Category
    period: BudgetPeriod
    transaction_date: date


def movement_date(classification: Classification, today: date) -> date:
    """The day the message says, or else the day the user wrote."""
    return classification.transaction_date or today


def is_movement(classification: Classification) -> bool:
    """Whether it is a registration of the types that have code: an expense or an income."""
    return classification.registration_type in _TRANSACTION_TYPES


def resolve_movement(
    classification: Classification,
    text: str,
    accounts: Sequence[Account],
    categories: Sequence[Category],
    today: date,
    time_zone: str,
    periods: Sequence[BudgetPeriod],
) -> ResolvedMovement | None:
    """The movement to register, or None when something needs the user (domain rules, § 1).

    `periods` are the ones that cover its day, which the use case reads before: a domain
    service touches no port.
    """
    if classification.registration_type not in _TRANSACTION_TYPES:
        return None
    transaction_type = _TRANSACTION_TYPES[classification.registration_type]
    amount = classification.amount
    if amount is None or not _is_valid_amount(amount):
        return None
    # Never an account by default: the message has to name it, and only it.
    account = named_account(
        text,
        classification.account,
        classification.currency,
        [account for account in accounts if account.type in _ACCOUNT_TYPES_FOR_MOVEMENTS],
    )
    category = _only_one(
        [
            category
            for category in categories
            if category.kind is transaction_type
            and _same_name(category.name, classification.category)
        ]
    )
    if account is None or category is None:
        return None
    transaction_date = movement_date(classification, today)
    # Nothing is registered before the day the account was opened (domain rules, § 2).
    if transaction_date < local_today(account.opened_at, time_zone):
        return None
    period = _only_one(list(periods))
    # With a single possible period, and confirmed, it goes there without asking. An expense
    # in another currency than its period needs a rate, which is not built yet.
    if (
        period is None
        or period.status is not PeriodStatus.CONFIRMED
        or period.user_id is None
        or period.primary_currency != account.currency
    ):
        return None
    return ResolvedMovement(
        type=transaction_type,
        amount=amount,
        account=account,
        category=category,
        period=period,
        transaction_date=transaction_date,
    )


def _is_valid_amount(amount: Decimal) -> bool:
    exponent = amount.as_tuple().exponent
    return (
        amount.is_finite()
        and amount > 0
        and isinstance(exponent, int)
        and exponent >= _CENTS_EXPONENT
    )


def _same_name(stored: str, written: str | None) -> bool:
    return written is not None and stored.casefold() == written.strip().casefold()


def _only_one[T](found: list[T]) -> T | None:
    return found[0] if len(found) == 1 else None
