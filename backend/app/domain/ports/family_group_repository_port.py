from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.entities.family_group import FamilyGroup, Membership


class FamilyGroupRepositoryPort(Protocol):
    def add(self, group: FamilyGroup) -> None: ...

    def add_membership(self, membership: Membership) -> None: ...

    def find_owned_by(self, owner_id: uuid.UUID, name: str) -> FamilyGroup | None:
        """The group with that name whose current owner is that user, if there is one."""
        ...
