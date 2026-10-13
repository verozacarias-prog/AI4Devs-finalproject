"""Which endpoint a request line is about (docs/operacion.md, 6.3).

Cases 68 to 72, 74 and 80. The line carries the method and the route as the code declares it,
never the address that was asked for.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings
from tests.log_lines import LogLine, events_of

pytestmark = pytest.mark.integration

THING_ID = "8f3a1c2e-5b7d-4e9a-a1b2-c3d4e5f60718"
PHONE = "+5491100000000"


@pytest.fixture
def stream() -> io.StringIO:
    return io.StringIO()


def _app(database_url: str, stream: io.StringIO, dashboard_dir: Path | None = None) -> FastAPI:
    environ = {"DATABASE_URL": database_url, "APP_ENV": "production", "APP_VERSION": "test"}
    if dashboard_dir is not None:
        environ["DASHBOARD_DIR"] = str(dashboard_dir)
    return create_app(load_settings(environ), log_stream=stream)


def _request_line(stream: io.StringIO) -> LogLine:
    [line] = events_of(stream, "http.request")
    return line


def test_the_line_of_a_request_says_its_method_and_its_route(
    database_url: str, stream: io.StringIO
) -> None:
    # Case 68.
    TestClient(_app(database_url, stream)).get("/healthz")

    assert _request_line(stream)["endpoint"] == "GET /healthz"


def test_a_route_with_a_parameter_is_logged_as_declared_without_the_value(
    database_url: str, stream: io.StringIO
) -> None:
    # Case 69.
    app = _app(database_url, stream)

    @app.get("/things/{thing_id}")
    def thing(thing_id: str) -> dict[str, str]:
        return {"id": thing_id}

    response = TestClient(app).get(f"/things/{THING_ID}")

    assert response.status_code == 200
    assert _request_line(stream)["endpoint"] == "GET /things/{thing_id}"
    assert THING_ID not in stream.getvalue()


def test_the_query_of_a_request_is_never_logged(database_url: str, stream: io.StringIO) -> None:
    # Case 70.
    response = TestClient(_app(database_url, stream)).get(
        "/healthz", params={"phone": PHONE, "text": "farmacia"}
    )

    assert response.status_code == 200
    assert _request_line(stream)["endpoint"] == "GET /healthz"
    logged = stream.getvalue()
    for sent in (PHONE, "5491100000000", "phone", "farmacia"):
        assert sent not in logged


def test_a_route_that_does_not_exist_is_logged_with_its_method_alone(
    database_url: str, stream: io.StringIO
) -> None:
    # Case 71.
    response = TestClient(_app(database_url, stream)).get(f"/nobody-home/{PHONE}")

    assert response.status_code == 404
    assert _request_line(stream)["endpoint"] == "GET"
    logged = stream.getvalue()
    assert "nobody-home" not in logged
    assert "5491100000000" not in logged


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_the_pages_of_the_contract_are_logged_with_their_route(
    database_url: str, stream: io.StringIO, path: str
) -> None:
    # Case 80. The framework serves them, and they are routes like any other.
    response = TestClient(_app(database_url, stream)).get(path)

    assert response.status_code == 200
    assert _request_line(stream)["endpoint"] == f"GET {path}"


def test_the_reference_has_one_page_only(database_url: str, stream: io.StringIO) -> None:
    # The second page the framework offers shows the same contract, so it is turned off.
    response = TestClient(_app(database_url, stream)).get("/redoc")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}


@pytest.mark.parametrize("path", ["/app/", "/app/assets/app.js", "/app/cuentas"])
def test_a_request_to_the_dashboard_is_logged_without_the_file(
    database_url: str, stream: io.StringIO, tmp_path: Path, path: str
) -> None:
    # Case 72.
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Platita</title>")
    (tmp_path / "assets" / "app.js").write_text("console.log('platita')")

    response = TestClient(_app(database_url, stream, tmp_path)).get(path)

    assert response.status_code == 200
    assert _request_line(stream)["endpoint"] == "GET /app"
    assert "app.js" not in stream.getvalue()
    assert "cuentas" not in stream.getvalue()


def test_the_line_of_a_request_that_fails_says_its_endpoint_too(
    database_url: str, stream: io.StringIO
) -> None:
    # Case 74.
    app = _app(database_url, stream)

    @app.post("/things/{thing_id}/boom")
    def boom(thing_id: str) -> None:
        raise RuntimeError(f"could not touch {thing_id}")

    response = TestClient(app, raise_server_exceptions=False).post(
        f"/things/{THING_ID}/boom",
        json={},
        headers={"Origin": "http://testserver"},
    )

    assert response.status_code == 500
    line = _request_line(stream)
    assert line["result"] == 500
    assert line["endpoint"] == "POST /things/{thing_id}/boom"
    assert THING_ID not in stream.getvalue()
