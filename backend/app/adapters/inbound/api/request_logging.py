"""Gives every API request an identifier and logs one line when it ends."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status

from app.adapters.outbound.observability.logs import LOGGER_NAME, request_id_var

logger = logging.getLogger(f"{LOGGER_NAME}.api")


async def log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Not reset afterwards: whatever the server logs about this request once it leaves this
    # function, such as an unhandled error, carries the same identifier.
    request_id_var.set(uuid.uuid4().hex)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as error:
        logger.error(
            "http.request",
            extra={
                "result": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "duration_ms": _elapsed_ms(started),
                "error_type": type(error).__name__,
            },
        )
        raise
    logger.info(
        "http.request",
        extra={"result": response.status_code, "duration_ms": _elapsed_ms(started)},
    )
    return response


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
