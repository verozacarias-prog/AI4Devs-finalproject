"""The texts of the API reference, in one place: what `/docs` shows.

They are for whoever calls the API, so they are in English. The contract they end up in is
generated from the code, and `scripts/verify_api_contract.py` fails when an operation, a
response or a field is left without its text. What each endpoint must do is decided in
docs/04-api.md, not here.
"""

from __future__ import annotations

from app.adapters.inbound.api.routes import (
    ACCOUNTS_TAG,
    BUDGETS_TAG,
    CATEGORIES_TAG,
    CHAT_TAG,
    CURRENCIES_TAG,
    DEV_TAG,
    HEALTH_TAG,
    SESSION_TAG,
)

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
        "name": BUDGETS_TAG,
        "description": "The budget periods the user of the session can read, the summary of "
        "one, and what one limit spent, computed from the movements. Building, changing and "
        "confirming a period of their own.",
    },
    {
        "name": CATEGORIES_TAG,
        "description": "The categories of expenses the user of the session can put a limit on.",
    },
    {
        "name": CURRENCIES_TAG,
        "description": "The currencies of the catalog, to choose the one of a budget period.",
    },
    {
        "name": CHAT_TAG,
        "description": "The chat of the dashboard, for development and demonstration. A "
        "message goes the same way as one of WhatsApp: it is stored, and the worker answers "
        "it later. These routes exist only when the web chat is enabled, and never in "
        "production.",
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
QUEUEZ_SUMMARY = "Does the worker keep up with the messages"
QUEUEZ_DESCRIPTION = (
    "Fails when a pending message has waited longer than the configured wait to be processed: "
    "10 minutes, unless `QUEUE_MAX_WAIT_MINUTES` says otherwise. A message delayed on purpose "
    "does not count. It is what the external monitor watches, because the worker may hang "
    "while the API is healthy."
)
QUEUEZ_OK = "No pending message has waited longer than the configured wait."
QUEUEZ_UNAVAILABLE = (
    "A pending message has waited longer than the configured wait, or the database does not "
    "answer. The body has the same shape as the `200`."
)
HEALTH_STATE = "`ok`, or `unavailable` when what the route checks fails."

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

# The accounts of the user.
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

# Reading the budget.
BUDGET_PERIODS_SUMMARY = "List the budget periods"
BUDGET_PERIODS_DESCRIPTION = (
    "The periods the user of the session can read: their own, every period of the groups they "
    "are a current member of, and of a group they left, the ones that overlap their "
    "membership. Each one with its limits, whether the user can edit it, and whether it covers "
    "today, in the time zone of the user. The one that starts latest comes first; with the "
    "same start, the individual one before those of groups, by name."
)
BUDGET_PERIODS_OK = "The periods the user can read. An empty list when there are none."
BUDGET_PERIODS_LIST = "The periods, in the order the dashboard shows them."
PERIOD_ID = "The identifier of the period."
PERIOD_GROUP_ID = "The group the period belongs to, or null in an individual period."
PERIOD_GROUP_NAME = (
    "The name of the group, to tell the budgets apart, or null in an individual one."
)
PERIOD_TYPE = (
    "`monthly`, which lasts a month; `biweekly`, the fortnight of the calendar; or `custom`, "
    "which ends on the day given."
)
PERIOD_START = "The first day of the period."
PERIOD_END = "The last day of the period, included."
PERIOD_STATUS = "`draft` while it is being built, `confirmed` once it can receive movements."
PERIOD_CURRENCY = "The currency of the period, as an ISO 4217 code. What it spent is in it."
PERIOD_ESTIMATED_INCOME = "What the user expects to receive in the period."
PERIOD_CAN_EDIT = (
    "Whether the user can change it: an individual period of their own, or one of a group "
    "they currently own. It does not look at the status."
)
PERIOD_IS_CURRENT = (
    "Whether it covers today, in the time zone of the user. At most one per owner: an "
    "individual one and one of each group."
)
PERIOD_BUDGETS = "The limits of the period, by category name."
BUDGET_ID = "The identifier of the limit."
BUDGET_CATEGORY_ID = "The category the limit is for."
BUDGET_CATEGORY = "The name of the category."
BUDGET_LIMIT = "The limit, in the currency of the period."
CREATE_PERIOD_SUMMARY = "Build a budget period"
CREATE_PERIOD_DESCRIPTION = (
    "A draft of an individual period of the user of the session, with its limits. A monthly "
    "period ends the day before the same day of the next month, and a biweekly one starts on "
    "the 1st or the 16th and ends on the 15th or the last day of the month. Each "
    "amount is accepted as a JSON number or as a decimal text, and kept exact."
)
CREATE_PERIOD_CREATED = "The draft, whole, in the same shape as an item of the list."
PERIOD_CONTENT_INVALID = (
    "A field is missing, unknown or has no valid value, or the content breaks a rule of the "
    "period: its `error` says which."
)
PERIOD_CREATE_GROUP_ID = "Always null or absent: building a period of a group is not available yet."
PERIOD_CATEGORY_NOT_FOUND = (
    "A category of the limits does not exist, or it is not of the user. The same answer for both."
)
PERIOD_OVERLAP = "It overlaps another period of the same owner (`budget_period_overlap`)."
PERIOD_EDIT_FORBIDDEN = (
    "The request did not come from the page of the API itself or it is not JSON, or the period "
    "is of a group the user is a member of without being its owner (`not_the_owner`)."
)
PERIOD_EDIT_NOT_FOUND = (
    "The period does not exist or the user cannot read it, or a category of the limits is not "
    "of the user. The same answer for each."
)
PERIOD_EDIT_CONFLICT = (
    "It changes the cadence, the dates or the currency of a confirmed period "
    "(`confirmed_period_fixed`), or it overlaps another period of the same owner "
    "(`budget_period_overlap`)."
)
UPDATE_PERIOD_SUMMARY = "Change a budget period"
UPDATE_PERIOD_DESCRIPTION = (
    "Replaces the content of a period: its dates, currency, estimated income and limits. A "
    "limit that stays keeps its id."
)
UPDATE_PERIOD_OK = "The period, whole, in the same shape as an item of the list."
CONFIRM_PERIOD_SUMMARY = "Confirm a budget period"
CONFIRM_PERIOD_DESCRIPTION = (
    "A draft becomes confirmed, and from then on receives movements. Confirming one already "
    "confirmed answers the same, and changes nothing."
)
CONFIRM_PERIOD_OK = "The period, confirmed, in the same shape as an item of the list."
PERIOD_CONTENT_BUDGETS = "The limits of the period, one per category."
PERIOD_CONTENT_END = (
    "The last day of the period, included. Required in a custom period. In a monthly or a "
    "biweekly one it is computed, and if it comes it has to be that day."
)
PERIOD_SUMMARY_SUMMARY = "Read the summary of a period"
PERIOD_SUMMARY_DESCRIPTION = (
    "The incomes of the period and what each category spent, in the currency of the period. "
    "Every category with a limit, even without expenses, and every one without a limit that "
    "had movements in the period, by name. What a category spent is net of the refunds linked "
    "to its expenses that arrived in the period, and can be negative."
)
PERIOD_SUMMARY_OK = "The summary of the period."
PERIOD_NOT_FOUND = (
    "The period does not exist, or the user cannot read it. The same answer for both."
)
PERIOD_ID_INVALID = "`period_id` is not a UUID."
PERIOD_ACTUAL_INCOME = "What the period received, without the refunds."
PERIOD_TOTAL_SPENT = "What every category of the summary spent, added."
PERIOD_CATEGORIES = "The categories of the summary, by name."
SPENDING_BUDGET_ID = "The limit of the category, to read its detail, or null without one."
SPENDING_LIMIT = "The limit, or null in a category without one."
SPENT_AMOUNT = (
    "What the category spent in the period, net of refunds, in the currency of the period. "
    "Each movement is converted with its own rate and rounded before adding."
)
USED_PERCENTAGE = (
    "What is spent over the limit, times a hundred, with one decimal and the half up. Null "
    "without a limit."
)
BUDGET_STATUS_SUMMARY = "Read what a limit spent"
BUDGET_STATUS_DESCRIPTION = (
    "One limit of a period, what its category spent and the movements that count in it: the "
    "expenses of the category and the refunds linked to them that arrived in the period, the "
    "newest first. Deleted movements and those marked as duplicates are not there."
)
BUDGET_STATUS_OK = "The limit and its movements."
BUDGET_NOT_FOUND = (
    "The limit does not exist, or the user cannot read its period. The same answer for both."
)
BUDGET_ID_INVALID = "`budget_id` is not a UUID."
BUDGET_PERIOD_ID = "The period the limit belongs to."
BUDGET_TRANSACTIONS = "The movements that count in the limit, the newest first."
MOVEMENT_ID = "The identifier of the movement."
MOVEMENT_DATE = "The day of the movement."
MOVEMENT_DESCRIPTION = "What the user wrote about it, or null."
MOVEMENT_TYPE = "`expense`, or `income` when it is a linked refund, which subtracts."
MOVEMENT_AMOUNT = "The amount as it was made, in its own currency."
MOVEMENT_CURRENCY = "The currency the movement was made in, as an ISO 4217 code."
MOVEMENT_BUDGET_AMOUNT = (
    "What it weighs on the limit, in the currency of the period, rounded on its own."
)
MOVEMENT_EXCHANGE_RATE = (
    "The rate it was converted to the period with, or null when it was already in its currency."
)
MOVEMENT_ACCOUNT = "The name of the account it moved."
MOVEMENT_SOURCE = "`manual`, or `automatic` when the system generated it."

# The web chat.
SEND_CHAT_MESSAGE_SUMMARY = "Write to Platita"
SEND_CHAT_MESSAGE_DESCRIPTION = (
    "Stores the message as written by the user of the session, and answers at once without "
    "processing it. The reply of Platita is not here: it shows up later in "
    "`GET /chat/messages`. The time of the message is the one the server received it at."
)
SEND_CHAT_MESSAGE_ACCEPTED = "The message was stored, pending. The worker processes it later."
SEND_CHAT_MESSAGE_INVALID = (
    "The text is empty or only spaces, or the header `Idempotency-Key` is missing."
)
SEND_CHAT_MESSAGE_REPEATED = (
    "This user already sent a message with that `Idempotency-Key`: nothing is stored, and the "
    "body is the message stored the first time."
)
SEND_CHAT_MESSAGE_NOT_FOUND = (
    "The web chat is disabled, or `quoted_message_id` is not a reply of Platita to this user."
)
IDEMPOTENCY_KEY = (
    "A UUID the browser generates once per message, and sends again unchanged if it repeats "
    "the request."
)
CHAT_TEXT = "What the user wrote."
CHAT_QUOTED_MESSAGE_ID = "The reply of Platita the user is answering to, if any."
CHAT_MESSAGE_ID = "The identifier of the message."
CHAT_MESSAGE_STATUS = "`pending` until the worker takes it."
LIST_CHAT_MESSAGES_SUMMARY = "Read the conversation"
LIST_CHAT_MESSAGES_DESCRIPTION = (
    "The messages of the web chat of the user of the session, what the user wrote and what "
    "Platita replied, in the order they happened. With `after`, only the ones that come after "
    "that message: it is what the dashboard asks every few seconds. It does not count as "
    "activity of the session."
)
LIST_CHAT_MESSAGES_OK = "The conversation. An empty list when there is nothing (new)."
LIST_CHAT_MESSAGES_INVALID = "`after` is not a UUID."
LIST_CHAT_MESSAGES_NOT_FOUND = (
    "The web chat is disabled, or `after` is not a message of the conversation of this user."
)
CHAT_AFTER = "The `next_cursor` of the previous answer. Without it, the whole conversation."
CHAT_MESSAGES = "The messages, in the order they happened."
CHAT_NEXT_CURSOR = (
    "Where the next read starts: the last message, or the same cursor when nothing is new. "
    "Null only when the conversation is empty."
)
CHAT_DIRECTION = "`inbound` if the user wrote it, `outbound` if Platita did."
CHAT_RESPONSE_KIND = "What kind of reply it is. Only in a message of Platita."
CHAT_CREATED_AT = "When it was received or written, in the time zone of the user."

# Development entry.
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

# The categories.
CATEGORIES_SUMMARY = "List the categories of expenses"
CATEGORIES_DESCRIPTION = (
    "The categories of expenses the user of the session can put a limit on: those of the base "
    "catalog and their own, by name, without telling capitals apart."
)
CATEGORIES_OK = "The categories of expenses of the user."
CATEGORIES_LIST = "The categories, by name."
CATEGORY_ID = "The identifier of the category."
CATEGORY_NAME = "The name of the category."
CATEGORY_IS_BASE = "Whether it is of the base catalog, which every user has."

# The currencies.
CURRENCIES_SUMMARY = "List the currencies"
CURRENCIES_DESCRIPTION = "The currencies of the catalog a budget period can be in, by code."
CURRENCIES_OK = "The currencies of the catalog."
CURRENCIES_LIST = "The currencies, by code."
CURRENCY_CODE = "The ISO 4217 code of the currency."
CURRENCY_NAME = "The name of the currency."
