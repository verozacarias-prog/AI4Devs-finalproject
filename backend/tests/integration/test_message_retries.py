"""When the call to the model fails, against PostgreSQL (FEAT-003, its spec.md).

Cases C2-25, C2-28 to C2-31 and C2-41: the retries with a growing wait, the message that fails for
good and its notice, the next message after it, and a refusal of the model. The worker runs
whole rounds, with the model replaced by a double inside the wrapper that records each call.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.domain.entities.classification import Classification, MessageClass
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError, ModelRefusedError
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, status_of
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import (
    NOW,
    SUPERMARKET_EXPENSE,
    seed_on_october_1,
    supermarket_expense,
)

pytestmark = pytest.mark.integration

SENT_AT = NOW - timedelta(seconds=5)


@pytest.fixture
def engine(fresh_database_url: str) -> Iterator[Engine]:
    engine = create_engine(fresh_database_url)
    seed_on_october_1(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def settings(fresh_database_url: str, engine: Engine) -> Settings:
    return load_settings(
        {
            "DATABASE_URL": fresh_database_url,
            "APP_ENV": "local",
            "APP_VERSION": "test",
            "WEB_CHAT_ENABLED": "true",
        }
    )


def _run_round(settings: Settings, llm: FakeLLM, now: datetime = NOW) -> bool:
    return create_worker(settings, FixedClock(now), log_stream=io.StringIO(), llm=llm).run_round()


def _provider_down() -> FakeLLM:
    return FakeLLM(supermarket_expense(), error=ModelCallFailedError(LlmOutcome.PROVIDER_ERROR))


def _replies_to(engine: Engine, message: uuid.UUID) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT content FROM outbound_message WHERE inbound_message_id = :id"),
            {"id": message},
        ).all()
    return [
        row.content if isinstance(row.content, dict) else json.loads(row.content) for row in rows
    ]


def _next_attempt_at(engine: Engine, message: uuid.UUID) -> datetime:
    with engine.connect() as connection:
        found: datetime = connection.execute(
            text("SELECT next_attempt_at FROM inbound_message WHERE id = :id"), {"id": message}
        ).scalar_one()
    return found


def _outcomes(engine: Engine, message: uuid.UUID) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT outcome FROM llm_call WHERE inbound_message_id = :id"), {"id": message}
        ).all()
    return [row.outcome for row in rows]


def _count(engine: Engine, query: str) -> int:
    with engine.connect() as connection:
        found: int = connection.execute(text(query)).scalar_one()
    return found


def test_if_the_provider_fails_the_message_is_retried_and_the_call_recorded(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-25.
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)

    _run_round(settings, _provider_down())

    assert status_of(engine, message) == ("pending", 1)
    assert _next_attempt_at(engine, message) == NOW + timedelta(seconds=30)
    assert _replies_to(engine, message) == []
    assert _outcomes(engine, message) == ["provider_error"]


def test_a_message_is_not_taken_before_its_next_attempt(settings: Settings, engine: Engine) -> None:
    # Case C2-28.
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    _run_round(settings, _provider_down())

    early = FakeLLM(supermarket_expense())
    _run_round(settings, early, NOW + timedelta(seconds=10))
    on_time = FakeLLM(supermarket_expense())
    _run_round(settings, on_time, NOW + timedelta(seconds=31))

    assert early.requests == []
    assert len(on_time.requests) == 1
    assert status_of(engine, message) == ("processed", 2)


def test_with_the_attempts_used_up_the_message_fails_and_the_user_is_told(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-29. Two attempts already failed: this one is the third.
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT, attempts=2)

    _run_round(settings, _provider_down())

    assert status_of(engine, message)[0] == "failed"
    assert _count(engine, "SELECT count(*) FROM transaction") == 0
    [reply] = _replies_to(engine, message)
    assert reply["text"] == (
        "Tuve un problema y no pude procesar tu mensaje. ¿Me lo mandás de nuevo en un rato?"
    )
    assert reply["response_kind"] == "fixed_text"


def test_after_a_failed_message_the_next_one_is_processed(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-30.
    failed = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT, attempts=2)
    _run_round(settings, _provider_down())
    assert status_of(engine, failed)[0] == "failed"
    greeting = inbound(engine, "Lucía", "hola", sent_at=NOW + timedelta(seconds=1))

    _run_round(settings, FakeLLM(Classification(MessageClass.NONE)), NOW + timedelta(seconds=2))

    assert status_of(engine, greeting)[0] == "processed"
    [reply] = _replies_to(engine, greeting)
    assert reply["text"] == (
        "¡Hola! Soy Platita y te ayudo a llevar las cuentas. Contame qué gastaste o qué "
        "cobraste, y con qué cuenta. Por ejemplo: «gasté 3500 en el súper con Mercado Pago»."
    )


def test_if_the_model_refuses_the_fixed_text_goes_out_and_it_is_not_retried(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-31.
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)

    _run_round(settings, FakeLLM(error=ModelRefusedError()))

    assert status_of(engine, message) == ("processed", 1)
    assert _count(engine, "SELECT count(*) FROM transaction") == 0
    [reply] = _replies_to(engine, message)
    assert reply["text"] == (
        "No pude entender ese mensaje. ¿Me lo escribís de otra forma? Por ejemplo: «gasté 3500 "
        "en el súper con Mercado Pago»."
    )
    assert reply["response_kind"] == "fixed_text"
    assert _outcomes(engine, message) == ["blocked"]


def test_a_write_the_database_rejects_fails_the_message_without_retrying(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-41. Its state will not change, so it is not tried again.
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_transaction() RETURNS trigger AS $$ BEGIN "
                "RAISE EXCEPTION 'la base rechaza el movimiento'; END $$ LANGUAGE plpgsql"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER reject_transaction BEFORE INSERT ON transaction "
                "FOR EACH ROW EXECUTE FUNCTION reject_transaction()"
            )
        )
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    greeting = inbound(engine, "Lucía", "hola", sent_at=SENT_AT + timedelta(seconds=1))

    _run_round(settings, FakeLLM(supermarket_expense()))
    after = FakeLLM(Classification(MessageClass.NONE))
    _run_round(settings, after, NOW + timedelta(seconds=1))

    assert status_of(engine, message) == ("failed", 1)
    assert _count(engine, "SELECT count(*) FROM transaction") == 0
    [notice] = _replies_to(engine, message)
    assert notice["text"] == (
        "Tuve un problema y no pude procesar tu mensaje. ¿Me lo mandás de nuevo en un rato?"
    )
    assert [request.text for request in after.requests] == ["hola"]
    [reply] = _replies_to(engine, greeting)
    assert reply["text"] == (
        "¡Hola! Soy Platita y te ayudo a llevar las cuentas. Contame qué gastaste o qué "
        "cobraste, y con qué cuenta. Por ejemplo: «gasté 3500 en el súper con Mercado Pago»."
    )
