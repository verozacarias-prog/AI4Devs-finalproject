"""The invented data a test user is born with, and the test users of the local environment.

One place for the template of docs/operacion.md, section 2. It is test data in plain sight,
never a default for a real registration (domain rules, § 11).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.account import AccountType
from app.domain.entities.financial_profile import IncomeRange, MainGoal

PESOS = "ARS"
DOLLARS = "USD"

TEMPLATE_COUNTRY = "AR"
TEMPLATE_TIME_ZONE = "America/Argentina/Buenos_Aires"
TEMPLATE_CURRENCY = PESOS
TEMPLATE_EXCHANGE_RATE_REFERENCE = "DOLAR_MEP"
# The test environments have no WhatsApp through which a proactive message could go.
TEMPLATE_NOTIFICATIONS_OPT_IN = False


@dataclass(frozen=True)
class TemplateAccount:
    name: str
    type: AccountType
    currency: str
    initial_balance: Decimal


# Two accounts named "Galicia", so that mentioning "la Galicia" forces the assistant to ask.
TEMPLATE_ACCOUNTS: tuple[TemplateAccount, ...] = (
    TemplateAccount("Galicia pesos", AccountType.BANK_ACCOUNT, PESOS, Decimal("350000.00")),
    TemplateAccount("Mercado Pago", AccountType.DIGITAL_WALLET, PESOS, Decimal("80000.00")),
    TemplateAccount("Efectivo", AccountType.CASH, PESOS, Decimal("25000.00")),
    TemplateAccount("Galicia USD", AccountType.BANK_ACCOUNT, DOLLARS, Decimal("500.00")),
)

TEMPLATE_INCOME_RANGE = IncomeRange.RANGE_3
TEMPLATE_DEPENDENTS = 1
TEMPLATE_HAS_DEBTS = False
TEMPLATE_EMERGENCY_FUND_MONTHS = Decimal("2.0")
TEMPLATE_MAIN_GOAL = MainGoal.SAVE

# No country has a calling code that starts with 0, so a phone that starts like this is
# nobody's number. It is what tells a test user apart (ADR 0016).
TEST_PHONE_PREFIX = "+000"

# What the script records as consent: nobody accepted anything, and the version says so.
LOCAL_TERMS_VERSION = "local-seed-1"


@dataclass(frozen=True)
class LocalTestUser:
    name: str
    # It starts with TEST_PHONE_PREFIX.
    phone: str


LUCIA = LocalTestUser("Lucía", "+000000000001")
PABLO = LocalTestUser("Pablo", "+000000000002")
SOFIA = LocalTestUser("Sofía", "+000000000003")
LOCAL_TEST_USERS: tuple[LocalTestUser, ...] = (LUCIA, PABLO, SOFIA)

# Pablo owns it and Sofía is a member; Lucía has only her own budget.
LOCAL_GROUP_NAME = "Casa"
LOCAL_GROUP_OWNER = PABLO
LOCAL_GROUP_MEMBERS: tuple[LocalTestUser, ...] = (SOFIA,)
