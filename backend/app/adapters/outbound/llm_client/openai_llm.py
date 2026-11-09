"""The language model through the OpenAI SDK, with no framework (ADR 0020, ADR 0025).

The only place that builds what is sent to the provider (ADR 0013, point 3): the system prompt
is the same for every user, and the data of the task goes delimited in the user message,
without any identifier. The structured output is validated here before the domain sees it.
"""

from __future__ import annotations

import json
import re
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
    CURRENCY_CODE_PATTERN,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_REASONING_EFFORT,
    LLM_SDK_RETRIES,
)
from app.domain.entities.account import AccountType
from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    ModelUsage,
    MovementReading,
    NumberedReply,
    OpenBatch,
    PendingReply,
    RegistrationType,
)
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelCallFailedError, ModelRefusedError

_SCHEMA_NAME = "classification"
_NULLABLE_TEXT = {"type": ["string", "null"]}
_BOOLEAN = {"type": "boolean"}
# Only a type of the catalog of ACCOUNT.type, or none.
_ACCOUNT_TYPE = {
    "type": ["string", "null"],
    "enum": [*(value.value for value in AccountType), None],
}
# How the Responses API says the answer did not finish.
_INCOMPLETE = "incomplete"
# The fields of one movement: those of the first one, at the top, and of each one after it.
_MOVEMENT_PROPERTIES: dict[str, object] = {
    "registration_type": {
        "type": ["string", "null"],
        "enum": [*(value.value for value in RegistrationType), None],
    },
    # Text, so that an amount never goes through float.
    "amount": {"type": ["string", "null"], "pattern": r"^\d+(\.\d{1,2})?$"},
    "account": _NULLABLE_TEXT,
    "account_type": _ACCOUNT_TYPE,
    "account_type_words": _NULLABLE_TEXT,
    "to_account": _NULLABLE_TEXT,
    "to_account_type": _ACCOUNT_TYPE,
    "to_account_type_words": _NULLABLE_TEXT,
    "category": _NULLABLE_TEXT,
    "currency": {"type": ["string", "null"], "pattern": CURRENCY_CODE_PATTERN},
    "currency_words": _NULLABLE_TEXT,
    "transaction_date": {"type": ["string", "null"], "format": "date"},
    "proposed_category": _NULLABLE_TEXT,
}
# Each movement after the first, in the order the message writes them (FEAT-007).
_MORE_MOVEMENTS = {
    "type": "array",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": list(_MOVEMENT_PROPERTIES),
        "properties": _MOVEMENT_PROPERTIES,
    },
}
# What a reply says of each pending of the open batch, by its number (FEAT-007, CA-9).
_NUMBERED_REPLY_PROPERTIES: dict[str, object] = {
    "number": {"type": "integer"},
    "discards": _BOOLEAN,
    "accepts_proposal": _BOOLEAN,
    **_MOVEMENT_PROPERTIES,
}
_NUMBERED_REPLIES = {
    "type": "array",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": list(_NUMBERED_REPLY_PROPERTIES),
        "properties": _NUMBERED_REPLY_PROPERTIES,
    },
}
# Strict structured output: every field present, nothing else (ADR 0025).
_CLASSIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message_class",
        "registration_type",
        "amount",
        "account",
        "account_type",
        "account_type_words",
        "to_account",
        "to_account_type",
        "to_account_type_words",
        "category",
        "currency",
        "currency_words",
        "transaction_date",
        "proposed_category",
        "more_movements",
        "pending_reply",
        "numbered_replies",
    ],
    "properties": {
        "message_class": {"type": "string", "enum": [value.value for value in MessageClass]},
        **_MOVEMENT_PROPERTIES,
        "more_movements": _MORE_MOVEMENTS,
        "pending_reply": {
            "type": ["string", "null"],
            "enum": [*(value.value for value in PendingReply), None],
        },
        "numbered_replies": _NUMBERED_REPLIES,
    },
}


class _MovementOutput(BaseModel):
    """One movement after the first, as the model must answer it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    registration_type: RegistrationType | None
    amount: Decimal | None
    account: str | None
    account_type: AccountType | None
    account_type_words: str | None
    to_account: str | None
    to_account_type: AccountType | None
    to_account_type_words: str | None
    category: str | None
    currency: str | None
    currency_words: str | None
    transaction_date: date | None
    proposed_category: str | None

    @field_validator("currency")
    @classmethod
    def _known_currency(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(CURRENCY_CODE_PATTERN, value) is None:
            raise ValueError(value)
        return value

    def reading(self) -> MovementReading:
        return MovementReading(
            registration_type=self.registration_type,
            amount=self.amount,
            account=self.account,
            account_type=self.account_type,
            account_type_words=self.account_type_words,
            to_account=self.to_account,
            to_account_type=self.to_account_type,
            to_account_type_words=self.to_account_type_words,
            category=self.category,
            currency=self.currency,
            currency_words=self.currency_words,
            transaction_date=self.transaction_date,
            proposed_category=self.proposed_category,
        )


class _NumberedReplyOutput(_MovementOutput):
    """What a reply says of one pending of the open batch, as the model must answer it."""

    number: int
    discards: bool
    accepts_proposal: bool = False

    def numbered_reply(self) -> NumberedReply:
        return NumberedReply(
            number=self.number,
            reading=self.reading(),
            discards=self.discards,
            accepts_proposal=self.accepts_proposal,
        )


class _ClassificationOutput(BaseModel):
    @field_validator("currency")
    @classmethod
    def _known_currency(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(CURRENCY_CODE_PATTERN, value) is None:
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
    account_type: AccountType | None = None
    account_type_words: str | None = None
    to_account: str | None = None
    to_account_type: AccountType | None = None
    to_account_type_words: str | None = None
    currency: str | None = None
    currency_words: str | None = None
    transaction_date: date | None
    proposed_category: str | None = None
    more_movements: tuple[_MovementOutput, ...] = ()
    pending_reply: PendingReply | None = None
    numbered_replies: tuple[_NumberedReplyOutput, ...] = ()


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
                max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
                text=ResponseTextConfigParam(format=output_format),
                # Nothing chains answers: the provider keeps only its abuse logs (ADR 0025).
                store=False,
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
            account_type=output.account_type,
            account_type_words=output.account_type_words,
            to_account=output.to_account,
            to_account_type=output.to_account_type,
            to_account_type_words=output.to_account_type_words,
            category=output.category,
            currency=output.currency,
            currency_words=output.currency_words,
            transaction_date=output.transaction_date,
            proposed_category=output.proposed_category,
            more_movements=tuple(movement.reading() for movement in output.more_movements),
            pending_reply=output.pending_reply,
            numbered_replies=tuple(reply.numbered_reply() for reply in output.numbered_replies),
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
    if request.open_batch is not None:
        data[prompts.DATA_KEY_OPEN_BATCH] = _batch_data(request.open_batch)
    # Escaped as JSON allows, so that a message cannot close the delimiter with "</datos>".
    encoded = json.dumps(data, ensure_ascii=False)
    for character, escaped in prompts.DELIMITER_ESCAPES.items():
        encoded = encoded.replace(character, escaped)
    return f"{prompts.DATA_OPEN}{encoded}{prompts.DATA_CLOSE}"


def _batch_data(batch: OpenBatch) -> dict[str, object]:
    """The batch the message may answer: each pending with its number, what was understood and
    what is missing, and the question.
    """
    return {
        prompts.DATA_KEY_PENDINGS: [
            {
                prompts.DATA_KEY_NUMBER: pending.number,
                prompts.DATA_KEY_INTERPRETED: {
                    key: value for key, value in pending.interpreted.items() if value is not None
                },
                prompts.DATA_KEY_MISSING: list(pending.missing),
            }
            for pending in batch.pendings
        ],
        prompts.DATA_KEY_QUESTION: batch.question,
    }
