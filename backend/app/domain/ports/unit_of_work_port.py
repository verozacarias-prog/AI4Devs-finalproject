from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from app.domain.ports.account_repository import AccountRepository
from app.domain.ports.budget_period_repository import BudgetPeriodRepository
from app.domain.ports.family_group_repository import FamilyGroupRepository
from app.domain.ports.financial_profile_repository import FinancialProfileRepository
from app.domain.ports.user_repository import UserRepository


class UnitOfWorkPort(Protocol):
    """One database transaction. Leaving the block without a commit undoes everything."""

    @property
    def users(self) -> UserRepository: ...

    @property
    def accounts(self) -> AccountRepository: ...

    @property
    def budget_periods(self) -> BudgetPeriodRepository: ...

    @property
    def financial_profiles(self) -> FinancialProfileRepository: ...

    @property
    def family_groups(self) -> FamilyGroupRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...
