from __future__ import annotations

from app import test_data
from app.domain.entities.user import User
from app.domain.ports.unit_of_work_port import UnitOfWorkPort


class ListTestUsers:
    """The users the development entry of the local environment lets anyone choose.

    A test user is told apart by its invented phone, so a real person who registered against
    a local database is never in the list.
    """

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    def execute(self) -> list[User]:
        with self._unit_of_work as unit_of_work:
            return unit_of_work.users.list_by_phone_prefix(test_data.TEST_PHONE_PREFIX)
