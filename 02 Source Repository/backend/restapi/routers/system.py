from __future__ import annotations

from django.conf import settings
from ninja import Router

from assurex_claim_engine.db.database import Claim, Document, Product, User
from config.settings_loader import get_settings

from ..deps import auth, current_principal, db_of
from ..services.models import registry

router = Router(tags=["System"])


@router.get("/health", auth=None)
def health(request):
    status = registry.status()
    return {
        "status": "ok" if status["models_ready"] else "loading",
        "service": "assurex-claim-engine-rest-api",
        "version": "2.0.0",
        **status,
    }


@router.get("/system/models", auth=auth)
def model_status(request):
    return registry.status()


@router.get("/system/info", auth=auth)
def system_info(request):
    principal = current_principal(request)
    db = db_of(request)
    return {
        "service": "assurex-claim-engine-rest-api",
        "version": "2.0.0",
        "database": str(settings.DB_PATH),
        "uploads": str(settings.UPLOADS_DIR),
        "models": registry.status(),
        "settings": get_settings(),
        "request": {
            "user_id": principal.user_id,
            "role": principal.role,
        },
        "counts": {
            "users": db.query(User).count(),
            "products": db.query(Product).count(),
            "claims": db.query(Claim).count(),
            "documents": db.query(Document).count(),
        },
    }
