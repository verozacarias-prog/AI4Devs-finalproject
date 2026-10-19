"""Registering an expense and an income, against PostgreSQL (FEAT-003, its spec.md).

Cases C1-01, C1-02, C1-05, C1-09, C1-10, C1-12, C1-13, C1-16 and C2-52. The worker runs whole
rounds, the way its process does, with the model replaced by a double: no test reaches the
provider. The double goes inside the wrapper that records each call, as the real adapter does.
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
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.message_worker.worker import create_worker
from app.domain.entities.classification import Classification, MessageClass, RegistrationType
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, status_of, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import (
    NOW,
    OCTOBER_1,
    OCTOBER_17,
    OCTOBER_31,
    SALARY_INCOME,
    SUPERMARKET_EXPENSE,
    salary_income,
    seed_on_october_1,
    supermarket_expense,
)

pytestmark = pytest.mark.integration

# The cookie is Secure, so the client talks to the API over HTTPS, as a browser does.
BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
SENT_AT = NOW - timedelta(seconds=5)
CANNOT_REGISTER = "Eso todavía no lo sé anotar. Por ahora me manejo con gastos e ingresos."
CANNOT_ANSWER = (
    "Todavía no sé responder preguntas. Por ahora anoto gastos e ingresos, y tus saldos los ves "
    "en el dashboard."
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


def _enter_as(client: TestClient, name: str) -> None:
    """Opens a session for that test user; the client keeps its cookie."""
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    found = next(user["id"] for user in users if user["name"] == name)
    response = client.post("/dev/session", json={"user_id": found}, headers=SAME_ORIGIN)
    assert response.status_code == 204


def _transactions(engine: Engine) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT t.id, t.user_id, t.type, t.amount, t.currency, t.source, "
                "t.exchange_rate, t.description, t.transaction_date, a.name AS account, "
                "c.name AS category, c.is_base, p.user_id AS period_user_id, p.period_start, "
                "p.period_end FROM transaction t JOIN account a ON a.id = t.account_id "
                "JOIN category c ON c.id = t.category_id "
                "JOIN budget_period p ON p.id = t.budget_period_id"
            )
        ).all()
    return [dict(row._mapping) for row in rows]


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


def _count(engine: Engine, query: str) -> int:
    with engine.connect() as connection:
        found: int = connection.execute(text(query)).scalar_one()
    return found


def test_an_expense_that_names_the_account_is_registered(
    settings: Settings, engine: Engine
) -> None:
    # Case C1-01.
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    lucia = user_id(engine, "Lucía")

    _run_round(settings, FakeLLM(supermarket_expense()))

    [movement] = _transactions(engine)
    assert movement["user_id"] == lucia
    assert movement["type"] == "expense"
    assert movement["amount"] == Decimal("3500.00")
    assert movement["currency"] == "ARS"
    assert movement["account"] == "Mercado Pago"
    assert movement["category"] == "Supermercado"
    assert movement["is_base"] is True
    assert movement["period_user_id"] == lucia
    assert (movement["period_start"], movement["period_end"]) == (OCTOBER_1, OCTOBER_31)
    assert movement["transaction_date"] == OCTOBER_17
    assert movement["source"] == "manual"
    assert movement["exchange_rate"] is None
    assert movement["description"] is None
    with engine.connect() as connection:
        batches = connection.execute(
            text(
                "SELECT id, user_id, source, status, awaiting_reply, confirmation_message_id "
                "FROM pending_batch"
            )
        ).all()
        pendings = connection.execute(
            text(
                "SELECT batch_id, position, source, status, intent, missing_fields, "
                "resulting_transaction_id FROM pending_transaction"
            )
        ).all()
    [batch] = batches
    assert batch.user_id == lucia
    assert batch.source == "manual"
    assert batch.status == "closed"
    assert batch.awaiting_reply is False
    [pending] = pendings
    assert pending.batch_id == batch.id
    assert pending.position == 1
    assert pending.source == "manual"
    assert pending.status == "promoted"
    assert pending.intent == "transaction"
    assert pending.missing_fields == []
    assert pending.resulting_transaction_id == movement["id"]
    assert status_of(engine, message)[0] == "processed"
    [reply] = _replies_to(engine, message)
    assert reply["response_kind"] == "registration"
    assert batch.confirmation_message_id == reply["id"]


def test_an_income_that_names_the_account_is_registered(settings: Settings, engine: Engine) -> None:
    # Case C1-02.
    message = inbound(engine, "Lucía", SALARY_INCOME, sent_at=SENT_AT)
    lucia = user_id(engine, "Lucía")

    _run_round(settings, FakeLLM(salary_income()))

    [movement] = _transactions(engine)
    assert movement["user_id"] == lucia
    assert movement["type"] == "income"
    assert movement["amount"] == Decimal("850000.00")
    assert movement["currency"] == "ARS"
    assert movement["account"] == "Galicia pesos"
    assert movement["category"] == "Sueldo"
    assert movement["is_base"] is True
    assert movement["period_user_id"] == lucia
    assert (movement["period_start"], movement["period_end"]) == (OCTOBER_1, OCTOBER_31)
    assert movement["transaction_date"] == OCTOBER_17
    [reply] = _replies_to(engine, message)
    assert reply["response_kind"] == "registration"


def test_the_balance_of_the_account_already_includes_the_expense(
    settings: Settings, engine: Engine, client: TestClient
) -> None:
    # Case C1-05.
    inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)
    _run_round(settings, FakeLLM(supermarket_expense()))
    _enter_as(client, "Lucía")

    response = client.get("/accounts")

    assert response.status_code == 200
    accounts = json.loads(response.text, parse_float=Decimal)["accounts"]
    assert {account["name"]: account["balance"] for account in accounts} == {
        "Galicia pesos": Decimal("350000.00"),
        "Mercado Pago": Decimal("76500.00"),
        "Efectivo": Decimal("25000.00"),
        "Galicia USD": Decimal("500.00"),
    }


def test_a_transfer_gets_the_fixed_text_and_registers_nothing(
    settings: Settings, engine: Engine
) -> None:
    # Case C1-09.
    message = inbound(
        engine, "Lucía", "pasé 20000 de Galicia pesos a Mercado Pago", sent_at=SENT_AT
    )
    llm = FakeLLM(
        Classification(MessageClass.REGISTRATION, registration_type=RegistrationType.TRANSFER)
    )

    _run_round(settings, llm)

    assert _count(engine, "SELECT count(*) FROM transaction") == 0
    assert _count(engine, "SELECT count(*) FROM transfer") == 0
    assert len(llm.requests) == 1
    assert status_of(engine, message)[0] == "processed"
    [reply] = _replies_to(engine, message)
    assert reply["text"] == CANNOT_REGISTER
    assert reply["response_kind"] == "fixed_text"


def test_a_query_gets_the_fixed_text(settings: Settings, engine: Engine) -> None:
    # Case C1-10.
    message = inbound(engine, "Lucía", "¿cuánto gasté este mes?", sent_at=SENT_AT)
    llm = FakeLLM(Classification(MessageClass.QUERY))

    _run_round(settings, llm)

    assert len(llm.requests) == 1
    assert status_of(engine, message)[0] == "processed"
    [reply] = _replies_to(engine, message)
    assert reply["text"] == CANNOT_ANSWER
    assert reply["response_kind"] == "fixed_text"


def test_a_greeting_gets_the_request_for_details(settings: Settings, engine: Engine) -> None:
    # Case C1-12.
    message = inbound(engine, "Lucía", "hola", sent_at=SENT_AT)

    _run_round(settings, FakeLLM(Classification(MessageClass.NONE)))

    assert _count(engine, "SELECT count(*) FROM transaction") == 0
    assert _count(engine, "SELECT count(*) FROM pending_transaction") == 0
    assert status_of(engine, message)[0] == "processed"
    [reply] = _replies_to(engine, message)
    assert reply["text"] == (
        "¡Hola! Soy Platita y te ayudo a llevar las cuentas. Contame qué gastaste o qué "
        "cobraste, y con qué cuenta. Por ejemplo: «gasté 3500 en el súper con Mercado Pago»."
    )
    assert reply["response_kind"] == "fixed_text"


def test_the_classification_leaves_its_row_in_llm_call(settings: Settings, engine: Engine) -> None:
    # Case C1-13. 812 × 0.75 / 1,000,000 + 64 × 4.50 / 1,000,000 = 0.000897 dollars.
    message = inbound(engine, "Lucía", SUPERMARKET_EXPENSE, sent_at=SENT_AT)

    _run_round(settings, FakeLLM(supermarket_expense(), input_tokens=812, output_tokens=64))

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT * FROM llm_call")).all()
    [call] = rows
    assert call.inbound_message_id == message
    assert call.purpose == "classification"
    assert call.provider == "openai"
    assert call.model == "gpt-5.4-mini"
    assert call.prompt_version == "test-1"
    assert call.input_tokens == 812
    assert call.output_tokens == 64
    assert call.duration_ms >= 0
    assert call.estimated_cost_usd == Decimal("0.000897")
    assert call.outcome == "ok"
    # The identifiers and the instant are left out: by chance, they could hold those digits.
    stored = " ".join(
        str(value)
        for column, value in call._mapping.items()
        if column not in ("id", "inbound_message_id", "created_at")
    )
    for content in (SUPERMARKET_EXPENSE, "3500", "Mercado Pago", "Supermercado"):
        assert content not in stored, f"{content!r} was stored in llm_call"


def test_write_an_expense_in_the_chat_and_see_the_confirmation(
    settings: Settings, client: TestClient
) -> None:
    # Case C1-16.
    _enter_as(client, "Lucía")
    sent = client.post(
        "/chat/messages",
        json={"text": SUPERMARKET_EXPENSE},
        headers={**SAME_ORIGIN, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert sent.status_code == 202

    _run_round(settings, FakeLLM(supermarket_expense()))
    response = client.get("/chat/messages")

    assert response.status_code == 200
    messages = response.json()["messages"]
    assert [(message["direction"], message["text"]) for message in messages] == [
        ("inbound", SUPERMARKET_EXPENSE),
        (
            "outbound",
            "¡Listo! Anoté un gasto de $3.500 en Mercado Pago.\n"
            "Fecha: 17/10/2026\n"
            "Moneda: ARS\n"
            "Categoría: Supermercado\n"
            "Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026",
        ),
    ]


def test_with_more_than_one_possible_period_the_expense_gets_its_text_and_is_not_pending(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-52. Pablo has his own period and the one of Casa for the same day.
    message = inbound(engine, "Pablo", SUPERMARKET_EXPENSE, sent_at=SENT_AT)

    _run_round(settings, FakeLLM(supermarket_expense()))

    assert _count(engine, "SELECT count(*) FROM transaction") == 0
    assert _count(engine, "SELECT count(*) FROM pending_transaction") == 0
    assert status_of(engine, message)[0] == "processed"
    [reply] = _replies_to(engine, message)
    assert reply["text"] == (
        "Para esa fecha tenés más de un presupuesto, y todavía no sé elegir en cuál anotarlo. "
        "Por ahora no lo anoto."
    )
    assert reply["response_kind"] == "fixed_text"
