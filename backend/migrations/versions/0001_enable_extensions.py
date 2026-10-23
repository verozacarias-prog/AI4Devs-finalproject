"""Enable the PostgreSQL extensions the schema needs.

pgvector for the knowledge base vectors (ADR 0019) and btree_gist for the exclusion
constraints of budget_period (docs/06-tickets.md, Ticket 3). The tables come in the next
migration.

Revision ID: 0001
Revises:
"""
from __future__ import annotations

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
    op.execute("DROP EXTENSION IF EXISTS vector")
