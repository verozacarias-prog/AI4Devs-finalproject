from __future__ import annotations

import uuid

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.domain.entities.budget import Budget


class PostgresBudgetRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def list_by_period(self, period_id: uuid.UUID) -> list[Budget]:
        rows = self._connection.execute(
            text(queries.SELECT_BUDGETS_BY_PERIOD), {"period_id": period_id}
        ).all()
        return [
            Budget(
                id=row.id,
                budget_period_id=row.budget_period_id,
                category_id=row.category_id,
                limit_amount=row.limit_amount,
            )
            for row in rows
        ]
