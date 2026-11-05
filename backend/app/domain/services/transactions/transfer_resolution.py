"""Whether an interpreted transfer can be registered without asking (domain rules, § 13; FEAT-006).

It can when everything is in sight: the amount, and on each side exactly one account of the
user, named by the same rule as the account of an expense (§ 1). The two accounts are distinct,
in the same currency, and already opened on its day. What is not in sight is not guessed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.entities.account import Account
from app.domain.entities.classification import Classification
from app.domain.services.dates.local_date import local_today
from app.domain.services.transactions.account_resolution import AccountWords, named_account
from app.domain.services.transactions.movement_resolution import (
    ParsedKey,
    account_words,
    fits,
    movement_date,
    rounded,
    verified_currency,
)


@dataclass(frozen=True)
class ResolvedTransfer:
    """A transfer to register: the same amount leaves one account and reaches the other."""

    amount: Decimal
    from_account: Account
    to_account: Account
    transfer_date: date


def resolve_transfer(
    classification: Classification,
    text: str,
    accounts: Sequence[Account],
    today: date,
    time_zone: str,
) -> ResolvedTransfer | None:
    """The transfer to register, or None when something is not in sight (§ 1, § 13)."""
    amount = classification.amount
    from_account = named_account(text, account_words(classification, text), accounts)
    to_account = named_account(
        text,
        AccountWords(
            classification.to_account,
            classification.to_account_type,
            classification.to_account_type_words,
            verified_currency(classification, text),
        ),
        accounts,
    )
    transfer_date = movement_date(classification, today)
    if (
        amount is None
        or not fits(amount)
        or from_account is None
        or to_account is None
        or from_account.id == to_account.id
        or from_account.currency != to_account.currency
        or _before_opening(from_account, transfer_date, time_zone)
        or _before_opening(to_account, transfer_date, time_zone)
    ):
        return None
    return ResolvedTransfer(
        amount=rounded(amount),
        from_account=from_account,
        to_account=to_account,
        transfer_date=transfer_date,
    )


def _before_opening(account: Account, day: date, time_zone: str) -> bool:
    """What happened before an account was opened is already in its initial balance (§ 2)."""
    return day < local_today(account.opened_at, time_zone)


def transfer_parsed_data(transfer: ResolvedTransfer) -> dict[str, str | None]:
    """What its pending keeps, as text: amounts never go through float."""
    return {
        ParsedKey.AMOUNT: str(transfer.amount),
        ParsedKey.CURRENCY: transfer.from_account.currency,
        ParsedKey.ACCOUNT: transfer.from_account.name,
        ParsedKey.TO_ACCOUNT: transfer.to_account.name,
        ParsedKey.TRANSACTION_DATE: transfer.transfer_date.isoformat(),
    }
