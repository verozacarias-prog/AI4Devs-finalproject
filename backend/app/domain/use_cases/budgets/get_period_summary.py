from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.errors import ErrorCode, NotFoundError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.services.budgets.budget_spending import (
    ZERO,
    actual_income,
    spent_by_category,
    used_percentage,
)
from app.domain.services.budgets.period_access import can_read


@dataclass(frozen=True)
class CategorySpending:
    category: str
    # The three are None in a category without a limit.
    budget_id: uuid.UUID | None
    limit_amount: Decimal | None
    used_percentage: Decimal | None
    spent_amount: Decimal


@dataclass(frozen=True)
class PeriodSummary:
    period: BudgetPeriod
    estimated_income: Decimal
    actual_income: Decimal
    total_spent: Decimal
    categories: list[CategorySpending]


def _spending(name: str, limit: Budget | None, spent: Decimal | None) -> CategorySpending:
    spent_amount = spent if spent is not None else ZERO
    if limit is None:
        return CategorySpending(name, None, None, None, spent_amount)
    return CategorySpending(
        name,
        limit.id,
        limit.limit_amount,
        used_percentage(spent_amount, limit.limit_amount),
        spent_amount,
    )


class GetPeriodSummary:
    """The summary of a period: its incomes and what each category spent (domain rules, § 17).

    Every category with a limit, even without expenses, and every one without a limit that had
    movements in the period, by name without telling capitals apart (FEAT-004, CA-12).
    """

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, user_id: uuid.UUID, period_id: uuid.UUID) -> PeriodSummary:
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            period = unit_of_work.budget_periods.find_by_id(period_id)
            memberships = unit_of_work.family_groups.list_memberships(user_id)
            if (
                user is None
                or period is None
                or not can_read(period, user_id, memberships, user.time_zone)
            ):
                # Another user's period does not exist for this one (docs/04-api.md).
                raise NotFoundError(ErrorCode.NOT_FOUND)
            transactions = unit_of_work.transactions.list_by_period(period_id)
            refunded = {
                transaction.id: transaction
                for transaction in unit_of_work.transactions.list_by_ids(
                    {t.refund_of for t in transactions if t.refund_of is not None}
                )
            }
            limits = {
                budget.category_id: budget
                for budget in unit_of_work.budgets.list_by_period(period_id)
            }
            spent = spent_by_category(transactions, refunded, period)
            names = {
                category.id: category.name
                for category in unit_of_work.categories.list_by_ids(set(limits) | set(spent))
            }
        categories = sorted(
            (
                _spending(names[category_id], limits.get(category_id), spent.get(category_id))
                for category_id in set(limits) | set(spent)
            ),
            key=lambda item: item.category.casefold(),
        )
        return PeriodSummary(
            period=period,
            estimated_income=period.estimated_income,
            actual_income=actual_income(transactions, period),
            total_spent=sum((item.spent_amount for item in categories), ZERO),
            categories=categories,
        )
