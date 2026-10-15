from __future__ import annotations

from datetime import timedelta

from app import messages
from app.domain.entities.outbound_message import ResponseKind, reply_to
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from app.shared.clock import Clock


class ProcessNextMessage:
    """One round of the worker: take the next message and answer it (ADR 0010).

    Until there is a model, the answer is a fixed text (FEAT-002). The message is marked
    processed and its reply is stored in one transaction, or neither happens.
    """

    def __init__(
        self, unit_of_work: UnitOfWorkPort, clock: Clock, lock_duration: timedelta
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._claim = ClaimNextMessage(unit_of_work, clock, lock_duration)

    def execute(self) -> bool:
        """True if there was a message to take, so the worker asks again right away."""
        message = self._claim.execute()
        if message is None:
            return False
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            # First, so that a worker another one displaced writes nothing at all.
            if not unit_of_work.inbound_messages.mark_processed(message.id, message.attempts, now):
                return True
            unit_of_work.outbound_messages.add(
                reply_to(
                    message.id,
                    message.provider,
                    message.user_id,
                    message.from_phone,
                    messages.FIXED_REPLY,
                    ResponseKind.FIXED_TEXT,
                    now,
                )
            )
            unit_of_work.commit()
        return True
