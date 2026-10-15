"""Builds the FastAPI application: the place where adapters are wired to use cases."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

from fastapi import FastAPI

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.accounts import build_accounts_router
from app.adapters.inbound.api.chat import build_chat_router
from app.adapters.inbound.api.dashboard import mount_dashboard
from app.adapters.inbound.api.dev_entry import build_dev_entry_router
from app.adapters.inbound.api.errors import install_error_handlers
from app.adapters.inbound.api.health import build_health_router
from app.adapters.inbound.api.origin_check import refuse_requests_from_elsewhere
from app.adapters.inbound.api.request_logging import log_request
from app.adapters.inbound.api.security_headers import add_security_headers
from app.adapters.inbound.api.session import build_session_router
from app.adapters.outbound.observability.events import Event, LoggerName
from app.adapters.outbound.observability.logs import configure_logging
from app.adapters.outbound.postgres.connection import create_db_engine
from app.adapters.outbound.postgres.database_health import PostgresDatabaseHealth
from app.adapters.outbound.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.constants import APP_TITLE, Environment
from app.domain.use_cases.authenticate_session import AuthenticateSession, ValidateSession
from app.domain.use_cases.check_readiness import CheckReadiness
from app.domain.use_cases.close_session import CloseSession
from app.domain.use_cases.list_accounts import ListAccounts
from app.domain.use_cases.list_chat_messages import ListChatMessages
from app.domain.use_cases.list_test_users import ListTestUsers
from app.domain.use_cases.open_dev_session import OpenDevSession
from app.domain.use_cases.send_chat_message import SendChatMessage
from app.settings import Settings
from app.shared.clock import Clock, SystemClock

logger = logging.getLogger(LoggerName.API)


def create_app(
    settings: Settings, log_stream: TextIO | None = None, clock: Clock | None = None
) -> FastAPI:
    configure_logging(log_stream or sys.stdout, settings.version)
    engine = create_db_engine(settings.database_url)
    # Only a test passes one, to fix the instant.
    clock = clock or SystemClock()

    def unit_of_work() -> SqlAlchemyUnitOfWork:
        # One for each request: it holds the connection of its transaction.
        return SqlAlchemyUnitOfWork(engine)

    app = FastAPI(
        title=APP_TITLE,
        version=settings.version,
        description=reference.API_DESCRIPTION,
        openapi_tags=reference.TAGS,
        # One page for the reference is enough: the other one shows the same contract.
        redoc_url=None,
    )
    # The middleware added last runs first: the request is logged, gets its headers, and
    # only then is checked, so a refused one leaves its line and carries its reference.
    app.middleware("http")(refuse_requests_from_elsewhere)
    app.middleware("http")(add_security_headers)
    install_error_handlers(app, settings.environment)
    app.middleware("http")(log_request)
    app.include_router(build_health_router(CheckReadiness(PostgresDatabaseHealth(engine))))
    app.include_router(
        build_session_router(
            lambda: AuthenticateSession(unit_of_work(), clock),
            lambda: CloseSession(unit_of_work(), clock),
        )
    )
    app.include_router(
        build_accounts_router(
            lambda: AuthenticateSession(unit_of_work(), clock),
            lambda: ListAccounts(unit_of_work(), clock),
        )
    )
    if settings.web_chat_enabled:
        app.include_router(
            build_chat_router(
                lambda: AuthenticateSession(unit_of_work(), clock),
                lambda: ValidateSession(unit_of_work(), clock),
                lambda: SendChatMessage(unit_of_work(), clock),
                lambda: ListChatMessages(unit_of_work()),
            )
        )
    if settings.dev_entry_enabled:
        # Said at every start, so that nobody leaves it on without knowing (ADR 0016).
        logger.warning(Event.DEV_SCAFFOLD_ENABLED)
        in_local = settings.environment is Environment.LOCAL
        app.include_router(
            build_dev_entry_router(
                lambda: OpenDevSession(unit_of_work(), clock, settings.environment),
                (lambda: ListTestUsers(unit_of_work())) if in_local else None,
            )
        )
    mount_dashboard(app, settings.dashboard_dir)
    return app
