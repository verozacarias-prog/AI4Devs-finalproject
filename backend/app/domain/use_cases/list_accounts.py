from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.domain.account_balance import balance_kind_of, balance_of
from app.domain.entities.account import Account, BalanceKind
from app.domain.errors import ErrorCode, NotFoundError
from app.domain.local_date import local_today
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


@dataclass(frozen=True)
class AccountBalance:
    account: Account
    balance: Decimal
    balance_kind: BalanceKind


class ListAccounts:
    """The accounts of a user with their computed balance, in the order the screen shows them.

    First the accounts in the primary currency of the user, then the other currencies by
    code, and within each currency by name, without telling capitals apart (FEAT-001, CA-12).
    """

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, user_id: uuid.UUID) -> list[AccountBalance]:
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            if user is None:
                raise NotFoundError(ErrorCode.NOT_FOUND)
            accounts = unit_of_work.accounts.list_by_user(user_id)
            transactions = unit_of_work.transactions.list_by_user(user_id)
            transfers = unit_of_work.transfers.list_by_user(user_id)
        today = local_today(self._clock.now(), user.time_zone)
        ordered = sorted(
            accounts,
            key=lambda account: (
                account.currency != user.primary_currency,
                account.currency,
                account.name.casefold(),
            ),
        )
        return [
            AccountBalance(
                account=account,
                balance=balance_of(account, transactions, transfers, today),
                balance_kind=balance_kind_of(account),
            )
            for account in ordered
        ]
