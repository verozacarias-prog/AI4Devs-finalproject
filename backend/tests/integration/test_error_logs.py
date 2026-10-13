"""Cases E7, E8 and E15 to E17: the log line an error leaves (docs/operacion.md, 6.3).

It says which error, by which path and on which rows, and never with which values. Only the
local environment also writes the error in full.
"""

from __future__ import annotations

import io
import re
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.constants import Environment
from app.domain.errors import ConflictError
from app.settings import load_settings
from tests.log_lines import events_of, stack_of

pytestmark = pytest.mark.integration

MESSAGE = "could not register 58400 for +5491155551234"
PLACE = re.compile(r"[A-Za-z_][\w.]*:\w+:\d+")


def _app(database_url: str, stream: io.StringIO, environment: str = "production") -> FastAPI:
    settings = load_settings(
        {"DATABASE_URL": database_url, "APP_ENV": environment, "APP_VERSION": "test"}
    )
    return create_app(settings, log_stream=stream)


def _raise_conflict() -> None:
    raise ConflictError("period_overlaps")


def _add_boom(app: FastAPI) -> None:
    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(MESSAGE)


def test_an_expected_error_leaves_one_line_with_its_code_and_its_path(database_url: str) -> None:
    """Case E7."""
    stream = io.StringIO()
    app = _app(database_url, stream)

    @app.get("/fails")
    def fails() -> None:
        _raise_conflict()

    TestClient(app).get("/fails")

    errors = events_of(stream, "error.expected")
    assert len(errors) == 1
    line = errors[0]
    assert line["level"] == "INFO"
    assert line["error_type"] == "ConflictError"
    assert line["error_code"] == "period_overlaps"
    stack = stack_of(line)
    assert all(PLACE.fullmatch(place) for place in stack)
    assert stack[-1].startswith(f"{__name__}:_raise_conflict:")
    router = [place for place in stack if place.startswith(f"{__name__}:fails:")]
    assert len(router) == 1
    assert stack.index(router[0]) < len(stack) - 1
    assert line["request_id"] == events_of(stream, "http.request")[0]["request_id"]


def test_an_unexpected_error_leaves_one_line_without_its_values(
    database_url: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Case E8."""
    stream = io.StringIO()
    app = _app(database_url, stream)
    _add_boom(app)

    TestClient(app, raise_server_exceptions=False).get("/boom")

    errors = events_of(stream, "error.unexpected")
    assert len(errors) == 1
    line = errors[0]
    assert line["level"] == "ERROR"
    assert line["error_type"] == "RuntimeError"
    assert line.get("error_code") is None
    assert stack_of(line)[-1].startswith(f"{__name__}:boom:")
    for written in (stream.getvalue(), capsys.readouterr().err):
        assert "58400" not in written
        assert "5491155551234" not in written


def test_the_line_says_which_rows_and_which_catalog_values_were_involved(
    database_url: str,
) -> None:
    """Case E15."""
    stream = io.StringIO()
    app = _app(database_url, stream)
    account_id, period_id = uuid.uuid4(), uuid.uuid4()

    @app.get("/fails")
    def fails() -> None:
        raise ConflictError(
            "period_overlaps",
            context={
                "account_id": account_id,
                "budget_period_id": period_id,
                "environment": Environment.DEMO,
            },
        )

    TestClient(app).get("/fails")

    line = events_of(stream, "error.expected")[0]
    assert line["account_id"] == str(account_id)
    assert line["budget_period_id"] == str(period_id)
    assert line["environment"] == "demo"


def test_in_local_an_error_is_also_written_in_full(
    database_url: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Case E16."""
    stream = io.StringIO()
    app = _app(database_url, stream, environment="local")
    _add_boom(app)

    TestClient(app, raise_server_exceptions=False).get("/boom")

    written = capsys.readouterr().err
    assert MESSAGE in written
    assert "Traceback" in written
    assert len(events_of(stream, "error.unexpected")) == 1
    assert "58400" not in stream.getvalue()
    assert "5491155551234" not in stream.getvalue()


@pytest.mark.parametrize("environment", ["demo", "production"])
def test_outside_local_nothing_is_written_in_full(
    database_url: str, capsys: pytest.CaptureFixture[str], environment: str
) -> None:
    """Case E17."""
    app = _app(database_url, io.StringIO(), environment)
    _add_boom(app)

    TestClient(app, raise_server_exceptions=False).get("/boom")

    assert capsys.readouterr().err == ""
