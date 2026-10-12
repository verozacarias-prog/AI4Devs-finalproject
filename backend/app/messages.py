"""Every message the code writes for a person, in one place.

These are for whoever operates the system, so they are in English. The texts sent to the end
user go in Spanish and will live here too, in their own section.
"""

from __future__ import annotations

# Start-up errors. They name the variable and never show a value.
MISSING_ENV_VAR = "Missing required environment variable: {name}"
INVALID_ENV_VAR = "{name} must be one of: {allowed}"
