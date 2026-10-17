"""The wrapper of the LLM port that records each call, without its content (ADR 0023).

It implements the same port as the real adapter and goes around it: the entry points always
inject it, so no call skips it. The use cases do not know they are measured.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import replace
from decimal import Decimal

from app.adapters.observability.events import UNREPORTED_USAGE
from app.adapters.observability.logs import message_id_var
from app.constants import (
    LLM_PRICES_USD_PER_MILLION_TOKENS,
    MILLISECONDS_PER_SECOND,
    TOKENS_PER_MILLION,
)
from app.domain.entities.classification import Classification, ClassificationRequest, ModelUsage
from app.domain.entities.llm_call import LlmCall, LlmOutcome, LlmPurpose
from app.domain.errors import ModelCallFailedError, ModelRefusedError
from app.domain.ports.llm_call_log_port import LlmCallLogPort
from app.domain.ports.llm_port import LLMPort

# NUMERIC(12, 6), as the column stores it.
_COST_PRECISION = Decimal("0.000001")


class RecordedLLM:
    """Implements LLMPort. The purpose comes from the method that was called, never a parameter."""

    def __init__(self, llm: LLMPort, calls: LlmCallLogPort) -> None:
        self._llm = llm
        self._calls = calls

    def classify(self, request: ClassificationRequest) -> Classification:
        """A call that fails or that the model refuses is recorded too, with how it ended."""
        started = time.monotonic()
        try:
            classification = self._llm.classify(request)
        except ModelCallFailedError as error:
            self._calls.record(
                _call(LlmPurpose.CLASSIFICATION, error.usage, started, error.outcome)
            )
            raise
        except ModelRefusedError as error:
            self._calls.record(
                _call(LlmPurpose.CLASSIFICATION, error.usage, started, LlmOutcome.BLOCKED)
            )
            raise
        call = _call(LlmPurpose.CLASSIFICATION, classification.usage, started, LlmOutcome.OK)
        self._calls.record(call)
        return replace(classification, call_id=call.id)


def _call(
    purpose: LlmPurpose, usage: ModelUsage | None, started: float, outcome: LlmOutcome
) -> LlmCall:
    elapsed = round((time.monotonic() - started) * MILLISECONDS_PER_SECOND)
    # The message the entry point is processing, if the call was born from one.
    message_id = message_id_var.get()
    return LlmCall(
        id=uuid.uuid4(),
        inbound_message_id=uuid.UUID(message_id) if message_id else None,
        purpose=purpose,
        provider=usage.provider if usage else UNREPORTED_USAGE,
        model=usage.model if usage else UNREPORTED_USAGE,
        prompt_version=usage.prompt_version if usage else None,
        input_tokens=usage.input_tokens if usage else None,
        output_tokens=usage.output_tokens if usage else None,
        duration_ms=elapsed,
        estimated_cost_usd=_cost(usage),
        outcome=outcome,
    )


def _cost(usage: ModelUsage | None) -> Decimal | None:
    """In dollars, with the prices of the model as they are today (ADR 0023, point 8)."""
    if (
        usage is None
        or usage.input_tokens is None
        or usage.output_tokens is None
        or usage.model not in LLM_PRICES_USD_PER_MILLION_TOKENS
    ):
        return None
    input_price, output_price = LLM_PRICES_USD_PER_MILLION_TOKENS[usage.model]
    cost = (
        usage.input_tokens * Decimal(input_price) + usage.output_tokens * Decimal(output_price)
    ) / TOKENS_PER_MILLION
    return cost.quantize(_COST_PRECISION)
