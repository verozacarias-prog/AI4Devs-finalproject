"""POST and GET /chat/messages over HTTP, against PostgreSQL (FEAT-002, its spec.md).

Cases C1-01, C1-06 to C1-09. Each test has a database of its own, with the test data of the
script, and talks to the API the way the dashboard does: it enters through the development
entry and keeps the session cookie. The API runs with a fixed clock, so the time a message is
received is the one the case says.
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
from app.adapters.inbound.message_worker.worker import create_worker
from app.settings import Settings, load_settings
from tests.support.chat_data import FIXED_REPLY, NOW, inbound, outbound, seed, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM

pytestmark = pytest.mark.integration

# The cookie is Secure, so the client talks to the API over HTTPS, as a browser does.
BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
IDEMPOTENCY_KEY = str(uuid.uuid4())
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
def settings(seeded_database_url: str) -> Settings:
    return load_settings(
        {
            "DATABASE_URL": seeded_database_url,
            "APP_ENV": "local",
            "APP_VERSION": "test",
            "DEV_ENTRY_ENABLED": "true",
            "WEB_CHAT_ENABLED": "true",
        }
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings, log_stream=io.StringIO(), clock=FixedClock(NOW))
    return TestClient(app, base_url=BASE_URL)


def _enter_as(client: TestClient, name: str) -> None:
    """Opens a session for that test user; the client keeps its cookie."""
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    found = next(user["id"] for user in users if user["name"] == name)
    response = client.post("/dev/session", json={"user_id": found}, headers=SAME_ORIGIN)
    assert response.status_code == 204


def _three_messages_of_lucia(engine: Engine) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """The conversation of C1-06: a message, its reply, and a second message."""
    first = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(minutes=2))
    reply = outbound(
        engine, first, FIXED_REPLY, created_at=NOW - timedelta(minutes=2) + timedelta(seconds=4)
    )
    second = inbound(engine, "Lucía", FUEL, sent_at=NOW - timedelta(minutes=1))
    return first, reply, second


def test_lucia_writes_and_her_message_is_stored_as_pending(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-01.
    _enter_as(client, "Lucía")

    response = client.post(
        "/chat/messages",
        json={"text": SUPERMARKET},
        headers={**SAME_ORIGIN, "Idempotency-Key": IDEMPOTENCY_KEY},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, provider, provider_message_id, user_id, from_phone, "
                "payload ->> 'text' AS text, sent_at, status, attempts, "
                "quoted_outbound_message_id FROM inbound_message"
            )
        ).all()
    assert len(rows) == 1
    row = rows[0]
    lucia = user_id(engine, "Lucía")
    assert str(row.id) == body["id"]
    assert row.provider == "web"
    assert row.user_id == lucia
    assert row.from_phone == "+000000000001"
    assert row.provider_message_id.startswith(str(lucia))
    assert row.provider_message_id.endswith(IDEMPOTENCY_KEY)
    assert row.text == SUPERMARKET
    assert row.sent_at == NOW
    assert row.status == "pending"
    assert row.attempts == 0
    assert row.quoted_outbound_message_id is None


def test_the_conversation_comes_in_order_with_the_reply_in_its_place(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-06.
    first, reply, second = _three_messages_of_lucia(engine)
    _enter_as(client, "Lucía")

    response = client.get("/chat/messages")

    assert response.status_code == 200
    body = response.json()
    messages = body["messages"]
    assert [message["id"] for message in messages] == [str(first), str(reply), str(second)]
    assert messages[0]["direction"] == "inbound"
    assert messages[0]["text"] == SUPERMARKET
    assert messages[0]["quoted_message_id"] is None
    assert messages[0]["created_at"] == "2026-10-15T14:58:00-03:00"
    assert messages[1]["direction"] == "outbound"
    assert messages[1]["text"] == FIXED_REPLY
    assert messages[1]["response_kind"] == "fixed_text"
    assert messages[1]["created_at"] == "2026-10-15T14:58:04-03:00"
    assert messages[2]["direction"] == "inbound"
    assert messages[2]["text"] == FUEL
    assert messages[2]["created_at"] == "2026-10-15T14:59:00-03:00"
    assert body["next_cursor"] == str(second)


def test_with_a_cursor_only_the_later_messages_come(client: TestClient, engine: Engine) -> None:
    # Case C1-07.
    _first, reply, second = _three_messages_of_lucia(engine)
    _enter_as(client, "Lucía")

    response = client.get("/chat/messages", params={"after": str(reply)})

    assert response.status_code == 200
    body = response.json()
    assert [message["id"] for message in body["messages"]] == [str(second)]
    assert body["messages"][0]["text"] == FUEL
    assert body["next_cursor"] == str(second)


def test_with_a_cursor_and_nothing_new_the_list_is_empty(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-08.
    _first, _reply, second = _three_messages_of_lucia(engine)
    _enter_as(client, "Lucía")

    response = client.get("/chat/messages", params={"after": str(second)})

    assert response.status_code == 200
    body = response.json()
    assert body["messages"] == []
    assert body["next_cursor"] == str(second)


def test_write_process_and_read_the_reply(client: TestClient, settings: Settings) -> None:
    # Case C1-09.
    _enter_as(client, "Lucía")
    sent = client.post(
        "/chat/messages",
        json={"text": SUPERMARKET},
        headers={**SAME_ORIGIN, "Idempotency-Key": IDEMPOTENCY_KEY},
    )
    assert sent.status_code == 202

    create_worker(settings, FixedClock(NOW), log_stream=io.StringIO(), llm=FakeLLM()).run_round()
    response = client.get("/chat/messages")

    assert response.status_code == 200
    messages = response.json()["messages"]
    assert [(message["direction"], message["text"]) for message in messages] == [
        ("inbound", SUPERMARKET),
        ("outbound", FIXED_REPLY),
    ]
    assert messages[1]["response_kind"] == "fixed_text"
