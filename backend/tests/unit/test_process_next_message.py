"""One round of the worker when storing the reply fails (FEAT-002, its spec.md).

Case C2-05: the message and its reply go together or not at all (ADR 0010).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.inbound_message import InboundMessage, InboundStatus, Provider
from app.domain.use_cases.messages.process_next_message import ProcessNextMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork

NOW = datetime(2026, 10, 15, 18, 0, 0, tzinfo=UTC)


class ReplyStoreDown(Exception):
    """What the store of replies raises in this case."""


def test_if_storing_the_reply_fails_the_message_is_not_left_processed() -> None:
    # Case C2-05.
    unit_of_work = InMemoryUnitOfWork()
    unit_of_work.inbound_messages.claimable.append(
        InboundMessage(
            id=uuid.uuid4(),
            provider=Provider.WEB,
            provider_message_id="lucia:key",
            user_id=uuid.uuid4(),
            from_phone="+000000000001",
            text="gasté 3500 en el súper",
            quoted_outbound_message_id=None,
            sent_at=NOW,
            status=InboundStatus.PROCESSING,
            attempts=1,
            locked_until=NOW + timedelta(minutes=2),
            processed_at=None,
        )
    )
    unit_of_work.outbound_messages.failure = ReplyStoreDown()

    with pytest.raises(ReplyStoreDown):
        ProcessNextMessage(unit_of_work, FixedClock(NOW), timedelta(minutes=2)).execute()

    # The only commit is the one that took the message: the round itself left nothing.
    assert unit_of_work.commits == 1
    assert unit_of_work.inbound_messages.marked == []
    assert unit_of_work.outbound_messages.added == []
