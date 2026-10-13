"""Turns a write the database rejected into an error the domain knows (ADR 0001)."""

from __future__ import annotations

from collections.abc import Mapping

import psycopg
from psycopg import errors as postgres_errors
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from app.domain.errors import ConflictError, ErrorCode, StoreRejectionError


def execute_write(connection: Connection, statement: str, parameters: Mapping[str, object]) -> None:
    try:
        connection.execute(text(statement), parameters)
    except IntegrityError as error:
        raise _translated(error) from error


def _translated(error: IntegrityError) -> Exception:
    original = error.orig
    constraint = original.diag.constraint_name if isinstance(original, psycopg.Error) else None
    # A repeated unique key is a conflict the domain foresees. Anything else, such as a CHECK,
    # is a rule the use case should have enforced before writing.
    if isinstance(original, postgres_errors.UniqueViolation):
        return ConflictError(ErrorCode.CONFLICT, constraint=constraint)
    return StoreRejectionError(constraint)
