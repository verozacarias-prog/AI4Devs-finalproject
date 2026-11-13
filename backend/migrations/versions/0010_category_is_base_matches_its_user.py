"""A category is of the base catalog exactly when it has no user (issue 189).

`is_base` and an empty `user_id` say the same thing: the CHECK keeps them from saying different
things.

Revision ID: 0010
Revises: 0009
"""

from __future__ import annotations

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE category ADD CONSTRAINT ck_category_is_base "
        "CHECK (is_base = (user_id IS NULL))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE category DROP CONSTRAINT ck_category_is_base")
