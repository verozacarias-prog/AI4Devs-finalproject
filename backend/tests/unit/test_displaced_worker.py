"""A worker another one displaced, with the ports replaced by doubles (FEAT-002, its spec.md).

Case C3-14: the line `message.answered` is left only by the worker that answered (ADR 0010).
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta

from app.adapters.inbound.message_worker.worker import MessageWorker
from app.adapters.observability.logs import configure_logging
from app.domain.entities.inbound_message import InboundMessage, InboundStatus, Provider
from app.domain.use_cases.messages.process_next_message import ProcessNextMessage
from tests.support.doubles import FixedClock, InMemoryUnitOfWork
from tests.support.log_lines import events_of

NOW = datetime(2026, 10, 15, 18, 0, 0, tzinfo=UTC)
LOCK = timedelta(minutes=2)


def test_a_displaced_worker_leaves_no_answered_line() -> None:
    # Case C3-14.
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
            locked_until=NOW + LOCK,
            processed_at=None,
        )
    )
    unit_of_work.inbound_messages.taken_again = True
    stream = io.StringIO()
    configure_logging(stream, "test", "worker")
    worker = MessageWorker(
        lambda: ProcessNextMessage(unit_of_work, FixedClock(NOW), LOCK), in_full=False
    )

    worker.run_round()

    assert unit_of_work.outbound_messages.added == []
    assert events_of(stream, "message.answered") == []
