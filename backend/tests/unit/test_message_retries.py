"""A call to the model that fails leaves the message for another attempt (FEAT-003, its spec.md).

Cases C2-26 and C2-27. The model fails inside the wrapper that records each call, as in the
worker; the database is in memory. The integration tests check the retries against PostgreSQL.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from app.adapters.observability.llm_calls import RecordedLLM
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryLlmCallLog, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, SUPERMARKET_EXPENSE, Lucia


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
