"""The size limits of a request and of the web chat, against PostgreSQL (issue #81).

Cases T-1 to T-8 and T-12 of the task, from the description of its pull request. Each test has a
database of its own, with the test data of the script, and talks to the API the way the
dashboard does, with a fixed clock.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings
from tests.support.chat_data import NOW, inbound, seed
from tests.support.doubles import FixedClock
from tests.support.log_lines import events_of

pytestmark = pytest.mark.integration

BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
AS_JSON = {"Content-Type": "application/json"}
LARGEST_BODY = 64 * 1024
LARGEST_TEXT = 4096
LOADED_AT_ONCE = 200
TOO_LARGE = {"error": "content_too_large"}


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
def stream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def browser(seeded_database_url: str, stream: io.StringIO) -> TestClient:
    settings = load_settings(
        {
            "DATABASE_URL": seeded_database_url,
            "APP_ENV": "local",
            "APP_VERSION": "test",
            "DEV_ENTRY_ENABLED": "true",
            "WEB_CHAT_ENABLED": "true",
        }
    )
    app = create_app(settings, log_stream=stream, clock=FixedClock(NOW))
    return TestClient(app, base_url=BASE_URL)


@pytest.fixture
def lucia(browser: TestClient) -> TestClient:
    users: list[dict[str, str]] = browser.get("/dev/users").json()["users"]
    found = next(user["id"] for user in users if user["name"] == "Lucía")
    entered = browser.post("/dev/session", json={"user_id": found}, headers=SAME_ORIGIN)
    assert entered.status_code == 204
    return browser


def _in_parts(size: int) -> Iterator[bytes]:
    """A body with no Content-Length: the server learns its size only by reading it."""
    sent = 0
    while sent < size:
        part = min(1024, size - sent)
        sent += part
        yield b"x" * part


def _send_chat(browser: TestClient, body: bytes) -> int:
    headers = {**SAME_ORIGIN, **AS_JSON, "Idempotency-Key": str(uuid.uuid4())}
    return browser.post("/chat/messages", content=body, headers=headers).status_code


def _messages(engine: Engine, how_many: int) -> list[uuid.UUID]:
    """That many messages of Lucía in the web chat, one a minute, the last one just now."""
    return [
        inbound(
            engine,
            "Lucía",
            f"mensaje {number}",
            sent_at=NOW - timedelta(minutes=how_many - number),
        )
        for number in range(how_many)
    ]


def test_a_declared_size_over_the_limit_is_refused_before_the_origin_check(
    browser: TestClient,
) -> None:
    # Case T-1. With no session and no Origin: it would be a 403 if the origin came first.
    response = browser.post("/chat/messages", content=b"x" * (LARGEST_BODY + 1))

    assert response.status_code == 413
    assert response.json() == TOO_LARGE


def test_a_body_in_parts_over_the_limit_is_refused(browser: TestClient) -> None:
    # Case T-2. The origin is the right one: the size is only known by reading, and ADR 0016
    # says nothing is read before the origin check.
    response = browser.post(
        "/chat/messages",
        content=_in_parts(LARGEST_BODY + 1),
        headers={**SAME_ORIGIN, **AS_JSON},
    )

    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert response.json() == TOO_LARGE


def test_a_body_of_exactly_the_limit_goes_on_to_its_own_answer(lucia: TestClient) -> None:
    # Case T-3. Its text is over the limit of the text, so its own answer is that one.
    envelope = len(json.dumps({"text": ""}))
    body = json.dumps({"text": "x" * (LARGEST_BODY - envelope)}).encode()
    assert len(body) == LARGEST_BODY

    assert _send_chat(lucia, body) == 422


@pytest.mark.parametrize(
    "send",
    [
        pytest.param(
            lambda browser: browser.post("/chat/messages", content=b"x" * (LARGEST_BODY + 1)),
            id="declared",
        ),
        pytest.param(
            lambda browser: browser.post(
                "/chat/messages",
                content=_in_parts(LARGEST_BODY + 1),
                headers={**SAME_ORIGIN, **AS_JSON},
            ),
            id="in-parts",
        ),
    ],
)
def test_a_refused_body_has_its_headers_and_its_line_and_no_error_line(
    browser: TestClient, stream: io.StringIO, send: object
) -> None:
    # Case T-4.
    assert callable(send)
    response = send(browser)

    assert response.status_code == 413
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    requests = events_of(stream, "http.request")
    assert [line["result"] for line in requests] == [413]
    assert events_of(stream, "error.expected") == []
    assert events_of(stream, "error.unexpected") == []


def test_a_text_of_the_largest_size_is_stored_counting_each_emoji_as_one(
    lucia: TestClient,
) -> None:
    # Case T-5. Escaped in JSON, as `json.dumps` does, each emoji takes 12 bytes.
    body = json.dumps({"text": "😀" * LARGEST_TEXT}).encode()

    assert _send_chat(lucia, body) == 202


def test_a_text_over_the_largest_size_is_not_stored(lucia: TestClient, engine: Engine) -> None:
    # Case T-6.
    body = json.dumps({"text": "x" * (LARGEST_TEXT + 1)}).encode()

    assert _send_chat(lucia, body) == 422
    with engine.connect() as connection:
        stored = connection.execute(text("SELECT count(*) FROM inbound_message")).scalar_one()
    assert stored == 0


def test_the_first_read_brings_the_latest_messages_in_order(
    lucia: TestClient, engine: Engine
) -> None:
    # Case T-7.
    ids = [str(message) for message in _messages(engine, LOADED_AT_ONCE + 1)]

    answer = lucia.get("/chat/messages").json()

    assert [message["id"] for message in answer["messages"]] == ids[1:]
    assert answer["next_cursor"] == ids[-1]


def test_a_read_from_a_cursor_brings_every_later_message(lucia: TestClient, engine: Engine) -> None:
    # Case T-8. A limit here would skip messages, since the cursor moves to the last one read.
    ids = [str(message) for message in _messages(engine, LOADED_AT_ONCE + 2)]

    answer = lucia.get("/chat/messages", params={"after": ids[0]}).json()

    assert [message["id"] for message in answer["messages"]] == ids[1:]


def test_a_declared_size_too_long_to_be_a_number_is_refused(
    browser: TestClient, stream: io.StringIO
) -> None:
    # Case T-12. Python refuses to turn that many digits into a number.
    response = browser.post("/chat/messages", headers={"Content-Length": "9" * 5000})

    assert response.status_code == 413
    assert response.json() == TOO_LARGE
    assert events_of(stream, "error.unexpected") == []
