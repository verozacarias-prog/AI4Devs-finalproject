"""Case 6: migrations run cleanly from an empty database. Case C2-57 of FEAT-005: the periods
that do not match their cadence become custom, with the same dates."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture
def empty_database_url(database_url: str) -> Iterator[str]:
    name = f"platita_mig_{uuid.uuid4().hex[:12]}"
    admin = create_engine(database_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield make_url(database_url).set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


def test_upgrade_head_on_an_empty_database_installs_the_extensions(
    empty_database_url: str,
) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", empty_database_url)

    command.upgrade(config, "head")

    engine = create_engine(empty_database_url)
    with engine.connect() as connection:
        installed = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())
    engine.dispose()
    assert {"vector", "btree_gist"} <= installed


def test_the_migration_leaves_as_custom_the_periods_that_do_not_match_their_cadence(
    empty_database_url: str,
) -> None:
    # Case C2-57.
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", empty_database_url)
    command.upgrade(config, "0006")

    insert = text(
        "INSERT INTO budget_period (user_id, period_type, period_start, period_end, "
        "primary_currency, status) VALUES (:user_id, :period_type, :period_start, :period_end, "
        "'ARS', :status) RETURNING id"
    )
    engine = create_engine(empty_database_url)
    with engine.begin() as connection:
        user_id = connection.execute(
            text(
                "INSERT INTO app_user (name, whatsapp_phone, country, time_zone, "
                "primary_currency, terms_accepted_at, terms_version, onboarding_status) VALUES "
                "('Lucía', '+000000000001', 'AR', 'America/Argentina/Buenos_Aires', 'ARS', now(), "
                "'1', 'completed') RETURNING id"
            )
        ).scalar_one()
        short_confirmed = connection.execute(
            insert,
            {
                "user_id": user_id,
                "period_type": "monthly",
                "period_start": date(2026, 11, 15),
                "period_end": date(2026, 11, 30),
                "status": "confirmed",
            },
        ).scalar_one()
        off_calendar = connection.execute(
            insert,
            {
                "user_id": user_id,
                "period_type": "biweekly",
                "period_start": date(2026, 9, 10),
                "period_end": date(2026, 9, 24),
                "status": "draft",
            },
        ).scalar_one()
        whole_month = connection.execute(
            insert,
            {
                "user_id": user_id,
                "period_type": "monthly",
                "period_start": date(2026, 10, 10),
                "period_end": date(2026, 11, 9),
                "status": "confirmed",
            },
        ).scalar_one()

    command.upgrade(config, "head")

    with engine.connect() as connection:
        stored = {
            row.id: (row.period_type, row.period_start, row.period_end)
            for row in connection.execute(
                text("SELECT id, period_type, period_start, period_end FROM budget_period")
            )
        }
    engine.dispose()
    assert stored == {
        short_confirmed: ("custom", date(2026, 11, 15), date(2026, 11, 30)),
        off_calendar: ("custom", date(2026, 9, 10), date(2026, 9, 24)),
        whole_month: ("monthly", date(2026, 10, 10), date(2026, 11, 9)),
    }
