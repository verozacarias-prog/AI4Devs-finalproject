"""The values of the regression set, in one place."""

from __future__ import annotations

from decimal import Decimal

# How many times each case is asked by default: the model does not answer the same every time.
DEFAULT_RUNS = 5

# What one call of the classification prompt takes, rounded up, to announce a run before it starts.
ESTIMATED_INPUT_TOKENS = 5200
ESTIMATED_OUTPUT_TOKENS = 250
ESTIMATE_QUANTUM = Decimal("0.01")

# The path of a field: its parts are split by this, a number is a position in a list, and this
# last part counts the items of a list.
PATH_SEPARATOR = "."
LENGTH_PART = "length"
# What a path gives when the answer has nothing there, as a list shorter than the position.
ABSENT = "<ausente>"
# The attribute of a reply to a pending that holds the movement it reads.
READING_ATTRIBUTE = "reading"
# The outcome of a call that gave an answer the code would use, or would drop.
OUTCOME_OK = "ok"
OUTCOME_BLOCKED = "blocked"

# Where the reports are kept, next to this file, and how each one is named.
RESULTS_DIR_NAME = "results"
REPORT_SUFFIX = ".json"
REPORT_NAME = "{stamp}-{prompt_version}"
STAMP_FORMAT = "%Y%m%d-%H%M%S"

# What the script writes.
ANNOUNCEMENT = (
    "{cases} casos, {runs} corridas por caso: {calls} llamadas al modelo, unos US${cost}."
)
RUN_HINT = "Nada se llamó. Para correrlo, sumá --run."
STOPPED = "La corrida se frenó en el caso {case}: el proveedor falló. Revisá el saldo."
SUMMARY = (
    "Prompt {prompt_version}: {calls} llamadas, {blocked} bloqueadas, "
    "{input_tokens} tokens de entrada y {output_tokens} de salida, US${cost}."
)
OUTCOME_LINE = "  {outcome}: {count}"
FIELD_LINE = "  {field}: {hits}/{checked}"
MISS_LINE = "  {case} · {field}: se esperaba {expected!r} y vino {got!r}"
FIELDS_TITLE = "Aciertos por campo:"
MISSES_TITLE = "Errores:"
OUTCOMES_TITLE = "Llamadas por resultado:"
COMPARISON_TITLE = "Contra {prompt_version}:"
CHANGE_LINE = "  {field}: {before_hits}/{before_checked} → {after_hits}/{after_checked}"
WORSE_TITLE = "Casos que empeoraron:"
WORSE_LINE = "  {case}"
REPORT_SAVED = "Informe guardado en {path}."

# The cases, next to this file, and the keys of cases.json that are not paths of the answer.
CASES_FILE_NAME = "cases.json"
NAME_KEY = "name"
MESSAGE_KEY = "message"
TODAY_KEY = "today"
OPEN_BATCH_KEY = "open_batch"
EXPECTED_KEY = "expected"
PENDINGS_KEY = "pendings"
QUESTION_KEY = "question"
NUMBER_KEY = "number"
INTERPRETED_KEY = "interpreted"
MISSING_KEY = "missing"
AMOUNT_FIELD = "amount"
DATE_FIELD = "transaction_date"
# The day of the cases that do not say one, as in the specs: 17/10/2026.
DEFAULT_TODAY = "2026-10-17"
# Lucía of the tests (tests/support/registration_data.py), and the daily categories of the base
# catalog (domain rules § 4), the ones a user starts with.
ACCOUNTS = ("Galicia pesos", "Mercado Pago", "Efectivo", "Galicia USD")
EXPENSE_CATEGORIES = (
    "Supermercado",
    "Comida afuera y delivery",
    "Vivienda",
    "Servicios",
    "Transporte",
    "Salud",
    "Educación",
    "Ropa",
    "Hogar",
    "Salidas y ocio",
    "Suscripciones",
    "Mascotas",
    "Regalos",
    "Impuestos y trámites",
    "Insumos",
)
INCOME_CATEGORIES = (
    "Sueldo",
    "Aguinaldo",
    "Honorarios",
    "Ventas",
    "Jubilación y pensión",
    "Otros ingresos",
)
