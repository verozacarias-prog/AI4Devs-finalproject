"""A message written in the web chat, on the use case alone (FEAT-002, its spec.md).

Case C1-02: the time of the message comes from the clock, because the request carries none.
Case C2-30: two requests at once with the same key answer the message stored first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.inbound_message import InboundMessage, InboundStatus, Provider
from app.domain.use_cases.messages.send_chat_message import SendChatMessage
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from tests.support.doubles import FixedClock, InMemoryUnitOfWork

NOW = datetime(2026, 10, 15, 18, 0, 0, tzinfo=UTC)


def test_the_time_of_the_message_is_the_one_of_the_server_clock() -> None:
    # Case C1-02.
    unit_of_work = InMemoryUnitOfWork()
    lucia = CreateTestUser(FixedClock(NOW)).execute(
        unit_of_work, name="Lucía", phone="+000000000001", terms_version="local-seed-1"
    )

    SendChatMessage(unit_of_work, FixedClock(NOW)).execute(
        user_id=lucia.id,
        text="gasté 3500 en el súper",
        idempotency_key=str(uuid.uuid4()),
    )

    assert len(unit_of_work.inbound_messages.added) == 1
    assert unit_of_work.inbound_messages.added[0].sent_at == datetime(
        2026, 10, 15, 18, 0, 0, tzinfo=UTC
    )


def test_two_requests_at_once_with_the_same_key_answer_the_original_message() -> None:
    # Case C2-30. Another request with the same key stores its message between the search for
    # the key and the write of this one, and the store rejects the second write.
    unit_of_work = InMemoryUnitOfWork()
    lucia = CreateTestUser(FixedClock(NOW)).execute(
        unit_of_work, name="Lucía", phone="+000000000001", terms_version="local-seed-1"
    )
    browser_uuid = str(uuid.uuid4())
    stored_by_the_other = InboundMessage(
        id=uuid.uuid4(),
        provider=Provider.WEB,
        provider_message_id=f"{lucia.id}:{browser_uuid}",
        user_id=lucia.id,
        from_phone="+000000000001",
        text="gasté 3500 en el súper",
        quoted_outbound_message_id=None,
        sent_at=NOW,
        status=InboundStatus.PENDING,
        attempts=0,
        locked_until=None,
        processed_at=None,
    )
    unit_of_work.inbound_messages.stored_meanwhile = stored_by_the_other

    sent = SendChatMessage(unit_of_work, FixedClock(NOW)).execute(
        user_id=lucia.id, text="gasté 3500 en el súper", idempotency_key=browser_uuid
    )

    assert sent.message == stored_by_the_other
    assert sent.created is False
