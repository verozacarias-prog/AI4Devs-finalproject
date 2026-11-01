"""The estimated income of a budget period is 0 or more (FEAT-005, CA-15).

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE budget_period ADD CONSTRAINT ck_budget_period_estimated_income "
        "CHECK (estimated_income >= 0)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE budget_period DROP CONSTRAINT ck_budget_period_estimated_income")
