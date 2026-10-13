"""Doubles of the ports, for the unit tests of the use cases: nothing here touches a database."""

from __future__ import annotations

import uuid
from datetime import datetime
from types import TracebackType
from typing import Self

from app.domain.entities.account import Account
from app.domain.entities.budget_period import BudgetPeriod
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.financial_profile import FinancialProfile
from app.domain.entities.user import User


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


class InMemoryAccounts:
    def __init__(self) -> None:
        self.added: list[Account] = []

    def add(self, account: Account) -> None:
        self.added.append(account)


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


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.users = InMemoryUsers()
        self.accounts = InMemoryAccounts()
        self.budget_periods = InMemoryBudgetPeriods()
        self.financial_profiles = InMemoryFinancialProfiles()
        self.family_groups = InMemoryFamilyGroups()
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
