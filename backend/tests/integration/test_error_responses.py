"""Cases E1 to E6: what the API answers to an error (docs/04-api.md).

Every error has the same body, a stable code, and every response carries its reference.
"""

from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.domain.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    InvalidError,
    NotFoundError,
)
from app.settings import load_settings
from tests.log_lines import events_of

pytestmark = pytest.mark.integration


def _app(database_url: str, stream: io.StringIO | None = None) -> FastAPI:
    settings = load_settings(
        {"DATABASE_URL": database_url, "APP_ENV": "production", "APP_VERSION": "test"}
    )
    return create_app(settings, log_stream=stream or io.StringIO())


@pytest.mark.parametrize(
    ("error_class", "status"),
    [(NotFoundError, 404), (ForbiddenError, 403), (ConflictError, 409), (InvalidError, 422)],
    ids=["not-found", "forbidden", "conflict", "invalid"],
)
def test_each_category_of_error_has_its_status_and_the_same_body(
    database_url: str, error_class: type[DomainError], status: int
) -> None:
    """Case E1."""
    app = _app(database_url)

    @app.get("/fails")
    def fails() -> None:
        raise error_class("something_expected")

    response = TestClient(app).get("/fails")

    assert response.status_code == status
    assert response.json() == {"error": "something_expected"}


def test_an_error_adds_only_the_fields_the_client_needs(database_url: str) -> None:
    """Case E2."""
    app = _app(database_url)

    @app.get("/fails")
    def fails() -> None:
        raise InvalidError(
            "missing_fields", details={"missing_fields": ["account_id", "budget_period_id"]}
        )

    response = TestClient(app).get("/fails")

    assert response.status_code == 422
    assert response.json() == {
        "error": "missing_fields",
        "missing_fields": ["account_id", "budget_period_id"],
    }


def test_a_request_outside_the_contract_does_not_get_its_own_value_back(
    database_url: str,
) -> None:
    """Case E3."""
    app = _app(database_url)

    @app.get("/items/{number}")
    def item(number: int) -> None:
        return None

    response = TestClient(app).get("/items/gaste-58400")

    assert response.status_code == 422
    assert response.json() == {"error": "invalid_request"}
    assert "58400" not in response.text


def test_an_unexpected_error_answers_a_fixed_body_that_says_nothing_about_it(
    database_url: str,
) -> None:
    """Case E4."""
    app = _app(database_url)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("could not register 58400 for +5491155551234")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "internal_error"}


def test_every_response_carries_the_identifier_of_its_request(database_url: str) -> None:
    """Case E5."""
    stream = io.StringIO()
    app = _app(database_url, stream)

    @app.get("/fails")
    def fails() -> None:
        raise ConflictError("something_expected")

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("unexpected")

    client = TestClient(app, raise_server_exceptions=False)
    references = [
        client.get(path).headers["x-request-id"] for path in ("/healthz", "/fails", "/boom")
    ]

    assert len(set(references)) == 3
    logged = [line["request_id"] for line in events_of(stream, "http.request")]
    assert logged == references


def test_an_expected_error_carries_the_security_headers(database_url: str) -> None:
    """Case E6."""
    app = _app(database_url)

    @app.get("/fails")
    def fails() -> None:
        raise NotFoundError("something_expected")

    response = TestClient(app).get("/fails")

    assert response.status_code == 404
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
