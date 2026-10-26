from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.transaction import Transaction, TransactionSource, TransactionType


class PostgresTransactionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, transaction: Transaction) -> None:
        execute_write(self._connection, queries.INSERT_TRANSACTION, asdict(transaction))

    def list_by_user(self, user_id: uuid.UUID) -> list[Transaction]:
        return self._list(queries.SELECT_TRANSACTIONS_BY_USER, {"user_id": user_id})

    def list_by_period(self, period_id: uuid.UUID) -> list[Transaction]:
        return self._list(queries.SELECT_TRANSACTIONS_BY_PERIOD, {"period_id": period_id})

    def list_by_ids(self, transaction_ids: set[uuid.UUID]) -> list[Transaction]:
        return self._list(queries.SELECT_TRANSACTIONS_BY_IDS, {"ids": list(transaction_ids)})

    def _list(self, query: str, parameters: dict[str, object]) -> list[Transaction]:
        rows = self._connection.execute(text(query), parameters).all()
        return [_transaction_from(row) for row in rows]


def _transaction_from(row: Row[tuple[object, ...]]) -> Transaction:
    return Transaction(
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
        budget_period_id=row.budget_period_id,
        category_id=row.category_id,
        source=TransactionSource(row.source),
        description=row.description,
        refund_of=row.refund_of,
    )
