"""Cases 8, 9, 17 and 19: logs are JSON lines and every request carries its identifier."""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings
from tests.conftest import UNREACHABLE_DATABASE_URL

pytestmark = pytest.mark.integration

JsonLine = dict[str, str | int | float | bool | None]


def lines_of(stream: io.StringIO) -> list[JsonLine]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


@pytest.fixture
def stream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def client(database_url: str, stream: io.StringIO) -> TestClient:
    settings = load_settings({"DATABASE_URL": database_url, "APP_VERSION": "test"})
    return TestClient(create_app(settings, log_stream=stream))


def test_every_log_line_is_one_json_object_with_the_base_fields(
    client: TestClient, stream: io.StringIO
) -> None:
    client.get("/healthz")

    raw_lines = stream.getvalue().splitlines()
    assert raw_lines, "the request left no log line"
    for raw in raw_lines:
        line: JsonLine = json.loads(raw)
        for field in ("ts", "level", "event", "request_id"):
            assert line.get(field), f"{field} is missing in {raw}"


def test_each_request_has_its_own_identifier(client: TestClient, stream: io.StringIO) -> None:
    client.get("/healthz")
    first = {line["request_id"] for line in lines_of(stream)}
    stream.truncate(0)
    stream.seek(0)

    client.get("/readyz")
    second = {line["request_id"] for line in lines_of(stream)}

    assert len(first) == 1
    assert len(second) == 1
    assert first != second


def test_a_failing_request_leaves_a_line_with_its_identifier_and_the_error_class(
    database_url: str, stream: io.StringIO
) -> None:
    """Case 17."""
    settings = load_settings({"DATABASE_URL": database_url, "APP_VERSION": "test"})
    app = create_app(settings, log_stream=stream)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("could not register 58400 for +5491155551234")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    requests = [line for line in lines_of(stream) if line["event"] == "http.request"]
    assert len(requests) == 1
    assert requests[0]["request_id"]
    assert requests[0]["result"] == 500
    assert requests[0]["error_type"] == "RuntimeError"
    assert "58400" not in stream.getvalue()
    assert "5491155551234" not in stream.getvalue()


def test_an_unreachable_database_is_logged_without_its_url(stream: io.StringIO) -> None:
    """Case 19."""
    settings = load_settings({"DATABASE_URL": UNREACHABLE_DATABASE_URL, "APP_VERSION": "test"})
    client = TestClient(create_app(settings, log_stream=stream))

    response = client.get("/readyz")

    assert response.status_code == 503
    unreachable = [line for line in lines_of(stream) if line["event"] == "database.unreachable"]
    assert len(unreachable) == 1
    assert unreachable[0]["error_type"]
    assert "platita:platita" not in stream.getvalue()
    assert "127.0.0.1:9" not in stream.getvalue()
