"""Prints the contract of the API as JSON: `python -m app.adapters.inbound.api.export_openapi`.

The dashboard generates its types from this file, so the two cannot drift apart without the
pipeline noticing (ADR 0005). It needs no database and no secret.
"""

from __future__ import annotations

import io
import json
import sys

from app.adapters.inbound.api.app import create_app
from app.constants import (
    CONTRACT_EXPORT_ENVIRONMENT,
    DEFAULT_VERSION,
    JSON_INDENT,
    LINE_END,
    UNUSED_DATABASE_URL,
)
from app.settings import Settings


def export_openapi() -> str:
    settings = Settings(
        # The contract does not depend on the database: the engine is never used here.
        database_url=UNUSED_DATABASE_URL,
        environment=CONTRACT_EXPORT_ENVIRONMENT,
        version=DEFAULT_VERSION,
    )
    app = create_app(settings, log_stream=io.StringIO())
    contract = json.dumps(app.openapi(), indent=JSON_INDENT, ensure_ascii=False, sort_keys=True)
    return contract + LINE_END


if __name__ == "__main__":
    sys.stdout.write(export_openapi())
