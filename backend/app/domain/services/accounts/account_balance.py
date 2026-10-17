"""The balance of an account, computed from what already happened in it (domain rules, § 2)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.entities.account import Account, AccountType, BalanceKind
from app.domain.entities.transaction import Transaction, TransactionType
from app.domain.entities.transfer import Transfer
from app.domain.errors import InconsistentDataError

CENT = Decimal("0.01")


def in_account_currency(transaction: Transaction, account: Account) -> Decimal:
    """What a movement moves in its account, rounded on its own before any sum (§ 6).

    Rounded half away from zero, like ROUND in PostgreSQL, which the data model names. Without
    a rate the balance would add two currencies, so nothing is computed (FEAT-001, C2-12).
    """
    if transaction.currency == account.currency:
        return transaction.amount
    if transaction.exchange_rate is None:
        raise InconsistentDataError
    return (transaction.amount * transaction.exchange_rate).quantize(CENT, ROUND_HALF_UP)


def balance_of(
    account: Account,
    transactions: Iterable[Transaction],
    transfers: Iterable[Transfer],
    today: date,
) -> Decimal:
    """The initial balance, plus incomes, minus expenses, plus transfers in, minus out.

    Only what is dated up to today counts, and nothing deleted or marked as a duplicate.
    """
    balance = account.initial_balance
    for transaction in transactions:
        if (
            transaction.account_id != account.id
            or transaction.transaction_date > today
            or transaction.deleted_at is not None
            or transaction.duplicate_of is not None
        ):
            continue
        amount = in_account_currency(transaction, account)
        balance += amount if transaction.type is TransactionType.INCOME else -amount
    for transfer in transfers:
        if transfer.transfer_date > today or transfer.deleted_at is not None:
            continue
        if transfer.to_account_id == account.id:
            balance += transfer.to_amount
        if transfer.from_account_id == account.id:
            balance -= transfer.from_amount
    return balance


def balance_kind_of(account: Account) -> BalanceKind:
    if account.type is AccountType.BROKER:
        return BalanceKind.NET_CONTRIBUTED
    return BalanceKind.BALANCE
