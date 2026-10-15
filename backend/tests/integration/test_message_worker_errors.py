"""The message worker when something goes wrong, against PostgreSQL (FEAT-002).

Cases C2-06 to C2-08, from the spec.md of FEAT-002: a worker that fell and left its message
taken, and two workers that end up with the same message (ADR 0010).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.use_cases.messages.answer_message import AnswerMessage
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from tests.support.chat_data import NOW, inbound, seed, status_of
from tests.support.doubles import FixedClock

pytestmark = pytest.mark.integration

LOCK = timedelta(minutes=2)
SUPERMARKET = "gasté 3500 en el súper"
FUEL = "y 1200 de nafta"


@pytest.fixture
def engine(fresh_database_url: str) -> Iterator[Engine]:
    seed(fresh_database_url)
    engine = create_engine(fresh_database_url)
    yield engine
    engine.dispose()


def _left_by_a_worker_that_fell(engine: Engine) -> uuid.UUID:
    """In process since 17:57, with its lock ended at 17:59: the worker never came back."""
    return inbound(
        engine,
        "Lucía",
        SUPERMARKET,
        sent_at=NOW - timedelta(minutes=3),
        status="processing",
        attempts=1,
        locked_until=NOW - timedelta(minutes=1),
    )


def test_a_message_whose_lock_ended_is_taken_again(engine: Engine) -> None:
    # Case C2-06.
    message = _left_by_a_worker_that_fell(engine)

    ClaimNextMessage(SqlAlchemyUnitOfWork(engine), FixedClock(NOW), LOCK).execute()

    with engine.connect() as connection:
        locked_until = connection.execute(
            text("SELECT locked_until FROM inbound_message WHERE id = :id"), {"id": message}
        ).scalar_one()
    assert status_of(engine, message) == ("processing", 2)
    assert locked_until == NOW + LOCK


def test_a_message_whose_lock_ended_still_goes_before_the_next_ones(engine: Engine) -> None:
    # Case C2-07.
    message = _left_by_a_worker_that_fell(engine)
    following = inbound(engine, "Lucía", FUEL, sent_at=NOW - timedelta(minutes=2))

    ClaimNextMessage(SqlAlchemyUnitOfWork(engine), FixedClock(NOW), LOCK).execute()

    assert status_of(engine, message) == ("processing", 2)
    assert status_of(engine, following) == ("pending", 0)


def test_two_workers_finish_the_same_message_and_only_one_reply_is_left(engine: Engine) -> None:
    # Case C2-08. The first worker takes it at 18:00 and is still working at 18:03, when its
    # lock has ended and a second worker takes it again.
    message = inbound(engine, "Lucía", SUPERMARKET, sent_at=NOW - timedelta(seconds=5))
    later = NOW + timedelta(minutes=3)
    first = ClaimNextMessage(SqlAlchemyUnitOfWork(engine), FixedClock(NOW), LOCK).execute()
    second = ClaimNextMessage(SqlAlchemyUnitOfWork(engine), FixedClock(later), LOCK).execute()
    assert first is not None and second is not None
    assert (first.attempts, second.attempts) == (1, 2)

    first_ends = later + timedelta(seconds=10)
    second_ends = later + timedelta(seconds=20)
    AnswerMessage(SqlAlchemyUnitOfWork(engine), FixedClock(first_ends)).execute(first)
    AnswerMessage(SqlAlchemyUnitOfWork(engine), FixedClock(second_ends)).execute(second)

    with engine.connect() as connection:
        replies = connection.execute(
            text("SELECT created_at FROM outbound_message WHERE inbound_message_id = :id"),
            {"id": message},
        ).all()
    # One reply, written when the second worker finished: the first one wrote nothing.
    assert [reply.created_at for reply in replies] == [second_ends]
    assert status_of(engine, message) == ("processed", 2)
