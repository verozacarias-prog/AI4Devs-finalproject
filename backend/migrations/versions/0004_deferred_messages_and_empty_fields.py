"""A message put off by a limit of use, and the empty fields of a classification (FEAT-003).

A message put off to the next day by the daily cap or by the quota of registration is pending
like one that waits for its retry, but it does not hold back the next messages of its sender
(ADR 0010, point 4). `deferred` tells the two apart, and only a pending message can be put off.

A call to the model says which fields of its output came empty, by their names and never with
a value, to diagnose an interpretation that failed without keeping content (ADR 0023, CA-34).

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE inbound_message ADD COLUMN deferred BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute(
        "ALTER TABLE inbound_message ADD CONSTRAINT ck_inbound_message_deferred_pending "
        "CHECK (NOT deferred OR status = 'pending')"
    )
    op.execute("ALTER TABLE llm_call ADD COLUMN empty_fields TEXT[]")
    op.execute(
        "ALTER TABLE llm_call ADD CONSTRAINT ck_llm_call_empty_fields CHECK ("
        "empty_fields <@ ARRAY['registration_type', 'amount', 'account', 'category', "
        "'currency', 'transaction_date']::TEXT[])"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE llm_call DROP COLUMN empty_fields")
    op.execute("ALTER TABLE inbound_message DROP COLUMN deferred")
