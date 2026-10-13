from __future__ import annotations

import uuid
from dataclasses import dataclass

from app import test_data
from app.constants import Environment
from app.domain.entities.budget_period import first_period
from app.domain.entities.family_group import FamilyGroup, GroupRole, Membership
from app.domain.entities.user import User
from app.domain.errors import TestDataNotAllowedError
from app.domain.local_date import local_today
from app.domain.ports.unit_of_work_port import UnitOfWorkPort
from app.domain.use_cases.create_test_user import CreateTestUser
from app.shared.clock import Clock


@dataclass(frozen=True)
class SeedReport:
    created: int
    existing: int


class SeedTestData:
    """Creates the test users of the local environment, and their group.

    It can run any number of times: a user who already exists, recognised by the phone, is
    neither touched nor repaired, and the missing ones are created. Everything happens in one
    transaction, so a failure leaves nothing behind.
    """

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        clock: Clock,
        create_test_user: CreateTestUser,
        environment: Environment,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._create_test_user = create_test_user
        self._environment = environment

    def execute(self) -> SeedReport:
        # In demo a user is born when a person accepts the test notice, never from a script.
        if self._environment is not Environment.LOCAL:
            raise TestDataNotAllowedError(self._environment)
        with self._unit_of_work as unit_of_work:
            users: dict[str, User] = {}
            created: set[str] = set()
            for wanted in test_data.LOCAL_TEST_USERS:
                user = unit_of_work.users.find_by_phone(wanted.phone)
                if user is None:
                    user = self._create_test_user.execute(
                        unit_of_work,
                        name=wanted.name,
                        phone=wanted.phone,
                        terms_version=test_data.LOCAL_TERMS_VERSION,
                    )
                    created.add(wanted.phone)
                users[wanted.phone] = user
            self._ensure_group(unit_of_work, users, created)
            unit_of_work.commit()
        return SeedReport(created=len(created), existing=len(users) - len(created))

    def _ensure_group(
        self, unit_of_work: UnitOfWorkPort, users: dict[str, User], created: set[str]
    ) -> None:
        owner = users[test_data.LOCAL_GROUP_OWNER.phone]
        now = self._clock.now()
        group = unit_of_work.family_groups.find_owned_by(owner.id, test_data.LOCAL_GROUP_NAME)
        group_is_new = group is None
        if group is None:
            if owner.whatsapp_phone not in created:
                # The owner was already there without the group: an existing user is not repaired.
                return
            group = FamilyGroup(id=uuid.uuid4(), name=test_data.LOCAL_GROUP_NAME)
            unit_of_work.family_groups.add(group)
            unit_of_work.family_groups.add_membership(
                Membership(owner.id, group.id, GroupRole.OWNER, now)
            )
            # A group is born with its first period, like a user (domain rules, § 10).
            today = local_today(now, owner.time_zone)
            unit_of_work.budget_periods.add(
                first_period(family_group_id=group.id, currency=owner.primary_currency, today=today)
            )
        for wanted in test_data.LOCAL_GROUP_MEMBERS:
            if group_is_new or wanted.phone in created:
                member = users[wanted.phone]
                unit_of_work.family_groups.add_membership(
                    Membership(member.id, group.id, GroupRole.MEMBER, now)
                )
