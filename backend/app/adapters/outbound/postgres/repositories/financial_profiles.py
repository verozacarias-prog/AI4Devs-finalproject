from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import Connection

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.financial_profile import FinancialProfile


class PostgresFinancialProfileRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, profile: FinancialProfile) -> None:
        execute_write(self._connection, queries.INSERT_FINANCIAL_PROFILE, asdict(profile))
