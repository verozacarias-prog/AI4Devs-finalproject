from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.budget import Budget


class PostgresBudgetRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def replace_for_period(self, period_id: uuid.UUID, budgets: list[Budget]) -> None:
        execute_write(
            self._connection,
            queries.DELETE_BUDGETS_NOT_IN,
            {"period_id": period_id, "ids": [budget.id for budget in budgets]},
        )
        for budget in budgets:
            execute_write(self._connection, queries.UPSERT_BUDGET, asdict(budget))

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
