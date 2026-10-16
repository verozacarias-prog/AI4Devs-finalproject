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
# What the database says when it rejects a reply: it must not reach the logs either.
REPLY_REJECTION = "la base rechaza la respuesta"


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
    provider: str = "web",
    purged: bool = False,
    next_attempt_at: datetime | None = None,
) -> uuid.UUID:
    """A message the user wrote, by default in the web chat, in the state the case needs.

    Without `next_attempt_at`, it is the default of the table: the moment it was stored.
    """
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO inbound_message (provider, provider_message_id, user_id, "
                "from_phone, payload, purged_at, sent_at, status, attempts, locked_until, "
                "next_attempt_at, created_at) "
                "SELECT :provider, id::text || ':' || :key, id, "
                "CASE WHEN :purged THEN NULL ELSE whatsapp_phone END, "
                "CASE WHEN :purged THEN NULL ELSE CAST(:payload AS jsonb) END, "
                "CASE WHEN :purged THEN :sent_at END, :sent_at, :status, :attempts, "
                ":locked_until, COALESCE(CAST(:next_attempt_at AS timestamptz), now()), :sent_at "
                "FROM app_user WHERE name = :name RETURNING id"
            ),
            {
                "provider": provider,
                "purged": purged,
                "key": str(uuid.uuid4()),
                "payload": json.dumps({"text": message}),
                "sent_at": sent_at,
                "status": status,
                "attempts": attempts,
                "locked_until": locked_until,
                "next_attempt_at": next_attempt_at,
                "name": name,
            },
        ).scalar_one()
    return created


def outbound(
    engine: Engine, answers: uuid.UUID, message: str, *, created_at: datetime
) -> uuid.UUID:
    """A reply of Platita, by the channel of the inbound message it answers."""
    with engine.begin() as connection:
        created: uuid.UUID = connection.execute(
            text(
                "INSERT INTO outbound_message (provider, user_id, to_phone, "
                "inbound_message_id, content, status, sent_at, created_at) "
                "SELECT provider, user_id, from_phone, id, CAST(:content AS jsonb), 'sent', "
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


def alert_by_whatsapp(engine: Engine, name: str, message: str, *, created_at: datetime) -> None:
    """A message of Platita by WhatsApp that answers none: an alert or a reminder."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO outbound_message (provider, user_id, to_phone, content, status, "
                "created_at) SELECT 'meta', id, whatsapp_phone, CAST(:content AS jsonb), "
                "'pending', :created_at FROM app_user WHERE name = :name"
            ),
            {
                "content": json.dumps({"text": message, "response_kind": "proactive"}),
                "created_at": created_at,
                "name": name,
            },
        )


def messages_of(engine: Engine, name: str) -> list[tuple[str, uuid.UUID | None]]:
    """The text and the quoted reply of every message the user wrote, in the order they came."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT payload ->> 'text' AS text, quoted_outbound_message_id "
                "FROM inbound_message m JOIN app_user u ON u.id = m.user_id "
                "WHERE u.name = :name ORDER BY m.sent_at, m.id"
            ),
            {"name": name},
        ).all()
    return [(row.text, row.quoted_outbound_message_id) for row in rows]


def reject_every_reply(engine: Engine) -> None:
    """A database that refuses to store any reply of Platita."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_reply() RETURNS trigger AS $$ BEGIN "
                f"RAISE EXCEPTION '{REPLY_REJECTION}'; END $$ LANGUAGE plpgsql"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER reject_reply BEFORE INSERT ON outbound_message "
                "FOR EACH ROW EXECUTE FUNCTION reject_reply()"
            )
        )
