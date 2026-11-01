from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy import Connection, Engine
from sqlalchemy.exc import OperationalError

from app.adapters.outbound.postgres.repositories.accounts import PostgresAccountRepository
from app.adapters.outbound.postgres.repositories.budget_periods import (
    PostgresBudgetPeriodRepository,
)
from app.adapters.outbound.postgres.repositories.budgets import PostgresBudgetRepository
from app.adapters.outbound.postgres.repositories.categories import PostgresCategoryRepository
from app.adapters.outbound.postgres.repositories.chat_messages import PostgresChatMessageRepository
from app.adapters.outbound.postgres.repositories.currencies import PostgresCurrencyRepository
from app.adapters.outbound.postgres.repositories.family_groups import PostgresFamilyGroupRepository
from app.adapters.outbound.postgres.repositories.financial_profiles import (
    PostgresFinancialProfileRepository,
)
from app.adapters.outbound.postgres.repositories.inbound_messages import (
    PostgresInboundMessageRepository,
)
from app.adapters.outbound.postgres.repositories.llm_usage import PostgresLlmUsageRepository
from app.adapters.outbound.postgres.repositories.outbound_messages import (
    PostgresOutboundMessageRepository,
)
from app.adapters.outbound.postgres.repositories.pendings import PostgresPendingRepository
from app.adapters.outbound.postgres.repositories.sessions import PostgresSessionRepository
from app.adapters.outbound.postgres.repositories.transactions import PostgresTransactionRepository
from app.adapters.outbound.postgres.repositories.transfers import PostgresTransferRepository
from app.adapters.outbound.postgres.repositories.users import PostgresUserRepository
from app.domain.errors import StoreUnavailableError
from app.domain.ports.account_repository_port import AccountRepositoryPort
from app.domain.ports.budget_period_repository_port import BudgetPeriodRepositoryPort
from app.domain.ports.budget_repository_port import BudgetRepositoryPort
from app.domain.ports.category_repository_port import CategoryRepositoryPort
from app.domain.ports.chat_message_repository_port import ChatMessageRepositoryPort
from app.domain.ports.currency_repository_port import CurrencyRepositoryPort
from app.domain.ports.family_group_repository_port import FamilyGroupRepositoryPort
from app.domain.ports.financial_profile_repository_port import FinancialProfileRepositoryPort
from app.domain.ports.inbound_message_repository_port import InboundMessageRepositoryPort
from app.domain.ports.llm_usage_repository_port import LlmUsageRepositoryPort
from app.domain.ports.outbound_message_repository_port import OutboundMessageRepositoryPort
from app.domain.ports.pending_repository_port import PendingRepositoryPort
from app.domain.ports.session_repository_port import SessionRepositoryPort
from app.domain.ports.transaction_repository_port import TransactionRepositoryPort
from app.domain.ports.transfer_repository_port import TransferRepositoryPort
from app.domain.ports.user_repository_port import UserRepositoryPort


class SqlAlchemyUnitOfWork:
    """Implements UnitOfWorkPort: one connection and one transaction for the whole block.

    Leaving the block without calling `commit` rolls everything back, whether it ended well or
    with an error.
    """

    users: UserRepositoryPort
    accounts: AccountRepositoryPort
    budget_periods: BudgetPeriodRepositoryPort
    budgets: BudgetRepositoryPort
    categories: CategoryRepositoryPort
    currencies: CurrencyRepositoryPort
    pendings: PendingRepositoryPort
    financial_profiles: FinancialProfileRepositoryPort
    family_groups: FamilyGroupRepositoryPort
    sessions: SessionRepositoryPort
    transactions: TransactionRepositoryPort
    transfers: TransferRepositoryPort
    inbound_messages: InboundMessageRepositoryPort
    outbound_messages: OutboundMessageRepositoryPort
    chat_messages: ChatMessageRepositoryPort
    llm_usage: LlmUsageRepositoryPort

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None

    def __enter__(self) -> Self:
        try:
            connection = self._engine.connect()
            connection.begin()
        except OperationalError as error:
            raise StoreUnavailableError from error
        self._connection = connection
        self.users = PostgresUserRepository(connection)
        self.accounts = PostgresAccountRepository(connection)
        self.budget_periods = PostgresBudgetPeriodRepository(connection)
        self.budgets = PostgresBudgetRepository(connection)
        self.categories = PostgresCategoryRepository(connection)
        self.currencies = PostgresCurrencyRepository(connection)
        self.pendings = PostgresPendingRepository(connection)
        self.financial_profiles = PostgresFinancialProfileRepository(connection)
        self.family_groups = PostgresFamilyGroupRepository(connection)
        self.sessions = PostgresSessionRepository(connection)
        self.transactions = PostgresTransactionRepository(connection)
        self.transfers = PostgresTransferRepository(connection)
        self.inbound_messages = PostgresInboundMessageRepository(connection)
        self.outbound_messages = PostgresOutboundMessageRepository(connection)
        self.chat_messages = PostgresChatMessageRepository(connection)
        self.llm_usage = PostgresLlmUsageRepository(connection)
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
        # A connection lost, or two transactions that collided, may work a while later: the
        # single place where the domain learns it, whatever query met it.
        if isinstance(exc, OperationalError):
            raise StoreUnavailableError from exc

    def commit(self) -> None:
        if self._connection is not None:
            try:
                self._connection.commit()
            except OperationalError as error:
                raise StoreUnavailableError from error
