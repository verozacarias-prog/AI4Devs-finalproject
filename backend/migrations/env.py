"""Alembic environment. Migrations are written by hand; there is no autogenerate."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine

from app.constants import EnvVar
from migrations.application_role import enable_application_role

config = context.config


def run_migrations() -> None:
    # A test passes the URL of its own empty database and logs in as nobody else. Every other run
    # uses the environment: the owner of the tables migrates, and the application role is enabled.
    test_url = config.get_main_option("sqlalchemy.url")
    url = test_url or os.environ[EnvVar.MIGRATIONS_DATABASE_URL]
    password = None if test_url else os.environ[EnvVar.APPLICATION_DB_PASSWORD]
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
