from __future__ import annotations

import uuid

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.domain.entities.budget import Budget


class PostgresBudgetRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def list_by_period(self, period_id: uuid.UUID) -> list[Budget]:
        rows = self._connection.execute(
            text(queries.SELECT_BUDGETS_BY_PERIOD), {"period_id": period_id}
        ).all()
        return [_budget_from(row) for row in rows]

    def find_by_id(self, budget_id: uuid.UUID) -> Budget | None:
        row = self._connection.execute(
            text(queries.SELECT_BUDGET_BY_ID), {"budget_id": budget_id}
        ).one_or_none()
        return None if row is None else _budget_from(row)


def _budget_from(row: Row[tuple[object, ...]]) -> Budget:
    return Budget(
        id=row.id,
        budget_period_id=row.budget_period_id,
        category_id=row.category_id,
        limit_amount=row.limit_amount,
    )
