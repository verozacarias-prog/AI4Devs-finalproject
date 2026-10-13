from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy import Connection, Engine

from app.adapters.outbound.postgres.repositories import (
    PostgresAccountRepository,
    PostgresBudgetPeriodRepository,
    PostgresFamilyGroupRepository,
    PostgresFinancialProfileRepository,
    PostgresUserRepository,
)
from app.domain.ports.account_repository_port import AccountRepositoryPort
from app.domain.ports.budget_period_repository_port import BudgetPeriodRepositoryPort
from app.domain.ports.family_group_repository_port import FamilyGroupRepositoryPort
from app.domain.ports.financial_profile_repository_port import FinancialProfileRepositoryPort
from app.domain.ports.user_repository_port import UserRepositoryPort


class SqlAlchemyUnitOfWork:
    """Implements UnitOfWorkPort: one connection and one transaction for the whole block.

    Leaving the block without calling `commit` rolls everything back, whether it ended well or
    with an error.
    """

    users: UserRepositoryPort
    accounts: AccountRepositoryPort
    budget_periods: BudgetPeriodRepositoryPort
    financial_profiles: FinancialProfileRepositoryPort
    family_groups: FamilyGroupRepositoryPort

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None

    def __enter__(self) -> Self:
        connection = self._engine.connect()
        connection.begin()
        self._connection = connection
        self.users = PostgresUserRepository(connection)
        self.accounts = PostgresAccountRepository(connection)
        self.budget_periods = PostgresBudgetPeriodRepository(connection)
        self.financial_profiles = PostgresFinancialProfileRepository(connection)
        self.family_groups = PostgresFamilyGroupRepository(connection)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._connection is not None:
            # Closing a connection with an open transaction rolls it back.
            self._connection.close()
            self._connection = None

    def commit(self) -> None:
        if self._connection is not None:
            self._connection.commit()
