"""The names and values the schema tests repeat, in one place.

They were born here because the tests came first. A constant lives in the application: as soon
as the application needs one of these, such as the types of a movement in the domain, it moves
there and the tests import it. The application never imports from here. What a single test
asserts, such as the name of the constraint that must answer, stays in that test.
"""

from __future__ import annotations

from decimal import Decimal


class Table:
    """The tables of the schema migration (docs/06-tickets.md, Ticket 3)."""

    ACCOUNT = "account"
    ALLOWED_PHONE = "allowed_phone"
    APP_USER = "app_user"
    AUTH_THROTTLE = "auth_throttle"
    BUDGET = "budget"
    BUDGET_PERIOD = "budget_period"
    CARD_STATEMENT = "card_statement"
    CATEGORY = "category"
    CURRENCY = "currency"
    DEV_ACCESS_LINK = "dev_access_link"
    EXCHANGE_RATE = "exchange_rate"
    FAMILY_GROUP = "family_group"
    FINANCIAL_PROFILE = "financial_profile"
    GROUP_INVITATION = "group_invitation"
    INBOUND_MESSAGE = "inbound_message"
    INDICATOR_VALUE = "indicator_value"
    LLM_CALL = "llm_call"
    LLM_USAGE = "llm_usage"
    LOGIN_CODE = "login_code"
    OUTBOUND_MESSAGE = "outbound_message"
    PENDING_BATCH = "pending_batch"
    PENDING_TRANSACTION = "pending_transaction"
    RECURRING_RULE = "recurring_rule"
    SENT_ALERT = "sent_alert"
    SESSION = "session"
    TRANSACTION = "transaction"
    TRANSFER = "transfer"
    USER_GROUP = "user_group"


# The role the application connects with: it cannot delete movements (ADR 0015).
APPLICATION_ROLE = "platita_app"

# Currencies of the catalog, and a code that is not in it.
PESOS = "ARS"
DOLLARS = "USD"
EUROS = "EUR"
OUTSIDE_THE_CATALOG = "ZZZ"
PESOS_PER_DOLLAR = Decimal("1200")

# Values of the closed sets that several tests use.
EXPENSE = "expense"
INCOME = "income"
MANUAL = "manual"
AUTOMATIC = "automatic"
OWNER = "owner"
DRAFT = "draft"
CONFIRMED = "confirmed"
PROMOTED = "promoted"
MONTHLY = "monthly"
META = "meta"
TWILIO = "twilio"
WEB = "web"
# A value that belongs to no closed set.
OUTSIDE_THE_SET = "unknown"

TIME_ZONE = "America/Argentina/Buenos_Aires"
