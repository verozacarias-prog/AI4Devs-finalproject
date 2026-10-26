from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.transaction import Transaction, TransactionSource
from app.domain.errors import ErrorCode, InconsistentDataError, NotFoundError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.budgets.budget_spending import (
    ZERO,
    counts,
    in_period_currency,
    signed_weight,
    spending_category,
    used_percentage,
)
from app.domain.services.budgets.period_access import can_read


@dataclass(frozen=True)
class BudgetMovement:
    transaction: Transaction
    # What it weighs on the limit, in the currency of the period. A refund weighs positive
    # here, and subtracts because it is an income.
    budget_amount: Decimal
    # The rate it was converted to the period with; None when it was already in its currency.
    exchange_rate: Decimal | None
    account: str
    source: TransactionSource


@dataclass(frozen=True)
class BudgetStatus:
    budget: Budget
    period: BudgetPeriod
    category: str
    limit_amount: Decimal
    spent_amount: Decimal
    used_percentage: Decimal
    movements: list[BudgetMovement]

    @property
    def primary_currency(self) -> str:
        return self.period.primary_currency


def _source_of(transaction: Transaction) -> TransactionSource:
    # Every stored movement has one: the column is NOT NULL.
    if transaction.source is None:
        raise InconsistentDataError
    return transaction.source


class GetBudgetStatus:
    """The limit of one category in a period: what it spent and the movements that count.

    The movements are the expenses of the category and the refunds linked to them that arrived
    in the period, the newest first (FEAT-004, CA-14).
    """

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, user_id: uuid.UUID, budget_id: uuid.UUID) -> BudgetStatus:
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            budget = unit_of_work.budgets.find_by_id(budget_id)
            period = (
                unit_of_work.budget_periods.find_by_id(budget.budget_period_id)
                if budget is not None
                else None
            )
            memberships = unit_of_work.family_groups.list_memberships(user_id)
            if (
                user is None
                or budget is None
                or period is None
                or not can_read(period, user_id, memberships, user.time_zone)
            ):
                # A limit of another user's period does not exist for this one.
                raise NotFoundError(ErrorCode.NOT_FOUND)
            transactions = unit_of_work.transactions.list_by_period(period.id)
            refunded = {
                transaction.id: transaction
                for transaction in unit_of_work.transactions.list_by_ids(
                    {t.refund_of for t in transactions if t.refund_of is not None}
                )
            }
            counted = [
                transaction
                for transaction in transactions
                if counts(transaction)
                and spending_category(transaction, refunded) == budget.category_id
            ]
            accounts = {
                account.id: account.name
                for account in unit_of_work.accounts.list_by_ids(
                    {transaction.account_id for transaction in counted}
                )
            }
            category = unit_of_work.categories.list_by_ids({budget.category_id})[0]
        spent = sum((signed_weight(transaction, period) for transaction in counted), ZERO)
        movements = [
            BudgetMovement(
                transaction=transaction,
                budget_amount=in_period_currency(transaction, period),
                exchange_rate=(
                    transaction.exchange_rate
                    if transaction.currency != period.primary_currency
                    else None
                ),
                account=accounts[transaction.account_id],
                source=_source_of(transaction),
            )
            for transaction in sorted(
                counted,
                key=lambda transaction: (transaction.transaction_date, transaction.id),
                reverse=True,
            )
        ]
        return BudgetStatus(
            budget=budget,
            period=period,
            category=category.name,
            limit_amount=budget.limit_amount,
            spent_amount=spent,
            used_percentage=used_percentage(spent, budget.limit_amount),
            movements=movements,
        )
