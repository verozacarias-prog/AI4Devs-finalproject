from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum

from app.domain.entities.inbound_message import InboundMessage
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.use_cases.messages.answer_message import AnswerMessage
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from app.shared.clock import Clock


class RoundOutcome(StrEnum):
    """How one round of the worker ended."""

    # Nothing to take: the worker waits before asking again.
    NOTHING_TO_TAKE = "nothing_to_take"
    ANSWERED = "answered"
    # Another worker took the message after this one, and this one wrote nothing (ADR 0010).
    TAKEN_BY_ANOTHER = "taken_by_another"


class ProcessNextMessage:
    """One round of the worker: take the next message and answer it (ADR 0010)."""

    def __init__(
        self, unit_of_work: UnitOfWorkPort, clock: Clock, lock_duration: timedelta, llm: LLMPort
    ) -> None:
        self._claim = ClaimNextMessage(unit_of_work, clock, lock_duration)
        self._answer = AnswerMessage(unit_of_work, clock, llm)

    def execute(self, on_claimed: Callable[[InboundMessage], None] | None = None) -> RoundOutcome:
        """`on_claimed` learns which message was taken before it is answered, so that whatever
        happens while answering it can be told apart from the other messages.
        """
        message = self._claim.execute()
        if message is None:
            return RoundOutcome.NOTHING_TO_TAKE
        if on_claimed is not None:
            on_claimed(message)
        if self._answer.execute(message):
            return RoundOutcome.ANSWERED
        return RoundOutcome.TAKEN_BY_ANOTHER
