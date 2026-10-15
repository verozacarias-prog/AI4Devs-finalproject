from __future__ import annotations

import uuid

from app.domain.entities.inbound_message import (
    InboundMessage,
    InboundStatus,
    Provider,
    web_message_id,
)
from app.domain.errors import UnauthenticatedError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


class SendChatMessage:
    """Stores what the user wrote in the web chat, without processing it (ADR 0010).

    The worker takes it later, like a message of WhatsApp. Its time is the one of the server
    clock: the request carries none.
    """

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(
        self,
        user_id: uuid.UUID,
        text: str,
        idempotency_key: str,
        quoted_message_id: uuid.UUID | None = None,
    ) -> InboundMessage:
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            if user is None:
                # The user came from a valid session a moment ago, and is no longer there.
                raise UnauthenticatedError
            message = InboundMessage(
                id=uuid.uuid4(),
                provider=Provider.WEB,
                provider_message_id=web_message_id(user.id, idempotency_key),
                user_id=user.id,
                from_phone=user.whatsapp_phone,
                text=text,
                quoted_outbound_message_id=quoted_message_id,
                sent_at=self._clock.now(),
                status=InboundStatus.PENDING,
                attempts=0,
                locked_until=None,
                processed_at=None,
            )
            unit_of_work.inbound_messages.add(message)
            unit_of_work.commit()
        return message
