"""Every message the code writes for a person, in one place.

These are for whoever operates the system, so they are in English. The texts sent to the end
user go in Spanish and will live here too, in their own section.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.constants import Environment
from app.domain.errors import ErrorCode

# Start-up errors. They name the variable and never show a value.
MISSING_ENV_VAR = "Missing required environment variable: {name}"
INVALID_ENV_VAR = "{name} must be one of: {allowed}"
# The scaffold never runs in production (ADR 0016).
NOT_ALLOWED_IN_ENVIRONMENT = "{name} cannot be enabled in the {environment} environment"
NOT_A_POSITIVE_INTEGER = "{name} must be a whole number greater than zero"

# The test data script. It counts users and never names a phone or a balance.
TEST_DATA_SEEDED = "Test data: {created} created, {existing} already existed."

# What an operation command tells whoever ran it when it ends in an error. Each text may use
# the context of its error, which holds identifiers and catalog values only.
COMMAND_ERRORS: Mapping[str, str] = {
    ErrorCode.TEST_DATA_NOT_ALLOWED: (
        f"The test data script runs only in the {Environment.LOCAL} environment, and this one "
        "is {environment}. Nothing was written."
    ),
}
COMMAND_REFUSED = "The command was refused: {code}."
COMMAND_FAILED = "The command failed."
# A mistake of the code, for whoever reads the traceback: never shown to an end user.
NAIVE_INSTANT = "An instant needs its time zone to say which day it is"

# The identifier to look for in the logs.
ERROR_REFERENCE = "Reference: {reference}"

# For the end user, in Spanish: rioplatense, with voseo, warm and short (docs/01-producto.md).

# The confirmation of a registered movement: what it was, then what was assumed, one per line
# (domain rules, § 1; FEAT-003).
REGISTERED_EXPENSE = "¡Listo! Anoté un gasto de {amount} en {account}."
REGISTERED_INCOME = "¡Listo! Anoté un ingreso de {amount} en {account}."
CONFIRMATION_DATE = "Fecha: {date}"
CONFIRMATION_CURRENCY = "Moneda: {currency}"
CONFIRMATION_CATEGORY = "Categoría: {category}"
CONFIRMATION_PERSONAL_BUDGET = "Presupuesto: tu presupuesto personal, del {start} al {end}"
# A movement dated before its account was opened, which is already in its initial balance
# (domain rules, § 2).
BEFORE_ACCOUNT_OPENING = (
    "{account} la tenés cargada desde el {date}, así que lo que {done} antes ya está en el "
    "saldo con el que la diste de alta. Lo dejo sin anotar para no contarlo dos veces."
)
SPENT_BEFORE = "gastaste"
RECEIVED_BEFORE = "cobraste"
# How a day is written in a message: 17/10/2026, and 1/10/2026 without a leading zero.
DAY_FORMAT = "{day}/{month}/{year}"
# How an amount is written: $3.500, and $3.500,50 when it has cents.
THOUSANDS_SEPARATOR = "."
DECIMAL_SEPARATOR = ","
CURRENCY_SYMBOLS: Mapping[str, str] = {"ARS": "$", "USD": "US$"}

# What the assistant cannot do yet answers a fixed text (ADR 0018; roadmap, entrega 2).
CANNOT_REGISTER_YET = "Eso todavía no lo sé anotar. Por ahora me manejo con gastos e ingresos."
CANNOT_ANSWER_YET = (
    "Todavía no sé responder preguntas. Por ahora anoto gastos e ingresos, y tus saldos los ves "
    "en el dashboard."
)
# A message of no class: a greeting, or anything the model cannot place.
ASK_FOR_DETAILS = (
    "¡Hola! Soy Platita y te ayudo a llevar las cuentas. Contame qué gastaste o qué cobraste, y "
    "con qué cuenta. Por ejemplo: «gasté 3500 en el súper con Mercado Pago»."
)
