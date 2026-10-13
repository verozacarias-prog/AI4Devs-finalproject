"""The security headers the API sends, in one place (ADR 0016).

Because the API serves the HTML of the dashboard, it is also the one that tells the browser
what that page may load.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.adapters.inbound.api.routes import DASHBOARD_PREFIX

# Sent with every response.
COMMON_HEADERS = {
    # The browser must trust the declared content type instead of guessing it.
    "X-Content-Type-Options": "nosniff",
    # Never tell another site which page the user came from.
    "Referrer-Policy": "no-referrer",
}

# Sent with the dashboard only. Everything the page loads comes from its own origin: no
# inline code, no other site, and no other page may embed it. The interactive API docs are
# not under this policy, because they load their code from elsewhere.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
    )
)
DASHBOARD_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
}


def security_headers_for(path: str) -> dict[str, str]:
    """The headers a response to this path must carry."""
    is_dashboard = path == DASHBOARD_PREFIX or path.startswith(f"{DASHBOARD_PREFIX}/")
    return COMMON_HEADERS | DASHBOARD_HEADERS if is_dashboard else COMMON_HEADERS


async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers.update(security_headers_for(request.url.path))
    return response
