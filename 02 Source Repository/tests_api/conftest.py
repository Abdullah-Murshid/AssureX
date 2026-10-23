"""Pytest bootstrap for the Django Ninja REST API.

The suite runs against an isolated temporary SQLite database and uploads
directory, so the released ``database/assurex.db`` is never modified.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "backend", ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_TMP_DIR = Path(tempfile.mkdtemp(prefix="assurex_api_tests_"))
os.environ["ASSUREX_DB_PATH"] = str(_TMP_DIR / "assurex_test.db")
os.environ["ASSUREX_UPLOADS_DIR"] = str(_TMP_DIR / "uploads")
os.environ["ASSUREX_API_PRELOAD_MODELS"] = "0"
os.environ["ASSUREX_MODEL_TIMEOUT_SECONDS"] = "300"
os.environ["ASSUREX_DEBUG"] = "1"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "assurex_api.settings")

import django  # noqa: E402

django.setup()

from assurex_claim_engine.db.database import init_db  # noqa: E402
from django.test import Client  # noqa: E402


def pytest_sessionstart(session):  # noqa: ARG001
    init_db()


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


@pytest.fixture()
def client() -> Client:
    return Client()


def _login(client: Client, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    return response.json()["access_token"]


@pytest.fixture()
def customer_headers(client: Client) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {_login(client, 'customer@assurex.com', 'customer123')}"}


@pytest.fixture()
def reviewer_headers(client: Client) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {_login(client, 'reviewer@assurex.com', 'reviewer123')}"}


@pytest.fixture()
def admin_headers(client: Client) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {_login(client, 'admin@assurex.com', 'admin123')}"}


@pytest.fixture(scope="session")
def models_ready():
    from restapi.services.models import registry

    registry.ensure_ready()
    assert registry.ready
    return registry
