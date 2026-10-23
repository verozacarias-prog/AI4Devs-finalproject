from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.outbound_message import OutboundMessage


class PostgresOutboundMessageRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, message: OutboundMessage) -> None:
        parameters: dict[str, object] = asdict(message)
        parameters["content"] = json.dumps(
            {
                queries.MESSAGE_TEXT_KEY: parameters.pop("text"),
                queries.RESPONSE_KIND_KEY: parameters.pop("response_kind"),
            }
        )
        execute_write(self._connection, queries.INSERT_OUTBOUND_MESSAGE, parameters)

    def exists_for_user(self, message_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        exists: bool = self._connection.execute(
            text(queries.OUTBOUND_MESSAGE_OF_USER_EXISTS),
            {"message_id": message_id, "user_id": user_id},
        ).scalar_one()
        return exists

    def sent_since(self, user_id: uuid.UUID, text_sent: str, since: datetime) -> bool:
        sent: bool = self._connection.execute(
            text(queries.OUTBOUND_TEXT_SENT_SINCE),
            {
                "user_id": user_id,
                "text_key": queries.MESSAGE_TEXT_KEY,
                "text": text_sent,
                "since": since,
            },
        ).scalar_one()
        return sent
