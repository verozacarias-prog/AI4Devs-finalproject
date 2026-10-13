"""Cases E24 to E27: the edges of the error handling.

A request outside the contract leaves no error line, a repeated primary key is a failure of
the code and not a conflict, and nothing an error carries can replace a field of its own.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from enum import StrEnum

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.adapters.inbound.api.app import create_app
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities.user import OnboardingStatus, User
from app.domain.errors import ConflictError, InvalidError
from app.settings import load_settings
from tests.log_lines import events_of

pytestmark = pytest.mark.integration


class _Word(StrEnum):
    OTHER = "other"


@pytest.fixture
def engine(fresh_database_url: str) -> Iterator[Engine]:
    engine = create_db_engine(fresh_database_url)
    yield engine
    engine.dispose()


def _app(database_url: str, stream: io.StringIO) -> FastAPI:
    settings = load_settings(
        {"DATABASE_URL": database_url, "APP_ENV": "production", "APP_VERSION": "test"}
    )
    return create_app(settings, log_stream=stream)


def test_a_request_outside_the_contract_leaves_its_line_and_no_error_line(
    database_url: str,
) -> None:
    """Case E24."""
    stream = io.StringIO()
    app = _app(database_url, stream)

    @app.get("/items/{number}")
    def item(number: int) -> None:
        return None

    response = TestClient(app).get("/items/gaste-58400")

    assert response.status_code == 422
    requests = events_of(stream, "http.request")
    assert len(requests) == 1
    assert requests[0]["result"] == 422
    assert events_of(stream, "error.expected") == []
    assert events_of(stream, "error.unexpected") == []


def test_a_repeated_primary_key_is_a_failure_of_the_code_and_not_a_conflict(
    fresh_database_url: str, engine: Engine
) -> None:
    """Case E25."""
    stream = io.StringIO()
    app = _app(fresh_database_url, stream)
    user = User(
        id=uuid.uuid4(),
        name="Ana",
        whatsapp_phone="+5491155551234",
        country="AR",
        time_zone="America/Argentina/Buenos_Aires",
        primary_currency="ARS",
        exchange_rate_reference="DOLAR_MEP",
        terms_accepted_at=datetime(2031, 3, 7, 12, 0, tzinfo=UTC),
        terms_version="test-1",
        notifications_opt_in=False,
        onboarding_status=OnboardingStatus.COMPLETED,
    )

    @app.get("/same-id")
    def same_id() -> None:
        with SqlAlchemyUnitOfWork(engine) as unit_of_work:
            unit_of_work.users.add(user)
            unit_of_work.users.add(replace(user, whatsapp_phone="+5491155550000"))

    response = TestClient(app, raise_server_exceptions=False).get("/same-id")

    assert response.status_code == 500
    assert response.json() == {"error": "internal_error"}
    assert events_of(stream, "error.expected") == []
    errors = events_of(stream, "error.unexpected")
    assert len(errors) == 1
    assert errors[0]["constraint"] == "pk_app_user"


def test_the_context_of_an_error_cannot_replace_a_field_of_the_line(database_url: str) -> None:
    """Case E26."""
    stream = io.StringIO()
    app = _app(database_url, stream)

    @app.get("/fails")
    def fails() -> None:
        raise ConflictError(
            "period_overlaps", context={"error_type": _Word.OTHER, "error_code": _Word.OTHER}
        )

    TestClient(app).get("/fails")

    line = events_of(stream, "error.expected")[0]
    assert line["error_type"] == "ConflictError"
    assert line["error_code"] == "period_overlaps"


def test_the_details_of_an_error_cannot_replace_its_code(database_url: str) -> None:
    """Case E27."""
    app = _app(database_url, io.StringIO())

    @app.get("/fails")
    def fails() -> None:
        raise InvalidError("missing_fields", details={"error": "other"})

    response = TestClient(app).get("/fails")

    assert response.json()["error"] == "missing_fields"


def test_the_context_of_an_error_cannot_replace_the_reference_or_break_the_line(
    database_url: str,
) -> None:
    """Case E26, the fields the line sets outside the error."""
    stream = io.StringIO()
    app = _app(database_url, stream)

    @app.get("/fails")
    def fails() -> None:
        raise ConflictError(
            "period_overlaps",
            context={"request_id": uuid.uuid4(), "name": _Word.OTHER, "account_id": uuid.uuid4()},
        )

    response = TestClient(app).get("/fails")

    assert response.status_code == 409
    line = events_of(stream, "error.expected")[0]
    assert line["request_id"] == response.headers["x-request-id"]
    assert line["logger"] == "platita.errors"
    assert line["account_id"]
