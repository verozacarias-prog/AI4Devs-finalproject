from __future__ import annotations

import json
from dataclasses import asdict

from sqlalchemy import Connection

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.pending_transaction import PendingBatch, PendingTransaction


class PostgresPendingRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add_batch(self, batch: PendingBatch) -> None:
        execute_write(self._connection, queries.INSERT_PENDING_BATCH, asdict(batch))

    def add(self, pending: PendingTransaction) -> None:
        parameters = asdict(pending)
        parameters["parsed_data"] = json.dumps(dict(pending.parsed_data))
        parameters["missing_fields"] = list(pending.missing_fields)
        execute_write(self._connection, queries.INSERT_PENDING_TRANSACTION, parameters)
