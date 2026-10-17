"""The language model through the OpenAI SDK, with no framework (ADR 0020, ADR 0025).

The only place that builds what is sent to the provider (ADR 0013, point 3): the system prompt
is the same for every user, and the data of the task goes delimited in the user message,
without any identifier. The structured output is validated here before the domain sees it.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Literal

import httpx2
from openai import OpenAI
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseFormatTextJSONSchemaConfigParam,
    ResponseTextConfigParam,
)
from openai.types.shared_params import Reasoning
from pydantic import BaseModel, ConfigDict

from app.adapters.outbound.llm_client import prompts
from app.constants import (
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_REASONING_EFFORT,
    LLM_SDK_RETRIES,
    LLM_TIMEOUT_SECONDS,
    MESSAGE_CURRENCIES,
)
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    ModelUsage,
    RegistrationType,
)

_SCHEMA_NAME = "classification"
_NULLABLE_TEXT = {"type": ["string", "null"]}
# Strict structured output: every field present, nothing else (ADR 0025).
_CLASSIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message_class",
        "registration_type",
        "amount",
        "account",
        "category",
        "currency",
        "transaction_date",
    ],
    "properties": {
        "message_class": {"type": "string", "enum": [value.value for value in MessageClass]},
        "registration_type": {
            "type": ["string", "null"],
            "enum": [*(value.value for value in RegistrationType), None],
        },
        # Text, so that an amount never goes through float.
        "amount": {"type": ["string", "null"], "pattern": r"^\d+(\.\d{1,2})?$"},
        "account": _NULLABLE_TEXT,
        "category": _NULLABLE_TEXT,
        "currency": {"type": ["string", "null"], "enum": [*MESSAGE_CURRENCIES, None]},
        "transaction_date": {"type": ["string", "null"], "format": "date"},
    },
}


class _ClassificationOutput(BaseModel):
    """What the model must answer. Anything else is rejected before reaching the domain."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    message_class: MessageClass
    registration_type: RegistrationType | None
    amount: Decimal | None
    account: str | None
    category: str | None
    # Absent from an answer of an earlier schema, which said no currency.
    currency: Literal["ARS", "USD"] | None = None
    transaction_date: date | None


class OpenAILLM:
    """Implements LLMPort. A test passes its own HTTP client, so nothing reaches the network."""

    def __init__(self, api_key: str, http_client: httpx2.Client | None = None) -> None:
        self._client = OpenAI(
            api_key=api_key,
            http_client=http_client,
            timeout=LLM_TIMEOUT_SECONDS,
            max_retries=LLM_SDK_RETRIES,
        )

    def classify(self, request: ClassificationRequest) -> Classification:
        output_format = ResponseFormatTextJSONSchemaConfigParam(
            type="json_schema", name=_SCHEMA_NAME, schema=_CLASSIFICATION_SCHEMA, strict=True
        )
        response = self._client.responses.create(
            model=LLM_MODEL,
            input=[
                EasyInputMessageParam(role="system", content=prompts.CLASSIFICATION_SYSTEM_PROMPT),
                EasyInputMessageParam(role="user", content=_delimited(request)),
            ],
            reasoning=Reasoning(effort=LLM_REASONING_EFFORT),
            text=ResponseTextConfigParam(format=output_format),
        )
        output = _ClassificationOutput.model_validate_json(response.output_text, strict=False)
        usage = response.usage
        return Classification(
            message_class=output.message_class,
            registration_type=output.registration_type,
            amount=output.amount,
            account=output.account,
            category=output.category,
            currency=output.currency,
            transaction_date=output.transaction_date,
            usage=ModelUsage(
                provider=LLM_PROVIDER,
                model=LLM_MODEL,
                prompt_version=prompts.CLASSIFICATION_PROMPT_VERSION,
                input_tokens=usage.input_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
            ),
        )


def _delimited(request: ClassificationRequest) -> str:
    """The data of the task, marked as information (ADR 0013, point 9)."""
    data = {
        "mensaje": request.text,
        "dia_en_que_escribio": request.today.isoformat(),
        "cuentas": list(request.accounts),
        "categorias_de_gasto": list(request.expense_categories),
        "categorias_de_ingreso": list(request.income_categories),
    }
    # Escaped as JSON allows, so that a message cannot close the delimiter with "</datos>".
    encoded = json.dumps(data, ensure_ascii=False)
    for character, escaped in prompts.DELIMITER_ESCAPES.items():
        encoded = encoded.replace(character, escaped)
    return f"{prompts.DATA_OPEN}{encoded}{prompts.DATA_CLOSE}"
