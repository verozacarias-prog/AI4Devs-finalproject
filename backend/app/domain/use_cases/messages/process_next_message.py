from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum

from app.domain.entities.inbound_message import InboundMessage, RetryPolicy
from app.domain.entities.llm_usage import UsageLimits
from app.domain.ports.llm_call_log_port import LlmCallLogPort
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.use_cases.messages.answer_message import (
    AnswerMessage,
    AnswerNotice,
    LimitReached,
    ModelFailed,
)
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from app.shared.clock import Clock


class RoundOutcome(StrEnum):
    """How one round of the worker ended."""

    # Nothing to take: the worker waits before asking again.
    NOTHING_TO_TAKE = "nothing_to_take"
    ANSWERED = "answered"
    # Another worker took the message after this one, and this one wrote nothing (ADR 0010).
    TAKEN_BY_ANOTHER = "taken_by_another"
    # The call to the model failed: the message waits for another attempt, or failed.
    LEFT_FOR_LATER = "left_for_later"
    # A limit of use put it off to the next day of the user without a notice: the one of the
    # cap goes out once a day (domain rules, § 12). With its notice, it was answered.
    PUT_OFF = "put_off"


class ProcessNextMessage:
    """One round of the worker: take the next message and answer it (ADR 0010)."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        clock: Clock,
        lock_duration: timedelta,
        llm: LLMPort,
        retries: RetryPolicy | None = None,
        limits: UsageLimits | None = None,
        calls: LlmCallLogPort | None = None,
    ) -> None:
        self._claim = ClaimNextMessage(unit_of_work, clock, lock_duration)
        self._answer = AnswerMessage(unit_of_work, clock, llm, retries, limits, calls)

    def execute(
        self,
        on_claimed: Callable[[InboundMessage], None] | None = None,
        on_notice: Callable[[AnswerNotice], None] | None = None,
    ) -> RoundOutcome:
        """`on_claimed` learns which message was taken before it is answered, so that whatever
        happens while answering it can be told apart from the other messages. `on_notice`
        learns what the entry point logs besides: a limit reached, or a call that failed.
        """
        message = self._claim.execute()
        if message is None:
            return RoundOutcome.NOTHING_TO_TAKE
        if on_claimed is not None:
            on_claimed(message)
        notices: list[AnswerNotice] = []

        def notify(notice: AnswerNotice) -> None:
            notices.append(notice)
            if on_notice is not None:
                on_notice(notice)

        if not self._answer.execute(message, notify):
            return RoundOutcome.TAKEN_BY_ANOTHER
        if any(isinstance(notice, ModelFailed) for notice in notices):
            return RoundOutcome.LEFT_FOR_LATER
        if any(isinstance(notice, LimitReached) and not notice.answered for notice in notices):
            return RoundOutcome.PUT_OFF
        return RoundOutcome.ANSWERED
