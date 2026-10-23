"""What the registration leaves in the logs, against PostgreSQL (FEAT-003, its spec.md).

Case C3-12: no line carries the text, the amount or the phone (ADR 0023, point 2). Case C3-20:
a message left for another attempt is not logged as answered, and its failure leaves a line.
The worker writes its lines in a stream the test reads.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine

from app.adapters.inbound.message_worker.worker import create_worker
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, status_of
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.log_lines import events_of, lines_of
from tests.support.registration_data import (
    NOW,
    SUPERMARKET_EXPENSE,
    seed_on_october_1,
    supermarket_expense,
)

pytestmark = pytest.mark.integration

# What no line may carry: the amount in both ways, the words, the account, the name and the
# phone of Lucía.
PERSONAL_DATA = ("3500", "3.500", "súper", "con MP", "Mercado Pago", "Lucía", "000000000001")


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


def _run_round(settings: Settings, llm: FakeLLM, now: datetime, stream: io.StringIO) -> None:
    create_worker(settings, FixedClock(now), log_stream=stream, llm=llm).run_round()


def _free_text_of(stream: io.StringIO) -> str:
    """Every value of every line, except the moment and the identifiers.

    Those have a fixed shape the filter checks, and a random one may hold "3500" by chance.
    """
    return "\n".join(
        str(value)
        for line in lines_of(stream)
        for key, value in line.items()
        if key != "ts" and not key.endswith("_id")
    )


def test_no_log_line_carries_the_text_the_amount_or_the_phone(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-12. The first message stays pending; the reply registers it.
    stream = io.StringIO()
    first = inbound(engine, "Lucía", "gasté 3500 en el súper", sent_at=NOW - timedelta(seconds=5))
    _run_round(
        settings,
        FakeLLM(
            Classification(
                MessageClass.REGISTRATION,
                registration_type=RegistrationType.EXPENSE,
                amount=Decimal("3500"),
                category="Supermercado",
            )
        ),
        NOW,
        stream,
    )
    reply_at = NOW + timedelta(minutes=1)
    reply = inbound(engine, "Lucía", "con MP", sent_at=reply_at - timedelta(seconds=5))

    _run_round(
        settings,
        FakeLLM(
            Classification(
                MessageClass.REGISTRATION, account="MP", pending_reply=PendingReply.CONTINUES
            )
        ),
        reply_at,
        stream,
    )

    assert status_of(engine, first)[0] == "processed"
    assert status_of(engine, reply)[0] == "processed"
    assert len(events_of(stream, "message.answered")) == 2
    free_text = _free_text_of(stream)
    for data in PERSONAL_DATA:
        assert data not in free_text, data
    assert "000000000001" not in stream.getvalue()


def test_a_message_left_for_another_attempt_is_not_logged_as_answered(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-20. The message of C2-25, with the provider down.
    stream = io.StringIO()
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=NOW - timedelta(seconds=5))
    llm = FakeLLM(supermarket_expense(), error=ModelCallFailedError(LlmOutcome.PROVIDER_ERROR))

    _run_round(settings, llm, NOW, stream)

    assert status_of(engine, message) == ("pending", 1)
    assert events_of(stream, "message.answered") == []
    [error] = [
        line for line in lines_of(stream) if line.get("error_type") == "ModelCallFailedError"
    ]
    assert error["event"] == "error.expected"
    assert error["error_code"] == "model_call_failed"
    assert error["message_id"] == str(message)
    for data in PERSONAL_DATA:
        assert data not in _free_text_of(stream), data
