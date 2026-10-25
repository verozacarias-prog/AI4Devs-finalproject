"""The budget of Lucía, built in memory for the unit tests of FEAT-004.

Unless a case says otherwise: Lucía is from Buenos Aires, with ARS as her primary currency; she
has "Galicia pesos", in ARS, and "Galicia USD", in USD; her individual period goes from 10
October to 9 November 2026, confirmed, in ARS, with an estimated income of $1.450.000,00 and two
limits, Supermercado $300.000,00 and Transporte $80.000,00; and today is 25 October 2026.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.entities.account import Account, AccountType
from app.domain.entities.budget import Budget
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.entities.category import Category
from app.domain.entities.transaction import Transaction, TransactionSource, TransactionType
from app.domain.entities.user import OnboardingStatus, User
from tests.support.doubles import InMemoryUnitOfWork

BUENOS_AIRES = "America/Argentina/Buenos_Aires"
PESOS = "ARS"
DOLLARS = "USD"
OPENED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
# Midday in Buenos Aires: 25 October for the user and for the machine alike.
TODAY_AT_NOON = datetime(2026, 10, 25, 15, 0, tzinfo=UTC)
DELETED_AT = datetime(2026, 10, 20, 18, 0, tzinfo=UTC)

SUPERMARKET = "Supermercado"
TRANSPORT = "Transporte"
EATING_OUT = "Comida afuera y delivery"
HEALTH = "Salud"
SALARY = "Sueldo"
OTHER_INCOME = "Otros ingresos"
REFUNDS = "Devoluciones y reintegros"
BASE_EXPENSES = (SUPERMARKET, TRANSPORT, EATING_OUT, HEALTH)
BASE_INCOMES = (SALARY, OTHER_INCOME, REFUNDS)


@dataclass
class LuciaBudget:
    """What a case needs to add movements to the budget of Lucía and to read it."""

    unit_of_work: InMemoryUnitOfWork
    user: User
    pesos: Account
    dollars: Account
    period: BudgetPeriod
    limits: dict[str, Budget]
    categories: dict[str, Category]

    def own_category(self, name: str) -> Category:
        """A category of Lucía, of expenses, that she confirmed."""
        category = Category(
            id=uuid.uuid4(), name=name, kind=TransactionType.EXPENSE, user_id=self.user.id
        )
        self.unit_of_work.categories.add(category)
        self.categories[name] = category
        return category

    def other_period(self, start: date, end: date) -> BudgetPeriod:
        """Another confirmed period of Lucía, in ARS, without limits."""
        return add_period(self.unit_of_work, self.user.id, start, end)

    def expense(
        self,
        category: str,
        amount: str,
        on: date,
        *,
        account: Account | None = None,
        currency: str | None = None,
        exchange_rate: str | None = None,
        period: BudgetPeriod | None = None,
        duplicate_of: uuid.UUID | None = None,
        deleted_at: datetime | None = None,
    ) -> Transaction:
        return self._movement(
            TransactionType.EXPENSE,
            category,
            amount,
            on,
            account=account,
            currency=currency,
            exchange_rate=exchange_rate,
            period=period,
            duplicate_of=duplicate_of,
            deleted_at=deleted_at,
        )

    def income(
        self,
        category: str,
        amount: str,
        on: date,
        *,
        account: Account | None = None,
        currency: str | None = None,
        exchange_rate: str | None = None,
        refund_of: uuid.UUID | None = None,
        deleted_at: datetime | None = None,
    ) -> Transaction:
        return self._movement(
            TransactionType.INCOME,
            category,
            amount,
            on,
            account=account,
            currency=currency,
            exchange_rate=exchange_rate,
            refund_of=refund_of,
            deleted_at=deleted_at,
        )

    def refund(
        self, of: Transaction, amount: str, on: date, *, deleted_at: datetime | None = None
    ) -> Transaction:
        """An income in "Devoluciones y reintegros" linked to that expense."""
        return self.income(REFUNDS, amount, on, refund_of=of.id, deleted_at=deleted_at)

    def _movement(
        self,
        type: TransactionType,
        category: str,
        amount: str,
        on: date,
        *,
        account: Account | None,
        currency: str | None,
        exchange_rate: str | None,
        period: BudgetPeriod | None = None,
        duplicate_of: uuid.UUID | None = None,
        refund_of: uuid.UUID | None = None,
        deleted_at: datetime | None = None,
    ) -> Transaction:
        account = account or self.pesos
        transaction = Transaction(
            id=uuid.uuid4(),
            user_id=self.user.id,
            account_id=account.id,
            type=type,
            amount=Decimal(amount),
            currency=currency or account.currency,
            exchange_rate=Decimal(exchange_rate) if exchange_rate is not None else None,
            transaction_date=on,
            duplicate_of=duplicate_of,
            deleted_at=deleted_at,
            budget_period_id=(period or self.period).id,
            category_id=self.categories[category].id,
            source=TransactionSource.MANUAL,
            refund_of=refund_of,
        )
        self.unit_of_work.transactions.add(transaction)
        return transaction


def add_user(unit_of_work: InMemoryUnitOfWork, name: str, phone: str) -> User:
    user = User(
        id=uuid.uuid4(),
        name=name,
        whatsapp_phone=phone,
        country="AR",
        time_zone=BUENOS_AIRES,
        primary_currency=PESOS,
        exchange_rate_reference=None,
        terms_accepted_at=OPENED_AT,
        terms_version="local-seed-1",
        notifications_opt_in=False,
        onboarding_status=OnboardingStatus.COMPLETED,
    )
    unit_of_work.users.add(user)
    return user


def add_period(
    unit_of_work: InMemoryUnitOfWork,
    user_id: uuid.UUID | None,
    start: date,
    end: date,
    *,
    family_group_id: uuid.UUID | None = None,
    status: PeriodStatus = PeriodStatus.CONFIRMED,
    estimated_income: str = "0",
) -> BudgetPeriod:
    period = BudgetPeriod(
        id=uuid.uuid4(),
        user_id=user_id,
        family_group_id=family_group_id,
        period_type=PeriodType.MONTHLY,
        period_start=start,
        period_end=end,
        primary_currency=PESOS,
        estimated_income=Decimal(estimated_income),
        status=status,
    )
    unit_of_work.budget_periods.add(period)
    return period


def lucia_budget() -> LuciaBudget:
    unit_of_work = InMemoryUnitOfWork()
    user = add_user(unit_of_work, "Lucía", "+000000000001")
    pesos = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Galicia pesos",
        type=AccountType.BANK_ACCOUNT,
        currency=PESOS,
        initial_balance=Decimal("350000.00"),
        opened_at=OPENED_AT,
    )
    dollars = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Galicia USD",
        type=AccountType.BANK_ACCOUNT,
        currency=DOLLARS,
        initial_balance=Decimal("500.00"),
        opened_at=OPENED_AT,
    )
    unit_of_work.accounts.add(pesos)
    unit_of_work.accounts.add(dollars)
    categories: dict[str, Category] = {}
    for names, kind in (
        (BASE_EXPENSES, TransactionType.EXPENSE),
        (BASE_INCOMES, TransactionType.INCOME),
    ):
        for name in names:
            category = Category(id=uuid.uuid4(), name=name, kind=kind, user_id=None)
            unit_of_work.categories.add(category)
            categories[name] = category
    period = add_period(
        unit_of_work,
        user.id,
        date(2026, 10, 10),
        date(2026, 11, 9),
        estimated_income="1450000.00",
    )
    limits: dict[str, Budget] = {}
    for name, limit in ((SUPERMARKET, "300000.00"), (TRANSPORT, "80000.00")):
        budget = Budget(
            id=uuid.uuid4(),
            budget_period_id=period.id,
            category_id=categories[name].id,
            limit_amount=Decimal(limit),
        )
        unit_of_work.budgets.add(budget)
        limits[name] = budget
    return LuciaBudget(unit_of_work, user, pesos, dollars, period, limits, categories)
