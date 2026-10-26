from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership


class PostgresFamilyGroupRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, group: FamilyGroup) -> None:
        execute_write(self._connection, queries.INSERT_FAMILY_GROUP, asdict(group))

    def add_membership(self, membership: Membership) -> None:
        execute_write(self._connection, queries.INSERT_MEMBERSHIP, asdict(membership))

    def find_owned_by(self, owner_id: uuid.UUID, name: str) -> FamilyGroup | None:
        row = self._connection.execute(
            text(queries.SELECT_GROUP_OWNED_BY),
            {"owner_id": owner_id, "owner_role": GroupRole.OWNER, "name": name},
        ).one_or_none()
        return None if row is None else FamilyGroup(id=row.id, name=row.name)

    def find_by_id(self, group_id: uuid.UUID) -> FamilyGroup | None:
        row = self._connection.execute(
            text(queries.SELECT_GROUP_BY_ID), {"group_id": group_id}
        ).one_or_none()
        return None if row is None else FamilyGroup(id=row.id, name=row.name)

    def list_memberships(self, user_id: uuid.UUID) -> list[Membership]:
        rows = self._connection.execute(
            text(queries.SELECT_MEMBERSHIPS_BY_USER), {"user_id": user_id}
        ).all()
        return [
            Membership(
                user_id=row.user_id,
                family_group_id=row.family_group_id,
                role=GroupRole(row.role),
                joined_at=row.joined_at,
                left_at=row.left_at,
            )
            for row in rows
        ]
