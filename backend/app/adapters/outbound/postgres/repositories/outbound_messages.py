from __future__ import annotations

import json
from dataclasses import asdict

from sqlalchemy import Connection

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
