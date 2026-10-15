"""The edit mark and the logical deletion of movements (ADR 0014 and 0015): cases 111 to 115."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from tests.integration.schema.names import (
    APPLICATION_ROLE,
    Table,
)
from tests.integration.schema.rows import Home, Rows

pytestmark = pytest.mark.integration

MARKED_TABLES = [Table.TRANSACTION, Table.TRANSFER, Table.RECURRING_RULE]


def _row(rows: Rows, home: Home, table: str, **overrides: object) -> uuid.UUID:
    if table == Table.TRANSACTION:
        return rows.transaction(home, **overrides)
    if table == Table.TRANSFER:
        return rows.transfer(home.user, home.account, rows.account(home.user), **overrides)
    return rows.rule(home, **overrides)


@pytest.mark.parametrize("table", MARKED_TABLES)
def test_an_update_marks_when_and_who_even_if_it_does_not_mention_it(
    rows: Rows, table: str
) -> None:
    # Case 111.
    home = rows.home()
    row = _row(rows, home, table)
    assert rows.value(table, row, "updated_at") is None
    assert rows.value(table, row, "updated_by") is None

    rows.act_as(home.user)
    rows.update(table, row, description="corregido")

    assert isinstance(rows.value(table, row, "updated_at"), datetime)
    assert rows.value(table, row, "updated_by") == home.user


@pytest.mark.parametrize("table", MARKED_TABLES)
def test_who_updated_a_row_is_not_recorded_without_when(rows: Rows, table: str) -> None:
    # Case 112.
    home = rows.home()
    _row(rows, home, table)

    with rows.rejected_by(f"ck_{table}_updated_by"):
        _row(rows, home, table, updated_by=home.user)


@pytest.mark.parametrize("table", MARKED_TABLES)
def test_deleting_is_setting_deleted_at_and_the_database_records_who(
    rows: Rows, table: str
) -> None:
    # Case 113. The row stays.
    home = rows.home()
    row = _row(rows, home, table)

    rows.act_as(home.user)
    rows.update(table, row, deleted_at=datetime(2026, 3, 11, 15, tzinfo=UTC))

    assert rows.value(table, row, "deleted_by") == home.user


@pytest.mark.parametrize("table", MARKED_TABLES)
def test_who_deleted_a_row_is_not_recorded_without_when(rows: Rows, table: str) -> None:
    # Case 114.
    home = rows.home()
    _row(rows, home, table)

    with rows.rejected_by(f"ck_{table}_deleted_by"):
        _row(rows, home, table, deleted_by=home.user)


@pytest.mark.parametrize("table", MARKED_TABLES)
def test_the_application_role_updates_a_movement_but_cannot_delete_it(
    rows: Rows, table: str
) -> None:
    # Case 115.
    home = rows.home()
    row = _row(rows, home, table)

    rows.connection.execute(text(f"SET LOCAL ROLE {APPLICATION_ROLE}"))
    rows.update(table, row, description="corregido")

    with rows.denied():
        rows.connection.execute(
            text(f"DELETE FROM {table} WHERE id = :row_id"),  # noqa: S608
            {"row_id": row},
        )
