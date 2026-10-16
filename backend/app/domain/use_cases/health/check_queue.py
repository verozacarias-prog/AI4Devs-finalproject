from __future__ import annotations

from datetime import timedelta

from app.domain.ports.queue_health_port import QueueHealthPort
from app.shared.clock import Clock


class CheckQueue:
    """Whether the worker keeps up: no pending message has waited longer than allowed.

    The API may be healthy while the worker hangs, so this is checked apart (ADR 0023).
    """

    def __init__(self, queue: QueueHealthPort, clock: Clock, max_wait: timedelta) -> None:
        self._queue = queue
        self._clock = clock
        self._max_wait = max_wait

    def execute(self) -> bool:
        return self._queue.is_keeping_up(self._clock.now() - self._max_wait)
