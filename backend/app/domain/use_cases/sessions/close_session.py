from __future__ import annotations

import uuid

from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.use_cases.sessions.authenticate_session import valid_session
from app.shared.clock import Clock


class CloseSession:
    """Revokes the session of the request, and only that one."""

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, token: str | None) -> uuid.UUID:
        """The user whose session was closed."""
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            session = valid_session(unit_of_work, token, now)
            unit_of_work.sessions.revoke(session.id, now)
            unit_of_work.commit()
        return session.user_id
