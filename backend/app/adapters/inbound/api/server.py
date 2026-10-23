"""The web server that serves the API. The only place that starts it."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI


def build_server(app: FastAPI, host: str, port: int) -> uvicorn.Server:
    # log_config=None keeps the server from installing its own handlers: its lines go through
    # the JSON handler of the process. access_log=False because that log prints the client IP,
    # which is never logged (docs/operacion.md 6.3).
    return uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_config=None, access_log=False)
    )
