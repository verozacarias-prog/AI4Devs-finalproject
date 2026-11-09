"""A batch of several pendings, asked and answered by number, with the model replaced (FEAT-007).

Cases C2-03 to C2-09, C2-11 to C2-24 and C2-26 to C2-29 of its spec.md: a general reply, the list
repeated while something is missing, discarding one or all, what cannot be registered yet,
another movement that joins the batch, the limit of 10, a number that is not in the batch, what
the model receives and what the adapter returns, the pendings that expire, and a reply that
brings another movement. Each case that starts from an open batch gets it the way a user does: a
first message that leaves it waiting, and then the reply. The database is in memory; the
integration tests check the same use case against PostgreSQL.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import cast

import httpx2

from app.adapters.outbound.llm_client.openai_llm import OpenAILLM
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    MovementReading,
    NumberedReply,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.pending_transaction import BatchStatus, PendingStatus
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, OCTOBER_16, OCTOBER_17, Lucia

UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
ALL_ACCOUNTS = "¿Con qué cuenta? Galicia pesos, Mercado Pago, Efectivo o Galicia USD."
CANNOT_REGISTER = (
    "eso todavía no lo sé anotar. Por ahora me manejo con gastos, ingresos y transferencias."
)
# The list of C2-01: the expense of the supermarket complete, and the nafta with no account.
LIST_OF_C2_01 = [
    "1. El gasto de $3.500 en Supermercado con Mercado Pago, completo.",
    "",
    "2. El gasto de $1.200 en Transporte.",
    ALL_ACCOUNTS,
]


def _answer(
    unit_of_work: InMemoryUnitOfWork,
    lucia: Lucia,
    text: str,
    classification: Classification,
    *,
    minutes_later: int = 0,
) -> FakeLLM:
    llm = FakeLLM(classification)
    now = NOW + timedelta(minutes=minutes_later)
    AnswerMessage(unit_of_work, FixedClock(now), llm).execute(
        lucia.message(text, sent_at=now - timedelta(seconds=5))
    )
    return llm


def _expense(amount: str | None, account: str | None, category: str | None) -> MovementReading:
    return MovementReading(
        registration_type=RegistrationType.EXPENSE,
        amount=None if amount is None else Decimal(amount),
        account=account,
        category=category,
    )


def _registration(
    first: MovementReading,
    *more: MovementReading,
    pending_reply: PendingReply | None = None,
) -> Classification:
    """A registration with those movements, the first one in the fields of the classification."""
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=first.registration_type,
        amount=first.amount,
        account=first.account,
        category=first.category,
        currency=first.currency,
        currency_words=first.currency_words,
        more_movements=more,
        pending_reply=pending_reply,
    )


def _by_number(*replies: NumberedReply) -> Classification:
    """A reply to the open batch, by number."""
    return Classification(
        MessageClass.REGISTRATION,
        pending_reply=PendingReply.CONTINUES,
        numbered_replies=replies,
    )


def _supermarket_and_nafta(unit_of_work: InMemoryUnitOfWork, lucia: Lucia) -> None:
    """The batch of C2-01: the supermarket with MP, complete, and the nafta with no account."""
    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper con MP y 1200 de nafta",
        _registration(_expense("3500", "MP", "Supermercado"), _expense("1200", None, "Transporte")),
    )


def _last_reply(unit_of_work: InMemoryUnitOfWork) -> str:
    return unit_of_work.outbound_messages.added[-1].text


def _status_by_position(unit_of_work: InMemoryUnitOfWork) -> dict[int, PendingStatus]:
    return {pending.position: pending.status for pending in unit_of_work.pendings.added}


def test_a_general_reply_applies_to_each_pending() -> None:
    # Case C2-03.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper y 1200 de nafta",
        _registration(_expense("3500", None, "Supermercado"), _expense("1200", None, "Transporte")),
    )

    _answer(
        unit_of_work,
        lucia,
        "todos con MP",
        _by_number(
            NumberedReply(number=1, reading=MovementReading(account="MP")),
            NumberedReply(number=2, reading=MovementReading(account="MP")),
        ),
        minutes_later=1,
    )

    transactions = unit_of_work.transactions.added
    assert sorted(transaction.amount for transaction in transactions) == [
        Decimal("1200.00"),
        Decimal("3500.00"),
    ]
    assert {transaction.account_id for transaction in transactions} == {
        lucia.accounts["Mercado Pago"]
    }
    assert _last_reply(unit_of_work).splitlines()[0] == "¡Listo! Anoté 2 movimientos:"


def test_while_something_is_missing_the_list_is_repeated_up_to_date() -> None:
    # Case C2-04.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper y la nafta con efectivo",
        _registration(
            _expense("3500", None, "Supermercado"), _expense(None, "Efectivo", "Transporte")
        ),
    )

    _answer(
        unit_of_work,
        lucia,
        "el 1 con MP",
        _by_number(NumberedReply(number=1, reading=MovementReading(account="MP"))),
        minutes_later=1,
    )

    assert unit_of_work.transactions.added == []
    first = next(pending for pending in unit_of_work.pendings.added if pending.position == 1)
    assert first.status is PendingStatus.OPEN
    assert first.missing_fields == ()
    assert first.parsed_data["account"] == "Mercado Pago"
    assert _last_reply(unit_of_work).splitlines() == [
        "1. El gasto de $3.500 en Supermercado con Mercado Pago, completo.",
        "",
        "2. El gasto en Transporte con Efectivo.",
        "¿Cuánto fue?",
    ]


def test_discarding_one_by_number_registers_the_others() -> None:
    # Case C2-05.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "el 2 no lo anotes",
        _by_number(NumberedReply(number=2, discards=True)),
        minutes_later=1,
    )

    assert _status_by_position(unit_of_work) == {
        1: PendingStatus.PROMOTED,
        2: PendingStatus.REJECTED,
    }
    [transaction] = unit_of_work.transactions.added
    assert transaction.amount == Decimal("3500.00")
    assert transaction.account_id == lucia.accounts["Mercado Pago"]
    [batch] = unit_of_work.pendings.batches
    assert batch.status is BatchStatus.CLOSED
    assert _last_reply(unit_of_work).splitlines()[0] == (
        "¡Listo! Anoté un gasto de $3.500 en Mercado Pago."
    )


def test_discarding_all_closes_the_batch_with_nothing_registered() -> None:
    # Case C2-06.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "no anotes ninguno",
        Classification(MessageClass.REGISTRATION, pending_reply=PendingReply.DISCARDS),
        minutes_later=1,
    )

    assert unit_of_work.transactions.added == []
    assert _status_by_position(unit_of_work) == {
        1: PendingStatus.REJECTED,
        2: PendingStatus.REJECTED,
    }
    [batch] = unit_of_work.pendings.batches
    assert batch.status is BatchStatus.CLOSED
    assert batch.awaiting_reply is False
    assert _last_reply(unit_of_work) == "Listo, no anoto ninguno."


def test_a_movement_that_cannot_be_registered_yet_is_named_apart() -> None:
    # Case C2-07.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper con MP y compré una heladera en 6 cuotas con la Visa",
        _registration(
            _expense("3500", "MP", "Supermercado"),
            MovementReading(registration_type=RegistrationType.CARD_PURCHASE),
        ),
    )

    [transaction] = unit_of_work.transactions.added
    assert transaction.amount == Decimal("3500.00")
    [pending] = unit_of_work.pendings.added
    assert pending.position == 1
    assert pending.status is PendingStatus.PROMOTED
    lines = _last_reply(unit_of_work).splitlines()
    assert lines[0] == "¡Listo! Anoté un gasto de $3.500 en Mercado Pago."
    assert lines[-2:] == ["", "El segundo movimiento no lo anoté: " + CANNOT_REGISTER]


def test_when_none_can_be_registered_nothing_is_left_pending() -> None:
    # Case C2-08.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)

    _answer(
        unit_of_work,
        lucia,
        "compré una heladera en 6 cuotas y pago el alquiler todos los meses",
        _registration(
            MovementReading(registration_type=RegistrationType.CARD_PURCHASE),
            MovementReading(registration_type=RegistrationType.RECURRING_RULE),
        ),
    )

    assert unit_of_work.transactions.added == []
    assert unit_of_work.pendings.batches == []
    assert unit_of_work.pendings.added == []
    assert _last_reply(unit_of_work).splitlines() == [
        "El primer movimiento no lo anoté: " + CANNOT_REGISTER,
        "El segundo movimiento no lo anoté: " + CANNOT_REGISTER,
    ]


def test_a_reply_that_leaves_a_pending_unregistrable_takes_it_out_of_the_batch() -> None:
    # Case C2-09. Galicia USD is in dollars, and the period of October in pesos.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "el 2 con la Galicia USD",
        _by_number(NumberedReply(number=2, reading=MovementReading(account="Galicia USD"))),
        minutes_later=1,
    )

    assert _status_by_position(unit_of_work) == {
        1: PendingStatus.PROMOTED,
        2: PendingStatus.REJECTED,
    }
    [transaction] = unit_of_work.transactions.added
    assert transaction.account_id == lucia.accounts["Mercado Pago"]
    lines = _last_reply(unit_of_work).splitlines()
    assert lines[0] == "¡Listo! Anoté un gasto de $3.500 en Mercado Pago."
    assert lines[-2:] == ["", "El 2 no lo anoté: " + CANNOT_REGISTER]


def test_with_a_pending_transfer_another_movement_joins_and_the_list_names_it_in_its_currency() -> (
    None
):
    # Case C2-11.
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
        _registration(
            _expense("3500", "Mercado Pago", "Supermercado"),
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        minutes_later=1,
    )

    assert unit_of_work.transfers.added == []
    assert unit_of_work.transactions.added == []
    assert _status_by_position(unit_of_work) == {1: PendingStatus.OPEN, 2: PendingStatus.OPEN}
    lines = _last_reply(unit_of_work).splitlines()
    assert lines[0] == "1. La transferencia de US$100."
    assert lines[-1] == "2. El gasto de $3.500 en Supermercado con Mercado Pago, completo."


def test_of_a_message_with_more_than_10_the_first_10_go_in() -> None:
    # Case C2-12.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    twelve = [_expense(str(100 * number), "MP", "Supermercado") for number in range(1, 13)]

    _answer(unit_of_work, lucia, "doce gastos con MP", _registration(*twelve))

    amounts = sorted(transaction.amount for transaction in unit_of_work.transactions.added)
    assert amounts == [Decimal(100 * number).quantize(Decimal("0.01")) for number in range(1, 11)]
    assert sorted(pending.position for pending in unit_of_work.pendings.added) == list(range(1, 11))
    [batch] = unit_of_work.pendings.batches
    assert batch.status is BatchStatus.CLOSED
    assert _last_reply(unit_of_work).splitlines()[-2:] == [
        "",
        "Tomé solo los primeros 10 movimientos. Los otros 2 mandámelos en otro mensaje.",
    ]


def test_a_batch_with_9_adds_only_one_of_the_two_that_come() -> None:
    # Case C2-13. The first of the nine has no account, so the batch waits.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    nine = [
        _expense(str(100 * number), None if number == 1 else "MP", "Supermercado")
        for number in range(1, 10)
    ]
    _answer(unit_of_work, lucia, "nueve gastos", _registration(*nine))

    _answer(
        unit_of_work,
        lucia,
        "y 1000 de nafta y 1100 de colectivo en efectivo",
        _registration(
            _expense("1000", "Efectivo", "Transporte"),
            _expense("1100", "Efectivo", "Transporte"),
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        minutes_later=1,
    )

    assert unit_of_work.transactions.added == []
    positions = sorted(pending.position for pending in unit_of_work.pendings.added)
    assert positions == list(range(1, 11))
    tenth = next(pending for pending in unit_of_work.pendings.added if pending.position == 10)
    assert Decimal(str(tenth.parsed_data["amount"])) == Decimal("1000")
    assert _last_reply(unit_of_work).splitlines()[-2:] == [
        "",
        "Tomé solo el primero de los movimientos nuevos. El otro mandámelo cuando terminemos "
        "con estos.",
    ]


def test_a_reply_to_a_number_that_is_not_in_the_batch_changes_nothing() -> None:
    # Case C2-14.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta(unit_of_work, lucia)
    before = list(unit_of_work.pendings.added)

    _answer(
        unit_of_work,
        lucia,
        "el 5 con MP",
        _by_number(NumberedReply(number=5, reading=MovementReading(account="MP"))),
        minutes_later=1,
    )

    assert unit_of_work.transactions.added == []
    assert [
        (pending.status, pending.parsed_data, pending.missing_fields)
        for pending in unit_of_work.pendings.added
    ] == [(pending.status, pending.parsed_data, pending.missing_fields) for pending in before]
    assert _last_reply(unit_of_work).splitlines() == LIST_OF_C2_01


def test_the_model_receives_each_pending_of_the_batch_with_its_number() -> None:
    # Case C2-15.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta(unit_of_work, lucia)

    llm = _answer(
        unit_of_work,
        lucia,
        "el 2 en efectivo",
        _by_number(NumberedReply(number=2, reading=MovementReading(account="efectivo"))),
        minutes_later=1,
    )

    [request] = llm.requests
    assert request.open_batch is not None
    first, second = request.open_batch.pendings
    assert (first.number, first.missing) == (1, ())
    assert Decimal(str(first.interpreted["amount"])) == Decimal("3500")
    assert (second.number, second.missing) == (2, ("account_id",))
    assert second.interpreted["category"] == "Transporte"
    assert request.open_batch.question.splitlines() == LIST_OF_C2_01
    assert UUID_PATTERN.search(repr(request)) is None


class _FakeTransport:
    """Answers with one structured output, and keeps what it received."""

    def __init__(self, output: dict[str, object]) -> None:
        self._output = output
        self.received: list[dict[str, object]] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.received.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 0,
                "model": "gpt-5.4-mini",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(self._output),
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 812,
                    "output_tokens": 64,
                    "total_tokens": 876,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": [],
            },
        )


def _numbered(number: int, *, discards: bool, account: str | None) -> dict[str, object]:
    return {
        "number": number,
        "discards": discards,
        "registration_type": None,
        "amount": None,
        "account": account,
        "account_type": None,
        "account_type_words": None,
        "to_account": None,
        "to_account_type": None,
        "to_account_type_words": None,
        "category": None,
        "currency": None,
        "currency_words": None,
        "transaction_date": None,
        "proposed_category": None,
    }


def test_the_adapter_returns_the_replies_by_number() -> None:
    # Case C2-16.
    transport = _FakeTransport(
        {
            "message_class": "registration",
            "registration_type": None,
            "amount": None,
            "account": None,
            "category": None,
            "transaction_date": None,
            "pending_reply": "continues",
            "numbered_replies": [
                _numbered(2, discards=False, account="efectivo"),
                _numbered(1, discards=True, account=None),
            ],
        }
    )
    client = httpx2.Client(transport=httpx2.MockTransport(transport.handle))
    request = ClassificationRequest(
        text="el 2 en efectivo y el 1 no lo anotes",
        accounts=("Galicia pesos", "Mercado Pago", "Efectivo", "Galicia USD"),
        expense_categories=("Supermercado", "Transporte"),
        income_categories=("Sueldo",),
        today=OCTOBER_17,
    )

    classification = OpenAILLM(api_key="test-key", http_client=client).classify(request)

    second, first = classification.numbered_replies
    assert second.number == 2
    assert second.discards is False
    assert second.reading.account == "efectivo"
    assert first.number == 1
    assert first.discards is True
    [sent] = transport.received
    output_format = cast(dict[str, dict[str, object]], sent["text"])["format"]
    schema = cast(dict[str, object], output_format["schema"])
    properties = cast(dict[str, dict[str, object]], schema["properties"])
    assert "numbered_replies" in cast(list[str], schema["required"])
    assert properties["numbered_replies"]["type"] == "array"


# Minutes from the first message of a batch: the second one joins 8 hours later, and the reply
# comes 26 hours after the first, when only the first pending expired.
JOINED_LATER = 8 * 60
EXPIRED_FIRST = 26 * 60
EXPIRED = "El 1 no lo anoté: pasaron más de 24 horas."


def _supermarket_and_nafta_joined_later(
    unit_of_work: InMemoryUnitOfWork, lucia: Lucia, nafta_account: str | None
) -> None:
    """The supermarket with no account, and 8 hours later the nafta, which joins the batch."""
    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper",
        _registration(_expense("3500", None, "Supermercado")),
    )
    _answer(
        unit_of_work,
        lucia,
        "y 1200 de nafta" if nafta_account is None else "y 1200 de nafta en efectivo",
        _registration(
            _expense("1200", nafta_account, "Transporte"),
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        minutes_later=JOINED_LATER,
    )


def test_an_expired_pending_leaves_the_batch_and_the_reply_names_it() -> None:
    # Case C2-17.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta_joined_later(unit_of_work, lucia, "Efectivo")

    _answer(
        unit_of_work,
        lucia,
        "el 1 con MP",
        _by_number(NumberedReply(number=1, reading=MovementReading(account="MP"))),
        minutes_later=EXPIRED_FIRST,
    )

    assert _status_by_position(unit_of_work) == {
        1: PendingStatus.EXPIRED,
        2: PendingStatus.PROMOTED,
    }
    [transaction] = unit_of_work.transactions.added
    assert transaction.amount == Decimal("1200.00")
    assert transaction.account_id == lucia.accounts["Efectivo"]
    [batch] = unit_of_work.pendings.batches
    assert batch.status is BatchStatus.CLOSED
    lines = _last_reply(unit_of_work).splitlines()
    assert lines[0] == "¡Listo! Anoté un gasto de $1.200 en Efectivo."
    assert lines[-2:] == ["", EXPIRED]


def test_the_model_receives_only_the_pendings_still_valid() -> None:
    # Case C2-18.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta_joined_later(unit_of_work, lucia, None)

    llm = _answer(
        unit_of_work,
        lucia,
        "el 1 con MP",
        _by_number(NumberedReply(number=1, reading=MovementReading(account="MP"))),
        minutes_later=EXPIRED_FIRST,
    )

    [request] = llm.requests
    assert request.open_batch is not None
    assert [pending.number for pending in request.open_batch.pendings] == [2]
    assert unit_of_work.transactions.added == []
    assert _status_by_position(unit_of_work) == {
        1: PendingStatus.EXPIRED,
        2: PendingStatus.OPEN,
    }
    assert _last_reply(unit_of_work).splitlines() == [
        "2. El gasto de $1.200 en Transporte.",
        ALL_ACCOUNTS,
        "",
        EXPIRED,
    ]


def test_when_all_expired_the_batch_closes_and_the_message_is_a_new_one() -> None:
    # Case C2-19.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _answer(
        unit_of_work,
        lucia,
        "gasté 3500 en el súper y 1200 de nafta",
        _registration(_expense("3500", None, "Supermercado"), _expense("1200", None, "Transporte")),
    )

    llm = _answer(
        unit_of_work,
        lucia,
        "gasté 500 en el súper con MP",
        _registration(_expense("500", "MP", "Supermercado")),
        minutes_later=EXPIRED_FIRST,
    )

    [request] = llm.requests
    assert request.open_batch is None
    old, new = unit_of_work.pendings.batches
    assert old.status is BatchStatus.CLOSED
    assert old.awaiting_reply is False
    expired = [pending for pending in unit_of_work.pendings.added if pending.batch_id == old.id]
    assert [pending.status for pending in expired] == [PendingStatus.EXPIRED] * 2
    assert new.status is BatchStatus.CLOSED
    [transaction] = unit_of_work.transactions.added
    assert transaction.amount == Decimal("500.00")
    reply = _last_reply(unit_of_work)
    assert reply.splitlines()[0] == "¡Listo! Anoté un gasto de $500 en Mercado Pago."
    assert "24 horas" not in reply


def test_what_cannot_be_registered_takes_no_place_of_the_10() -> None:
    # Case C2-21. The first of the nine has no account, so the batch waits.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    nine = [
        _expense(str(100 * number), None if number == 1 else "mp", "Supermercado")
        for number in range(1, 10)
    ]
    _answer(unit_of_work, lucia, "nueve gastos con mp", _registration(*nine))

    _answer(
        unit_of_work,
        lucia,
        "compré una heladera en cuotas y 500 de café con MP",
        _registration(
            MovementReading(registration_type=RegistrationType.CARD_PURCHASE),
            _expense("500", "MP", "Supermercado"),
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        minutes_later=1,
    )

    tenth = next(pending for pending in unit_of_work.pendings.added if pending.position == 10)
    assert Decimal(str(tenth.parsed_data["amount"])) == Decimal("500")
    reply = _last_reply(unit_of_work)
    assert "10. El gasto de $500 en Supermercado con Mercado Pago, completo." in reply
    assert "Tomé solo" not in reply
    assert reply.splitlines()[-2:] == ["", "El primer movimiento no lo anoté: " + CANNOT_REGISTER]


def test_a_batch_that_used_its_10_numbers_says_so_though_it_shows_fewer() -> None:
    # Case C2-22.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    ten = [_expense(str(100 * number), None, "Supermercado") for number in range(1, 11)]
    _answer(unit_of_work, lucia, "diez gastos", _registration(*ten))
    _answer(
        unit_of_work,
        lucia,
        "del 4 al 10 no los anotes",
        _by_number(*(NumberedReply(number=number, discards=True) for number in range(4, 11))),
        minutes_later=1,
    )

    _answer(
        unit_of_work,
        lucia,
        "y 500 de café con MP",
        _registration(
            _expense("500", "MP", "Supermercado"), pending_reply=PendingReply.OTHER_MOVEMENT
        ),
        minutes_later=2,
    )

    assert len(unit_of_work.pendings.added) == 10
    lines = _last_reply(unit_of_work).splitlines()
    numbered = [line.split(".")[0] for line in lines if line[:1].isdigit()]
    assert numbered == ["1", "2", "3"]
    assert lines[-1] == (
        "Esta lista ya usó sus 10 números, así que no tomé los nuevos: mandámelos cuando "
        "terminemos con estos."
    )


def test_a_reply_by_number_and_a_new_movement_in_the_same_message() -> None:
    # Case C2-23.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    lucia.add_base_category("Comida afuera y delivery")
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "el 2 con efectivo, y además 500 de café con MP",
        Classification(
            MessageClass.REGISTRATION,
            pending_reply=PendingReply.CONTINUES,
            numbered_replies=(
                NumberedReply(number=2, reading=MovementReading(account="efectivo")),
            ),
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("500"),
            account="MP",
            category="Comida afuera y delivery",
        ),
        minutes_later=1,
    )

    assert sorted(transaction.amount for transaction in unit_of_work.transactions.added) == [
        Decimal("1200.00"),
        Decimal("3500.00"),
    ]
    assert sorted(pending.position for pending in unit_of_work.pendings.added) == [1, 2]
    reply = _last_reply(unit_of_work)
    assert reply.startswith("¡Listo! Anoté 2 movimientos:")
    assert reply.splitlines()[-1] == "El movimiento nuevo mandámelo en otro mensaje."


def test_a_single_new_movement_that_cannot_be_registered_is_named_without_an_ordinal() -> None:
    # Case C2-24.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "compré una heladera en cuotas",
        _registration(
            MovementReading(registration_type=RegistrationType.CARD_PURCHASE),
            pending_reply=PendingReply.OTHER_MOVEMENT,
        ),
        minutes_later=1,
    )

    assert _status_by_position(unit_of_work) == {1: PendingStatus.OPEN, 2: PendingStatus.OPEN}
    assert _last_reply(unit_of_work).splitlines() == [
        *LIST_OF_C2_01,
        "",
        "Ese movimiento no lo anoté: " + CANNOT_REGISTER,
    ]


def test_a_pending_that_can_no_longer_be_registered_when_another_joins_is_rejected() -> None:
    # Case C2-20. Yesterday is covered by both periods, and today only by the one of October.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    supermarket = _registration(_expense("3500", None, "Supermercado"))
    _answer(
        unit_of_work,
        lucia,
        "ayer gasté 3500 en el súper",
        Classification(
            MessageClass.REGISTRATION,
            registration_type=supermarket.registration_type,
            amount=supermarket.amount,
            category=supermarket.category,
            transaction_date=OCTOBER_16,
        ),
    )
    unit_of_work.budget_periods.add(
        BudgetPeriod(
            id=uuid.uuid4(),
            user_id=lucia.id,
            family_group_id=None,
            period_type=PeriodType.MONTHLY,
            period_start=date(2026, 9, 15),
            period_end=OCTOBER_16,
            primary_currency="ARS",
            estimated_income=Decimal("0"),
            status=PeriodStatus.CONFIRMED,
        )
    )

    _answer(
        unit_of_work,
        lucia,
        "y 1200 de nafta con MP",
        _registration(
            _expense("1200", "MP", "Transporte"), pending_reply=PendingReply.OTHER_MOVEMENT
        ),
        minutes_later=1,
    )

    [transaction] = unit_of_work.transactions.added
    assert transaction.amount == Decimal("1200.00")
    assert transaction.account_id == lucia.accounts["Mercado Pago"]
    assert _status_by_position(unit_of_work) == {
        1: PendingStatus.REJECTED,
        2: PendingStatus.PROMOTED,
    }
    [batch] = unit_of_work.pendings.batches
    assert batch.status is BatchStatus.CLOSED
    assert _last_reply(unit_of_work).splitlines()[-1] == (
        "El 1 no lo anoté: para esa fecha tenés más de un presupuesto, y todavía no sé elegir en "
        "cuál anotarlo. Por ahora no lo anoto."
    )


def _discarded_with_a_coffee(unit_of_work: InMemoryUnitOfWork) -> None:
    """Nothing registered, the batch closed, and the coffee asked for in another message."""
    assert unit_of_work.transactions.added == []
    assert _status_by_position(unit_of_work) == {
        1: PendingStatus.REJECTED,
        2: PendingStatus.REJECTED,
    }
    [batch] = unit_of_work.pendings.batches
    assert batch.status is BatchStatus.CLOSED
    assert _last_reply(unit_of_work) == (
        "Listo, no anoto ninguno.\n\nEl movimiento nuevo mandámelo en otro mensaje."
    )


def test_discarding_all_by_number_with_a_new_movement_confirms_and_warns() -> None:
    # Case C2-26.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    lucia.add_base_category("Comida afuera y delivery")
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "el 1 y el 2 no, y anotá 500 de café con MP",
        Classification(
            MessageClass.REGISTRATION,
            pending_reply=PendingReply.CONTINUES,
            numbered_replies=(
                NumberedReply(number=1, reading=MovementReading(), discards=True),
                NumberedReply(number=2, reading=MovementReading(), discards=True),
            ),
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("500"),
            account="MP",
            category="Comida afuera y delivery",
        ),
        minutes_later=1,
    )

    _discarded_with_a_coffee(unit_of_work)


def test_discarding_the_whole_batch_with_a_new_movement_warns() -> None:
    # Case C2-27.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    lucia.add_base_category("Comida afuera y delivery")
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "no anotes ninguno, anotá solo 500 de café con MP",
        Classification(
            MessageClass.REGISTRATION,
            pending_reply=PendingReply.DISCARDS,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("500"),
            account="MP",
            category="Comida afuera y delivery",
        ),
        minutes_later=1,
    )

    _discarded_with_a_coffee(unit_of_work)


def test_discarding_a_lone_pending_with_a_new_movement_answers_as_a_lone_pending() -> None:
    # Case C2-28.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    lucia.add_base_category("Comida afuera y delivery")
    _answer(
        unit_of_work,
        lucia,
        "gasté 1200 de nafta",
        _registration(_expense("1200", None, "Transporte")),
    )

    _answer(
        unit_of_work,
        lucia,
        "no lo anotes, y anotá 500 de café con MP",
        Classification(
            MessageClass.REGISTRATION,
            pending_reply=PendingReply.DISCARDS,
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("500"),
            account="MP",
            category="Comida afuera y delivery",
        ),
        minutes_later=1,
    )

    assert unit_of_work.transactions.added == []
    assert _status_by_position(unit_of_work) == {1: PendingStatus.REJECTED}
    assert _last_reply(unit_of_work) == (
        "Listo, no lo anoto.\n\nEl movimiento nuevo mandámelo en otro mensaje."
    )


def test_a_reply_that_brings_two_new_movements_warns_in_plural() -> None:
    # Case C2-29.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    lucia.add_base_category("Comida afuera y delivery")
    _supermarket_and_nafta(unit_of_work, lucia)

    _answer(
        unit_of_work,
        lucia,
        "el 2 con efectivo, y además 500 de café y 800 del diario con MP",
        Classification(
            MessageClass.REGISTRATION,
            pending_reply=PendingReply.CONTINUES,
            numbered_replies=(
                NumberedReply(number=2, reading=MovementReading(account="efectivo")),
            ),
            registration_type=RegistrationType.EXPENSE,
            amount=Decimal("500"),
            account="MP",
            category="Comida afuera y delivery",
            more_movements=(_expense("800", "MP", "Comida afuera y delivery"),),
        ),
        minutes_later=1,
    )

    assert sorted(transaction.amount for transaction in unit_of_work.transactions.added) == [
        Decimal("1200.00"),
        Decimal("3500.00"),
    ]
    assert _last_reply(unit_of_work).splitlines()[-1] == (
        "Los movimientos nuevos mandámelos en otro mensaje."
    )
