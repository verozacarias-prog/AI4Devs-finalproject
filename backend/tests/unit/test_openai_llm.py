"""The OpenAI adapter, with the HTTP transport of the SDK replaced (FEAT-003, its spec.md).

Cases C1-14, C1-15 and C1-23: what the adapter sends, and how it reads the amount and the
currency back. Case C2-32: an answer the provider cut. Case C2-39: a call that fails, recorded.
Case C3-13: the system prompt is the same for every user. Case C3-14: no identifier reaches
the provider.
Outside the spec, T-1: every key of the data is one the system prompt names. T-2: the
provider is asked not to keep the answer.
Nothing here reaches the provider.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date
from decimal import Decimal
from typing import cast

import httpx2
import pytest

from app.adapters.observability.llm_calls import RecordedLLM
from app.adapters.outbound.llm_client import prompts
from app.adapters.outbound.llm_client.openai_llm import OpenAILLM
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    OpenPending,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError, ModelRefusedError
from app.domain.use_cases.messages.answer_message import AnswerMessage
from tests.support.doubles import FixedClock, InMemoryLlmCallLog, InMemoryUnitOfWork
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import NOW, Lucia

ACCOUNTS = ("Galicia pesos", "Mercado Pago", "Efectivo", "Galicia USD")
EXPENSE_CATEGORIES = ("Supermercado", "Transporte", "Comida afuera y delivery")
INCOME_CATEGORIES = ("Sueldo", "Otros ingresos")
TEXT = "gasté 3500 en el súper con Mercado Pago"
REQUEST = ClassificationRequest(
    text=TEXT,
    accounts=ACCOUNTS,
    expense_categories=EXPENSE_CATEGORIES,
    income_categories=INCOME_CATEGORIES,
    today=date(2026, 10, 17),
)


class FakeTransport:
    """Answers every request with the same structured output, and keeps what it received."""

    def __init__(self, output: dict[str, str | None]) -> None:
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


def _adapter(transport: FakeTransport) -> OpenAILLM:
    client = httpx2.Client(transport=httpx2.MockTransport(transport.handle))
    return OpenAILLM(api_key="test-key", http_client=client)


def _expense(amount: str) -> dict[str, str | None]:
    return {
        "message_class": "registration",
        "registration_type": "expense",
        "amount": amount,
        "account": "Mercado Pago",
        "category": "Supermercado",
        "transaction_date": None,
    }


def test_the_adapter_asks_the_configured_model_for_a_structured_output() -> None:
    # Case C1-14.
    transport = FakeTransport(_expense("3500"))

    _adapter(transport).classify(REQUEST)

    [sent] = transport.received
    assert sent["model"] == "gpt-5.4-mini"
    assert sent["reasoning"] == {"effort": "low"}
    output_format = cast(dict[str, dict[str, object]], sent["text"])["format"]
    assert output_format["type"] == "json_schema"
    assert "schema" in output_format
    [system, user] = cast(list[dict[str, str]], sent["input"])
    assert system["role"] == "system"
    assert user["role"] == "user"
    data = user["content"]
    assert data.startswith("<datos>")
    assert data.endswith("</datos>")
    task_data = (TEXT, *ACCOUNTS, *EXPENSE_CATEGORIES, *INCOME_CATEGORIES, "2026-10-17")
    for value in task_data:
        assert value in data, f"{value!r} is missing from the data of the request"
        assert value not in system["content"], f"{value!r} reached the system prompt"


def test_every_key_of_the_data_is_named_in_the_system_prompt() -> None:
    # Task T-1. The prompt explains the data by its keys: a key it does not name means nothing.
    transport = FakeTransport(_expense("3500"))
    pending = OpenPending(
        interpreted={"amount": "3500", "category": "Supermercado"},
        missing=("account_id",),
        question="¿Con qué cuenta lo pagaste?",
    )
    request = dataclasses.replace(REQUEST, open_pending=pending)

    _adapter(transport).classify(request)

    [sent] = transport.received
    [system, user] = cast(list[dict[str, str]], sent["input"])
    data = user["content"].removeprefix("<datos>").removesuffix("</datos>")
    keys = _keys(json.loads(data))
    assert "lo_que_falta" in keys, "the data carried no open pending"
    for key in keys:
        # Quoted, as a name: a key that is also a plain word must not pass by chance.
        assert f'"{key}"' in system["content"], f"{key!r} is not named in the system prompt"


def _keys(data: dict[str, object]) -> set[str]:
    """The keys of the data, nested ones included; those of what was understood are domain names."""
    keys = set(data)
    for key, value in data.items():
        if isinstance(value, dict) and key != "lo_interpretado":
            keys |= _keys(cast(dict[str, object], value))
    return keys


def test_the_adapter_asks_the_provider_not_to_store_the_answer() -> None:
    # Task T-2. Kept by default for 30 days or more, beyond the abuse logs that ADR 0025 accepts.
    transport = FakeTransport(_expense("3500"))

    _adapter(transport).classify(REQUEST)

    [sent] = transport.received
    assert sent.get("store") is False


def test_the_adapter_limits_what_the_model_may_write() -> None:
    # Issue #81, case T-9. The reasoning of the model counts against this limit too.
    transport = FakeTransport(_expense("3500"))

    _adapter(transport).classify(REQUEST)

    [sent] = transport.received
    assert sent.get("max_output_tokens") == 2000


def test_the_adapter_returns_the_amount_as_a_decimal() -> None:
    # Case C1-15.
    transport = FakeTransport(_expense("3500.50"))

    classification = _adapter(transport).classify(REQUEST)

    assert classification.message_class is MessageClass.REGISTRATION
    assert classification.registration_type is RegistrationType.EXPENSE
    assert classification.amount == Decimal("3500.50")
    assert isinstance(classification.amount, Decimal)
    assert not isinstance(classification.amount, float)


def test_the_adapter_returns_the_currency_the_message_says() -> None:
    # Case C1-23.
    transport = FakeTransport({**_expense("2000"), "account": "galicia", "currency": "ARS"})

    classification = _adapter(transport).classify(REQUEST)

    assert classification.account == "galicia"
    assert classification.currency == "ARS"
    [sent] = transport.received
    output_format = cast(dict[str, dict[str, object]], sent["text"])["format"]
    schema = cast(dict[str, object], output_format["schema"])
    assert "currency" in cast(list[str], schema["required"])
    properties = cast(dict[str, dict[str, object]], schema["properties"])
    assert set(cast(list[str | None], properties["currency"]["enum"])) == {"ARS", "USD", None}


def test_a_cut_answer_is_treated_as_a_model_that_is_down() -> None:
    # Case C2-32. The provider stopped the answer halfway: what came is not a refusal.
    def cut(request: httpx2.Request) -> httpx2.Response:
        response = FakeTransport(_expense("3500")).handle(request)
        body = json.loads(response.content)
        body["status"] = "incomplete"
        body["incomplete_details"] = {"reason": "max_output_tokens"}
        body["output"][0]["status"] = "incomplete"
        body["output"][0]["content"][0]["text"] = '{"message_class": "regis'
        return httpx2.Response(200, json=body)

    client = httpx2.Client(transport=httpx2.MockTransport(cut))
    adapter = OpenAILLM(api_key="test-key", http_client=client)

    with pytest.raises(ModelCallFailedError) as error:
        adapter.classify(REQUEST)

    assert error.value.outcome is LlmOutcome.PROVIDER_ERROR
    assert not isinstance(error.value, ModelRefusedError)


def test_a_call_that_fails_records_the_provider_and_the_model() -> None:
    # Case C2-39. The provider answers a 500, inside the wrapper that records each call.
    def down(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, json={"error": {"message": "server error"}})

    client = httpx2.Client(transport=httpx2.MockTransport(down))
    calls = InMemoryLlmCallLog()
    llm = RecordedLLM(OpenAILLM(api_key="test-key", http_client=client), calls)

    with pytest.raises(ModelCallFailedError) as error:
        llm.classify(REQUEST)

    assert error.value.outcome is LlmOutcome.PROVIDER_ERROR
    [call] = calls.recorded
    assert call.provider == "openai"
    assert call.model == "gpt-5.4-mini"
    assert call.prompt_version == prompts.CLASSIFICATION_PROMPT_VERSION
    assert call.outcome is LlmOutcome.PROVIDER_ERROR
    assert call.input_tokens is None
    assert call.output_tokens is None
    assert call.estimated_cost_usd is None


def test_the_system_prompt_is_the_same_for_two_users() -> None:
    # Case C3-13. What tells them apart goes only in the data, delimited.
    transport = FakeTransport(_expense("3500"))
    other = ClassificationRequest(
        text="cobré 120000 de honorarios en el Santander",
        accounts=("Santander", "Ualá"),
        expense_categories=("Gimnasio",),
        income_categories=("Honorarios",),
        today=date(2026, 10, 17),
    )

    _adapter(transport).classify(REQUEST)
    _adapter(transport).classify(other)

    [lucia, someone_else] = [
        cast(list[dict[str, str]], sent["input"]) for sent in transport.received
    ]
    assert lucia[0]["role"] == someone_else[0]["role"] == "system"
    assert lucia[0]["content"] == someone_else[0]["content"]
    for request, (system, data) in ((REQUEST, lucia), (other, someone_else)):
        values = (
            request.text,
            *request.accounts,
            *request.expense_categories,
            *request.income_categories,
        )
        for value in values:
            assert value not in system["content"], f"{value!r} reached the system prompt"
            assert value in data["content"], f"{value!r} is missing from the data"
        assert data["content"].startswith("<datos>")
        assert data["content"].endswith("</datos>")


def test_no_identifier_reaches_the_provider() -> None:
    # Case C3-14. The reply "con MP" of C2-07, to the pending of C2-01, through the use case:
    # the request is built from what is stored, identifiers and all.
    unit_of_work = InMemoryUnitOfWork()
    lucia = Lucia(unit_of_work)
    AnswerMessage(
        unit_of_work,
        FixedClock(NOW),
        FakeLLM(
            Classification(
                MessageClass.REGISTRATION,
                registration_type=RegistrationType.EXPENSE,
                amount=Decimal("3500"),
                category="Supermercado",
            )
        ),
    ).execute(lucia.message("gasté 3500 en el súper"))
    transport = FakeTransport(
        {
            **_expense("3500"),
            "registration_type": None,
            "amount": None,
            "account": "MP",
            "category": None,
            "pending_reply": PendingReply.CONTINUES.value,
        }
    )
    reply = lucia.message("con MP")

    AnswerMessage(unit_of_work, FixedClock(NOW), _adapter(transport)).execute(reply)

    [sent] = transport.received
    body = json.dumps(sent, ensure_ascii=False)
    assert "lo_que_falta" in body, "the request carried no open pending"
    [pending] = unit_of_work.pendings.added
    [batch] = unit_of_work.pendings.batches
    identifiers = (
        lucia.id,
        reply.id,
        pending.id,
        batch.id,
        *lucia.accounts.values(),
        *lucia.categories.values(),
        lucia.period.id,
    )
    for identifier in identifiers:
        assert str(identifier) not in body
        assert identifier.hex not in body
    assert "000000000001" not in body
    assert "Lucía" not in body
