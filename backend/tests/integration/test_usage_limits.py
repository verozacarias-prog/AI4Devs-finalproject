"""The daily limits of use, against PostgreSQL (FEAT-003, its spec.md).

Cases C3-01 to C3-03, C3-05, C3-07, C3-08, C3-11, C3-21 and C3-22: the total daily cap before
classifying, the quota of registration after it, the messages put off to the next day, the
event of a limit reached, a call that failed, and which messages put off were answered. The
worker runs whole rounds, with the model replaced by a double inside the wrapper that records
each call.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.domain.entities.classification import Classification, MessageClass
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError, ModelRefusedError
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, status_of, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.log_lines import events_of, lines_of
from tests.support.registration_data import (
    NOW,
    OCTOBER_17,
    SUPERMARKET_EXPENSE,
    seed_on_october_1,
    supermarket_expense,
)

pytestmark = pytest.mark.integration

SENT_AT = NOW - timedelta(seconds=5)
OCTOBER_18 = date(2026, 10, 18)
# 00:00 of Sunday 18 in Buenos Aires: when a message put off on Saturday 17 is due again.
START_OF_OCTOBER_18 = datetime(2026, 10, 18, 3, 0, 0, tzinfo=UTC)
DAILY_LIMIT_REACHED = (
    "Por hoy llegué al límite de mensajes que puedo leer. Lo que me mandes de acá en adelante "
    "lo guardo y lo proceso mañana."
)
REGISTRATION_QUOTA_USED_UP = (
    "Por hoy ya anoté todo lo que puedo. Este lo guardo y lo anoto mañana, con la fecha de hoy."
)
ASK_FOR_DETAILS = (
    "¡Hola! Soy Platita y te ayudo a llevar las cuentas. Contame qué gastaste o qué cobraste, y "
    "con qué cuenta. Por ejemplo: «gasté 3500 en el súper con Mercado Pago»."
)


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


def _run_round(
    settings: Settings, llm: FakeLLM, now: datetime = NOW, stream: io.StringIO | None = None
) -> None:
    create_worker(
        settings, FixedClock(now), log_stream=stream or io.StringIO(), llm=llm
    ).run_round()


def _set_usage(
    engine: Engine,
    day: date,
    counter: str,
    count: int,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """What Lucía already used that day, in one of her counters."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO llm_usage (user_id, usage_date, quota, message_count, "
                "input_tokens, output_tokens) SELECT id, :day, :counter, :count, :input, "
                ":output FROM app_user WHERE name = 'Lucía'"
            ),
            {
                "day": day,
                "counter": counter,
                "count": count,
                "input": input_tokens,
                "output": output_tokens,
            },
        )


def _usage(engine: Engine, day: date, counter: str) -> tuple[int, int, int] | None:
    """Lucía's count of that day and counter, with its tokens, or None if there is no row."""
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT message_count, input_tokens, output_tokens FROM llm_usage u "
                "JOIN app_user a ON a.id = u.user_id "
                "WHERE a.name = 'Lucía' AND usage_date = :day AND quota = :counter"
            ),
            {"day": day, "counter": counter},
        ).one_or_none()
    return None if row is None else (row.message_count, row.input_tokens, row.output_tokens)


def _replies_to(engine: Engine, message: uuid.UUID) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT content FROM outbound_message WHERE inbound_message_id = :id "
                "ORDER BY created_at"
            ),
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


def _count(engine: Engine, query: str, **parameters: object) -> int:
    with engine.connect() as connection:
        found: int = connection.execute(text(query), parameters).scalar_one()
    return found


def _transactions(engine: Engine) -> list[date]:
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT transaction_date FROM transaction")).all()
    return [row.transaction_date for row in rows]


def test_with_the_daily_cap_reached_the_message_is_not_classified_and_is_put_off(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-01.
    _set_usage(engine, OCTOBER_17, "classification", 100)
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    llm = FakeLLM(supermarket_expense())

    _run_round(settings, llm)

    assert llm.requests == []
    assert (
        _count(engine, "SELECT count(*) FROM llm_call WHERE inbound_message_id = :id", id=message)
        == 0
    )
    assert _transactions(engine) == []
    assert status_of(engine, message) == ("pending", 0)
    assert _next_attempt_at(engine, message) == START_OF_OCTOBER_18
    [reply] = _replies_to(engine, message)
    assert reply["text"] == DAILY_LIMIT_REACHED
    assert reply["response_kind"] == "fixed_text"


def test_the_notice_of_the_cap_goes_out_once_a_day(settings: Settings, engine: Engine) -> None:
    # Case C3-02.
    _set_usage(engine, OCTOBER_17, "classification", 100)
    first = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    _run_round(settings, FakeLLM(supermarket_expense()))
    assert len(_replies_to(engine, first)) == 1
    greeting = inbound(engine, "Lucía", "hola", sent_at=NOW + timedelta(seconds=1))

    _run_round(settings, FakeLLM(Classification(MessageClass.NONE)), NOW + timedelta(seconds=2))

    assert status_of(engine, greeting)[0] == "pending"
    assert _next_attempt_at(engine, greeting) == START_OF_OCTOBER_18
    assert _replies_to(engine, greeting) == []
    assert _count(engine, "SELECT count(*) FROM outbound_message") == 1


def test_each_classification_adds_one_to_the_cap_of_the_day_with_its_tokens(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-03. A greeting counts against the cap and against no quota.
    _set_usage(engine, OCTOBER_17, "classification", 7, input_tokens=100, output_tokens=10)
    _set_usage(engine, OCTOBER_17, "registration", 3)
    inbound(engine, "Lucía", "hola", sent_at=SENT_AT)

    _run_round(
        settings, FakeLLM(Classification(MessageClass.NONE), input_tokens=900, output_tokens=40)
    )

    assert _usage(engine, OCTOBER_17, "classification") == (8, 1000, 50)
    assert _usage(engine, OCTOBER_17, "registration") == (3, 0, 0)


def _expense_with_the_quota_used_up(settings: Settings, engine: Engine) -> uuid.UUID:
    """The message of C3-05: Lucía already registered 50 movements and classified 60 today."""
    _set_usage(engine, OCTOBER_17, "registration", 50)
    _set_usage(engine, OCTOBER_17, "classification", 60)
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    _run_round(settings, FakeLLM(supermarket_expense()))
    return message


def test_with_the_quota_of_registration_used_up_an_expense_is_put_off_with_its_fixed_text(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-05.
    _set_usage(engine, OCTOBER_17, "registration", 50)
    _set_usage(engine, OCTOBER_17, "classification", 60)
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    llm = FakeLLM(supermarket_expense())

    _run_round(settings, llm)

    assert len(llm.requests) == 1
    assert _transactions(engine) == []
    assert _count(engine, "SELECT count(*) FROM pending_transaction") == 0
    assert status_of(engine, message)[0] == "pending"
    assert _next_attempt_at(engine, message) == START_OF_OCTOBER_18
    [reply] = _replies_to(engine, message)
    assert reply["text"] == REGISTRATION_QUOTA_USED_UP
    assert reply["response_kind"] == "fixed_text"
    classification = _usage(engine, OCTOBER_17, "classification")
    assert classification is not None
    assert classification[0] == 61
    assert _usage(engine, OCTOBER_17, "registration") == (50, 0, 0)


def test_a_message_put_off_does_not_hold_back_the_next_ones(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-07.
    put_off = _expense_with_the_quota_used_up(settings, engine)
    greeting = inbound(engine, "Lucía", "hola", sent_at=NOW + timedelta(seconds=1))

    _run_round(settings, FakeLLM(Classification(MessageClass.NONE)), NOW + timedelta(seconds=2))

    assert status_of(engine, put_off)[0] == "pending"
    assert status_of(engine, greeting)[0] == "processed"
    [reply] = _replies_to(engine, greeting)
    assert reply["text"] == ASK_FOR_DETAILS


def test_the_next_day_the_message_put_off_is_registered_with_the_day_it_was_written(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-08. 09:00 of Sunday 18 in Buenos Aires.
    message = _expense_with_the_quota_used_up(settings, engine)
    sunday_morning = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)

    _run_round(settings, FakeLLM(supermarket_expense()), sunday_morning)

    assert _transactions(engine) == [OCTOBER_17]
    confirmation = _replies_to(engine, message)[-1]
    assert "Fecha: 17/10/2026" in str(confirmation["text"]).splitlines()
    registration = _usage(engine, OCTOBER_18, "registration")
    assert registration is not None
    assert registration[0] == 1


@pytest.mark.parametrize(("counter", "used"), [("classification", 100), ("registration", 50)])
def test_going_over_the_cap_or_the_quota_leaves_its_event_without_the_phone(
    settings: Settings, engine: Engine, counter: str, used: int
) -> None:
    # Case C3-11. The messages of C3-01 and of C3-05.
    _set_usage(engine, OCTOBER_17, counter, used)
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    stream = io.StringIO()

    _run_round(settings, FakeLLM(supermarket_expense()), stream=stream)

    [event] = events_of(stream, "usage.quota_exceeded")
    assert event["user_id"] == str(user_id(engine, "Lucía"))
    assert event["message_id"] == str(message)
    assert event["quota"] == counter
    assert "000000000001" not in stream.getvalue()
    for line in lines_of(stream):
        for key, value in line.items():
            if key != "ts" and not key.endswith("_id"):
                assert "súper" not in str(value)
                assert "3500" not in str(value)


@pytest.mark.parametrize(
    ("error", "status", "classified"),
    [
        (ModelCallFailedError(LlmOutcome.PROVIDER_ERROR), ("pending", 1), 7),
        (ModelRefusedError(), ("processed", 1), 8),
    ],
)
def test_a_failed_call_does_not_add_to_the_cap_and_a_refusal_does(
    settings: Settings,
    engine: Engine,
    error: Exception,
    status: tuple[str, int],
    classified: int,
) -> None:
    # Case C3-21. A fall of the provider does not use up the cap of the user; a refusal is a
    # message processed with its fixed text (ADR 0018, point 3).
    _set_usage(engine, OCTOBER_17, "classification", 7)
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)

    _run_round(settings, FakeLLM(supermarket_expense(), error=error))

    assert status_of(engine, message) == status
    classification = _usage(engine, OCTOBER_17, "classification")
    assert classification is not None
    assert classification[0] == classified


def _answered(stream: io.StringIO, message: uuid.UUID) -> int:
    return sum(
        1 for line in events_of(stream, "message.answered") if line["message_id"] == str(message)
    )


def test_a_message_put_off_with_a_notice_is_answered_and_one_put_off_in_silence_is_not(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-22. The messages of C3-01 and C3-02, and then the one of C3-05.
    stream = io.StringIO()
    _set_usage(engine, OCTOBER_17, "classification", 100)
    with_the_notice = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    _run_round(settings, FakeLLM(supermarket_expense()), stream=stream)
    in_silence = inbound(engine, "Lucía", "hola", sent_at=NOW + timedelta(seconds=1))
    _run_round(
        settings,
        FakeLLM(Classification(MessageClass.NONE)),
        NOW + timedelta(seconds=2),
        stream,
    )
    # Pablo, with the quota of registration used up: the message of C3-05.
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO llm_usage (user_id, usage_date, quota, message_count) "
                "SELECT id, :day, 'registration', 50 FROM app_user WHERE name = 'Pablo'"
            ),
            {"day": OCTOBER_17},
        )
    over_the_quota = inbound(engine, "Pablo", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    _run_round(settings, FakeLLM(supermarket_expense()), NOW + timedelta(seconds=3), stream)

    assert _replies_to(engine, over_the_quota)[0]["text"] == REGISTRATION_QUOTA_USED_UP
    assert _answered(stream, with_the_notice) == 1
    assert _answered(stream, over_the_quota) == 1
    assert _answered(stream, in_silence) == 0
