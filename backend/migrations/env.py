"""Alembic environment. Migrations are written by hand; there is no autogenerate."""

from __future__ import annotations

import os

from alembic import command, context
from sqlalchemy import create_engine

from app.constants import EnvVar
from migrations.application_role import enable_application_role

_LATEST_REVISION = "head"

config = context.config


def is_upgrade_to_the_latest() -> bool:
    # Empty when a test runs Alembic from code. A command that only reads changes nothing.
    options = config.cmd_opts
    return (
        options is not None
        and options.cmd[0] is command.upgrade
        and options.revision == _LATEST_REVISION
    )


def run_migrations() -> None:
    # A test passes the URL of its own empty database; every other run uses the owner of the tables.
    url = config.get_main_option("sqlalchemy.url") or os.environ[EnvVar.MIGRATIONS_DATABASE_URL]
    password = os.environ[EnvVar.APPLICATION_DB_PASSWORD] if is_upgrade_to_the_latest() else None
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
            if password is not None:
                driver_connection = connection.connection.driver_connection
                assert driver_connection is not None
                enable_application_role(driver_connection, password)
    engine.dispose()


run_migrations()
