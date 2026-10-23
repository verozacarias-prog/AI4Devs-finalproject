from __future__ import annotations

import uuid

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.category import Category
from app.domain.entities.transaction import TransactionType


class PostgresCategoryRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, category: Category) -> None:
        execute_write(
            self._connection,
            queries.INSERT_CATEGORY,
            {
                "id": category.id,
                "name": category.name,
                "user_id": category.user_id,
                "kind": category.kind,
            },
        )

    def list_available(self, user_id: uuid.UUID) -> list[Category]:
        rows = self._connection.execute(
            text(queries.SELECT_CATEGORIES_AVAILABLE), {"user_id": user_id}
        ).all()
        return [
            Category(id=row.id, name=row.name, kind=TransactionType(row.kind), user_id=row.user_id)
            for row in rows
        ]
