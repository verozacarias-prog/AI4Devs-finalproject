"""Cases E19 to E23: the errors the server answers before reaching any use case.

They have the same body as every other error (docs/04-api.md) and leave no error line of
their own: the line of their request already says the result (docs/operacion.md, 6.3).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings
from tests.log_lines import events_of

pytestmark = pytest.mark.integration


@pytest.fixture
def stream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def client(database_url: str, tmp_path: Path, stream: io.StringIO) -> TestClient:
    dashboard = tmp_path / "dashboard"
    (dashboard / "assets").mkdir(parents=True)
    (dashboard / "index.html").write_text("<!doctype html><title>Platita</title>")
    settings = load_settings(
        {
            "DATABASE_URL": database_url,
            "APP_ENV": "production",
            "APP_VERSION": "test",
            "DASHBOARD_DIR": str(dashboard),
        }
    )
    return TestClient(create_app(settings, log_stream=stream))


def test_a_route_that_does_not_exist_answers_with_the_error_body(client: TestClient) -> None:
    """Case E19."""
    response = client.get("/no-existe")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}


def test_a_method_the_route_does_not_accept_answers_with_the_error_body(
    client: TestClient,
) -> None:
    """Case E20."""
    response = client.post("/healthz")

    assert response.status_code == 405
    assert response.json() == {"error": "method_not_allowed"}
    assert response.headers["allow"] == "GET"


def test_a_missing_file_of_the_dashboard_answers_with_the_error_body(client: TestClient) -> None:
    """Case E21."""
    response = client.get("/app/assets/falta.js")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}


@pytest.mark.parametrize(("method", "path"), [("GET", "/no-existe"), ("POST", "/healthz")])
def test_these_answers_carry_the_reference_and_the_security_headers(
    client: TestClient, method: str, path: str
) -> None:
    """Case E22."""
    headers = client.request(method, path).headers

    assert headers["x-request-id"]
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize(
    ("method", "path", "status"), [("GET", "/no-existe", 404), ("POST", "/healthz", 405)]
)
def test_these_requests_leave_their_line_and_no_error_line(
    client: TestClient, stream: io.StringIO, method: str, path: str, status: int
) -> None:
    """Case E23."""
    client.request(method, path)

    requests = events_of(stream, "http.request")
    assert len(requests) == 1
    assert requests[0]["result"] == status
    assert events_of(stream, "error.expected") == []
    assert events_of(stream, "error.unexpected") == []
