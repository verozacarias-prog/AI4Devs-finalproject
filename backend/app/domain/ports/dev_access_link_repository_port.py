from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.dev_access_link import DevAccessLink


class DevAccessLinkRepositoryPort(Protocol):
    def add(self, link: DevAccessLink) -> None: ...

    def find_by_label(self, label: str) -> DevAccessLink | None: ...

    def lock_by_label(self, label: str) -> DevAccessLink | None:
        """Finds the link and holds it until the transaction ends: a regeneration waits for an
        acceptance in progress, and sees the user it created."""
        ...

    def lock_by_token_hash(self, token_hash: str) -> DevAccessLink | None:
        """Finds the link and holds it until the transaction ends: only one acceptance at a
        time can create its user."""
        ...

    def replace_token_hash(self, link_id: uuid.UUID, token_hash: str) -> None: ...

    def assign_user(self, link_id: uuid.UUID, user_id: uuid.UUID) -> None: ...
