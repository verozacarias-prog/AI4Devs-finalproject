"""What a batch of several movements leaves to measure, against PostgreSQL (FEAT-007).

Cases C3-01 and C3-04 of its spec.md: the line of a message with several movements says how
many came and how many entered the batch, with no data of the user, and the corrections of each
pending are stored. The worker runs whole rounds, with the model replaced by a double.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    MovementReading,
    NumberedReply,
    PendingReply,
    RegistrationType,
)
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.log_lines import events_of, lines_of
from tests.support.registration_data import NOW, seed_on_october_1

pytestmark = pytest.mark.integration

SENT_AT = NOW - timedelta(seconds=5)
# What no line may carry: the amounts in both ways, the words, the accounts, the name and the
# phone of Lucía.
PERSONAL_DATA = (
    "3500",
    "3.500",
    "1200",
    "1.200",
    "súper",
    "heladera",
    "Mercado Pago",
    "Efectivo",
    "Lucía",
    "000000000001",
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
    settings: Settings, classification: Classification, now: datetime, stream: io.StringIO
) -> None:
    llm = FakeLLM(classification)
    create_worker(settings, FixedClock(now), log_stream=stream, llm=llm).run_round()


def _expense(amount: str, account: str | None, category: str) -> MovementReading:
    return MovementReading(
        registration_type=RegistrationType.EXPENSE,
        amount=Decimal(amount),
        account=account,
        category=category,
    )


def _registration(first: MovementReading, *more: MovementReading) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=first.registration_type,
        amount=first.amount,
        account=first.account,
        category=first.category,
        more_movements=more,
    )


def _free_text_of(stream: io.StringIO) -> str:
    """Every value of every line, except the moment and the identifiers, whose random shape may
    hold "3500" by chance.
    """
    return "\n".join(
        str(value)
        for line in lines_of(stream)
        for key, value in line.items()
        if key != "ts" and not key.endswith("_id")
    )


def test_the_line_of_a_message_with_several_movements_says_how_many_came_and_entered(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-01.
    stream = io.StringIO()
    inbound(
        engine,
        "Lucía",
        "gasté 3500 en el súper con MP, 1200 de nafta en efectivo y compré una heladera en cuotas",
        sent_at=SENT_AT,
    )

    _run_round(
        settings,
        _registration(
            _expense("3500", "MP", "Supermercado"),
            _expense("1200", "efectivo", "Transporte"),
            MovementReading(registration_type=RegistrationType.CARD_PURCHASE),
        ),
        NOW,
        stream,
    )

    [answered] = events_of(stream, "message.answered")
    assert answered["movements"] == 3
    assert answered["batched"] == 2
    free_text = _free_text_of(stream)
    for data in PERSONAL_DATA:
        assert data not in free_text, data


def _corrections(engine: Engine) -> dict[int, int]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT position, corrected_fields_count FROM pending_transaction")
        ).all()
    return {row.position: row.corrected_fields_count for row in rows}


def test_the_corrections_of_each_pending_of_the_batch_are_stored(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-04. The batch of C2-01, and then the reply by number.
    stream = io.StringIO()
    inbound(engine, "Lucía", "gasté 3500 en el súper con MP y 1200 de nafta", sent_at=SENT_AT)
    _run_round(
        settings,
        _registration(_expense("3500", "MP", "Supermercado"), _expense("1200", None, "Transporte")),
        NOW,
        stream,
    )
    reply_at = NOW + timedelta(minutes=1)
    inbound(
        engine, "Lucía", "el 2 fueron 1300 en efectivo", sent_at=reply_at - timedelta(seconds=5)
    )

    _run_round(
        settings,
        Classification(
            MessageClass.REGISTRATION,
            pending_reply=PendingReply.CONTINUES,
            numbered_replies=(
                NumberedReply(
                    number=2,
                    reading=MovementReading(amount=Decimal("1300"), account="efectivo"),
                ),
            ),
        ),
        reply_at,
        stream,
    )

    assert _corrections(engine) == {1: 0, 2: 1}
