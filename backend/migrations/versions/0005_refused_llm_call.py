"""A refusal of the model is its own outcome of a call (FEAT-003, CA-40).

Until now a refusal was `blocked`, as an output the validation rejected, and the metric of
hallucinations counted it. It is no hallucination: the model invented nothing (ADR 0023).

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE llm_call DROP CONSTRAINT ck_llm_call_outcome")
    op.execute(
        "ALTER TABLE llm_call ADD CONSTRAINT ck_llm_call_outcome CHECK (outcome IN "
        "('ok', 'invalid_output', 'blocked', 'refused', 'provider_error', 'timeout'))"
    )


def downgrade() -> None:
    op.execute("UPDATE llm_call SET outcome = 'blocked' WHERE outcome = 'refused'")
    op.execute("ALTER TABLE llm_call DROP CONSTRAINT ck_llm_call_outcome")
    op.execute(
        "ALTER TABLE llm_call ADD CONSTRAINT ck_llm_call_outcome CHECK (outcome IN "
        "('ok', 'invalid_output', 'blocked', 'provider_error', 'timeout'))"
    )
