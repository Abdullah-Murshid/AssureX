"""NinjaAPI instance and router registration for the AssureX REST API."""

from __future__ import annotations

from ninja import NinjaAPI

from .routers import (
    admin,
    auth,
    claims,
    documents,
    notifications,
    products,
    repairs,
    review,
    system,
    warranties,
)

api = NinjaAPI(
    title="AssureX Claim Engine API",
    version="2.0.0",
    description=(
        "REST API for the AssureX warranty claim engine. It exposes the same "
        "authentication, product, evidence, adjudication, reviewer and "
        "administration capabilities as the original server-rendered "
        "application, backed by the same SQLAlchemy database and ML models.\n\n"
        "Authenticate with `POST /api/v1/auth/login` and send the returned token "
        "as `Authorization: Bearer <token>`."
    ),
    urls_namespace="assurex_api",
)

api.add_router("/v1/auth", auth.router)
api.add_router("/v1", products.router)
api.add_router("/v1", warranties.router)
api.add_router("/v1", documents.router)
api.add_router("/v1", notifications.router)
api.add_router("/v1", repairs.router)
api.add_router("/v1", claims.router)
api.add_router("/v1", review.router)
api.add_router("/v1", admin.router)
api.add_router("/v1", system.router)


@api.get("/", auth=None, tags=["System"])
def api_root(request):
    return {
        "service": "assurex-claim-engine-rest-api",
        "version": "2.0.0",
        "docs": "/api/docs",
        "openapi": "/api/openapi.json",
        "health": "/api/v1/health",
        "authentication": "POST /api/v1/auth/login -> Authorization: Bearer <token>",
    }
