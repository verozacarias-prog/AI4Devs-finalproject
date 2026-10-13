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

# An extra field of the answer, for the client to go on: never something the client sent.
DetailValue = str | int | bool | list[str]
# What the error was touching, for the log: an identifier or a value of a closed catalog.
# Typed this way so that free text cannot travel in it.
ContextValue = uuid.UUID | StrEnum


class ContextField(StrEnum):
    """The catalog values an error may say it was touching. Identifiers end in `_id`."""

    ENVIRONMENT = "environment"


class ErrorCategory(StrEnum):
    NOT_FOUND = "not_found"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    INVALID = "invalid"


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


class StoreRejectionError(Exception):
    """The store refused a write no rule foresaw. Not a DomainError: it is a failure of the code.

    It carries the name of the constraint and never the row.
    """

    def __init__(self, constraint: str | None) -> None:
        super().__init__(constraint)
        self.constraint = constraint
