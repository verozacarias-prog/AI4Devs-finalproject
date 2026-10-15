"""The development entry of the local environment, over HTTP (docs/04-api.md, ADR 0016).

Cases 21 to 27, 29, 31 to 54, 79 and 81. Each test has a database of its own, with the test
data of the script, and talks to the API the way the dashboard does.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from datetime import timedelta

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.operator_commands.seed_test_data import main as seed_test_data
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from app.settings import load_settings
from app.shared.clock import SystemClock
from tests.support.log_lines import events_of

pytestmark = pytest.mark.integration

# The cookie is Secure, so the client talks to the API over HTTPS, as a browser does.
BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
COOKIE = "__Host-sid"
REAL_PHONE = "+5491100000000"
NOT_FOUND = {"error": "not_found"}
UNAUTHORIZED = {"error": "unauthorized"}
FORBIDDEN = {"error": "forbidden"}
INVALID_REQUEST = {"error": "invalid_request"}
SESSION_COLUMNS = "id, user_id, token_hash, created_at, last_seen_at, expires_at, revoked_at"


@pytest.fixture
def seeded_database_url(fresh_database_url: str) -> str:
    code = seed_test_data(
        {"DATABASE_URL": fresh_database_url, "APP_ENV": "local"}, io.StringIO(), io.StringIO()
    )
    assert code == 0, "the test data script failed"
    return fresh_database_url


@pytest.fixture
def engine(seeded_database_url: str) -> Iterator[Engine]:
    engine = create_engine(seeded_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def stream() -> io.StringIO:
    return io.StringIO()


def _client(
    database_url: str,
    *,
    environment: str = "local",
    dev_entry: str | None = "true",
    stream: io.StringIO | None = None,
) -> TestClient:
    environ = {"DATABASE_URL": database_url, "APP_ENV": environment, "APP_VERSION": "test"}
    if dev_entry is not None:
        environ["DEV_ENTRY_ENABLED"] = dev_entry
    app = create_app(load_settings(environ), log_stream=stream or io.StringIO())
    return TestClient(app, base_url=BASE_URL)


@pytest.fixture
def client(seeded_database_url: str, stream: io.StringIO) -> TestClient:
    return _client(seeded_database_url, stream=stream)


def _user_id(client: TestClient, name: str) -> str:
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    return next(user["id"] for user in users if user["name"] == name)


def _enter(client: TestClient, user_id: str) -> httpx2.Response:
    return client.post("/dev/session", json={"user_id": user_id}, headers=SAME_ORIGIN)


def _enter_as(client: TestClient, name: str) -> str:
    """Opens a session for that test user and returns the token of its cookie."""
    response = _enter(client, _user_id(client, name))
    assert response.status_code == 204
    token: str = response.cookies[COOKIE]
    return token


def _sessions(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text("SELECT count(*) FROM session")).scalar_one())


def _add_user_with_a_real_phone(engine: Engine) -> str:
    clock = SystemClock()
    unit_of_work = SqlAlchemyUnitOfWork(engine)
    with unit_of_work:
        user = CreateTestUser(clock).execute(
            unit_of_work, name="Vero", phone=REAL_PHONE, terms_version="local-seed-1"
        )
        unit_of_work.commit()
    return str(user.id)


# B. GET /dev/users


def test_the_list_has_the_test_users_in_order_with_their_id_and_name_only(
    client: TestClient,
) -> None:
    # Case 21.
    response = client.get("/dev/users")

    assert response.status_code == 200
    body = response.json()
    assert list(body) == ["users"]
    assert [user["name"] for user in body["users"]] == ["Lucía", "Pablo", "Sofía"]
    assert all(set(user) == {"id", "name"} for user in body["users"])
    assert len({user["id"] for user in body["users"]}) == 3


def test_a_user_with_a_real_phone_is_not_in_the_list(client: TestClient, engine: Engine) -> None:
    # Case 22.
    real_id = _add_user_with_a_real_phone(engine)

    users = client.get("/dev/users").json()["users"]

    assert [user["name"] for user in users] == ["Lucía", "Pablo", "Sofía"]
    assert real_id not in {user["id"] for user in users}


def test_without_test_users_the_list_is_empty(fresh_database_url: str) -> None:
    # Case 23.
    response = _client(fresh_database_url).get("/dev/users")

    assert response.status_code == 200
    assert response.json() == {"users": []}


def test_the_list_asks_for_no_session(client: TestClient) -> None:
    # Case 24.
    client.cookies.clear()

    response = client.get("/dev/users")

    assert response.status_code == 200
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("dev_entry", [None, "false"], ids=["unset", "false"])
def test_with_the_entry_off_the_list_does_not_exist(
    seeded_database_url: str, dev_entry: str | None
) -> None:
    # Case 25.
    response = _client(seeded_database_url, dev_entry=dev_entry).get("/dev/users")

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


def test_in_demo_the_list_does_not_exist(seeded_database_url: str) -> None:
    # Case 26.
    response = _client(seeded_database_url, environment="demo").get("/dev/users")

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


# C. POST /dev/session with user_id


def test_choosing_a_user_answers_with_the_session_cookie_and_no_body(client: TestClient) -> None:
    # Case 27.
    response = _enter(client, _user_id(client, "Lucía"))

    assert response.status_code == 204
    assert response.content == b""
    cookie = response.headers["set-cookie"]
    name_and_value, *attributes = [part.strip() for part in cookie.split(";")]
    assert name_and_value.startswith("__Host-sid=")
    assert len(name_and_value) > len("__Host-sid=")
    assert {attribute.lower() for attribute in attributes} == {
        "httponly",
        "secure",
        "samesite=strict",
        "path=/",
    }


def test_the_session_is_of_that_user_and_lasts_twelve_hours(
    client: TestClient, engine: Engine
) -> None:
    # Case 28, against the real table.
    lucia_id = _user_id(client, "Lucía")

    _enter(client, lucia_id)

    with engine.connect() as connection:
        [session] = connection.execute(text(f"SELECT {SESSION_COLUMNS} FROM session")).all()  # noqa: S608
    assert str(session.user_id) == lucia_id
    assert session.expires_at - session.created_at == timedelta(hours=12)
    assert session.last_seen_at == session.created_at
    assert session.revoked_at is None


def test_the_token_of_the_cookie_is_in_no_column(client: TestClient, engine: Engine) -> None:
    # Case 29.
    token = _enter_as(client, "Lucía")

    with engine.connect() as connection:
        [session] = connection.execute(text(f"SELECT {SESSION_COLUMNS} FROM session")).all()  # noqa: S608
    assert session.token_hash
    assert all(token not in str(value) for value in session)


def test_entering_twice_gives_two_tokens_and_both_work(client: TestClient, engine: Engine) -> None:
    # Case 30.
    first = _enter_as(client, "Lucía")
    second = _enter_as(client, "Lucía")

    assert first != second
    assert _sessions(engine) == 2
    for token in (first, second):
        client.cookies.clear()
        client.cookies.set(COOKIE, token)
        assert client.get("/me").status_code == 200


def test_a_user_who_does_not_exist_is_not_found(client: TestClient, engine: Engine) -> None:
    # Case 31.
    response = _enter(client, "00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert "set-cookie" not in response.headers
    assert _sessions(engine) == 0


def test_a_user_with_a_real_phone_cannot_be_chosen(client: TestClient, engine: Engine) -> None:
    # Case 32.
    response = _enter(client, _add_user_with_a_real_phone(engine))

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert "set-cookie" not in response.headers
    assert _sessions(engine) == 0


@pytest.mark.parametrize(
    "body",
    [{"user_id": "lucia"}, {}, {"user_id": None}],
    ids=["not-a-uuid", "empty", "null"],
)
def test_a_body_outside_the_contract_is_an_invalid_request(
    client: TestClient, engine: Engine, body: dict[str, str | None]
) -> None:
    # Case 33.
    response = client.post("/dev/session", json=body, headers=SAME_ORIGIN)

    assert response.status_code == 422
    assert response.json() == INVALID_REQUEST
    assert _sessions(engine) == 0


def test_with_the_entry_off_nobody_enters(seeded_database_url: str, engine: Engine) -> None:
    # Case 34.
    lucia_id = _user_id(_client(seeded_database_url), "Lucía")

    response = _enter(_client(seeded_database_url, dev_entry=None), lucia_id)

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert _sessions(engine) == 0


@pytest.mark.parametrize("with_link", [False, True], ids=["alone", "with-link"])
def test_in_demo_nobody_enters_by_choosing_a_user(
    seeded_database_url: str, engine: Engine, with_link: bool
) -> None:
    # Case 35.
    body = {"user_id": _user_id(_client(seeded_database_url), "Lucía")}
    if with_link:
        body["access_token"] = "a-personal-link"

    response = _client(seeded_database_url, environment="demo").post(
        "/dev/session", json=body, headers=SAME_ORIGIN
    )

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert "set-cookie" not in response.headers
    assert _sessions(engine) == 0


@pytest.mark.parametrize("environment", ["local", "demo"])
def test_a_personal_link_answers_like_one_that_does_not_exist(
    seeded_database_url: str, engine: Engine, environment: str
) -> None:
    # Case 36.
    response = _client(seeded_database_url, environment=environment).post(
        "/dev/session", json={"access_token": "a-personal-link"}, headers=SAME_ORIGIN
    )

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert _sessions(engine) == 0


# D. GET /me and how long a session is valid


def test_me_is_the_user_of_the_session(client: TestClient) -> None:
    # Case 37.
    pablo_id = _user_id(client, "Pablo")
    _enter(client, pablo_id)

    response = client.get("/me")

    assert response.status_code == 200
    assert response.json() == {"id": pablo_id, "name": "Pablo"}


def test_without_a_cookie_nobody_is_authenticated(client: TestClient) -> None:
    # Case 38.
    response = client.get("/me")

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_a_token_of_no_session_is_not_authenticated(client: TestClient) -> None:
    # Case 39.
    _enter_as(client, "Lucía")
    client.cookies.clear()
    client.cookies.set(COOKIE, "not-a-token-of-anybody")

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


@pytest.mark.parametrize(
    "aging",
    [
        "revoked_at = now()",
        # Opened a little over twelve hours ago and used two minutes ago.
        "created_at = now() - interval '12 hours 1 minute', "
        "expires_at = now() - interval '1 minute', "
        "last_seen_at = now() - interval '2 minutes'",
        "last_seen_at = now() - interval '31 minutes'",
    ],
    ids=["40-revoked", "41-twelve-hours", "42-idle"],
)
def test_a_session_that_is_over_answers_like_no_session(
    client: TestClient, engine: Engine, aging: str
) -> None:
    # Cases 40, 41 and 42. The exact minute is checked with a fixed clock, in the unit tests:
    # here the clock of the database and the one of the API may be a moment apart.
    _enter_as(client, "Lucía")
    assert client.get("/me").status_code == 200
    with engine.begin() as connection:
        connection.execute(text(f"UPDATE session SET {aging}"))  # noqa: S608

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_a_request_within_thirty_minutes_counts_as_activity(
    client: TestClient, engine: Engine
) -> None:
    # Case 43.
    _enter_as(client, "Lucía")
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE session SET created_at = now() - interval '1 hour', "
                "last_seen_at = now() - interval '28 minutes'"
            )
        )

    response = client.get("/me")

    assert response.status_code == 200
    with engine.connect() as connection:
        idle = connection.execute(text("SELECT now() - last_seen_at FROM session")).scalar_one()
    assert idle < timedelta(minutes=1)


@pytest.mark.parametrize("environment", ["local", "demo", "production"])
def test_me_exists_with_the_development_entry_off(
    seeded_database_url: str, environment: str
) -> None:
    # Case 44. It answers that there is no session, not that the route does not exist.
    response = _client(seeded_database_url, environment=environment, dev_entry=None).get("/me")

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


# E. Requests that change something


@pytest.mark.parametrize(
    "origin",
    ["https://evil.example", "https://testserver.evil.example", "null"],
    ids=["other-site", "look-alike", "opaque"],
)
def test_a_request_from_another_origin_is_forbidden(
    client: TestClient, engine: Engine, origin: str
) -> None:
    # Case 45.
    lucia_id = _user_id(client, "Lucía")

    response = client.post("/dev/session", json={"user_id": lucia_id}, headers={"Origin": origin})

    assert response.status_code == 403
    assert response.json() == FORBIDDEN
    assert "set-cookie" not in response.headers
    assert _sessions(engine) == 0


def test_a_request_without_origin_is_forbidden(client: TestClient, engine: Engine) -> None:
    # Case 46.
    lucia_id = _user_id(client, "Lucía")

    response = client.post("/dev/session", json={"user_id": lucia_id})

    assert response.status_code == 403
    assert response.json() == FORBIDDEN
    assert _sessions(engine) == 0


@pytest.mark.parametrize(
    "content_type",
    ["text/plain", "application/x-www-form-urlencoded", None],
    ids=["text", "form", "missing"],
)
def test_a_request_that_is_not_json_is_forbidden(
    client: TestClient, engine: Engine, content_type: str | None
) -> None:
    # Case 47. The body is valid JSON: only its declared type is wrong.
    lucia_id = _user_id(client, "Lucía")
    headers = SAME_ORIGIN | ({"Content-Type": content_type} if content_type else {})

    response = client.post(
        "/dev/session", content=f'{{"user_id": "{lucia_id}"}}'.encode(), headers=headers
    )

    assert response.status_code == 403
    assert response.json() == FORBIDDEN
    assert _sessions(engine) == 0


@pytest.mark.parametrize("body", [b"{not json", b"", b"\xff\xfe"], ids=["broken", "empty", "bytes"])
def test_a_request_from_another_origin_is_forbidden_whatever_its_body_is(
    client: TestClient, engine: Engine, stream: io.StringIO, body: bytes
) -> None:
    # Case 79. The origin is checked before anything the request sent is read.
    response = client.post(
        "/dev/session",
        content=body,
        headers={"Origin": "https://evil.example", "Content-Type": "application/json"},
    )

    assert response.status_code == 403
    assert response.json() == FORBIDDEN
    assert _sessions(engine) == 0
    # A refused request still leaves its line.
    assert [line["result"] for line in events_of(stream, "http.request")] == [403]


def test_a_refused_request_is_answered_like_any_other(
    client: TestClient, stream: io.StringIO
) -> None:
    # Case 81. Refused before reaching its endpoint, it still carries its reference and the
    # security headers, and leaves its line.
    response = client.post("/dev/session", json={}, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    [line] = [line for line in events_of(stream, "http.request") if line["result"] == 403]
    assert line["request_id"] == response.headers["X-Request-Id"]


def test_a_read_needs_no_origin(client: TestClient) -> None:
    # Case 48.
    _enter_as(client, "Lucía")

    for path in ("/dev/users", "/me"):
        response = client.get(path)
        assert "origin" not in response.request.headers
        assert response.status_code == 200


# F. Logs


def test_starting_with_the_entry_on_is_logged(
    seeded_database_url: str, stream: io.StringIO
) -> None:
    # Case 49.
    _client(seeded_database_url, stream=stream)

    assert len(events_of(stream, "dev.scaffold_enabled")) == 1


@pytest.mark.parametrize("dev_entry", [None, "false"], ids=["unset", "false"])
def test_starting_with_the_entry_off_logs_nothing_about_it(
    seeded_database_url: str, stream: io.StringIO, dev_entry: str | None
) -> None:
    # Case 49.
    _client(seeded_database_url, dev_entry=dev_entry, stream=stream)

    assert events_of(stream, "dev.scaffold_enabled") == []


def test_opening_a_session_is_logged_with_who_and_how(
    client: TestClient, engine: Engine, stream: io.StringIO
) -> None:
    # Case 50.
    lucia_id = _user_id(client, "Lucía")

    response = _enter(client, lucia_id)

    with engine.connect() as connection:
        session_id = connection.execute(text("SELECT id FROM session")).scalar_one()
    [line] = events_of(stream, "auth.session_created")
    assert line["user_id"] == lucia_id
    assert line["session_id"] == str(session_id)
    assert line["method"] == "dev_user_list"
    assert line["request_id"] == response.headers["X-Request-Id"]


def test_no_log_line_carries_the_token_the_name_or_the_phone(
    client: TestClient, stream: io.StringIO
) -> None:
    # Case 51.
    token = _enter_as(client, "Lucía")
    client.get("/me")

    logged = stream.getvalue()
    assert "auth.session_created" in logged
    for secret in (token, "__Host-sid", "Lucía", "+000000000001", "000000000001"):
        assert secret not in logged
    assert "[redacted]" not in logged


def test_a_refused_entry_is_not_logged_as_a_session(
    client: TestClient, stream: io.StringIO
) -> None:
    # Case 52.
    response = _enter(client, "00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert events_of(stream, "auth.session_created") == []


# G. Closing the session


def test_logging_out_revokes_the_session_and_clears_the_cookie(
    client: TestClient, engine: Engine
) -> None:
    # Case 53.
    token = _enter_as(client, "Lucía")

    response = client.post(
        "/auth/logout", headers=SAME_ORIGIN | {"Content-Type": "application/json"}
    )

    assert response.status_code == 204
    cleared = response.headers["set-cookie"].lower()
    assert cleared.startswith('__host-sid="";') or cleared.startswith("__host-sid=;")
    assert "max-age=0" in cleared
    assert {"secure", "path=/"} <= {part.strip() for part in cleared.split(";")}
    with engine.connect() as connection:
        revoked_at = connection.execute(text("SELECT revoked_at FROM session")).scalar_one()
    assert revoked_at is not None
    # The browser dropped the cookie; someone who kept the token cannot use it either.
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    again = client.get("/me")
    assert again.status_code == 401
    assert again.json() == UNAUTHORIZED


def test_logging_out_without_a_session_is_not_authenticated(client: TestClient) -> None:
    # Case 54.
    response = client.post(
        "/auth/logout", headers=SAME_ORIGIN | {"Content-Type": "application/json"}
    )

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED
