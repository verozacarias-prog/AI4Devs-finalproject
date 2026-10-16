"""Health routes (docs/04-api.md). They ask for no session and return nobody's data."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.adapters.inbound.api import reference
from app.adapters.inbound.api.routes import HEALTH_TAG, HEALTHZ, QUEUEZ, READYZ, HealthState
from app.domain.use_cases.health.check_queue import CheckQueue
from app.domain.use_cases.health.check_readiness import CheckReadiness


class HealthStatus(BaseModel):
    status: HealthState = Field(description=reference.HEALTH_STATE)


def build_health_router(
    check_readiness: CheckReadiness, check_queue: Callable[[], CheckQueue]
) -> APIRouter:
    router = APIRouter(tags=[HEALTH_TAG])

    @router.get(
        HEALTHZ,
        summary=reference.HEALTHZ_SUMMARY,
        description=reference.HEALTHZ_DESCRIPTION,
        response_description=reference.HEALTHZ_OK,
    )
    def healthz() -> HealthStatus:
        return HealthStatus(status=HealthState.OK)

    @router.get(
        READYZ,
        summary=reference.READYZ_SUMMARY,
        description=reference.READYZ_DESCRIPTION,
        response_description=reference.READYZ_OK,
        response_model=HealthStatus,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": HealthStatus,
                "description": reference.READYZ_UNAVAILABLE,
            }
        },
    )
    def readyz() -> JSONResponse:
        return _health(check_readiness.execute())

    @router.get(
        QUEUEZ,
        summary=reference.QUEUEZ_SUMMARY,
        description=reference.QUEUEZ_DESCRIPTION,
        response_description=reference.QUEUEZ_OK,
        response_model=HealthStatus,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": HealthStatus,
                "description": reference.QUEUEZ_UNAVAILABLE,
            }
        },
    )
    def queuez() -> JSONResponse:
        return _health(check_queue().execute())

    return router


def _health(ok: bool) -> JSONResponse:
    if ok:
        return JSONResponse(HealthStatus(status=HealthState.OK).model_dump())
    return JSONResponse(
        HealthStatus(status=HealthState.UNAVAILABLE).model_dump(),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
