from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import date

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType


class PostgresBudgetPeriodRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, period: BudgetPeriod) -> None:
        execute_write(self._connection, queries.INSERT_BUDGET_PERIOD, asdict(period))

    def list_covering(self, user_id: uuid.UUID, day: date) -> list[BudgetPeriod]:
        rows = self._connection.execute(
            text(queries.SELECT_PERIODS_COVERING), {"user_id": user_id, "day": day}
        ).all()
        return [
            BudgetPeriod(
                id=row.id,
                user_id=row.user_id,
                family_group_id=row.family_group_id,
                period_type=PeriodType(row.period_type),
                period_start=row.period_start,
                period_end=row.period_end,
                primary_currency=row.primary_currency,
                estimated_income=row.estimated_income,
                status=PeriodStatus(row.status),
            )
            for row in rows
        ]
