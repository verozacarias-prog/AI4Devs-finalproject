from __future__ import annotations

import uuid

from app.constants import Environment
from app.domain.entities.dev_access_link import DevAccessLink, hash_link_value
from app.domain.entities.session import new_token
from app.domain.errors import (
    ConflictError,
    ErrorCode,
    ForbiddenError,
    NotFoundError,
    PersonalLinkNotAllowedError,
)
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.shared.clock import Clock


def _key_for(environment: Environment, server_key: str | None) -> str:
    # Production first: there the commands do not exist, whatever else is missing.
    if environment is Environment.PRODUCTION:
        raise PersonalLinkNotAllowedError(environment)
    if server_key is None:
        raise ForbiddenError(ErrorCode.SERVER_KEY_MISSING)
    return server_key


class CreatePersonalLink:
    """Creates the link of a label and returns its value, which is never seen again (ADR 0016).

    It creates no user: that happens when the person accepts the test notice.
    """

    def __init__(
        self, unit_of_work: UnitOfWorkPort, environment: Environment, server_key: str | None
    ) -> None:
        self._unit_of_work = unit_of_work
        self._environment = environment
        self._server_key = server_key

    def execute(self, label: str) -> str:
        key = _key_for(self._environment, self._server_key)
        value = new_token()
        with self._unit_of_work as unit_of_work:
            if unit_of_work.dev_access_links.find_by_label(label) is not None:
                raise ConflictError(ErrorCode.PERSONAL_LINK_LABEL_TAKEN)
            unit_of_work.dev_access_links.add(
                DevAccessLink(
                    id=uuid.uuid4(),
                    label=label,
                    user_id=None,
                    token_hash=hash_link_value(value, key),
                )
            )
            unit_of_work.commit()
        return value


class RegeneratePersonalLink:
    """Replaces the link of a label: the old one stops working and its sessions end (ADR 0016)."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        clock: Clock,
        environment: Environment,
        server_key: str | None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._environment = environment
        self._server_key = server_key

    def execute(self, label: str) -> str:
        key = _key_for(self._environment, self._server_key)
        value = new_token()
        now = self._clock.now()
        with self._unit_of_work as unit_of_work:
            link = unit_of_work.dev_access_links.lock_by_label(label)
            if link is None:
                raise NotFoundError(ErrorCode.PERSONAL_LINK_UNKNOWN_LABEL)
            unit_of_work.dev_access_links.replace_token_hash(link.id, hash_link_value(value, key))
            if link.user_id is not None:
                unit_of_work.sessions.revoke_all_of_user(link.user_id, now)
            unit_of_work.commit()
        return value
