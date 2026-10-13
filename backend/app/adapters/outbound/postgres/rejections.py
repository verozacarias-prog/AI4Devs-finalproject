"""Turns a write the database rejected into an error the domain knows (ADR 0001)."""

from __future__ import annotations

from collections.abc import Mapping

import psycopg
from psycopg import errors as postgres_errors
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from app.domain.errors import ConflictError, ErrorCode, StoreRejectionError

# How the schema names its primary keys. PostgreSQL reports a repeated primary key and a
# repeated unique key with the same error, and only the name tells them apart.
PRIMARY_KEY_PREFIX = "pk_"


def execute_write(connection: Connection, statement: str, parameters: Mapping[str, object]) -> None:
    try:
        connection.execute(text(statement), parameters)
    except IntegrityError as error:
        raise _translated(error) from error


def _translated(error: IntegrityError) -> Exception:
    original = error.orig
    constraint = original.diag.constraint_name if isinstance(original, psycopg.Error) else None
    # A repeated unique key is a conflict the domain foresees. Anything else is a failure of
    # the code: a CHECK the use case should have enforced, or an identifier created twice.
    is_unique_key = isinstance(original, postgres_errors.UniqueViolation) and not (
        constraint or PRIMARY_KEY_PREFIX
    ).startswith(PRIMARY_KEY_PREFIX)
    if is_unique_key:
        return ConflictError(ErrorCode.CONFLICT, constraint=constraint)
    return StoreRejectionError(constraint)
