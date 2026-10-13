"""Every message the code writes for a person, in one place.

These are for whoever operates the system, so they are in English. The texts sent to the end
user go in Spanish and will live here too, in their own section.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.domain.errors import ErrorCode

# Start-up errors. They name the variable and never show a value.
MISSING_ENV_VAR = "Missing required environment variable: {name}"
INVALID_ENV_VAR = "{name} must be one of: {allowed}"

# The test data script. It counts users and never names a phone or a balance.
TEST_DATA_SEEDED = "Test data: {created} created, {existing} already existed."

# What an operation command tells whoever ran it when it ends in an error. Each text may use
# the context of its error, which holds identifiers and catalog values only.
COMMAND_ERRORS: Mapping[str, str] = {
    ErrorCode.TEST_DATA_NOT_ALLOWED: (
        "The test data script runs only in the local environment, and this one is "
        "{environment}. Nothing was written."
    ),
}
COMMAND_REFUSED = "The command was refused: {code}."
COMMAND_FAILED = "The command failed."
# The identifier to look for in the logs.
ERROR_REFERENCE = "Reference: {reference}"
