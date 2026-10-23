"""Authentication, authorisation and request-scoped helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ninja.errors import AuthenticationError, HttpError
from ninja.security import HttpBearer
from sqlalchemy.orm import Session

from assurex_claim_engine.db.database import SessionLocal, User

from .services.tokens import decode_token


@dataclass(frozen=True)
class Principal:
    """Authenticated caller, detached from the SQLAlchemy session."""

    user_id: str
    email: str
    role: str
    full_name: str


class SessionOrBearerAuth(HttpBearer):
    """Bearer token authentication with a same-origin session fallback.

    ``Authorization: Bearer <token>`` is the canonical mechanism. When the
    header is absent, a Django signed-cookie session is accepted so the
    browsable Swagger UI (``/api/docs``) can be used after calling
    ``POST /api/v1/auth/login`` from the same origin.
    """

    def __call__(self, request):
        principal = self.authenticate(request, self._extract_token(request))
        if principal is None:
            raise AuthenticationError(401, "Authentication required")
        return principal

    def _extract_token(self, request) -> Optional[str]:
        header = request.headers.get(self.header)
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != self.openapi_scheme:
            raise AuthenticationError(401, "Invalid Authorization header")
        return parts[1]

    def authenticate(self, request, token):  # type: ignore[override]
        if token:
            payload = decode_token(token)
            if not payload or not payload.get("uid"):
                raise AuthenticationError(401, "Invalid or expired token")
            user_id = payload["uid"]
        else:
            session = getattr(request, "session", None)
            user_id = session.get("user_id") if session is not None else None

        if not user_id:
            return None

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user is None:
                return None
            return Principal(
                user_id=user.user_id,
                email=user.email,
                role=user.role,
                full_name=user.full_name,
            )
        finally:
            db.close()


auth = SessionOrBearerAuth()


def current_principal(request) -> Principal:
    principal = getattr(request, "auth", None)
    if not isinstance(principal, Principal):
        raise HttpError(401, "Authentication required")
    return principal


def require_roles(*roles: str):
    """Dependency factory enforcing the legacy RBAC matrix (admin bypass)."""

    def dependency(request) -> Principal:
        principal = current_principal(request)
        if principal.role not in roles and principal.role != "admin":
            raise HttpError(
                403,
                f"Role '{principal.role}' is not authorized to access this resource.",
            )
        return principal

    return dependency


def db_of(request) -> Session:
    session = getattr(request, "db", None)
    if session is None:  # pragma: no cover - misconfiguration guard
        raise RuntimeError(
            "Database session missing. Ensure restapi.middleware.DBSessionMiddleware is installed."
        )
    return session


def user_row(db: Session, principal: Principal) -> User:
    user = db.query(User).filter(User.user_id == principal.user_id).first()
    if user is None:  # pragma: no cover - token for deleted user
        raise HttpError(401, "User no longer exists")
    return user
