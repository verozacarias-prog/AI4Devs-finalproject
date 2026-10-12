"""Health routes (docs/04-api.md). They ask for no session and return nobody's data."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.adapters.inbound.api.routes import HEALTH_TAG, HEALTHZ, READYZ, HealthState
from app.domain.use_cases.check_readiness import CheckReadiness


class HealthStatus(BaseModel):
    status: HealthState


def build_health_router(check_readiness: CheckReadiness) -> APIRouter:
    router = APIRouter(tags=[HEALTH_TAG])

    @router.get(HEALTHZ)
    def healthz() -> HealthStatus:
        return HealthStatus(status=HealthState.OK)

    @router.get(
        READYZ,
        response_model=HealthStatus,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthStatus}},
    )
    def readyz() -> JSONResponse:
        if check_readiness.execute():
            return JSONResponse(HealthStatus(status=HealthState.OK).model_dump())
        return JSONResponse(
            HealthStatus(status=HealthState.UNAVAILABLE).model_dump(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return router
