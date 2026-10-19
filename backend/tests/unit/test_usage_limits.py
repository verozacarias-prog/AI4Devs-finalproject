"""The daily limits of use, with the model replaced (FEAT-003, its spec.md).

Cases C3-04, C3-06 and C3-09: the day a counter belongs to, what counts against the quota of
registration, and a message put off that is not an attempt. The database is in memory; the
integration tests check the limits against PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities.classification import (
    Classification,
    MessageClass,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_usage import UsageCounter
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import (
    NOW,
    OCTOBER_17,
    SALARY_INCOME,
    SUPERMARKET_EXPENSE,
    Lucia,
    salary_income,
    supermarket_expense,
)

# Sends the message of a case, on top of what the case set up.
_Send = Callable[[InMemoryUnitOfWork, Lucia], object]
# 00:00 of Sunday 18 in Buenos Aires: when a message put off on Saturday 17 is due again.
START_OF_OCTOBER_18 = datetime(2026, 10, 18, 3, 0, 0, tzinfo=UTC)
DAILY_LIMIT_REACHED = (
    "Por hoy llegué al límite de mensajes que puedo leer. Lo que me mandes de acá en adelante "
    "lo guardo y lo proceso mañana."
)


def _answer(
    unit_of_work: InMemoryUnitOfWork,
    lucia: Lucia,
    text: str,
    classification: Classification,
    *,
    now: datetime = NOW,
) -> FakeLLM:
    llm = FakeLLM(classification)
    AnswerMessage(unit_of_work, FixedClock(now), llm).execute(
        lucia.message(text, sent_at=now - timedelta(seconds=5))
    )
    return llm


def _supermarket_without_account(unit_of_work: InMemoryUnitOfWork, lucia: Lucia) -> None:
    """The pending of C2-01: an expense of 3500 in Supermercado, with no account."""
    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("3500"),
            category="Supermercado",
        ),
    )


def test_the_day_of_the_counter_is_the_day_of_the_user() -> None:
    # Case C3-04. At 02:30 UTC of the 18th it is still 23:30 of the 17th in Buenos Aires.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    late = datetime(2026, 10, 18, 2, 30, 0, tzinfo=UTC)

    _answer(unit_of_work, lucia, SUPERMARKET_EXPENSE, supermarket_expense(), now=late)

    usage = unit_of_work.llm_usage
    assert usage.count(lucia.id, OCTOBER_17, UsageCounter.CLASSIFICATION) == 1
    assert usage.count(lucia.id, date(2026, 10, 18), UsageCounter.CLASSIFICATION) == 0


def _new_message(text: str, classification: Classification) -> _Send:
    def send(unit_of_work: InMemoryUnitOfWork, lucia: Lucia) -> object:
        return _answer(unit_of_work, lucia, text, classification)

    return send


def _reply_to_the_pending(text: str, classification: Classification) -> _Send:
    def send(unit_of_work: InMemoryUnitOfWork, lucia: Lucia) -> object:
        return _answer(unit_of_work, lucia, text, classification, now=NOW + timedelta(minutes=1))

    return send


@pytest.mark.parametrize(
    ("with_a_pending", "send", "counted"),
    [
        pytest.param(
            False, _new_message(SUPERMARKET_EXPENSE, supermarket_expense()), True, id="C1-01"
        ),
        pytest.param(False, _new_message(SALARY_INCOME, salary_income()), True, id="C1-02"),
        pytest.param(
            False,
            _new_message(
                "gasté 3500 en el súper",
                Classification(
                    MessageClass.REGISTRATION,
                    registration_type=RegistrationType.EXPENSE,
                    amount=Decimal("3500"),
                    category="Supermercado",
                ),
            ),
            True,
            id="C2-01",
        ),
        pytest.param(
            True,
            _reply_to_the_pending(
                "con MP",
                Classification(
                    MessageClass.REGISTRATION,
                    account="MP",
                    pending_reply=PendingReply.CONTINUES,
                ),
            ),
            True,
            id="C2-07",
        ),
        pytest.param(
            True,
            _reply_to_the_pending(
                "dejalo, no lo anotes",
                Classification(MessageClass.REGISTRATION, pending_reply=PendingReply.DISCARDS),
            ),
            True,
            id="C2-13",
        ),
        pytest.param(
            False,
            _new_message(
                "pasé 20000 de Galicia pesos a Mercado Pago",
                Classification(
                    MessageClass.REGISTRATION,
                    registration_type=RegistrationType.TRANSFER,
                    amount=Decimal("20000"),
                ),
            ),
            False,
            id="C1-09",
        ),
        pytest.param(
            False,
            _new_message("¿cuánto gasté este mes?", Classification(MessageClass.QUERY)),
            False,
            id="C1-10",
        ),
        pytest.param(
            False, _new_message("hola", Classification(MessageClass.NONE)), False, id="C1-12"
        ),
    ],
)
def test_what_counts_against_the_quota_of_registration_and_what_does_not(
    with_a_pending: bool, send: _Send, counted: bool
) -> None:
    # Case C3-06. The pending of C2-01 comes first when the message replies to it, and the
    # count starts after it.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    if with_a_pending:
        _supermarket_without_account(unit_of_work, lucia)
    key = (lucia.id, OCTOBER_17, UsageCounter.REGISTRATION)
    unit_of_work.llm_usage.counts[key] = 10

    send(unit_of_work, lucia)

    assert unit_of_work.llm_usage.counts[key] == (11 if counted else 10)


def test_a_message_put_off_is_not_an_attempt_nor_tells_a_failure() -> None:
    # Case C3-09. Stored with 2 attempts, this is the third and last: the claim counted it.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    unit_of_work.llm_usage.counts[(lucia.id, OCTOBER_17, UsageCounter.CLASSIFICATION)] = 100
    message = replace(lucia.message(SUPERMARKET_EXPENSE), attempts=3)
    llm = FakeLLM(supermarket_expense())

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(message)

    assert llm.requests == []
    assert unit_of_work.inbound_messages.deferred == [(message.id, 2, START_OF_OCTOBER_18)]
    assert unit_of_work.inbound_messages.failed == []
    assert unit_of_work.inbound_messages.retried == []
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == DAILY_LIMIT_REACHED
