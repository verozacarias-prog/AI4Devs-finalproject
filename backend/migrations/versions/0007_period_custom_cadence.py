"""A period says what it lasts: a custom cadence, and dates that match the cadence (FEAT-005).

The periods that do not match become custom, with the same dates, even the confirmed ones.

Revision ID: 0007
Revises: 0006
"""

from __future__ import annotations

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | None = None
depends_on: str | None = None

MONTHLY_END = "period_end = (period_start + INTERVAL '1 month')::date - 1"
BIWEEKLY_DATES = (
    "(EXTRACT(DAY FROM period_start) = 1 AND period_end = period_start + 14) OR "
    "(EXTRACT(DAY FROM period_start) = 16 "
    "AND period_end = (period_start - 15 + INTERVAL '1 month')::date - 1)"
)


def upgrade() -> None:
    op.execute("ALTER TABLE budget_period DROP CONSTRAINT ck_budget_period_period_type")
    op.execute(
        "ALTER TABLE budget_period ADD CONSTRAINT ck_budget_period_period_type "
        "CHECK (period_type IN ('monthly', 'biweekly', 'custom'))"
    )
    op.execute(
        "UPDATE budget_period SET period_type = 'custom' WHERE "
        f"(period_type = 'monthly' AND NOT ({MONTHLY_END})) OR "
        f"(period_type = 'biweekly' AND NOT ({BIWEEKLY_DATES}))"
    )
    op.execute(
        "ALTER TABLE budget_period ADD CONSTRAINT ck_budget_period_monthly_dates "
        f"CHECK (period_type <> 'monthly' OR {MONTHLY_END})"
    )
    op.execute(
        "ALTER TABLE budget_period ADD CONSTRAINT ck_budget_period_biweekly_dates "
        f"CHECK (period_type <> 'biweekly' OR {BIWEEKLY_DATES})"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE budget_period DROP CONSTRAINT ck_budget_period_biweekly_dates")
    op.execute("ALTER TABLE budget_period DROP CONSTRAINT ck_budget_period_monthly_dates")
    op.execute("UPDATE budget_period SET period_type = 'monthly' WHERE period_type = 'custom'")
    op.execute("ALTER TABLE budget_period DROP CONSTRAINT ck_budget_period_period_type")
    op.execute(
        "ALTER TABLE budget_period ADD CONSTRAINT ck_budget_period_period_type "
        "CHECK (period_type IN ('monthly', 'biweekly'))"
    )
