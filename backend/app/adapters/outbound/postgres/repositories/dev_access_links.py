from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.dev_access_link import DevAccessLink


class PostgresDevAccessLinkRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, link: DevAccessLink) -> None:
        execute_write(self._connection, queries.INSERT_DEV_ACCESS_LINK, asdict(link))

    def find_by_label(self, label: str) -> DevAccessLink | None:
        row = self._connection.execute(
            text(queries.SELECT_DEV_ACCESS_LINK_BY_LABEL), {"label": label}
        ).one_or_none()
        return None if row is None else _link_from(row)

    def lock_by_token_hash(self, token_hash: str) -> DevAccessLink | None:
        row = self._connection.execute(
            text(queries.LOCK_DEV_ACCESS_LINK_BY_TOKEN_HASH), {"token_hash": token_hash}
        ).one_or_none()
        return None if row is None else _link_from(row)

    def replace_token_hash(self, link_id: uuid.UUID, token_hash: str) -> None:
        execute_write(
            self._connection,
            queries.UPDATE_DEV_ACCESS_LINK_TOKEN_HASH,
            {"link_id": link_id, "token_hash": token_hash},
        )

    def assign_user(self, link_id: uuid.UUID, user_id: uuid.UUID) -> None:
        execute_write(
            self._connection,
            queries.ASSIGN_DEV_ACCESS_LINK_USER,
            {"link_id": link_id, "user_id": user_id},
        )


def _link_from(row: Row[tuple[uuid.UUID, str, uuid.UUID | None, str]]) -> DevAccessLink:
    return DevAccessLink(id=row.id, label=row.label, user_id=row.user_id, token_hash=row.token_hash)
