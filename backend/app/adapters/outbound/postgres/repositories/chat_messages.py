from __future__ import annotations

import uuid

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.domain.entities.chat_message import ChatMessage, Direction
from app.domain.entities.outbound_message import ResponseKind


class PostgresChatMessageRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def list_by_user(self, user_id: uuid.UUID, after: uuid.UUID | None) -> list[ChatMessage]:
        rows = self._connection.execute(
            text(queries.SELECT_CHAT_MESSAGES_BY_USER), {"user_id": user_id, "after": after}
        ).all()
        return [
            ChatMessage(
                id=row.id,
                direction=Direction(row.direction),
                text=row.text,
                quoted_message_id=row.quoted_message_id,
                response_kind=_response_kind_from(row.response_kind),
                created_at=row.created_at,
            )
            for row in rows
        ]


def _response_kind_from(value: str | None) -> ResponseKind | None:
    return None if value is None else ResponseKind(value)
