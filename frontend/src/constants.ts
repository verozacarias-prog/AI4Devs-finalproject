/** Values shared by the whole dashboard, in one place. */

/** The API serves the build under this path (ADR 0016). */
export const DASHBOARD_BASE = '/app/'

/** How long the dashboard waits for the API before giving up. */
export const API_TIMEOUT_MS = 10_000

export const HTTP_UNAUTHORIZED = 401
export const HTTP_NOT_FOUND = 404
export const HTTP_SERVICE_UNAVAILABLE = 503

export const JSON_CONTENT_TYPE = 'application/json'

/** How the dashboard writes an amount: Argentine format, always with two decimals. */
export const AMOUNT_LOCALE = 'es-AR'
export const AMOUNT_DECIMALS = 2

/** The command that creates the test users of the local environment (docs/operacion.md). */
export const SEED_TEST_DATA_COMMAND =
  'docker compose exec api python -m app.adapters.inbound.operator_commands.seed_test_data'

/** The address of the API while developing. Deployed, both share one origin (ADR 0016). */
export const DEV_API_ORIGIN = 'http://127.0.0.1:8000'
