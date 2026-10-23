from __future__ import annotations

import json
import uuid
from dataclasses import asdict

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.pending_transaction import (
    BatchStatus,
    PendingBatch,
    PendingIntent,
    PendingSource,
    PendingStatus,
    PendingTransaction,
)


class PostgresPendingRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add_batch(self, batch: PendingBatch) -> None:
        execute_write(self._connection, queries.INSERT_PENDING_BATCH, asdict(batch))

    def add(self, pending: PendingTransaction) -> None:
        execute_write(self._connection, queries.INSERT_PENDING_TRANSACTION, _parameters(pending))

    def find_awaiting_reply(
        self, user_id: uuid.UUID
    ) -> tuple[PendingBatch, PendingTransaction] | None:
        row = self._connection.execute(
            text(queries.SELECT_AWAITING_PENDING), {"user_id": user_id}
        ).one_or_none()
        return None if row is None else (_batch_from(row), _pending_from(row))

    def update(self, pending: PendingTransaction) -> None:
        execute_write(self._connection, queries.UPDATE_PENDING_TRANSACTION, _parameters(pending))

    def update_batch(self, batch: PendingBatch) -> None:
        execute_write(self._connection, queries.UPDATE_PENDING_BATCH, asdict(batch))


def _parameters(pending: PendingTransaction) -> dict[str, object]:
    parameters = asdict(pending)
    parameters["parsed_data"] = json.dumps(dict(pending.parsed_data))
    parameters["missing_fields"] = list(pending.missing_fields)
    return parameters


def _batch_from(row: Row[tuple[object, ...]]) -> PendingBatch:
    return PendingBatch(
        id=row.batch_id,
        user_id=row.batch_user_id,
        source=PendingSource(row.batch_source),
        awaiting_reply=row.awaiting_reply,
        question_message_id=row.question_message_id,
        confirmation_message_id=row.confirmation_message_id,
        status=BatchStatus(row.batch_status),
        created_at=row.batch_created_at,
    )


def _pending_from(row: Row[tuple[object, ...]]) -> PendingTransaction:
    parsed = row.parsed_data if isinstance(row.parsed_data, dict) else json.loads(row.parsed_data)
    return PendingTransaction(
        id=row.id,
        user_id=row.user_id,
        intent=PendingIntent(row.intent),
        parsed_data=parsed,
        missing_fields=tuple(row.missing_fields),
        source=PendingSource(row.source),
        batch_id=row.batch_id,
        position=row.position,
        resulting_transaction_id=row.resulting_transaction_id,
        status=PendingStatus(row.status),
        resolved_by=row.resolved_by,
        expires_at=row.expires_at,
        created_at=row.created_at,
        corrected_fields_count=row.corrected_fields_count,
    )
