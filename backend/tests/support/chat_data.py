"""Shared setup of the web chat tests (FEAT-002): a seeded database and messages written with SQL.

The messages are written by hand so each case starts from exactly the state it describes, the
way the accounts tests write their movements.
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from app.adapters.inbound.operator_commands.seed_test_data import main as seed_test_data

# The clock of every case, unless the case says otherwise: 15:00:00 in Buenos Aires.
NOW = datetime(2026, 10, 15, 18, 0, 0, tzinfo=UTC)
FIXED_REPLY = "Recibí tu mensaje. Todavía no puedo procesarlo."


def seed(database_url: str) -> None:
    code = seed_test_data(
        {"DATABASE_URL": database_url, "APP_ENV": "local"}, io.StringIO(), io.StringIO()
    )
    assert code == 0, "the test data script failed"


def user_id(engine: Engine, name: str) -> uuid.UUID:
    with engine.connect() as connection:
        found: uuid.UUID = connection.execute(
            text("SELECT id FROM app_user WHERE name = :name"), {"name": name}
        ).scalar_one()
    return found


def inbound(
    engine: Engine,
    name: str,
    message: str,
    *,
    sent_at: datetime,
    status: str = "pending",
    attempts: int = 0,
    locked_until: datetime | None = None,
) -> uuid.UUID:
    """A message the user wrote in the web chat, in the state the case needs."""
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO inbound_message (provider, provider_message_id, user_id, "
                "from_phone, payload, sent_at, status, attempts, locked_until, created_at) "
                "SELECT 'web', id::text || ':' || :key, id, whatsapp_phone, "
                "CAST(:payload AS jsonb), :sent_at, :status, :attempts, :locked_until, "
                ":sent_at FROM app_user WHERE name = :name RETURNING id"
            ),
            {
                "key": str(uuid.uuid4()),
                "payload": json.dumps({"text": message}),
                "sent_at": sent_at,
                "status": status,
                "attempts": attempts,
                "locked_until": locked_until,
                "name": name,
            },
        ).scalar_one()
    return created


def outbound(
    engine: Engine, answers: uuid.UUID, message: str, *, created_at: datetime
) -> uuid.UUID:
    """A reply of Platita in the web chat, to the inbound message it answers."""
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO outbound_message (provider, user_id, to_phone, "
                "inbound_message_id, content, status, sent_at, created_at) "
                "SELECT 'web', user_id, from_phone, id, CAST(:content AS jsonb), 'sent', "
                ":created_at, :created_at FROM inbound_message WHERE id = :answers "
                "RETURNING id"
            ),
            {
                "content": json.dumps({"text": message, "response_kind": "fixed_text"}),
                "created_at": created_at,
                "answers": answers,
            },
        ).scalar_one()
    return created


def status_of(engine: Engine, message_id: uuid.UUID) -> tuple[str, int]:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT status, attempts FROM inbound_message WHERE id = :id"),
            {"id": message_id},
        ).one()
    return row.status, row.attempts
