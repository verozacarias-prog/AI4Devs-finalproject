from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from app.domain.ports.account_repository_port import AccountRepositoryPort
from app.domain.ports.budget_period_repository_port import BudgetPeriodRepositoryPort
from app.domain.ports.budget_repository_port import BudgetRepositoryPort
from app.domain.ports.category_repository_port import CategoryRepositoryPort
from app.domain.ports.chat_message_repository_port import ChatMessageRepositoryPort
from app.domain.ports.family_group_repository_port import FamilyGroupRepositoryPort
from app.domain.ports.financial_profile_repository_port import FinancialProfileRepositoryPort
from app.domain.ports.inbound_message_repository_port import InboundMessageRepositoryPort
from app.domain.ports.outbound_message_repository_port import OutboundMessageRepositoryPort
from app.domain.ports.pending_repository_port import PendingRepositoryPort
from app.domain.ports.session_repository_port import SessionRepositoryPort
from app.domain.ports.transaction_repository_port import TransactionRepositoryPort
from app.domain.ports.transfer_repository_port import TransferRepositoryPort
from app.domain.ports.user_repository_port import UserRepositoryPort


class UnitOfWorkPort(Protocol):
    """One database transaction. Leaving the block without a commit undoes everything."""

    @property
    def users(self) -> UserRepositoryPort: ...

    @property
    def accounts(self) -> AccountRepositoryPort: ...

    @property
    def budget_periods(self) -> BudgetPeriodRepositoryPort: ...
    @property
    def budgets(self) -> BudgetRepositoryPort: ...

    @property
    def categories(self) -> CategoryRepositoryPort: ...

    @property
    def pendings(self) -> PendingRepositoryPort: ...

    @property
    def financial_profiles(self) -> FinancialProfileRepositoryPort: ...

    @property
    def family_groups(self) -> FamilyGroupRepositoryPort: ...

    @property
    def sessions(self) -> SessionRepositoryPort: ...

    @property
    def transactions(self) -> TransactionRepositoryPort: ...

    @property
    def transfers(self) -> TransferRepositoryPort: ...

    @property
    def inbound_messages(self) -> InboundMessageRepositoryPort: ...

    @property
    def outbound_messages(self) -> OutboundMessageRepositoryPort: ...

    @property
    def chat_messages(self) -> ChatMessageRepositoryPort: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...
