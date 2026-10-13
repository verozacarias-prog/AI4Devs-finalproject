"""SQL written by hand, in one place. Only this package may hold SQL (ADR 0001)."""

from __future__ import annotations

# How the schema names its primary keys (docs/03-modelo-de-datos.md, 3.2). PostgreSQL reports
# a repeated primary key and a repeated unique key with the same error, and only the name
# tells them apart.
PRIMARY_KEY_PREFIX = "pk_"

# The cheapest query that proves the database answers.
PING = "SELECT 1"

INSERT_USER = """
    INSERT INTO app_user (
        id, name, whatsapp_phone, country, time_zone, primary_currency,
        exchange_rate_reference, terms_accepted_at, terms_version, notifications_opt_in,
        onboarding_status
    ) VALUES (
        :id, :name, :whatsapp_phone, :country, :time_zone, :primary_currency,
        :exchange_rate_reference, :terms_accepted_at, :terms_version, :notifications_opt_in,
        :onboarding_status
    )
"""

SELECT_USER_BY_PHONE = """
    SELECT id, name, whatsapp_phone, country, time_zone, primary_currency,
           exchange_rate_reference, terms_accepted_at, terms_version, notifications_opt_in,
           onboarding_status
      FROM app_user
     WHERE whatsapp_phone = :phone
"""

INSERT_ACCOUNT = """
    INSERT INTO account (id, user_id, name, type, currency, initial_balance, created_at)
    VALUES (:id, :user_id, :name, :type, :currency, :initial_balance, :opened_at)
"""

INSERT_BUDGET_PERIOD = """
    INSERT INTO budget_period (
        id, user_id, family_group_id, period_type, period_start, period_end,
        primary_currency, estimated_income, status
    ) VALUES (
        :id, :user_id, :family_group_id, :period_type, :period_start, :period_end,
        :primary_currency, :estimated_income, :status
    )
"""

INSERT_FINANCIAL_PROFILE = """
    INSERT INTO financial_profile (
        user_id, income_range, dependents, has_debts, emergency_fund_months, main_goal
    ) VALUES (
        :user_id, :income_range, :dependents, :has_debts, :emergency_fund_months, :main_goal
    )
"""

INSERT_FAMILY_GROUP = "INSERT INTO family_group (id, name) VALUES (:id, :name)"

INSERT_MEMBERSHIP = """
    INSERT INTO user_group (user_id, family_group_id, role, joined_at)
    VALUES (:user_id, :family_group_id, :role, :joined_at)
"""

# The current owner: a membership that was closed no longer owns the group.
SELECT_GROUP_OWNED_BY = """
    SELECT g.id, g.name
      FROM family_group g
      JOIN user_group m ON m.family_group_id = g.id
     WHERE m.user_id = :owner_id
       AND m.role = :owner_role
       AND m.left_at IS NULL
       AND g.name = :name
"""
