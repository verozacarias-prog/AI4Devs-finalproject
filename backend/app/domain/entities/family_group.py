from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class GroupRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


@dataclass(frozen=True)
class FamilyGroup:
    """A family or an activity of a user. Nothing in it says which of the two it is."""

    id: uuid.UUID
    name: str


@dataclass(frozen=True)
class Membership:
    user_id: uuid.UUID
    family_group_id: uuid.UUID
    role: GroupRole
    joined_at: datetime
    # Set when the user left the group: the membership is closed, never deleted (§ 10).
    left_at: datetime | None = None
