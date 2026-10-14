"""The texts of the API reference, in one place: what `/docs` shows.

They are for whoever calls the API, so they are in English. The contract they end up in is
generated from the code, and `scripts/verify_api_contract.py` fails when an operation, a
response or a field is left without its text. What each endpoint must do is decided in
docs/04-api.md, not here.
"""

from __future__ import annotations

from app.adapters.inbound.api.routes import ACCOUNTS_TAG, DEV_TAG, HEALTH_TAG, SESSION_TAG

API_DESCRIPTION = (
    "The API of Platita, a personal and family finance assistant. The dashboard is its only "
    "client, and both are served from one origin.\n\n"
    "**Session.** It travels in the cookie `__Host-sid`, which the page cannot read. An "
    "operation that asks for a session is marked as such, and answers `401` without a "
    "valid one.\n\n"
    "**Requests that change something.** A `POST`, `PUT`, `PATCH` or `DELETE` must come "
    "from the page of the API itself and be JSON: with another `Origin`, without one, or "
    "with another `Content-Type`, it answers `403`.\n\n"
    "**Errors.** Every error has the same body: its code in `error`, a short lowercase word "
    "that never changes. Every response carries the header `X-Request-Id`, the reference to "
    "look for in the logs."
)

TAGS: list[dict[str, str]] = [
    {
        "name": HEALTH_TAG,
        "description": "Whether the service is up. They ask for no session and return "
        "nobody's data.",
    },
    {
        "name": SESSION_TAG,
        "description": "Who is behind the session of a request, and closing it.",
    },
    {
        "name": ACCOUNTS_TAG,
        "description": "The accounts of the user of the session, with their computed balance.",
    },
    {
        "name": DEV_TAG,
        "description": "The development entry: a real session without a login code, for a "
        "test user. These routes exist only when the entry is enabled, and never in "
        "production.",
    },
]

# The session cookie, as the reference shows it.
SESSION_COOKIE_SCHEME = "SessionCookie"
SESSION_COOKIE_DESCRIPTION = (
    "The token of the session. The API sets it when a session is opened, and the browser "
    "sends it by itself."
)

# The body of every error.
ERROR_CODE = "The code of the error: a short lowercase word that never changes."

# Responses shared by several operations.
NO_SESSION = "There is no valid session: missing, unknown, revoked or expired, told apart nowhere."
FOREIGN_REQUEST = (
    "The request did not come from the page of the API itself, or it is not JSON. Nothing "
    "of what it sent was read."
)

# Health.
HEALTHZ_SUMMARY = "Is the process alive"
HEALTHZ_DESCRIPTION = "Answers as long as the process runs. It does not touch the database."
HEALTHZ_OK = "The process is alive."
READYZ_SUMMARY = "Can the API reach the database"
READYZ_DESCRIPTION = (
    "Asks the database the cheapest question there is. It is what a deployment waits for "
    "before sending requests."
)
READYZ_OK = "The database answers."
READYZ_UNAVAILABLE = "The database does not answer. The body has the same shape as the `200`."
HEALTH_STATE = "`ok`, or `unavailable` when the database does not answer."

# Session.
ME_SUMMARY = "Who is behind this session"
ME_DESCRIPTION = (
    "The user of the session of the request. The dashboard asks this when it loads, because "
    "it cannot read the cookie. It counts as activity of the session."
)
ME_OK = "The user of the session."
USER_ID = "The identifier of the user."
USER_NAME = "The name the user is shown with."
LOGOUT_SUMMARY = "Close this session"
LOGOUT_DESCRIPTION = (
    "Revokes the session of the request, and only that one, and clears its cookie. The body "
    "of the request is ignored."
)
LOGOUT_OK = "The session was revoked and its cookie cleared."

# Development entry.
ACCOUNTS_SUMMARY = "List the accounts and their balance"
ACCOUNTS_DESCRIPTION = (
    "The accounts of the user of the session, each with its balance computed from its "
    "movements and transfers dated up to today, in the time zone of the user. The balance is "
    "never stored. They come first in the primary currency of the user, then in the other "
    "currencies by code, and within each currency by name. An account of type `receivable` "
    "is money others owe the user: the dashboard does not list it with the others."
)
ACCOUNTS_OK = "The accounts of the user. An empty list when there are none."
ACCOUNTS_LIST = "The accounts, in the order the dashboard shows them."
ACCOUNT_ID = "The identifier of the account."
ACCOUNT_NAME = "The name of the account, unique for its user."
ACCOUNT_TYPE = "What kind of account it is."
ACCOUNT_CURRENCY = "The currency of the account, as an ISO 4217 code. Its balance is in it."
ACCOUNT_BALANCE = (
    "The computed balance, in the currency of the account, with its two decimals exactly as "
    "computed. In an investment account it is the net contributed."
)
ACCOUNT_BALANCE_KIND = (
    "`balance`, or `net_contributed` in an investment account: what was declared on opening, "
    "plus transfers in, minus transfers out. Never added to any total."
)

DEV_USERS_SUMMARY = "List the test users"
DEV_USERS_DESCRIPTION = (
    "The users anyone may enter as: the ones with an invented phone, which starts with "
    "`+000`. A user with a real phone is never listed. It asks for no session. It exists "
    "only in the local environment."
)
DEV_USERS_OK = "The test users, ordered by name. An empty list when there are none."
DEV_USERS_LIST = "The test users, ordered by name."
DEV_USERS_NOT_FOUND = "The development entry is disabled, or the environment is not local."
DEV_SESSION_SUMMARY = "Enter as a test user"
DEV_SESSION_DESCRIPTION = (
    "Opens a real session without a login code and returns it in the session cookie. In the "
    "local environment the user is chosen from the list, with `user_id`. A personal link, "
    "with `access_token`, is the way in of the demo environment and is not built yet: it "
    "answers `404`. One of the two is required."
)
DEV_SESSION_OK = "The session was opened. Its token is in the cookie, and the body is empty."
DEV_SESSION_NOT_FOUND = (
    "The development entry is disabled, the user does not exist or is not a test user, "
    "`user_id` was sent outside the local environment, or the personal link is unknown. The "
    "same answer for all of them."
)
DEV_SESSION_INVALID = "Neither `user_id` nor `access_token` was sent, or `user_id` is not a UUID."
DEV_SESSION_USER_ID = "The test user to enter as, from the list. Only in the local environment."
# Not a secret: the description of the field that carries the value of a link.
DEV_SESSION_ACCESS_TOKEN = "The value of a personal link. Not built yet: it answers `404`."  # noqa: S105
