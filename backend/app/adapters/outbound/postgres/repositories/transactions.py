from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.transaction import Transaction, TransactionType


class PostgresTransactionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, transaction: Transaction) -> None:
        execute_write(self._connection, queries.INSERT_TRANSACTION, asdict(transaction))

    def list_by_user(self, user_id: uuid.UUID) -> list[Transaction]:
        rows = self._connection.execute(
            text(queries.SELECT_TRANSACTIONS_BY_USER), {"user_id": user_id}
        ).all()
        return [
            Transaction(
                id=row.id,
                user_id=row.user_id,
                account_id=row.account_id,
                type=TransactionType(row.type),
                amount=row.amount,
                currency=row.currency,
                exchange_rate=row.exchange_rate,
                transaction_date=row.transaction_date,
                duplicate_of=row.duplicate_of,
                deleted_at=row.deleted_at,
            )
            for row in rows
        ]
