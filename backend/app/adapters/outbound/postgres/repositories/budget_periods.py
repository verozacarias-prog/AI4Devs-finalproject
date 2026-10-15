from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import Connection

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.budget_period import BudgetPeriod


class PostgresBudgetPeriodRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, period: BudgetPeriod) -> None:
        execute_write(self._connection, queries.INSERT_BUDGET_PERIOD, asdict(period))
