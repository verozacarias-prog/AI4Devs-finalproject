"""Lets the application role log in (ADR 0030)."""

from __future__ import annotations

from psycopg import Connection, sql
from psycopg.rows import TupleRow

from app.constants import APPLICATION_ROLE

_PASSWORD_ALGORITHM = b"scram-sha-256"


def enable_application_role(connection: Connection[TupleRow], password: str) -> None:
    # The hash, computed here: PostgreSQL writes a failed statement to its log, and SQLAlchemy
    # would print it too, which is why this goes through the driver.
    hashed = connection.pgconn.encrypt_password(
        password.encode(), APPLICATION_ROLE.encode(), _PASSWORD_ALGORITHM
    )
    connection.execute(
        sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
            sql.Identifier(APPLICATION_ROLE), sql.Literal(hashed.decode())
        )
    )
