from __future__ import annotations

from datetime import timedelta

from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


class CheckQueue:
    """Whether the worker keeps up: no pending message has waited longer than allowed.

    The API may be healthy while the worker hangs, so this is checked apart (ADR 0023).
    """

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock, max_wait: timedelta) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._max_wait = max_wait

    def execute(self) -> bool:
        since = self._clock.now() - self._max_wait
        with self._unit_of_work as unit_of_work:
            return not unit_of_work.inbound_messages.any_pending_waiting_since(since)
