"""What the web chat and the worker leave in the logs, against PostgreSQL (FEAT-002, its spec.md).

Cases C3-01 to C3-03 and C3-18 to C3-21: no line carries the text of a message or a phone, the
processing of a message is followed by its identifier, and a line written while the process knows
whose it is carries the user (docs/operacion.md 6.3). The API and the worker write their lines in
a stream the test reads.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.message_worker.worker import create_worker
from app.settings import Settings, load_settings
from tests.support.chat_data import (
    NOW,
    REPLY_REJECTION,
    inbound,
    reject_every_inbound_message,
    reject_every_reply,
    seed,
    user_id,
)
from tests.support.doubles import FixedClock
from tests.support.log_lines import events_of, lines_of

pytestmark = pytest.mark.integration

BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
IDEMPOTENCY_KEY = str(uuid.uuid4())
SUPERMARKET = "gasté 3500 en el súper"
# What no line may carry: the amount, the words, the phone and the name of Lucía.
PERSONAL_DATA = ("3500", "súper", "+000000000001", "Lucía")


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


def _enter_as(client: TestClient, name: str) -> None:
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    found = next(user["id"] for user in users if user["name"] == name)
    response = client.post("/dev/session", json={"user_id": found}, headers=SAME_ORIGIN)
    assert response.status_code == 204


def _free_text_of(stream: io.StringIO) -> str:
    """Every value of every line, except the moment and the identifiers.

    Those have a fixed shape the filter checks, and a random one may hold "3500" by chance:
    a timestamp such as "…:13.350012" or a hexadecimal id.
    """
    return "\n".join(
        str(value)
        for line in lines_of(stream)
        for key, value in line.items()
        if key != "ts" and not key.endswith("_id")
    )


def test_writing_and_reading_the_chat_leaves_no_text_or_phone_in_the_logs(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-01.
    stream = io.StringIO()
    client = TestClient(
        create_app(settings, log_stream=stream, clock=FixedClock(NOW)), base_url=BASE_URL
    )
    _enter_as(client, "Lucía")

    sent = client.post(
        "/chat/messages",
        json={"text": SUPERMARKET},
        headers={**SAME_ORIGIN, "Idempotency-Key": IDEMPOTENCY_KEY},
    )
    read = client.get("/chat/messages")

    assert (sent.status_code, read.status_code) == (202, 200)
    lucia = str(user_id(engine, "Lucía"))
    requests = {
        line["endpoint"]: line
        for line in events_of(stream, "http.request")
        if line["endpoint"] in ("POST /chat/messages", "GET /chat/messages")
    }
    assert set(requests) == {"POST /chat/messages", "GET /chat/messages"}
    assert all(line["user_id"] == lucia for line in requests.values())
    free_text = _free_text_of(stream)
    for data in PERSONAL_DATA:
        assert data not in free_text, data


def test_the_worker_leaves_one_line_per_answered_message_with_its_identifier(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-02.
    message = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(seconds=5))
    stream = io.StringIO()

    create_worker(settings, FixedClock(NOW), log_stream=stream).run_round()

    [answered] = events_of(stream, "message.answered")
    assert answered["process"] == "worker"
    assert answered["message_id"] == str(message)
    assert answered["user_id"] == str(user_id(engine, "Lucía"))
    assert isinstance(answered["duration_ms"], int)
    free_text = _free_text_of(stream)
    for data in PERSONAL_DATA:
        assert data not in free_text, data


def test_an_error_processing_a_message_leaves_its_line_with_the_message_identifier(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-03.
    message = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(seconds=5))
    reject_every_reply(engine)
    stream = io.StringIO()
    worker = create_worker(settings, FixedClock(NOW), log_stream=stream)

    worker.run_round()

    [error] = events_of(stream, "error.unexpected")
    assert error["message_id"] == str(message)
    assert isinstance(error["error_type"], str) and error["error_type"]
    assert REPLY_REJECTION not in stream.getvalue()
    # The round ended without taking the worker down: it goes on with the next one.
    assert worker.run_round() is False


def _client(settings: Settings, stream: io.StringIO) -> TestClient:
    return TestClient(
        create_app(settings, log_stream=stream, clock=FixedClock(NOW)), base_url=BASE_URL
    )


def test_the_error_of_the_worker_carries_the_user_of_the_message(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-18.
    message = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(seconds=5))
    reject_every_reply(engine)
    stream = io.StringIO()

    create_worker(settings, FixedClock(NOW), log_stream=stream).run_round()

    [error] = events_of(stream, "error.unexpected")
    assert error["user_id"] == str(user_id(engine, "Lucía"))
    assert error["message_id"] == str(message)


def test_a_foreseen_error_of_a_request_with_a_session_carries_its_user(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-19.
    of_pablo = inbound(engine, "Pablo", "y 1200 de nafta", sent_at=NOW - timedelta(minutes=1))
    stream = io.StringIO()
    client = _client(settings, stream)
    _enter_as(client, "Lucía")

    response = client.get("/chat/messages", params={"after": str(of_pablo)})

    assert response.status_code == 404
    [error] = events_of(stream, "error.expected")
    assert error["user_id"] == str(user_id(engine, "Lucía"))


def test_an_unforeseen_error_of_a_request_with_a_session_carries_its_user(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-20.
    reject_every_inbound_message(engine)
    stream = io.StringIO()
    client = TestClient(
        create_app(settings, log_stream=stream, clock=FixedClock(NOW)),
        base_url=BASE_URL,
        raise_server_exceptions=False,
    )
    _enter_as(client, "Lucía")

    response = client.post(
        "/chat/messages",
        json={"text": SUPERMARKET},
        headers={**SAME_ORIGIN, "Idempotency-Key": IDEMPOTENCY_KEY},
    )

    assert response.status_code == 500
    [error] = events_of(stream, "error.unexpected")
    assert error["user_id"] == str(user_id(engine, "Lucía"))


def test_closing_the_session_leaves_its_line_with_the_user(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-21.
    stream = io.StringIO()
    client = _client(settings, stream)
    _enter_as(client, "Lucía")

    response = client.post(
        "/auth/logout", headers=SAME_ORIGIN | {"Content-Type": "application/json"}
    )

    assert response.status_code == 204
    [line] = [
        line
        for line in events_of(stream, "http.request")
        if line["endpoint"] == "POST /auth/logout"
    ]
    assert line["user_id"] == str(user_id(engine, "Lucía"))
