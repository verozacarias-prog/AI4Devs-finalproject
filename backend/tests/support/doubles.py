"""Doubles of the ports, for the unit tests of the use cases: nothing here touches a database."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date, datetime
from types import TracebackType
from typing import TYPE_CHECKING, Self

from app.domain.entities.account import Account
from app.domain.entities.budget_period import BudgetPeriod, PeriodStatus
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.financial_profile import FinancialProfile
from app.domain.entities.session import Session
from app.domain.entities.user import User
from app.domain.errors import ConflictError, ErrorCode

if TYPE_CHECKING:
    from app.domain.entities.budget import Budget
    from app.domain.entities.category import Category
    from app.domain.entities.chat_message import ChatMessage
    from app.domain.entities.inbound_message import InboundMessage
    from app.domain.entities.llm_call import LlmCall
    from app.domain.entities.llm_usage import UsageCounter
    from app.domain.entities.outbound_message import OutboundMessage
    from app.domain.entities.pending_transaction import PendingBatch, PendingTransaction
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

    def list_by_ids(self, account_ids: set[uuid.UUID]) -> list[Account]:
        return [account for account in self.added if account.id in account_ids]


class InMemoryBudgetPeriods:
    def __init__(self) -> None:
        self.added: list[BudgetPeriod] = []
        # Every write the port is asked for, so that a case can tell nothing was written.
        self.writes = 0

    def add(self, period: BudgetPeriod) -> None:
        self.writes += 1
        self.added.append(period)

    def update(self, period: BudgetPeriod) -> None:
        self.writes += 1
        self.added = [period if kept.id == period.id else kept for kept in self.added]

    def list_covering(self, user_id: uuid.UUID, day: date) -> list[BudgetPeriod]:
        # The periods of the groups of the user are a rule of the query: the integration tests
        # check them against PostgreSQL.
        return [
            period
            for period in self.added
            if period.user_id == user_id and period.period_start <= day <= period.period_end
        ]

    def find_by_id(self, period_id: uuid.UUID) -> BudgetPeriod | None:
        return next((period for period in self.added if period.id == period_id), None)

    def list_owned_by(self, user_id: uuid.UUID, group_ids: set[uuid.UUID]) -> list[BudgetPeriod]:
        return [
            period
            for period in self.added
            if period.user_id == user_id or period.family_group_id in group_ids
        ]

    def confirm(self, period_id: uuid.UUID) -> None:
        self.writes += 1
        self.added = [
            replace(period, status=PeriodStatus.CONFIRMED) if period.id == period_id else period
            for period in self.added
        ]


class InMemoryBudgets:
    def __init__(self) -> None:
        self.added: list[Budget] = []
        self.writes = 0

    def add(self, budget: Budget) -> None:
        self.writes += 1
        self.added.append(budget)

    def replace_for_period(self, period_id: uuid.UUID, budgets: list[Budget]) -> None:
        self.writes += 1
        kept = [budget for budget in self.added if budget.budget_period_id != period_id]
        self.added = kept + budgets

    def list_by_period(self, period_id: uuid.UUID) -> list[Budget]:
        return [budget for budget in self.added if budget.budget_period_id == period_id]

    def find_by_id(self, budget_id: uuid.UUID) -> Budget | None:
        return next((budget for budget in self.added if budget.id == budget_id), None)


class InMemoryCurrencies:
    """A catalog with the two currencies the cases use."""

    def __init__(self) -> None:
        self.codes = {"ARS", "USD"}

    def exists(self, code: str) -> bool:
        return code in self.codes


class InMemoryCategories:
    def __init__(self) -> None:
        self.added: list[Category] = []

    def add(self, category: Category) -> None:
        self.added.append(category)

    def list_available(self, user_id: uuid.UUID) -> list[Category]:
        return [
            category
            for category in self.added
            if category.user_id is None or category.user_id == user_id
        ]

    def list_by_ids(self, category_ids: set[uuid.UUID]) -> list[Category]:
        return [category for category in self.added if category.id in category_ids]


class InMemoryPendings:
    def __init__(self) -> None:
        self.batches: list[PendingBatch] = []
        self.added: list[PendingTransaction] = []

    def add_batch(self, batch: PendingBatch) -> None:
        self.batches.append(batch)

    def add(self, pending: PendingTransaction) -> None:
        self.added.append(pending)

    def find_awaiting_reply(
        self, user_id: uuid.UUID
    ) -> tuple[PendingBatch, PendingTransaction] | None:
        batch = next(
            (batch for batch in self.batches if batch.user_id == user_id and batch.awaiting_reply),
            None,
        )
        if batch is None:
            return None
        pending = next(pending for pending in self.added if pending.batch_id == batch.id)
        return batch, pending

    def update(self, pending: PendingTransaction) -> None:
        self.added = [pending if stored.id == pending.id else stored for stored in self.added]

    def update_batch(self, batch: PendingBatch) -> None:
        self.batches = [batch if stored.id == batch.id else stored for stored in self.batches]


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

    def find_by_id(self, group_id: uuid.UUID) -> FamilyGroup | None:
        return next((group for group in self.added if group.id == group_id), None)

    def list_memberships(self, user_id: uuid.UUID) -> list[Membership]:
        return [membership for membership in self.memberships if membership.user_id == user_id]


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
        # Raised by the next add instead of storing, when a case needs the store to fail.
        self.failure: Exception | None = None

    def add(self, transaction: Transaction) -> None:
        if self.failure is not None:
            raise self.failure
        self.added.append(transaction)

    def list_by_user(self, user_id: uuid.UUID) -> list[Transaction]:
        return [transaction for transaction in self.added if transaction.user_id == user_id]

    def list_by_period(self, period_id: uuid.UUID) -> list[Transaction]:
        return [
            transaction for transaction in self.added if transaction.budget_period_id == period_id
        ]

    def list_by_ids(self, transaction_ids: set[uuid.UUID]) -> list[Transaction]:
        return [transaction for transaction in self.added if transaction.id in transaction_ids]


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
        # What the next claims hand out, in order. The order and the wait per sender are rules
        # of the query: the integration tests check them against PostgreSQL.
        self.claimable: list[InboundMessage] = []
        # Marked processed, and committed. A mark waits for the commit of its unit of work, as
        # in the database, where leaving the block without a commit undoes it.
        self.marked: list[uuid.UUID] = []
        self.marked_uncommitted: list[uuid.UUID] = []
        # Another request with the same key, stored between the search for the key and the
        # next add, which the store then rejects as a repeated key.
        self.stored_meanwhile: InboundMessage | None = None
        # Another worker took the message again after this one did: marking it fails.
        self.taken_again = False
        # Left for another attempt, as (message, attempts, next attempt), and failed for good.
        self.retried: list[tuple[uuid.UUID, int, datetime]] = []
        self.failed: list[uuid.UUID] = []
        # Put off to the next day by a limit of use, as (message, attempts, next attempt).
        self.deferred: list[tuple[uuid.UUID, int, datetime]] = []

    def add(self, message: InboundMessage) -> None:
        if self.stored_meanwhile is not None:
            self.added.append(self.stored_meanwhile)
            self.stored_meanwhile = None
            raise ConflictError(ErrorCode.CONFLICT)
        self.added.append(message)

    def find_web(self, provider_message_id: str) -> InboundMessage | None:
        return next(
            (
                message
                for message in self.added
                if message.provider_message_id == provider_message_id
            ),
            None,
        )

    def claim_next(self, now: datetime, locked_until: datetime) -> InboundMessage | None:
        return self.claimable.pop(0) if self.claimable else None

    def mark_processed(self, message_id: uuid.UUID, attempts: int, at: datetime) -> bool:
        if self.taken_again:
            return False
        self.marked_uncommitted.append(message_id)
        return True

    def retry_later(self, message_id: uuid.UUID, attempts: int, next_attempt_at: datetime) -> bool:
        if self.taken_again:
            return False
        self.retried.append((message_id, attempts, next_attempt_at))
        return True

    def mark_failed(self, message_id: uuid.UUID, attempts: int, at: datetime) -> bool:
        if self.taken_again:
            return False
        self.failed.append(message_id)
        return True

    def defer(self, message_id: uuid.UUID, attempts: int, next_attempt_at: datetime) -> bool:
        if self.taken_again:
            return False
        self.deferred.append((message_id, attempts, next_attempt_at))
        return True

    def commit(self) -> None:
        self.marked.extend(self.marked_uncommitted)
        self.marked_uncommitted.clear()


class InMemoryOutboundMessages:
    def __init__(self) -> None:
        self.added: list[OutboundMessage] = []
        # Raised by the next add instead of storing, when a case needs the store to fail.
        self.failure: Exception | None = None

    def add(self, message: OutboundMessage) -> None:
        if self.failure is not None:
            raise self.failure
        self.added.append(message)

    def exists_for_user(self, message_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return any(
            message.id == message_id and message.user_id == user_id for message in self.added
        )

    def sent_since(self, user_id: uuid.UUID, text: str, since: datetime) -> bool:
        return any(
            message.user_id == user_id and message.text == text and message.created_at >= since
            for message in self.added
        )


class InMemoryChatMessages:
    def contains(self, user_id: uuid.UUID, message_id: uuid.UUID) -> bool:
        # The conversation is put together by the queries: the integration tests check it.
        raise NotImplementedError

    def list_by_user(self, user_id: uuid.UUID, after: uuid.UUID | None) -> list[ChatMessage]:
        # The conversation is put together by the query: the integration tests check it.
        raise NotImplementedError


class InMemoryLlmUsage:
    """The daily counters of each user, as (user, day, counter): what LLM_USAGE keeps."""

    def __init__(self) -> None:
        self.counts: dict[tuple[uuid.UUID, date, UsageCounter], int] = {}
        self.tokens: dict[tuple[uuid.UUID, date, UsageCounter], tuple[int, int]] = {}

    def count(self, user_id: uuid.UUID, day: date, counter: UsageCounter) -> int:
        return self.counts.get((user_id, day, counter), 0)

    def add(
        self,
        user_id: uuid.UUID,
        day: date,
        counter: UsageCounter,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        key = (user_id, day, counter)
        self.counts[key] = self.counts.get(key, 0) + 1
        stored_input, stored_output = self.tokens.get(key, (0, 0))
        self.tokens[key] = (stored_input + input_tokens, stored_output + output_tokens)


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.users = InMemoryUsers()
        self.accounts = InMemoryAccounts()
        self.budget_periods = InMemoryBudgetPeriods()
        self.budgets = InMemoryBudgets()
        self.categories = InMemoryCategories()
        self.currencies = InMemoryCurrencies()
        self.pendings = InMemoryPendings()
        self.financial_profiles = InMemoryFinancialProfiles()
        self.family_groups = InMemoryFamilyGroups()
        self.sessions = InMemorySessions()
        self.transactions = InMemoryTransactions()
        self.transfers = InMemoryTransfers()
        self.inbound_messages = InMemoryInboundMessages()
        self.outbound_messages = InMemoryOutboundMessages()
        self.chat_messages = InMemoryChatMessages()
        self.llm_usage = InMemoryLlmUsage()
        self.commits = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # Leaving the block without a commit undoes what it did not commit.
        self.inbound_messages.marked_uncommitted.clear()

    def commit(self) -> None:
        self.commits += 1
        self.inbound_messages.commit()


class InMemoryLlmCallLog:
    def __init__(self) -> None:
        self.recorded: list[LlmCall] = []
        # The calls whose output the validation rejected, in the order they were marked.
        self.blocked: list[uuid.UUID] = []

    def record(self, call: LlmCall) -> None:
        self.recorded.append(call)

    def mark_blocked(self, call_id: uuid.UUID) -> None:
        self.blocked.append(call_id)
