"""Health routes (docs/04-api.md). They ask for no session and return nobody's data."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain.use_cases.check_readiness import CheckReadiness


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]


def build_health_router(check_readiness: CheckReadiness) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/healthz")
    def healthz() -> HealthStatus:
        return HealthStatus(status="ok")

    @router.get("/readyz", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthStatus}})
    def readyz() -> JSONResponse:
        if check_readiness.execute():
            return JSONResponse(HealthStatus(status="ok").model_dump())
        return JSONResponse(
            HealthStatus(status="unavailable").model_dump(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return router
