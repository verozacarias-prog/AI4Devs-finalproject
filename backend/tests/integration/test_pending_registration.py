"""A registration that asks, and its continuation, against PostgreSQL (FEAT-003, its spec.md).

Cases C2-01, C2-07, C2-14, C2-16, C2-19, C2-21, C2-24, C2-33 and C2-36. The worker runs whole
rounds, the way its process does, with the model replaced by a double inside the wrapper that
records each call. A case that starts from an open pending gets it the way a user does: a first
message that leaves it pending, and then the reply.
"""

from __future__ import annotations

import io
import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine, text

from app.adapters.inbound.message_worker.worker import create_worker
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities.classification import (
    Classification,
    MessageClass,
    PendingReply,
    RegistrationType,
)
from app.domain.use_cases.messages.answer_message import AnswerMessage
from app.domain.use_cases.messages.claim_next_message import ClaimNextMessage
from app.settings import Settings, load_settings
from tests.support.chat_data import inbound, status_of, user_id
from tests.support.doubles import FixedClock
from tests.support.fake_llm import FakeLLM
from tests.support.registration_data import (
    NOW,
    OCTOBER_1,
    OCTOBER_17,
    OCTOBER_31,
    seed_on_october_1,
)

pytestmark = pytest.mark.integration

ALL_ACCOUNTS = "¿Con qué cuenta? Galicia pesos, Mercado Pago, Efectivo o Galicia USD."
# Sunday 1 November 2026, 15:00 in Buenos Aires.
NOVEMBER_1_NOW = datetime(2026, 11, 1, 18, 0, 0, tzinfo=UTC)


@pytest.fixture
def engine(fresh_database_url: str) -> Iterator[Engine]:
    engine = create_engine(fresh_database_url)
    seed_on_october_1(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def settings(fresh_database_url: str, engine: Engine) -> Settings:
    return load_settings(
        {
            "DATABASE_URL": fresh_database_url,
            "APP_ENV": "local",
            "APP_VERSION": "test",
            "WEB_CHAT_ENABLED": "true",
        }
    )


def _run_round(settings: Settings, llm: FakeLLM, now: datetime = NOW) -> None:
    create_worker(settings, FixedClock(now), log_stream=io.StringIO(), llm=llm).run_round()


def _write_and_answer(
    settings: Settings,
    engine: Engine,
    message: str,
    classification: Classification,
    *,
    name: str = "Lucía",
    now: datetime = NOW,
) -> tuple[uuid.UUID, FakeLLM]:
    """A message of the user, and the round of the worker that answers it."""
    written = inbound(engine, name, message, sent_at=now - timedelta(seconds=5))
    llm = FakeLLM(classification)
    _run_round(settings, llm, now)
    return written, llm


def _expense(
    *,
    amount: str | None = "3500",
    account: str | None = None,
    category: str | None = "Supermercado",
    proposed_category: str | None = None,
) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        registration_type=RegistrationType.EXPENSE,
        amount=None if amount is None else Decimal(amount),
        account=account,
        category=category,
        proposed_category=proposed_category,
    )


def _continues(*, account: str | None = None, accepts_proposal: bool = False) -> Classification:
    return Classification(
        MessageClass.REGISTRATION,
        account=account,
        pending_reply=PendingReply.CONTINUES,
        accepts_proposal=accepts_proposal,
    )


def _rows(engine: Engine, query: str, **parameters: object) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(text(query), parameters).all()
    return [dict(row._mapping) for row in rows]


def _replies_to(engine: Engine, message: uuid.UUID) -> list[dict[str, object]]:
    replies = []
    for row in _rows(
        engine,
        "SELECT id, content FROM outbound_message WHERE inbound_message_id = :id",
        id=message,
    ):
        content = row["content"]
        decoded = content if isinstance(content, dict) else json.loads(str(content))
        replies.append({"id": row["id"], **decoded})
    return replies


def _transactions(engine: Engine) -> list[dict[str, object]]:
    return _rows(
        engine,
        "SELECT t.id, t.amount, t.transaction_date, a.name AS account, c.name AS category, "
        "c.user_id AS category_user_id, t.budget_period_id FROM transaction t "
        "JOIN account a ON a.id = t.account_id JOIN category c ON c.id = t.category_id",
    )


def _supermarket_without_account(settings: Settings, engine: Engine, now: datetime = NOW) -> None:
    """The pending of C2-01."""
    _write_and_answer(settings, engine, "gasté 3500 en el súper", _expense(), now=now)


def test_an_expense_without_an_account_stays_pending_and_its_batch_awaits_a_reply(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-01.
    lucia = user_id(engine, "Lucía")

    message, _ = _write_and_answer(settings, engine, "gasté 3500 en el súper", _expense())

    assert _rows(engine, "SELECT id FROM transaction") == []
    [reply] = _replies_to(engine, message)
    [batch] = _rows(engine, "SELECT * FROM pending_batch")
    assert batch["user_id"] == lucia
    assert batch["source"] == "manual"
    assert batch["status"] == "open"
    assert batch["awaiting_reply"] is True
    assert batch["question_message_id"] == reply["id"]
    [pending] = _rows(engine, "SELECT * FROM pending_transaction")
    assert pending["batch_id"] == batch["id"]
    assert pending["position"] == 1
    assert pending["status"] == "open"
    assert pending["intent"] == "transaction"
    assert pending["missing_fields"] == ["account_id"]
    parsed = pending["parsed_data"]
    assert isinstance(parsed, dict)
    assert parsed["type"] == "expense"
    assert parsed["amount"] == "3500"
    assert parsed["category"] == "Supermercado"
    assert parsed["transaction_date"] == "2026-10-17"
    assert pending["expires_at"] == NOW + timedelta(hours=24)
    assert status_of(engine, message)[0] == "processed"
    assert reply["response_kind"] == "registration"


def test_the_reply_completes_the_pending_and_registers_it(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-07.
    lucia = user_id(engine, "Lucía")
    _supermarket_without_account(settings, engine)

    reply_message, _ = _write_and_answer(
        settings, engine, "con MP", _continues(account="MP"), now=NOW + timedelta(minutes=1)
    )

    [movement] = _transactions(engine)
    assert movement["amount"] == Decimal("3500.00")
    assert movement["account"] == "Mercado Pago"
    assert movement["category"] == "Supermercado"
    assert movement["transaction_date"] == OCTOBER_17
    [pending] = _rows(engine, "SELECT * FROM pending_transaction")
    assert pending["status"] == "promoted"
    assert pending["resulting_transaction_id"] == movement["id"]
    assert pending["resolved_by"] == lucia
    [confirmation] = _replies_to(engine, reply_message)
    [batch] = _rows(engine, "SELECT * FROM pending_batch")
    assert batch["status"] == "closed"
    assert batch["awaiting_reply"] is False
    assert batch["confirmation_message_id"] == confirmation["id"]
    assert confirmation["response_kind"] == "registration"
    assert confirmation["text"] == (
        "¡Listo! Anoté un gasto de $3.500 en Mercado Pago.\n"
        "Fecha: 17/10/2026\n"
        "Moneda: ARS\n"
        "Categoría: Supermercado\n"
        "Presupuesto: tu presupuesto personal, del 1/10/2026 al 31/10/2026"
    )


def test_an_expired_pending_is_not_continued(settings: Settings, engine: Engine) -> None:
    # Case C2-14. The pending was created 25 hours before the reply.
    _supermarket_without_account(settings, engine, now=NOW - timedelta(hours=25))
    [first] = _rows(engine, "SELECT id, batch_id FROM pending_transaction")

    _, llm = _write_and_answer(settings, engine, "con MP", _expense(amount=None, account="MP"))

    [request] = llm.requests
    assert request.open_pending is None
    [expired] = _rows(
        engine, "SELECT status FROM pending_transaction WHERE id = :id", id=first["id"]
    )
    assert expired["status"] == "expired"
    [old_batch] = _rows(
        engine,
        "SELECT status, awaiting_reply FROM pending_batch WHERE id = :id",
        id=first["batch_id"],
    )
    assert (old_batch["status"], old_batch["awaiting_reply"]) == ("closed", False)
    [new] = _rows(
        engine,
        "SELECT batch_id, missing_fields, status FROM pending_transaction WHERE id <> :id",
        id=first["id"],
    )
    assert new["batch_id"] != first["batch_id"]
    assert new["status"] == "open"
    assert new["missing_fields"] == ["amount"]


def test_with_a_yes_the_new_category_is_created_and_the_expense_registered(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-16.
    lucia = user_id(engine, "Lucía")
    _write_and_answer(
        settings,
        engine,
        "gasté 9000 en la peluquería con MP",
        _expense(amount="9000", account="MP", category=None, proposed_category="Peluquería"),
    )

    reply_message, _ = _write_and_answer(
        settings,
        engine,
        "sí, creala",
        _continues(accepts_proposal=True),
        now=NOW + timedelta(minutes=1),
    )

    [category] = _rows(
        engine, "SELECT id, user_id, is_base, kind FROM category WHERE name = 'Peluquería'"
    )
    assert category["user_id"] == lucia
    assert category["is_base"] is False
    assert category["kind"] == "expense"
    [movement] = _transactions(engine)
    assert movement["category"] == "Peluquería"
    [confirmation] = _replies_to(engine, reply_message)
    assert "Categoría: Peluquería" in str(confirmation["text"]).splitlines()


def _november_draft(engine: Engine) -> uuid.UUID:
    """Her draft of November, with its estimated income and one limit."""
    with engine.begin() as connection:
        draft: uuid.UUID = connection.execute(
            text(
                "INSERT INTO budget_period (user_id, period_type, period_start, period_end, "
                "primary_currency, estimated_income, status) SELECT id, 'monthly', "
                "'2026-11-01', '2026-11-30', 'ARS', 1200000, 'draft' FROM app_user "
                "WHERE name = 'Lucía' RETURNING id"
            )
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO budget (budget_period_id, category_id, limit_amount) "
                "SELECT :draft, id, 300000 FROM category "
                "WHERE name = 'Supermercado' AND user_id IS NULL"
            ),
            {"draft": draft},
        )
    return draft


def test_with_a_yes_the_draft_is_confirmed_and_the_expense_registered_in_it(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-19.
    draft = _november_draft(engine)
    _write_and_answer(
        settings,
        engine,
        "gasté 3500 en el súper con MP",
        _expense(account="MP"),
        now=NOVEMBER_1_NOW,
    )

    reply_message, _ = _write_and_answer(
        settings,
        engine,
        "sí",
        _continues(accepts_proposal=True),
        now=NOVEMBER_1_NOW + timedelta(minutes=1),
    )

    [period] = _rows(
        engine, "SELECT status, estimated_income FROM budget_period WHERE id = :id", id=draft
    )
    assert period["status"] == "confirmed"
    assert period["estimated_income"] == Decimal("1200000.00")
    [limit] = _rows(
        engine, "SELECT limit_amount FROM budget WHERE budget_period_id = :id", id=draft
    )
    assert limit["limit_amount"] == Decimal("300000.00")
    [movement] = _transactions(engine)
    assert movement["budget_period_id"] == draft
    [confirmation] = _replies_to(engine, reply_message)
    assert str(confirmation["text"]).splitlines()[-1] == (
        "Presupuesto: tu presupuesto personal, del 1/11/2026 al 30/11/2026"
    )


def test_the_only_possible_period_of_a_group_gets_the_expense_without_asking(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-21. Lucía without her own period, and a member of Casa.
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM budget_period WHERE user_id = "
                "(SELECT id FROM app_user WHERE name = 'Lucía')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO user_group (user_id, family_group_id, role, joined_at) "
                "SELECT u.id, g.id, 'member', :joined FROM app_user u, family_group g "
                "WHERE u.name = 'Lucía' AND g.name = 'Casa'"
            ),
            {"joined": NOW - timedelta(days=20)},
        )
    [group_period] = _rows(
        engine,
        "SELECT p.id, p.period_start, p.period_end FROM budget_period p "
        "JOIN family_group g ON g.id = p.family_group_id WHERE g.name = 'Casa'",
    )
    assert (group_period["period_start"], group_period["period_end"]) == (OCTOBER_1, OCTOBER_31)

    message, _ = _write_and_answer(
        settings,
        engine,
        "gasté 3500 en el súper con Mercado Pago",
        _expense(account="Mercado Pago"),
    )

    [movement] = _transactions(engine)
    assert movement["budget_period_id"] == group_period["id"]
    [confirmation] = _replies_to(engine, message)
    assert str(confirmation["text"]).splitlines()[-1] == (
        "Presupuesto: el de Casa, del 1/10/2026 al 31/10/2026"
    )


def test_nothing_of_another_user_reaches_the_model_or_is_used(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-24. Sofía has a Brubank account, her own category Pádel, and an open pending.
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO account (user_id, name, type, currency, initial_balance, created_at) "
                "SELECT id, 'Brubank', 'bank_account', 'ARS', 1000, :opened FROM app_user "
                "WHERE name = 'Sofía'"
            ),
            {"opened": NOW - timedelta(days=16)},
        )
        connection.execute(
            text(
                "INSERT INTO category (name, user_id, kind) "
                "SELECT 'Pádel', id, 'expense' FROM app_user WHERE name = 'Sofía'"
            )
        )
    _write_and_answer(
        settings,
        engine,
        "gasté 5000 en el súper",
        _expense(amount="5000"),
        name="Sofía",
        now=NOW - timedelta(minutes=10),
    )

    message, llm = _write_and_answer(
        settings,
        engine,
        "gasté 3500 en el pádel con Brubank",
        _expense(account="Brubank", category="Pádel"),
    )

    [request] = llm.requests
    sent = json.dumps(
        {
            "text": request.text,
            "accounts": request.accounts,
            "expense_categories": request.expense_categories,
            "income_categories": request.income_categories,
        },
        ensure_ascii=False,
    )
    assert "Brubank" not in request.accounts
    assert "Pádel" not in request.expense_categories
    assert request.open_pending is None
    assert "5000" not in sent
    assert _rows(engine, "SELECT id FROM transaction") == []
    [reply] = _replies_to(engine, message)
    assert str(reply["text"]).splitlines()[1] == ALL_ACCOUNTS


def test_two_workers_that_continue_the_same_pending_leave_one_movement(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-33. The first worker took the reply and its lock ended; a second one took it
    # again. Both reach the final transaction: first the second, then the first.
    _supermarket_without_account(settings, engine)
    reply_at = NOW + timedelta(minutes=1)
    inbound(engine, "Lucía", "con MP", sent_at=reply_at - timedelta(seconds=5))
    lock = timedelta(seconds=settings.worker_lock_seconds)
    unit_of_work = SqlAlchemyUnitOfWork(create_engine(settings.database_url))
    first = ClaimNextMessage(unit_of_work, FixedClock(reply_at), lock).execute()
    later = reply_at + lock + timedelta(seconds=1)
    second = ClaimNextMessage(unit_of_work, FixedClock(later), lock).execute()
    assert first is not None and second is not None
    assert first.id == second.id

    llm = FakeLLM(_continues(account="MP"))
    assert AnswerMessage(unit_of_work, FixedClock(later), llm).execute(second) is True
    assert AnswerMessage(unit_of_work, FixedClock(later), llm).execute(first) is False

    assert len(_transactions(engine)) == 1
    [pending] = _rows(engine, "SELECT status FROM pending_transaction")
    assert pending["status"] == "promoted"
    assert len(_replies_to(engine, first.id)) == 1


def test_a_reply_that_changes_an_interpreted_field_adds_a_correction(
    settings: Settings, engine: Engine
) -> None:
    # Case C2-36. The amount changed, which the model had interpreted; the account was
    # missing, and completing it does not count.
    _supermarket_without_account(settings, engine)
    reply = Classification(
        MessageClass.REGISTRATION,
        amount=Decimal("3800"),
        account="MP",
        pending_reply=PendingReply.CONTINUES,
    )

    _write_and_answer(
        settings, engine, "con MP, y eran 3800", reply, now=NOW + timedelta(minutes=1)
    )

    [movement] = _transactions(engine)
    assert movement["amount"] == Decimal("3800.00")
    assert movement["account"] == "Mercado Pago"
    [pending] = _rows(engine, "SELECT status, corrected_fields_count FROM pending_transaction")
    assert pending["status"] == "promoted"
    assert pending["corrected_fields_count"] == 1
