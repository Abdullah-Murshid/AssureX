"""Per-request SQLAlchemy session management.

Django's ORM is intentionally unused; the legacy SQLAlchemy models own the
database. A single session is opened per HTTP request and always closed, so the
API behaves like the original FastAPI dependency injection did.
"""

from __future__ import annotations

import threading
from typing import Callable

from assurex_claim_engine.db.database import SessionLocal, init_db

_bootstrap_lock = threading.Lock()
_bootstrapped = False


def ensure_database_initialized() -> None:
    """Create/migrate the SQLite schema and seed demo users once per process.

    The legacy FastAPI app did this in its lifespan hook; doing it lazily on the
    first request keeps Django management commands fast and makes the REST API
    work on a fresh checkout without an extra setup step.
    """
    global _bootstrapped
    if _bootstrapped:
        return
    with _bootstrap_lock:
        if _bootstrapped:
            return
        init_db()
        _bootstrapped = True


class DBSessionMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        ensure_database_initialized()
        request.db = SessionLocal()
        try:
            return self.get_response(request)
        finally:
            try:
                request.db.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
