"""Gives every API request an identifier and logs one line when it ends."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.routing import Route

from app.adapters.inbound.api.routes import DASHBOARD_PREFIX, REQUEST_ID_HEADER
from app.adapters.outbound.observability.events import (
    ENDPOINT_SEPARATOR,
    Event,
    Field,
    LoggerName,
)
from app.adapters.outbound.observability.logs import request_id_var
from app.constants import MILLISECONDS_PER_SECOND

logger = logging.getLogger(LoggerName.API)


async def log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Not reset afterwards: whatever the server logs about this request once it leaves this
    # function, such as an unhandled error, carries the same identifier.
    request_id = uuid.uuid4().hex
    request_id_var.set(request_id)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as error:
        logger.error(
            Event.HTTP_REQUEST,
            extra={
                Field.ENDPOINT: _endpoint(request),
                Field.RESULT: status.HTTP_500_INTERNAL_SERVER_ERROR,
                Field.DURATION_MS: _elapsed_ms(started),
                Field.ERROR_TYPE: type(error).__name__,
            },
        )
        raise
    logger.info(
        Event.HTTP_REQUEST,
        extra={
            Field.ENDPOINT: _endpoint(request),
            Field.RESULT: response.status_code,
            Field.DURATION_MS: _elapsed_ms(started),
        },
    )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def _endpoint(request: Request) -> str:
    """The method and the route as the code declares it, read once the request was routed.

    Never the address that was asked for: it may carry an identifier, a query with data, or
    whatever someone typed. A request that matched no route is logged with its method alone.
    """
    route: object = request.scope.get("route")
    if isinstance(route, Route):
        return request.method + ENDPOINT_SEPARATOR + route.path
    # The dashboard is mounted, not routed: what marks its requests is the prefix they were
    # served under. Which file was asked for is not logged.
    if request.scope.get("root_path") == DASHBOARD_PREFIX:
        return request.method + ENDPOINT_SEPARATOR + DASHBOARD_PREFIX
    return request.method


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * MILLISECONDS_PER_SECOND)
