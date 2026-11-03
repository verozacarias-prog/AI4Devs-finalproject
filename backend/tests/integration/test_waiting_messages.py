"""The most messages a user may have waiting, over HTTP and against PostgreSQL (issue #125).

Cases 7 to 10 of #125. Waiting are the messages of the user still `pending` or `processing`,
the ones put off to the next day among them. Each test has a database of its own, with the test
data of the script, and talks to the API the way the dashboard does.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.settings import Settings, load_settings
from tests.support.chat_data import NOW, inbound, seed, user_id
from tests.support.doubles import FixedClock

pytestmark = pytest.mark.integration

# The cookie is Secure, so the client talks to the API over HTTPS, as a browser does.
BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
BREAD = "y 800 de pan"


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
    settings: Settings = load_settings(
        {
            "DATABASE_URL": seeded_database_url,
            "APP_ENV": "local",
            "APP_VERSION": "test",
            "DEV_ENTRY_ENABLED": "true",
            "WEB_CHAT_ENABLED": "true",
        }
    )
    app = create_app(settings, log_stream=io.StringIO(), clock=FixedClock(NOW))
    return TestClient(app, base_url=BASE_URL)


def _enter_as(client: TestClient, name: str) -> None:
    """Opens a session for that test user; the client keeps its cookie."""
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    found = next(user["id"] for user in users if user["name"] == name)
    response = client.post("/dev/session", json={"user_id": found}, headers=SAME_ORIGIN)
    assert response.status_code == 204


def _messages(engine: Engine, name: str, count: int, status: str) -> None:
    """That many messages of the user, in that state, written in the last minutes."""
    for minute in range(count):
        inbound(
            engine,
            name,
            "gasté 3500 en el súper",
            sent_at=NOW - timedelta(minutes=count - minute),
            status=status,
            locked_until=NOW + timedelta(minutes=1) if status == "processing" else None,
        )


def _send(client: TestClient, key: str | None = None) -> int:
    response = client.post(
        "/chat/messages",
        json={"text": BREAD},
        headers={**SAME_ORIGIN, "Idempotency-Key": key or str(uuid.uuid4())},
    )
    return response.status_code


def _stored(engine: Engine, name: str) -> int:
    with engine.connect() as connection:
        found: int = connection.execute(
            text("SELECT count(*) FROM inbound_message WHERE user_id = :user"),
            {"user": user_id(engine, name)},
        ).scalar_one()
    return found


def test_with_200_waiting_the_next_one_is_not_stored(client: TestClient, engine: Engine) -> None:
    # Case 7 of #125. 198 pending, one put off to tomorrow and one being processed.
    _messages(engine, "Lucía", 198, "pending")
    inbound(
        engine,
        "Lucía",
        "gasté 3500 en el súper",
        sent_at=NOW - timedelta(hours=1),
        next_attempt_at=NOW + timedelta(hours=12),
    )
    _messages(engine, "Lucía", 1, "processing")
    _enter_as(client, "Lucía")

    response = client.post(
        "/chat/messages",
        json={"text": BREAD},
        headers={**SAME_ORIGIN, "Idempotency-Key": str(uuid.uuid4())},
    )

    assert response.status_code == 429
    assert response.json() == {"error": "too_many_waiting_messages"}
    assert _stored(engine, "Lucía") == 200


def test_with_199_waiting_the_next_one_is_stored(client: TestClient, engine: Engine) -> None:
    # Case 8 of #125.
    _messages(engine, "Lucía", 199, "pending")
    _enter_as(client, "Lucía")

    assert _send(client) == 202
    assert _stored(engine, "Lucía") == 200


def test_a_repeated_key_answers_the_same_with_200_waiting(
    client: TestClient, engine: Engine
) -> None:
    # Case 9 of #125. The repeated message is one of the 200 waiting.
    _messages(engine, "Lucía", 199, "pending")
    _enter_as(client, "Lucía")
    key = str(uuid.uuid4())
    assert _send(client, key) == 202

    response = client.post(
        "/chat/messages",
        json={"text": BREAD},
        headers={**SAME_ORIGIN, "Idempotency-Key": key},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert _stored(engine, "Lucía") == 200


def test_only_her_own_messages_waiting_count(client: TestClient, engine: Engine) -> None:
    # Case 10 of #125. Hers are answered or failed, and the 200 waiting are of Pablo.
    _messages(engine, "Lucía", 200, "processed")
    _messages(engine, "Lucía", 200, "failed")
    _messages(engine, "Pablo", 200, "pending")
    _enter_as(client, "Lucía")

    assert _send(client) == 202
