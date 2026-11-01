-- Manual test data for the budget screen (FEAT-004): an estimated income, three limits and
-- some movements for Lucía, in her period that covers today, to see the screen with data
-- without loading it by hand.
--
-- Local environment only, after seed_test_data, and once: a second run fails on the limits.
--   docker compose exec -T db psql -U platita -d platita < scripts/budget_test_data.sql
BEGIN;

CREATE TEMP TABLE ctx ON COMMIT DROP AS
SELECT u.id AS user_id, p.id AS period_id
  FROM app_user u
  JOIN budget_period p ON p.user_id = u.id
 WHERE u.whatsapp_phone = '+000000000001'
   AND CURRENT_DATE BETWEEN p.period_start AND p.period_end;

UPDATE budget_period SET estimated_income = 1450000.00 WHERE id = (SELECT period_id FROM ctx);

-- Limits: Supermercado well below, Transporte past it, Salud near it.
INSERT INTO budget (budget_period_id, category_id, limit_amount)
SELECT ctx.period_id, c.id, l.amount
  FROM ctx, category c
  JOIN (VALUES ('Supermercado', 300000.00), ('Transporte', 80000.00), ('Salud', 50000.00))
       AS l(name, amount) ON l.name = c.name
 WHERE c.user_id IS NULL AND c.kind = 'expense';

-- Movements, all dated today: the accounts of a test user open on the day of the seed.
INSERT INTO transaction (user_id, account_id, budget_period_id, category_id, amount, currency,
                         exchange_rate, type, source, description, transaction_date)
SELECT ctx.user_id, a.id, ctx.period_id, c.id, m.amount, m.currency, m.rate, m.type, m.source,
       m.description, CURRENT_DATE
  FROM ctx
  JOIN (VALUES
          ('Galicia pesos', 'Supermercado', 'expense', 154500.00, 'ARS', NULL::numeric, 'manual', NULL),
          ('Galicia USD', 'Supermercado', 'expense', 10.00, 'USD', 1234.5678, 'manual', 'super en dólares'),
          ('Mercado Pago', 'Transporte', 'expense', 80040.00, 'ARS', NULL, 'automatic', 'nafta'),
          ('Efectivo', 'Salud', 'expense', 42500.00, 'ARS', NULL, 'manual', 'farmacia'),
          ('Efectivo', 'Comida afuera y delivery', 'expense', 3500.00, 'ARS', NULL, 'manual', 'café'),
          ('Galicia pesos', 'Sueldo', 'income', 1500000.00, 'ARS', NULL, 'manual', NULL)
       ) AS m(account, category, type, amount, currency, rate, source, description) ON TRUE
  JOIN account a ON a.user_id = ctx.user_id AND a.name = m.account
  JOIN category c ON c.user_id IS NULL AND c.name = m.category AND c.kind = m.type;

-- A refund of 30.000 linked to the Supermercado expense in pesos: it subtracts.
INSERT INTO transaction (user_id, account_id, budget_period_id, category_id, amount, currency,
                         type, source, description, transaction_date, refund_of)
SELECT ctx.user_id, a.id, ctx.period_id, c.id, 30000.00, 'ARS', 'income', 'manual',
       'devolución', CURRENT_DATE, t.id
  FROM ctx
  JOIN account a ON a.user_id = ctx.user_id AND a.name = 'Galicia pesos'
  JOIN category c ON c.user_id IS NULL AND c.name = 'Devoluciones y reintegros'
  JOIN transaction t ON t.user_id = ctx.user_id AND t.amount = 154500.00;

COMMIT;
