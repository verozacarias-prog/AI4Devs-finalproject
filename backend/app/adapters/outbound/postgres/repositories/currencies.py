from __future__ import annotations

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.domain.entities.currency import Currency


class PostgresCurrencyRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def list_all(self) -> list[Currency]:
        rows = self._connection.execute(text(queries.SELECT_CURRENCIES)).all()
        return [Currency(code=row.code, name=row.name) for row in rows]

    def exists(self, code: str) -> bool:
        row = self._connection.execute(text(queries.SELECT_CURRENCY), {"code": code}).first()
        return row is not None
