"""Filesystem helpers shared by document and claim endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings


def uploads_dir() -> Path:
    path = Path(settings.UPLOADS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(contents: bytes, filename: str) -> tuple[str, Path]:
    """Persist an upload and return the legacy-relative path plus absolute path.

    The legacy database stores paths such as ``uploads/CLM-..._receipt.pdf``.
    Keeping that format means the SQLite database stays readable by both the
    FastAPI app and the REST API.
    """
    safe_name = os.path.basename(filename or "upload.bin")
    absolute = uploads_dir() / safe_name
    absolute.write_bytes(contents)
    return str(Path("uploads") / safe_name), absolute


def resolve_stored_path(stored_path: str) -> Path:
    candidate = Path(stored_path)
    if candidate.is_absolute():
        return candidate
    # Stored paths are relative to the repository root (e.g. uploads/x.pdf).
    root_candidate = Path(settings.PROJECT_ROOT) / candidate if hasattr(settings, "PROJECT_ROOT") else candidate
    if root_candidate.exists():
        return root_candidate
    return uploads_dir() / candidate.name
