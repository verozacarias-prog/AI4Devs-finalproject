from __future__ import annotations

from typing import Protocol

from app.domain.entities.financial_profile import FinancialProfile


class FinancialProfileRepository(Protocol):
    def add(self, profile: FinancialProfile) -> None: ...
