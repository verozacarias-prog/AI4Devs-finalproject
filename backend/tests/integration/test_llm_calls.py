"""The record of each call to the model, against PostgreSQL (FEAT-003, its spec.md).

Case C3-15: a call whose final transaction is undone keeps its row (ADR 0023, point 5).
Case C3-17: the row of a classification says which fields came empty (CA-34). Case C3-19:
`scripts/llm_metrics.sql` gives the four metrics of ADR 0023 (CA-35).
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, RowMapping, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.adapters.observability.llm_calls import RecordedLLM
from app.adapters.outbound.postgres.repositories.llm_calls import PostgresLlmCallLog
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    PendingReply,
    RegistrationType,
)
from app.domain.use_cases.messages.answer_message import AnswerMessage
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound
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
METRICS_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "llm_metrics.sql"


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


def _run_round(settings: Settings, llm: FakeLLM, now: datetime = NOW) -> None:
    create_worker(settings, FixedClock(now), log_stream=io.StringIO(), llm=llm).run_round()


def _count(engine: Engine, query: str) -> int:
    with engine.connect() as connection:
        found: int = connection.execute(text(query)).scalar_one()
    return found


def _empty_fields(engine: Engine, message: uuid.UUID) -> list[str] | None:
    with engine.connect() as connection:
        found: list[str] | None = connection.execute(
            text("SELECT empty_fields FROM llm_call WHERE inbound_message_id = :id"),
            {"id": message},
        ).scalar_one()
    return found


def test_a_call_whose_final_transaction_is_undone_keeps_its_row(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-15. The first worker took the message and its lock ended; a second one took it
    # again and finished. The first one's final transaction is then undone.
    inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    lock = timedelta(seconds=settings.worker_lock_seconds)
    unit_of_work = SqlAlchemyUnitOfWork(create_engine(settings.database_url))
    first = ClaimNextMessage(unit_of_work, FixedClock(NOW), lock).execute()
    later = NOW + lock + timedelta(seconds=1)
    second = ClaimNextMessage(unit_of_work, FixedClock(later), lock).execute()
    assert first is not None and second is not None
    llm = RecordedLLM(FakeLLM(supermarket_expense()), PostgresLlmCallLog(engine))

    assert AnswerMessage(unit_of_work, FixedClock(later), llm).execute(second) is True
    assert AnswerMessage(unit_of_work, FixedClock(later), llm).execute(first) is False

    assert _count(engine, "SELECT count(*) FROM llm_call") == 2
    assert _count(engine, "SELECT count(*) FROM transaction") == 1


def test_the_row_of_a_classification_says_which_fields_came_empty(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-17. Only the names of the fields, never a value.
    expense = inbound(engine, "Lucía", "gasté 3500 en el súper", sent_at=SENT_AT)
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
    )
    greeting = inbound(engine, "Lucía", "hola", sent_at=NOW + timedelta(seconds=1))

    _run_round(settings, FakeLLM(Classification(MessageClass.NONE)), NOW + timedelta(seconds=2))

    empty = _empty_fields(engine, expense)
    assert empty is not None
    assert sorted(empty) == ["account", "currency", "transaction_date"]
    assert _empty_fields(engine, greeting) is None


def _metrics(engine: Engine) -> list[list[RowMapping]]:
    """Each statement of the script, in its order, with the rows it gives.

    The script is for psql, and its statements end with a semicolon; its comments are whole
    lines.
    """
    script = "\n".join(
        line
        for line in METRICS_SCRIPT.read_text().splitlines()
        if not line.lstrip().startswith("--")
    )
    statements = [statement for statement in script.split(";") if statement.strip()]
    with engine.connect() as connection:
        return [list(connection.execute(text(statement)).mappings()) for statement in statements]


def _call(
    engine: Engine,
    created_at: datetime,
    duration_ms: int,
    cost: str,
    outcome: str,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO llm_call (purpose, provider, model, prompt_version, input_tokens, "
                "output_tokens, duration_ms, estimated_cost_usd, outcome, created_at) VALUES "
                "('classification', 'openai', 'gpt-5.4-mini', 'test-1', 800, 60, :duration, "
                ":cost, :outcome, :created_at)"
            ),
            {
                "duration": duration_ms,
                "cost": Decimal(cost),
                "outcome": outcome,
                "created_at": created_at,
            },
        )


def test_the_metrics_script_gives_the_four_metrics(settings: Settings, engine: Engine) -> None:
    # Case C3-19. Two promoted pendings, as a user leaves them: one registered at once, and one
    # whose reply changed the amount. Their calls are then replaced by the rows of the case.
    inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    _run_round(settings, FakeLLM(supermarket_expense()))
    inbound(engine, "Lucía", "gasté 3500 en el súper", sent_at=NOW + timedelta(seconds=1))
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
        NOW + timedelta(seconds=2),
    )
    inbound(engine, "Lucía", "con MP, y eran 3800", sent_at=NOW + timedelta(minutes=1))
    _run_round(
        settings,
        FakeLLM(
            Classification(
                MessageClass.REGISTRATION,
                amount=Decimal("3800"),
                account="MP",
                pending_reply=PendingReply.CONTINUES,
            )
        ),
        NOW + timedelta(minutes=1, seconds=5),
    )
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM llm_call"))
    october_17 = datetime(2026, 10, 17, 15, 0, 0, tzinfo=UTC)
    for duration, outcome in (
        (1000, "ok"),
        (2000, "ok"),
        (3000, "ok"),
        (1500, "invalid_output"),
        (1500, "blocked"),
    ):
        _call(engine, october_17, duration, "0.001", outcome)
    _call(engine, october_17 - timedelta(days=1), 2000, "0.002", "ok")

    latency, cost, quality, hallucinations = _metrics(engine)

    [classification] = latency
    assert classification["purpose"] == "classification"
    assert float(classification["median_ms"]) == pytest.approx(1750)
    assert float(classification["p95_ms"]) == pytest.approx(2750)
    assert {(row["day"], row["purpose"]): row["cost_usd"] for row in cost} == {
        (date(2026, 10, 16), "classification"): Decimal("0.002"),
        (date(2026, 10, 17), "classification"): Decimal("0.005"),
    }
    [rates] = quality
    assert rates["confirmed_without_corrections_pct"] == Decimal("50.0")
    assert rates["invalid_output_pct"] == Decimal("16.7")
    [blocked] = hallucinations
    assert blocked["blocked_pct"] == Decimal("16.7")
