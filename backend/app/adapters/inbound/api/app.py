"""Builds the FastAPI application: the place where adapters are wired to use cases."""

from __future__ import annotations

import sys
from typing import TextIO

from fastapi import FastAPI

from app.adapters.inbound.api.dashboard import mount_dashboard
from app.adapters.inbound.api.errors import install_error_handlers
from app.adapters.inbound.api.health import build_health_router
from app.adapters.inbound.api.request_logging import log_request
from app.adapters.inbound.api.security_headers import add_security_headers
from app.adapters.outbound.observability.logs import configure_logging
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.database_health import PostgresDatabaseHealth
from app.constants import APP_TITLE
from app.domain.use_cases.check_readiness import CheckReadiness
from app.settings import Settings


def create_app(settings: Settings, log_stream: TextIO | None = None) -> FastAPI:
    configure_logging(log_stream or sys.stdout, settings.version)
    engine = create_db_engine(settings.database_url)

    app = FastAPI(title=APP_TITLE, version=settings.version)
    app.middleware("http")(add_security_headers)
    install_error_handlers(app, settings.environment)
    app.middleware("http")(log_request)
    app.include_router(build_health_router(CheckReadiness(PostgresDatabaseHealth(engine))))
    mount_dashboard(app, settings.dashboard_dir)
    return app
