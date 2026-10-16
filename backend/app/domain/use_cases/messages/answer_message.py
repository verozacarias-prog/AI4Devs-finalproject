from __future__ import annotations

from app import messages
from app.domain.entities.inbound_message import InboundMessage
from app.domain.entities.outbound_message import ResponseKind, reply_to
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


class AnswerMessage:
    """Answers a message a worker took (ADR 0010).

    Until there is a model, the answer is a fixed text (FEAT-002). The message is marked
    processed and its reply is stored in one transaction, or neither happens. If another worker
    took the message after this one, nothing is written: the attempts are the fencing token.
    """

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, message: InboundMessage) -> bool:
        """True if this worker answered it; False if another one took it after this one."""
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            # First, so that a worker another one displaced writes nothing at all.
            if not unit_of_work.inbound_messages.mark_processed(message.id, message.attempts, now):
                return False
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
