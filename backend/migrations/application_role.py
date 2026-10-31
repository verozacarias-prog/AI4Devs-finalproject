"""Lets the application role log in (ADR 0030)."""

from __future__ import annotations

import re

from psycopg import Connection, sql
from psycopg.rows import TupleRow

from app import messages
from app.constants import APPLICATION_ROLE, EnvVar

_PASSWORD_ALGORITHM = b"scram-sha-256"
# `DATABASE_URL` carries the password as it is: anything else could change what the URL says.
_PASSWORD_SAFE_IN_A_URL = re.compile(r"[A-Za-z0-9_-]+")


def refuse_unsafe_password(password: str) -> None:
    if _PASSWORD_SAFE_IN_A_URL.fullmatch(password) is None:
        raise SystemExit(
            messages.UNSAFE_CHARACTERS_IN_ENV_VAR.format(name=EnvVar.APPLICATION_DB_PASSWORD)
        )


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
