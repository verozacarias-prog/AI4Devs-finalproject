"""Entry point of the API process: `uvicorn app.main:app`."""

from __future__ import annotations

import os

from app.adapters.inbound.api.app import create_app
from app.settings import load_settings

app = create_app(load_settings(os.environ))
