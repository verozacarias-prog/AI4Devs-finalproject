"""GET /accounts over HTTP, against PostgreSQL (FEAT-001, docs/features/FEAT-001/spec.md).

Cases C1-14 to C1-19 and C1-23, the integration ones, and C3-01, the logs of the request.
Each test has a database of its own, with the test data of the script, and talks to the API
the way the dashboard does: it enters through the development entry and asks for the accounts
with the session cookie.

"Today" here is the real today in Buenos Aires, because the API runs with the clock of the
machine. The movements are written with SQL, as the registration flow does not exist yet.
"""

from __future__ import annotations

import io
import json
import re
import uuid
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.operator_commands.seed_test_data import main as seed_test_data
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.use_cases.test_data.create_test_user import CreateTestUser
from app.settings import load_settings
from app.shared.clock import SystemClock

pytestmark = pytest.mark.integration

# The cookie is Secure, so the client talks to the API over HTTPS, as a browser does.
BASE_URL = "https://testserver"
SAME_ORIGIN = {"Origin": BASE_URL}
BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")
ACCOUNT_FIELDS = {"id", "name", "type", "currency", "balance", "balance_kind"}
EXPENSE_CATEGORY = "Supermercado"
INCOME_CATEGORY = "Otros ingresos"
OCTOBER_1 = date(2026, 10, 1)
OCTOBER_10 = date(2026, 10, 10)


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
    yield engine
    engine.dispose()


@pytest.fixture
def client(seeded_database_url: str) -> TestClient:
    environ = {
        "DATABASE_URL": seeded_database_url,
        "APP_ENV": "local",
        "APP_VERSION": "test",
        "DEV_ENTRY_ENABLED": "true",
    }
    app = create_app(load_settings(environ), log_stream=io.StringIO())
    return TestClient(app, base_url=BASE_URL)


def _today() -> date:
    return datetime.now(BUENOS_AIRES).date()


def _enter_as(client: TestClient, name: str) -> None:
    """Opens a session for that test user; the client keeps its cookie."""
    users: list[dict[str, str]] = client.get("/dev/users").json()["users"]
    user_id = next(user["id"] for user in users if user["name"] == name)
    response = client.post("/dev/session", json={"user_id": user_id}, headers=SAME_ORIGIN)
    assert response.status_code == 204


def _accounts(client: TestClient) -> list[dict[str, object]]:
    """The accounts of the answer, with every amount read as an exact Decimal."""
    response = client.get("/accounts")
    assert response.status_code == 200
    body = json.loads(response.text, parse_float=Decimal)
    assert list(body) == ["accounts"]
    accounts: list[dict[str, object]] = body["accounts"]
    return accounts


def _balances(accounts: list[dict[str, object]]) -> dict[object, object]:
    return {account["name"]: account["balance"] for account in accounts}


def _user_id(engine: Engine, name: str) -> uuid.UUID:
    with engine.connect() as connection:
        found: uuid.UUID = connection.execute(
            text("SELECT id FROM app_user WHERE name = :name"), {"name": name}
        ).scalar_one()
    return found


def _account_id(engine: Engine, user_id: uuid.UUID, name: str) -> uuid.UUID:
    with engine.connect() as connection:
        found: uuid.UUID = connection.execute(
            text("SELECT id FROM account WHERE user_id = :user_id AND name = :name"),
            {"user_id": user_id, "name": name},
        ).scalar_one()
    return found


def _add_account(
    engine: Engine,
    user_id: uuid.UUID,
    name: str,
    *,
    type: str,
    currency: str,
    initial_balance: str,
) -> uuid.UUID:
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO account (user_id, name, type, currency, initial_balance) "
                "VALUES (:user_id, :name, :type, :currency, :initial_balance) RETURNING id"
            ),
            {
                "user_id": user_id,
                "name": name,
                "type": type,
                "currency": currency,
                "initial_balance": Decimal(initial_balance),
            },
        ).scalar_one()
    return created


def _open_accounts_on(engine: Engine, user_id: uuid.UUID, day: date) -> None:
    """Moves the opening of every account of the user back to that day, at noon."""
    opened_at = datetime.combine(day, time(12), tzinfo=BUENOS_AIRES)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE account SET created_at = :opened_at WHERE user_id = :user_id"),
            {"opened_at": opened_at, "user_id": user_id},
        )


def _period_id(engine: Engine, user_id: uuid.UUID, day: date) -> uuid.UUID:
    """The confirmed individual period that covers that day; one is added if none does."""
    with engine.begin() as connection:
        found = connection.execute(
            text(
                "SELECT id FROM budget_period WHERE user_id = :user_id "
                "AND status = 'confirmed' AND :day BETWEEN period_start AND period_end"
            ),
            {"user_id": user_id, "day": day},
        ).scalar_one_or_none()
        if found is None:
            found = connection.execute(
                text(
                    "INSERT INTO budget_period (user_id, period_type, period_start, "
                    "period_end, primary_currency, status) "
                    "SELECT :user_id, 'custom', :day, :day, primary_currency, 'confirmed' "
                    "FROM app_user WHERE id = :user_id RETURNING id"
                ),
                {"user_id": user_id, "day": day},
            ).scalar_one()
    period: uuid.UUID = found
    return period


def _movement(
    engine: Engine,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    type: str,
    amount: str,
    day: date,
    deleted: bool = False,
    duplicate_of: uuid.UUID | None = None,
) -> uuid.UUID:
    category = EXPENSE_CATEGORY if type == "expense" else INCOME_CATEGORY
    period_id = _period_id(engine, user_id, day)
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO transaction (user_id, account_id, budget_period_id, category_id, "
                "amount, currency, type, source, transaction_date, duplicate_of, deleted_at) "
                "SELECT :user_id, a.id, :period_id, c.id, :amount, a.currency, :type, "
                "'manual', :day, :duplicate_of, CASE WHEN :deleted THEN now() END "
                "FROM account a, category c "
                "WHERE a.id = :account_id AND c.name = :category AND c.user_id IS NULL "
                "RETURNING id"
            ),
            {
                "user_id": user_id,
                "account_id": account_id,
                "period_id": period_id,
                "category": category,
                "amount": Decimal(amount),
                "type": type,
                "day": day,
                "duplicate_of": duplicate_of,
                "deleted": deleted,
            },
        ).scalar_one()
    return created


def _transfer(
    engine: Engine,
    user_id: uuid.UUID,
    from_account_id: uuid.UUID,
    to_account_id: uuid.UUID,
    *,
    amount: str,
    day: date,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO transfer (user_id, from_account_id, from_amount, from_currency, "
                "to_account_id, to_amount, to_currency, transfer_date, source) "
                "SELECT :user_id, f.id, :amount, f.currency, t.id, :amount, t.currency, "
                ":day, 'manual' FROM account f, account t "
                "WHERE f.id = :from_account_id AND t.id = :to_account_id"
            ),
            {
                "user_id": user_id,
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount": Decimal(amount),
                "day": day,
            },
        )


def _add_test_user(engine: Engine, name: str, phone: str) -> uuid.UUID:
    """A test user of the template, without the accounts of the template."""
    unit_of_work = SqlAlchemyUnitOfWork(engine)
    with unit_of_work:
        user = CreateTestUser(SystemClock()).execute(
            unit_of_work, name=name, phone=phone, terms_version="local-seed-1"
        )
        unit_of_work.commit()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM account WHERE user_id = :id"), {"id": user.id})
    return user.id


def test_lucia_sees_her_four_accounts(client: TestClient) -> None:
    # Case C1-14.
    _enter_as(client, "Lucía")

    accounts = _accounts(client)

    assert len(accounts) == 4
    assert all(set(account) == ACCOUNT_FIELDS for account in accounts)
    by_name = {account["name"]: account for account in accounts}
    assert {name: (a["type"], a["currency"], a["balance"]) for name, a in by_name.items()} == {
        "Galicia pesos": ("bank_account", "ARS", Decimal("350000.00")),
        "Mercado Pago": ("digital_wallet", "ARS", Decimal("80000.00")),
        "Efectivo": ("cash", "ARS", Decimal("25000.00")),
        "Galicia USD": ("bank_account", "USD", Decimal("500.00")),
    }
    assert all(account["balance_kind"] == "balance" for account in accounts)
    assert len({account["id"] for account in accounts}) == 4


def test_a_stored_expense_lowers_its_account_and_no_other(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-15: 350.000 − 3.500.
    lucia = _user_id(engine, "Lucía")
    galicia = _account_id(engine, lucia, "Galicia pesos")
    _movement(engine, lucia, galicia, type="expense", amount="3500.00", day=_today())
    _enter_as(client, "Lucía")

    assert _balances(_accounts(client)) == {
        "Galicia pesos": Decimal("346500.00"),
        "Mercado Pago": Decimal("80000.00"),
        "Efectivo": Decimal("25000.00"),
        "Galicia USD": Decimal("500.00"),
    }


def test_the_query_to_the_database_applies_the_same_rules_as_the_calculation(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-16: 350.000 + 10.000 − 1.500 − 5.000, and 80.000 + 5.000.
    lucia = _user_id(engine, "Lucía")
    galicia = _account_id(engine, lucia, "Galicia pesos")
    mercado_pago = _account_id(engine, lucia, "Mercado Pago")
    today = _today()
    _movement(engine, lucia, galicia, type="income", amount="10000.00", day=today)
    _movement(engine, lucia, galicia, type="expense", amount="2000.00", day=today, deleted=True)
    original = _movement(engine, lucia, galicia, type="expense", amount="1500.00", day=today)
    _movement(
        engine,
        lucia,
        galicia,
        type="expense",
        amount="1500.00",
        day=today,
        duplicate_of=original,
    )
    _movement(
        engine, lucia, galicia, type="expense", amount="9000.00", day=today + timedelta(days=1)
    )
    _transfer(engine, lucia, galicia, mercado_pago, amount="5000.00", day=today)
    _enter_as(client, "Lucía")

    balances = _balances(_accounts(client))

    assert balances["Galicia pesos"] == Decimal("353500.00")
    assert balances["Mercado Pago"] == Decimal("85000.00")


def test_the_amount_arrives_with_its_exact_digits(client: TestClient, engine: Engine) -> None:
    # Case C1-17: 0,10 + 0,20, written as 0.30 and never through a float.
    user = _add_test_user(engine, "Marta", "+000000000009")
    petty_cash = _add_account(
        engine, user, "Caja chica", type="cash", currency="ARS", initial_balance="0.10"
    )
    _movement(engine, user, petty_cash, type="income", amount="0.20", day=_today())
    _enter_as(client, "Marta")

    response = client.get("/accounts")

    assert response.status_code == 200
    assert re.search(r'"balance":\s*0\.30[,}\s]', response.text), response.text


def test_the_accounts_of_lucia_come_in_order(client: TestClient) -> None:
    # Case C1-18: first the three in pesos, by name, and then the one in dollars.
    _enter_as(client, "Lucía")

    names = [account["name"] for account in _accounts(client)]

    assert names == ["Efectivo", "Galicia pesos", "Mercado Pago", "Galicia USD"]


def test_the_order_with_another_primary_currency_and_lowercase_names(
    client: TestClient, engine: Engine
) -> None:
    # Case C1-19: the primary currency first, then ARS and EUR by code, and "banco" after
    # "Ahorro" although it starts with a lowercase letter.
    user = _add_test_user(engine, "Nora", "+000000000008")
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE app_user SET primary_currency = 'USD' WHERE id = :id"), {"id": user}
        )
    for name, currency in (("Caja", "EUR"), ("banco", "ARS"), ("Wise", "USD"), ("Ahorro", "ARS")):
        _add_account(
            engine, user, name, type="bank_account", currency=currency, initial_balance="0.00"
        )
    _enter_as(client, "Nora")

    names = [account["name"] for account in _accounts(client)]

    assert names == ["Wise", "Ahorro", "banco", "Caja"]


def test_an_account_others_owe_comes_marked_by_its_type(client: TestClient, engine: Engine) -> None:
    # Case C1-23: "Me debe Juan" 0 + 30.000, and "Mercado Pago" 80.000 − 30.000.
    lucia = _user_id(engine, "Lucía")
    owed = _add_account(
        engine, lucia, "Me debe Juan", type="receivable", currency="ARS", initial_balance="0.00"
    )
    _open_accounts_on(engine, lucia, OCTOBER_1)
    mercado_pago = _account_id(engine, lucia, "Mercado Pago")
    _transfer(engine, lucia, mercado_pago, owed, amount="30000.00", day=OCTOBER_10)
    _enter_as(client, "Lucía")

    by_name = {account["name"]: account for account in _accounts(client)}

    assert by_name["Me debe Juan"]["type"] == "receivable"
    assert by_name["Me debe Juan"]["balance"] == Decimal("30000.00")
    assert by_name["Mercado Pago"]["balance"] == Decimal("50000.00")


# Cut 2: errors and the empty state.

UNAUTHORIZED = {"error": "unauthorized"}


def _template_balances(balance_of_galicia: str = "350000.00") -> dict[object, object]:
    return {
        "Galicia pesos": Decimal(balance_of_galicia),
        "Mercado Pago": Decimal("80000.00"),
        "Efectivo": Decimal("25000.00"),
        "Galicia USD": Decimal("500.00"),
    }


def _account_ids(engine: Engine, user_id: uuid.UUID) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id FROM account WHERE user_id = :user_id"), {"user_id": user_id}
        ).scalars()
        return {str(row) for row in rows}


def test_without_a_session_there_are_no_accounts(client: TestClient) -> None:
    # Case C2-01.
    response = client.get("/accounts")

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_an_expired_session_is_worth_the_same_as_none(client: TestClient, engine: Engine) -> None:
    # Case C2-02: a session of Lucía created 12 hours ago.
    _enter_as(client, "Lucía")
    lucia = _user_id(engine, "Lucía")
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE session SET created_at = now() - interval '12 hours', "
                "last_seen_at = now() - interval '1 minute', expires_at = now() "
                "WHERE user_id = :user_id"
            ),
            {"user_id": lucia},
        )

    response = client.get("/accounts")

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_lucia_does_not_see_the_accounts_of_pablo(client: TestClient, engine: Engine) -> None:
    # Case C2-03: the same four names for both, and only hers in the answer.
    lucia = _account_ids(engine, _user_id(engine, "Lucía"))
    pablo = _account_ids(engine, _user_id(engine, "Pablo"))
    _enter_as(client, "Lucía")

    ids = {account["id"] for account in _accounts(client)}

    assert ids == lucia
    assert ids.isdisjoint(pablo)


def test_an_expense_of_pablo_does_not_change_the_balance_of_lucia(
    client: TestClient, engine: Engine
) -> None:
    # Case C2-04.
    pablo = _user_id(engine, "Pablo")
    galicia_of_pablo = _account_id(engine, pablo, "Galicia pesos")
    _movement(engine, pablo, galicia_of_pablo, type="expense", amount="3500.00", day=_today())
    _enter_as(client, "Lucía")

    assert _balances(_accounts(client)) == _template_balances()


def test_a_user_without_accounts_gets_an_empty_list(client: TestClient, engine: Engine) -> None:
    # Case C2-05: not an error.
    _add_test_user(engine, "Elena", "+000000000007")
    _enter_as(client, "Elena")

    response = client.get("/accounts")

    assert response.status_code == 200
    assert response.json() == {"accounts": []}


def test_the_user_comes_from_the_session_not_from_the_request(
    client: TestClient, engine: Engine
) -> None:
    # Case C2-06: the parameter is not read.
    pablo = _user_id(engine, "Pablo")
    lucia = _account_ids(engine, _user_id(engine, "Lucía"))
    _enter_as(client, "Lucía")

    response = client.get("/accounts", params={"user_id": str(pablo)})

    assert response.status_code == 200
    assert {account["id"] for account in response.json()["accounts"]} == lucia


def test_the_logs_carry_no_balances_or_names(seeded_database_url: str, engine: Engine) -> None:
    # Case C3-01. Every value of every line, except the moment and the identifiers, which have
    # a fixed shape and may hold a digit by chance.
    stream = io.StringIO()
    environ = {
        "DATABASE_URL": seeded_database_url,
        "APP_ENV": "local",
        "APP_VERSION": "test",
        "DEV_ENTRY_ENABLED": "true",
    }
    client = TestClient(create_app(load_settings(environ), log_stream=stream), base_url=BASE_URL)
    _enter_as(client, "Lucía")
    written_before = len(stream.getvalue().splitlines())

    _accounts(client)

    lines = [json.loads(line) for line in stream.getvalue().splitlines()[written_before:]]
    [request] = [line for line in lines if line["event"] == "http.request"]
    assert request["endpoint"] == "GET /accounts"
    free_text = "\n".join(
        str(value)
        for line in lines
        for key, value in line.items()
        if key != "ts" and not key.endswith("_id")
    )
    for data in (
        "350000",
        "80000",
        "25000",
        "500.00",
        "Galicia",
        "Mercado Pago",
        "Efectivo",
        "Lucía",
    ):
        assert data not in free_text, data
