"""A transfer that lacks something, and its continuation, against PostgreSQL (FEAT-006).

Cases C2-01, C2-04, C2-08 and C3-02 of docs/features/FEAT-006/spec.md. The worker runs rounds,
the way its process does, with the model replaced by a double inside the wrapper that records
each call. A case that starts from an open pending gets it the way a user does: a first message that
leaves it pending, and then the reply.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    PendingReply,
    RegistrationType,
)
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, status_of, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, OCTOBER_17, seed_on_october_1

pytestmark = pytest.mark.integration


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


def _write_and_answer(
    settings: Settings,
    engine: Engine,
    message: str,
    classification: Classification,
    *,
    now: datetime = NOW,
) -> uuid.UUID:
    """A message of Lucía, and the round of the worker that answers it."""
    written = inbound(engine, "Lucía", message, sent_at=now - timedelta(seconds=5))
    create_worker(
        settings, FixedClock(now), log_stream=io.StringIO(), llm=FakeLLM(classification)
    ).run_round()
    return written


def _transfer(
    *, amount: str = "20000", account: str | None = None, to_account: str | None = None
) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=RegistrationType.TRANSFER,
        amount=Decimal(amount),
        account=account,
        to_account=to_account,
    )


def _rows(engine: Engine, query: str, **parameters: object) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(text(query), parameters).all()
    return [dict(row._mapping) for row in rows]


def _replies_to(engine: Engine, message: uuid.UUID) -> list[dict[str, object]]:
    replies = []
    for row in _rows(
        engine,
        "SELECT id, content FROM outbound_message WHERE inbound_message_id = :id",
        id=message,
    ):
        content = row["content"]
        decoded = content if isinstance(content, dict) else json.loads(str(content))
        replies.append({"id": row["id"], **decoded})
    return replies


def _registrations_of_october_17(engine: Engine) -> list[dict[str, object]]:
    return _rows(
        engine,
        "SELECT u.message_count FROM llm_usage u JOIN app_user a ON a.id = u.user_id "
        "WHERE a.name = 'Lucía' AND u.usage_date = :day AND u.quota = 'registration'",
        day=OCTOBER_17,
    )


def _transfers(engine: Engine) -> list[dict[str, object]]:
    return _rows(
        engine,
        "SELECT t.id, t.from_amount, t.from_currency, t.to_amount, t.to_currency, "
        "t.transfer_date, f.name AS from_account, d.name AS to_account FROM transfer t "
        "JOIN account f ON f.id = t.from_account_id JOIN account d ON d.id = t.to_account_id",
    )


def _from_galicia_pesos(settings: Settings, engine: Engine) -> uuid.UUID:
    """The pending of C2-01."""
    return _write_and_answer(
        settings, engine, "pasé 20000 de Galicia pesos", _transfer(account="Galicia pesos")
    )


def test_a_transfer_without_a_destination_stays_pending_and_asks_where_it_went(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-01.
    lucia = user_id(engine, "Lucía")

    message = _from_galicia_pesos(settings, engine)

    assert _rows(engine, "SELECT id FROM transfer") == []
    [reply] = _replies_to(engine, message)
    [batch] = _rows(engine, "SELECT * FROM pending_batch")
    assert batch["user_id"] == lucia
    assert batch["source"] == "manual"
    assert batch["status"] == "open"
    assert batch["awaiting_reply"] is True
    assert batch["question_message_id"] == reply["id"]
    [pending] = _rows(engine, "SELECT * FROM pending_transaction")
    assert pending["batch_id"] == batch["id"]
    assert pending["status"] == "open"
    assert pending["intent"] == "transfer"
    assert pending["missing_fields"] == ["to_account_id"]
    assert status_of(engine, message)[0] == "processed"
    assert _registrations_of_october_17(engine) == [{"message_count": 1}]
    assert reply["response_kind"] == "registration"
    assert reply["text"] == "¿A qué cuenta fue? Mercado Pago, Efectivo o Galicia USD."


def test_the_reply_completes_the_pending_and_registers_the_transfer(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-04.
    _from_galicia_pesos(settings, engine)

    reply_message = _write_and_answer(
        settings,
        engine,
        "a Mercado Pago",
        Classification(
            MessageClass.REGISTRATION,
            to_account="Mercado Pago",
            pending_reply=PendingReply.CONTINUES,
        ),
        now=NOW + timedelta(minutes=1),
    )

    [transfer] = _transfers(engine)
    assert transfer["from_account"] == "Galicia pesos"
    assert transfer["to_account"] == "Mercado Pago"
    assert transfer["from_amount"] == Decimal("20000.00")
    assert transfer["to_amount"] == Decimal("20000.00")
    assert (transfer["from_currency"], transfer["to_currency"]) == ("ARS", "ARS")
    assert transfer["transfer_date"] == OCTOBER_17
    [pending] = _rows(engine, "SELECT * FROM pending_transaction")
    assert pending["status"] == "promoted"
    assert pending["missing_fields"] == []
    assert pending["resulting_transfer_id"] == transfer["id"]
    [confirmation] = _replies_to(engine, reply_message)
    [batch] = _rows(engine, "SELECT * FROM pending_batch")
    assert batch["status"] == "closed"
    assert batch["awaiting_reply"] is False
    assert batch["confirmation_message_id"] == confirmation["id"]
    assert confirmation["text"] == (
        "¡Listo! Anoté una transferencia de $20.000 de Galicia pesos a Mercado Pago.\n"
        "No cuenta como gasto.\n"
        "Fecha: 17/10/2026\n"
        "Moneda: ARS"
    )


def test_a_transfer_between_different_currencies_gets_the_fixed_text_and_stays_no_pending(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-08.
    message = _write_and_answer(
        settings,
        engine,
        "pasé 100 de Galicia USD a Mercado Pago",
        _transfer(amount="100", account="Galicia USD", to_account="Mercado Pago"),
    )

    assert _rows(engine, "SELECT id FROM transfer") == []
    assert _rows(engine, "SELECT id FROM pending_batch") == []
    assert _rows(engine, "SELECT id FROM pending_transaction") == []
    assert (
        len(_rows(engine, "SELECT id FROM llm_call WHERE inbound_message_id = :id", id=message))
        == 1
    )
    assert _registrations_of_october_17(engine) == []
    assert status_of(engine, message)[0] == "processed"
    [reply] = _replies_to(engine, message)
    assert reply["response_kind"] == "fixed_text"
    assert reply["text"] == (
        "Todavía no sé anotar una transferencia entre cuentas de distinta moneda. Por ahora, "
        "solo entre cuentas de la misma moneda."
    )


def test_a_reply_that_changes_the_amount_of_a_pending_transfer_adds_a_correction(
    settings: Settings, engine: Engine
) -> None:
    # Case C3-02. The amount changed, which the model had interpreted; the destination was
    # missing, and completing it does not count.
    _from_galicia_pesos(settings, engine)

    _write_and_answer(
        settings,
        engine,
        "no, fueron 30 lucas, a Mercado Pago",
        Classification(
            MessageClass.REGISTRATION,
            amount=Decimal("30000"),
            to_account="Mercado Pago",
            pending_reply=PendingReply.CONTINUES,
        ),
        now=NOW + timedelta(minutes=1),
    )

    [transfer] = _transfers(engine)
    assert transfer["from_account"] == "Galicia pesos"
    assert transfer["to_account"] == "Mercado Pago"
    assert transfer["from_amount"] == Decimal("30000.00")
    [pending] = _rows(engine, "SELECT status, corrected_fields_count FROM pending_transaction")
    assert pending["status"] == "promoted"
    assert pending["corrected_fields_count"] == 1
