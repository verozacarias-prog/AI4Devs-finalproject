"""A database of its own for each test that commits.

A test of a use case that commits cannot hide behind a rolled-back transaction. So the schema
is migrated once into a template, and each test gets a copy of it, which PostgreSQL makes
without running the migrations again.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _url_of(database_url: str, name: str) -> str:
    return make_url(database_url).set(database=name).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def admin_engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def migrated_template(database_url: str, admin_engine: Engine) -> Iterator[str]:
    name = f"platita_template_{uuid.uuid4().hex[:12]}"
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
        config.set_main_option("sqlalchemy.url", _url_of(database_url, name))
        command.upgrade(config, "head")
        yield name
    finally:
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))


@pytest.fixture
def fresh_database_url(
    database_url: str, admin_engine: Engine, migrated_template: str
) -> Iterator[str]:
    name = f"platita_test_{uuid.uuid4().hex[:12]}"
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{migrated_template}"'))
    try:
        yield _url_of(database_url, name)
    finally:
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
