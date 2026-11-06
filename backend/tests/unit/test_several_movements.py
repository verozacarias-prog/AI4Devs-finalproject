"""Several movements in one message, with the model replaced (FEAT-007, its spec.md).

Cases C1-02, C1-05, C1-06 and C1-07: the numbered confirmation of a batch, the date of each
movement, the quota a message with several movements counts, and the adapter that returns
every movement. The database is in memory; the integration tests check the same use case
against PostgreSQL.
"""

from __future__ import annotations

import json
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
    RegistrationType,
)
from app.domain.entities.llm_usage import UsageCounter
from app.domain.entities.transaction import TransactionType
from app.domain.services.transactions.registration_confirmation import (
    batch_confirmation_text,
    confirmation_text,
    transfer_confirmation_text,
)
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import (
    NOW,
    OCTOBER_1,
    OCTOBER_16,
    OCTOBER_17,
    OCTOBER_31,
    Lucia,
)

TWO_EXPENSES = "gasté 3500 en el súper con MP y 1200 de nafta en efectivo"
LUCIAS_OCTOBER = BudgetPeriod(
    id=uuid.uuid4(),
    user_id=uuid.uuid4(),
    family_group_id=None,
    period_type=PeriodType.MONTHLY,
    period_start=OCTOBER_1,
    period_end=OCTOBER_31,
    primary_currency="ARS",
    estimated_income=Decimal("0"),
    status=PeriodStatus.CONFIRMED,
)


def _two_expenses(*, first_date: date | None = None) -> Classification:
    """What the model answers for the two expenses of C1-01 of FEAT-007."""
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=RegistrationType.EXPENSE,
        amount=Decimal("3500"),
        account="MP",
        category="Supermercado",
        transaction_date=first_date,
        more_movements=(
            MovementReading(
                registration_type=RegistrationType.EXPENSE,
                amount=Decimal("1200"),
                account="efectivo",
                category="Transporte",
            ),
        ),
    )


def test_the_confirmation_of_a_batch_lists_each_movement_with_its_number() -> None:
    # Case C1-02.
    first = confirmation_text(
        type=TransactionType.EXPENSE,
        amount=Decimal("3500.00"),
        currency="ARS",
        account_name="Mercado Pago",
        category_name="Supermercado",
        transaction_date=OCTOBER_16,
        period=LUCIAS_OCTOBER,
        position=1,
    )
    second = confirmation_text(
        type=TransactionType.EXPENSE,
        amount=Decimal("1200.00"),
        currency="ARS",
        account_name="Efectivo",
        category_name="Transporte",
        transaction_date=OCTOBER_17,
        period=LUCIAS_OCTOBER,
        position=2,
    )
    transfer = transfer_confirmation_text(
        amount=Decimal("20000.00"),
        currency="ARS",
        from_account_name="Galicia pesos",
        to_account_name="Efectivo",
        transfer_date=OCTOBER_17,
        position=2,
    )

    assert batch_confirmation_text((first, second)).splitlines() == [
        "¡Listo! Anoté 2 movimientos:",
        "",
        "1. Un gasto de $3.500 en Mercado Pago.",
        "Fecha: 16/10/2026",
        "Moneda: ARS",
        "Categoría: Supermercado",
        "Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026",
        "",
        "2. Un gasto de $1.200 en Efectivo.",
        "Fecha: 17/10/2026",
        "Moneda: ARS",
        "Categoría: Transporte",
        "Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026",
    ]
    assert transfer.splitlines() == [
        "2. Una transferencia de $20.000 de Galicia pesos a Efectivo.",
        "No cuenta como gasto.",
        "Fecha: 17/10/2026",
        "Moneda: ARS",
    ]


def test_each_movement_keeps_its_own_date() -> None:
    # Case C1-05.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    llm = FakeLLM(_two_expenses(first_date=OCTOBER_16))

    AnswerMessage(unit_of_work, FixedClock(NOW), llm).execute(
        lucia.message("ayer gasté 3500 en el súper con MP y hoy 1200 de nafta en efectivo")
    )

    dates = {
        transaction.amount: transaction.transaction_date
        for transaction in unit_of_work.transactions.added
    }
    assert dates == {Decimal("3500.00"): OCTOBER_16, Decimal("1200.00"): OCTOBER_17}


def test_a_message_with_several_movements_counts_once_against_the_quota() -> None:
    # Case C1-06.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    registration = (lucia.id, OCTOBER_17, UsageCounter.REGISTRATION)
    cap = (lucia.id, OCTOBER_17, UsageCounter.CLASSIFICATION)
    unit_of_work.llm_usage.counts[registration] = 3
    unit_of_work.llm_usage.counts[cap] = 3

    AnswerMessage(unit_of_work, FixedClock(NOW), FakeLLM(_two_expenses())).execute(
        lucia.message(TWO_EXPENSES, sent_at=NOW - timedelta(seconds=5))
    )

    assert len(unit_of_work.transactions.added) == 2
    assert unit_of_work.llm_usage.counts[registration] == 4
    assert unit_of_work.llm_usage.counts[cap] == 4


class _FakeTransport:
    """Answers with the structured output of a registration with two movements."""

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


def test_the_adapter_returns_every_movement_of_the_message() -> None:
    # Case C1-07.
    transport = _FakeTransport(
        {
            "message_class": "registration",
            "registration_type": "expense",
            "amount": "3500",
            "account": "MP",
            "category": "Supermercado",
            "transaction_date": None,
            "more_movements": [
                {
                    "registration_type": "transfer",
                    "amount": "20000",
                    "account": "Galicia pesos",
                    "account_type": None,
                    "account_type_words": None,
                    "to_account": "efectivo",
                    "to_account_type": None,
                    "to_account_type_words": None,
                    "category": None,
                    "currency": None,
                    "currency_words": None,
                    "transaction_date": None,
                    "proposed_category": None,
                }
            ],
        }
    )
    client = httpx2.Client(transport=httpx2.MockTransport(transport.handle))
    request = ClassificationRequest(
        text="gasté 3500 en el súper con MP y pasé 20000 de Galicia pesos a efectivo",
        accounts=("Galicia pesos", "Mercado Pago", "Efectivo", "Galicia USD"),
        expense_categories=("Supermercado", "Transporte"),
        income_categories=("Sueldo",),
        today=OCTOBER_17,
    )

    classification = OpenAILLM(api_key="test-key", http_client=client).classify(request)

    [first, second] = classification.movements()
    assert first.registration_type is RegistrationType.EXPENSE
    assert first.amount == Decimal("3500")
    assert first.account == "MP"
    assert first.category == "Supermercado"
    assert second.registration_type is RegistrationType.TRANSFER
    assert second.amount == Decimal("20000")
    assert second.account == "Galicia pesos"
    assert second.to_account == "efectivo"
    [sent] = transport.received
    output_format = cast(dict[str, dict[str, object]], sent["text"])["format"]
    schema = cast(dict[str, object], output_format["schema"])
    properties = cast(dict[str, dict[str, object]], schema["properties"])
    assert "more_movements" in cast(list[str], schema["required"])
    assert properties["more_movements"]["type"] == "array"
