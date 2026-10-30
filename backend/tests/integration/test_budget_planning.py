"""Building and confirming a budget period over HTTP, against PostgreSQL (FEAT-005).

Cases C1-11 to C1-16, C1-18, C1-20 and C1-21 of docs/features/FEAT-005/spec.md, the integration
ones: POST /budget-periods, PUT /budget-periods/{period_id},
POST /budget-periods/{period_id}/confirm, GET /budget-periods and GET /categories. Each test has a
database of its own, with the test data of the script, and talks to the API the way the
dashboard does: it enters through the development entry and asks with the session cookie.

The API runs with a fixed clock, 29 October 2026 at noon in Buenos Aires. The periods the
script creates start on the real day it runs, so each test replaces them with the October one
of Lucía, from 10 October to 9 November 2026, confirmed, with its two limits.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.operator_commands.seed_test_data import main as seed_test_data
from app.settings import load_settings
from tests.support.doubles import FixedClock

pytestmark = pytest.mark.integration

# The cookie is Secure, so the client talks to the API over HTTPS, as a browser does.
BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL, "Content-Type": "application/json"}
TODAY_AT_NOON = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)
SUPERMARKET = "Supermercado"
TRANSPORT = "Transporte"
HEALTH = "Salud"
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
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM budget_period"))
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


def _enter_as(client: TestClient, name: str) -> None:
    """Opens a session for that test user; the client keeps its cookie."""
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    user_id = next(user["id"] for user in users if user["name"] == name)
    response = client.post("/dev/session", json={"user_id": user_id}, headers=SAME_ORIGIN)
    assert response.status_code == 204


def _body(response: Response) -> dict[str, object]:
    """The body, with every number read as an exact Decimal."""
    body: dict[str, object] = json.loads(response.text, parse_float=Decimal)
    return body


def _periods(client: TestClient) -> list[dict[str, object]]:
    response = client.get("/budget-periods")
    assert response.status_code == 200, response.text
    periods: list[dict[str, object]] = _body(response)["budget_periods"]  # type: ignore[assignment]
    return periods


def _user_id(engine: Engine, name: str) -> uuid.UUID:
    with engine.connect() as connection:
        found: uuid.UUID = connection.execute(
            text("SELECT id FROM app_user WHERE name = :name"), {"name": name}
        ).scalar_one()
    return found


def _base_category(engine: Engine, name: str) -> str:
    with engine.connect() as connection:
        found: uuid.UUID = connection.execute(
            text(
                "SELECT id FROM category "
                "WHERE name = :name AND user_id IS NULL AND kind = 'expense'"
            ),
            {"name": name},
        ).scalar_one()
    return str(found)


def _own_category(engine: Engine, user_id: uuid.UUID, name: str, kind: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO category (name, user_id, is_base, kind) "
                "VALUES (:name, :user_id, false, :kind)"
            ),
            {"name": name, "user_id": user_id, "kind": kind},
        )


def _lucia_october(engine: Engine) -> uuid.UUID:
    """The October period of Lucía, confirmed, with Supermercado and Transporte."""
    lucia = _user_id(engine, "Lucía")
    with engine.begin() as connection:
        period: uuid.UUID = connection.execute(
            text(
                "INSERT INTO budget_period (user_id, period_type, period_start, period_end, "
                "primary_currency, estimated_income, status) "
                "VALUES (:user_id, 'monthly', '2026-10-10', '2026-11-09', 'ARS', 1450000.00, "
                "'confirmed') RETURNING id"
            ),
            {"user_id": lucia},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO budget (budget_period_id, category_id, limit_amount) "
                "SELECT :period_id, id, CASE name WHEN :supermarket THEN 300000.00 "
                "ELSE 80000.00 END FROM category "
                "WHERE name IN (:supermarket, :transport) AND user_id IS NULL "
                "AND kind = 'expense'"
            ),
            {"period_id": period, "supermarket": SUPERMARKET, "transport": TRANSPORT},
        )
    return period


def _content(
    engine: Engine,
    start: str,
    income: str,
    limits: dict[str, str],
    *,
    end: str | None = None,
) -> str:
    """A body for POST or PUT, written by hand so that each amount keeps its digits."""
    budgets = ", ".join(
        f'{{"category_id": "{_base_category(engine, name)}", "limit_amount": {amount}}}'
        for name, amount in limits.items()
    )
    period_end = f'"{end}"' if end is not None else "null"
    return (
        f'{{"period_type": "monthly", "period_start": "{start}", "period_end": {period_end}, '
        f'"primary_currency": "ARS", "estimated_income": {income}, "budgets": [{budgets}]}}'
    )


def _create_november(client: TestClient, engine: Engine) -> dict[str, object]:
    """The draft of C1-11, from 10 November to 9 December 2026."""
    response = client.post(
        "/budget-periods",
        content=_content(
            engine, "2026-11-10", "1500000", {SUPERMARKET: "320000", TRANSPORT: "90000"}
        ),
        headers=SAME_ORIGIN,
    )
    assert response.status_code == 201, response.text
    return _body(response)


def _limits(period: dict[str, object]) -> list[tuple[object, object]]:
    budgets: list[dict[str, object]] = period["budgets"]  # type: ignore[assignment]
    return [(budget["category"], budget["limit_amount"]) for budget in budgets]


def test_lucia_creates_the_draft_of_the_next_period(client: TestClient, engine: Engine) -> None:
    # Case C1-11: the answer is the whole period, the same shape as an item of the list.
    _lucia_october(engine)
    _enter_as(client, "Lucía")

    response = client.post(
        "/budget-periods",
        content=_content(
            engine, "2026-11-10", "1500000", {SUPERMARKET: "320000", TRANSPORT: "90000"}
        ),
        headers=SAME_ORIGIN,
    )

    assert response.status_code == 201, response.text
    created = _body(response)
    assert set(created) == PERIOD_FIELDS
    assert {key: value for key, value in created.items() if key not in {"id", "budgets"}} == {
        "family_group_id": None,
        "family_group_name": None,
        "period_type": "monthly",
        "period_start": "2026-11-10",
        "period_end": "2026-12-09",
        "status": "draft",
        "primary_currency": "ARS",
        "estimated_income": Decimal("1500000"),
        "can_edit": True,
        "is_current": False,
    }
    assert _limits(created) == [
        (SUPERMARKET, Decimal("320000")),
        (TRANSPORT, Decimal("90000")),
    ]
    budgets: list[dict[str, object]] = created["budgets"]  # type: ignore[assignment]
    assert all(budget["id"] for budget in budgets)
    with engine.connect() as connection:
        stored = connection.execute(
            text(
                "SELECT p.user_id, p.family_group_id, count(b.id) FROM budget_period p "
                "LEFT JOIN budget b ON b.budget_period_id = p.id WHERE p.id = :id "
                "GROUP BY p.user_id, p.family_group_id"
            ),
            {"id": created["id"]},
        ).one()
    assert tuple(stored) == (_user_id(engine, "Lucía"), None, 2)


def test_the_draft_appears_in_the_list_with_its_limits(client: TestClient, engine: Engine) -> None:
    # Case C1-12.
    october = _lucia_october(engine)
    _enter_as(client, "Lucía")
    draft = _create_november(client, engine)

    periods = _periods(client)

    assert [
        (period["id"], period["status"], period["can_edit"], period["is_current"])
        for period in periods
    ] == [
        (draft["id"], "draft", True, False),
        (str(october), "confirmed", True, True),
    ]
    assert _limits(periods[0]) == [
        (SUPERMARKET, Decimal("320000")),
        (TRANSPORT, Decimal("90000")),
    ]


def test_lucia_changes_the_draft(client: TestClient, engine: Engine) -> None:
    # Case C1-13: the content of C1-06; the answer is the whole period.
    _lucia_october(engine)
    _enter_as(client, "Lucía")
    draft = _create_november(client, engine)

    response = client.put(
        f"/budget-periods/{draft['id']}",
        content=_content(engine, "2026-11-15", "1600000", {SUPERMARKET: "350000", HEALTH: "50000"}),
        headers=SAME_ORIGIN,
    )

    assert response.status_code == 200, response.text
    changed = _body(response)
    assert set(changed) == PERIOD_FIELDS
    assert (
        changed["id"],
        changed["period_start"],
        changed["period_end"],
        changed["status"],
        changed["estimated_income"],
        changed["can_edit"],
    ) == (draft["id"], "2026-11-15", "2026-12-14", "draft", Decimal("1600000"), True)
    assert _limits(changed) == [(HEALTH, Decimal("50000")), (SUPERMARKET, Decimal("350000"))]
    listed = next(period for period in _periods(client) if period["id"] == draft["id"])
    assert listed == changed


def test_lucia_confirms_the_draft(client: TestClient, engine: Engine) -> None:
    # Case C1-14: the answer is the whole period.
    _lucia_october(engine)
    _enter_as(client, "Lucía")
    draft = _create_november(client, engine)

    response = client.post(f"/budget-periods/{draft['id']}/confirm", headers=SAME_ORIGIN)

    assert response.status_code == 200, response.text
    confirmed = _body(response)
    assert set(confirmed) == PERIOD_FIELDS
    assert (
        confirmed["id"],
        confirmed["status"],
        confirmed["period_start"],
        confirmed["period_end"],
        confirmed["estimated_income"],
        confirmed["can_edit"],
    ) == (draft["id"], "confirmed", "2026-11-10", "2026-12-09", Decimal("1500000"), True)
    assert _limits(confirmed) == [(SUPERMARKET, Decimal("320000")), (TRANSPORT, Decimal("90000"))]
    listed = next(period for period in _periods(client) if period["id"] == draft["id"])
    assert listed == confirmed


def test_confirming_it_again_answers_the_same(client: TestClient, engine: Engine) -> None:
    # Case C1-15: the same body as in C1-14, and nothing changes in the database.
    _lucia_october(engine)
    _enter_as(client, "Lucía")
    draft = _create_november(client, engine)
    first = client.post(f"/budget-periods/{draft['id']}/confirm", headers=SAME_ORIGIN)
    assert first.status_code == 200, first.text
    with engine.connect() as connection:
        before = connection.execute(
            text("SELECT * FROM budget_period WHERE id = :id"), {"id": draft["id"]}
        ).one()

    again = client.post(f"/budget-periods/{draft['id']}/confirm", headers=SAME_ORIGIN)

    assert again.status_code == 200, again.text
    assert _body(again) == _body(first)
    with engine.connect() as connection:
        after = connection.execute(
            text("SELECT * FROM budget_period WHERE id = :id"), {"id": draft["id"]}
        ).one()
    assert after == before


def test_the_income_and_the_limits_arrive_with_their_exact_cents(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-16.
    _lucia_october(engine)
    _enter_as(client, "Lucía")
    response = client.post(
        "/budget-periods",
        content=_content(engine, "2026-11-10", "1450000.55", {SUPERMARKET: "300000.10"}),
        headers=SAME_ORIGIN,
    )
    assert response.status_code == 201, response.text
    draft_id = _body(response)["id"]

    listed = next(period for period in _periods(client) if period["id"] == draft_id)

    assert listed["estimated_income"] == Decimal("1450000.55")
    assert _limits(listed) == [(SUPERMARKET, Decimal("300000.10"))]
    assert str(listed["estimated_income"]) == "1450000.55"


def test_lucia_puts_another_income_and_other_limits_on_her_current_period(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-18: the content of C1-17, with the same dates and the same currency.
    october = _lucia_october(engine)
    _enter_as(client, "Lucía")

    response = client.put(
        f"/budget-periods/{october}",
        content=_content(
            engine,
            "2026-10-10",
            "1520000",
            {SUPERMARKET: "310000", HEALTH: "40000"},
            end="2026-11-09",
        ),
        headers=SAME_ORIGIN,
    )

    assert response.status_code == 200, response.text
    listed = next(period for period in _periods(client) if period["id"] == str(october))
    assert (
        listed["status"],
        listed["period_start"],
        listed["period_end"],
        listed["estimated_income"],
    ) == ("confirmed", "2026-10-10", "2026-11-09", Decimal("1520000"))
    assert _limits(listed) == [(HEALTH, Decimal("40000")), (SUPERMARKET, Decimal("310000"))]


def test_lucia_sees_her_expense_categories_base_and_own_by_name(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-20: the 21 expense ones of the base catalog and hers, without the income ones.
    lucia = _user_id(engine, "Lucía")
    _own_category(engine, lucia, "clases de inglés", "expense")
    _own_category(engine, lucia, "Clases particulares", "income")
    with engine.connect() as connection:
        base = [
            name
            for (name,) in connection.execute(
                text("SELECT name FROM category WHERE user_id IS NULL AND kind = 'expense'")
            )
        ]
    assert len(base) == 21
    _enter_as(client, "Lucía")

    response = client.get("/categories")

    assert response.status_code == 200, response.text
    categories: list[dict[str, object]] = _body(response)["categories"]  # type: ignore[assignment]
    assert all(set(category) == {"id", "name", "is_base"} for category in categories)
    names = [category["name"] for category in categories]
    assert names == sorted([*base, "clases de inglés"], key=str.casefold)
    own = names.index("clases de inglés")
    assert names[own - 1 : own + 2] == [
        "Aporte a la actividad",
        "clases de inglés",
        "Comida afuera y delivery",
    ]
    assert [category["is_base"] for category in categories if category["name"] in base] == [
        True
    ] * 21
    assert categories[own]["is_base"] is False
    assert "Clases particulares" not in names


def test_the_own_categories_of_another_user_do_not_appear(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-21.
    _own_category(engine, _user_id(engine, "Pablo"), "Kiosco", "expense")
    _enter_as(client, "Lucía")

    response = client.get("/categories")

    assert response.status_code == 200, response.text
    categories: list[dict[str, object]] = _body(response)["categories"]  # type: ignore[assignment]
    assert "Kiosco" not in [category["name"] for category in categories]
    assert all(category["is_base"] is True for category in categories)
