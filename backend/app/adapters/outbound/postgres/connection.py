"""Creation of the database connection. Nothing outside this package imports SQLAlchemy."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

CONNECT_TIMEOUT_SECONDS = 3


def create_db_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )
