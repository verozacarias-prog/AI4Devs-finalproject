"""The language model through the OpenAI SDK, with no framework (ADR 0020, ADR 0025).

The only place that builds what is sent to the provider (ADR 0013, point 3): the system prompt
is the same for every user, and the data of the task goes delimited in the user message,
without any identifier. The structured output is validated here before the domain sees it.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import httpx2
from openai import APIError, APITimeoutError, OpenAI
from openai.types.responses import (
    EasyInputMessageParam,
    Response,
    ResponseFormatTextJSONSchemaConfigParam,
    ResponseOutputMessage,
    ResponseOutputRefusal,
    ResponseTextConfigParam,
)
from openai.types.shared_params import Reasoning
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.adapters.outbound.llm_client import prompts
from app.constants import (
    DEFAULT_LLM_TIMEOUT_SECONDS,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_REASONING_EFFORT,
    LLM_SDK_RETRIES,
    MESSAGE_CURRENCIES,
)
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    ModelUsage,
    OpenPending,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError, ModelRefusedError

_SCHEMA_NAME = "classification"
_NULLABLE_TEXT = {"type": ["string", "null"]}
_BOOLEAN = {"type": "boolean"}
# How the Responses API says the answer did not finish.
_INCOMPLETE = "incomplete"
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
        "currency_words",
        "transaction_date",
        "proposed_category",
        "several_movements",
        "pending_reply",
        "accepts_proposal",
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
        "currency_words": _NULLABLE_TEXT,
        "transaction_date": {"type": ["string", "null"], "format": "date"},
        "proposed_category": _NULLABLE_TEXT,
        "several_movements": _BOOLEAN,
        "pending_reply": {
            "type": ["string", "null"],
            "enum": [*(value.value for value in PendingReply), None],
        },
        "accepts_proposal": _BOOLEAN,
    },
}


class _ClassificationOutput(BaseModel):
    @field_validator("currency")
    @classmethod
    def _known_currency(cls, value: str | None) -> str | None:
        if value is not None and value not in MESSAGE_CURRENCIES:
            raise ValueError(value)
        return value

    """What the model must answer. Anything else is rejected before reaching the domain."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    message_class: MessageClass
    registration_type: RegistrationType | None
    amount: Decimal | None
    account: str | None
    category: str | None
    # Absent from an answer of an earlier schema, which did not have them.
    currency: str | None = None
    currency_words: str | None = None
    transaction_date: date | None
    proposed_category: str | None = None
    several_movements: bool = False
    pending_reply: PendingReply | None = None
    accepts_proposal: bool = False


class OpenAILLM:
    """Implements LLMPort. A test passes its own HTTP client, so nothing reaches the network."""

    def __init__(
        self,
        api_key: str,
        timeout_seconds: int = DEFAULT_LLM_TIMEOUT_SECONDS,
        http_client: httpx2.Client | None = None,
    ) -> None:
        self._client = OpenAI(
            api_key=api_key,
            http_client=http_client,
            timeout=timeout_seconds,
            max_retries=LLM_SDK_RETRIES,
        )

    def classify(self, request: ClassificationRequest) -> Classification:
        output_format = ResponseFormatTextJSONSchemaConfigParam(
            type="json_schema", name=_SCHEMA_NAME, schema=_CLASSIFICATION_SCHEMA, strict=True
        )
        # The errors of the SDK become those of the domain, which say only how the call ended.
        try:
            response = self._client.responses.create(
                model=LLM_MODEL,
                input=[
                    EasyInputMessageParam(
                        role="system", content=prompts.CLASSIFICATION_SYSTEM_PROMPT
                    ),
                    EasyInputMessageParam(role="user", content=_delimited(request)),
                ],
                reasoning=Reasoning(effort=LLM_REASONING_EFFORT),
                text=ResponseTextConfigParam(format=output_format),
            )
        except APITimeoutError:
            raise ModelCallFailedError(LlmOutcome.TIMEOUT, _NO_TOKENS) from None
        except APIError:
            raise ModelCallFailedError(LlmOutcome.PROVIDER_ERROR, _NO_TOKENS) from None
        if response.status == _INCOMPLETE:
            # The provider cut the answer halfway: the model is down, not refusing (CA-40).
            raise ModelCallFailedError(LlmOutcome.PROVIDER_ERROR, _usage(response))
        if any(
            isinstance(part, ResponseOutputRefusal)
            for item in response.output
            if isinstance(item, ResponseOutputMessage)
            for part in item.content
        ):
            raise ModelRefusedError(_usage(response))
        try:
            output = _ClassificationOutput.model_validate_json(response.output_text, strict=False)
        except ValidationError:
            raise ModelCallFailedError(LlmOutcome.INVALID_OUTPUT, _usage(response)) from None
        return Classification(
            message_class=output.message_class,
            registration_type=output.registration_type,
            amount=output.amount,
            account=output.account,
            category=output.category,
            currency=output.currency,
            currency_words=output.currency_words,
            transaction_date=output.transaction_date,
            proposed_category=output.proposed_category,
            several_movements=output.several_movements,
            pending_reply=output.pending_reply,
            accepts_proposal=output.accepts_proposal,
            usage=_usage(response),
        )


# A call that gave no answer reports no tokens: the row says which model, and leaves them empty.
_NO_TOKENS = ModelUsage(
    provider=LLM_PROVIDER,
    model=LLM_MODEL,
    prompt_version=prompts.CLASSIFICATION_PROMPT_VERSION,
    input_tokens=None,
    output_tokens=None,
)


def _usage(response: Response) -> ModelUsage:
    """What the call cost, as the provider reports it: tokens are None when it does not."""
    usage = response.usage
    return ModelUsage(
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
        prompt_version=prompts.CLASSIFICATION_PROMPT_VERSION,
        input_tokens=usage.input_tokens if usage else None,
        output_tokens=usage.output_tokens if usage else None,
    )


def _delimited(request: ClassificationRequest) -> str:
    """The data of the task, marked as information (ADR 0013, point 9)."""
    data: dict[str, object] = {
        prompts.DATA_KEY_MESSAGE: request.text,
        prompts.DATA_KEY_TODAY: request.today.isoformat(),
        prompts.DATA_KEY_ACCOUNTS: list(request.accounts),
        prompts.DATA_KEY_EXPENSE_CATEGORIES: list(request.expense_categories),
        prompts.DATA_KEY_INCOME_CATEGORIES: list(request.income_categories),
    }
    if request.open_pending is not None:
        data[prompts.DATA_KEY_OPEN_PENDING] = _pending_data(request.open_pending)
    # Escaped as JSON allows, so that a message cannot close the delimiter with "</datos>".
    encoded = json.dumps(data, ensure_ascii=False)
    for character, escaped in prompts.DELIMITER_ESCAPES.items():
        encoded = encoded.replace(character, escaped)
    return f"{prompts.DATA_OPEN}{encoded}{prompts.DATA_CLOSE}"


def _pending_data(pending: OpenPending) -> dict[str, object]:
    """The pending the message may answer: what was understood, what is missing, the question."""
    return {
        prompts.DATA_KEY_INTERPRETED: {
            key: value for key, value in pending.interpreted.items() if value is not None
        },
        prompts.DATA_KEY_MISSING: list(pending.missing),
        prompts.DATA_KEY_QUESTION: pending.question,
    }
