/** Values shared by the whole dashboard, in one place. */

/** The API serves the build under this path (ADR 0016). */
export const DASHBOARD_BASE = '/app/'

/** How long the dashboard waits for the API before giving up. */
export const API_TIMEOUT_MS = 10_000

/**
 * How often the chat asks for new messages while its screen is open (FEAT-002): more often
 * while a reply of Platita is pending, so it shows up at once, and less the rest of the time.
 */
export const CHAT_WAITING_POLL_MS = 500
export const CHAT_POLL_MS = 3_000
/** The header that lets the API tell a repeated message from a new one (docs/04-api.md). */
export const IDEMPOTENCY_KEY_HEADER = 'Idempotency-Key'
/** Where a time starts and ends in an ISO 8601 date, such as 2026-10-15T14:58:00-03:00. */
export const ISO_TIME_START = 11
export const ISO_TIME_END = 16

export const HTTP_UNAUTHORIZED = 401
export const HTTP_NOT_FOUND = 404
export const HTTP_SERVER_ERROR = 500
export const HTTP_SERVICE_UNAVAILABLE = 503
/** What the API answers for something that is not there, or that is of someone else. */
export const API_ERROR_NOT_FOUND = 'not_found'
export const API_ERROR_PERIOD_OVERLAP = 'budget_period_overlap'
/** How long an ISO date is, such as 2026-10-15. */
export const ISO_DATE_LENGTH = 10

export const JSON_CONTENT_TYPE = 'application/json'

/** How the dashboard writes an amount: Argentine format, always with two decimals. */
export const AMOUNT_LOCALE = 'es-AR'
// How a person writes an amount. A parameter, for the user to choose it in a future settings section.
export const AMOUNT_SEPARATORS = { thousands: '.', decimal: ',' }
export const AMOUNT_DECIMALS = 2
/** How the dashboard writes a calendar day, such as 9/10/2026. */
export const DATE_LOCALE = 'es-AR'
export const DATE_FORMAT: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'numeric', year: 'numeric' }
export const DATE_TIME_ZONE = 'UTC'
/** A used percentage has one decimal, as the API rounds it (FEAT-004, CA-10). */
export const PERCENTAGE_DECIMALS = 1
/** An exchange rate is shown with every decimal it has, up to the ten the database keeps. */
export const EXCHANGE_RATE_MAX_DECIMALS = 10

/**
 * When a budget bar is near its limit and when it is over it: past 80 % and past 100 %, the
 * same thresholds as the budget alerts (domain rules, § 3; FEAT-004, decision 9). They are
 * here because the configuration of the alerts does not exist yet.
 */
export const NEAR_LIMIT_PERCENTAGE = 80
export const OVER_LIMIT_PERCENTAGE = 100

/** The command that creates the test users of the local environment (docs/operacion.md). */
export const SEED_TEST_DATA_COMMAND =
  'docker compose exec api python -m app.adapters.inbound.operator_commands.seed_test_data'

/** The address of the API while developing. Deployed, both share one origin (ADR 0016). */
export const DEV_API_ORIGIN = 'http://127.0.0.1:8000'
