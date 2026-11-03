"""An amount that does not fit in NUMERIC(20,2), with the model replaced (issue #125).

Cases 2, 3 and 5 of #125: an amount of 19 or more integer digits is not registered nor fails the
message; it is asked again, in a new pending or in the open one. The database is in memory; the
integration tests check the largest amount that fits against PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities.classification import (
    Classification,
    MessageClass,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_usage import UsageCounter
from app.domain.entities.pending_transaction import PendingStatus
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, OCTOBER_17, Lucia

ASK_AGAIN = "Ese monto es más grande de lo que puedo registrar. ¿Cuánto fue?"


def _answer(
    unit_of_work: InMemoryUnitOfWork,
    lucia: Lucia,
    text: str,
    classification: Classification,
    *,
    now: datetime = NOW,
) -> None:
    AnswerMessage(unit_of_work, FixedClock(now), FakeLLM(classification)).execute(
        lucia.message(text, sent_at=now - timedelta(seconds=5))
    )


@pytest.mark.parametrize(
    "amount",
    [
        # Case 2 of #125: 19 integer digits, the first amount that does not fit.
        pytest.param("1000000000000000000", id="case-2"),
        # Case 3 of #125: 29 integer digits, where rounding to cents cannot even be done.
        pytest.param("10000000000000000000000000000", id="case-3"),
    ],
)
def test_an_amount_that_does_not_fit_is_asked_again(amount: str) -> None:
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _answer(
        unit_of_work,
        lucia,
        f"gasté {amount} en el súper con MP",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal(amount),
            account="MP",
            category="Supermercado",
        ),
    )

    assert unit_of_work.transactions.added == []
    assert unit_of_work.inbound_messages.failed == []
    [pending] = unit_of_work.pendings.added
    assert pending.missing_fields == ("amount",)
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text.splitlines()[-1] == ASK_AGAIN
    usage = unit_of_work.llm_usage
    assert usage.count(lucia.id, OCTOBER_17, UsageCounter.CLASSIFICATION) == 1
    assert usage.count(lucia.id, OCTOBER_17, UsageCounter.REGISTRATION) == 1


def test_a_reply_with_an_amount_that_does_not_fit_asks_again() -> None:
    # Case 5 of #125. The pending of C2-04 lacks the amount, and the reply gives one too large.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "cargué nafta con MP",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            account="MP",
            category="Transporte",
        ),
    )

    _answer(
        unit_of_work,
        lucia,
        "1000000000000000000",
        Classification(
            MessageClass.REGISTRATION,
            amount=Decimal("1000000000000000000"),
            pending_reply=PendingReply.CONTINUES,
        ),
        now=NOW + timedelta(minutes=1),
    )

    assert unit_of_work.transactions.added == []
    assert unit_of_work.inbound_messages.failed == []
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.OPEN
    assert pending.missing_fields == ("amount",)
    assert unit_of_work.outbound_messages.added[-1].text.splitlines()[-1] == ASK_AGAIN
