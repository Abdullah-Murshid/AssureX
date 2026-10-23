from __future__ import annotations

from datetime import datetime, timezone

from ninja import Router, Status
from ninja.errors import HttpError

from assurex_claim_engine.db.database import User, hash_password, verify_password
from assurex_claim_engine.web.helpers import write_audit

from ..deps import auth, current_principal, db_of
from ..schemas import AuthOut, ChangePasswordIn, LoginIn, ProfileUpdateIn, RegisterIn
from ..serializers import user_out
from ..services.tokens import issue_token, token_ttl

router = Router(tags=["Authentication"], auth=auth)


def _start_session(request, user: User) -> None:
    request.session["user_id"] = user.user_id
    request.session["email"] = user.email
    request.session["role"] = user.role
    request.session["full_name"] = user.full_name


def _auth_payload(user: User) -> dict:
    return {
        "access_token": issue_token(user.user_id),
        "token_type": "Bearer",
        "expires_in": token_ttl(),
        "user": user_out(user),
    }


@router.post("/register", response={201: AuthOut}, auth=None)
def register(request, payload: RegisterIn):
    """Self-registration. Only customer / service_center roles are accepted."""
    db = db_of(request)
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HttpError(400, f"Email address '{payload.email}' is already registered.")

    count = db.query(User).count() + 1
    user_id = f"USR-{count:04d}"
    user = User(
        user_id=user_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
    )
    db.add(user)
    write_audit(
        db,
        action="Account Created",
        performed_by=user_id,
        user_id=user_id,
        entity_type="user",
        entity_id=user_id,
        details={"email": payload.email, "role": payload.role, "via": "rest_api"},
    )
    db.commit()
    _start_session(request, user)
    return Status(201, _auth_payload(user))


@router.post("/login", response=AuthOut, auth=None)
def login(request, payload: LoginIn):
    """Exchange credentials for a signed bearer token (and a same-origin session)."""
    db = db_of(request)
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HttpError(401, "Invalid email or password.")

    _start_session(request, user)
    write_audit(
        db,
        action="Login",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="user",
        entity_id=user.user_id,
        details={"via": "rest_api"},
    )
    db.commit()
    return _auth_payload(user)


@router.post("/logout")
def logout(request):
    """Clear the same-origin session. Bearer tokens are stateless: discard them client-side."""
    request.session.flush()
    return {"detail": "Logged out."}


@router.get("/me")
def me(request):
    principal = current_principal(request)
    db = db_of(request)
    user = db.query(User).filter(User.user_id == principal.user_id).first()
    if user is None:  # pragma: no cover - token for deleted account
        raise HttpError(401, "User no longer exists.")

    from assurex_claim_engine.web.helpers import scoped_claims, scoped_products

    return {
        "user": user_out(user),
        "stats": {
            "products": scoped_products(db, user).count(),
            "claims": scoped_claims(db, user).count(),
        },
    }


@router.patch("/me")
def update_profile(request, payload: ProfileUpdateIn):
    principal = current_principal(request)
    db = db_of(request)
    user = db.query(User).filter(User.user_id == principal.user_id).first()
    if user is None:  # pragma: no cover
        raise HttpError(401, "User no longer exists.")

    taken = (
        db.query(User)
        .filter(User.email == payload.email, User.user_id != user.user_id)
        .first()
    )
    if taken:
        raise HttpError(400, "That email is already in use.")

    user.full_name = payload.full_name.strip()
    user.email = payload.email
    user.phone_number = payload.phone_number.strip()
    user.mailing_address = payload.mailing_address.strip()
    request.session["full_name"] = user.full_name
    request.session["email"] = user.email
    write_audit(
        db,
        action="Profile Updated",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="user",
        entity_id=user.user_id,
        details={"via": "rest_api"},
    )
    db.commit()
    return {"user": user_out(user)}


@router.post("/change-password")
def change_password(request, payload: ChangePasswordIn):
    principal = current_principal(request)
    db = db_of(request)
    user = db.query(User).filter(User.user_id == principal.user_id).first()
    if user is None:  # pragma: no cover
        raise HttpError(401, "User no longer exists.")
    if not verify_password(payload.current_password, user.hashed_password):
        raise HttpError(400, "Current password is incorrect.")

    user.hashed_password = hash_password(payload.new_password)
    write_audit(
        db,
        action="Password Changed",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="user",
        entity_id=user.user_id,
        details={"via": "rest_api"},
    )
    db.commit()
    return {"detail": "Password changed.", "changed_at": datetime.now(timezone.utc).isoformat()}
