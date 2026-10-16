from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.inbound_message import InboundMessage, InboundStatus, Provider


class PostgresInboundMessageRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, message: InboundMessage) -> None:
        parameters: dict[str, object] = asdict(message)
        parameters["payload"] = json.dumps({queries.MESSAGE_TEXT_KEY: parameters.pop("text")})
        execute_write(self._connection, queries.INSERT_INBOUND_MESSAGE, parameters)

    def claim_next(self, now: datetime, locked_until: datetime) -> InboundMessage | None:
        row = self._connection.execute(
            text(queries.CLAIM_NEXT_INBOUND_MESSAGE),
            {
                "now": now,
                "locked_until": locked_until,
                "text_key": queries.MESSAGE_TEXT_KEY,
            },
        ).one_or_none()
        return None if row is None else _message_from(row)

    def find_web(self, provider_message_id: str) -> InboundMessage | None:
        row = self._connection.execute(
            text(queries.SELECT_WEB_INBOUND_MESSAGE_BY_PROVIDER_ID),
            {"provider_message_id": provider_message_id, "text_key": queries.MESSAGE_TEXT_KEY},
        ).one_or_none()
        return None if row is None else _message_from(row)

    def mark_processed(self, message_id: uuid.UUID, attempts: int, at: datetime) -> bool:
        row = self._connection.execute(
            text(queries.MARK_INBOUND_MESSAGE_PROCESSED),
            {"message_id": message_id, "attempts": attempts, "at": at},
        ).one_or_none()
        return row is not None


def _message_from(row: Row[tuple[object, ...]]) -> InboundMessage:
    return InboundMessage(
        id=row.id,
        provider=Provider(row.provider),
        provider_message_id=row.provider_message_id,
        user_id=row.user_id,
        from_phone=row.from_phone,
        text=row.text,
        quoted_outbound_message_id=row.quoted_outbound_message_id,
        sent_at=row.sent_at,
        status=InboundStatus(row.status),
        attempts=row.attempts,
        locked_until=row.locked_until,
        processed_at=row.processed_at,
    )
