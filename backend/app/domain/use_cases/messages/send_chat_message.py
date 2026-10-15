from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.entities.inbound_message import (
    InboundMessage,
    InboundStatus,
    Provider,
    web_message_id,
)
from app.domain.errors import ConflictError, ErrorCode, NotFoundError, UnauthenticatedError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


@dataclass(frozen=True)
class SentChatMessage:
    message: InboundMessage
    # False when the browser repeated a message it had already sent: nothing new was stored.
    created: bool


class SendChatMessage:
    """Stores what the user wrote in the web chat, without processing it (ADR 0010).

    The worker takes it later, like a message of WhatsApp. Its time is the one of the server
    clock: the request carries none. The same key sent again by the same user returns the
    message stored the first time, and a quoted message must be a reply of Platita to that user.
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
    ) -> SentChatMessage:
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            if user is None:
                # The user came from a valid session a moment ago, and is no longer there.
                raise UnauthenticatedError
            provider_message_id = web_message_id(user.id, idempotency_key)
            stored = unit_of_work.inbound_messages.find_web(provider_message_id)
            if stored is not None:
                return SentChatMessage(message=stored, created=False)
            if quoted_message_id is not None and not unit_of_work.outbound_messages.exists_for_user(
                quoted_message_id, user.id
            ):
                # A reply to someone else, or no reply at all: told apart nowhere.
                raise NotFoundError(ErrorCode.NOT_FOUND)
            message = InboundMessage(
                id=uuid.uuid4(),
                provider=Provider.WEB,
                provider_message_id=provider_message_id,
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
            try:
                unit_of_work.inbound_messages.add(message)
                unit_of_work.commit()
            except ConflictError:
                # Another request with the same key stored it a moment ago: that one counts.
                # It is read after this block ends, since the rejected write left it unusable.
                taken_meanwhile = True
            else:
                taken_meanwhile = False
        if taken_meanwhile:
            return self._stored_meanwhile(provider_message_id)
        return SentChatMessage(message=message, created=True)

    def _stored_meanwhile(self, provider_message_id: str) -> SentChatMessage:
        with self._unit_of_work as unit_of_work:
            stored = unit_of_work.inbound_messages.find_web(provider_message_id)
        if stored is None:
            # The conflict was not the key of this message: nothing foresees it.
            raise ConflictError(ErrorCode.CONFLICT)
        return SentChatMessage(message=stored, created=False)
