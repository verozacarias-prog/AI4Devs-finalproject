from __future__ import annotations

from datetime import timedelta

from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.use_cases.messages.answer_message import AnswerMessage
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from app.shared.clock import Clock


class ProcessNextMessage:
    """One round of the worker: take the next message and answer it (ADR 0010)."""

    def __init__(
        self, unit_of_work: UnitOfWorkPort, clock: Clock, lock_duration: timedelta
    ) -> None:
        self._claim = ClaimNextMessage(unit_of_work, clock, lock_duration)
        self._answer = AnswerMessage(unit_of_work, clock)

    def execute(self) -> bool:
        """True if there was a message to take, so the worker asks again right away."""
        message = self._claim.execute()
        if message is None:
            return False
        self._answer.execute(message)
        return True
