"""Cases 8 and 9: logs are JSON lines and every request carries its own identifier."""
from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings

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
