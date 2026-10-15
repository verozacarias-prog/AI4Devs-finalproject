"""The script of test data for the local environment (docs/operacion.md, section 2).

Cases 9 to 16. Each test runs the command the way a person does, against a database of its own.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import date, datetime
from typing import Self
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.operator_commands.seed_test_data import main
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import Environment
from app.domain.entities.family_group import FamilyGroup, Membership
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from app.domain.use_cases.test_data.seed_test_data import SeedTestData
from app.shared.clock import SystemClock

pytestmark = pytest.mark.integration

OK = 0
REFUSED = 1


@pytest.fixture
def engine(fresh_database_url: str) -> Iterator[Engine]:
    engine = create_engine(fresh_database_url)
    yield engine
    engine.dispose()


def _run(database_url: str, environment: str = "local") -> tuple[int, str]:
    output = io.StringIO()
    code = main({"DATABASE_URL": database_url, "APP_ENV": environment}, output)
    return code, output.getvalue()


def _count(engine: Engine, table: str, where: str = "TRUE") -> int:
    statement = f"SELECT count(*) FROM {table} WHERE {where}"  # noqa: S608
    with engine.connect() as connection:
        return int(connection.execute(text(statement)).scalar_one())


def _snapshot(engine: Engine) -> dict[str, int]:
    tables = ["app_user", "account", "budget_period", "financial_profile", "family_group"]
    return {table: _count(engine, table) for table in [*tables, "user_group"]}


def _today_in_buenos_aires() -> date:
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()


def test_the_script_leaves_the_three_users_with_their_accounts_periods_and_the_group(
    fresh_database_url: str, engine: Engine
) -> None:
    # Case 9, and the database side of case 7.
    code, _ = _run(fresh_database_url)

    assert code == OK
    with engine.connect() as connection:
        users = connection.execute(
            text(
                "SELECT name, whatsapp_phone, terms_version, onboarding_status FROM app_user "
                "ORDER BY whatsapp_phone"
            )
        ).all()
        memberships = connection.execute(
            text(
                "SELECT u.name, g.name, m.role FROM user_group m "
                "JOIN app_user u ON u.id = m.user_id "
                "JOIN family_group g ON g.id = m.family_group_id ORDER BY u.name"
            )
        ).all()
        periods = connection.execute(
            text("SELECT status, period_start, period_end FROM budget_period")
        ).all()
    assert [tuple(user) for user in users] == [
        ("Lucía", "+000000000001", "local-seed-1", "completed"),
        ("Pablo", "+000000000002", "local-seed-1", "completed"),
        ("Sofía", "+000000000003", "local-seed-1", "completed"),
    ]
    assert [tuple(membership) for membership in memberships] == [
        ("Pablo", "Casa", "owner"),
        ("Sofía", "Casa", "member"),
    ]
    assert _snapshot(engine) == {
        "app_user": 3,
        "account": 12,
        "budget_period": 4,
        "financial_profile": 3,
        "family_group": 1,
        "user_group": 2,
    }
    assert _count(engine, "budget_period", "family_group_id IS NOT NULL") == 1
    today = _today_in_buenos_aires()
    assert {(status, start) for status, start, _ in periods} == {("confirmed", today)}
    assert {(end.year, end.month) for _, _, end in periods} == {(today.year, today.month)}
    assert _count(engine, "category", "user_id IS NOT NULL") == 0
    assert _count(engine, "budget") == 0


def test_a_second_run_adds_and_changes_nothing(fresh_database_url: str, engine: Engine) -> None:
    # Case 10.
    _run(fresh_database_url)
    before = _snapshot(engine)

    code, _ = _run(fresh_database_url)

    assert code == OK
    assert _snapshot(engine) == before


def test_the_script_creates_only_the_users_that_are_missing(
    fresh_database_url: str, engine: Engine
) -> None:
    # Case 11. Lucía is already there, with a name of her own to tell her apart.
    clock = SystemClock()
    unit_of_work = SqlAlchemyUnitOfWork(engine)
    with unit_of_work:
        CreateTestUser(clock).execute(
            unit_of_work,
            name="Lucía de antes",
            phone="+000000000001",
            terms_version="local-seed-1",
        )
        unit_of_work.commit()

    code, _ = _run(fresh_database_url)

    assert code == OK
    with engine.connect() as connection:
        names = connection.execute(
            text("SELECT name FROM app_user ORDER BY whatsapp_phone")
        ).scalars()
        assert list(names) == ["Lucía de antes", "Pablo", "Sofía"]
    assert _count(engine, "account") == 12
    assert _count(engine, "family_group") == 1
    assert _count(engine, "user_group") == 2


def test_the_script_does_not_repair_a_user_who_already_exists(
    fresh_database_url: str, engine: Engine
) -> None:
    # Case 12.
    _run(fresh_database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM account WHERE name = 'Efectivo' AND user_id = "
                "(SELECT id FROM app_user WHERE whatsapp_phone = '+000000000001')"
            )
        )

    code, _ = _run(fresh_database_url)

    assert code == OK
    assert _count(engine, "account") == 11


class _GroupsThatFail:
    def add(self, group: FamilyGroup) -> None:
        raise RuntimeError("the database went away")

    def add_membership(self, membership: Membership) -> None:
        raise AssertionError("never reached: the group fails first")

    def find_owned_by(self, owner_id: uuid.UUID, name: str) -> FamilyGroup | None:
        return None


class _FailsAtTheGroup(SqlAlchemyUnitOfWork):
    """The real unit of work, except that creating the group fails."""

    def __enter__(self) -> Self:
        super().__enter__()
        self.family_groups = _GroupsThatFail()
        return self


def test_a_failure_halfway_leaves_nothing_behind(engine: Engine) -> None:
    # Case 13. Lucía and Pablo were already written when the group failed.
    clock = SystemClock()
    seed = SeedTestData(_FailsAtTheGroup(engine), clock, CreateTestUser(clock), Environment.LOCAL)

    with pytest.raises(RuntimeError):
        seed.execute()

    assert _snapshot(engine) == dict.fromkeys(_snapshot(engine), 0)


def test_the_script_reports_how_many_users_it_created_without_phones_or_balances(
    fresh_database_url: str,
) -> None:
    # Case 14.
    _, first = _run(fresh_database_url)
    _, second = _run(fresh_database_url)

    assert "3 created" in first
    assert "0 already existed" in first
    assert "0 created" in second
    assert "3 already existed" in second
    for output in (first, second):
        assert "+000" not in output
        assert "350000" not in output
        assert "350.000" not in output


@pytest.mark.parametrize("environment", ["production", "demo"], ids=["15", "16"])
def test_the_script_refuses_to_run_outside_the_local_environment(
    fresh_database_url: str, engine: Engine, environment: str
) -> None:
    # Cases 15 and 16.
    code, output = _run(fresh_database_url, environment)

    assert code == REFUSED
    assert "local" in output
    assert environment in output
    assert _snapshot(engine) == dict.fromkeys(_snapshot(engine), 0)
