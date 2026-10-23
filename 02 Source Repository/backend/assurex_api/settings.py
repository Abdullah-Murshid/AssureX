"""
Django settings for the AssureX Claim Engine REST API.

The REST API is a thin HTTP layer over the existing, framework-agnostic
AssureX domain code in ``src/assurex_claim_engine``. It therefore does not use
the Django ORM: the original SQLAlchemy schema and the original SQLite file
(``database/assurex.db``) remain the single source of truth.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
PROJECT_ROOT = BASE_DIR.parent                             # repository root

# The domain package (src/) and the project root (config/, dataset_generator/)
# must be importable exactly like they are for the legacy FastAPI app.
for _path in (str(PROJECT_ROOT / "src"), str(PROJECT_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "assurex-rest-api-dev-secret-change-me-before-production"
)
DEBUG = _env_bool("ASSUREX_DEBUG", True)
ALLOWED_HOSTS = _csv_env("ASSUREX_ALLOWED_HOSTS", "*")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "restapi",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "restapi.middleware.DBSessionMiddleware",
]

ROOT_URLCONF = "assurex_api.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
WSGI_APPLICATION = "assurex_api.wsgi.application"
ASGI_APPLICATION = "assurex_api.asgi.application"

APPEND_SLASH = False

# --------------------------------------------------------------------------- #
# Data (legacy SQLite database, owned by SQLAlchemy)
# --------------------------------------------------------------------------- #
DB_PATH = Path(
    os.environ.get("ASSUREX_DB_PATH", str(PROJECT_ROOT / "database" / "assurex.db"))
).resolve()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DB_PATH),
        "OPTIONS": {"timeout": 30},
    }
}

# Signed-cookie sessions: no extra database tables are created, so the legacy
# SQLite schema is never touched by Django. Used as a convenience fallback for
# the Swagger UI (Bearer tokens stay the primary authentication mechanism).
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# --------------------------------------------------------------------------- #
# Static / uploads / API behaviour
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

UPLOADS_DIR = Path(os.environ.get("ASSUREX_UPLOADS_DIR", str(PROJECT_ROOT / "uploads")))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

API_TOKEN_TTL_SECONDS = int(os.environ.get("ASSUREX_API_TOKEN_TTL_SECONDS", 8 * 60 * 60))
MODEL_READY_TIMEOUT_SECONDS = int(os.environ.get("ASSUREX_MODEL_TIMEOUT_SECONDS", 300))
PRELOAD_MODELS = _env_bool("ASSUREX_API_PRELOAD_MODELS", True)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
