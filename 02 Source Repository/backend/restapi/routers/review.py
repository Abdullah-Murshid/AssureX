from __future__ import annotations

import json

from ninja import Router
from ninja.errors import HttpError

from assurex_claim_engine.db.database import AuditLog, Claim, Product
from assurex_claim_engine.db.status_history import record_status_transition
from assurex_claim_engine import notifications as notification_service
from assurex_claim_engine.web.helpers import paginate

from ..deps import auth, current_principal, db_of, require_roles
from ..schemas import ReviewDecisionIn
from ..serializers import claim_out, pagination_out

router = Router(tags=["Reviewer Queue"], auth=auth)


@router.get("/review/queue")
def review_queue(request, page: int = 1, per_page: int = 15):
    principal = current_principal(request)
    db = db_of(request)
    require_roles("reviewer")(request)  # admin is implicitly allowed

    query = (
        db.query(Claim)
        .filter(Claim.status.in_(["Manual Review", "Request More Info"]))
        .order_by(Claim.created_at.desc())
    )
    pagination = paginate(query, page=page, per_page=per_page)
    items = []
    for claim in pagination["items"]:
        product = db.query(Product).filter(Product.product_id == claim.product_id).first()
        items.append(claim_out(claim, product))
    return pagination_out(pagination, items)


@router.get("/review/stats")
def review_stats(request):
    require_roles("reviewer")(request)
    db = db_of(request)
    return {
        "manual_review": db.query(Claim).filter(Claim.status == "Manual Review").count(),
        "request_more_info": db.query(Claim)
        .filter(Claim.status == "Request More Info")
        .count(),
        "overrides": db.query(Claim).filter(Claim.override_flag.is_(True)).count(),
        "total_claims": db.query(Claim).count(),
    }


@router.post("/review/{claim_id}/decision")
def review_decision(request, claim_id: str, payload: ReviewDecisionIn):
    principal = require_roles("reviewer", "admin")(request)
    db = db_of(request)

    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if claim is None:
        raise HttpError(404, "Claim not found.")

    original_decision = claim.final_decision
    record_status_transition(
        db,
        claim,
        payload.action,
        actor_user_id=principal.user_id,
        actor_role=principal.role,
        note=payload.comments.strip(),
    )
    claim.reviewer_comments = payload.comments.strip()
    claim.reviewed_by = f"{principal.full_name} ({principal.role.capitalize()})"
    claim.override_flag = True

    db.add(
        AuditLog(
            claim_id=claim_id,
            user_id=principal.user_id,
            entity_type="claim",
            entity_id=claim_id,
            action=f"Reviewer Override -> {payload.action}",
            performed_by=principal.user_id,
            details_json=json.dumps(
                {
                    "comments": payload.comments,
                    "original_decision": original_decision,
                    "new_status": payload.action,
                    "via": "rest_api",
                }
            ),
        )
    )
    db.commit()
    try:
        notification_service.after_review_action(claim, payload.action, payload.comments.strip())
    except Exception as exc:  # notifications must never break a review
        print(f"[notifications] review {claim_id} notification failed: {exc}", flush=True)
    db.refresh(claim)

    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    return claim_out(claim, product)
