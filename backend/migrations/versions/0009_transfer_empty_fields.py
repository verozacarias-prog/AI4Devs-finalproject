"""The destination of a transfer is a field that may come empty (FEAT-006, CA-18).

The row of a classification that is a transfer lists its own empty fields: those of an expense
without the category, and with the account the money goes to.

Revision ID: 0009
Revises: 0008
"""

from __future__ import annotations

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE llm_call DROP CONSTRAINT ck_llm_call_empty_fields")
    op.execute(
        "ALTER TABLE llm_call ADD CONSTRAINT ck_llm_call_empty_fields CHECK ("
        "empty_fields <@ ARRAY['registration_type', 'amount', 'account', 'to_account', "
        "'category', 'currency', 'transaction_date']::TEXT[])"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE llm_call SET empty_fields = array_remove(empty_fields, 'to_account') "
        "WHERE 'to_account' = ANY(empty_fields)"
    )
    op.execute("ALTER TABLE llm_call DROP CONSTRAINT ck_llm_call_empty_fields")
    op.execute(
        "ALTER TABLE llm_call ADD CONSTRAINT ck_llm_call_empty_fields CHECK ("
        "empty_fields <@ ARRAY['registration_type', 'amount', 'account', 'category', "
        "'currency', 'transaction_date']::TEXT[])"
    )
