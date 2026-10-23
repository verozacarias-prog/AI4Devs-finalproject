"""A call to the model that fails leaves the message for another attempt (FEAT-003, its spec.md).

Cases C2-26 and C2-27: the model fails inside the wrapper that records each call, as in the
worker. Cases C2-42 and C2-43: a failure that is not of the model. The database is in
memory; the integration tests check the retries against PostgreSQL.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from app.adapters.observability.llm_calls import RecordedLLM
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError, StoreUnavailableError
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryLlmCallLog, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import (
    NOW,
    SUPERMARKET_EXPENSE,
    Lucia,
    supermarket_expense,
)


@pytest.mark.parametrize("outcome", [LlmOutcome.TIMEOUT, LlmOutcome.INVALID_OUTPUT])
def test_a_timeout_and_an_invalid_output_are_also_retried(outcome: LlmOutcome) -> None:
    # Case C2-26.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    calls = InMemoryLlmCallLog()
    llm = RecordedLLM(FakeLLM(error=ModelCallFailedError(outcome)), calls)
    message = lucia.message(SUPERMARKET_EXPENSE)

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(message)

    assert unit_of_work.transactions.added == []
    assert unit_of_work.outbound_messages.added == []
    assert unit_of_work.inbound_messages.marked == []
    [(retried, attempts, _)] = unit_of_work.inbound_messages.retried
    assert (retried, attempts) == (message.id, message.attempts)
    [call] = calls.recorded
    assert call.outcome is outcome


def test_the_wait_between_attempts_grows() -> None:
    # Case C2-27. The second attempt failed: the third waits 2 minutes, not 30 seconds.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = FakeLLM(error=ModelCallFailedError(LlmOutcome.PROVIDER_ERROR))
    message = replace(lucia.message(SUPERMARKET_EXPENSE), attempts=2)

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(message)

    [(_, _, next_attempt_at)] = unit_of_work.inbound_messages.retried
    assert next_attempt_at == NOW + timedelta(minutes=2)


def test_with_the_database_down_the_message_is_retried() -> None:
    # Case C2-42. A failure that may go away: it is tried again, and still logged.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    unit_of_work.transactions.failure = StoreUnavailableError()
    message = lucia.message(SUPERMARKET_EXPENSE)

    with pytest.raises(StoreUnavailableError):
        AnswerMessage(unit_of_work, FixedClock(NOW), FakeLLM(supermarket_expense())).execute(
            message
        )

    assert unit_of_work.transactions.added == []
    assert unit_of_work.outbound_messages.added == []
    assert unit_of_work.inbound_messages.failed == []
    [(retried, attempts, next_attempt_at)] = unit_of_work.inbound_messages.retried
    assert (retried, attempts) == (message.id, 1)
    assert next_attempt_at == NOW + timedelta(seconds=30)


def test_an_error_of_the_code_fails_the_message_without_retrying() -> None:
    # Case C2-43. Its state will not change: it fails at once, and is still logged.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    unit_of_work.transactions.failure = RuntimeError("a mistake of the code")
    message = lucia.message(SUPERMARKET_EXPENSE)

    with pytest.raises(RuntimeError):
        AnswerMessage(unit_of_work, FixedClock(NOW), FakeLLM(supermarket_expense())).execute(
            message
        )

    assert unit_of_work.transactions.added == []
    assert unit_of_work.inbound_messages.retried == []
    assert unit_of_work.inbound_messages.failed == [message.id]
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == (
        "Tuve un problema y no pude procesar tu mensaje. ¿Me lo mandás de nuevo en un rato?"
    )
