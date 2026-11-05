from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.transaction import TransactionSource
from app.domain.entities.transfer import Transfer


class PostgresTransferRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, transfer: Transfer) -> None:
        execute_write(self._connection, queries.INSERT_TRANSFER, asdict(transfer))

    def list_by_user(self, user_id: uuid.UUID) -> list[Transfer]:
        rows = self._connection.execute(
            text(queries.SELECT_TRANSFERS_BY_USER), {"user_id": user_id}
        ).all()
        return [
            Transfer(
                id=row.id,
                user_id=row.user_id,
                from_account_id=row.from_account_id,
                from_amount=row.from_amount,
                from_currency=row.from_currency,
                to_account_id=row.to_account_id,
                to_amount=row.to_amount,
                to_currency=row.to_currency,
                exchange_rate=row.exchange_rate,
                transfer_date=row.transfer_date,
                deleted_at=row.deleted_at,
                source=TransactionSource(row.source),
            )
            for row in rows
        ]
