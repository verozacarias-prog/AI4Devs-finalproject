from __future__ import annotations

from app.domain.entities.currency import Currency
from app.domain.ports.unit_of_work_port import UnitOfWorkPort


class ListCurrencies:
    """The currencies of the catalog, to choose the one of a period (FEAT-005, CA-17)."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    def execute(self) -> list[Currency]:
        with self._unit_of_work as unit_of_work:
            return unit_of_work.currencies.list_all()
