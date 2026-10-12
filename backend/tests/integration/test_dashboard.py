"""Cases 28 to 34, 41 to 44, 49 and 50: the API serves the compiled dashboard (ADR 0016)."""

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
# Everything the page loads comes from its own origin, and no other page may embed it.
PAGE_POLICY = (
    "default-src 'self'; base-uri 'self'; form-action 'self'; "
    "frame-ancestors 'none'; object-src 'none'"
)


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


@pytest.mark.parametrize("path", ["/app/%2e%2e/outside.txt", "/app/..%2foutside.txt"])
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


def test_the_page_carries_its_content_policy(client: TestClient) -> None:
    """Case 41."""
    headers = client.get("/app/").headers

    assert headers["content-security-policy"] == PAGE_POLICY
    assert headers["x-frame-options"] == "DENY"


def test_the_dashboard_files_carry_the_same_policy(client: TestClient) -> None:
    """Case 42."""
    page = client.get("/app/").headers["content-security-policy"]
    script = client.get("/app/assets/app.js").headers["content-security-policy"]

    assert script == page


@pytest.mark.parametrize("path", ["/app/", "/app/assets/app.js", "/healthz", "/readyz"])
def test_no_response_lets_the_browser_guess_the_type_or_leak_the_referrer(
    client: TestClient, path: str
) -> None:
    """Case 43."""
    headers = client.get(path).headers

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"


def test_the_policy_does_not_break_the_api(client: TestClient) -> None:
    """Case 44."""
    for path in ("/healthz", "/readyz"):
        response = client.get(path)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_an_unexpected_error_carries_the_headers_too(
    database_url: str, dashboard_dir: Path
) -> None:
    """Case 49."""
    settings = load_settings({"DATABASE_URL": database_url, "DASHBOARD_DIR": str(dashboard_dir)})
    app = create_app(settings)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("unexpected")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("path", ["/application", "/apple/pie", "/healthz"])
def test_the_page_policy_does_not_reach_other_routes(client: TestClient, path: str) -> None:
    """Case 50."""
    headers = client.get(path).headers

    assert "content-security-policy" not in headers
    assert "x-frame-options" not in headers
