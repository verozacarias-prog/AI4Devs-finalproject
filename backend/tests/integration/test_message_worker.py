"""The message worker, against PostgreSQL (FEAT-002, docs/features/FEAT-002/spec.md).

Cases C1-03 to C1-05 and C1-10. C1-03 runs a whole round of the worker, the way its process
does. The others only take the next message, which is the step that decides the order and the
wait behind a message in process (ADR 0010).
"""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from app.settings import load_settings
from tests.support.chat_data import FIXED_REPLY, NOW, inbound, seed, status_of, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM

pytestmark = pytest.mark.integration

LOCK = timedelta(minutes=2)
SUPERMARKET = "gasté 3500 en el súper"
FUEL = "y 1200 de nafta"
SALARY = "cobré 50000"


@pytest.fixture
def seeded_database_url(fresh_database_url: str) -> str:
    seed(fresh_database_url)
    return fresh_database_url


@pytest.fixture
def engine(seeded_database_url: str) -> Iterator[Engine]:
    engine = create_engine(seeded_database_url)
    yield engine
    engine.dispose()


def _claim_next(engine: Engine) -> None:
    ClaimNextMessage(SqlAlchemyUnitOfWork(engine), FixedClock(NOW), LOCK).execute()


def test_the_worker_answers_a_pending_message_with_the_fixed_text(
    seeded_database_url: str, engine: Engine
) -> None:
    # Case C1-03.
    message = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(seconds=5))
    settings = load_settings(
        {"DATABASE_URL": seeded_database_url, "APP_ENV": "local", "APP_VERSION": "test"}
    )

    create_worker(settings, FixedClock(NOW), log_stream=io.StringIO(), llm=FakeLLM()).run_round()

    with engine.connect() as connection:
        answered = connection.execute(
            text("SELECT status, attempts, processed_at FROM inbound_message WHERE id = :id"),
            {"id": message},
        ).one()
        replies = connection.execute(
            text(
                "SELECT provider, user_id, to_phone, inbound_message_id, status, sent_at, "
                "provider_message_id, content FROM outbound_message"
            )
        ).all()
    assert answered.status == "processed"
    assert answered.attempts == 1
    assert answered.processed_at == NOW
    assert len(replies) == 1
    reply = replies[0]
    assert reply.provider == "web"
    assert reply.user_id == user_id(engine, "Lucía")
    assert reply.to_phone == "+000000000001"
    assert reply.inbound_message_id == message
    assert reply.status == "sent"
    assert reply.sent_at == NOW
    assert reply.provider_message_id is None
    content = reply.content if isinstance(reply.content, dict) else json.loads(reply.content)
    assert content == {"text": FIXED_REPLY, "response_kind": "fixed_text"}


def test_the_worker_takes_first_the_message_that_arrived_first(engine: Engine) -> None:
    # Case C1-04. The later one is stored first, so the order cannot come from the insert.
    later = inbound(engine, "Lucía", FUEL, sent_at=NOW - timedelta(seconds=55))
    earlier = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(seconds=60))

    _claim_next(engine)

    with engine.connect() as connection:
        locked_until = connection.execute(
            text("SELECT locked_until FROM inbound_message WHERE id = :id"), {"id": earlier}
        ).scalar_one()
    assert status_of(engine, earlier) == ("processing", 1)
    assert locked_until == NOW + LOCK
    assert status_of(engine, later) == ("pending", 0)


def test_with_a_message_of_lucia_in_process_her_next_waits_and_pablos_does_not(
    engine: Engine,
) -> None:
    # Case C1-05.
    inbound(
        engine,
        "Lucía",
        SUPERMARKET,
        sent_at=NOW - timedelta(seconds=60),
        status="processing",
        attempts=1,
        locked_until=NOW + timedelta(minutes=2),
    )
    lucias_next = inbound(engine, "Lucía", FUEL, sent_at=NOW - timedelta(seconds=55))
    pablos = inbound(engine, "Pablo", SALARY, sent_at=NOW - timedelta(seconds=50))

    _claim_next(engine)

    assert status_of(engine, pablos) == ("processing", 1)
    assert status_of(engine, lucias_next) == ("pending", 0)


def test_a_message_already_answered_does_not_hold_the_next_one(engine: Engine) -> None:
    # Case C1-10.
    inbound(
        engine,
        "Lucía",
        SUPERMARKET,
        sent_at=NOW - timedelta(seconds=60),
        status="processed",
        attempts=1,
    )
    following = inbound(engine, "Lucía", FUEL, sent_at=NOW - timedelta(seconds=55))

    _claim_next(engine)

    assert status_of(engine, following) == ("processing", 1)
