"""Reading the budget over HTTP, against PostgreSQL (FEAT-004, docs/features/FEAT-004/spec.md).

Cases C1-19 to C1-25 and C2-01 to C2-08, the integration ones: GET /budget-periods, the
summary of a period and GET /budgets/{budget_id}. Each test has a database of its own, with
the test data of the script, and talks to the API the way the dashboard does: it enters
through the development entry and asks with the session cookie.

The API runs with a fixed clock, 25 October 2026 at noon in Buenos Aires. The periods the
script creates start on the real day it runs, so each test replaces them with its own, and the
movements are written with SQL.
"""

from __future__ import annotations

import io
import json
import re
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.operator_commands.seed_test_data import main as seed_test_data
from app.settings import load_settings
from tests.support.doubles import FixedClock

pytestmark = pytest.mark.integration

# The cookie is Secure, so the client talks to the API over HTTPS, as a browser does.
BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")
TODAY_AT_NOON = datetime(2026, 10, 25, 15, 0, tzinfo=UTC)
OCTOBER_1 = date(2026, 10, 1)
OCTOBER_5 = date(2026, 10, 5)
OCTOBER_10 = date(2026, 10, 10)
OCTOBER_12 = date(2026, 10, 12)
OCTOBER_18 = date(2026, 10, 18)
OCTOBER_20 = date(2026, 10, 20)
OCTOBER_31 = date(2026, 10, 31)
NOVEMBER_9 = date(2026, 11, 9)
SUPERMARKET = "Supermercado"
TRANSPORT = "Transporte"
EATING_OUT = "Comida afuera y delivery"
SALARY = "Sueldo"
REFUNDS = "Devoluciones y reintegros"
PERIOD_FIELDS = {
    "id",
    "family_group_id",
    "family_group_name",
    "period_type",
    "period_start",
    "period_end",
    "status",
    "primary_currency",
    "estimated_income",
    "can_edit",
    "is_current",
    "budgets",
}
MOVEMENT_FIELDS = {
    "id",
    "transaction_date",
    "description",
    "type",
    "amount",
    "currency",
    "budget_amount",
    "exchange_rate",
    "account",
    "source",
}


@pytest.fixture
def seeded_database_url(fresh_database_url: str) -> str:
    code = seed_test_data(
        {"DATABASE_URL": fresh_database_url, "APP_ENV": "local"}, io.StringIO(), io.StringIO()
    )
    assert code == 0, "the test data script failed"
    return fresh_database_url


@pytest.fixture
def engine(seeded_database_url: str) -> Iterator[Engine]:
    engine = create_engine(seeded_database_url)
    _replace_the_periods_of_the_script(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(seeded_database_url: str, engine: Engine) -> TestClient:
    environ = {
        "DATABASE_URL": seeded_database_url,
        "APP_ENV": "local",
        "APP_VERSION": "test",
        "DEV_ENTRY_ENABLED": "true",
    }
    app = create_app(
        load_settings(environ), log_stream=io.StringIO(), clock=FixedClock(TODAY_AT_NOON)
    )
    return TestClient(app, base_url=BASE_URL)


def _replace_the_periods_of_the_script(engine: Engine) -> None:
    """No periods are left, and every account was opened on 1 October, at noon."""
    opened_at = datetime.combine(OCTOBER_1, time(12), tzinfo=BUENOS_AIRES)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM budget_period"))
        connection.execute(text("UPDATE account SET created_at = :at"), {"at": opened_at})


def _enter_as(client: TestClient, name: str) -> None:
    """Opens a session for that test user; the client keeps its cookie."""
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    user_id = next(user["id"] for user in users if user["name"] == name)
    response = client.post("/dev/session", json={"user_id": user_id}, headers=SAME_ORIGIN)
    assert response.status_code == 204


def _get(client: TestClient, path: str) -> dict[str, object]:
    """The body of a 200, with every number read as an exact Decimal."""
    response = client.get(path)
    assert response.status_code == 200, response.text
    body: dict[str, object] = json.loads(response.text, parse_float=Decimal)
    return body


def _periods(client: TestClient) -> list[dict[str, object]]:
    body = _get(client, "/budget-periods")
    assert list(body) == ["budget_periods"]
    periods: list[dict[str, object]] = body["budget_periods"]  # type: ignore[assignment]
    assert all(set(period) == PERIOD_FIELDS for period in periods)
    return periods


def _user_id(engine: Engine, name: str) -> uuid.UUID:
    with engine.connect() as connection:
        found: uuid.UUID = connection.execute(
            text("SELECT id FROM app_user WHERE name = :name"), {"name": name}
        ).scalar_one()
    return found


def _group_id(engine: Engine, name: str) -> uuid.UUID:
    with engine.connect() as connection:
        found: uuid.UUID = connection.execute(
            text("SELECT id FROM family_group WHERE name = :name"), {"name": name}
        ).scalar_one()
    return found


def _period(
    engine: Engine,
    start: date,
    end: date,
    *,
    user_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    status: str = "confirmed",
    estimated_income: str = "0",
) -> uuid.UUID:
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO budget_period (user_id, family_group_id, period_type, "
                "period_start, period_end, primary_currency, estimated_income, status) "
                "VALUES (:user_id, :group_id, 'monthly', :start, :end, 'ARS', "
                ":estimated_income, :status) RETURNING id"
            ),
            {
                "user_id": user_id,
                "group_id": group_id,
                "start": start,
                "end": end,
                "estimated_income": Decimal(estimated_income),
                "status": status,
            },
        ).scalar_one()
    return created


def _limit(engine: Engine, period_id: uuid.UUID, category: str, amount: str) -> uuid.UUID:
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO budget (budget_period_id, category_id, limit_amount) "
                "SELECT :period_id, id, :amount FROM category "
                "WHERE name = :category AND user_id IS NULL AND kind = 'expense' "
                "RETURNING id"
            ),
            {"period_id": period_id, "category": category, "amount": Decimal(amount)},
        ).scalar_one()
    return created


def _movement(
    engine: Engine,
    user_id: uuid.UUID,
    period_id: uuid.UUID,
    *,
    account: str,
    type: str,
    category: str,
    amount: str,
    day: date,
    currency: str | None = None,
    exchange_rate: str | None = None,
    description: str | None = None,
    deleted: bool = False,
    duplicate_of: uuid.UUID | None = None,
    refund_of: uuid.UUID | None = None,
) -> uuid.UUID:
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO transaction (user_id, account_id, budget_period_id, category_id, "
                "amount, currency, exchange_rate, type, source, description, "
                "transaction_date, duplicate_of, refund_of, deleted_at) "
                "SELECT :user_id, a.id, :period_id, c.id, :amount, "
                "COALESCE(:currency, a.currency), :exchange_rate, :type, 'manual', "
                ":description, :day, :duplicate_of, :refund_of, "
                "CASE WHEN :deleted THEN now() END "
                "FROM account a, category c "
                "WHERE a.user_id = :user_id AND a.name = :account "
                "AND c.name = :category AND c.user_id IS NULL AND c.kind = :type "
                "RETURNING id"
            ),
            {
                "user_id": user_id,
                "period_id": period_id,
                "account": account,
                "category": category,
                "amount": Decimal(amount),
                "currency": currency,
                "exchange_rate": Decimal(exchange_rate) if exchange_rate is not None else None,
                "type": type,
                "description": description,
                "day": day,
                "duplicate_of": duplicate_of,
                "refund_of": refund_of,
                "deleted": deleted,
            },
        ).scalar_one()
    return created


def _lucia_october(engine: Engine) -> tuple[uuid.UUID, uuid.UUID, dict[str, uuid.UUID]]:
    """Lucía, her October period with its two limits, and the id of each limit."""
    lucia = _user_id(engine, "Lucía")
    period = _period(engine, OCTOBER_10, NOVEMBER_9, user_id=lucia, estimated_income="1450000.00")
    limits = {
        SUPERMARKET: _limit(engine, period, SUPERMARKET, "300000.00"),
        TRANSPORT: _limit(engine, period, TRANSPORT, "80000.00"),
    }
    return lucia, period, limits


def test_lucia_sees_her_periods_in_order_and_with_their_limits(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-19.
    lucia, october, _ = _lucia_october(engine)
    november = _period(
        engine,
        date(2026, 11, 10),
        date(2026, 12, 9),
        user_id=lucia,
        status="draft",
        estimated_income="1500000.00",
    )
    _limit(engine, november, TRANSPORT, "90000.00")
    _enter_as(client, "Lucía")

    periods = _periods(client)

    assert [
        (
            period["id"],
            period["status"],
            period["is_current"],
            period["family_group_id"],
            period["family_group_name"],
            period["can_edit"],
        )
        for period in periods
    ] == [
        (str(november), "draft", False, None, None, True),
        (str(october), "confirmed", True, None, None, True),
    ]
    assert periods[0]["estimated_income"] == Decimal("1500000.00")
    assert [(b["category"], b["limit_amount"]) for b in periods[0]["budgets"]] == [  # type: ignore[attr-defined]
        (TRANSPORT, Decimal("90000.00"))
    ]
    assert [(b["category"], b["limit_amount"]) for b in periods[1]["budgets"]] == [  # type: ignore[attr-defined]
        (SUPERMARKET, Decimal("300000.00")),
        (TRANSPORT, Decimal("80000.00")),
    ]


def test_pablo_sees_his_period_and_the_one_of_casa_and_can_edit_them(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-20.
    pablo = _user_id(engine, "Pablo")
    home = _group_id(engine, "Casa")
    own = _period(engine, OCTOBER_1, OCTOBER_31, user_id=pablo)
    of_home = _period(engine, OCTOBER_1, OCTOBER_31, group_id=home)
    _enter_as(client, "Pablo")

    periods = _periods(client)

    assert [
        (
            period["id"],
            period["family_group_id"],
            period["family_group_name"],
            period["is_current"],
            period["can_edit"],
        )
        for period in periods
    ] == [
        (str(own), None, None, True, True),
        (str(of_home), str(home), "Casa", True, True),
    ]


def test_sofia_sees_the_period_of_casa_and_cannot_edit_it(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-21.
    home = _group_id(engine, "Casa")
    of_home = _period(engine, OCTOBER_1, OCTOBER_31, group_id=home)
    _limit(engine, of_home, SUPERMARKET, "500000.00")
    _enter_as(client, "Sofía")

    listed = next(period for period in _periods(client) if period["id"] == str(of_home))
    summary = _get(client, f"/budget-periods/{of_home}/summary")

    assert listed["family_group_name"] == "Casa"
    assert listed["can_edit"] is False
    assert [
        (c["category"], c["spent_amount"], c["limit_amount"])
        for c in summary["categories"]  # type: ignore[attr-defined]
    ] == [(SUPERMARKET, Decimal("0.00"), Decimal("500000.00"))]


def test_the_summary_of_the_period_of_lucia(client: TestClient, engine: Engine) -> None:
    # Case C1-22: 214.500 + 12.000 + 38.500 = 265.000 spent.
    lucia, period, limits = _lucia_october(engine)
    _movement(
        engine,
        lucia,
        period,
        account="Galicia pesos",
        type="income",
        category=SALARY,
        amount="1200000.00",
        day=OCTOBER_12,
    )
    _movement(
        engine,
        lucia,
        period,
        account="Galicia pesos",
        type="expense",
        category=SUPERMARKET,
        amount="154500.00",
        day=OCTOBER_12,
    )
    _movement(
        engine,
        lucia,
        period,
        account="Galicia USD",
        type="expense",
        category=SUPERMARKET,
        amount="50.00",
        exchange_rate="1200",
        day=OCTOBER_18,
    )
    _movement(
        engine,
        lucia,
        period,
        account="Galicia pesos",
        type="expense",
        category=TRANSPORT,
        amount="12000.00",
        day=OCTOBER_12,
    )
    _movement(
        engine,
        lucia,
        period,
        account="Galicia pesos",
        type="expense",
        category=EATING_OUT,
        amount="38500.00",
        day=OCTOBER_12,
    )
    _enter_as(client, "Lucía")

    summary = _get(client, f"/budget-periods/{period}/summary")

    assert summary["budget_period_id"] == str(period)
    assert summary["primary_currency"] == "ARS"
    assert summary["estimated_income"] == Decimal("1450000.00")
    assert summary["actual_income"] == Decimal("1200000.00")
    assert summary["total_spent"] == Decimal("265000.00")
    assert summary["categories"] == [
        {
            "category": EATING_OUT,
            "budget_id": None,
            "limit_amount": None,
            "spent_amount": Decimal("38500.00"),
            "used_percentage": None,
        },
        {
            "category": SUPERMARKET,
            "budget_id": str(limits[SUPERMARKET]),
            "limit_amount": Decimal("300000.00"),
            "spent_amount": Decimal("214500.00"),
            "used_percentage": Decimal("71.5"),
        },
        {
            "category": TRANSPORT,
            "budget_id": str(limits[TRANSPORT]),
            "limit_amount": Decimal("80000.00"),
            "spent_amount": Decimal("12000.00"),
            "used_percentage": Decimal("15.0"),
        },
    ]


def test_the_detail_of_supermercado_with_its_movements(client: TestClient, engine: Engine) -> None:
    # Case C1-23.
    lucia, period, limits = _lucia_october(engine)
    in_pesos = _movement(
        engine,
        lucia,
        period,
        account="Galicia pesos",
        type="expense",
        category=SUPERMARKET,
        amount="154500.00",
        day=OCTOBER_12,
    )
    in_dollars = _movement(
        engine,
        lucia,
        period,
        account="Galicia USD",
        type="expense",
        category=SUPERMARKET,
        amount="50.00",
        exchange_rate="1200",
        description="super",
        day=OCTOBER_18,
    )
    _enter_as(client, "Lucía")

    status = _get(client, f"/budgets/{limits[SUPERMARKET]}")

    assert status["id"] == str(limits[SUPERMARKET])
    assert status["budget_period_id"] == str(period)
    assert status["category"] == SUPERMARKET
    assert status["primary_currency"] == "ARS"
    assert status["limit_amount"] == Decimal("300000.00")
    assert status["spent_amount"] == Decimal("214500.00")
    assert status["used_percentage"] == Decimal("71.5")
    movements: list[dict[str, object]] = status["transactions"]  # type: ignore[assignment]
    assert all(set(movement) == MOVEMENT_FIELDS for movement in movements)
    assert movements == [
        {
            "id": str(in_dollars),
            "transaction_date": "2026-10-18",
            "description": "super",
            "type": "expense",
            "amount": Decimal("50.00"),
            "currency": "USD",
            "budget_amount": Decimal("60000.00"),
            "exchange_rate": 1200,
            "account": "Galicia USD",
            "source": "manual",
        },
        {
            "id": str(in_pesos),
            "transaction_date": "2026-10-12",
            "description": None,
            "type": "expense",
            "amount": Decimal("154500.00"),
            "currency": "ARS",
            "budget_amount": Decimal("154500.00"),
            "exchange_rate": None,
            "account": "Galicia pesos",
            "source": "manual",
        },
    ]


def test_the_database_query_follows_the_rules_of_what_is_spent(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-24: 100.000 − 30.000.
    lucia, period, limits = _lucia_october(engine)
    september = _period(engine, date(2026, 9, 10), date(2026, 10, 9), user_id=lucia)
    original = _movement(
        engine,
        lucia,
        period,
        type="expense",
        category=SUPERMARKET,
        amount="100000.00",
        account="Galicia pesos",
        day=OCTOBER_12,
    )
    _movement(
        engine,
        lucia,
        period,
        type="expense",
        category=SUPERMARKET,
        amount="40000.00",
        deleted=True,
        account="Galicia pesos",
        day=OCTOBER_12,
    )
    _movement(
        engine,
        lucia,
        period,
        type="expense",
        category=SUPERMARKET,
        amount="25000.00",
        duplicate_of=original,
        account="Galicia pesos",
        day=OCTOBER_12,
    )
    refund = _movement(
        engine,
        lucia,
        period,
        account="Galicia pesos",
        type="income",
        category=REFUNDS,
        amount="30000.00",
        refund_of=original,
        day=OCTOBER_20,
    )
    _movement(
        engine,
        lucia,
        september,
        account="Galicia pesos",
        type="expense",
        category=SUPERMARKET,
        amount="50000.00",
        day=OCTOBER_5,
    )
    _movement(
        engine,
        lucia,
        period,
        type="expense",
        category=TRANSPORT,
        amount="12000.00",
        account="Galicia pesos",
        day=OCTOBER_12,
    )
    _enter_as(client, "Lucía")

    status = _get(client, f"/budgets/{limits[SUPERMARKET]}")

    assert status["spent_amount"] == Decimal("70000.00")
    assert [
        (movement["id"], movement["type"])
        for movement in status["transactions"]  # type: ignore[attr-defined]
    ] == [(str(refund), "income"), (str(original), "expense")]


def test_the_amounts_and_the_percentage_arrive_with_their_exact_digits(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-25: 24.716,04 / 300.000 × 100 = 8,238…, and 80.040 / 80.000 × 100 = 100,05.
    lucia, period, _ = _lucia_october(engine)
    for _ in range(2):
        _movement(
            engine,
            lucia,
            period,
            account="Galicia USD",
            type="expense",
            category=SUPERMARKET,
            amount="10.01",
            exchange_rate="1234.5678",
            day=OCTOBER_18,
        )
    _movement(
        engine,
        lucia,
        period,
        account="Galicia pesos",
        type="expense",
        category=TRANSPORT,
        amount="80040.00",
        day=OCTOBER_12,
    )
    _enter_as(client, "Lucía")

    response = client.get(f"/budget-periods/{period}/summary")

    assert response.status_code == 200
    assert re.search(r'"spent_amount":\s*24716\.04[,}\s]', response.text), response.text
    assert re.search(r'"used_percentage":\s*8\.2[,}\s]', response.text), response.text
    assert re.search(r'"spent_amount":\s*80040\.00[,}\s]', response.text), response.text
    assert re.search(r'"used_percentage":\s*100\.1[,}\s]', response.text), response.text


# Cut 2: errors and empty states.

NOVEMBER_10 = date(2026, 11, 10)
DECEMBER_9 = date(2026, 12, 9)
NOT_A_UUID = "abc"


def _status_and_body(client: TestClient, path: str) -> tuple[int, dict[str, object]]:
    response = client.get(path)
    body: dict[str, object] = response.json()
    return response.status_code, body


def _pablo_october(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    """An individual period of Pablo, with a limit in Supermercado: its id and the limit's."""
    pablo = _user_id(engine, "Pablo")
    period = _period(engine, OCTOBER_10, NOVEMBER_9, user_id=pablo)
    return period, _limit(engine, period, SUPERMARKET, "200000.00")


def test_without_a_session_the_three_endpoints_answer_401(
    client: TestClient, engine: Engine
) -> None:
    # Case C2-01. The client never enters, so it has no session cookie.
    _, period, limits = _lucia_october(engine)

    answers = [
        _status_and_body(client, path)
        for path in (
            "/budget-periods",
            f"/budget-periods/{period}/summary",
            f"/budgets/{limits[SUPERMARKET]}",
        )
    ]

    assert answers == [(401, {"error": "unauthorized"})] * 3


def test_the_summary_of_another_users_period_answers_404(
    client: TestClient, engine: Engine
) -> None:
    # Case C2-02.
    of_pablo, _ = _pablo_october(engine)
    _enter_as(client, "Lucía")

    another = _status_and_body(client, f"/budget-periods/{of_pablo}/summary")
    nobodys = _status_and_body(client, f"/budget-periods/{uuid.uuid4()}/summary")

    assert another == (404, {"error": "not_found"})
    assert nobodys == another


def test_the_detail_of_another_users_limit_answers_404(client: TestClient, engine: Engine) -> None:
    # Case C2-03.
    _, limit_of_pablo = _pablo_october(engine)
    _enter_as(client, "Lucía")

    assert _status_and_body(client, f"/budgets/{limit_of_pablo}") == (
        404,
        {"error": "not_found"},
    )


def test_who_is_not_a_member_of_a_group_does_not_see_its_periods(
    client: TestClient, engine: Engine
) -> None:
    # Case C2-04.
    _, own, _ = _lucia_october(engine)
    of_home = _period(engine, OCTOBER_10, NOVEMBER_9, group_id=_group_id(engine, "Casa"))
    limit_of_home = _limit(engine, of_home, SUPERMARKET, "500000.00")
    _enter_as(client, "Lucía")

    assert [period["id"] for period in _periods(client)] == [str(own)]
    assert _status_and_body(client, f"/budget-periods/{of_home}/summary")[0] == 404
    assert _status_and_body(client, f"/budgets/{limit_of_home}")[0] == 404


def test_who_left_a_group_sees_only_the_periods_of_their_membership(
    client: TestClient, engine: Engine
) -> None:
    # Case C2-05. Sofía joined "Casa" on 1 October and left it on 15 October.
    home = _group_id(engine, "Casa")
    october = _period(engine, OCTOBER_10, NOVEMBER_9, group_id=home)
    november = _period(engine, NOVEMBER_10, DECEMBER_9, group_id=home, status="draft")
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE user_group SET joined_at = :joined, left_at = :left "
                "WHERE family_group_id = :home "
                "AND user_id = (SELECT id FROM app_user WHERE name = 'Sofía')"
            ),
            {
                "joined": datetime.combine(OCTOBER_1, time(12), tzinfo=BUENOS_AIRES),
                "left": datetime.combine(date(2026, 10, 15), time(12), tzinfo=BUENOS_AIRES),
                "home": home,
            },
        )
    _enter_as(client, "Sofía")

    periods = _periods(client)

    assert [(period["id"], period["can_edit"]) for period in periods] == [(str(october), False)]
    assert _status_and_body(client, f"/budget-periods/{october}/summary")[0] == 200
    assert _status_and_body(client, f"/budget-periods/{november}/summary")[0] == 404


def test_an_id_that_is_not_a_uuid_answers_422(client: TestClient, engine: Engine) -> None:
    # Case C2-06.
    _enter_as(client, "Lucía")

    for path in (f"/budget-periods/{NOT_A_UUID}/summary", f"/budgets/{NOT_A_UUID}"):
        status, body = _status_and_body(client, path)
        assert status == 422, path
        assert set(body) >= {"error"}, path


def test_a_period_without_limits_or_movements_is_empty_not_a_failure(
    client: TestClient, engine: Engine
) -> None:
    # Case C2-07.
    period = _period(engine, OCTOBER_10, NOVEMBER_9, user_id=_user_id(engine, "Lucía"))
    _enter_as(client, "Lucía")

    summary = _get(client, f"/budget-periods/{period}/summary")

    assert (
        summary["estimated_income"],
        summary["actual_income"],
        summary["total_spent"],
        summary["categories"],
    ) == (Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), [])


def test_a_user_without_periods_gets_an_empty_list(client: TestClient, engine: Engine) -> None:
    # Case C2-08. The fixture leaves nobody with a period.
    _enter_as(client, "Lucía")

    assert _get(client, "/budget-periods") == {"budget_periods": []}
