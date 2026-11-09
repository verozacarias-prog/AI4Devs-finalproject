"""The confirmation of a registered movement (domain rules, § 1; FEAT-003, FEAT-006, FEAT-007).

It says what was registered, and lists the date, the currency and the category, which may have
been assumed, together with the budget it went to. A transfer has no category and no budget.
In a batch of several, each movement goes with its number, and one confirmation lists them all.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from app import messages
from app.constants import LINE_END
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.transaction import TransactionType

_FIRST_LINE = {
    TransactionType.EXPENSE: messages.REGISTERED_EXPENSE,
    TransactionType.INCOME: messages.REGISTERED_INCOME,
}
_NUMBERED_FIRST_LINE = {
    TransactionType.EXPENSE: messages.BATCH_EXPENSE,
    TransactionType.INCOME: messages.BATCH_INCOME,
}
# Between one movement of a batch and the next, so that each reads apart.
_BETWEEN_MOVEMENTS = LINE_END * 2


def confirmation_text(
    *,
    type: TransactionType,
    amount: Decimal,
    currency: str,
    account_name: str,
    category_name: str,
    transaction_date: date,
    period: BudgetPeriod,
    group_name: str | None = None,
    position: int | None = None,
) -> str:
    """`group_name` is that of the group the period belongs to, when it is not the user's.

    `position` is its number in a batch of several, which `batch_confirmation_text` joins.
    """
    start, end = written_day(period.period_start), written_day(period.period_end)
    budget = (
        messages.CONFIRMATION_PERSONAL_BUDGET.format(start=start, end=end)
        if group_name is None
        else messages.CONFIRMATION_GROUP_BUDGET.format(group=group_name, start=start, end=end)
    )
    amount_text = written_amount(amount, currency)
    first_line = (
        _FIRST_LINE[type].format(amount=amount_text, account=account_name)
        if position is None
        else _NUMBERED_FIRST_LINE[type].format(
            position=position, amount=amount_text, account=account_name
        )
    )
    lines = (
        first_line,
        messages.CONFIRMATION_DATE.format(date=written_day(transaction_date)),
        messages.CONFIRMATION_CURRENCY.format(currency=currency),
        messages.CONFIRMATION_CATEGORY.format(category=category_name),
        budget,
    )
    return LINE_END.join(lines)


def transfer_confirmation_text(
    *,
    amount: Decimal,
    currency: str,
    from_account_name: str,
    to_account_name: str,
    transfer_date: date,
    position: int | None = None,
) -> str:
    """A transfer is in no budget, so it says it does not count as an expense (§ 13)."""
    amount_text = written_amount(amount, currency)
    first_line = (
        messages.REGISTERED_TRANSFER.format(
            amount=amount_text, from_account=from_account_name, to_account=to_account_name
        )
        if position is None
        else messages.BATCH_TRANSFER.format(
            position=position,
            amount=amount_text,
            from_account=from_account_name,
            to_account=to_account_name,
        )
    )
    lines = (
        first_line,
        messages.TRANSFER_IS_NOT_AN_EXPENSE,
        messages.CONFIRMATION_DATE.format(date=written_day(transfer_date)),
        messages.CONFIRMATION_CURRENCY.format(currency=currency),
    )
    return LINE_END.join(lines)


def batch_confirmation_text(movements: Sequence[str]) -> str:
    """The confirmation of a batch: how many, and then each one with its number (FEAT-007)."""
    heading = messages.REGISTERED_BATCH.format(count=len(movements))
    return _BETWEEN_MOVEMENTS.join((heading, *movements))


def before_opening_text(type: TransactionType, account_name: str, opened_on: date) -> str:
    """Why a movement before its account was opened is not registered (domain rules, § 2)."""
    return messages.BEFORE_ACCOUNT_OPENING.format(
        account=account_name, date=written_day(opened_on), done=_DONE_BEFORE[type]
    )


def transfer_before_opening_text(account_name: str, opened_on: date) -> str:
    """Why a transfer before one of its accounts was opened is not registered (§ 2, CA-15)."""
    return messages.BEFORE_ACCOUNT_OPENING.format(
        account=account_name, date=written_day(opened_on), done=messages.TRANSFERRED_BEFORE
    )


_DONE_BEFORE = {
    TransactionType.EXPENSE: messages.SPENT_BEFORE,
    TransactionType.INCOME: messages.RECEIVED_BEFORE,
}


def written_amount(amount: Decimal, currency: str) -> str:
    """$3.500, or $3.500,50 when it has cents: how an amount is read in Argentina."""
    whole, cents = f"{amount:,.2f}".split(".")
    whole = whole.replace(",", messages.THOUSANDS_SEPARATOR)
    number = whole if cents == "00" else f"{whole}{messages.DECIMAL_SEPARATOR}{cents}"
    return f"{messages.CURRENCY_SYMBOLS.get(currency, currency)}{number}"


def written_day(day: date) -> str:
    return messages.DAY_FORMAT.format(day=day.day, month=day.month, year=day.year)
