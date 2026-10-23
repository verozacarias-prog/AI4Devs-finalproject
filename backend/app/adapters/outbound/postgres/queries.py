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

SELECT_USER_BY_ID = """
    SELECT id, name, whatsapp_phone, country, time_zone, primary_currency,
           exchange_rate_reference, terms_accepted_at, terms_version, notifications_opt_in,
           onboarding_status
      FROM app_user
     WHERE id = :user_id
"""

# The id breaks the tie between two users with the same name, so the order never changes.
SELECT_USERS_BY_PHONE_PREFIX = """
    SELECT id, name, whatsapp_phone, country, time_zone, primary_currency,
           exchange_rate_reference, terms_accepted_at, terms_version, notifications_opt_in,
           onboarding_status
      FROM app_user
     WHERE starts_with(whatsapp_phone, :prefix)
     ORDER BY name, id
"""

INSERT_SESSION = """
    INSERT INTO session (
        id, user_id, token_hash, created_at, last_seen_at, expires_at, revoked_at
    ) VALUES (
        :id, :user_id, :token_hash, :created_at, :last_seen_at, :expires_at, :revoked_at
    )
"""

# Not a secret: the name of this query has the word "token" in it.
SELECT_SESSION_BY_TOKEN_HASH = """
    SELECT id, user_id, token_hash, created_at, last_seen_at, expires_at, revoked_at
      FROM session
     WHERE token_hash = :token_hash
"""  # noqa: S105

TOUCH_SESSION = "UPDATE session SET last_seen_at = :at WHERE id = :session_id"

REVOKE_SESSION = "UPDATE session SET revoked_at = :at WHERE id = :session_id"

INSERT_ACCOUNT = """
    INSERT INTO account (id, user_id, name, type, currency, initial_balance, created_at)
    VALUES (:id, :user_id, :name, :type, :currency, :initial_balance, :opened_at)
"""

SELECT_ACCOUNTS_BY_USER = """
    SELECT id, user_id, name, type, currency, initial_balance, created_at AS opened_at
    FROM account
    WHERE user_id = :user_id
"""

# Deleted and duplicated movements included: which ones count is a rule of the domain.
SELECT_TRANSACTIONS_BY_USER = """
    SELECT id, user_id, account_id, type, amount, currency, exchange_rate, transaction_date,
           duplicate_of, deleted_at
    FROM transaction
    WHERE user_id = :user_id
"""

SELECT_TRANSFERS_BY_USER = """
    SELECT id, user_id, from_account_id, from_amount, from_currency, to_account_id, to_amount,
           to_currency, exchange_rate, transfer_date, deleted_at
    FROM transfer
    WHERE user_id = :user_id
"""

INSERT_TRANSACTION = """
    INSERT INTO transaction (
        id, user_id, account_id, budget_period_id, category_id, amount, currency,
        exchange_rate, type, source, description, transaction_date
    ) VALUES (
        :id, :user_id, :account_id, :budget_period_id, :category_id, :amount, :currency,
        :exchange_rate, :type, :source, :description, :transaction_date
    )
"""

# The own periods of the user and those of the groups they are in now, that cover that day.
SELECT_PERIODS_COVERING = """
    SELECT id, user_id, family_group_id, period_type, period_start, period_end,
           primary_currency, estimated_income, status
      FROM budget_period
     WHERE :day BETWEEN period_start AND period_end
       AND (
           user_id = :user_id
           OR family_group_id IN (
               SELECT family_group_id FROM user_group
                WHERE user_id = :user_id AND left_at IS NULL
           )
       )
"""

# A category of a user: the base catalog is created by the migrations.
INSERT_CATEGORY = """
    INSERT INTO category (id, name, user_id, is_base, kind)
    VALUES (:id, :name, :user_id, FALSE, :kind)
"""

# Only a draft: the query protects itself, whatever the use case checked before.
CONFIRM_BUDGET_PERIOD = """
    UPDATE budget_period SET status = 'confirmed' WHERE id = :period_id AND status = 'draft'
"""

SELECT_BUDGETS_BY_PERIOD = """
    SELECT id, budget_period_id, category_id, limit_amount
      FROM budget
     WHERE budget_period_id = :period_id
"""

SELECT_CATEGORIES_AVAILABLE = """
    SELECT id, name, kind, user_id
      FROM category
     WHERE user_id IS NULL OR user_id = :user_id
"""

INSERT_PENDING_BATCH = """
    INSERT INTO pending_batch (
        id, user_id, source, awaiting_reply, question_message_id, confirmation_message_id,
        status, created_at
    ) VALUES (
        :id, :user_id, :source, :awaiting_reply, :question_message_id,
        :confirmation_message_id, :status, :created_at
    )
"""

INSERT_PENDING_TRANSACTION = """
    INSERT INTO pending_transaction (
        id, user_id, intent, parsed_data, missing_fields, source, batch_id, position,
        resulting_transaction_id, status, resolved_by, expires_at, created_at,
        corrected_fields_count
    ) VALUES (
        :id, :user_id, :intent, CAST(:parsed_data AS jsonb), :missing_fields, :source,
        :batch_id, :position, :resulting_transaction_id, :status, :resolved_by, :expires_at,
        :created_at, :corrected_fields_count
    )
"""

# The batch of the user that awaits a reply, and its pending: in delivery 2, the only one.
SELECT_AWAITING_PENDING = """
    SELECT b.id AS batch_id, b.user_id AS batch_user_id, b.source AS batch_source,
           b.awaiting_reply, b.question_message_id, b.confirmation_message_id,
           b.status AS batch_status, b.created_at AS batch_created_at,
           p.id, p.user_id, p.intent, p.parsed_data, p.missing_fields, p.source, p.batch_id,
           p.position, p.resulting_transaction_id, p.status, p.resolved_by, p.expires_at,
           p.created_at, p.corrected_fields_count
      FROM pending_batch b
      JOIN pending_transaction p ON p.batch_id = b.id
     WHERE b.user_id = :user_id AND b.awaiting_reply
     ORDER BY p.position
     LIMIT 1
"""

UPDATE_PENDING_TRANSACTION = """
    UPDATE pending_transaction
       SET parsed_data = CAST(:parsed_data AS jsonb), missing_fields = :missing_fields,
           resulting_transaction_id = :resulting_transaction_id, status = :status,
           resolved_by = :resolved_by, corrected_fields_count = :corrected_fields_count
     WHERE id = :id
"""

UPDATE_PENDING_BATCH = """
    UPDATE pending_batch
       SET awaiting_reply = :awaiting_reply, question_message_id = :question_message_id,
           confirmation_message_id = :confirmation_message_id, status = :status
     WHERE id = :id
"""

INSERT_LLM_CALL = """
    INSERT INTO llm_call (
        id, inbound_message_id, purpose, provider, model, prompt_version, input_tokens,
        output_tokens, duration_ms, estimated_cost_usd, outcome, empty_fields
    ) VALUES (
        :id, :inbound_message_id, :purpose, :provider, :model, :prompt_version, :input_tokens,
        :output_tokens, :duration_ms, :estimated_cost_usd, :outcome, :empty_fields
    )
"""

# The validation rejected what the call returned (ADR 0023, point 6).
MARK_LLM_CALL_BLOCKED = """
    UPDATE llm_call SET outcome = 'blocked' WHERE id = :call_id
"""

# The daily counters of a user (domain rules, § 12). One row per user, day and counter.
SELECT_LLM_USAGE_COUNT = """
    SELECT message_count FROM llm_usage
     WHERE user_id = :user_id AND usage_date = :day AND quota = :counter
"""

ADD_LLM_USAGE = """
    INSERT INTO llm_usage (user_id, usage_date, quota, message_count, input_tokens, output_tokens)
    VALUES (:user_id, :day, :counter, 1, :input_tokens, :output_tokens)
    ON CONFLICT (user_id, usage_date, quota) DO UPDATE
       SET message_count = llm_usage.message_count + 1,
           input_tokens = llm_usage.input_tokens + EXCLUDED.input_tokens,
           output_tokens = llm_usage.output_tokens + EXCLUDED.output_tokens
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

SELECT_GROUP_BY_ID = "SELECT id, name FROM family_group WHERE id = :group_id"

# The messages of the channel (ADR 0010). The text of a message lives in its JSON, under this
# key, both in the payload of what came in and in the content of what goes out. The queries
# that read them take the keys as parameters, so these are the only place they are written.
MESSAGE_TEXT_KEY = "text"
RESPONSE_KIND_KEY = "response_kind"

INSERT_INBOUND_MESSAGE = """
    INSERT INTO inbound_message (
        id, provider, provider_message_id, user_id, from_phone, quoted_outbound_message_id,
        payload, sent_at, status, attempts, next_attempt_at, locked_until, processed_at,
        created_at
    ) VALUES (
        :id, :provider, :provider_message_id, :user_id, :from_phone,
        :quoted_outbound_message_id, CAST(:payload AS jsonb), :sent_at, :status, :attempts,
        :sent_at, :locked_until, :processed_at, :sent_at
    )
"""

# The sender is the user when there is one, and the phone while there is not (ADR 0010).
# The text is read where a web message keeps it; a message of Meta keeps it under text.body,
# and the adapter of WhatsApp makes this depend on the provider (FEAT-002, decision 6).
# A message is available when it is pending, or in process with its lock ended: the worker
# that took it fell, and it is free again. It is taken only if it is the earliest available
# one of its sender, and the sender has no message in process with its lock in force. The
# first condition also covers two workers racing: the one that skips a locked message cannot
# take the next of the same sender. A message put off by a limit of use holds back nobody while
# it waits; once due, it does, so the ones put off keep their order (ADR 0018, point 5).
CLAIM_NEXT_INBOUND_MESSAGE = """
    UPDATE inbound_message
       SET status = 'processing', attempts = attempts + 1, locked_until = :locked_until,
           deferred = FALSE
     WHERE id = (
        SELECT candidate.id
          FROM inbound_message candidate
         WHERE ((candidate.status = 'pending' AND candidate.next_attempt_at <= :now)
                OR (candidate.status = 'processing' AND candidate.locked_until <= :now))
           AND NOT EXISTS (
                SELECT 1
                  FROM inbound_message other
                 WHERE COALESCE(other.user_id::text, other.from_phone)
                       = COALESCE(candidate.user_id::text, candidate.from_phone)
                   AND (
                        (other.status = 'processing' AND other.locked_until > :now)
                        OR (((other.status = 'pending'
                              AND (NOT other.deferred OR other.next_attempt_at <= :now))
                             OR (other.status = 'processing' AND other.locked_until <= :now))
                            AND (other.sent_at, other.id) < (candidate.sent_at, candidate.id))
                   )
           )
         ORDER BY candidate.sent_at, candidate.id
         LIMIT 1
           FOR UPDATE SKIP LOCKED
     )
    RETURNING id, provider, provider_message_id, user_id, from_phone,
              payload ->> :text_key AS text, quoted_outbound_message_id, sent_at, status,
              attempts, locked_until, processed_at
"""

SELECT_WEB_INBOUND_MESSAGE_BY_PROVIDER_ID = """
    SELECT id, provider, provider_message_id, user_id, from_phone,
           payload ->> :text_key AS text, quoted_outbound_message_id, sent_at, status,
           attempts, locked_until, processed_at
      FROM inbound_message
     WHERE provider = 'web' AND provider_message_id = :provider_message_id
"""

# A message delayed on purpose has its next attempt in the future, so it does not count.
INBOUND_MESSAGE_WAITING_SINCE_EXISTS = """
SELECT EXISTS (
    SELECT 1 FROM inbound_message
    WHERE status = 'pending' AND next_attempt_at < :since
)
"""

# The attempts are the fencing token: only the claim that took it last completes it.
MARK_INBOUND_MESSAGE_PROCESSED = """
    UPDATE inbound_message
       SET status = 'processed', processed_at = :at
     WHERE id = :message_id AND status = 'processing' AND attempts = :attempts
    RETURNING id
"""

# Another attempt later, by the same fencing token (ADR 0010, point 4).
RETRY_INBOUND_MESSAGE_LATER = """
    UPDATE inbound_message
       SET status = 'pending', next_attempt_at = :next_attempt_at, locked_until = NULL
     WHERE id = :message_id AND status = 'processing' AND attempts = :attempts
    RETURNING id
"""

# Put off by a limit of use, with the attempts it had before this claim: it is no failure
# (ADR 0010, point 4). The same fencing token, the attempts of this claim.
DEFER_INBOUND_MESSAGE = """
    UPDATE inbound_message
       SET status = 'pending', attempts = :attempts, next_attempt_at = :next_attempt_at,
           locked_until = NULL, deferred = TRUE
     WHERE id = :message_id AND status = 'processing' AND attempts = :attempts + 1
    RETURNING id
"""

# Its attempts were used up: it is not taken again, and stops holding back the next ones.
MARK_INBOUND_MESSAGE_FAILED = """
    UPDATE inbound_message
       SET status = 'failed', locked_until = NULL
     WHERE id = :message_id AND status = 'processing' AND attempts = :attempts
    RETURNING id
"""

# Whether a message of Platita went to that user: the only kind a message may quote.
OUTBOUND_MESSAGE_OF_USER_EXISTS = """
    SELECT EXISTS (
        SELECT 1 FROM outbound_message WHERE id = :message_id AND user_id = :user_id
    )
"""

# Whether Platita sent that text to that user from that moment on: a notice that goes out once.
OUTBOUND_TEXT_SENT_SINCE = """
    SELECT EXISTS (
        SELECT 1 FROM outbound_message
         WHERE user_id = :user_id AND content ->> :text_key = :text AND created_at >= :since
    )
"""

INSERT_OUTBOUND_MESSAGE = """
    INSERT INTO outbound_message (
        id, provider, user_id, to_phone, inbound_message_id, content, status, sent_at,
        created_at
    ) VALUES (
        :id, :provider, :user_id, :to_phone, :inbound_message_id, CAST(:content AS jsonb),
        :status, :sent_at, :created_at
    )
"""

# What the user wrote is ordered by when it arrived, and a reply by when it was written. At
# the same instant the message of the user goes first, since a reply never comes before what
# it answers; then the id breaks the tie, so the order never changes and the cursor never
# skips a message.
SELECT_CHAT_MESSAGES_BY_USER = """
    WITH conversation AS (
        SELECT id, 'inbound' AS direction, 0 AS turn, payload ->> :text_key AS text,
               quoted_outbound_message_id AS quoted_message_id,
               NULL AS response_kind, sent_at AS created_at
          FROM inbound_message
         WHERE provider = 'web' AND user_id = :user_id AND purged_at IS NULL
        UNION ALL
        SELECT id, 'outbound', 1, content ->> :text_key, NULL,
               content ->> :response_kind_key,
               created_at
          FROM outbound_message
         WHERE provider = 'web' AND user_id = :user_id AND purged_at IS NULL
    )
    SELECT id, direction, text, quoted_message_id, response_kind, created_at
      FROM conversation
     WHERE CAST(:after AS uuid) IS NULL
        OR (created_at, turn, id) > (
            SELECT created_at, turn, id FROM conversation WHERE id = CAST(:after AS uuid)
        )
     ORDER BY created_at, turn, id
"""

# Whether a message is in the web conversation of the user: a cursor of anyone else's, or of
# none, is not.
CHAT_MESSAGE_OF_USER_EXISTS = """
    SELECT EXISTS (
        SELECT 1 FROM inbound_message
         WHERE id = :message_id AND provider = 'web' AND user_id = :user_id
           AND purged_at IS NULL
        UNION ALL
        SELECT 1 FROM outbound_message
         WHERE id = :message_id AND provider = 'web' AND user_id = :user_id
           AND purged_at IS NULL
    )
"""
