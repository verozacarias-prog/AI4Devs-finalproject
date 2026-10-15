"""Entry point of the worker process: `python -m app.adapters.inbound.message_worker.main`."""

from __future__ import annotations

import os
import sys

from app.adapters.inbound.message_worker.worker import create_worker
from app.constants import EXIT_FAILED, LINE_END
from app.settings import SettingsError, load_settings


def main() -> int:
    try:
        settings = load_settings(os.environ)
    except SettingsError as error:
        # Its message names the variable and never a value, so it is all that is written.
        sys.stderr.write(str(error) + LINE_END)
        return EXIT_FAILED
    create_worker(settings).run_forever()


if __name__ == "__main__":
    sys.exit(main())
