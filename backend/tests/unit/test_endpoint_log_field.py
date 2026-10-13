"""Case 73: the endpoint of a log line passes the filter only with the shape of one.

A method followed by a route as the code declares it. Anything else may be an address someone
typed, so it is redacted (docs/operacion.md, 6.3).
"""

from __future__ import annotations

import io
import json
import logging

import pytest

from app.adapters.outbound.observability.logs import REDACTED, build_handler


def _logged_endpoint(value: object) -> object:
    stream = io.StringIO()
    logger = logging.getLogger("platita.test.endpoint")
    logger.handlers = [build_handler(stream, version="test")]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.info("http.request", extra={"endpoint": value})
    [raw] = stream.getvalue().splitlines()
    line: dict[str, object] = json.loads(raw)
    return line["endpoint"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "GET /healthz",
        "POST /dev/session",
        "GET /budget-periods/{budget_period_id}",
        "DELETE /family-groups/{family_group_id}/invitations/{invitation_id}",
        "GET /app",
        "GET /v2/accounts",
        "GET /oauth2/callback",
        "GET",
    ],
)
def test_a_method_with_a_declared_route_passes(endpoint: str) -> None:
    assert _logged_endpoint(endpoint) == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "GET /healthz?phone=+5491100000000",
        "GET /users/+5491100000000",
        "GET /budget-periods/8f3a1c2e-5b7d-4e9a-a1b2-c3d4e5f60718",
        # An identifier that happens to start with a letter is still an identifier.
        "GET /budget-periods/af3a1c2e-5b7d-4e9a-a1b2-c3d4e5f60718",
        "GET /budget-periods/af3a1c2e5b7d4e9aa1b2c3d4e5f60718",
        "GET /users/5491100000000",
        "GET /search/gasté 3500 en la farmacia",
        "GET /Things/Lucía",
        "BREW /healthz",
        "get /healthz",
        "/healthz",
        "GET healthz",
        "GET  /healthz",
        "GET /" + "a" * 200,
        "",
        42,
        ["GET /healthz"],
    ],
)
def test_anything_else_is_redacted(endpoint: object) -> None:
    assert _logged_endpoint(endpoint) == REDACTED
