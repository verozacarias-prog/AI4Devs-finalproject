"""Cases E9 and E10: a write the database rejects.

A repeated unique key is a conflict the domain foresees. A violated CHECK is a failure of the
code. Either way the log names the constraint and never the row.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.adapters.inbound.api.app import create_app
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities.budget_period import first_period
from app.domain.entities.user import OnboardingStatus, User
from app.domain.errors import ConflictError
from app.settings import load_settings
from tests.log_lines import events_of

pytestmark = pytest.mark.integration

PHONE = "+5491155551234"


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


def _user_with_the_phone() -> User:
    return User(
        id=uuid.uuid4(),
        name="Ana",
        whatsapp_phone=PHONE,
        country="AR",
        time_zone="America/Argentina/Buenos_Aires",
        primary_currency="ARS",
        exchange_rate_reference="DOLAR_MEP",
        terms_accepted_at=datetime(2031, 3, 7, 12, 0, tzinfo=UTC),
        terms_version="test-1",
        notifications_opt_in=False,
        onboarding_status=OnboardingStatus.COMPLETED,
    )


def _add_the_same_phone_twice(engine: Engine) -> None:
    with SqlAlchemyUnitOfWork(engine) as unit_of_work:
        unit_of_work.users.add(_user_with_the_phone())
        unit_of_work.users.add(_user_with_the_phone())


def test_a_repeated_unique_key_is_a_conflict_that_names_the_constraint_and_not_the_row(
    fresh_database_url: str, engine: Engine
) -> None:
    """Case E9."""
    stream = io.StringIO()
    app = _app(fresh_database_url, stream)

    @app.get("/duplicate")
    def duplicate() -> None:
        _add_the_same_phone_twice(engine)

    response = TestClient(app).get("/duplicate")

    assert response.status_code == 409
    assert response.json() == {"error": "conflict"}
    errors = events_of(stream, "error.expected")
    assert len(errors) == 1
    assert errors[0]["error_type"] == "ConflictError"
    assert errors[0]["error_code"] == "conflict"
    assert errors[0]["error_cause"] == "IntegrityError"
    assert errors[0]["constraint"] == "uq_app_user_whatsapp_phone"
    assert "5491155551234" not in stream.getvalue()


def test_the_text_of_a_translated_error_does_not_carry_the_row(engine: Engine) -> None:
    """Case E9, the error itself."""
    with pytest.raises(ConflictError) as caught:
        _add_the_same_phone_twice(engine)

    assert "5491155551234" not in str(caught.value)


def test_a_violated_check_is_an_unexpected_error_that_names_the_constraint(
    fresh_database_url: str, engine: Engine
) -> None:
    """Case E10."""
    stream = io.StringIO()
    app = _app(fresh_database_url, stream)

    @app.get("/ownerless")
    def ownerless() -> None:
        with SqlAlchemyUnitOfWork(engine) as unit_of_work:
            unit_of_work.budget_periods.add(first_period(currency="ARS", today=date(2031, 3, 7)))

    response = TestClient(app, raise_server_exceptions=False).get("/ownerless")

    assert response.status_code == 500
    assert response.json() == {"error": "internal_error"}
    errors = events_of(stream, "error.unexpected")
    assert len(errors) == 1
    assert errors[0]["constraint"] == "ck_budget_period_one_owner"
    assert "2031-03-07" not in stream.getvalue()
    assert "2031-03-31" not in stream.getvalue()
