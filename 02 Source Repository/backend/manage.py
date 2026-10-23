#!/usr/bin/env python
"""Django management entry point for the AssureX REST API."""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "assurex_api.settings")


def main() -> None:
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ImportError(
            "Django is not installed. Run `uv sync` from the repository root."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
