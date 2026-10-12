"""Serves the compiled dashboard under /app, from the same origin as the API (ADR 0016).

The backend knows nothing about the dashboard except the folder its build is copied to.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from fastapi import FastAPI, status
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.adapters.inbound.api.routes import DASHBOARD_MOUNT_NAME, DASHBOARD_PREFIX
from app.constants import DASHBOARD_ASSETS_FOLDER, DASHBOARD_INDEX_FILE


class DashboardFiles(StaticFiles):
    """Static files, plus the page itself for any inner route of the dashboard.

    The dashboard resolves its own routes in the browser, so reloading /app/cuentas has to
    return the page. A path that names a file is different: if the file is missing, that is
    a 404.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != status.HTTP_404_NOT_FOUND or _names_a_file(path):
                raise
            return await super().get_response(DASHBOARD_INDEX_FILE, scope)


def _names_a_file(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts) and (parts[0] == DASHBOARD_ASSETS_FOLDER or "." in parts[-1])


def mount_dashboard(app: FastAPI, directory: Path | None) -> None:
    """Does nothing when there is no compiled dashboard: the API still starts."""
    if directory is None or not (directory / DASHBOARD_INDEX_FILE).is_file():
        return
    app.mount(
        DASHBOARD_PREFIX, DashboardFiles(directory=directory, html=True), name=DASHBOARD_MOUNT_NAME
    )
