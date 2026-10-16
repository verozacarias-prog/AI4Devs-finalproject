"""GET /queuez, against PostgreSQL (FEAT-002, its spec.md; contract in docs/04-api.md).

Cases C3-04 to C3-06: the route the external monitor watches, because the worker may hang with
the API healthy. It fails when a pending message has been waiting more than 10 minutes.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings
from tests.support.chat_data import NOW, inbound, seed
from tests.support.doubles import FixedClock

pytestmark = pytest.mark.integration

SUPERMARKET = "gasté 3500 en el súper"
FUEL = "y 1200 de nafta"


@pytest.fixture
def seeded_database_url(fresh_database_url: str) -> str:
    seed(fresh_database_url)
    return fresh_database_url


@pytest.fixture
def engine(seeded_database_url: str) -> Iterator[Engine]:
    engine = create_engine(seeded_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def client(seeded_database_url: str) -> TestClient:
    settings = load_settings(
        {
            "DATABASE_URL": seeded_database_url,
            "APP_ENV": "local",
            "APP_VERSION": "test",
            "WEB_CHAT_ENABLED": "true",
        }
    )
    return TestClient(create_app(settings, log_stream=io.StringIO(), clock=FixedClock(NOW)))


def test_with_no_message_waiting_queuez_is_ok(client: TestClient) -> None:
    # Case C3-04.
    client.cookies.clear()

    response = client.get("/queuez")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_with_a_message_waiting_more_than_10_minutes_queuez_is_unavailable(
    client: TestClient, engine: Engine
) -> None:
    # Case C3-05. Waiting since 17:49:00: 11 minutes at 18:00:00.
    waiting_since = NOW - timedelta(minutes=11)
    inbound(engine, "Lucía", SUPERMARKET, sent_at=waiting_since, next_attempt_at=waiting_since)

    response = client.get("/queuez")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_a_recent_message_or_one_delayed_on_purpose_does_not_count(
    client: TestClient, engine: Engine
) -> None:
    # Case C3-06. One waiting since 17:51:00, 9 minutes; the other delayed until the next day
    # by a usage limit.
    recent = NOW - timedelta(minutes=9)
    inbound(engine, "Lucía", SUPERMARKET, sent_at=recent, next_attempt_at=recent)
    inbound(
        engine,
        "Pablo",
        FUEL,
        sent_at=NOW - timedelta(minutes=30),
        next_attempt_at=NOW + timedelta(days=1),
    )

    response = client.get("/queuez")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
