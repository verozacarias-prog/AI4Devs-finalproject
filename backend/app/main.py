"""Entry point of the API process: `python -m app.main`."""

from __future__ import annotations

import os

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.api.server import build_server
from app.constants import API_HOST, API_PORT
from app.settings import load_settings


def main() -> None:
    app = create_app(load_settings(os.environ))
    build_server(app, API_HOST, API_PORT).run()


if __name__ == "__main__":
    main()
