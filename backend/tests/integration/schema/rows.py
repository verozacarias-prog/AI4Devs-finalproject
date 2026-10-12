"""A valid row of every table, and the ways the database says no.

Every rejection test inserts the valid row first and then changes one value, so a test cannot
pass because of some other mistake in the row. The constraint names asserted here are the
contract the schema migration has to honour: triggers raise with the same kind of name.
"""

from __future__ import annotations

import json
import secrets
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import psycopg
import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from tests.integration.schema.names import (
    CONFIRMED,
    DOLLARS,
    EXPENSE,
    MANUAL,
    META,
    MONTHLY,
    PESOS,
    TIME_ZONE,
    WEB,
    Table,
)

OPENED_AT = datetime(2026, 1, 1, 12, tzinfo=UTC)
PERIOD_START = date(2026, 3, 1)
PERIOD_END = date(2026, 3, 31)
MOVEMENT_DATE = date(2026, 3, 10)

NOT_NULL_VIOLATION = "23502"
INSUFFICIENT_PRIVILEGE = "42501"

_CASTS = {
    "parsed_data": "jsonb",
    "payload": "jsonb",
    "content": "jsonb",
    "retrieval": "jsonb",
    "missing_fields": "text[]",
}


def _token() -> str:
    return secrets.token_hex(8)


def _phone() -> str:
    return f"+54911{secrets.randbelow(10**8):08d}"


def _placeholder(column: str) -> str:
    cast = _CASTS.get(column)
    return f"CAST(:{column} AS {cast})" if cast else f":{column}"


def _bound(column: str, value: object) -> object:
    if _CASTS.get(column) == "jsonb" and value is not None:
        return json.dumps(value)
    return value


def _diagnostics(error: DBAPIError) -> psycopg.Error:
    original = error.orig
    assert isinstance(original, psycopg.Error), repr(original)
    return original


@dataclass(frozen=True)
class Home:
    """A user who can register a movement: an account, a confirmed period and a category."""

    user: uuid.UUID
    account: uuid.UUID
    period: uuid.UUID
    category: uuid.UUID


class Rows:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    # --- plain SQL -------------------------------------------------------------------------

    def insert(self, table: str, values: Mapping[str, object]) -> None:
        columns = ", ".join(values)
        placeholders = ", ".join(_placeholder(column) for column in values)
        statement = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"  # noqa: S608
        bound = {column: _bound(column, value) for column, value in values.items()}
        self.connection.execute(text(statement), bound)

    def update(self, table: str, row_id: uuid.UUID, **values: object) -> None:
        assignments = ", ".join(f"{column} = {_placeholder(column)}" for column in values)
        statement = f"UPDATE {table} SET {assignments} WHERE id = :row_id"  # noqa: S608
        bound = {column: _bound(column, value) for column, value in values.items()}
        self.connection.execute(text(statement), {**bound, "row_id": row_id})

    def value(self, table: str, row_id: uuid.UUID, column: str) -> object:
        statement = f"SELECT {column} FROM {table} WHERE id = :row_id"  # noqa: S608
        return self.connection.execute(text(statement), {"row_id": row_id}).scalar_one()

    def act_as(self, user: uuid.UUID) -> None:
        """What the application does before a change: say who is making it."""
        self.connection.execute(
            text("SELECT set_config('app.actor_id', :actor, true)"), {"actor": str(user)}
        )

    def check_deferred(self) -> None:
        """Run now the checks that normally wait for the commit."""
        self.connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        self.connection.execute(text("SET CONSTRAINTS ALL DEFERRED"))

    # --- the ways the database says no -----------------------------------------------------

    @contextmanager
    def rejected_by(self, *constraints: str) -> Iterator[None]:
        savepoint = self.connection.begin_nested()
        try:
            yield
            self.connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        except DBAPIError as error:
            savepoint.rollback()
            diagnostics = _diagnostics(error)
            assert diagnostics.diag.constraint_name in constraints, str(diagnostics)
            return
        savepoint.rollback()
        pytest.fail(f"the database accepted what {' or '.join(constraints)} must reject")

    @contextmanager
    def rejected_null(self, column: str) -> Iterator[None]:
        savepoint = self.connection.begin_nested()
        try:
            yield
        except DBAPIError as error:
            savepoint.rollback()
            diagnostics = _diagnostics(error)
            assert diagnostics.sqlstate == NOT_NULL_VIOLATION, str(diagnostics)
            assert diagnostics.diag.column_name == column, str(diagnostics)
            return
        savepoint.rollback()
        pytest.fail(f"the database accepted a row without {column}")

    @contextmanager
    def denied(self) -> Iterator[None]:
        savepoint = self.connection.begin_nested()
        try:
            yield
        except DBAPIError as error:
            savepoint.rollback()
            diagnostics = _diagnostics(error)
            assert diagnostics.sqlstate == INSUFFICIENT_PRIVILEGE, str(diagnostics)
            return
        savepoint.rollback()
        pytest.fail("the database allowed a statement the role has no permission for")

    # --- users, groups and access ----------------------------------------------------------

    def _new(
        self, table: str, defaults: Mapping[str, object], overrides: Mapping[str, object]
    ) -> uuid.UUID:
        values: dict[str, object] = {"id": uuid.uuid4(), **defaults, **overrides}
        self.insert(table, values)
        identifier = values["id"]
        assert isinstance(identifier, uuid.UUID)
        return identifier

    def user(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "name": "Ana",
            "whatsapp_phone": _phone(),
            "country": "AR",
            "time_zone": TIME_ZONE,
            "primary_currency": PESOS,
            "terms_accepted_at": OPENED_AT,
            "terms_version": "1",
            "onboarding_status": "completed",
        }
        return self._new(Table.APP_USER, defaults, overrides)

    def group(self, **overrides: object) -> uuid.UUID:
        return self._new(Table.FAMILY_GROUP, {"name": "Casa"}, overrides)

    def membership(self, user: uuid.UUID, group: uuid.UUID, **overrides: object) -> None:
        defaults: dict[str, object] = {
            "user_id": user,
            "family_group_id": group,
            "role": "member",
            "joined_at": OPENED_AT,
        }
        self.insert(Table.USER_GROUP, {**defaults, **overrides})

    def invitation(self, group: uuid.UUID, owner: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "family_group_id": group,
            "created_by": owner,
            "code_hash": _token(),
            "created_at": OPENED_AT,
            "expires_at": OPENED_AT + timedelta(days=7),
        }
        return self._new(Table.GROUP_INVITATION, defaults, overrides)

    def financial_profile(self, user: uuid.UUID, **overrides: object) -> None:
        self.insert(Table.FINANCIAL_PROFILE, {"user_id": user, **overrides})

    def login_code(self, user: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": user,
            "purpose": "login",
            "code_hash": _token(),
            "created_at": OPENED_AT,
            "expires_at": OPENED_AT + timedelta(minutes=5),
        }
        return self._new(Table.LOGIN_CODE, defaults, overrides)

    def session(self, user: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": user,
            "token_hash": _token(),
            "created_at": OPENED_AT,
            "last_seen_at": OPENED_AT,
            "expires_at": OPENED_AT + timedelta(hours=12),
        }
        return self._new(Table.SESSION, defaults, overrides)

    def dev_access_link(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {"label": f"tester-{_token()}", "token_hash": _token()}
        return self._new(Table.DEV_ACCESS_LINK, defaults, overrides)

    def auth_throttle(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "key_type": "phone",
            "key_hash": _token(),
            "event": "code_request",
        }
        return self._new(Table.AUTH_THROTTLE, defaults, overrides)

    def allowed_phone(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {"phone_hash": _token(), "enabled_at": OPENED_AT}
        return self._new(Table.ALLOWED_PHONE, defaults, overrides)

    # --- accounts, categories and budgets --------------------------------------------------

    def account(self, user: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": user,
            "name": f"Cuenta {_token()}",
            "type": "bank_account",
            "currency": PESOS,
            "created_at": OPENED_AT,
        }
        return self._new(Table.ACCOUNT, defaults, overrides)

    def card(self, user: uuid.UUID, **overrides: object) -> uuid.UUID:
        card: dict[str, object] = {"type": "credit_card", "closing_day": 20, "due_day": 5}
        return self.account(user, **{**card, **overrides})

    def category(self, user: uuid.UUID | None, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "name": f"Propia {_token()}",
            "user_id": user,
            "is_base": user is None,
            "kind": EXPENSE,
        }
        return self._new(Table.CATEGORY, defaults, overrides)

    def period(
        self, *, user: uuid.UUID | None = None, group: uuid.UUID | None = None, **overrides: object
    ) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": user,
            "family_group_id": group,
            "period_type": MONTHLY,
            "period_start": PERIOD_START,
            "period_end": PERIOD_END,
            "primary_currency": PESOS,
            "status": CONFIRMED,
        }
        return self._new(Table.BUDGET_PERIOD, defaults, overrides)

    def budget(self, period: uuid.UUID, category: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "budget_period_id": period,
            "category_id": category,
            "limit_amount": Decimal("300000.00"),
        }
        return self._new(Table.BUDGET, defaults, overrides)

    def sent_alert(
        self, budget: uuid.UUID, user: uuid.UUID, message: uuid.UUID, **overrides: object
    ) -> uuid.UUID:
        defaults: dict[str, object] = {
            "budget_id": budget,
            "threshold": 80,
            "user_id": user,
            "outbound_message_id": message,
        }
        return self._new(Table.SENT_ALERT, defaults, overrides)

    def home(self) -> Home:
        user = self.user()
        return Home(
            user=user,
            account=self.account(user),
            period=self.period(user=user),
            category=self.category(user),
        )

    # --- movements -------------------------------------------------------------------------

    def transaction(self, home: Home, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": home.user,
            "account_id": home.account,
            "budget_period_id": home.period,
            "category_id": home.category,
            "amount": Decimal("3500.00"),
            "currency": PESOS,
            "type": EXPENSE,
            "source": MANUAL,
            "transaction_date": MOVEMENT_DATE,
        }
        return self._new(Table.TRANSACTION, defaults, overrides)

    def transfer(
        self, user: uuid.UUID, origin: uuid.UUID, destination: uuid.UUID, **overrides: object
    ) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": user,
            "from_account_id": origin,
            "from_amount": Decimal("1000.00"),
            "from_currency": PESOS,
            "to_account_id": destination,
            "to_amount": Decimal("1000.00"),
            "to_currency": PESOS,
            "transfer_date": MOVEMENT_DATE,
            "source": MANUAL,
        }
        return self._new(Table.TRANSFER, defaults, overrides)

    def rule(self, home: Home, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": home.user,
            "category_id": home.category,
            "type": EXPENSE,
            "account_id": home.account,
            "budget_user_id": home.user,
            "amount": Decimal("9000.00"),
            "currency": PESOS,
            "frequency": MONTHLY,
            "execution_day": 10,
            "next_execution": date(2026, 4, 10),
        }
        return self._new(Table.RECURRING_RULE, defaults, overrides)

    def card_statement(self, card: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "account_id": card,
            "closing_date": date(2026, 3, 20),
            "due_date": date(2026, 4, 5),
        }
        return self._new(Table.CARD_STATEMENT, defaults, overrides)

    # --- pendings and messages -------------------------------------------------------------

    def batch(self, user: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {"user_id": user, "source": MANUAL}
        return self._new(Table.PENDING_BATCH, defaults, overrides)

    def pending(self, user: uuid.UUID, batch: uuid.UUID, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "user_id": user,
            "intent": "transaction",
            "parsed_data": {"amount": "3500.00"},
            "missing_fields": ["account"],
            "source": MANUAL,
            "batch_id": batch,
            "position": 1,
            "status": "open",
            "expires_at": OPENED_AT + timedelta(days=90),
        }
        return self._new(Table.PENDING_TRANSACTION, defaults, overrides)

    def inbound(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "provider": META,
            "provider_message_id": f"wamid.{_token()}",
            "from_phone": _phone(),
            "payload": {"text": "gasté 3500 en el súper"},
            "sent_at": OPENED_AT,
        }
        return self._new(Table.INBOUND_MESSAGE, defaults, overrides)

    def outbound(self, user: uuid.UUID | None, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "provider": WEB,
            "user_id": user,
            "to_phone": _phone(),
            "content": {"text": "Listo", "response_kind": "registration"},
            "status": "sent",
        }
        return self._new(Table.OUTBOUND_MESSAGE, defaults, overrides)

    # --- rates, indicators and model usage -------------------------------------------------

    def exchange_rate(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "source": "DOLAR_MEP",
            "base_currency": DOLLARS,
            "quote_currency": PESOS,
            "rate": Decimal("1200.0000000000"),
            "rate_at": OPENED_AT,
        }
        return self._new(Table.EXCHANGE_RATE, defaults, overrides)

    def indicator_value(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "source": "INDEC_CPI_MONTHLY",
            "value": Decimal("2.5000000000"),
            "value_date": PERIOD_START,
        }
        return self._new(Table.INDICATOR_VALUE, defaults, overrides)

    def llm_usage(self, user: uuid.UUID, **overrides: object) -> None:
        defaults: dict[str, object] = {
            "user_id": user,
            "usage_date": MOVEMENT_DATE,
            "quota": "registration",
        }
        self.insert(Table.LLM_USAGE, {**defaults, **overrides})

    def llm_call(self, **overrides: object) -> uuid.UUID:
        defaults: dict[str, object] = {
            "purpose": "classification",
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "duration_ms": 120,
            "outcome": "ok",
        }
        return self._new(Table.LLM_CALL, defaults, overrides)
