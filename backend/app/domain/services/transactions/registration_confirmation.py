"""The confirmation of a registered movement (domain rules, § 1; FEAT-003).

It says what was registered, and lists the date, the currency and the category, which may have
been assumed, together with the budget it went to.
"""

from __future__ import annotations

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


def confirmation_text(
    *,
    type: TransactionType,
    amount: Decimal,
    currency: str,
    account_name: str,
    category_name: str,
    transaction_date: date,
    period: BudgetPeriod,
) -> str:
    lines = (
        _FIRST_LINE[type].format(amount=written_amount(amount, currency), account=account_name),
        messages.CONFIRMATION_DATE.format(date=written_day(transaction_date)),
        messages.CONFIRMATION_CURRENCY.format(currency=currency),
        messages.CONFIRMATION_CATEGORY.format(category=category_name),
        messages.CONFIRMATION_PERSONAL_BUDGET.format(
            start=written_day(period.period_start), end=written_day(period.period_end)
        ),
    )
    return LINE_END.join(lines)


def before_opening_text(type: TransactionType, account_name: str, opened_on: date) -> str:
    """Why a movement before its account was opened is not registered (domain rules, § 2)."""
    return messages.BEFORE_ACCOUNT_OPENING.format(
        account=account_name, date=written_day(opened_on), done=_DONE_BEFORE[type]
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
