from __future__ import annotations

from typing import Protocol

from app.domain.entities.currency import Currency


class CurrencyRepositoryPort(Protocol):
    def list_all(self) -> list[Currency]:
        """The catalog, by code."""
        ...

    def exists(self, code: str) -> bool:
        """Whether that code is in the catalog."""
        ...
