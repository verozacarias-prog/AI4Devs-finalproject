"""The personal links of the demo environment (ADR 0016, docs/04-api.md, issue #84).

Cases 1 to 18, 20, 30 to 32 and 40 to 44 of the descriptions of the pull requests. Each test has a
database of its own, runs the commands the way a person does and talks to the API the way the
dashboard does.
"""

from __future__ import annotations

import io
import re
import threading
import time
from collections.abc import Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.operator_commands.create_personal_link import (
    main as create_personal_link,
)
from app.adapters.inbound.operator_commands.regenerate_personal_link import (
    main as regenerate_personal_link,
)
from app.settings import load_settings
from tests.support.log_lines import events_of

pytestmark = pytest.mark.integration

BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
COOKIE = "__Host-sid"
SERVER_KEY = "only-for-the-tests-of-the-personal-links"
OK = 0
LINK_VALUE = re.compile(r"/app/#(\S+)")
NOT_FOUND = {"error": "not_found"}
NOTICE_REQUIRED = {"error": "test_notice_required", "notice_version": "demo-1"}


@pytest.fixture
def engine(fresh_database_url: str) -> Iterator[Engine]:
    engine = create_engine(fresh_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def stream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def client(fresh_database_url: str, stream: io.StringIO) -> TestClient:
    return _client(fresh_database_url, stream)


def _client(database_url: str, stream: io.StringIO | None = None) -> TestClient:
    environ = {
        "DATABASE_URL": database_url,
        "APP_ENV": "demo",
        "APP_VERSION": "test",
        "DEV_ENTRY_ENABLED": "true",
        "SERVER_SECRET_KEY": SERVER_KEY,
    }
    return TestClient(
        create_app(load_settings(environ), log_stream=stream or io.StringIO()), base_url=BASE_URL
    )


def _environ(database_url: str, environment: str = "demo") -> dict[str, str]:
    return {
        "DATABASE_URL": database_url,
        "APP_ENV": environment,
        "SERVER_SECRET_KEY": SERVER_KEY,
    }


def _value_in(output: str) -> str:
    match = LINK_VALUE.search(output)
    assert match is not None, "the command did not return a link"
    return match.group(1)


def _create(database_url: str, label: str = "Ana") -> str:
    output = io.StringIO()
    code = create_personal_link([label], _environ(database_url), output, io.StringIO())
    assert code == OK, output.getvalue()
    return _value_in(output.getvalue())


def _regenerate(database_url: str, label: str = "Ana") -> str:
    output = io.StringIO()
    code = regenerate_personal_link([label], _environ(database_url), output, io.StringIO())
    assert code == OK, output.getvalue()
    return _value_in(output.getvalue())


def _post(client: TestClient, **body: str) -> httpx2.Response:
    return client.post("/dev/session", json=body, headers=SAME_ORIGIN)


def _accept(client: TestClient, value: str) -> httpx2.Response:
    return _post(client, access_token=value, accept_test_notice="demo-1")


def _count(engine: Engine, table: str) -> int:
    statement = f"SELECT count(*) FROM {table}"  # noqa: S608
    with engine.connect() as connection:
        return int(connection.execute(text(statement)).scalar_one())


def _link_row(engine: Engine, label: str = "Ana") -> dict[str, str | None]:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT label, user_id::text AS user_id, token_hash "
                "FROM dev_access_link WHERE label = :label"
            ),
            {"label": label},
        ).one()
    return {"label": row.label, "user_id": row.user_id, "token_hash": row.token_hash}


# The commands


def test_creating_a_link_returns_it_and_keeps_only_its_hmac(
    fresh_database_url: str, engine: Engine
) -> None:
    # Case 1.
    value = _create(fresh_database_url)

    row = _link_row(engine)
    assert row["user_id"] is None
    assert row["token_hash"] != value
    assert value not in str(row)
    assert _count(engine, "app_user") == 0


def test_a_repeated_label_is_refused_and_the_first_link_keeps_working(
    fresh_database_url: str, engine: Engine, client: TestClient
) -> None:
    # Case 2.
    value = _create(fresh_database_url)
    before = _link_row(engine)
    output = io.StringIO()

    code = create_personal_link(["Ana"], _environ(fresh_database_url), output, io.StringIO())

    assert code != OK
    assert _count(engine, "dev_access_link") == 1
    assert _link_row(engine) == before
    assert _post(client, access_token=value).status_code == 409


def test_regenerating_a_used_link_keeps_the_account_and_closes_its_sessions(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 3.
    old_value = _create(fresh_database_url)
    entered = _accept(client, old_value)
    assert entered.status_code == 204
    old_cookie = entered.cookies[COOKIE]
    user_id = _link_row(engine)["user_id"]

    new_value = _regenerate(fresh_database_url)

    client.cookies.clear()
    assert _post(client, access_token=old_value).json() == NOT_FOUND
    assert client.get("/me", cookies={COOKIE: old_cookie}).status_code == 401
    client.cookies.clear()
    assert _post(client, access_token=new_value).status_code == 204
    assert client.get("/me").json()["id"] == user_id
    assert _count(engine, "app_user") == 1


def test_regenerating_an_unopened_link_gives_a_new_first_time(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 4.
    old_value = _create(fresh_database_url)

    new_value = _regenerate(fresh_database_url)

    assert _post(client, access_token=old_value).status_code == 404
    response = _post(client, access_token=new_value)
    assert response.status_code == 409
    assert response.json() == NOTICE_REQUIRED
    assert _count(engine, "app_user") == 0


def test_regenerating_a_label_that_does_not_exist_is_refused(
    fresh_database_url: str, engine: Engine
) -> None:
    # Case 5.
    output = io.StringIO()

    code = regenerate_personal_link(["Pedro"], _environ(fresh_database_url), output, io.StringIO())

    assert code != OK
    assert LINK_VALUE.search(output.getvalue()) is None
    assert _count(engine, "dev_access_link") == 0


def test_the_commands_refuse_to_run_in_production(fresh_database_url: str, engine: Engine) -> None:
    # Case 6.
    _create(fresh_database_url)
    before = _link_row(engine)
    production = _environ(fresh_database_url, "production")

    created = create_personal_link(["Pedro"], production, io.StringIO(), io.StringIO())
    regenerated = regenerate_personal_link(["Ana"], production, io.StringIO(), io.StringIO())

    assert created != OK
    assert regenerated != OK
    assert _count(engine, "dev_access_link") == 1
    assert _link_row(engine) == before


@pytest.mark.parametrize("command", [create_personal_link, regenerate_personal_link])
def test_without_the_server_key_the_commands_refuse_and_name_the_variable(
    fresh_database_url: str, engine: Engine, command: object
) -> None:
    # Case 7.
    assert callable(command)
    output = io.StringIO()
    environ = {
        "DATABASE_URL": fresh_database_url,
        "APP_ENV": "demo",
        "OPENAI_API_KEY": "another-value-that-must-not-show",
    }

    code = command(["Ana"], environ, output, io.StringIO())

    assert code != OK
    assert "SERVER_SECRET_KEY" in output.getvalue()
    assert "another-value-that-must-not-show" not in output.getvalue()
    assert _count(engine, "dev_access_link") == 0


# POST /dev/session with a link


def test_the_first_time_asks_for_the_notice_and_creates_nothing(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 8.
    value = _create(fresh_database_url)

    response = _post(client, access_token=value)

    assert response.status_code == 409
    assert response.json() == NOTICE_REQUIRED
    assert COOKIE not in response.cookies
    assert _count(engine, "app_user") == 0
    assert _count(engine, "session") == 0


def test_accepting_the_notice_creates_the_user_from_the_template_and_enters(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 9.
    value = _create(fresh_database_url)

    response = _accept(client, value)

    assert response.status_code == 204
    assert COOKIE in response.cookies
    with engine.connect() as connection:
        user = connection.execute(
            text(
                "SELECT id::text AS id, name, whatsapp_phone, terms_version, terms_accepted_at "
                "FROM app_user"
            )
        ).one()
    assert user.name == "Ana"
    assert user.whatsapp_phone.startswith("+000")
    assert user.terms_version == "demo-1"
    assert user.terms_accepted_at is not None
    assert _link_row(engine)["user_id"] == user.id
    assert _count(engine, "account") == 4
    assert _count(engine, "budget_period") == 1
    assert _count(engine, "financial_profile") == 1
    assert client.get("/me").json() == {"id": user.id, "name": "Ana"}


def test_accepting_an_old_version_of_the_notice_asks_for_the_current_one(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 10.
    value = _create(fresh_database_url)

    response = _post(client, access_token=value, accept_test_notice="demo-0")

    assert response.status_code == 409
    assert response.json() == NOTICE_REQUIRED
    assert COOKIE not in response.cookies
    assert _count(engine, "app_user") == 0


def test_coming_back_enters_the_same_account_without_the_notice(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 11.
    value = _create(fresh_database_url)
    assert _accept(client, value).status_code == 204
    user_id = _link_row(engine)["user_id"]
    client.cookies.clear()

    response = _post(client, access_token=value)

    assert response.status_code == 204
    assert client.get("/me").json()["id"] == user_id
    assert _count(engine, "app_user") == 1


def test_accepting_again_enters_and_keeps_the_first_consent(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 12.
    value = _create(fresh_database_url)
    assert _accept(client, value).status_code == 204
    with engine.connect() as connection:
        first = connection.execute(
            text("SELECT terms_accepted_at, terms_version FROM app_user")
        ).one()
    client.cookies.clear()

    response = _accept(client, value)

    assert response.status_code == 204
    with engine.connect() as connection:
        second = connection.execute(
            text("SELECT terms_accepted_at, terms_version FROM app_user")
        ).one()
    assert second == first
    assert _count(engine, "app_user") == 1


def test_two_acceptances_at_once_create_one_user_and_neither_fails(
    fresh_database_url: str, engine: Engine
) -> None:
    # Case 13.
    value = _create(fresh_database_url)
    clients = [_client(fresh_database_url), _client(fresh_database_url)]
    barrier = threading.Barrier(len(clients))
    statuses: list[int] = []

    def accept(client: TestClient) -> None:
        barrier.wait()
        statuses.append(_accept(client, value).status_code)

    threads = [threading.Thread(target=accept, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert statuses == [204, 204]
    assert _count(engine, "app_user") == 1
    assert _count(engine, "account") == 4


@pytest.mark.parametrize("value", ["a-link-nobody-created", ""])
def test_an_unknown_or_empty_link_answers_the_same_as_the_entry_turned_off(
    fresh_database_url: str, client: TestClient, value: str
) -> None:
    # Case 14.
    environ = {
        "DATABASE_URL": fresh_database_url,
        "APP_ENV": "demo",
        "APP_VERSION": "test",
    }
    turned_off = TestClient(
        create_app(load_settings(environ), log_stream=io.StringIO()), base_url=BASE_URL
    )

    response = _post(client, access_token=value)
    off = _post(turned_off, access_token=value)

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert off.status_code == response.status_code
    assert off.json() == response.json()


def test_a_user_id_next_to_a_valid_link_is_refused_in_demo(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 15.
    ana = _create(fresh_database_url, "Ana")
    assert _accept(client, ana).status_code == 204
    victim = _link_row(engine)["user_id"]
    assert victim is not None
    sessions = _count(engine, "session")
    other = _create(fresh_database_url, "Pedro")
    client.cookies.clear()

    response = _post(client, access_token=other, user_id=victim)

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert COOKIE not in response.cookies
    assert _count(engine, "app_user") == 1
    assert _count(engine, "session") == sessions


def test_each_link_sees_only_its_own_data(
    fresh_database_url: str, client: TestClient, engine: Engine
) -> None:
    # Case 16.
    assert _accept(client, _create(fresh_database_url, "Pedro")).status_code == 204
    pedro = _link_row(engine, "Pedro")["user_id"]
    pedros_accounts = {account["id"] for account in client.get("/accounts").json()["accounts"]}
    with engine.connect() as connection:
        pedros_period = connection.execute(
            text("SELECT id::text FROM budget_period WHERE user_id = :user"),
            {"user": pedro},
        ).scalar_one()
    client.cookies.clear()

    assert _accept(client, _create(fresh_database_url, "Ana")).status_code == 204

    assert client.get("/me").json()["name"] == "Ana"
    anas_accounts = {account["id"] for account in client.get("/accounts").json()["accounts"]}
    assert anas_accounts.isdisjoint(pedros_accounts)
    response = client.get(f"/budget-periods/{pedros_period}/summary")
    assert response.status_code == 404
    assert response.json() == NOT_FOUND


# Logs and startup


def test_the_value_of_a_link_never_reaches_the_logs(
    fresh_database_url: str, stream: io.StringIO
) -> None:
    # Case 17.
    command_output = io.StringIO()
    command_logs = io.StringIO()
    code = create_personal_link(["Ana"], _environ(fresh_database_url), command_output, command_logs)
    assert code == OK
    value = _value_in(command_output.getvalue())
    # After the command, which configures the logging of its own process.
    client = _client(fresh_database_url, stream)

    assert _post(client, access_token=value).status_code == 409
    assert _accept(client, value).status_code == 204
    invented = "a-link-nobody-created"
    assert _post(client, access_token=invented).status_code == 404
    assert _post(client, access_token=value, user_id="not-a-uuid").status_code == 422

    assert stream.getvalue(), "the logs of the API were not captured"
    logged = stream.getvalue() + command_logs.getvalue()
    assert value not in logged
    assert invented not in logged


def test_the_log_of_the_session_says_it_was_opened_by_a_personal_link(
    fresh_database_url: str, stream: io.StringIO
) -> None:
    # Case 18.
    value = _create(fresh_database_url)
    # After the command, which configures the logging of its own process.
    client = _client(fresh_database_url, stream)
    assert _accept(client, value).status_code == 204

    [line] = events_of(stream, "auth.session_created")
    assert line["method"] == "dev_personal_link"


def test_only_outside_local_every_answer_demands_https(fresh_database_url: str) -> None:
    # Case 20.
    demo = _client(fresh_database_url)
    local = TestClient(
        create_app(
            load_settings(
                {"DATABASE_URL": fresh_database_url, "APP_ENV": "local", "APP_VERSION": "test"}
            ),
            log_stream=io.StringIO(),
        ),
        base_url=BASE_URL,
    )

    for path in ("/healthz", "/a-route-that-does-not-exist"):
        assert "max-age=" in demo.get(path).headers["Strict-Transport-Security"]
        assert "Strict-Transport-Security" not in local.get(path).headers


def test_production_and_an_unexpected_error_demand_https_too(fresh_database_url: str) -> None:
    # Case 40.
    production = TestClient(
        create_app(
            load_settings(
                {"DATABASE_URL": fresh_database_url, "APP_ENV": "production", "APP_VERSION": "test"}
            ),
            log_stream=io.StringIO(),
        ),
        base_url=BASE_URL,
    )
    assert "max-age=" in production.get("/healthz").headers["Strict-Transport-Security"]

    app = create_app(
        load_settings(_environ(fresh_database_url) | {"APP_VERSION": "test"}),
        log_stream=io.StringIO(),
    )

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("an error nobody expected")

    response = TestClient(app, base_url=BASE_URL, raise_server_exceptions=False).get("/boom")
    assert response.status_code == 500
    assert "max-age=" in response.headers["Strict-Transport-Security"]


# Closing every session of a person


def _close_every_session(client: TestClient) -> httpx2.Response:
    return client.post(
        "/auth/logout-all", headers=SAME_ORIGIN | {"Content-Type": "application/json"}
    )


def test_closing_every_session_ends_them_on_all_devices_and_clears_the_cookie(
    fresh_database_url: str, client: TestClient
) -> None:
    # Case 30.
    value = _create(fresh_database_url)
    computer = client
    phone = _client(fresh_database_url)
    assert _accept(computer, value).status_code == 204
    entered = _post(phone, access_token=value)
    assert entered.status_code == 204
    phone_cookie = entered.cookies[COOKIE]

    response = _close_every_session(phone)

    assert response.status_code == 204
    cleared = response.headers["set-cookie"].lower()
    assert cleared.startswith('__host-sid="";') or cleared.startswith("__host-sid=;")
    assert "max-age=0" in cleared
    assert computer.get("/me").status_code == 401
    # The browser dropped the cookie; someone who kept the token cannot use it either.
    phone.cookies.clear()
    assert phone.get("/me", cookies={COOKIE: phone_cookie}).status_code == 401


def test_closing_every_session_leaves_the_sessions_of_another_person_open(
    fresh_database_url: str, client: TestClient
) -> None:
    # Case 31.
    ana = client
    pedro = _client(fresh_database_url)
    assert _accept(ana, _create(fresh_database_url, "Ana")).status_code == 204
    assert _accept(pedro, _create(fresh_database_url, "Pedro")).status_code == 204

    assert _close_every_session(ana).status_code == 204

    assert pedro.get("/me").json()["name"] == "Pedro"


def test_closing_every_session_without_a_session_is_not_authenticated(
    client: TestClient,
) -> None:
    # Case 32.
    response = _close_every_session(client)

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def _wait_until_waiting_for_locks(engine: Engine, how_many: int) -> None:
    """Asks PostgreSQL, not the clock, whether both requests are already held."""
    deadline = time.monotonic() + 10
    with engine.connect() as connection:
        while time.monotonic() < deadline:
            waiting = connection.execute(
                text("SELECT count(*) FROM pg_locks WHERE NOT granted")
            ).scalar_one()
            if waiting >= how_many:
                return
            time.sleep(0.05)
    pytest.fail(f"{how_many} requests never waited for a lock")


def test_regenerating_while_the_notice_is_accepted_closes_the_session_it_opened(
    fresh_database_url: str, engine: Engine
) -> None:
    # Case 42.
    old_value = _create(fresh_database_url)
    ana = _client(fresh_database_url)
    accepted: list[httpx2.Response] = []
    regenerated: list[str] = []

    with engine.connect() as holder:
        # Holds the creation of the user of Ana halfway, with her link already reserved.
        holder.execute(text("LOCK TABLE app_user IN SHARE ROW EXCLUSIVE MODE"))
        acceptance = threading.Thread(target=lambda: accepted.append(_accept(ana, old_value)))
        acceptance.start()
        _wait_until_waiting_for_locks(engine, 1)
        regeneration = threading.Thread(
            target=lambda: regenerated.append(_regenerate(fresh_database_url))
        )
        regeneration.start()
        _wait_until_waiting_for_locks(engine, 2)
        holder.rollback()

    acceptance.join()
    regeneration.join()

    [response] = accepted
    assert response.status_code == 204
    old_session = response.cookies[COOKIE]
    ana.cookies.clear()
    assert ana.get("/me", cookies={COOKIE: old_session}).status_code == 401
    [new_value] = regenerated
    assert _post(ana, access_token=new_value).status_code == 204
    assert ana.get("/me").json()["name"] == "Ana"


def _both_commands(environ: dict[str, str]) -> list[str]:
    """What creating and then regenerating the link of Ana print."""
    outputs = [io.StringIO(), io.StringIO()]
    assert create_personal_link(["Ana"], environ, outputs[0], io.StringIO()) == OK
    assert regenerate_personal_link(["Ana"], environ, outputs[1], io.StringIO()) == OK
    return [output.getvalue() for output in outputs]


def test_with_the_public_address_the_commands_print_the_whole_link(
    fresh_database_url: str,
) -> None:
    # Case 43. The address ends in a slash, which must not end up twice in the link.
    environ = _environ(fresh_database_url) | {
        "PUBLIC_BASE_URL": "https://platita-demo-web.onrender.com/"
    }

    for output in _both_commands(environ):
        assert re.search(r"(?<!\S)https://platita-demo-web\.onrender\.com/app/#\S+", output), output


def test_without_the_public_address_the_commands_print_the_path(
    fresh_database_url: str,
) -> None:
    # Case 44.
    for output in _both_commands(_environ(fresh_database_url)):
        assert re.search(r"(?<!\S)/app/#\S+", output), output
