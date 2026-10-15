"""Doubles of the ports, for the unit tests of the use cases: nothing here touches a database."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Self

from app.domain.entities.account import Account
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.financial_profile import FinancialProfile
from app.domain.entities.session import Session
from app.domain.entities.user import User

if TYPE_CHECKING:
    from app.domain.entities.chat_message import ChatMessage
    from app.domain.entities.inbound_message import InboundMessage
    from app.domain.entities.outbound_message import OutboundMessage
    from app.domain.entities.transaction import Transaction
    from app.domain.entities.transfer import Transfer


class FixedClock:
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class InMemoryUsers:
    def __init__(self) -> None:
        self.added: list[User] = []

    def add(self, user: User) -> None:
        self.added.append(user)

    def find_by_phone(self, phone: str) -> User | None:
        return next((user for user in self.added if user.whatsapp_phone == phone), None)

    def find_by_id(self, user_id: uuid.UUID) -> User | None:
        return next((user for user in self.added if user.id == user_id), None)

    def list_by_phone_prefix(self, prefix: str) -> list[User]:
        matching = [user for user in self.added if user.whatsapp_phone.startswith(prefix)]
        return sorted(matching, key=lambda user: user.name)


class InMemoryAccounts:
    def __init__(self) -> None:
        self.added: list[Account] = []

    def add(self, account: Account) -> None:
        self.added.append(account)

    def list_by_user(self, user_id: uuid.UUID) -> list[Account]:
        return [account for account in self.added if account.user_id == user_id]


class InMemoryBudgetPeriods:
    def __init__(self) -> None:
        self.added: list[BudgetPeriod] = []

    def add(self, period: BudgetPeriod) -> None:
        self.added.append(period)


class InMemoryFinancialProfiles:
    def __init__(self) -> None:
        self.added: list[FinancialProfile] = []

    def add(self, profile: FinancialProfile) -> None:
        self.added.append(profile)


class InMemoryFamilyGroups:
    def __init__(self) -> None:
        self.added: list[FamilyGroup] = []
        self.memberships: list[Membership] = []

    def add(self, group: FamilyGroup) -> None:
        self.added.append(group)

    def add_membership(self, membership: Membership) -> None:
        self.memberships.append(membership)

    def find_owned_by(self, owner_id: uuid.UUID, name: str) -> FamilyGroup | None:
        owned = {
            membership.family_group_id
            for membership in self.memberships
            if membership.user_id == owner_id and membership.role == GroupRole.OWNER
        }
        return next(
            (group for group in self.added if group.id in owned and group.name == name), None
        )


class InMemorySessions:
    def __init__(self) -> None:
        self.stored: dict[uuid.UUID, Session] = {}

    def add(self, session: Session) -> None:
        self.stored[session.id] = session

    def find_by_token_hash(self, token_hash: str) -> Session | None:
        return next(
            (session for session in self.stored.values() if session.token_hash == token_hash),
            None,
        )

    def touch(self, session_id: uuid.UUID, at: datetime) -> None:
        self.stored[session_id] = replace(self.stored[session_id], last_seen_at=at)

    def revoke(self, session_id: uuid.UUID, at: datetime) -> None:
        self.stored[session_id] = replace(self.stored[session_id], revoked_at=at)


class InMemoryTransactions:
    def __init__(self) -> None:
        self.added: list[Transaction] = []

    def add(self, transaction: Transaction) -> None:
        self.added.append(transaction)

    def list_by_user(self, user_id: uuid.UUID) -> list[Transaction]:
        return [transaction for transaction in self.added if transaction.user_id == user_id]


class InMemoryTransfers:
    def __init__(self) -> None:
        self.added: list[Transfer] = []

    def add(self, transfer: Transfer) -> None:
        self.added.append(transfer)

    def list_by_user(self, user_id: uuid.UUID) -> list[Transfer]:
        return [transfer for transfer in self.added if transfer.user_id == user_id]


class InMemoryInboundMessages:
    def __init__(self) -> None:
        self.added: list[InboundMessage] = []

    def add(self, message: InboundMessage) -> None:
        self.added.append(message)

    def claim_next(self, now: datetime, locked_until: datetime) -> InboundMessage | None:
        # The order and the wait per sender are rules of the query: the integration tests
        # check them against PostgreSQL. No unit test claims a message yet.
        raise NotImplementedError

    def mark_processed(self, message_id: uuid.UUID, attempts: int, at: datetime) -> bool:
        raise NotImplementedError


class InMemoryOutboundMessages:
    def __init__(self) -> None:
        self.added: list[OutboundMessage] = []

    def add(self, message: OutboundMessage) -> None:
        self.added.append(message)


class InMemoryChatMessages:
    def list_by_user(self, user_id: uuid.UUID, after: uuid.UUID | None) -> list[ChatMessage]:
        # The conversation is put together by the query: the integration tests check it.
        raise NotImplementedError


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.users = InMemoryUsers()
        self.accounts = InMemoryAccounts()
        self.budget_periods = InMemoryBudgetPeriods()
        self.financial_profiles = InMemoryFinancialProfiles()
        self.family_groups = InMemoryFamilyGroups()
        self.sessions = InMemorySessions()
        self.transactions = InMemoryTransactions()
        self.transfers = InMemoryTransfers()
        self.inbound_messages = InMemoryInboundMessages()
        self.outbound_messages = InMemoryOutboundMessages()
        self.chat_messages = InMemoryChatMessages()
        self.commits = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1
