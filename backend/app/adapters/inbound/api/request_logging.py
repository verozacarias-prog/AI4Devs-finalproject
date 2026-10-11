"""Gives every API request an identifier and logs one line when it ends."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.adapters.outbound.observability.logs import LOGGER_NAME, request_id_var

logger = logging.getLogger(f"{LOGGER_NAME}.api")


async def log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    token = request_id_var.set(uuid.uuid4().hex)
    started = time.monotonic()
    try:
        response = await call_next(request)
        duration_ms = round((time.monotonic() - started) * 1000)
        logger.info(
            "http.request", extra={"result": response.status_code, "duration_ms": duration_ms}
        )
        return response
    finally:
        request_id_var.reset(token)
