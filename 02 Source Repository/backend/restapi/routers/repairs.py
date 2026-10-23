from __future__ import annotations

from ninja import Router, Status
from ninja.errors import HttpError

from assurex_claim_engine.db.database import Product, Repair
from assurex_claim_engine.web.helpers import (
    next_repair_id,
    paginate,
    scoped_products,
    scoped_repairs,
    write_audit,
)

from ..deps import auth, current_principal, db_of, require_roles
from ..schemas import RepairIn
from ..serializers import pagination_out, repair_out

router = Router(tags=["Repairs"], auth=auth)


@router.get("/repairs")
def list_repairs(request, product_id: str = "", page: int = 1, per_page: int = 15):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    query = scoped_repairs(db, user)
    if product_id:
        query = query.filter(Repair.product_id == product_id)
    pagination = paginate(query.order_by(Repair.created_at.desc()), page=page, per_page=per_page)
    return pagination_out(pagination, [repair_out(r) for r in pagination["items"]])


@router.post("/repairs", response={201: dict})
def create_repair(request, payload: RepairIn):
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    product = scoped_products(db, user).filter(Product.product_id == payload.product_id).first()
    if product is None:
        raise HttpError(404, "Product not found.")

    repair = Repair(
        repair_id=next_repair_id(db),
        product_id=product.product_id,
        user_id=user.user_id,
        repair_date=payload.repair_date,
        service_center_name=payload.service_center_name,
        replaced_parts=payload.replaced_parts,
        repair_cost=payload.repair_cost,
        outcome=payload.outcome,
        authorized=payload.authorized,
    )
    db.add(repair)
    write_audit(
        db,
        action="Repair Logged",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="repair",
        entity_id=repair.repair_id,
        details={"via": "rest_api"},
    )
    db.commit()
    db.refresh(repair)
    return Status(201, repair_out(repair))


def _user(db, user_id: str):
    from assurex_claim_engine.db.database import User

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:  # pragma: no cover
        raise HttpError(401, "User no longer exists.")
    return user
