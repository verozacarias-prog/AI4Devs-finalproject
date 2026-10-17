"""The OpenAI adapter, with the HTTP transport of the SDK replaced (FEAT-003, its spec.md).

Cases C1-14, C1-15 and C1-23: what the adapter sends, and how it reads the amount and the
currency back. Case C2-32: an answer the provider cut. Case C2-39: a call that fails, recorded.
Nothing here reaches the provider.
"""

from __future__ import annotations

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
    ClassificationRequest,
    MessageClass,
    RegistrationType,
)
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError, ModelRefusedError
from tests.support.doubles import InMemoryLlmCallLog

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
