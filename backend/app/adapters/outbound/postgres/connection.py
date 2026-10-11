"""Creation of the database connection. Nothing outside this package imports SQLAlchemy."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

CONNECT_TIMEOUT_SECONDS = 3


def create_db_engine(database_url: str) -> Engine:
    # Never pass echo=True: SQLAlchemy would install its own handler and print every query
    # with its parameters, bypassing the log filter (docs/operacion.md 6.3).
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )
