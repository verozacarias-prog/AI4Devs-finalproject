"""A transfer that lacks something, and how a reply continues it, with the model replaced.

Cases C2-02, C2-03, C2-05 to C2-07, C2-09, C2-10 to C2-15, C3-03, C3-04 and C3-06 of
docs/features/FEAT-006/spec.md. Each case that starts from an open pending gets it the way a
user does: a first message that leaves it pending, and then the reply. The database is in
memory; the integration tests check the same use case against PostgreSQL.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import fields, is_dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.domain.entities.classification import (
    Classification,
    MessageClass,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.outbound_message import ResponseKind
from app.domain.entities.pending_transaction import BatchStatus, PendingIntent, PendingStatus
from app.domain.entities.transfer import Transfer
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, Lucia

DIFFERENT_CURRENCIES = (
    "Todavía no sé anotar una transferencia entre cuentas de distinta moneda. Por ahora, solo "
    "entre cuentas de la misma moneda."
)
WHERE_IT_WENT = "¿A qué cuenta fue? Mercado Pago, Efectivo o Galicia USD."
# The day both accounts are opened in the cases of a date before the opening.
OCTOBER_13_NOON = datetime(2026, 10, 13, 15, 0, 0, tzinfo=UTC)
MONDAY_12 = date(2026, 10, 12)
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _transfer(
    *,
    amount: str | None = "20000",
    account: str | None = None,
    to_account: str | None = None,
    transaction_date: date | None = None,
) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=RegistrationType.TRANSFER,
        amount=None if amount is None else Decimal(amount),
        account=account,
        to_account=to_account,
        transaction_date=transaction_date,
    )


def _reply(
    pending_reply: PendingReply = PendingReply.CONTINUES,
    *,
    amount: str | None = None,
    account: str | None = None,
    to_account: str | None = None,
) -> Classification:
    """What the model answers to a message that comes while a pending awaits a reply."""
    return Classification(
        MessageClass.REGISTRATION,
        amount=None if amount is None else Decimal(amount),
        account=account,
        to_account=to_account,
        pending_reply=pending_reply,
    )


def _answer(
    unit_of_work: InMemoryUnitOfWork,
    lucia: Lucia,
    text: str,
    classification: Classification,
    *,
    now: datetime = NOW,
) -> FakeLLM:
    llm = FakeLLM(classification)
    AnswerMessage(unit_of_work, FixedClock(now), llm).execute(
        lucia.message(text, sent_at=now - timedelta(seconds=5))
    )
    return llm


def _last_reply(unit_of_work: InMemoryUnitOfWork) -> str:
    return unit_of_work.outbound_messages.added[-1].text


def _opened_on_october_13(unit_of_work: InMemoryUnitOfWork, *names: str) -> None:
    accounts = unit_of_work.accounts.added
    for index, account in enumerate(accounts):
        if account.name in names:
            accounts[index] = replace(account, opened_at=OCTOBER_13_NOON)


def _from_galicia_pesos(unit_of_work: InMemoryUnitOfWork, lucia: Lucia) -> None:
    """The pending of C2-01: a transfer of 20000 from Galicia pesos, with no destination."""
    _answer(unit_of_work, lucia, "pasé 20000 de Galicia pesos", _transfer(account="Galicia pesos"))


def _without_amount_nor_origin(unit_of_work: InMemoryUnitOfWork, lucia: Lucia) -> None:
    """The pending of C2-02."""
    _answer(
        unit_of_work,
        lucia,
        "pasé plata a Mercado Pago",
        _transfer(amount=None, to_account="Mercado Pago"),
    )


def _to_la_galicia(unit_of_work: InMemoryUnitOfWork, lucia: Lucia) -> None:
    """The pending of C2-03: "galicia" names Galicia pesos and Galicia USD."""
    _answer(
        unit_of_work,
        lucia,
        "pasé 20000 de Galicia pesos a la galicia",
        _transfer(account="Galicia pesos", to_account="galicia"),
    )


def _strings_in(value: object) -> list[str]:
    """Every text a value holds, however deep, to look for identifiers in it."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.items() for part in item for text in _strings_in(part)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _strings_in(item)]
    if is_dataclass(value) and not isinstance(value, type):
        return [text for field in fields(value) for text in _strings_in(getattr(value, field.name))]
    if isinstance(value, uuid.UUID):
        return [str(value)]
    return []


def test_without_an_amount_and_an_origin_it_asks_both_in_one_message() -> None:
    # Case C2-02.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _without_amount_nor_origin(unit_of_work, lucia)

    assert unit_of_work.transfers.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.intent is PendingIntent.TRANSFER
    assert pending.status is PendingStatus.OPEN
    assert pending.missing_fields == ("amount", "from_account_id")
    assert _last_reply(unit_of_work).splitlines() == [
        "¿Cuánto fue?",
        "¿De qué cuenta salió? Galicia pesos, Efectivo o Galicia USD.",
    ]


def test_a_mention_that_matches_two_does_not_offer_the_account_of_the_other_side() -> None:
    # Case C2-03.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _to_la_galicia(unit_of_work, lucia)

    assert unit_of_work.transfers.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.missing_fields == ("to_account_id",)
    assert _last_reply(unit_of_work) == "¿A qué cuenta fue? Galicia USD."


def test_a_reply_that_completes_half_asks_only_what_is_still_missing() -> None:
    # Case C2-05.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _without_amount_nor_origin(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "fueron 20 lucas",
        _reply(amount="20000"),
        now=NOW + timedelta(minutes=1),
    )

    assert unit_of_work.transfers.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.OPEN
    assert pending.missing_fields == ("from_account_id",)
    assert pending.parsed_data["amount"] == "20000"
    assert _last_reply(unit_of_work) == (
        "¿De qué cuenta salió? Galicia pesos, Efectivo o Galicia USD."
    )


def test_the_model_gets_the_pending_transfer_without_any_identifier() -> None:
    # Case C2-06.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _from_galicia_pesos(unit_of_work, lucia)
    question = _last_reply(unit_of_work)

    llm = _answer(
        unit_of_work,
        lucia,
        "a Mercado Pago",
        _reply(to_account="Mercado Pago"),
        now=NOW + timedelta(minutes=1),
    )

    [request] = llm.requests
    assert request.open_pending is not None
    interpreted = request.open_pending.interpreted
    assert interpreted["type"] == "transfer"
    assert interpreted["amount"] == "20000"
    assert interpreted["account"] == "Galicia pesos"
    assert request.open_pending.missing == ("to_account_id",)
    assert request.open_pending.question == question == WHERE_IT_WENT
    for text in _strings_in(request):
        assert not UUID_PATTERN.search(text), f"{text!r} holds an identifier"
        assert "+000000000001" not in text


def test_the_same_account_on_both_sides_registers_nothing_and_asks_both() -> None:
    # Case C2-07.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _answer(
        unit_of_work,
        lucia,
        "pasé 20000 de Galicia pesos a Galicia pesos",
        _transfer(account="Galicia pesos", to_account="Galicia pesos"),
    )

    assert unit_of_work.transfers.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.missing_fields == ("from_account_id", "to_account_id")
    assert pending.parsed_data.get("account") is None
    assert pending.parsed_data.get("to_account") is None
    assert _last_reply(unit_of_work).splitlines() == [
        "La cuenta de origen y la de destino no pueden ser la misma.",
        "¿De qué cuenta salió? Galicia pesos, Mercado Pago, Efectivo o Galicia USD.",
        "¿A qué cuenta fue? Galicia pesos, Mercado Pago, Efectivo o Galicia USD.",
    ]


def test_choosing_an_account_in_another_currency_in_the_reply_closes_the_pending_with_the_fixed_text() -> (  # noqa: E501
    None
):
    # Case C2-09.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _to_la_galicia(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "a Galicia USD",
        _reply(to_account="Galicia USD"),
        now=NOW + timedelta(minutes=1),
    )

    assert unit_of_work.transfers.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.REJECTED
    [batch] = unit_of_work.pendings.batches
    assert batch.status is BatchStatus.CLOSED
    assert batch.awaiting_reply is False
    reply = unit_of_work.outbound_messages.added[-1]
    assert reply.text == DIFFERENT_CURRENCIES
    assert reply.response_kind is ResponseKind.FIXED_TEXT


def test_a_date_before_both_accounts_were_opened_names_the_origin() -> None:
    # Case C2-10.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _opened_on_october_13(unit_of_work, "Galicia pesos", "Mercado Pago")

    _answer(
        unit_of_work,
        lucia,
        "el lunes pasé 20000 de Galicia pesos a Mercado Pago",
        _transfer(account="Galicia pesos", to_account="Mercado Pago", transaction_date=MONDAY_12),
    )

    assert unit_of_work.transfers.added == []
    assert [p for p in unit_of_work.pendings.added if p.status is PendingStatus.OPEN] == []
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == (
        "Galicia pesos la tenés cargada desde el 13/10/2026, así que lo que transferiste antes "
        "ya está en el saldo con el que la diste de alta. Lo dejo sin anotar para no contarlo "
        "dos veces."
    )
    assert reply.response_kind is ResponseKind.FIXED_TEXT


def test_a_date_before_only_the_destination_was_opened_names_the_destination() -> None:
    # Case C2-11. Galicia pesos was opened on 1 October, before the 12th.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _opened_on_october_13(unit_of_work, "Mercado Pago")

    _answer(
        unit_of_work,
        lucia,
        "el lunes pasé 20000 de Galicia pesos a Mercado Pago",
        _transfer(account="Galicia pesos", to_account="Mercado Pago", transaction_date=MONDAY_12),
    )

    assert unit_of_work.transfers.added == []
    assert [p for p in unit_of_work.pendings.added if p.status is PendingStatus.OPEN] == []
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == (
        "Mercado Pago la tenés cargada desde el 13/10/2026, así que lo que transferiste antes "
        "ya está en el saldo con el que la diste de alta. Lo dejo sin anotar para no contarlo "
        "dos veces."
    )


def test_with_a_pending_transfer_another_movement_is_not_registered_and_the_reply_names_it() -> (
    None
):
    # Case C2-12.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _from_galicia_pesos(unit_of_work, lucia)
    [before] = unit_of_work.pendings.added

    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper con Mercado Pago",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("3500"),
            account="Mercado Pago",
            category="Supermercado",
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        now=NOW + timedelta(minutes=1),
    )

    assert unit_of_work.transfers.added == []
    assert unit_of_work.transactions.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.OPEN
    assert pending.parsed_data == before.parsed_data
    assert pending.missing_fields == before.missing_fields
    assert _last_reply(unit_of_work).splitlines() == [
        "No anoté tu último mensaje: primero terminemos con la transferencia de $20.000 de "
        "Galicia pesos, y después mandámelo de nuevo.",
        WHERE_IT_WENT,
    ]


def test_an_amount_that_does_not_fit_is_asked_again_saying_why() -> None:
    # Case C2-13.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _answer(
        unit_of_work,
        lucia,
        "pasé 1000000000000000000 de Galicia pesos a Mercado Pago",
        _transfer(amount="1000000000000000000", account="Galicia pesos", to_account="Mercado Pago"),
    )

    assert unit_of_work.transfers.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.missing_fields == ("amount",)
    assert _last_reply(unit_of_work).splitlines() == [
        "Ese monto es más grande de lo que puedo registrar.",
        "¿Cuánto fue?",
    ]


def test_a_currency_said_that_is_not_the_one_of_the_accounts_gets_the_fixed_text() -> None:
    # Case C2-14. Both accounts are in pesos, and the message says dollars.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _answer(
        unit_of_work,
        lucia,
        "pasé 100 dólares de Galicia pesos a Mercado Pago",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.TRANSFER,
            amount=Decimal("100"),
            currency="USD",
            currency_words="dólares",
            account="Galicia pesos",
            to_account="Mercado Pago",
        ),
    )

    assert unit_of_work.transfers.added == []
    assert unit_of_work.pendings.added == []
    [reply] = unit_of_work.outbound_messages.added
    assert reply.text == (
        "Todavía no sé anotar una transferencia en otra moneda que la de sus cuentas. Por ahora, "
        "solo en la moneda de las dos cuentas."
    )
    assert reply.response_kind is ResponseKind.FIXED_TEXT


def test_without_accounts_the_amount_of_the_pending_transfer_is_named_in_the_currency_said() -> (
    None
):
    # Case C2-15.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "pasé 100 dólares",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.TRANSFER,
            amount=Decimal("100"),
            currency="USD",
            currency_words="dólares",
        ),
    )

    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper con Mercado Pago",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("3500"),
            account="Mercado Pago",
            category="Supermercado",
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        now=NOW + timedelta(minutes=1),
    )

    assert unit_of_work.transfers.added == []
    assert unit_of_work.transactions.added == []
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.OPEN
    assert _last_reply(unit_of_work).splitlines()[0] == (
        "No anoté tu último mensaje: primero terminemos con la transferencia de US$100, y "
        "después mandámelo de nuevo."
    )


def _accounts_of(unit_of_work: InMemoryUnitOfWork, transfer: Transfer) -> tuple[str, str]:
    """The names of the two accounts of a transfer, from its origin to its destination."""
    names = {account.id: account.name for account in unit_of_work.accounts.added}
    return names[transfer.from_account_id], names[transfer.to_account_id]


def test_changing_both_accounts_adds_a_single_correction() -> None:
    # Case C3-03. Both accounts changed, and they count as one field; the amount was missing.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "pasé plata de Galicia pesos a Mercado Pago",
        _transfer(amount=None, account="Galicia pesos", to_account="Mercado Pago"),
    )

    _answer(
        unit_of_work,
        lucia,
        "fueron 20000, de Efectivo a Galicia pesos",
        _reply(amount="20000", account="Efectivo", to_account="Galicia pesos"),
        now=NOW + timedelta(minutes=1),
    )

    [transfer] = unit_of_work.transfers.added
    assert _accounts_of(unit_of_work, transfer) == ("Efectivo", "Galicia pesos")
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.PROMOTED
    assert pending.corrected_fields_count == 1


def test_choosing_among_the_offered_accounts_adds_no_correction() -> None:
    # Case C3-04. The origin was missing: choosing it among the offered ones completes it.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "pasé 20000 de galicia a Mercado Pago",
        _transfer(account="galicia", to_account="Mercado Pago"),
    )

    _answer(
        unit_of_work,
        lucia,
        "de Galicia pesos",
        _reply(account="Galicia pesos"),
        now=NOW + timedelta(minutes=1),
    )

    [transfer] = unit_of_work.transfers.added
    assert _accounts_of(unit_of_work, transfer) == ("Galicia pesos", "Mercado Pago")
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.PROMOTED
    assert pending.corrected_fields_count == 0


def test_completing_an_amount_that_could_not_be_stored_adds_no_correction() -> None:
    # Case C3-06. The amount does not fit the column, so it was missing, not interpreted.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "pasé 100000000000000000000 de Galicia pesos a Mercado Pago",
        _transfer(
            amount="100000000000000000000", account="Galicia pesos", to_account="Mercado Pago"
        ),
    )

    _answer(
        unit_of_work,
        lucia,
        "fueron 20000",
        _reply(amount="20000"),
        now=NOW + timedelta(minutes=1),
    )

    [transfer] = unit_of_work.transfers.added
    assert transfer.from_amount == Decimal("20000")
    assert _accounts_of(unit_of_work, transfer) == ("Galicia pesos", "Mercado Pago")
    [pending] = unit_of_work.pendings.added
    assert pending.status is PendingStatus.PROMOTED
    assert pending.corrected_fields_count == 0
