"""Answering a message the worker took, with the model replaced (FEAT-003, its spec.md).

Cases C1-06, C1-07, C1-08 and C1-11: the date of a movement, the names of the account and the
category, and the fixed text of an advice. Cases C1-17 to C1-22: which account the message
names, decided by the code and not by the model. Case C1-24: a movement before the account was
opened. The database is in memory; the integration tests
check the same use case against PostgreSQL.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
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


def _expense(amount: str, account: str, category: str, currency: str | None) -> FakeLLM:
    return FakeLLM(
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal(amount),
            account=account,
            category=category,
            currency=currency,
        )
    )


def test_an_account_the_message_does_not_write_is_not_used() -> None:
    # Case C1-17. The model chose an account the message never wrote.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = _expense("26000", "Galicia pesos", "Impuestos y trámites", None)

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("pagué 26 mil a la muni por transferencia")
    )

    assert unit_of_work.transactions.added == []
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == "Eso todavía no lo sé anotar. Por ahora me manejo con gastos e ingresos."
    assert reply.response_kind is ResponseKind.FIXED_TEXT


def test_half_a_name_without_a_currency_does_not_choose_between_two_accounts() -> None:
    # Case C1-18. "galicia" names Galicia pesos and Galicia USD.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = _expense("2000", "galicia", "Supermercado", None)

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("gasté 2000 en la verdulería con galicia")
    )

    assert unit_of_work.transactions.added == []


def test_half_a_name_with_the_currency_said_chooses_the_account() -> None:
    # Case C1-19.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = _expense("2000", "galicia", "Supermercado", "ARS")

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("gasté 2000 mangos en la verdulería con galicia")
    )

    [transaction] = unit_of_work.transactions.added
    assert transaction.account_id == lucia.accounts["Galicia pesos"]
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text.splitlines()[0] == "¡Listo! Anoté un gasto de $2.000 en Galicia pesos."


def test_the_initials_name_an_account() -> None:
    # Case C1-20.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = _expense("3500", "MP", "Supermercado", None)

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("pagué 3500 en el súper con MP")
    )

    [transaction] = unit_of_work.transactions.added
    assert transaction.account_id == lucia.accounts["Mercado Pago"]


def test_the_type_and_the_currency_name_an_account() -> None:
    # Case C1-21. Galicia pesos is her only bank account in pesos.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = _expense("5000", "el banco", "Supermercado", "ARS")

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("gasté 5 mil pesos en la carnicería con el banco")
    )

    [transaction] = unit_of_work.transactions.added
    assert transaction.account_id == lucia.accounts["Galicia pesos"]


def test_the_type_without_a_currency_does_not_choose_between_two_accounts() -> None:
    # Case C1-22. She has two bank accounts.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = _expense("5000", "el banco", "Supermercado", None)

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("gasté 5 mil en la carnicería con el banco")
    )

    assert unit_of_work.transactions.added == []


def test_an_expense_before_its_account_was_opened_says_why_it_is_not_registered() -> None:
    # Case C1-24. Mercado Pago was opened on 13 October; the expense is of the 12th.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    accounts = unit_of_work.accounts.added
    [wallet] = [account for account in accounts if account.name == "Mercado Pago"]
    accounts[accounts.index(wallet)] = replace(
        wallet, opened_at=datetime(2026, 10, 13, 15, 0, 0, tzinfo=UTC)
    )
    llm = FakeLLM(
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("25000"),
            account="MP",
            category="Transporte",
            currency="ARS",
            transaction_date=date(2026, 10, 12),
        )
    )

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("el lunes cargué nafta, 25 lucas, con MP")
    )

    assert unit_of_work.transactions.added == []
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == (
        "Mercado Pago la tenés cargada desde el 13/10/2026, así que lo que gastaste antes ya está "
        "en el saldo con el que la diste de alta. Lo dejo sin anotar para no contarlo dos veces."
    )
    assert reply.response_kind is ResponseKind.FIXED_TEXT
