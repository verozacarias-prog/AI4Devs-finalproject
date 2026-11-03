from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

from app import test_data
from app.constants import Environment
from app.domain.entities.dev_access_link import DevAccessLink, hash_link_value
from app.domain.entities.session import Session, new_token, open_session
from app.domain.errors import ErrorCode, NotFoundError, TestNoticeRequiredError
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from app.shared.clock import Clock


@dataclass(frozen=True)
class OpenedSession:
    # The only moment the token exists outside the cookie: the store keeps its hash.
    token: str
    session: Session


class OpenDevSession:
    """Opens a real session without a login code, for a test user (ADR 0016).

    In the local environment the user can be chosen from the list: the one case where the user
    comes from the request. A personal link enters its own account, and the first time creates
    it, once the test notice is accepted. Every refusal is the same "not found", so that the
    answer tells nothing about who exists.
    """

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        clock: Clock,
        environment: Environment,
        *,
        server_key: str | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._environment = environment
        self._server_key = server_key

    def execute(
        self,
        *,
        user_id: uuid.UUID | None = None,
        access_token: str | None = None,
        accept_test_notice: str | None = None,
    ) -> OpenedSession:
        if user_id is not None:
            return self._enter_as_chosen_user(user_id)
        if access_token is None:
            raise NotFoundError(ErrorCode.NOT_FOUND)
        return self._enter_with_link(access_token, accept_test_notice)

    def _enter_as_chosen_user(self, user_id: uuid.UUID) -> OpenedSession:
        # A request that names a user is refused outside local, with or without a link.
        if self._environment is not Environment.LOCAL:
            raise NotFoundError(ErrorCode.NOT_FOUND)
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            user = unit_of_work.users.find_by_id(user_id)
            if user is None or not user.whatsapp_phone.startswith(test_data.TEST_PHONE_PREFIX):
                raise NotFoundError(ErrorCode.NOT_FOUND)
            opened = self._open(unit_of_work, user.id, now)
            unit_of_work.commit()
        return opened

    def _enter_with_link(self, value: str, accepted_notice: str | None) -> OpenedSession:
        if self._server_key is None or self._environment is Environment.PRODUCTION:
            raise NotFoundError(ErrorCode.NOT_FOUND)
        token_hash = hash_link_value(value, self._server_key)
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            link = unit_of_work.dev_access_links.lock_by_token_hash(token_hash)
            if link is None:
                raise NotFoundError(ErrorCode.NOT_FOUND)
            user_id = link.user_id
            if user_id is None:
                user_id = self._create_user(unit_of_work, link, accepted_notice)
            opened = self._open(unit_of_work, user_id, now)
            unit_of_work.commit()
        return opened

    def _create_user(
        self, unit_of_work: UnitOfWorkPort, link: DevAccessLink, accepted_notice: str | None
    ) -> uuid.UUID:
        # No consent, no user: the same rule as the real registration (domain rules, § 11).
        if accepted_notice != test_data.TEST_NOTICE_VERSION:
            raise TestNoticeRequiredError(test_data.TEST_NOTICE_VERSION)
        user = CreateTestUser(self._clock).execute(
            unit_of_work,
            name=link.label,
            phone=_invented_phone(),
            terms_version=test_data.TEST_NOTICE_VERSION,
        )
        unit_of_work.dev_access_links.assign_user(link.id, user.id)
        return user.id

    def _open(
        self, unit_of_work: UnitOfWorkPort, user_id: uuid.UUID, now: datetime
    ) -> OpenedSession:
        token = new_token()
        session = open_session(user_id, token, now)
        unit_of_work.sessions.add(session)
        return OpenedSession(token=token, session=session)


def _invented_phone() -> str:
    digits = test_data.TEST_PHONE_DIGITS
    return f"{test_data.TEST_PHONE_PREFIX}{secrets.randbelow(10**digits):0{digits}d}"
