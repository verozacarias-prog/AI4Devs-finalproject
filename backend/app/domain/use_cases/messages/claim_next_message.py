from __future__ import annotations

from datetime import timedelta

from app.domain.entities.inbound_message import InboundMessage
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


class ClaimNextMessage:
    """Takes the next message to process, in a short transaction of its own (ADR 0010).

    One message per sender at a time, in the order they arrived. The message stays in
    process until its lock ends; nothing slow happens inside this transaction.
    """

    def __init__(
        self, unit_of_work: UnitOfWorkPort, clock: Clock, lock_duration: timedelta
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._lock_duration = lock_duration

    def execute(self) -> InboundMessage | None:
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            claimed = unit_of_work.inbound_messages.claim_next(now, now + self._lock_duration)
            unit_of_work.commit()
        return claimed
