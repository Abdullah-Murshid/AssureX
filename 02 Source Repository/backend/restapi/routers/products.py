from __future__ import annotations

from ninja import Router, Status
from ninja.errors import HttpError

from assurex_claim_engine.db.database import Claim, Document, Product, Repair
from assurex_claim_engine.web.helpers import (
    enrich_product,
    next_product_id,
    paginate,
    scoped_products,
    write_audit,
)

from ..deps import auth, current_principal, db_of, require_roles
from ..schemas import ProductIn
from ..serializers import document_out, pagination_out, product_out, repair_out, warranty_out

router = Router(tags=["Products"], auth=auth)


@router.get("/products")
def list_products(
    request,
    category: str = "",
    serial: str = "",
    warranty_status: str = "",
    page: int = 1,
    per_page: int = 15,
):
    principal = current_principal(request)
    db = db_of(request)

    query = scoped_products(db, _principal_row(db, principal.user_id))
    if category:
        query = query.filter(Product.category == category.strip().lower())
    if serial:
        query = query.filter(Product.serial_number.contains(serial.strip()))

    cards = [enrich_product(p) for p in query.order_by(Product.created_at.desc()).all()]
    if warranty_status:
        cards = [c for c in cards if c["warranty_status"] == warranty_status]

    pagination = paginate(cards, page=page, per_page=per_page)
    return pagination_out(pagination, [warranty_out(c) for c in pagination["items"]])


@router.get("/products/{product_id}")
def get_product(request, product_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _principal_row(db, principal.user_id)

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise HttpError(404, "Product not found.")
    if not _can_access(user, product):
        raise HttpError(403, "You cannot access this product.")

    enriched = enrich_product(product)
    payload = warranty_out(enriched)
    payload.update(
        {
            "documents": [
                document_out(d)
                for d in db.query(Document).filter(Document.product_id == product_id).all()
            ],
            "repairs": [
                repair_out(r)
                for r in db.query(Repair).filter(Repair.product_id == product_id).all()
            ],
            "claims": [
                c.claim_id
                for c in db.query(Claim).filter(Claim.product_id == product_id).all()
            ],
        }
    )
    return payload


@router.post("/products", response={201: dict})
def create_product(request, payload: ProductIn):
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _principal_row(db, principal.user_id)

    extended = bool(
        payload.has_extended_warranty
        or payload.extended_warranty_provider
        or payload.extended_warranty_contract_number
        or payload.extended_warranty_duration_months > 0
    )
    product = Product(
        product_id=next_product_id(db),
        user_id=user.user_id,
        product_name=payload.product_name,
        category=payload.category,
        brand=payload.brand or "Generic",
        model_number=payload.model_number or "N/A",
        serial_number=payload.serial_number,
        purchase_date=payload.purchase_date,
        purchase_price=payload.purchase_price,
        retailer=payload.retailer or "Unknown",
        warranty_duration_months=payload.warranty_duration_months,
        has_extended_warranty=extended,
        extended_warranty_provider=payload.extended_warranty_provider.strip(),
        extended_warranty_contract_number=payload.extended_warranty_contract_number.strip(),
        extended_warranty_duration_months=payload.extended_warranty_duration_months,
    )
    db.add(product)
    write_audit(
        db,
        action="Product Registration",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="product",
        entity_id=product.product_id,
        details={"via": "rest_api"},
    )
    db.commit()
    db.refresh(product)
    return Status(201, {"product": product_out(product), "warranty": warranty_out(enrich_product(product))})


# --------------------------------------------------------------------------- #
# Internal helpers (imported lazily to avoid a circular import on start-up)
# --------------------------------------------------------------------------- #
def _principal_row(db, user_id: str):
    from assurex_claim_engine.db.database import User

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:  # pragma: no cover
        raise HttpError(401, "User no longer exists.")
    return user


def _can_access(user, product: Product) -> bool:
    if user.role in ("admin", "reviewer"):
        return True
    return product.user_id == user.user_id
