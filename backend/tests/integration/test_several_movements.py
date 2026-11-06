"""Several movements in one message, against PostgreSQL (FEAT-007, its spec.md).

Cases C1-01, C1-03 and C1-04: two expenses registered in one batch, an expense and a transfer
in the same message, and what the period spent. The worker runs whole rounds, the way its
process does, with the model replaced by a double: no test reaches the provider.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, Row, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.message_worker.worker import create_worker
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    MovementReading,
    RegistrationType,
)
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, status_of, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, OCTOBER_1, OCTOBER_17, seed_on_october_1

pytestmark = pytest.mark.integration

BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
SENT_AT = NOW - timedelta(seconds=5)
TWO_EXPENSES = "gasté 3500 en el súper con MP y 1200 de nafta en efectivo"
EXPENSE_AND_TRANSFER = "gasté 3500 en el súper con MP y pasé 20000 de Galicia pesos a efectivo"


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


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings, log_stream=io.StringIO(), clock=FixedClock(NOW))
    return TestClient(app, base_url=BASE_URL)


def _run_round(settings: Settings, llm: FakeLLM) -> None:
    create_worker(settings, FixedClock(NOW), log_stream=io.StringIO(), llm=llm).run_round()


def _supermarket_by_mp(*more: MovementReading) -> FakeLLM:
    """The expense of 3500 in Supermercado with "MP", followed by the movements given."""
    return FakeLLM(
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("3500"),
            account="MP",
            category="Supermercado",
            more_movements=more,
        )
    )


NAFTA_IN_CASH = MovementReading(
    registration_type=RegistrationType.EXPENSE,
    amount=Decimal("1200"),
    account="efectivo",
    category="Transporte",
)
TRANSFER_TO_CASH = MovementReading(
    registration_type=RegistrationType.TRANSFER,
    amount=Decimal("20000"),
    account="Galicia pesos",
    to_account="efectivo",
)


def _transactions(engine: Engine) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT t.id, t.user_id, t.type, t.amount, t.currency, t.source, "
                "t.transaction_date, a.name AS account, c.name AS category, "
                "p.period_start FROM transaction t JOIN account a ON a.id = t.account_id "
                "JOIN category c ON c.id = t.category_id "
                "JOIN budget_period p ON p.id = t.budget_period_id ORDER BY t.amount DESC"
            )
        ).all()
    return [dict(row._mapping) for row in rows]


def _transfers(engine: Engine) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT t.id, t.from_amount, t.from_currency, f.name AS from_account, "
                "d.name AS to_account FROM transfer t "
                "JOIN account f ON f.id = t.from_account_id "
                "JOIN account d ON d.id = t.to_account_id"
            )
        ).all()
    return [dict(row._mapping) for row in rows]


def _batches_and_pendings(engine: Engine) -> tuple[list[Row[tuple[object, ...]]], ...]:
    with engine.connect() as connection:
        batches = connection.execute(
            text(
                "SELECT id, user_id, source, status, awaiting_reply, confirmation_message_id "
                "FROM pending_batch"
            )
        ).all()
        pendings = connection.execute(
            text(
                "SELECT batch_id, position, status, intent, missing_fields, "
                "resulting_transaction_id, resulting_transfer_id FROM pending_transaction "
                "ORDER BY position"
            )
        ).all()
    return list(batches), list(pendings)


def _replies_to(engine: Engine, message: uuid.UUID) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, content FROM outbound_message WHERE inbound_message_id = :id"),
            {"id": message},
        ).all()
    replies = []
    for row in rows:
        content = row.content if isinstance(row.content, dict) else json.loads(row.content)
        replies.append({"id": row.id, **content})
    return replies


def test_two_complete_expenses_in_one_message_are_registered_in_one_batch(
    settings: Settings, engine: Engine
) -> None:
    # Case C1-01.
    message = inbound(engine, "Lucía", TWO_EXPENSES, sent_at=SENT_AT)
    lucia = user_id(engine, "Lucía")

    _run_round(settings, _supermarket_by_mp(NAFTA_IN_CASH))

    supermarket, nafta = _transactions(engine)
    for transaction in (supermarket, nafta):
        assert transaction["user_id"] == lucia
        assert transaction["type"] == "expense"
        assert transaction["source"] == "manual"
        assert transaction["transaction_date"] == OCTOBER_17
        assert transaction["currency"] == "ARS"
        assert transaction["period_start"] == OCTOBER_1
    assert supermarket["amount"] == Decimal("3500.00")
    assert supermarket["account"] == "Mercado Pago"
    assert supermarket["category"] == "Supermercado"
    assert nafta["amount"] == Decimal("1200.00")
    assert nafta["account"] == "Efectivo"
    assert nafta["category"] == "Transporte"
    [batch], pendings = _batches_and_pendings(engine)
    assert batch.user_id == lucia
    assert batch.source == "manual"
    assert batch.status == "closed"
    assert batch.awaiting_reply is False
    first, second = pendings
    for pending in (first, second):
        assert pending.batch_id == batch.id
        assert pending.status == "promoted"
        assert pending.missing_fields == []
    assert first.position == 1
    assert first.resulting_transaction_id == supermarket["id"]
    assert second.position == 2
    assert second.resulting_transaction_id == nafta["id"]
    assert status_of(engine, message)[0] == "processed"
    [reply] = _replies_to(engine, message)
    assert reply["response_kind"] == "registration"
    assert batch.confirmation_message_id == reply["id"]


def test_an_expense_and_a_transfer_in_one_message_are_registered(
    settings: Settings, engine: Engine
) -> None:
    # Case C1-03.
    message = inbound(engine, "Lucía", EXPENSE_AND_TRANSFER, sent_at=SENT_AT)

    _run_round(settings, _supermarket_by_mp(TRANSFER_TO_CASH))

    [expense] = _transactions(engine)
    assert expense["amount"] == Decimal("3500.00")
    assert expense["account"] == "Mercado Pago"
    [transfer] = _transfers(engine)
    assert transfer["from_amount"] == Decimal("20000.00")
    assert transfer["from_currency"] == "ARS"
    assert transfer["from_account"] == "Galicia pesos"
    assert transfer["to_account"] == "Efectivo"
    [batch], (first, second) = _batches_and_pendings(engine)
    assert batch.status == "closed"
    assert (first.position, first.status, first.intent) == (1, "promoted", "transaction")
    assert first.resulting_transaction_id == expense["id"]
    assert (second.position, second.status, second.intent) == (2, "promoted", "transfer")
    assert second.resulting_transfer_id == transfer["id"]
    [reply] = _replies_to(engine, message)
    assert batch.confirmation_message_id == reply["id"]


def test_what_the_period_spent_adds_both_expenses(
    settings: Settings, engine: Engine, client: TestClient
) -> None:
    # Case C1-04.
    inbound(engine, "Lucía", TWO_EXPENSES, sent_at=SENT_AT)
    _run_round(settings, _supermarket_by_mp(NAFTA_IN_CASH))
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    lucia = next(user["id"] for user in users if user["name"] == "Lucía")
    entered = client.post("/dev/session", json={"user_id": lucia}, headers=SAME_ORIGIN)
    assert entered.status_code == 204
    with engine.connect() as connection:
        period = connection.execute(
            text("SELECT id FROM budget_period WHERE user_id = :user"),
            {"user": user_id(engine, "Lucía")},
        ).scalar_one()

    response = client.get(f"/budget-periods/{period}/summary")

    assert response.status_code == 200
    summary = json.loads(response.text, parse_float=Decimal)
    assert summary["total_spent"] == Decimal("4700.00")
