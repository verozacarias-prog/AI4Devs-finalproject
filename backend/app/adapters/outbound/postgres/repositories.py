"""The repositories: each one implements a `*_repository` port over one open connection.

They translate an entity to the parameters of a query and back, and nothing else. The SQL is
in `queries.py`.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.account import Account, AccountType
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.chat_message import ChatMessage, Direction
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.financial_profile import FinancialProfile
from app.domain.entities.inbound_message import InboundMessage, InboundStatus, Provider
from app.domain.entities.outbound_message import OutboundMessage, ResponseKind
from app.domain.entities.session import Session
from app.domain.entities.transaction import Transaction, TransactionType
from app.domain.entities.transfer import Transfer
from app.domain.entities.user import OnboardingStatus, User


class PostgresUserRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, user: User) -> None:
        execute_write(self._connection, queries.INSERT_USER, asdict(user))

    def find_by_phone(self, phone: str) -> User | None:
        row = self._connection.execute(
            text(queries.SELECT_USER_BY_PHONE), {"phone": phone}
        ).one_or_none()
        return None if row is None else _user_from(row)

    def find_by_id(self, user_id: uuid.UUID) -> User | None:
        row = self._connection.execute(
            text(queries.SELECT_USER_BY_ID), {"user_id": user_id}
        ).one_or_none()
        return None if row is None else _user_from(row)

    def list_by_phone_prefix(self, prefix: str) -> list[User]:
        rows = self._connection.execute(
            text(queries.SELECT_USERS_BY_PHONE_PREFIX), {"prefix": prefix}
        ).all()
        return [_user_from(row) for row in rows]


def _user_from(row: Row[tuple[object, ...]]) -> User:
    return User(
        id=row.id,
        name=row.name,
        whatsapp_phone=row.whatsapp_phone,
        country=row.country,
        time_zone=row.time_zone,
        primary_currency=row.primary_currency,
        exchange_rate_reference=row.exchange_rate_reference,
        terms_accepted_at=row.terms_accepted_at,
        terms_version=row.terms_version,
        notifications_opt_in=row.notifications_opt_in,
        onboarding_status=OnboardingStatus(row.onboarding_status),
    )


class PostgresSessionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, session: Session) -> None:
        execute_write(self._connection, queries.INSERT_SESSION, asdict(session))

    def find_by_token_hash(self, token_hash: str) -> Session | None:
        row = self._connection.execute(
            text(queries.SELECT_SESSION_BY_TOKEN_HASH), {"token_hash": token_hash}
        ).one_or_none()
        if row is None:
            return None
        return Session(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )

    def touch(self, session_id: uuid.UUID, at: datetime) -> None:
        execute_write(self._connection, queries.TOUCH_SESSION, {"session_id": session_id, "at": at})

    def revoke(self, session_id: uuid.UUID, at: datetime) -> None:
        execute_write(
            self._connection, queries.REVOKE_SESSION, {"session_id": session_id, "at": at}
        )


class PostgresAccountRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, account: Account) -> None:
        execute_write(self._connection, queries.INSERT_ACCOUNT, asdict(account))

    def list_by_user(self, user_id: uuid.UUID) -> list[Account]:
        rows = self._connection.execute(
            text(queries.SELECT_ACCOUNTS_BY_USER), {"user_id": user_id}
        ).all()
        return [
            Account(
                id=row.id,
                user_id=row.user_id,
                name=row.name,
                type=AccountType(row.type),
                currency=row.currency,
                initial_balance=row.initial_balance,
                opened_at=row.opened_at,
            )
            for row in rows
        ]


class PostgresTransactionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def list_by_user(self, user_id: uuid.UUID) -> list[Transaction]:
        rows = self._connection.execute(
            text(queries.SELECT_TRANSACTIONS_BY_USER), {"user_id": user_id}
        ).all()
        return [
            Transaction(
                id=row.id,
                user_id=row.user_id,
                account_id=row.account_id,
                type=TransactionType(row.type),
                amount=row.amount,
                currency=row.currency,
                exchange_rate=row.exchange_rate,
                transaction_date=row.transaction_date,
                duplicate_of=row.duplicate_of,
                deleted_at=row.deleted_at,
            )
            for row in rows
        ]


class PostgresTransferRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def list_by_user(self, user_id: uuid.UUID) -> list[Transfer]:
        rows = self._connection.execute(
            text(queries.SELECT_TRANSFERS_BY_USER), {"user_id": user_id}
        ).all()
        return [
            Transfer(
                id=row.id,
                user_id=row.user_id,
                from_account_id=row.from_account_id,
                from_amount=row.from_amount,
                from_currency=row.from_currency,
                to_account_id=row.to_account_id,
                to_amount=row.to_amount,
                to_currency=row.to_currency,
                exchange_rate=row.exchange_rate,
                transfer_date=row.transfer_date,
                deleted_at=row.deleted_at,
            )
            for row in rows
        ]


class PostgresBudgetPeriodRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, period: BudgetPeriod) -> None:
        execute_write(self._connection, queries.INSERT_BUDGET_PERIOD, asdict(period))


class PostgresFinancialProfileRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, profile: FinancialProfile) -> None:
        execute_write(self._connection, queries.INSERT_FINANCIAL_PROFILE, asdict(profile))


class PostgresFamilyGroupRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, group: FamilyGroup) -> None:
        execute_write(self._connection, queries.INSERT_FAMILY_GROUP, asdict(group))

    def add_membership(self, membership: Membership) -> None:
        execute_write(self._connection, queries.INSERT_MEMBERSHIP, asdict(membership))

    def find_owned_by(self, owner_id: uuid.UUID, name: str) -> FamilyGroup | None:
        row = self._connection.execute(
            text(queries.SELECT_GROUP_OWNED_BY),
            {"owner_id": owner_id, "owner_role": GroupRole.OWNER, "name": name},
        ).one_or_none()
        return None if row is None else FamilyGroup(id=row.id, name=row.name)


class PostgresInboundMessageRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, message: InboundMessage) -> None:
        parameters: dict[str, object] = asdict(message)
        parameters["payload"] = json.dumps({queries.MESSAGE_TEXT_KEY: parameters.pop("text")})
        execute_write(self._connection, queries.INSERT_INBOUND_MESSAGE, parameters)

    def claim_next(self, now: datetime, locked_until: datetime) -> InboundMessage | None:
        row = self._connection.execute(
            text(queries.CLAIM_NEXT_INBOUND_MESSAGE), {"now": now, "locked_until": locked_until}
        ).one_or_none()
        if row is None:
            return None
        return InboundMessage(
            id=row.id,
            provider=Provider(row.provider),
            provider_message_id=row.provider_message_id,
            user_id=row.user_id,
            from_phone=row.from_phone,
            text=row.text,
            quoted_outbound_message_id=row.quoted_outbound_message_id,
            sent_at=row.sent_at,
            status=InboundStatus(row.status),
            attempts=row.attempts,
            locked_until=row.locked_until,
            processed_at=row.processed_at,
        )

    def mark_processed(self, message_id: uuid.UUID, attempts: int, at: datetime) -> bool:
        row = self._connection.execute(
            text(queries.MARK_INBOUND_MESSAGE_PROCESSED),
            {"message_id": message_id, "attempts": attempts, "at": at},
        ).one_or_none()
        return row is not None


class PostgresOutboundMessageRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, message: OutboundMessage) -> None:
        parameters: dict[str, object] = asdict(message)
        parameters["content"] = json.dumps(
            {
                queries.MESSAGE_TEXT_KEY: parameters.pop("text"),
                queries.RESPONSE_KIND_KEY: parameters.pop("response_kind"),
            }
        )
        execute_write(self._connection, queries.INSERT_OUTBOUND_MESSAGE, parameters)


class PostgresChatMessageRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def list_by_user(self, user_id: uuid.UUID, after: uuid.UUID | None) -> list[ChatMessage]:
        rows = self._connection.execute(
            text(queries.SELECT_CHAT_MESSAGES_BY_USER), {"user_id": user_id, "after": after}
        ).all()
        return [
            ChatMessage(
                id=row.id,
                direction=Direction(row.direction),
                text=row.text,
                quoted_message_id=row.quoted_message_id,
                response_kind=_response_kind_from(row.response_kind),
                created_at=row.created_at,
            )
            for row in rows
        ]


def _response_kind_from(value: str | None) -> ResponseKind | None:
    return None if value is None else ResponseKind(value)
