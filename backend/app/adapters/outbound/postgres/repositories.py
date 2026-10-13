"""The repositories: each one implements a `*_repository` port over one open connection.

They translate an entity to the parameters of a query and back, and nothing else. The SQL is
in `queries.py`.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import Connection, Row, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.account import Account
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.financial_profile import FinancialProfile
from app.domain.entities.session import Session
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
