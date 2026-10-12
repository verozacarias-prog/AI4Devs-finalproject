"""Cases 1 to 5: what the schema migration leaves in an empty database."""

from __future__ import annotations

import re

import pytest
from sqlalchemy import Connection, text

from tests.integration.schema.names import (
    DOLLARS,
    EUROS,
    EXPENSE,
    INCOME,
    PESOS,
    Table,
)

pytestmark = pytest.mark.integration

TABLES = {
    Table.ACCOUNT,
    Table.ALLOWED_PHONE,
    Table.APP_USER,
    Table.AUTH_THROTTLE,
    Table.BUDGET,
    Table.BUDGET_PERIOD,
    Table.CARD_STATEMENT,
    Table.CATEGORY,
    Table.CURRENCY,
    Table.DEV_ACCESS_LINK,
    Table.EXCHANGE_RATE,
    Table.FAMILY_GROUP,
    Table.FINANCIAL_PROFILE,
    Table.GROUP_INVITATION,
    Table.INBOUND_MESSAGE,
    Table.INDICATOR_VALUE,
    Table.LLM_CALL,
    Table.LLM_USAGE,
    Table.LOGIN_CODE,
    Table.OUTBOUND_MESSAGE,
    Table.PENDING_BATCH,
    Table.PENDING_TRANSACTION,
    Table.RECURRING_RULE,
    Table.SENT_ALERT,
    Table.SESSION,
    Table.TRANSACTION,
    Table.TRANSFER,
    Table.USER_GROUP,
}

BASE_CATEGORIES = {
    # Daily use.
    ("Supermercado", EXPENSE),
    ("Comida afuera y delivery", EXPENSE),
    ("Vivienda", EXPENSE),
    ("Servicios", EXPENSE),
    ("Transporte", EXPENSE),
    ("Salud", EXPENSE),
    ("Educación", EXPENSE),
    ("Ropa", EXPENSE),
    ("Hogar", EXPENSE),
    ("Salidas y ocio", EXPENSE),
    ("Suscripciones", EXPENSE),
    ("Mascotas", EXPENSE),
    ("Regalos", EXPENSE),
    ("Impuestos y trámites", EXPENSE),
    ("Insumos", EXPENSE),
    ("Sueldo", INCOME),
    ("Aguinaldo", INCOME),
    ("Honorarios", INCOME),
    ("Ventas", INCOME),
    ("Jubilación y pensión", INCOME),
    ("Otros ingresos", INCOME),
    # Special: used by the system in specific flows.
    ("Intereses, impuestos y cargos", EXPENSE),
    ("Devoluciones y reintegros", INCOME),
    ("Diferencia de cambio", EXPENSE),
    ("Diferencia de cambio a favor", INCOME),
    ("Comisiones", EXPENSE),
    ("Faltantes sin identificar", EXPENSE),
    ("Sobrantes sin identificar", INCOME),
    ("Rendimientos", INCOME),
    ("Retiro del titular", EXPENSE),
    ("Retiro de la actividad", INCOME),
    ("Aporte a la actividad", EXPENSE),
    ("Aporte del titular", INCOME),
}

NUMERIC_COLUMNS = {
    (Table.ACCOUNT, "initial_balance"): (20, 2),
    (Table.BUDGET, "limit_amount"): (20, 2),
    (Table.BUDGET_PERIOD, "estimated_income"): (20, 2),
    (Table.RECURRING_RULE, "amount"): (20, 2),
    (Table.TRANSACTION, "amount"): (20, 2),
    (Table.TRANSFER, "from_amount"): (20, 2),
    (Table.TRANSFER, "to_amount"): (20, 2),
    (Table.CARD_STATEMENT, "exchange_rate"): (24, 10),
    (Table.EXCHANGE_RATE, "rate"): (24, 10),
    (Table.INDICATOR_VALUE, "value"): (24, 10),
    (Table.TRANSACTION, "exchange_rate"): (24, 10),
    (Table.TRANSFER, "exchange_rate"): (24, 10),
    (Table.FINANCIAL_PROFILE, "emergency_fund_months"): (4, 1),
    (Table.LLM_CALL, "estimated_cost_usd"): (12, 6),
}

CURRENCY_COLUMNS = {
    (Table.ACCOUNT, "currency"),
    (Table.APP_USER, "primary_currency"),
    (Table.BUDGET_PERIOD, "primary_currency"),
    (Table.CURRENCY, "code"),
    (Table.EXCHANGE_RATE, "base_currency"),
    (Table.EXCHANGE_RATE, "quote_currency"),
    (Table.RECURRING_RULE, "currency"),
    (Table.TRANSACTION, "currency"),
    (Table.TRANSFER, "from_currency"),
    (Table.TRANSFER, "to_currency"),
}

INDEXES = [
    (Table.TRANSACTION, "user_id, source, currency, amount, transaction_date"),
    (Table.TRANSACTION, "account_id"),
    (Table.TRANSACTION, "budget_period_id, category_id"),
    (Table.PENDING_TRANSACTION, "batch_id"),
    (Table.INBOUND_MESSAGE, "from_phone, status, sent_at"),
    (Table.OUTBOUND_MESSAGE, "status, next_attempt_at"),
    (Table.PENDING_BATCH, "question_message_id"),
    (Table.PENDING_BATCH, "confirmation_message_id"),
]


def test_the_migration_creates_the_tables_of_the_ticket_and_no_other(
    connection: Connection,
) -> None:
    # Case 1. advice_document and advice_chunk wait for the embedding model (ADR 0019).
    found = set(
        connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        ).scalars()
    )

    assert found - {"alembic_version"} == TABLES


def test_currency_holds_the_iso_4217_catalog(connection: Connection) -> None:
    # Case 2.
    codes = set(connection.execute(text("SELECT code FROM currency")).scalars())

    assert {PESOS, DOLLARS, EUROS, "BRL", "UYU", "CLP", "PYG", "GBP", "JPY", "CHF"} <= codes
    assert len(codes) >= 150
    assert all(re.fullmatch(r"[A-Z]{3}", code) for code in codes)


def test_category_holds_the_base_catalog_with_its_kind(connection: Connection) -> None:
    # Case 3. The catalog of domain rules § 4, daily use and special.
    found = connection.execute(
        text("SELECT name, kind FROM category WHERE user_id IS NULL AND is_base")
    ).all()

    assert {(name, kind) for name, kind in found} == BASE_CATEGORIES
    assert len(found) == len(BASE_CATEGORIES)


def test_amounts_rates_instants_and_currencies_use_the_types_of_the_data_model(
    connection: Connection,
) -> None:
    # Case 4.
    columns = connection.execute(
        text(
            "SELECT table_name, column_name, data_type, numeric_precision, numeric_scale, "
            "character_maximum_length FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
        )
    ).all()

    numeric = {
        (table, column): (precision, scale)
        for table, column, data_type, precision, scale, _ in columns
        if data_type == "numeric"
    }
    currencies = {
        (table, column): (data_type, length)
        for table, column, data_type, _, _, length in columns
        if "currency" in column or (table, column) == (Table.CURRENCY, "code")
    }
    data_types = {data_type for _, _, data_type, _, _, _ in columns}

    assert numeric == NUMERIC_COLUMNS
    assert currencies == dict.fromkeys(CURRENCY_COLUMNS, ("character", 3))
    assert "timestamp with time zone" in data_types
    assert not data_types & {"real", "double precision", "timestamp without time zone", "money"}


@pytest.mark.parametrize(("table", "columns"), INDEXES)
def test_the_indexes_of_the_ticket_exist(connection: Connection, table: str, columns: str) -> None:
    # Case 5.
    definitions = connection.execute(
        text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = :table"),
        {"table": table},
    ).scalars()

    assert any(definition.endswith(f"({columns})") for definition in definitions)
