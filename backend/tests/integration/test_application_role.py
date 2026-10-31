"""The API and the worker reach the database with `platita_app`, against PostgreSQL (issue #83).

Cases T-1 to T-8 of the task, from the description of its pull request. Each case runs the
migrations the way Compose does, as a process with its environment. A role belongs to the whole
server, so the local stack uses the same one: a fixture leaves it as it found it.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, OperationalError

from migrations.application_role import enable_application_role

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[2]
COMPOSE_FILE = BACKEND_DIR.parent / "docker-compose.yml"
APPLICATION_ROLE = "platita_app"
OWNER_URL_VARIABLE = "MIGRATIONS_DATABASE_URL"
PASSWORD_VARIABLE = "APPLICATION_DB_PASSWORD"
INSUFFICIENT_PRIVILEGE = "42501"
TABLES_WITHOUT_DELETE = ("transaction", "transfer", "recurring_rule")


@pytest.fixture(autouse=True)
def role_as_it_was(admin_engine: Engine) -> Iterator[None]:
    with admin_engine.connect() as connection:
        can_login, password = connection.execute(
            text("SELECT rolcanlogin, rolpassword FROM pg_authid WHERE rolname = :role"),
            {"role": APPLICATION_ROLE},
        ).one()
    yield
    with admin_engine.connect() as connection:
        restore = connection.execute(
            text(
                "SELECT format('ALTER ROLE platita_app %s PASSWORD %L', "
                "CAST(:login AS text), CAST(:password AS text))"
            ),
            {"login": "LOGIN" if can_login else "NOLOGIN", "password": password},
        ).scalar_one()
        connection.exec_driver_sql(restore)


def _migrate(**variables: str) -> subprocess.CompletedProcess[str]:
    """`alembic upgrade head` as Compose runs it, with only the given variables of the task."""
    environment = {
        name: value
        for name, value in os.environ.items()
        if name not in {"DATABASE_URL", OWNER_URL_VARIABLE, PASSWORD_VARIABLE}
    }
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**environment, **variables},
        capture_output=True,
        text=True,
        check=False,
    )


def _migrate_with(owner_url: str, password: str) -> None:
    done = _migrate(**{OWNER_URL_VARIABLE: owner_url, PASSWORD_VARIABLE: password})
    assert done.returncode == 0, done.stderr


def _as_application(owner_url: str, password: str) -> Engine:
    url = make_url(owner_url).set(username=APPLICATION_ROLE, password=password)
    return create_engine(url)


def _password() -> str:
    return uuid.uuid4().hex


def test_after_migrating_the_role_logs_in_with_its_password(fresh_database_url: str) -> None:
    # Case T-1.
    password = _password()

    _migrate_with(fresh_database_url, password)

    engine = _as_application(fresh_database_url, password)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_user")).scalar_one() == APPLICATION_ROLE
    engine.dispose()


def test_migrating_again_changes_the_password(fresh_database_url: str) -> None:
    # Case T-2. There is nothing left to migrate the second time.
    old = _password()
    new = _password()
    _migrate_with(fresh_database_url, old)

    _migrate_with(fresh_database_url, new)

    engine = _as_application(fresh_database_url, new)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    engine.dispose()
    refused = _as_application(fresh_database_url, old)
    with pytest.raises(OperationalError):
        refused.connect()
    refused.dispose()


@pytest.mark.parametrize("table", TABLES_WITHOUT_DELETE)
def test_logged_in_as_the_role_a_movement_can_be_read_but_not_deleted(
    fresh_database_url: str, table: str
) -> None:
    # Case T-3. Case 115 proves the rights with SET ROLE; this one, with a real login.
    password = _password()
    _migrate_with(fresh_database_url, password)

    engine = _as_application(fresh_database_url, password)
    with engine.connect() as connection:
        assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0  # noqa: S608
        with pytest.raises(DBAPIError) as refused:
            connection.execute(text(f"DELETE FROM {table}"))  # noqa: S608
    engine.dispose()
    assert getattr(refused.value.orig, "sqlstate", None) == INSUFFICIENT_PRIVILEGE


def test_a_password_with_quotes_and_spaces_works(fresh_database_url: str) -> None:
    # Case T-4.
    password = f"a'b \"c d {_password()}"

    _migrate_with(fresh_database_url, password)

    engine = _as_application(fresh_database_url, password)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    engine.dispose()


def test_migrating_without_the_owner_url_fails_and_does_not_use_the_url_of_the_application(
    fresh_database_url: str,
) -> None:
    # Case T-5.
    done = _migrate(**{"DATABASE_URL": fresh_database_url, PASSWORD_VARIABLE: _password()})

    assert done.returncode != 0
    assert OWNER_URL_VARIABLE in done.stderr


def test_migrating_without_the_password_fails_and_names_it(fresh_database_url: str) -> None:
    # Case T-5.
    done = _migrate(**{OWNER_URL_VARIABLE: fresh_database_url})

    assert done.returncode != 0
    assert PASSWORD_VARIABLE in done.stderr


def test_a_failed_step_does_not_print_the_password(
    fresh_database_url: str, admin_engine: Engine
) -> None:
    # Case T-6. An owner with no right over roles, so the step is the one that fails.
    owner = f"owner_{uuid.uuid4().hex[:12]}"
    owner_password = _password()
    password = _password()
    database = create_engine(fresh_database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f"CREATE ROLE {owner} LOGIN PASSWORD '{owner_password}'")
    with database.connect() as connection:
        connection.exec_driver_sql(f"GRANT ALL ON alembic_version TO {owner}")
    limited = (
        make_url(fresh_database_url)
        .set(username=owner, password=owner_password)
        .render_as_string(hide_password=False)
    )
    try:
        done = _migrate(**{OWNER_URL_VARIABLE: limited, PASSWORD_VARIABLE: password})
    finally:
        with database.connect() as connection:
            connection.exec_driver_sql(f"DROP OWNED BY {owner}")
        database.dispose()
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(f"DROP ROLE {owner}")

    assert done.returncode != 0
    # A missing variable would fail too, before the step ever ran.
    assert "KeyError" not in done.stderr
    assert password not in done.stdout
    assert password not in done.stderr


def test_the_statement_carries_the_hash_and_not_the_password(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Case T-8. PostgreSQL writes a failed statement to its log, whatever `log_statement` says.
    password = _password()
    sent: list[str] = []
    monkeypatch.setattr(
        psycopg.Connection,
        "execute",
        lambda connection, statement: sent.append(statement.as_string(connection)),
    )
    url = make_url(database_url).set(drivername="postgresql")

    with psycopg.connect(url.render_as_string(hide_password=False)) as connection:
        enable_application_role(connection, password)

    assert len(sent) == 1
    assert password not in sent[0]
    assert "SCRAM-SHA-256$" in sent[0]


def _service(name: str) -> str:
    found = re.search(
        rf"^  {name}:\n(.*?)(?=^  \S|^\S|\Z)",
        COMPOSE_FILE.read_text(),
        re.MULTILINE | re.DOTALL,
    )
    assert found is not None
    return found.group(1)


@pytest.mark.parametrize("service", ["api", "worker"])
def test_compose_connects_the_api_and_the_worker_with_the_role(service: str) -> None:
    # Case T-7.
    assert (
        "DATABASE_URL: postgresql+psycopg://platita_app:${APPLICATION_DB_PASSWORD}@db:5432/"
        in _service(service)
    )


def test_compose_runs_the_migrations_with_the_owner() -> None:
    # Case T-7.
    migrations = _service("migrations")

    assert (
        "MIGRATIONS_DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:"
        in migrations
    )
    assert "APPLICATION_DB_PASSWORD: ${APPLICATION_DB_PASSWORD" in migrations
    assert "\n      DATABASE_URL:" not in migrations
