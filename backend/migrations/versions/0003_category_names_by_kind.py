"""The name of a category is unique within its kind (domain rules, § 4).

A category is recognized by its name within its kind, since an expense never uses a category of
income: a category of a user named "Honorarios", of expenses, lives next to the base one of
income. The two unique indexes and the trigger against the base names now compare the kind
too, and keep their names, so whoever reads an error finds the same rule.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None

REJECT_BASE_NAME_BY_KIND = """
    CREATE OR REPLACE FUNCTION category_reject_base_name() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.user_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM category base
            WHERE base.user_id IS NULL
              AND base.kind = NEW.kind
              AND lower(base.name) = lower(NEW.name)
        ) THEN
            RAISE EXCEPTION 'a category of a user cannot take the name of a base one of its kind'
                USING ERRCODE = 'check_violation',
                      TABLE = 'category',
                      CONSTRAINT = 'tg_category_name_not_base';
        END IF;
        RETURN NEW;
    END;
    $$
"""

REJECT_BASE_NAME_OF_ANY_KIND = """
    CREATE OR REPLACE FUNCTION category_reject_base_name() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.user_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM category base
            WHERE base.user_id IS NULL AND lower(base.name) = lower(NEW.name)
        ) THEN
            RAISE EXCEPTION 'a category of a user cannot take the name of a base one'
                USING ERRCODE = 'check_violation',
                      TABLE = 'category',
                      CONSTRAINT = 'tg_category_name_not_base';
        END IF;
        RETURN NEW;
    END;
    $$
"""


def upgrade() -> None:
    op.execute("DROP INDEX uq_category_user_name")
    op.execute("CREATE UNIQUE INDEX uq_category_user_name ON category (user_id, kind, lower(name))")
    op.execute("DROP INDEX uq_category_base_name")
    op.execute(
        "CREATE UNIQUE INDEX uq_category_base_name ON category (kind, lower(name)) "
        "WHERE user_id IS NULL"
    )
    op.execute(REJECT_BASE_NAME_BY_KIND)


def downgrade() -> None:
    # Fails if a user already has two categories with one name, one of each kind: they have to
    # be renamed first, as a decision of whoever goes back.
    op.execute(REJECT_BASE_NAME_OF_ANY_KIND)
    op.execute("DROP INDEX uq_category_base_name")
    op.execute(
        "CREATE UNIQUE INDEX uq_category_base_name ON category (lower(name)) WHERE user_id IS NULL"
    )
    op.execute("DROP INDEX uq_category_user_name")
    op.execute("CREATE UNIQUE INDEX uq_category_user_name ON category (user_id, lower(name))")
