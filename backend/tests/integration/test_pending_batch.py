"""A batch of several pendings, asked and answered by number, against PostgreSQL (FEAT-007).

Cases C2-01, C2-02 and C2-10 of its spec.md: a message with an incomplete movement registers
none and lists them by number, the reply by number completes the batch, and another movement
joins the batch that awaits a reply. The worker runs whole rounds, the way its process does,
with the model replaced by a double: no test reaches the provider.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import cast

import pytest
from sqlalchemy import Engine, Row, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.adapters.outbound.postgres.repositories.pendings import PostgresPendingRepository
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    MovementReading,
    NumberedReply,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.pending_transaction import BatchStatus, PendingStatus
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, seed_on_october_1

pytestmark = pytest.mark.integration

SENT_AT = NOW - timedelta(seconds=5)
ALL_ACCOUNTS = "¿Con qué cuenta? Galicia pesos, Mercado Pago, Efectivo o Galicia USD."


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
            "DEV_ENTRY_ENABLED": "true",
            "WEB_CHAT_ENABLED": "true",
        }
    )


def _run_round(settings: Settings, classification: Classification, *, minutes: int = 0) -> None:
    clock = FixedClock(NOW + timedelta(minutes=minutes))
    worker = create_worker(settings, clock, log_stream=io.StringIO(), llm=FakeLLM(classification))
    worker.run_round()


def _expense(amount: str, account: str | None, category: str) -> MovementReading:
    return MovementReading(
        registration_type=RegistrationType.EXPENSE,
        amount=Decimal(amount),
        account=account,
        category=category,
    )


def _registration(
    first: MovementReading,
    *more: MovementReading,
    pending_reply: PendingReply | None = None,
) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=first.registration_type,
        amount=first.amount,
        account=first.account,
        category=first.category,
        more_movements=more,
        pending_reply=pending_reply,
    )


def _batches(engine: Engine) -> list[Row[tuple[object, ...]]]:
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    "SELECT id, status, awaiting_reply, question_message_id, "
                    "confirmation_message_id FROM pending_batch"
                )
            ).all()
        )


def _pendings(engine: Engine) -> list[Row[tuple[object, ...]]]:
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    "SELECT batch_id, position, status, missing_fields, "
                    "resulting_transaction_id FROM pending_transaction ORDER BY position"
                )
            ).all()
        )


def _transactions(engine: Engine) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT t.id, t.amount, a.name AS account FROM transaction t "
                "JOIN account a ON a.id = t.account_id ORDER BY t.amount DESC"
            )
        ).all()
    return [dict(row._mapping) for row in rows]


def _reply_to(engine: Engine, message: uuid.UUID) -> dict[str, object]:
    with engine.connect() as connection:
        [row] = connection.execute(
            text("SELECT id, content FROM outbound_message WHERE inbound_message_id = :id"),
            {"id": message},
        ).all()
    content = row.content if isinstance(row.content, dict) else json.loads(row.content)
    return {"id": row.id, **content}


def _supermarket_and_nafta(settings: Settings, engine: Engine) -> uuid.UUID:
    """The message of C2-01, processed: the supermarket with MP and the nafta with no account."""
    message = inbound(
        engine, "Lucía", "gasté 3500 en el súper con MP y 1200 de nafta", sent_at=SENT_AT
    )
    _run_round(
        settings,
        _registration(_expense("3500", "MP", "Supermercado"), _expense("1200", None, "Transporte")),
    )
    return message


def test_with_an_incomplete_movement_none_is_registered_and_the_question_lists_them(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-01.
    message = _supermarket_and_nafta(settings, engine)

    assert _transactions(engine) == []
    [batch] = _batches(engine)
    assert batch.status == "open"
    assert batch.awaiting_reply is True
    first, second = _pendings(engine)
    for pending in (first, second):
        assert pending.batch_id == batch.id
        assert pending.status == "open"
    assert (first.position, first.missing_fields) == (1, [])
    assert (second.position, second.missing_fields) == (2, ["account_id"])
    reply = _reply_to(engine, message)
    assert batch.question_message_id == reply["id"]
    assert reply["response_kind"] == "registration"
    assert str(reply["text"]).splitlines() == [
        "1. El gasto de $3.500 en Supermercado con Mercado Pago, completo.",
        "",
        "2. El gasto de $1.200 en Transporte.",
        ALL_ACCOUNTS,
    ]


def test_the_reply_by_number_completes_the_batch_and_they_are_registered_together(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-02.
    _supermarket_and_nafta(settings, engine)
    reply = inbound(engine, "Lucía", "el 2 en efectivo", sent_at=SENT_AT + timedelta(minutes=1))

    _run_round(
        settings,
        Classification(
            MessageClass.REGISTRATION,
            pending_reply=PendingReply.CONTINUES,
            numbered_replies=(
                NumberedReply(number=2, reading=MovementReading(account="efectivo")),
            ),
        ),
        minutes=1,
    )

    supermarket, nafta = _transactions(engine)
    assert (supermarket["amount"], supermarket["account"]) == (
        Decimal("3500.00"),
        "Mercado Pago",
    )
    assert (nafta["amount"], nafta["account"]) == (Decimal("1200.00"), "Efectivo")
    first, second = _pendings(engine)
    assert (first.position, first.status) == (1, "promoted")
    assert first.resulting_transaction_id == supermarket["id"]
    assert (second.position, second.status) == (2, "promoted")
    assert second.resulting_transaction_id == nafta["id"]
    [batch] = _batches(engine)
    assert batch.status == "closed"
    assert batch.awaiting_reply is False
    confirmation = _reply_to(engine, reply)
    assert batch.confirmation_message_id == confirmation["id"]
    assert str(confirmation["text"]).splitlines()[0] == "¡Listo! Anoté 2 movimientos:"


def test_with_a_batch_awaiting_a_reply_another_movement_joins_it(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-10. The pending of C2-01 of FEAT-003: the supermarket with no account.
    inbound(engine, "Lucía", "gasté 3500 en el súper", sent_at=SENT_AT)
    _run_round(settings, _registration(_expense("3500", None, "Supermercado")))
    message = inbound(
        engine, "Lucía", "y 1200 de nafta en efectivo", sent_at=SENT_AT + timedelta(minutes=1)
    )

    _run_round(
        settings,
        _registration(
            _expense("1200", "efectivo", "Transporte"),
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        minutes=1,
    )

    assert _transactions(engine) == []
    [batch] = _batches(engine)
    assert batch.status == "open"
    assert batch.awaiting_reply is True
    first, second = _pendings(engine)
    assert (first.position, first.status, first.missing_fields) == (1, "open", ["account_id"])
    assert (second.position, second.status, second.missing_fields) == (2, "open", [])
    assert second.batch_id == batch.id
    reply = _reply_to(engine, message)
    assert batch.question_message_id == reply["id"]
    assert str(reply["text"]).splitlines() == [
        "1. El gasto de $3.500 en Supermercado.",
        ALL_ACCOUNTS,
        "",
        "2. El gasto de $1.200 en Transporte con Efectivo, completo.",
    ]


def test_the_pendings_of_a_batch_are_not_read_with_another_user(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-25. The batch of C2-01.
    inbound(engine, "Lucía", "gasté 3500 en el súper con MP y 1200 de nafta", sent_at=SENT_AT)
    _run_round(
        settings,
        _registration(_expense("3500", "MP", "Supermercado"), _expense("1200", None, "Transporte")),
    )
    [batch] = _batches(engine)
    batch_id = cast(uuid.UUID, batch.id)

    with engine.connect() as connection:
        pendings = PostgresPendingRepository(connection)
        of_pablo = pendings.list_in_batch(batch_id, user_id(engine, "Pablo"))
        of_lucia = pendings.list_in_batch(batch_id, user_id(engine, "Lucía"))

    assert of_pablo == []
    assert [pending.position for pending in of_lucia] == [1, 2]


def test_a_pending_is_not_updated_with_another_user(settings: Settings, engine: Engine) -> None:
    # Case T-01 of issue 154. The batch of C2-01.
    inbound(engine, "Lucía", "gasté 3500 en el súper con MP y 1200 de nafta", sent_at=SENT_AT)
    _run_round(
        settings,
        _registration(_expense("3500", "MP", "Supermercado"), _expense("1200", None, "Transporte")),
    )
    [batch] = _batches(engine)
    with engine.begin() as connection:
        pendings = PostgresPendingRepository(connection)
        second = pendings.list_in_batch(cast(uuid.UUID, batch.id), user_id(engine, "Lucía"))[1]
        pendings.update(
            replace(second, status=PendingStatus.REJECTED, user_id=user_id(engine, "Pablo"))
        )

    assert [pending.status for pending in _pendings(engine)] == ["open", "open"]


def test_a_batch_is_not_updated_with_another_user(settings: Settings, engine: Engine) -> None:
    # Case T-02 of issue 154. The batch of C2-01.
    inbound(engine, "Lucía", "gasté 3500 en el súper con MP y 1200 de nafta", sent_at=SENT_AT)
    _run_round(
        settings,
        _registration(_expense("3500", "MP", "Supermercado"), _expense("1200", None, "Transporte")),
    )
    with engine.begin() as connection:
        pendings = PostgresPendingRepository(connection)
        awaiting = pendings.find_awaiting_reply(user_id(engine, "Lucía"))
        assert awaiting is not None
        batch, _ = awaiting
        pendings.update_batch(
            replace(
                batch,
                status=BatchStatus.CLOSED,
                awaiting_reply=False,
                user_id=user_id(engine, "Pablo"),
            )
        )

    [stored] = _batches(engine)
    assert (stored.status, stored.awaiting_reply) == ("open", True)
