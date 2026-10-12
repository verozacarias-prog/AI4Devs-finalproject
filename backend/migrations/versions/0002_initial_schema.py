"""Initial schema: the tables, their constraints, the reference data and the application role.

Everything comes from docs/03-modelo-de-datos.md and docs/06-tickets.md (Ticket 3). The
knowledge base tables wait for the embedding model (ADR 0019).

A trigger rejects a row the same way a constraint does: with the code of a check violation
and a constraint name that starts with `tg_`, so whoever reads the error always finds the rule
by its name.

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None

# The role the application connects with. It cannot delete movements (ADR 0015).
APPLICATION_ROLE = "platita_app"

TABLES: tuple[str, ...] = (
    "currency",
    "app_user",
    "family_group",
    "user_group",
    "group_invitation",
    "financial_profile",
    "llm_usage",
    "login_code",
    "session",
    "dev_access_link",
    "auth_throttle",
    "allowed_phone",
    "indicator_value",
    "exchange_rate",
    "category",
    "budget_period",
    "budget",
    "account",
    "card_statement",
    "recurring_rule",
    "transaction",
    "transfer",
    "inbound_message",
    "outbound_message",
    "sent_alert",
    "pending_batch",
    "pending_transaction",
    "llm_call",
)

# Rows are marked as deleted, never removed (ADR 0015).
TABLES_WITHOUT_DELETE: tuple[str, ...] = ("transaction", "transfer", "recurring_rule")

CREATE_TABLES: tuple[str, ...] = (
    """
    CREATE TABLE currency (
        code CHAR(3) CONSTRAINT pk_currency PRIMARY KEY,
        name TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE app_user (
        id UUID CONSTRAINT pk_app_user PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT,
        whatsapp_phone TEXT CONSTRAINT uq_app_user_whatsapp_phone UNIQUE,
        email TEXT,
        email_connected BOOLEAN NOT NULL DEFAULT FALSE,
        country TEXT,
        time_zone TEXT,
        primary_currency CHAR(3)
            CONSTRAINT fk_app_user_primary_currency REFERENCES currency (code),
        inflation_source TEXT,
        exchange_rate_reference TEXT,
        terms_accepted_at TIMESTAMPTZ NOT NULL,
        terms_version TEXT NOT NULL,
        notifications_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
        onboarding_status TEXT NOT NULL DEFAULT 'in_progress',
        account_status TEXT NOT NULL DEFAULT 'active',
        deactivated_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_app_user_onboarding_status
            CHECK (onboarding_status IN ('in_progress', 'completed')),
        CONSTRAINT ck_app_user_account_status
            CHECK (account_status IN ('active', 'deactivated', 'deleted')),
        CONSTRAINT ck_app_user_onboarding_completed CHECK (
            onboarding_status <> 'completed'
            OR (
                name IS NOT NULL
                AND country IS NOT NULL
                AND time_zone IS NOT NULL
                AND primary_currency IS NOT NULL
            )
        ),
        CONSTRAINT ck_app_user_phone_iff_deleted
            CHECK ((whatsapp_phone IS NULL) = (account_status = 'deleted')),
        CONSTRAINT ck_app_user_deactivated_at CHECK (
            account_status NOT IN ('deactivated', 'deleted') OR deactivated_at IS NOT NULL
        )
    )
    """,
    """
    CREATE TABLE family_group (
        id UUID CONSTRAINT pk_family_group PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE user_group (
        user_id UUID NOT NULL CONSTRAINT fk_user_group_user REFERENCES app_user (id),
        family_group_id UUID NOT NULL
            CONSTRAINT fk_user_group_family_group REFERENCES family_group (id),
        role TEXT NOT NULL DEFAULT 'member',
        joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        left_at TIMESTAMPTZ,
        CONSTRAINT pk_user_group PRIMARY KEY (user_id, family_group_id),
        CONSTRAINT ck_user_group_role CHECK (role IN ('owner', 'member')),
        CONSTRAINT ck_user_group_left_after_joined
            CHECK (left_at IS NULL OR left_at > joined_at)
    )
    """,
    """
    CREATE UNIQUE INDEX uq_user_group_current_owner ON user_group (family_group_id)
        WHERE role = 'owner' AND left_at IS NULL
    """,
    """
    CREATE TABLE group_invitation (
        id UUID CONSTRAINT pk_group_invitation PRIMARY KEY DEFAULT gen_random_uuid(),
        family_group_id UUID NOT NULL
            CONSTRAINT fk_group_invitation_family_group REFERENCES family_group (id),
        created_by UUID NOT NULL
            CONSTRAINT fk_group_invitation_created_by REFERENCES app_user (id),
        code_hash TEXT NOT NULL CONSTRAINT uq_group_invitation_code_hash UNIQUE,
        expires_at TIMESTAMPTZ NOT NULL,
        used_by UUID CONSTRAINT fk_group_invitation_used_by REFERENCES app_user (id),
        used_at TIMESTAMPTZ,
        revoked_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_group_invitation_used_together
            CHECK ((used_by IS NULL) = (used_at IS NULL)),
        CONSTRAINT ck_group_invitation_used_not_revoked
            CHECK (used_at IS NULL OR revoked_at IS NULL),
        CONSTRAINT ck_group_invitation_expires_after_created CHECK (expires_at > created_at)
    )
    """,
    """
    CREATE TABLE financial_profile (
        user_id UUID CONSTRAINT pk_financial_profile PRIMARY KEY
            CONSTRAINT fk_financial_profile_user REFERENCES app_user (id),
        income_range TEXT,
        dependents INTEGER,
        has_debts BOOLEAN,
        emergency_fund_months NUMERIC(4, 1),
        main_goal TEXT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        -- The amounts of each range live in the configuration, so inflation needs no migration.
        CONSTRAINT ck_financial_profile_income_range CHECK (
            income_range IS NULL
            OR income_range IN ('range_1', 'range_2', 'range_3', 'range_4', 'range_5')
        ),
        CONSTRAINT ck_financial_profile_dependents
            CHECK (dependents IS NULL OR dependents >= 0),
        CONSTRAINT ck_financial_profile_emergency_fund_months
            CHECK (emergency_fund_months IS NULL OR emergency_fund_months >= 0),
        CONSTRAINT ck_financial_profile_main_goal CHECK (
            main_goal IS NULL
            OR main_goal IN ('save', 'pay_debts', 'emergency_fund', 'invest')
        )
    )
    """,
    """
    CREATE TABLE llm_usage (
        user_id UUID NOT NULL CONSTRAINT fk_llm_usage_user REFERENCES app_user (id),
        usage_date DATE NOT NULL,
        quota TEXT NOT NULL,
        message_count INTEGER NOT NULL DEFAULT 0,
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT pk_llm_usage PRIMARY KEY (user_id, usage_date, quota),
        CONSTRAINT ck_llm_usage_quota
            CHECK (quota IN ('registration', 'query', 'advice', 'classification')),
        CONSTRAINT ck_llm_usage_message_count CHECK (message_count >= 0)
    )
    """,
    """
    CREATE TABLE login_code (
        id UUID CONSTRAINT pk_login_code PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_login_code_user REFERENCES app_user (id),
        purpose TEXT NOT NULL,
        code_hash TEXT NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        used_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_login_code_purpose CHECK (purpose IN ('login', 'account_deletion')),
        CONSTRAINT ck_login_code_attempts CHECK (attempts BETWEEN 0 AND 5)
    )
    """,
    """
    CREATE TABLE session (
        id UUID CONSTRAINT pk_session PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_session_user REFERENCES app_user (id),
        token_hash TEXT NOT NULL CONSTRAINT uq_session_token_hash UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at TIMESTAMPTZ NOT NULL,
        revoked_at TIMESTAMPTZ,
        CONSTRAINT ck_session_expires_after_created CHECK (expires_at > created_at)
    )
    """,
    """
    CREATE TABLE dev_access_link (
        id UUID CONSTRAINT pk_dev_access_link PRIMARY KEY DEFAULT gen_random_uuid(),
        label TEXT NOT NULL CONSTRAINT uq_dev_access_link_label UNIQUE,
        user_id UUID CONSTRAINT uq_dev_access_link_user_id UNIQUE
            CONSTRAINT fk_dev_access_link_user REFERENCES app_user (id),
        token_hash TEXT NOT NULL CONSTRAINT uq_dev_access_link_token_hash UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE auth_throttle (
        id UUID CONSTRAINT pk_auth_throttle PRIMARY KEY DEFAULT gen_random_uuid(),
        key_type TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        event TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_auth_throttle_key_type CHECK (key_type IN ('phone', 'ip')),
        CONSTRAINT ck_auth_throttle_event CHECK (
            event IN ('code_request', 'token_failure', 'invite_failure', 'not_enabled_notice')
        )
    )
    """,
    """
    CREATE INDEX ix_auth_throttle_key_event
        ON auth_throttle (key_type, key_hash, event, created_at)
    """,
    """
    CREATE TABLE allowed_phone (
        id UUID CONSTRAINT pk_allowed_phone PRIMARY KEY DEFAULT gen_random_uuid(),
        phone_hash TEXT NOT NULL CONSTRAINT uq_allowed_phone_phone_hash UNIQUE,
        enabled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        disabled_at TIMESTAMPTZ,
        CONSTRAINT ck_allowed_phone_disabled_after_enabled
            CHECK (disabled_at IS NULL OR disabled_at > enabled_at)
    )
    """,
    """
    CREATE TABLE indicator_value (
        id UUID CONSTRAINT pk_indicator_value PRIMARY KEY DEFAULT gen_random_uuid(),
        source TEXT NOT NULL,
        value NUMERIC(24, 10) NOT NULL,
        value_date DATE NOT NULL,
        fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_indicator_value_source_date UNIQUE (source, value_date)
    )
    """,
    """
    CREATE TABLE exchange_rate (
        id UUID CONSTRAINT pk_exchange_rate PRIMARY KEY DEFAULT gen_random_uuid(),
        source TEXT NOT NULL,
        base_currency CHAR(3) NOT NULL
            CONSTRAINT fk_exchange_rate_base_currency REFERENCES currency (code),
        quote_currency CHAR(3) NOT NULL
            CONSTRAINT fk_exchange_rate_quote_currency REFERENCES currency (code),
        rate NUMERIC(24, 10) NOT NULL,
        rate_at TIMESTAMPTZ NOT NULL,
        fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_exchange_rate_rate CHECK (rate > 0),
        CONSTRAINT uq_exchange_rate_source_pair_rate_at
            UNIQUE (source, base_currency, quote_currency, rate_at)
    )
    """,
    """
    CREATE TABLE category (
        id UUID CONSTRAINT pk_category PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        user_id UUID CONSTRAINT fk_category_user REFERENCES app_user (id),
        is_base BOOLEAN NOT NULL DEFAULT FALSE,
        kind TEXT NOT NULL,
        CONSTRAINT ck_category_kind CHECK (kind IN ('expense', 'income')),
        CONSTRAINT uq_category_id_kind UNIQUE (id, kind)
    )
    """,
    "CREATE UNIQUE INDEX uq_category_user_name ON category (user_id, lower(name))",
    """
    CREATE UNIQUE INDEX uq_category_base_name ON category (lower(name))
        WHERE user_id IS NULL
    """,
    """
    CREATE TABLE budget_period (
        id UUID CONSTRAINT pk_budget_period PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID CONSTRAINT fk_budget_period_user REFERENCES app_user (id),
        family_group_id UUID
            CONSTRAINT fk_budget_period_family_group REFERENCES family_group (id),
        period_type TEXT NOT NULL,
        period_start DATE NOT NULL,
        period_end DATE NOT NULL,
        primary_currency CHAR(3) NOT NULL
            CONSTRAINT fk_budget_period_primary_currency REFERENCES currency (code),
        estimated_income NUMERIC(20, 2) NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_budget_period_one_owner
            CHECK (num_nonnulls(user_id, family_group_id) = 1),
        CONSTRAINT ck_budget_period_period_type
            CHECK (period_type IN ('monthly', 'biweekly')),
        CONSTRAINT ck_budget_period_status CHECK (status IN ('draft', 'confirmed')),
        CONSTRAINT ck_budget_period_dates CHECK (period_end >= period_start),
        CONSTRAINT ex_budget_period_user_overlap EXCLUDE USING gist (
            user_id WITH =, daterange(period_start, period_end, '[]') WITH &&
        ) WHERE (user_id IS NOT NULL),
        CONSTRAINT ex_budget_period_group_overlap EXCLUDE USING gist (
            family_group_id WITH =, daterange(period_start, period_end, '[]') WITH &&
        ) WHERE (family_group_id IS NOT NULL)
    )
    """,
    """
    CREATE TABLE budget (
        id UUID CONSTRAINT pk_budget PRIMARY KEY DEFAULT gen_random_uuid(),
        budget_period_id UUID NOT NULL
            CONSTRAINT fk_budget_budget_period REFERENCES budget_period (id),
        category_id UUID NOT NULL CONSTRAINT fk_budget_category REFERENCES category (id),
        limit_amount NUMERIC(20, 2) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_budget_limit_amount CHECK (limit_amount > 0),
        CONSTRAINT uq_budget_period_category UNIQUE (budget_period_id, category_id)
    )
    """,
    """
    CREATE TABLE account (
        id UUID CONSTRAINT pk_account PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_account_user REFERENCES app_user (id),
        name TEXT NOT NULL,
        institution TEXT,
        type TEXT NOT NULL,
        currency CHAR(3) NOT NULL CONSTRAINT fk_account_currency REFERENCES currency (code),
        initial_balance NUMERIC(20, 2) NOT NULL DEFAULT 0,
        closing_day INTEGER,
        due_day INTEGER,
        uses_linked_cards BOOLEAN,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_account_type CHECK (
            type IN (
                'bank_account', 'digital_wallet', 'broker', 'cash', 'credit_card', 'receivable'
            )
        ),
        CONSTRAINT ck_account_card_days CHECK (
            CASE
                WHEN type = 'credit_card' THEN closing_day IS NOT NULL AND due_day IS NOT NULL
                ELSE closing_day IS NULL AND due_day IS NULL
            END
        ),
        CONSTRAINT ck_account_closing_day
            CHECK (closing_day IS NULL OR closing_day BETWEEN 1 AND 31),
        CONSTRAINT ck_account_due_day CHECK (due_day IS NULL OR due_day BETWEEN 1 AND 31),
        CONSTRAINT ck_account_uses_linked_cards
            CHECK (uses_linked_cards IS NULL OR type = 'digital_wallet'),
        CONSTRAINT uq_account_id_user UNIQUE (id, user_id),
        CONSTRAINT uq_account_id_user_currency UNIQUE (id, user_id, currency)
    )
    """,
    "CREATE UNIQUE INDEX uq_account_user_name ON account (user_id, lower(name))",
    """
    CREATE TABLE card_statement (
        id UUID CONSTRAINT pk_card_statement PRIMARY KEY DEFAULT gen_random_uuid(),
        account_id UUID NOT NULL CONSTRAINT fk_card_statement_account REFERENCES account (id),
        closing_date DATE NOT NULL,
        due_date DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        exchange_rate NUMERIC(24, 10),
        CONSTRAINT ck_card_statement_due_after_closing CHECK (due_date > closing_date),
        CONSTRAINT ck_card_statement_status
            CHECK (status IN ('open', 'closed', 'reconciled')),
        CONSTRAINT ck_card_statement_exchange_rate
            CHECK (exchange_rate IS NULL OR exchange_rate > 0),
        CONSTRAINT uq_card_statement_account_closing UNIQUE (account_id, closing_date),
        CONSTRAINT uq_card_statement_account_due UNIQUE (account_id, due_date)
    )
    """,
    """
    CREATE TABLE recurring_rule (
        id UUID CONSTRAINT pk_recurring_rule PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_recurring_rule_user REFERENCES app_user (id),
        category_id UUID NOT NULL,
        type TEXT NOT NULL,
        account_id UUID NOT NULL,
        budget_user_id UUID
            CONSTRAINT fk_recurring_rule_budget_user REFERENCES app_user (id),
        budget_family_group_id UUID
            CONSTRAINT fk_recurring_rule_budget_family_group REFERENCES family_group (id),
        amount NUMERIC(20, 2) NOT NULL,
        amount_varies BOOLEAN NOT NULL DEFAULT FALSE,
        amount_confirmed_until DATE,
        currency CHAR(3) NOT NULL
            CONSTRAINT fk_recurring_rule_currency REFERENCES currency (code),
        description TEXT,
        frequency TEXT NOT NULL,
        execution_day INTEGER,
        next_execution DATE NOT NULL,
        occurrences INTEGER,
        generated_occurrences INTEGER NOT NULL DEFAULT 0,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ,
        updated_by UUID CONSTRAINT fk_recurring_rule_updated_by REFERENCES app_user (id),
        deleted_at TIMESTAMPTZ,
        deleted_by UUID CONSTRAINT fk_recurring_rule_deleted_by REFERENCES app_user (id),
        CONSTRAINT fk_recurring_rule_category_kind
            FOREIGN KEY (category_id, type) REFERENCES category (id, kind),
        CONSTRAINT fk_recurring_rule_account
            FOREIGN KEY (account_id, user_id, currency)
            REFERENCES account (id, user_id, currency),
        CONSTRAINT ck_recurring_rule_type CHECK (type IN ('expense', 'income')),
        CONSTRAINT ck_recurring_rule_one_budget_owner
            CHECK (num_nonnulls(budget_user_id, budget_family_group_id) = 1),
        CONSTRAINT ck_recurring_rule_budget_user
            CHECK (budget_user_id IS NULL OR budget_user_id = user_id),
        CONSTRAINT ck_recurring_rule_amount CHECK (amount > 0),
        CONSTRAINT ck_recurring_rule_frequency
            CHECK (frequency IN ('weekly', 'monthly', 'yearly')),
        CONSTRAINT ck_recurring_rule_execution_day CHECK (
            CASE frequency
                WHEN 'weekly' THEN execution_day IS NOT NULL AND execution_day BETWEEN 1 AND 7
                WHEN 'monthly' THEN execution_day IS NOT NULL AND execution_day BETWEEN 1 AND 31
                WHEN 'yearly' THEN execution_day IS NULL
                ELSE TRUE
            END
        ),
        CONSTRAINT ck_recurring_rule_occurrences
            CHECK (occurrences IS NULL OR occurrences >= 1),
        CONSTRAINT ck_recurring_rule_generated_occurrences CHECK (
            generated_occurrences >= 0
            AND (occurrences IS NULL OR generated_occurrences <= occurrences)
        ),
        CONSTRAINT ck_recurring_rule_varies_without_end
            CHECK (NOT amount_varies OR occurrences IS NULL),
        CONSTRAINT ck_recurring_rule_confirmed_until
            CHECK (amount_confirmed_until IS NULL OR amount_varies),
        CONSTRAINT ck_recurring_rule_updated_by
            CHECK (updated_by IS NULL OR updated_at IS NOT NULL),
        CONSTRAINT ck_recurring_rule_deleted_by
            CHECK (deleted_by IS NULL OR deleted_at IS NOT NULL)
    )
    """,
    """
    CREATE TABLE transaction (
        id UUID CONSTRAINT pk_transaction PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_transaction_user REFERENCES app_user (id),
        account_id UUID NOT NULL,
        budget_period_id UUID NOT NULL
            CONSTRAINT fk_transaction_budget_period REFERENCES budget_period (id),
        category_id UUID NOT NULL,
        recurring_rule_id UUID
            CONSTRAINT fk_transaction_recurring_rule REFERENCES recurring_rule (id),
        occurrence_date DATE,
        duplicate_of UUID,
        refund_of UUID,
        paired_with UUID,
        amount NUMERIC(20, 2) NOT NULL,
        currency CHAR(3) NOT NULL
            CONSTRAINT fk_transaction_currency REFERENCES currency (code),
        exchange_rate NUMERIC(24, 10),
        type TEXT NOT NULL,
        source TEXT NOT NULL,
        description TEXT,
        transaction_date DATE NOT NULL,
        client_request_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ,
        updated_by UUID CONSTRAINT fk_transaction_updated_by REFERENCES app_user (id),
        deleted_at TIMESTAMPTZ,
        deleted_by UUID CONSTRAINT fk_transaction_deleted_by REFERENCES app_user (id),
        CONSTRAINT uq_transaction_user_id UNIQUE (user_id, id),
        CONSTRAINT fk_transaction_account_user
            FOREIGN KEY (account_id, user_id) REFERENCES account (id, user_id),
        CONSTRAINT fk_transaction_category_kind
            FOREIGN KEY (category_id, type) REFERENCES category (id, kind),
        CONSTRAINT fk_transaction_duplicate_of
            FOREIGN KEY (user_id, duplicate_of) REFERENCES transaction (user_id, id),
        CONSTRAINT fk_transaction_refund_of
            FOREIGN KEY (user_id, refund_of) REFERENCES transaction (user_id, id),
        CONSTRAINT fk_transaction_paired_with
            FOREIGN KEY (user_id, paired_with) REFERENCES transaction (user_id, id)
            DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT ck_transaction_amount CHECK (amount > 0),
        CONSTRAINT ck_transaction_type CHECK (type IN ('expense', 'income')),
        CONSTRAINT ck_transaction_source CHECK (source IN ('manual', 'automatic')),
        CONSTRAINT ck_transaction_exchange_rate
            CHECK (exchange_rate IS NULL OR exchange_rate > 0),
        CONSTRAINT ck_transaction_refund_only_income
            CHECK (refund_of IS NULL OR type = 'income'),
        CONSTRAINT ck_transaction_rule_occurrence_together
            CHECK ((recurring_rule_id IS NULL) = (occurrence_date IS NULL)),
        CONSTRAINT ck_transaction_updated_by
            CHECK (updated_by IS NULL OR updated_at IS NOT NULL),
        CONSTRAINT ck_transaction_deleted_by
            CHECK (deleted_by IS NULL OR deleted_at IS NOT NULL),
        CONSTRAINT uq_transaction_user_client_request UNIQUE (user_id, client_request_id),
        CONSTRAINT uq_transaction_rule_occurrence UNIQUE (recurring_rule_id, occurrence_date)
    )
    """,
    # For the duplicate check between manual and automatic movements (domain rules, § 7).
    """
    CREATE INDEX ix_transaction_duplicate_check
        ON transaction (user_id, source, currency, amount, transaction_date)
    """,
    "CREATE INDEX ix_transaction_account ON transaction (account_id)",
    """
    CREATE INDEX ix_transaction_period_category
        ON transaction (budget_period_id, category_id)
    """,
    """
    CREATE TABLE transfer (
        id UUID CONSTRAINT pk_transfer PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_transfer_user REFERENCES app_user (id),
        from_account_id UUID NOT NULL,
        from_amount NUMERIC(20, 2) NOT NULL,
        from_currency CHAR(3) NOT NULL
            CONSTRAINT fk_transfer_from_currency REFERENCES currency (code),
        to_account_id UUID NOT NULL,
        to_amount NUMERIC(20, 2) NOT NULL,
        to_currency CHAR(3) NOT NULL
            CONSTRAINT fk_transfer_to_currency REFERENCES currency (code),
        exchange_rate NUMERIC(24, 10),
        transfer_date DATE NOT NULL,
        description TEXT,
        source TEXT NOT NULL,
        client_request_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ,
        updated_by UUID CONSTRAINT fk_transfer_updated_by REFERENCES app_user (id),
        deleted_at TIMESTAMPTZ,
        deleted_by UUID CONSTRAINT fk_transfer_deleted_by REFERENCES app_user (id),
        CONSTRAINT fk_transfer_from_account
            FOREIGN KEY (from_account_id, user_id, from_currency)
            REFERENCES account (id, user_id, currency),
        CONSTRAINT fk_transfer_to_account
            FOREIGN KEY (to_account_id, user_id, to_currency)
            REFERENCES account (id, user_id, currency),
        CONSTRAINT ck_transfer_from_amount CHECK (from_amount > 0),
        CONSTRAINT ck_transfer_to_amount CHECK (to_amount > 0),
        CONSTRAINT ck_transfer_distinct_accounts CHECK (from_account_id <> to_account_id),
        CONSTRAINT ck_transfer_currencies CHECK (
            (from_currency = to_currency AND from_amount = to_amount AND exchange_rate IS NULL)
            OR (from_currency <> to_currency AND exchange_rate IS NOT NULL)
        ),
        CONSTRAINT ck_transfer_exchange_rate
            CHECK (exchange_rate IS NULL OR exchange_rate > 0),
        CONSTRAINT ck_transfer_source CHECK (source IN ('manual', 'automatic')),
        CONSTRAINT ck_transfer_updated_by
            CHECK (updated_by IS NULL OR updated_at IS NOT NULL),
        CONSTRAINT ck_transfer_deleted_by
            CHECK (deleted_by IS NULL OR deleted_at IS NOT NULL),
        CONSTRAINT uq_transfer_user_client_request UNIQUE (user_id, client_request_id)
    )
    """,
    """
    CREATE TABLE inbound_message (
        id UUID CONSTRAINT pk_inbound_message PRIMARY KEY DEFAULT gen_random_uuid(),
        provider TEXT NOT NULL,
        provider_message_id TEXT NOT NULL,
        user_id UUID CONSTRAINT fk_inbound_message_user REFERENCES app_user (id),
        from_phone TEXT,
        quoted_outbound_message_id UUID,
        payload JSONB,
        purged_at TIMESTAMPTZ,
        sent_at TIMESTAMPTZ NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        locked_until TIMESTAMPTZ,
        processed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_inbound_message_provider CHECK (provider IN ('meta', 'twilio', 'web')),
        CONSTRAINT ck_inbound_message_status
            CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
        CONSTRAINT ck_inbound_message_web_user
            CHECK (provider <> 'web' OR user_id IS NOT NULL),
        CONSTRAINT ck_inbound_message_purge CHECK (
            (purged_at IS NULL AND payload IS NOT NULL AND from_phone IS NOT NULL)
            OR (purged_at IS NOT NULL AND payload IS NULL AND from_phone IS NULL)
        ),
        CONSTRAINT uq_inbound_message_provider_message UNIQUE (provider, provider_message_id)
    )
    """,
    # How the worker takes the next message of each sender (ADR 0010).
    """
    CREATE INDEX ix_inbound_message_sender_queue
        ON inbound_message (from_phone, status, sent_at)
    """,
    """
    CREATE TABLE outbound_message (
        id UUID CONSTRAINT pk_outbound_message PRIMARY KEY DEFAULT gen_random_uuid(),
        provider TEXT NOT NULL,
        user_id UUID CONSTRAINT fk_outbound_message_user REFERENCES app_user (id),
        to_phone TEXT,
        inbound_message_id UUID
            CONSTRAINT fk_outbound_message_inbound_message REFERENCES inbound_message (id),
        content JSONB,
        purged_at TIMESTAMPTZ,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        provider_message_id TEXT,
        sent_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_outbound_message_provider CHECK (provider IN ('meta', 'twilio', 'web')),
        CONSTRAINT ck_outbound_message_status CHECK (status IN ('pending', 'sent', 'failed')),
        CONSTRAINT ck_outbound_message_purge CHECK (
            (purged_at IS NULL AND content IS NOT NULL AND to_phone IS NOT NULL)
            OR (purged_at IS NOT NULL AND content IS NULL AND to_phone IS NULL)
        ),
        CONSTRAINT ck_outbound_message_response_kind CHECK (
            content IS NULL
            OR COALESCE(
                content ->> 'response_kind' IN (
                    'registration',
                    'query',
                    'advice_information',
                    'advice_education',
                    'advice_decision',
                    'advice_limit_explained',
                    'advice_limit_fixed',
                    'fixed_text',
                    'proactive'
                ),
                FALSE
            )
        ),
        CONSTRAINT uq_outbound_message_id_user UNIQUE (id, user_id),
        CONSTRAINT uq_outbound_message_provider_message UNIQUE (provider, provider_message_id)
    )
    """,
    """
    CREATE INDEX ix_outbound_message_send_queue
        ON outbound_message (status, next_attempt_at)
    """,
    # The two message tables point at each other, so this one is added once both exist.
    """
    ALTER TABLE inbound_message ADD CONSTRAINT fk_inbound_message_quoted_outbound
        FOREIGN KEY (quoted_outbound_message_id, user_id)
        REFERENCES outbound_message (id, user_id)
    """,
    """
    CREATE TABLE sent_alert (
        id UUID CONSTRAINT pk_sent_alert PRIMARY KEY DEFAULT gen_random_uuid(),
        budget_id UUID NOT NULL CONSTRAINT fk_sent_alert_budget REFERENCES budget (id),
        threshold INTEGER NOT NULL,
        user_id UUID NOT NULL CONSTRAINT fk_sent_alert_user REFERENCES app_user (id),
        outbound_message_id UUID NOT NULL
            CONSTRAINT fk_sent_alert_outbound_message REFERENCES outbound_message (id),
        sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_sent_alert_threshold CHECK (threshold BETWEEN 1 AND 100),
        CONSTRAINT uq_sent_alert_budget_threshold_user UNIQUE (budget_id, threshold, user_id)
    )
    """,
    """
    CREATE TABLE pending_batch (
        id UUID CONSTRAINT pk_pending_batch PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_pending_batch_user REFERENCES app_user (id),
        source TEXT NOT NULL,
        awaiting_reply BOOLEAN NOT NULL DEFAULT FALSE,
        question_message_id UUID
            CONSTRAINT fk_pending_batch_question_message REFERENCES outbound_message (id),
        confirmation_message_id UUID
            CONSTRAINT fk_pending_batch_confirmation_message REFERENCES outbound_message (id),
        status TEXT NOT NULL DEFAULT 'open',
        reminded_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_pending_batch_source CHECK (source IN ('manual', 'automatic')),
        CONSTRAINT ck_pending_batch_status CHECK (status IN ('open', 'closed')),
        CONSTRAINT ck_pending_batch_closed_not_awaiting
            CHECK (NOT (status = 'closed' AND awaiting_reply)),
        CONSTRAINT uq_pending_batch_id_source UNIQUE (id, source)
    )
    """,
    """
    CREATE UNIQUE INDEX uq_pending_batch_user_awaiting ON pending_batch (user_id)
        WHERE awaiting_reply
    """,
    # To find the batch of a reply that quotes a message (domain rules, § 5 and § 15).
    "CREATE INDEX ix_pending_batch_question_message ON pending_batch (question_message_id)",
    """
    CREATE INDEX ix_pending_batch_confirmation_message
        ON pending_batch (confirmation_message_id)
    """,
    """
    CREATE TABLE pending_transaction (
        id UUID CONSTRAINT pk_pending_transaction PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL CONSTRAINT fk_pending_transaction_user REFERENCES app_user (id),
        intent TEXT NOT NULL DEFAULT 'transaction',
        parsed_data JSONB NOT NULL,
        missing_fields TEXT[] NOT NULL,
        source TEXT NOT NULL,
        batch_id UUID NOT NULL,
        position INTEGER NOT NULL,
        recurring_rule_id UUID
            CONSTRAINT fk_pending_transaction_recurring_rule REFERENCES recurring_rule (id),
        occurrence_date DATE,
        raw_input TEXT,
        resulting_transaction_id UUID
            CONSTRAINT uq_pending_transaction_resulting_transaction UNIQUE
            CONSTRAINT fk_pending_transaction_resulting_transaction
                REFERENCES transaction (id),
        resulting_transfer_id UUID
            CONSTRAINT uq_pending_transaction_resulting_transfer UNIQUE
            CONSTRAINT fk_pending_transaction_resulting_transfer REFERENCES transfer (id),
        resulting_recurring_rule_id UUID
            CONSTRAINT uq_pending_transaction_resulting_recurring_rule UNIQUE
            CONSTRAINT fk_pending_transaction_resulting_recurring_rule
                REFERENCES recurring_rule (id),
        status TEXT NOT NULL DEFAULT 'open',
        resolved_by UUID
            CONSTRAINT fk_pending_transaction_resolved_by REFERENCES app_user (id),
        expires_at TIMESTAMPTZ,
        corrected_fields_count INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT fk_pending_transaction_batch_source
            FOREIGN KEY (batch_id, source) REFERENCES pending_batch (id, source),
        CONSTRAINT ck_pending_transaction_intent
            CHECK (intent IN ('transaction', 'transfer', 'recurring_rule', 'change')),
        CONSTRAINT ck_pending_transaction_source CHECK (source IN ('manual', 'automatic')),
        CONSTRAINT ck_pending_transaction_status
            CHECK (status IN ('open', 'promoted', 'rejected', 'expired')),
        CONSTRAINT ck_pending_transaction_position CHECK (position BETWEEN 1 AND 10),
        CONSTRAINT ck_pending_transaction_corrected_fields_count
            CHECK (corrected_fields_count >= 0),
        -- Promoted if and only if the result column of its intent is set; a change has none.
        CONSTRAINT ck_pending_transaction_result CHECK (
            (resulting_transaction_id IS NULL OR intent = 'transaction')
            AND (resulting_transfer_id IS NULL OR intent = 'transfer')
            AND (resulting_recurring_rule_id IS NULL OR intent = 'recurring_rule')
            AND (
                (status = 'promoted' AND intent IN ('transaction', 'transfer', 'recurring_rule'))
                = (
                    num_nonnulls(
                        resulting_transaction_id,
                        resulting_transfer_id,
                        resulting_recurring_rule_id
                    ) = 1
                )
            )
        ),
        CONSTRAINT ck_pending_transaction_rule_intent
            CHECK (recurring_rule_id IS NULL OR intent = 'transaction'),
        CONSTRAINT ck_pending_transaction_rule_occurrence_together
            CHECK ((recurring_rule_id IS NULL) = (occurrence_date IS NULL)),
        CONSTRAINT ck_pending_transaction_expires_iff_no_rule
            CHECK ((expires_at IS NULL) = (recurring_rule_id IS NOT NULL)),
        CONSTRAINT uq_pending_transaction_batch_position UNIQUE (batch_id, position),
        CONSTRAINT uq_pending_transaction_rule_occurrence
            UNIQUE (recurring_rule_id, occurrence_date)
    )
    """,
    "CREATE INDEX ix_pending_transaction_batch ON pending_transaction (batch_id)",
    """
    CREATE TABLE llm_call (
        id UUID CONSTRAINT pk_llm_call PRIMARY KEY DEFAULT gen_random_uuid(),
        inbound_message_id UUID
            CONSTRAINT fk_llm_call_inbound_message
                REFERENCES inbound_message (id) ON DELETE SET NULL,
        purpose TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        prompt_version TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        duration_ms INTEGER NOT NULL,
        estimated_cost_usd NUMERIC(12, 6),
        outcome TEXT NOT NULL,
        retrieval JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_llm_call_purpose CHECK (
            purpose IN ('classification', 'interpretation', 'query', 'advice', 'embedding')
        ),
        CONSTRAINT ck_llm_call_outcome CHECK (
            outcome IN ('ok', 'invalid_output', 'blocked', 'provider_error', 'timeout')
        ),
        CONSTRAINT ck_llm_call_duration_ms CHECK (duration_ms >= 0),
        CONSTRAINT ck_llm_call_estimated_cost_usd
            CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0)
    )
    """,
    # The metrics group by these two (ADR 0023).
    "CREATE INDEX ix_llm_call_created_purpose ON llm_call (created_at, purpose)",
)

CREATE_FUNCTIONS: tuple[str, ...] = (
    # ADR 0014 and 0015: when and who, on every change and on every logical deletion. The
    # application says who with SET LOCAL app.actor_id; a scheduled process says nothing.
    """
    CREATE FUNCTION mark_change() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
        actor UUID := CAST(NULLIF(current_setting('app.actor_id', TRUE), '') AS UUID);
    BEGIN
        NEW.updated_at := now();
        NEW.updated_by := actor;
        IF NEW.deleted_at IS NULL THEN
            NEW.deleted_by := NULL;
        ELSIF OLD.deleted_at IS NULL THEN
            NEW.deleted_by := actor;
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE FUNCTION account_keep_currency() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.currency IS DISTINCT FROM OLD.currency THEN
            RAISE EXCEPTION 'the currency of an account never changes'
                USING ERRCODE = 'check_violation',
                      TABLE = 'account',
                      CONSTRAINT = 'tg_account_currency_immutable';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE FUNCTION category_reject_base_name() RETURNS trigger LANGUAGE plpgsql AS $$
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
    """,
    """
    CREATE FUNCTION budget_period_validate_update() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF OLD.status = 'confirmed'
            AND NEW.primary_currency IS DISTINCT FROM OLD.primary_currency THEN
            RAISE EXCEPTION 'the currency of a confirmed period does not change'
                USING ERRCODE = 'check_violation',
                      TABLE = 'budget_period',
                      CONSTRAINT = 'tg_budget_period_currency_fixed';
        END IF;
        IF NEW.status = 'draft' AND OLD.status <> 'draft' AND EXISTS (
            SELECT 1 FROM transaction WHERE budget_period_id = OLD.id
        ) THEN
            RAISE EXCEPTION 'a period with movements does not go back to draft'
                USING ERRCODE = 'check_violation',
                      TABLE = 'budget_period',
                      CONSTRAINT = 'tg_budget_period_draft_with_transactions';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    # What a CHECK cannot see because it lives in another row: the account, the period and the
    # movement a refund points to. A missing or foreign reference is left to its foreign key.
    """
    CREATE FUNCTION transaction_validate() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
        account_type TEXT;
        account_currency CHAR(3);
        account_opened_on DATE;
        account_found BOOLEAN;
        period_status TEXT;
        period_currency CHAR(3);
        period_found BOOLEAN;
        currencies INTEGER;
        refunded_type TEXT;
    BEGIN
        SELECT a.type,
               a.currency,
               CAST(a.created_at AT TIME ZONE COALESCE(u.time_zone, 'UTC') AS DATE)
          INTO account_type, account_currency, account_opened_on
          FROM account a
          JOIN app_user u ON u.id = a.user_id
         WHERE a.id = NEW.account_id;
        account_found := FOUND;

        SELECT p.status, p.primary_currency
          INTO period_status, period_currency
          FROM budget_period p
         WHERE p.id = NEW.budget_period_id;
        period_found := FOUND;

        IF account_found AND account_type = 'broker' THEN
            RAISE EXCEPTION 'a broker account only takes transfers'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transaction',
                      CONSTRAINT = 'tg_transaction_broker_account';
        END IF;
        IF account_found AND NEW.transaction_date < account_opened_on THEN
            RAISE EXCEPTION 'a movement is not dated before its account was opened'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transaction',
                      CONSTRAINT = 'tg_transaction_before_account';
        END IF;
        IF period_found AND period_status <> 'confirmed' THEN
            RAISE EXCEPTION 'a movement is charged only to a confirmed period'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transaction',
                      CONSTRAINT = 'tg_transaction_period_confirmed';
        END IF;

        IF account_found AND period_found AND NEW.currency IS NOT NULL THEN
            SELECT count(DISTINCT code) INTO currencies
              FROM unnest(ARRAY[NEW.currency, account_currency, period_currency]) AS code;
            IF currencies > 2 THEN
                RAISE EXCEPTION 'a movement involves at most two currencies'
                    USING ERRCODE = 'check_violation',
                          TABLE = 'transaction',
                          CONSTRAINT = 'tg_transaction_three_currencies';
            END IF;
            IF currencies = 2 AND NEW.exchange_rate IS NULL THEN
                RAISE EXCEPTION 'a movement in another currency needs its exchange rate'
                    USING ERRCODE = 'check_violation',
                          TABLE = 'transaction',
                          CONSTRAINT = 'tg_transaction_rate_missing';
            END IF;
            IF currencies = 1 AND NEW.exchange_rate IS NOT NULL THEN
                RAISE EXCEPTION 'a movement in a single currency carries no exchange rate'
                    USING ERRCODE = 'check_violation',
                          TABLE = 'transaction',
                          CONSTRAINT = 'tg_transaction_rate_unexpected';
            END IF;
        END IF;

        IF NEW.refund_of IS NOT NULL THEN
            SELECT t.type INTO refunded_type
              FROM transaction t
             WHERE t.id = NEW.refund_of AND t.user_id = NEW.user_id;
            IF FOUND AND refunded_type <> 'expense' THEN
                RAISE EXCEPTION 'a refund points to an expense'
                    USING ERRCODE = 'check_violation',
                          TABLE = 'transaction',
                          CONSTRAINT = 'tg_transaction_refund_target';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    # The two halves of a withdrawal or a contribution are inserted in the same transaction,
    # so this runs at the commit, when both exist (domain rules, § 10).
    """
    CREATE FUNCTION transaction_validate_pair() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
        other transaction;
        own_is_group BOOLEAN;
        other_is_group BOOLEAN;
    BEGIN
        SELECT * INTO other
          FROM transaction t
         WHERE t.id = NEW.paired_with AND t.user_id = NEW.user_id;
        IF NOT FOUND THEN
            RETURN NULL;
        END IF;

        IF other.paired_with IS DISTINCT FROM NEW.id THEN
            RAISE EXCEPTION 'each half of a pair points to the other'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transaction',
                      CONSTRAINT = 'tg_transaction_pair_mutual';
        END IF;
        IF NOT (
            (NEW.type = 'expense' AND other.type = 'income')
            OR (NEW.type = 'income' AND other.type = 'expense')
        ) THEN
            RAISE EXCEPTION 'a pair is an expense and an income'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transaction',
                      CONSTRAINT = 'tg_transaction_pair_types';
        END IF;
        IF NEW.amount <> other.amount
            OR NEW.currency <> other.currency
            OR NEW.transaction_date <> other.transaction_date
            OR NEW.exchange_rate IS DISTINCT FROM other.exchange_rate THEN
            RAISE EXCEPTION 'the halves of a pair share amount, currency, date and rate'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transaction',
                      CONSTRAINT = 'tg_transaction_pair_mismatch';
        END IF;

        SELECT p.family_group_id IS NOT NULL INTO own_is_group
          FROM budget_period p WHERE p.id = NEW.budget_period_id;
        SELECT p.family_group_id IS NOT NULL INTO other_is_group
          FROM budget_period p WHERE p.id = other.budget_period_id;
        IF own_is_group = other_is_group THEN
            RAISE EXCEPTION 'a pair has one half in a group period and one in the individual'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transaction',
                      CONSTRAINT = 'tg_transaction_pair_periods';
        END IF;
        RETURN NULL;
    END;
    $$
    """,
    """
    CREATE FUNCTION transfer_validate() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF EXISTS (
            SELECT 1
              FROM account a
              JOIN app_user u ON u.id = a.user_id
             WHERE a.id IN (NEW.from_account_id, NEW.to_account_id)
               AND NEW.transfer_date
                   < CAST(a.created_at AT TIME ZONE COALESCE(u.time_zone, 'UTC') AS DATE)
        ) THEN
            RAISE EXCEPTION 'a transfer is not dated before either account was opened'
                USING ERRCODE = 'check_violation',
                      TABLE = 'transfer',
                      CONSTRAINT = 'tg_transfer_before_account';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    CREATE FUNCTION recurring_rule_validate() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM account a WHERE a.id = NEW.account_id AND a.type = 'broker'
        ) THEN
            RAISE EXCEPTION 'a broker account only takes transfers'
                USING ERRCODE = 'check_violation',
                      TABLE = 'recurring_rule',
                      CONSTRAINT = 'tg_recurring_rule_broker_account';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
)

FUNCTIONS: tuple[str, ...] = (
    "mark_change",
    "account_keep_currency",
    "category_reject_base_name",
    "budget_period_validate_update",
    "transaction_validate",
    "transaction_validate_pair",
    "transfer_validate",
    "recurring_rule_validate",
)

CREATE_TRIGGERS: tuple[str, ...] = (
    """
    CREATE TRIGGER tg_account_keep_currency BEFORE UPDATE ON account
        FOR EACH ROW EXECUTE FUNCTION account_keep_currency()
    """,
    """
    CREATE TRIGGER tg_category_reject_base_name BEFORE INSERT OR UPDATE ON category
        FOR EACH ROW EXECUTE FUNCTION category_reject_base_name()
    """,
    """
    CREATE TRIGGER tg_budget_period_validate_update BEFORE UPDATE ON budget_period
        FOR EACH ROW EXECUTE FUNCTION budget_period_validate_update()
    """,
    """
    CREATE TRIGGER tg_transaction_validate BEFORE INSERT OR UPDATE ON transaction
        FOR EACH ROW EXECUTE FUNCTION transaction_validate()
    """,
    """
    CREATE CONSTRAINT TRIGGER tg_transaction_validate_pair
        AFTER INSERT OR UPDATE ON transaction
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW WHEN (NEW.paired_with IS NOT NULL)
        EXECUTE FUNCTION transaction_validate_pair()
    """,
    """
    CREATE TRIGGER tg_transfer_validate BEFORE INSERT OR UPDATE ON transfer
        FOR EACH ROW EXECUTE FUNCTION transfer_validate()
    """,
    """
    CREATE TRIGGER tg_recurring_rule_validate BEFORE INSERT OR UPDATE ON recurring_rule
        FOR EACH ROW EXECUTE FUNCTION recurring_rule_validate()
    """,
    """
    CREATE TRIGGER tg_transaction_mark_change BEFORE UPDATE ON transaction
        FOR EACH ROW EXECUTE FUNCTION mark_change()
    """,
    """
    CREATE TRIGGER tg_transfer_mark_change BEFORE UPDATE ON transfer
        FOR EACH ROW EXECUTE FUNCTION mark_change()
    """,
    """
    CREATE TRIGGER tg_recurring_rule_mark_change BEFORE UPDATE ON recurring_rule
        FOR EACH ROW EXECUTE FUNCTION mark_change()
    """,
)

# ISO 4217, the national currencies in use.
CURRENCIES: tuple[tuple[str, str], ...] = (
    ("AED", "Dírham de los Emiratos Árabes Unidos"),
    ("AFN", "Afgani afgano"),
    ("ALL", "Lek albanés"),
    ("AMD", "Dram armenio"),
    ("AOA", "Kwanza angoleño"),
    ("ARS", "Peso argentino"),
    ("AUD", "Dólar australiano"),
    ("AWG", "Florín arubeño"),
    ("AZN", "Manat azerbaiyano"),
    ("BAM", "Marco convertible de Bosnia y Herzegovina"),
    ("BBD", "Dólar de Barbados"),
    ("BDT", "Taka bangladesí"),
    ("BHD", "Dinar bareiní"),
    ("BIF", "Franco burundés"),
    ("BMD", "Dólar bermudeño"),
    ("BND", "Dólar de Brunéi"),
    ("BOB", "Boliviano"),
    ("BRL", "Real brasileño"),
    ("BSD", "Dólar bahameño"),
    ("BTN", "Ngultrum butanés"),
    ("BWP", "Pula botsuano"),
    ("BYN", "Rublo bielorruso"),
    ("BZD", "Dólar beliceño"),
    ("CAD", "Dólar canadiense"),
    ("CDF", "Franco congoleño"),
    ("CHF", "Franco suizo"),
    ("CLP", "Peso chileno"),
    ("CNY", "Yuan chino"),
    ("COP", "Peso colombiano"),
    ("CRC", "Colón costarricense"),
    ("CUP", "Peso cubano"),
    ("CVE", "Escudo caboverdiano"),
    ("CZK", "Corona checa"),
    ("DJF", "Franco yibutiano"),
    ("DKK", "Corona danesa"),
    ("DOP", "Peso dominicano"),
    ("DZD", "Dinar argelino"),
    ("EGP", "Libra egipcia"),
    ("ERN", "Nakfa eritreo"),
    ("ETB", "Birr etíope"),
    ("EUR", "Euro"),
    ("FJD", "Dólar fiyiano"),
    ("FKP", "Libra malvinense"),
    ("GBP", "Libra esterlina"),
    ("GEL", "Lari georgiano"),
    ("GHS", "Cedi ghanés"),
    ("GIP", "Libra gibraltareña"),
    ("GMD", "Dalasi gambiano"),
    ("GNF", "Franco guineano"),
    ("GTQ", "Quetzal guatemalteco"),
    ("GYD", "Dólar guyanés"),
    ("HKD", "Dólar de Hong Kong"),
    ("HNL", "Lempira hondureño"),
    ("HTG", "Gourde haitiano"),
    ("HUF", "Forinto húngaro"),
    ("IDR", "Rupia indonesia"),
    ("ILS", "Nuevo séquel israelí"),
    ("INR", "Rupia india"),
    ("IQD", "Dinar iraquí"),
    ("IRR", "Rial iraní"),
    ("ISK", "Corona islandesa"),
    ("JMD", "Dólar jamaiquino"),
    ("JOD", "Dinar jordano"),
    ("JPY", "Yen japonés"),
    ("KES", "Chelín keniano"),
    ("KGS", "Som kirguís"),
    ("KHR", "Riel camboyano"),
    ("KMF", "Franco comorense"),
    ("KPW", "Won norcoreano"),
    ("KRW", "Won surcoreano"),
    ("KWD", "Dinar kuwaití"),
    ("KYD", "Dólar de las Islas Caimán"),
    ("KZT", "Tenge kazajo"),
    ("LAK", "Kip laosiano"),
    ("LBP", "Libra libanesa"),
    ("LKR", "Rupia de Sri Lanka"),
    ("LRD", "Dólar liberiano"),
    ("LSL", "Loti lesotense"),
    ("LYD", "Dinar libio"),
    ("MAD", "Dírham marroquí"),
    ("MDL", "Leu moldavo"),
    ("MGA", "Ariary malgache"),
    ("MKD", "Denar macedonio"),
    ("MMK", "Kyat birmano"),
    ("MNT", "Tugrik mongol"),
    ("MOP", "Pataca macaense"),
    ("MRU", "Uguiya mauritana"),
    ("MUR", "Rupia mauriciana"),
    ("MVR", "Rufiya maldiva"),
    ("MWK", "Kwacha malauí"),
    ("MXN", "Peso mexicano"),
    ("MYR", "Ringgit malayo"),
    ("MZN", "Metical mozambiqueño"),
    ("NAD", "Dólar namibio"),
    ("NGN", "Naira nigeriana"),
    ("NIO", "Córdoba nicaragüense"),
    ("NOK", "Corona noruega"),
    ("NPR", "Rupia nepalí"),
    ("NZD", "Dólar neozelandés"),
    ("OMR", "Rial omaní"),
    ("PAB", "Balboa panameño"),
    ("PEN", "Sol peruano"),
    ("PGK", "Kina de Papúa Nueva Guinea"),
    ("PHP", "Peso filipino"),
    ("PKR", "Rupia pakistaní"),
    ("PLN", "Esloti polaco"),
    ("PYG", "Guaraní paraguayo"),
    ("QAR", "Riyal catarí"),
    ("RON", "Leu rumano"),
    ("RSD", "Dinar serbio"),
    ("RUB", "Rublo ruso"),
    ("RWF", "Franco ruandés"),
    ("SAR", "Riyal saudí"),
    ("SBD", "Dólar de las Islas Salomón"),
    ("SCR", "Rupia seychelense"),
    ("SDG", "Libra sudanesa"),
    ("SEK", "Corona sueca"),
    ("SGD", "Dólar de Singapur"),
    ("SHP", "Libra de Santa Elena"),
    ("SLE", "Leone sierraleonés"),
    ("SOS", "Chelín somalí"),
    ("SRD", "Dólar surinamés"),
    ("SSP", "Libra sursudanesa"),
    ("STN", "Dobra santotomense"),
    ("SVC", "Colón salvadoreño"),
    ("SYP", "Libra siria"),
    ("SZL", "Lilangeni suazi"),
    ("THB", "Baht tailandés"),
    ("TJS", "Somoni tayiko"),
    ("TMT", "Manat turcomano"),
    ("TND", "Dinar tunecino"),
    ("TOP", "Paanga tongano"),
    ("TRY", "Lira turca"),
    ("TTD", "Dólar de Trinidad y Tobago"),
    ("TWD", "Nuevo dólar taiwanés"),
    ("TZS", "Chelín tanzano"),
    ("UAH", "Grivna ucraniana"),
    ("UGX", "Chelín ugandés"),
    ("USD", "Dólar estadounidense"),
    ("UYU", "Peso uruguayo"),
    ("UZS", "Sum uzbeko"),
    ("VES", "Bolívar venezolano"),
    ("VND", "Dong vietnamita"),
    ("VUV", "Vatu vanuatuense"),
    ("WST", "Tala samoano"),
    ("XAF", "Franco CFA de África Central"),
    ("XCD", "Dólar del Caribe Oriental"),
    ("XCG", "Florín caribeño"),
    ("XOF", "Franco CFA de África Occidental"),
    ("XPF", "Franco CFP"),
    ("YER", "Rial yemení"),
    ("ZAR", "Rand sudafricano"),
    ("ZMW", "Kwacha zambiano"),
    ("ZWG", "Oro de Zimbabue"),
)

# The base catalog of domain rules § 4: daily use first, then the special ones.
BASE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Supermercado", "expense"),
    ("Comida afuera y delivery", "expense"),
    ("Vivienda", "expense"),
    ("Servicios", "expense"),
    ("Transporte", "expense"),
    ("Salud", "expense"),
    ("Educación", "expense"),
    ("Ropa", "expense"),
    ("Hogar", "expense"),
    ("Salidas y ocio", "expense"),
    ("Suscripciones", "expense"),
    ("Mascotas", "expense"),
    ("Regalos", "expense"),
    ("Impuestos y trámites", "expense"),
    ("Insumos", "expense"),
    ("Sueldo", "income"),
    ("Aguinaldo", "income"),
    ("Honorarios", "income"),
    ("Ventas", "income"),
    ("Jubilación y pensión", "income"),
    ("Otros ingresos", "income"),
    ("Intereses, impuestos y cargos", "expense"),
    ("Devoluciones y reintegros", "income"),
    ("Diferencia de cambio", "expense"),
    ("Diferencia de cambio a favor", "income"),
    ("Comisiones", "expense"),
    ("Faltantes sin identificar", "expense"),
    ("Sobrantes sin identificar", "income"),
    ("Rendimientos", "income"),
    ("Retiro del titular", "expense"),
    ("Retiro de la actividad", "income"),
    ("Aporte a la actividad", "expense"),
    ("Aporte del titular", "income"),
)


def _values(rows: tuple[tuple[str, str], ...]) -> str:
    return ", ".join(f"('{first}', '{second}')" for first, second in rows)


def _create_application_role() -> None:
    # A role belongs to the whole server, so another database may have created it already.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APPLICATION_ROLE}') THEN
                CREATE ROLE {APPLICATION_ROLE} NOLOGIN;
            END IF;
        END
        $$
        """
    )
    # The grants never name the owner of the tables: each environment gives it its own name.
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APPLICATION_ROLE}")
    for table in TABLES:
        rights = "SELECT, INSERT, UPDATE"
        if table not in TABLES_WITHOUT_DELETE:
            rights += ", DELETE"
        op.execute(f"GRANT {rights} ON {table} TO {APPLICATION_ROLE}")


def upgrade() -> None:
    for statement in (*CREATE_TABLES, *CREATE_FUNCTIONS, *CREATE_TRIGGERS):
        op.execute(statement)
    op.execute(f"INSERT INTO currency (code, name) VALUES {_values(CURRENCIES)}")
    op.execute(
        "INSERT INTO category (name, kind, is_base) "
        f"SELECT name, kind, TRUE FROM (VALUES {_values(BASE_CATEGORIES)}) AS base (name, kind)"
    )
    _create_application_role()


def downgrade() -> None:
    # The role stays: it belongs to the server and other databases may use it.
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table} CASCADE")
    for function in FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}()")
