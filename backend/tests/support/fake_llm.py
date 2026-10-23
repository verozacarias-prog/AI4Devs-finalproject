"""The model replaced by a double, for the tests of the worker and of answering a message."""

from __future__ import annotations

from dataclasses import replace

from app.domain.entities.classification import (
    Classification,
    ClassificationRequest,
    MessageClass,
    ModelUsage,
)


class FakeLLM:
    """The model, answering every classification with the same interpretation.

    It reports the tokens of a call, as the real adapter does, so the wrapper that records the
    calls has something to write.
    """

    def __init__(
        self,
        classification: Classification | None = None,
        *,
        input_tokens: int = 812,
        output_tokens: int = 64,
        error: Exception | None = None,
    ) -> None:
        self._classification = classification or Classification(MessageClass.NONE)
        # Raised by every call instead of answering: a provider that fails, or a refusal.
        self._error = error
        self._usage = ModelUsage(
            provider="openai",
            model="gpt-5.4-mini",
            prompt_version="test-1",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.requests: list[ClassificationRequest] = []

    def classify(self, request: ClassificationRequest) -> Classification:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return replace(self._classification, usage=self._usage)
