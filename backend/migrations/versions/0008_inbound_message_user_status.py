"""An index to count the messages of a user waiting for an answer (issue #125).

The web chat refuses a message when its user already has the most allowed waiting (domain rules,
§ 12), and counts them on every message it receives.

Revision ID: 0008
Revises: 0007
"""

from __future__ import annotations

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_inbound_message_user_status ON inbound_message (user_id, status)")


def downgrade() -> None:
    op.execute("DROP INDEX ix_inbound_message_user_status")
