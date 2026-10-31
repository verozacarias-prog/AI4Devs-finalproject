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
UNSAFE_CHARACTERS_IN_ENV_VAR = "{name} can only have letters, numbers, _ and -"
INVALID_ENV_VAR = "{name} must be one of: {allowed}"
# The scaffold never runs in production (ADR 0016).
NOT_ALLOWED_IN_ENVIRONMENT = "{name} cannot be enabled in the {environment} environment"
NOT_A_POSITIVE_INTEGER = "{name} must be a whole number greater than zero"
# The call to the model must end before another worker can take the message (ADR 0010).
LOCK_NOT_LONGER_THAN_CALL = "{lock} must be greater than {call}"

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
CONFIRMATION_GROUP_BUDGET = "Presupuesto: el de {group}, del {start} al {end}"
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

# The question of a pending: what was understood, then one line for each thing that is missing,
# in this order (domain rules, § 5; FEAT-003).
QUESTION_ONE_MISSING = "Para anotar {movement} me falta un dato:"
QUESTION_SEVERAL_MISSING = "Para anotar {movement} me faltan unos datos:"
QUESTION_EXPENSE = "el gasto"
QUESTION_INCOME = "el ingreso"
QUESTION_MOVEMENT = "el movimiento"
QUESTION_AMOUNT_PART = " de {amount}"
QUESTION_CATEGORY_PART = " en {category}"
QUESTION_ACCOUNT_PART = " con {account}"
ASK_TYPE = "¿Fue un gasto o un ingreso?"
ASK_AMOUNT = "¿Cuánto fue?"
ASK_ACCOUNT = "¿Con qué cuenta? {options}."
# The last two options of a list go joined by this, and the rest by a comma.
LAST_OPTION_JOINER = " o "
OPTION_SEPARATOR = ", "
PROPOSE_CATEGORY = (
    "No encaja en ninguna de tus categorías. ¿Creo «{category}», o va en otra de las tuyas?"
)
# The name proposed is that of a category the user already has (domain rules, § 4).
OFFER_EXISTING_CATEGORY = "Ya tenés la categoría «{category}». ¿La uso, o preferís otro nombre?"
# Without a name to propose: the model gave none.
ASK_CATEGORY = "No encaja en ninguna de tus categorías. ¿En cuál lo anoto?"
CONFIRM_DRAFT = (
    "Tu presupuesto del {start} al {end} todavía no está confirmado. Ingreso estimado: "
    "{income}. {limits} ¿Lo confirmo así?"
)
DRAFT_LIMITS = "Topes: {limits}."
DRAFT_LIMIT = "{category} {amount}"
DRAFT_WITHOUT_LIMITS = "Sin topes."
NO_PERIOD = "No tenés un presupuesto para el {date}. Armalo en el dashboard y después avisame."
# Another movement while a pending awaits its reply: one at a time in delivery 2 (CA-36).
FINISH_THE_PENDING_FIRST = "Primero terminemos con lo anterior."
PENDING_DISCARDED = "Listo, no lo anoto."
# The model refused to interpret the message: it is not tried again (CA-40).
MODEL_REFUSED = (
    "No pude entender ese mensaje. ¿Me lo escribís de otra forma? Por ejemplo: «gasté 3500 en "
    "el súper con Mercado Pago»."
)
# A message whose attempts were used up (ADR 0010, point 4).
MESSAGE_FAILED = (
    "Tuve un problema y no pude procesar tu mensaje. ¿Me lo mandás de nuevo en un rato?"
)
# More than one possible period for the movement, as one of the user and one of a group:
# choosing between them belongs to the final delivery (FEAT-003, C2-52).
SEVERAL_PERIODS = (
    "Para esa fecha tenés más de un presupuesto, y todavía no sé elegir en cuál anotarlo. "
    "Por ahora no lo anoto."
)
# The daily cap of messages classified was reached: said once a day (domain rules, § 12).
DAILY_LIMIT_REACHED = (
    "Por hoy llegué al límite de mensajes que puedo leer. Lo que me mandes de acá en adelante "
    "lo guardo y lo proceso mañana."
)
# A registration that came with the quota of registration used up (domain rules, § 12).
REGISTRATION_QUOTA_USED_UP = (
    "Por hoy ya anoté todo lo que puedo. Este lo guardo y lo anoto mañana, con la fecha de hoy."
)
