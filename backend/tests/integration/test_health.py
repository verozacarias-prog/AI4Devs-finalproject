"""Casos 1 a 5: las rutas de salud (contrato en docs/04-api.md)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings
from tests.conftest import UNREACHABLE_DATABASE_URL

pytestmark = pytest.mark.integration


def client_for(database_url: str) -> TestClient:
    return TestClient(create_app(load_settings({"DATABASE_URL": database_url})))


def test_healthz_says_the_process_is_alive(database_url: str) -> None:
    response = client_for(database_url).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_does_not_depend_on_the_database() -> None:
    response = client_for(UNREACHABLE_DATABASE_URL).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_is_ok_when_the_database_is_reachable(database_url: str) -> None:
    response = client_for(database_url).get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_is_unavailable_when_the_database_is_down() -> None:
    response = client_for(UNREACHABLE_DATABASE_URL).get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_health_routes_do_not_ask_for_a_session(database_url: str, path: str) -> None:
    client = client_for(database_url)
    client.cookies.clear()

    response = client.get(path)

    assert response.status_code == 200
    assert "set-cookie" not in response.headers
