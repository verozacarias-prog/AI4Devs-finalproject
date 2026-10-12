"""Cases 28 to 34: the API serves the compiled dashboard under /app (ADR 0016)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings

pytestmark = pytest.mark.integration

INDEX_HTML = "<!doctype html><title>Platita</title><div id=root></div>"
SCRIPT = "console.log('platita')"
OUTSIDE_FILE = "this file is outside the dashboard folder"


@pytest.fixture
def dashboard_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "dashboard"
    (directory / "assets").mkdir(parents=True)
    (directory / "index.html").write_text(INDEX_HTML)
    (directory / "assets" / "app.js").write_text(SCRIPT)
    (tmp_path / "outside.txt").write_text(OUTSIDE_FILE)
    return directory


@pytest.fixture
def client(database_url: str, dashboard_dir: Path) -> TestClient:
    settings = load_settings({"DATABASE_URL": database_url, "DASHBOARD_DIR": str(dashboard_dir)})
    return TestClient(create_app(settings))


def test_the_api_serves_the_dashboard_page(client: TestClient) -> None:
    """Case 28."""
    response = client.get("/app/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX_HTML


def test_the_api_serves_the_dashboard_files(client: TestClient) -> None:
    """Case 29."""
    response = client.get("/app/assets/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.text == SCRIPT


def test_an_inner_route_of_the_dashboard_opens_the_application(client: TestClient) -> None:
    """Case 30."""
    response = client.get("/app/cuentas")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX_HTML


def test_a_missing_file_does_not_return_the_page(client: TestClient) -> None:
    """Case 31."""
    response = client.get("/app/assets/no-existe.js")

    assert response.status_code == 404
    assert INDEX_HTML not in response.text


@pytest.mark.parametrize(
    "path", ["/app/../outside.txt", "/app/%2e%2e/outside.txt", "/app/..%2foutside.txt"]
)
def test_a_request_cannot_leave_the_dashboard_folder(client: TestClient, path: str) -> None:
    """Case 32."""
    response = client.get(path)

    assert OUTSIDE_FILE not in response.text


def test_the_api_routes_do_not_change(client: TestClient) -> None:
    """Case 33."""
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_without_a_compiled_dashboard_the_api_still_starts(
    database_url: str, tmp_path: Path
) -> None:
    """Case 34."""
    settings = load_settings(
        {"DATABASE_URL": database_url, "DASHBOARD_DIR": str(tmp_path / "missing")}
    )
    client = TestClient(create_app(settings))

    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert client.get("/app/").status_code == 404


def test_without_the_dashboard_setting_the_api_still_starts(database_url: str) -> None:
    """Case 34."""
    client = TestClient(create_app(load_settings({"DATABASE_URL": database_url})))

    assert client.get("/healthz").status_code == 200
    assert client.get("/app/").status_code == 404
