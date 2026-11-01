"""The errors a business rule foresees, and the one the store raises when no rule did.

They know nothing about HTTP or the database. Each inbound adapter turns them into its own
output in a single place: a status, a message, an exit code (ADR 0001).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from enum import StrEnum
from typing import ClassVar

from app.constants import Environment
from app.domain.entities.classification import ModelUsage
from app.domain.entities.llm_call import LlmOutcome

# An extra field of the answer, for the client to go on: never something the client sent.
DetailValue = str | int | bool | list[str]
# What the error was touching, for the log: an identifier or a value of a closed catalog.
# Typed this way so that free text cannot travel in it.
ContextValue = uuid.UUID | StrEnum


class ContextField(StrEnum):
    """The catalog values an error may say it was touching. Identifiers end in `_id`."""

    ENVIRONMENT = "environment"
    # How a call to the model ended: one of LlmOutcome.
    OUTCOME = "outcome"


class ErrorCategory(StrEnum):
    NOT_FOUND = "not_found"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    INVALID = "invalid"
    # A service the use case depends on did not answer, as the language model.
    UNAVAILABLE = "unavailable"


class ErrorCode(StrEnum):
    """The stable codes. A client and a log line tell errors apart by these, never by a text."""

    # A unique key that was already there, when no use case gave the conflict its own code.
    CONFLICT = "conflict"
    # What does not exist, belongs to someone else or is turned off, when it needs no code of
    # its own. The same word the API answers for a route that does not exist.
    NOT_FOUND = "not_found"
    # No valid session. One code for every reason, so that the answer tells none apart.
    UNAUTHORIZED = "unauthorized"
    TEST_DATA_NOT_ALLOWED = "test_data_not_allowed"
    # The call to the model gave no answer to use: the message is tried again later.
    MODEL_CALL_FAILED = "model_call_failed"
    # The content of a budget period (docs/04-api.md).
    GROUP_PERIOD_NOT_SUPPORTED = "group_period_not_supported"
    NOT_THE_OWNER = "not_the_owner"
    PERIOD_END_REQUIRED = "period_end_required"
    PERIOD_DATES_INVERTED = "period_dates_inverted"
    PERIOD_END_NOT_MATCHING = "period_end_not_matching"
    BIWEEKLY_START_INVALID = "biweekly_start_invalid"
    CONFIRMED_PERIOD_FIXED = "confirmed_period_fixed"
    BUDGET_PERIOD_OVERLAP = "budget_period_overlap"
    BUDGET_LIMIT_NOT_POSITIVE = "budget_limit_not_positive"
    BUDGET_CATEGORY_REPEATED = "budget_category_repeated"
    BUDGET_CATEGORY_NOT_EXPENSE = "budget_category_not_expense"
    ESTIMATED_INCOME_NEGATIVE = "estimated_income_negative"
    AMOUNT_TOO_LARGE = "amount_too_large"
    CURRENCY_NOT_FOUND = "currency_not_found"


class DomainError(Exception):
    """An error a rule foresees. Its text is its code: it never carries a value."""

    category: ClassVar[ErrorCategory]

    def __init__(
        self,
        code: str,
        *,
        details: Mapping[str, DetailValue] | None = None,
        context: Mapping[str, ContextValue] | None = None,
        constraint: str | None = None,
    ) -> None:
        if not hasattr(type(self), "category"):
            # Only an error with a category can be turned into an answer.
            raise TypeError(type(self).__name__)
        super().__init__(code)
        self.code = code
        self.details = dict(details or {})
        self.context = dict(context or {})
        # Set by the adapter that translated a rejected write. A name of the schema.
        self.constraint = constraint


class NotFoundError(DomainError):
    """It does not exist, or it belongs to someone else: the two are told apart nowhere."""

    category = ErrorCategory.NOT_FOUND


class UnauthenticatedError(DomainError):
    """There is no valid session: missing, unknown, revoked or expired, told apart nowhere."""

    category = ErrorCategory.UNAUTHENTICATED

    def __init__(self) -> None:
        super().__init__(ErrorCode.UNAUTHORIZED)


class ForbiddenError(DomainError):
    category = ErrorCategory.FORBIDDEN


class ConflictError(DomainError):
    category = ErrorCategory.CONFLICT


class InvalidError(DomainError):
    """A value is missing or breaks a rule."""

    category = ErrorCategory.INVALID


class TestDataNotAllowedError(ForbiddenError):
    """The test data script was asked to run outside the local environment."""

    __test__ = False  # not a test class, whatever its name suggests to pytest

    def __init__(self, environment: Environment) -> None:
        super().__init__(
            ErrorCode.TEST_DATA_NOT_ALLOWED, context={ContextField.ENVIRONMENT: environment}
        )
        self.environment = environment


class InconsistentDataError(Exception):
    """Stored data breaks a rule the database already enforces, so no answer can be trusted.

    Not a DomainError: no rule foresees it, and it ends as an unexpected error. It carries no
    value of the data.
    """


class StoreRejectionError(Exception):
    """The store refused a write no rule foresaw. Not a DomainError: it is a failure of the code.

    It carries the name of the constraint and never the row.
    """

    def __init__(self, constraint: str | None) -> None:
        super().__init__(constraint)
        self.constraint = constraint


class StoreUnavailableError(Exception):
    """The store did not answer, or two transactions collided: it may work a while later.

    Not a DomainError: no rule foresees it. A message that meets it is tried again (CA-44).
    """


class ModelCallFailedError(DomainError):
    """The call to the model did not give an answer to use: the message is tried again later.

    It says how the call ended, a value of a closed catalog, and never what was sent or
    received.
    """

    category = ErrorCategory.UNAVAILABLE

    def __init__(self, outcome: LlmOutcome, usage: ModelUsage | None = None) -> None:
        super().__init__(ErrorCode.MODEL_CALL_FAILED, context={ContextField.OUTCOME: outcome})
        self.outcome = outcome
        # Which provider, model and prompt were called, with no tokens: the call gave none.
        self.usage = usage


class ModelRefusedError(Exception):
    """The model refused to interpret the message: trying again would get the same answer."""

    def __init__(self, usage: ModelUsage | None = None) -> None:
        super().__init__()
        self.usage = usage
