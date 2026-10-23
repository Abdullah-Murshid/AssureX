"""Stateless signed access tokens for the REST API.

Tokens are signed with the Django ``SECRET_KEY`` using itsdangerous (already a
project dependency). They are self-contained, expiring, and require no server
side storage, which keeps the legacy database schema untouched.
"""

from __future__ import annotations

from typing import Optional

from django.conf import settings
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = "assurex-rest-api-auth-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt=_SALT)


def issue_token(user_id: str) -> str:
    return _serializer().dumps({"uid": user_id})


def decode_token(token: str) -> Optional[dict]:
    """Return the token payload, or ``None`` when invalid/expired."""
    try:
        payload = _serializer().loads(token, max_age=settings.API_TOKEN_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return payload if isinstance(payload, dict) else None


def token_ttl() -> int:
    return int(settings.API_TOKEN_TTL_SECONDS)
