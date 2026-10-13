"""Entry point of the API process: `python -m app.main`."""

from __future__ import annotations

import os
import sys

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.api.server import build_server
from app.constants import API_HOST, API_PORT, EXIT_FAILED, EXIT_OK, LINE_END
from app.settings import SettingsError, load_settings


def main() -> int:
    try:
        settings = load_settings(os.environ)
    except SettingsError as error:
        # Its message names the variable and never a value, so it is all that is written.
        sys.stderr.write(str(error) + LINE_END)
        return EXIT_FAILED
    build_server(create_app(settings), API_HOST, API_PORT).run()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
