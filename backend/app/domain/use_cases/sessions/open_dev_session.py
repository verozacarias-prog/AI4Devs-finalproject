from __future__ import annotations

import uuid
from dataclasses import dataclass

from app import test_data
from app.constants import Environment
from app.domain.entities.session import Session, new_token, open_session
from app.domain.errors import ErrorCode, NotFoundError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


@dataclass(frozen=True)
class OpenedSession:
    # The only moment the token exists outside the cookie: the store keeps its hash.
    token: str
    session: Session


class OpenDevSession:
    """Opens a real session without a login code, for a test user (ADR 0016).

    In the local environment the user is chosen from the list: the one case where the user
    comes from the request. Every refusal is the same "not found", so that the answer tells
    nothing about who exists.
    """

    def __init__(
        self, unit_of_work: UnitOfWorkPort, clock: Clock, environment: Environment
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._environment = environment

    def execute(
        self, *, user_id: uuid.UUID | None = None, access_token: str | None = None
    ) -> OpenedSession:
        # A request that names a user is refused outside local, with or without a link. And a
        # link alone opens nothing yet: no personal link exists until the demo entry arrives.
        if user_id is None or self._environment is not Environment.LOCAL:
            raise NotFoundError(ErrorCode.NOT_FOUND)
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            if user is None or not user.whatsapp_phone.startswith(test_data.TEST_PHONE_PREFIX):
                raise NotFoundError(ErrorCode.NOT_FOUND)
            token = new_token()
            session = open_session(user.id, token, now)
            unit_of_work.sessions.add(session)
            unit_of_work.commit()
        return OpenedSession(token=token, session=session)
