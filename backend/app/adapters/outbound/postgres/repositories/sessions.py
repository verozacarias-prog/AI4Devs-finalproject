from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.session import Session


class PostgresSessionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, session: Session) -> None:
        execute_write(self._connection, queries.INSERT_SESSION, asdict(session))

    def find_by_token_hash(self, token_hash: str) -> Session | None:
        row = self._connection.execute(
            text(queries.SELECT_SESSION_BY_TOKEN_HASH), {"token_hash": token_hash}
        ).one_or_none()
        if row is None:
            return None
        return Session(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )

    def touch(self, session_id: uuid.UUID, at: datetime) -> None:
        execute_write(self._connection, queries.TOUCH_SESSION, {"session_id": session_id, "at": at})

    def revoke(self, session_id: uuid.UUID, at: datetime) -> None:
        execute_write(
            self._connection, queries.REVOKE_SESSION, {"session_id": session_id, "at": at}
        )
