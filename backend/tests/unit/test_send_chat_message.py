"""A message written in the web chat, on the use case alone (FEAT-002, its spec.md).

Case C1-02: the time of the message comes from the clock, because the request carries none.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.use_cases.create_test_user import CreateTestUser
from app.domain.use_cases.send_chat_message import SendChatMessage
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
        idempotency_key="9d2b7c1e-5a4f-4c3b-8e21-7f6a5b4c3d2e",
    )

    assert len(unit_of_work.inbound_messages.added) == 1
    assert unit_of_work.inbound_messages.added[0].sent_at == datetime(
        2026, 10, 15, 18, 0, 0, tzinfo=UTC
    )
