"""An answer cut by the cap of its output is its own outcome of a call (FEAT-003, CA-40).

Until now it was `provider_error`, so a message that was too long read as a fall of the provider,
and it was tried again. Issue 196.

Revision ID: 0011
Revises: 0010
"""

from __future__ import annotations

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE llm_call DROP CONSTRAINT ck_llm_call_outcome")
    op.execute(
        "ALTER TABLE llm_call ADD CONSTRAINT ck_llm_call_outcome CHECK (outcome IN "
        "('ok', 'invalid_output', 'blocked', 'refused', 'truncated', 'provider_error', "
        "'timeout'))"
    )


def downgrade() -> None:
    op.execute("UPDATE llm_call SET outcome = 'provider_error' WHERE outcome = 'truncated'")
    op.execute("ALTER TABLE llm_call DROP CONSTRAINT ck_llm_call_outcome")
    op.execute(
        "ALTER TABLE llm_call ADD CONSTRAINT ck_llm_call_outcome CHECK (outcome IN "
        "('ok', 'invalid_output', 'blocked', 'refused', 'provider_error', 'timeout'))"
    )
