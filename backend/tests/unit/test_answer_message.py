"""Answering a message the worker took, with the model replaced (FEAT-003, its spec.md).

Cases C1-06, C1-07, C1-08 and C1-11: the date of a movement, the names of the account and the
category, and the fixed text of an advice. The database is in memory; the integration tests
check the same use case against PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.domain.entities.classification import Classification, MessageClass, RegistrationType
from app.domain.entities.outbound_message import ResponseKind
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import (
    NOW,
    OCTOBER_16,
    SUPERMARKET_EXPENSE,
    Lucia,
    supermarket_expense,
)


def test_the_date_is_the_day_she_wrote_not_the_day_it_is_processed() -> None:
    # Case C1-06. At 02:30 UTC it is still the 16th, at 23:30, in Buenos Aires.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = FakeLLM(supermarket_expense())
    message = lucia.message(
        SUPERMARKET_EXPENSE, sent_at=datetime(2026, 10, 17, 2, 30, 0, tzinfo=UTC)
    )

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(message)

    [transaction] = unit_of_work.transactions.added
    assert transaction.transaction_date == OCTOBER_16
    [request] = llm.requests
    assert request.today == OCTOBER_16


def test_a_date_the_message_gives_is_kept() -> None:
    # Case C1-07.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = FakeLLM(
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("1200"),
            account="Efectivo",
            category="Transporte",
            transaction_date=OCTOBER_16,
        )
    )

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("ayer gasté 1200 de nafta con Efectivo")
    )

    [transaction] = unit_of_work.transactions.added
    assert transaction.transaction_date == OCTOBER_16
    [reply] = unit_of_work.outbound_messages.added
    assert "Fecha: 16/10/2026" in reply.text.splitlines()


def test_the_account_and_the_category_are_recognized_whatever_their_case() -> None:
    # Case C1-08.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = FakeLLM(supermarket_expense(account="mercado pago", category="SUPERMERCADO"))

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(lucia.message(SUPERMARKET_EXPENSE))

    [transaction] = unit_of_work.transactions.added
    assert transaction.account_id == lucia.accounts["Mercado Pago"]
    assert transaction.category_id == lucia.categories["Supermercado"]
    [reply] = unit_of_work.outbound_messages.added
    lines = reply.text.splitlines()
    assert lines[0] == "¡Listo! Anoté un gasto de $3.500 en Mercado Pago."
    assert "Categoría: Supermercado" in lines


def test_an_advice_gets_the_fixed_text() -> None:
    # Case C1-11.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = FakeLLM(Classification(MessageClass.ADVICE))

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("¿me conviene sacar un préstamo?")
    )

    assert len(llm.requests) == 1
    assert unit_of_work.transactions.added == []
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == (
        "Todavía no sé responder preguntas. Por ahora anoto gastos e ingresos, y tus saldos "
        "los ves en el dashboard."
    )
    assert reply.response_kind is ResponseKind.FIXED_TEXT
