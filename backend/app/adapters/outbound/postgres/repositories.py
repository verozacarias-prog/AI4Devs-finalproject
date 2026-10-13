"""The repositories: each one implements a `*_repository` port over one open connection.

They translate an entity to the parameters of a query and back, and nothing else. The SQL is
in `queries.py`.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import Connection, text

from app.adapters.outbound.postgres import queries
from app.adapters.outbound.postgres.rejections import execute_write
from app.domain.entities.account import Account
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.financial_profile import FinancialProfile
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
        if row is None:
            return None
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
