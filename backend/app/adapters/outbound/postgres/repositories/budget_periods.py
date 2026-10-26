from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import date

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus, PeriodType


class PostgresBudgetPeriodRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, period: BudgetPeriod) -> None:
        execute_write(self._connection, queries.INSERT_BUDGET_PERIOD, asdict(period))

    def confirm(self, period_id: uuid.UUID) -> None:
        execute_write(self._connection, queries.CONFIRM_BUDGET_PERIOD, {"period_id": period_id})

    def list_covering(self, user_id: uuid.UUID, day: date) -> list[BudgetPeriod]:
        rows = self._connection.execute(
            text(queries.SELECT_PERIODS_COVERING), {"user_id": user_id, "day": day}
        ).all()
        return [_period_from(row) for row in rows]

    def find_by_id(self, period_id: uuid.UUID) -> BudgetPeriod | None:
        row = self._connection.execute(
            text(queries.SELECT_BUDGET_PERIOD_BY_ID), {"period_id": period_id}
        ).one_or_none()
        return None if row is None else _period_from(row)

    def list_owned_by(self, user_id: uuid.UUID, group_ids: set[uuid.UUID]) -> list[BudgetPeriod]:
        rows = self._connection.execute(
            text(queries.SELECT_BUDGET_PERIODS_OWNED_BY),
            {"user_id": user_id, "group_ids": list(group_ids)},
        ).all()
        return [_period_from(row) for row in rows]


def _period_from(row: Row[tuple[object, ...]]) -> BudgetPeriod:
    return BudgetPeriod(
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
