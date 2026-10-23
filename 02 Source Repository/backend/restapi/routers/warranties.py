from __future__ import annotations

from ninja import Router
from ninja.errors import HttpError

from assurex_claim_engine.db.database import Product
from assurex_claim_engine.web.helpers import (
    enrich_product,
    paginate,
    scoped_products,
    warranty_alert_summary,
    write_audit,
)

from ..deps import auth, current_principal, db_of
from ..serializers import pagination_out, warranty_out

router = Router(tags=["Warranties & Alerts"], auth=auth)


@router.get("/warranties")
def list_warranties(request, page: int = 1, per_page: int = 15):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    cards = [
        enrich_product(p)
        for p in scoped_products(db, user).order_by(Product.created_at.desc()).all()
    ]
    pagination = paginate(cards, page=page, per_page=per_page)
    return pagination_out(pagination, [warranty_out(c) for c in pagination["items"]])


@router.get("/warranties/{product_id}")
def warranty_detail(request, product_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise HttpError(404, "Product not found.")
    if user.role not in ("admin", "reviewer") and product.user_id != user.user_id:
        raise HttpError(403, "You cannot access this product.")
    return warranty_out(enrich_product(product))


@router.get("/alerts")
def list_alerts(request, tab: str = "expiring", page: int = 1, per_page: int = 15):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    summary = warranty_alert_summary(db, user)
    tab = (tab or "expiring").lower()
    if tab == "expired":
        selected = summary["expired"]
    elif tab == "grace":
        selected = summary["grace"]
    elif tab == "all":
        selected = summary["expiring"] + summary["grace"] + summary["expired"]
    else:
        tab = "expiring"
        selected = summary["expiring"]

    pagination = paginate(selected, page=page, per_page=per_page)
    return {
        "tab": tab,
        "summary": {
            "expiring_count": summary["expiring_count"],
            "grace_count": summary["grace_count"],
            "expired_count": summary["expired_count"],
            "total_all": summary["total_all"],
        },
        "alerts": [warranty_out(item) for item in pagination["items"]],
        "pagination": {
            "page": pagination["page"],
            "per_page": pagination["per_page"],
            "total": pagination["total"],
            "total_pages": pagination["total_pages"],
        },
    }


@router.post("/alerts/{product_id}/dismiss")
def dismiss_alert(request, product_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    write_audit(
        db,
        action="Alert Dismissed",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="product",
        entity_id=product_id,
        details={"dismissed_by": user.email, "via": "rest_api"},
    )
    db.commit()
    return {"detail": f"Alert for product {product_id} dismissed."}


def _user(db, user_id: str):
    from assurex_claim_engine.db.database import User

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:  # pragma: no cover
        raise HttpError(401, "User no longer exists.")
    return user
