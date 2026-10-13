from __future__ import annotations

from datetime import datetime

from app.domain.entities.session import Session, hash_token
from app.domain.entities.user import User
from app.domain.errors import UnauthenticatedError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


def valid_session(unit_of_work: UnitOfWorkPort, token: str | None, now: datetime) -> Session:
    """The session of that token, if it is still valid. Every other case is the same error."""
    if not token:
        raise UnauthenticatedError
    session = unit_of_work.sessions.find_by_token_hash(hash_token(token))
    if session is None or not session.is_valid_at(now):
        raise UnauthenticatedError
    return session


class AuthenticateSession:
    """Says who is behind a request, from the token of its cookie, and counts the activity.

    The periodic read of the web chat must not count as activity (ADR 0016): it will validate
    the session without going through here.
    """

    def __init__(self, unit_of_work: UnitOfWorkPort, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, token: str | None) -> User:
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            session = valid_session(unit_of_work, token, now)
            user = unit_of_work.users.find_by_id(session.user_id)
            if user is None:
                raise UnauthenticatedError
            unit_of_work.sessions.touch(session.id, now)
            unit_of_work.commit()
        return user
