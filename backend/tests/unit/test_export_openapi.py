"""Case 40: the API contract is exported with a command, without needing the database."""

from __future__ import annotations

import json

from app.adapters.inbound.api.export_openapi import export_openapi


def test_the_contract_is_exported_as_json_with_the_health_routes() -> None:
    contract = json.loads(export_openapi())

    assert contract["openapi"].startswith("3.")
    assert "/healthz" in contract["paths"]
    assert "/readyz" in contract["paths"]


def test_exporting_twice_gives_the_same_text() -> None:
    assert export_openapi() == export_openapi()
