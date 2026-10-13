"""Case 40: the API contract is exported with a command, without needing the database."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adapters.inbound.api.export_openapi import export_openapi


def test_the_contract_is_exported_as_json_with_the_health_routes() -> None:
    contract = json.loads(export_openapi())

    assert contract["openapi"].startswith("3.")
    assert "/healthz" in contract["paths"]
    assert "/readyz" in contract["paths"]


def test_exporting_twice_gives_the_same_text() -> None:
    assert export_openapi() == export_openapi()


VERSIONED_CONTRACT = (
    Path(__file__).resolve().parents[3] / "frontend" / "src" / "api" / "openapi.json"
)


def test_the_versioned_contract_is_the_one_the_code_generates() -> None:
    """The reference and the types of the dashboard come from that file: it cannot lag behind."""
    if not VERSIONED_CONTRACT.is_file():
        pytest.skip("the dashboard is not in this checkout")

    assert VERSIONED_CONTRACT.read_text() == export_openapi(), (
        "regenerate it: python -m app.adapters.inbound.api.export_openapi "
        "> ../frontend/src/api/openapi.json"
    )
