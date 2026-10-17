"""Shared setup of the registration tests (FEAT-003, docs/features/FEAT-003/spec.md).

Lucía as the cases describe her: seeded on 1 October 2026, from Buenos Aires, with her four
accounts and one confirmed individual period for October. The unit tests get her in memory;
the integration tests get her from the test data script, run with the clock on that day.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Engine

from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import Environment
from app.domain.entities.account import Account, AccountType
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.entities.category import Category
from app.domain.entities.classification import Classification, MessageClass, RegistrationType
from app.domain.entities.inbound_message import InboundMessage, InboundStatus, Provider
from app.domain.entities.transaction import TransactionType
from app.domain.entities.user import OnboardingStatus, User
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from app.domain.use_cases.test_data.seed_test_data import SeedTestData
from tests.support.doubles import FixedClock, InMemoryUnitOfWork

# The clock of every case, unless the case says otherwise: 15:00 in Buenos Aires, Saturday 17.
NOW = datetime(2026, 10, 17, 18, 0, 0, tzinfo=UTC)
# Noon in Buenos Aires, on the day the test data was created.
SEEDED_AT = datetime(2026, 10, 1, 15, 0, 0, tzinfo=UTC)
OCTOBER_1 = date(2026, 10, 1)
OCTOBER_16 = date(2026, 10, 16)
OCTOBER_17 = date(2026, 10, 17)
OCTOBER_31 = date(2026, 10, 31)

SUPERMARKET_EXPENSE = "gasté 3500 en el súper con Mercado Pago"
SALARY_INCOME = "cobré 850000 de sueldo en la Galicia pesos"

LUCIAS_ACCOUNTS = (
    ("Galicia pesos", AccountType.BANK_ACCOUNT, "ARS", Decimal("350000.00")),
    ("Mercado Pago", AccountType.DIGITAL_WALLET, "ARS", Decimal("80000.00")),
    ("Efectivo", AccountType.CASH, "ARS", Decimal("25000.00")),
    ("Galicia USD", AccountType.BANK_ACCOUNT, "USD", Decimal("500.00")),
)
SOME_CATEGORIES = (
    ("Supermercado", TransactionType.EXPENSE),
    ("Transporte", TransactionType.EXPENSE),
    ("Impuestos y trámites", TransactionType.EXPENSE),
    ("Sueldo", TransactionType.INCOME),
)


def supermarket_expense(
    *, account: str = "Mercado Pago", category: str = "Supermercado"
) -> Classification:
    """What the model answers for the expense of C1-01: no date, so it is the day she wrote."""
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=RegistrationType.EXPENSE,
        amount=Decimal("3500"),
        account=account,
        category=category,
    )


def salary_income() -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=RegistrationType.INCOME,
        amount=Decimal("850000"),
        account="Galicia pesos",
        category="Sueldo",
    )


class Lucia:
    """Lucía in memory, with the ids of what she has, for the unit tests."""

    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self.id = uuid.uuid4()
        unit_of_work.users.add(
            User(
                id=self.id,
                name="Lucía",
                whatsapp_phone="+000000000001",
                country="AR",
                time_zone="America/Argentina/Buenos_Aires",
                primary_currency="ARS",
                exchange_rate_reference="DOLAR_MEP",
                terms_accepted_at=SEEDED_AT,
                terms_version="local-seed-1",
                notifications_opt_in=False,
                onboarding_status=OnboardingStatus.COMPLETED,
            )
        )
        self.accounts: dict[str, uuid.UUID] = {}
        for name, account_type, currency, balance in LUCIAS_ACCOUNTS:
            account_id = uuid.uuid4()
            self.accounts[name] = account_id
            unit_of_work.accounts.add(
                Account(
                    id=account_id,
                    user_id=self.id,
                    name=name,
                    type=account_type,
                    currency=currency,
                    initial_balance=balance,
                    opened_at=SEEDED_AT,
                )
            )
        self.categories: dict[str, uuid.UUID] = {}
        for name, kind in SOME_CATEGORIES:
            category_id = uuid.uuid4()
            self.categories[name] = category_id
            unit_of_work.categories.add(
                Category(id=category_id, name=name, kind=kind, user_id=None)
            )
        self.period = BudgetPeriod(
            id=uuid.uuid4(),
            user_id=self.id,
            family_group_id=None,
            period_type=PeriodType.MONTHLY,
            period_start=OCTOBER_1,
            period_end=OCTOBER_31,
            primary_currency="ARS",
            estimated_income=Decimal("0"),
            status=PeriodStatus.CONFIRMED,
        )
        unit_of_work.budget_periods.add(self.period)

    def message(
        self, text: str, *, sent_at: datetime = NOW - timedelta(seconds=5)
    ) -> InboundMessage:
        """A message of hers by the web chat, as the worker took it."""
        return InboundMessage(
            id=uuid.uuid4(),
            provider=Provider.WEB,
            provider_message_id=f"{self.id}:{uuid.uuid4()}",
            user_id=self.id,
            from_phone="+000000000001",
            text=text,
            quoted_outbound_message_id=None,
            sent_at=sent_at,
            status=InboundStatus.PROCESSING,
            attempts=1,
            locked_until=NOW + timedelta(minutes=2),
            processed_at=None,
        )


def seed_on_october_1(engine: Engine) -> None:
    """The test data of `local`, created on 1 October 2026 instead of on the real today."""
    clock = FixedClock(SEEDED_AT)
    SeedTestData(
        SqlAlchemyUnitOfWork(engine), clock, CreateTestUser(clock), Environment.LOCAL
    ).execute()
