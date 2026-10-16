"""The errors and the limits of POST and GET /chat/messages, against PostgreSQL (FEAT-002).

Cases C2-01 to C2-04 and C2-09 to C2-21, from the spec.md of FEAT-002. Each test has a database
of its own, with the test data of the script, and talks to the API the way the dashboard does,
with a fixed clock.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import timedelta
from typing import Protocol

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings
from tests.support.chat_data import (
    FIXED_REPLY,
    NOW,
    alert_by_whatsapp,
    inbound,
    messages_of,
    outbound,
    seed,
    user_id,
)
from tests.support.doubles import FixedClock

pytestmark = pytest.mark.integration

BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
# The UUID the browser generated for the message of the cases.
MESSAGE_UUID = str(uuid.uuid4())
SUPERMARKET = "gasté 3500 en el súper"
FUEL = "y 1200 de nafta"
NOT_FOUND = {"error": "not_found"}
UNAUTHORIZED = {"error": "unauthorized"}
INVALID = {"error": "invalid_request"}


class ClientFor(Protocol):
    def __call__(self, name: str | None = None, *, chat: bool = True) -> TestClient: ...


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
def client_for(seeded_database_url: str) -> ClientFor:
    """A browser of its own, already inside as that test user, unless it says otherwise."""

    def build(name: str | None = None, *, chat: bool = True) -> TestClient:
        environ = {
            "DATABASE_URL": seeded_database_url,
            "APP_ENV": "local",
            "APP_VERSION": "test",
            "DEV_ENTRY_ENABLED": "true",
        }
        if chat:
            environ["WEB_CHAT_ENABLED"] = "true"
        app = create_app(load_settings(environ), log_stream=io.StringIO(), clock=FixedClock(NOW))
        browser = TestClient(app, base_url=BASE_URL)
        if name is not None:
            users: list[dict[str, str]] = browser.get("/dev/users").json()["users"]
            found = next(user["id"] for user in users if user["name"] == name)
            entered = browser.post("/dev/session", json={"user_id": found}, headers=SAME_ORIGIN)
            assert entered.status_code == 204
        return browser

    return build


def _send(
    browser: TestClient,
    message: str,
    key: str | None = MESSAGE_UUID,
    quoted: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers = dict(SAME_ORIGIN)
    if key is not None:
        headers["Idempotency-Key"] = key
    body: dict[str, object] = {"text": message}
    if quoted is not None:
        body["quoted_message_id"] = quoted
    response = browser.post("/chat/messages", json=body, headers=headers)
    answer: dict[str, object] = response.json()
    return response.status_code, answer


def _texts(browser: TestClient, after: str | None = None) -> list[str]:
    params = {} if after is None else {"after": after}
    response = browser.get("/chat/messages", params=params)
    assert response.status_code == 200
    return [message["text"] for message in response.json()["messages"]]


def _inbound_count(engine: Engine) -> int:
    with engine.connect() as connection:
        counted: int = connection.execute(text("SELECT count(*) FROM inbound_message")).scalar_one()
    return counted


def _last_seen(engine: Engine, name: str) -> object:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT last_seen_at FROM session WHERE user_id = :user_id"),
            {"user_id": user_id(engine, name)},
        ).scalar_one()


def _seen_at_ten_to_three(engine: Engine, name: str) -> None:
    """The last activity of the session of that user, at 17:50 UTC: ten minutes ago."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE session SET last_seen_at = :at WHERE user_id = :user_id"),
            {"at": NOW - timedelta(minutes=10), "user_id": user_id(engine, name)},
        )


def test_the_same_key_twice_leaves_one_message_and_answers_the_original(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-01.
    lucia = client_for("Lucía")
    first_status, first = _send(lucia, SUPERMARKET)
    assert first_status == 202

    status, again = _send(lucia, SUPERMARKET)

    assert status == 200
    assert again == {"id": first["id"], "status": "pending"}
    assert _inbound_count(engine) == 1


def test_the_same_key_of_another_user_is_another_message(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-02.
    _, of_lucia = _send(client_for("Lucía"), SUPERMARKET)

    status, of_pablo = _send(client_for("Pablo"), "cobré 50000")

    assert status == 202
    assert of_pablo["id"] != of_lucia["id"]
    assert _inbound_count(engine) == 2


def test_an_empty_text_or_one_of_only_spaces_is_not_stored(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-03.
    lucia = client_for("Lucía")

    empty = _send(lucia, "", key=str(uuid.uuid4()))
    spaces = _send(lucia, "   ", key=str(uuid.uuid4()))

    assert empty == (422, INVALID)
    assert spaces == (422, INVALID)
    assert _inbound_count(engine) == 0


def test_without_a_key_the_message_is_not_stored(client_for: ClientFor, engine: Engine) -> None:
    # Case C2-04.
    status, answer = _send(client_for("Lucía"), SUPERMARKET, key=None)

    assert (status, answer) == (422, INVALID)
    assert _inbound_count(engine) == 0


def test_asking_does_not_renew_the_session(client_for: ClientFor, engine: Engine) -> None:
    # Case C2-09.
    lucia = client_for("Lucía")
    _seen_at_ten_to_three(engine, "Lucía")

    response = lucia.get("/chat/messages")

    assert response.status_code == 200
    assert _last_seen(engine, "Lucía") == NOW - timedelta(minutes=10)


def test_writing_renews_the_session(client_for: ClientFor, engine: Engine) -> None:
    # Case C2-10.
    lucia = client_for("Lucía")
    _seen_at_ten_to_three(engine, "Lucía")

    status, _ = _send(lucia, SUPERMARKET)

    assert status == 202
    assert _last_seen(engine, "Lucía") == NOW


def test_pablo_does_not_see_the_conversation_of_lucia(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-11.
    message = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(minutes=2))
    outbound(engine, message, FIXED_REPLY, created_at=NOW - timedelta(minutes=1))

    response = client_for("Pablo").get("/chat/messages")

    assert response.status_code == 200
    assert response.json() == {"messages": [], "next_cursor": None}


def test_a_cursor_of_the_conversation_of_another_user_answers_404(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-12.
    of_lucia = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(minutes=2))
    pablo = client_for("Pablo")

    foreign = pablo.get("/chat/messages", params={"after": str(of_lucia)})
    unknown = pablo.get("/chat/messages", params={"after": str(uuid.uuid4())})

    assert (foreign.status_code, foreign.json()) == (404, NOT_FOUND)
    assert (unknown.status_code, unknown.json()) == (404, NOT_FOUND)


def test_without_a_session_or_with_an_expired_one_nothing_is_read_or_written(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-13.
    nobody = client_for()
    expired = client_for("Lucía")
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE session SET created_at = :created, last_seen_at = :seen, "
                "expires_at = :now WHERE user_id = :user_id"
            ),
            {
                "created": NOW - timedelta(hours=12),
                "seen": NOW - timedelta(minutes=1),
                "now": NOW,
                "user_id": user_id(engine, "Lucía"),
            },
        )

    for browser in (nobody, expired):
        read = browser.get("/chat/messages")
        written = _send(browser, SUPERMARKET, key=str(uuid.uuid4()))
        assert (read.status_code, read.json()) == (401, UNAUTHORIZED)
        assert written == (401, UNAUTHORIZED)
    assert _inbound_count(engine) == 0


def test_with_the_chat_off_both_endpoints_answer_404(client_for: ClientFor) -> None:
    # Case C2-14.
    lucia = client_for("Lucía", chat=False)

    read = lucia.get("/chat/messages")
    written = _send(lucia, SUPERMARKET)

    assert (read.status_code, read.json()) == (404, NOT_FOUND)
    assert written == (404, NOT_FOUND)


def test_quoting_a_reply_of_platita_to_another_user_stores_nothing(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-15.
    of_pablo = inbound(engine, "Pablo", "cobré 50000", sent_at=NOW - timedelta(minutes=2))
    reply_to_pablo = outbound(engine, of_pablo, FIXED_REPLY, created_at=NOW - timedelta(minutes=1))

    status, answer = _send(client_for("Lucía"), "era con Galicia", quoted=str(reply_to_pablo))

    assert (status, answer) == (404, NOT_FOUND)
    assert messages_of(engine, "Lucía") == []


def test_quoting_a_message_that_is_not_a_reply_of_platita_stores_nothing(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-16.
    own = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(minutes=2))
    lucia = client_for("Lucía")

    quoting_own = _send(lucia, "era con Galicia", key=str(uuid.uuid4()), quoted=str(own))
    quoting_none = _send(lucia, "era con Galicia", key=str(uuid.uuid4()), quoted=str(uuid.uuid4()))

    assert quoting_own == (404, NOT_FOUND)
    assert quoting_none == (404, NOT_FOUND)
    assert messages_of(engine, "Lucía") == [(SUPERMARKET, None)]


def test_quoting_a_reply_of_platita_to_the_same_user_is_stored(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-17.
    own = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(minutes=2))
    reply = outbound(engine, own, FIXED_REPLY, created_at=NOW - timedelta(minutes=1))

    status, _ = _send(client_for("Lucía"), "era con Galicia", quoted=str(reply))

    assert status == 202
    assert messages_of(engine, "Lucía") == [(SUPERMARKET, None), ("era con Galicia", reply)]


def test_a_purged_message_does_not_show_up(client_for: ClientFor, engine: Engine) -> None:
    # Case C2-19.
    inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(minutes=2), purged=True)
    inbound(engine, "Lucía", FUEL, sent_at=NOW - timedelta(minutes=1))

    assert _texts(client_for("Lucía")) == [FUEL]


def test_what_came_by_whatsapp_does_not_show_up_in_the_chat(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-20.
    inbound(engine, "Lucía", "cobré 50000", sent_at=NOW - timedelta(minutes=3), provider="meta")
    alert_by_whatsapp(engine, "Lucía", "Te estás pasando", created_at=NOW - timedelta(minutes=2))
    inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(minutes=1))

    assert _texts(client_for("Lucía")) == [SUPERMARKET]


def test_two_messages_at_the_same_time_are_not_lost_with_the_cursor(
    client_for: ClientFor, engine: Engine
) -> None:
    # Case C2-21.
    same_time = NOW - timedelta(minutes=1)
    inbound(engine, "Lucía", SUPERMARKET, sent_at=same_time)
    inbound(engine, "Lucía", FUEL, sent_at=same_time)
    lucia = client_for("Lucía")
    whole = lucia.get("/chat/messages").json()["messages"]
    assert sorted(message["text"] for message in whole) == sorted([SUPERMARKET, FUEL])

    after_first = _texts(lucia, after=whole[0]["id"])

    assert after_first == [whole[1]["text"]]
