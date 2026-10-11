"""Alembic environment. Migrations are written by hand; there is no autogenerate."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine

config = context.config


def database_url() -> str:
    # A test passes the URL of its own empty database; every other run uses the environment.
    return config.get_main_option("sqlalchemy.url") or os.environ["DATABASE_URL"]


def run_migrations() -> None:
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
