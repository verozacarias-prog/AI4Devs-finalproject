from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.account import Account, AccountType


class PostgresAccountRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, account: Account) -> None:
        execute_write(self._connection, queries.INSERT_ACCOUNT, asdict(account))

    def list_by_user(self, user_id: uuid.UUID) -> list[Account]:
        rows = self._connection.execute(
            text(queries.SELECT_ACCOUNTS_BY_USER), {"user_id": user_id}
        ).all()
        return [
            Account(
                id=row.id,
                user_id=row.user_id,
                name=row.name,
                type=AccountType(row.type),
                currency=row.currency,
                initial_balance=row.initial_balance,
                opened_at=row.opened_at,
            )
            for row in rows
        ]
