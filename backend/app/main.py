"""Entry point of the API process: `python -m app.main`."""

from __future__ import annotations

import os

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.api.server import build_server
from app.settings import load_settings

HOST = "0.0.0.0"  # noqa: S104 - inside the container; Compose publishes it on localhost only
PORT = 8000


def main() -> None:
    app = create_app(load_settings(os.environ))
    build_server(app, HOST, PORT).run()


if __name__ == "__main__":
    main()
