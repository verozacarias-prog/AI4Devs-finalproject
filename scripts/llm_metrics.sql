-- The metrics of the calls to the language model (ADR 0023, point 11; docs/operacion.md 6.2).
-- Run with psql against the database: psql "$DATABASE_URL" -f scripts/llm_metrics.sql
-- They read LLM_CALL and PENDING_TRANSACTION, which keep no content. Four queries, in order;
-- each ends with a semicolon, and a comment takes a whole line.

-- Latency: the duration of the calls, by purpose.
SELECT purpose,
       count(*) AS calls,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS median_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms
  FROM llm_call
 GROUP BY purpose
 ORDER BY purpose;

-- Cost: the estimated cost in dollars, by day and by purpose. The day is the one of Buenos
-- Aires, the day of every user while Platita is only in Argentina.
SELECT (created_at AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS day,
       purpose,
       sum(estimated_cost_usd) AS cost_usd
  FROM llm_call
 GROUP BY day, purpose
 ORDER BY day, purpose;

-- Quality: the registrations confirmed without any correction, among those promoted, and the
-- calls whose output had an invalid format, among all of them. In percent, to one decimal.
SELECT (
           SELECT round(100.0 * count(*) FILTER (WHERE corrected_fields_count = 0)
                        / nullif(count(*), 0), 1)
             FROM pending_transaction
            WHERE status = 'promoted'
       ) AS confirmed_without_corrections_pct,
       (
           SELECT round(100.0 * count(*) FILTER (WHERE outcome = 'invalid_output')
                        / nullif(count(*), 0), 1)
             FROM llm_call
       ) AS invalid_output_pct;

-- Hallucinations: the calls whose output the validation blocked, among all of them.
SELECT round(100.0 * count(*) FILTER (WHERE outcome = 'blocked') / nullif(count(*), 0), 1)
       AS blocked_pct
  FROM llm_call;
