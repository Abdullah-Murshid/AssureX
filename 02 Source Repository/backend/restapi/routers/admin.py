from __future__ import annotations

import csv
import io
import json
import os
from collections import Counter

from django.http import HttpResponse
from ninja import Router
from ninja.errors import HttpError

from assurex_claim_engine.db.database import AuditLog, Claim, Document, Product
from assurex_claim_engine.web.helpers import (
    monitoring_flags,
    paginate,
    policy_file_map,
    validate_policy_payload,
    write_audit,
)
from config.settings_loader import get_settings, update_settings

from ..deps import auth, current_principal, db_of, require_roles
from ..schemas import PolicyUpdateIn, SettingsUpdateIn
from ..serializers import audit_out, pagination_out

router = Router(tags=["Administration"], auth=auth)


# --------------------------------------------------------------------------- #
# Policies
# --------------------------------------------------------------------------- #
def _read_policy(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (ValueError, OSError):
        return {}


@router.get("/admin/policies")
def list_policies(request):
    require_roles("admin")(request)
    mapping = policy_file_map()
    return {
        "categories": list(mapping.keys()),
        "policies": {category: _read_policy(path) for category, path in mapping.items()},
    }


@router.get("/admin/policies/{category}")
def get_policy(request, category: str):
    require_roles("admin")(request)
    mapping = policy_file_map()
    if category not in mapping:
        raise HttpError(404, f"Unknown policy category '{category}'.")
    return {"category": category, "policy": _read_policy(mapping[category])}


@router.put("/admin/policies/{category}")
def update_policy(request, category: str, payload: PolicyUpdateIn):
    principal = require_roles("admin")(request)
    db = db_of(request)

    mapping = policy_file_map()
    if category not in mapping:
        raise HttpError(404, f"Unknown policy category '{category}'.")

    data = dict(payload.data or {})
    data.setdefault("product_category", category)

    error = validate_policy_payload(data)
    if error:
        raise HttpError(400, error)

    path = mapping[category]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")

    # Refresh the in-memory policy cache used by the fusion engine.
    from ..services.models import registry

    try:
        evaluator = registry.fusion.rule_evaluator  # type: ignore[union-attr]
        evaluator.policies = evaluator._load_policies()
    except Exception:  # pragma: no cover - best effort cache refresh
        pass

    write_audit(
        db,
        action="Policy Updated",
        performed_by=principal.user_id,
        user_id=principal.user_id,
        entity_type="policy",
        entity_id=category,
        details={"category": category, "name": data.get("category_name", category), "via": "rest_api"},
    )
    db.commit()
    return {"category": category, "policy": data}


# --------------------------------------------------------------------------- #
# Analytics / monitoring
# --------------------------------------------------------------------------- #
@router.get("/admin/analytics")
def analytics(request):
    require_roles("admin")(request)
    db = db_of(request)

    total = db.query(Claim).count()
    valid = db.query(Claim).filter(Claim.final_decision == "Likely Valid").count()
    invalid = db.query(Claim).filter(Claim.final_decision == "Likely Invalid").count()
    review = db.query(Claim).filter(Claim.final_decision == "Manual Review Required").count()
    disagreements = db.query(Claim).filter(Claim.consistency_status == "Model Disagreement").count()

    status_counts = Counter(c.status or "Unknown" for c in db.query(Claim).all())
    category_counts: Counter = Counter()
    for product in db.query(Product).all():
        category_counts[product.category or "unknown"] += 1

    month_counts: Counter = Counter()
    for claim in db.query(Claim).all():
        key = (claim.claim_submission_date or "")[:7] or "unknown"
        month_counts[key] += 1

    return {
        "totals": {
            "claims": total,
            "likely_valid": valid,
            "likely_invalid": invalid,
            "manual_review": review,
            "model_disagreements": disagreements,
            "products": db.query(Product).count(),
            "documents": db.query(Document).count(),
            "audit_events": db.query(AuditLog).count(),
        },
        "decision_distribution": {
            "likely_valid": valid,
            "likely_invalid": invalid,
            "manual_review": review,
        },
        "status_distribution": dict(status_counts),
        "category_distribution": dict(category_counts),
        "monthly_claims": dict(sorted(month_counts.items())),
        "monitoring": monitoring_flags(db),
    }


@router.get("/admin/monitoring")
def monitoring(request):
    require_roles("admin", "reviewer")(request)
    return monitoring_flags(db_of(request))


@router.get("/admin/audit-logs")
def audit_logs(
    request,
    action: str = "",
    user_id: str = "",
    claim_id: str = "",
    page: int = 1,
    per_page: int = 20,
):
    require_roles("reviewer", "admin")(request)
    db = db_of(request)

    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.contains(action))
    if user_id:
        query = query.filter(
            (AuditLog.performed_by == user_id) | (AuditLog.user_id == user_id)
        )
    if claim_id:
        query = query.filter(AuditLog.claim_id.contains(claim_id))

    pagination = paginate(
        query.order_by(AuditLog.timestamp.desc()), page=page, per_page=per_page
    )
    return pagination_out(pagination, [audit_out(log) for log in pagination["items"]])


# --------------------------------------------------------------------------- #
# CSV export
# --------------------------------------------------------------------------- #
@router.get("/admin/export/claims.csv")
def export_claims_csv(request):
    principal = require_roles("admin")(request)
    db = db_of(request)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "claim_id",
            "product_id",
            "user_id",
            "status",
            "final_decision",
            "python_predicted_class",
            "vision_predicted_class",
            "consistency_status",
            "model_version",
            "serial_number",
            "category",
            "claim_submission_date",
        ]
    )
    for claim in db.query(Claim).order_by(Claim.created_at.desc()).all():
        product = db.query(Product).filter(Product.product_id == claim.product_id).first()
        writer.writerow(
            [
                claim.claim_id,
                claim.product_id,
                claim.user_id,
                claim.status,
                claim.final_decision,
                claim.python_predicted_class,
                claim.vision_predicted_class,
                claim.consistency_status,
                claim.model_version,
                product.serial_number if product else "",
                product.category if product else "",
                claim.claim_submission_date,
            ]
        )

    write_audit(
        db,
        action="Data Export",
        performed_by=principal.user_id,
        entity_type="export",
        entity_id="claims-csv",
        details={"via": "rest_api"},
    )
    db.commit()

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="assurex_claims_export.csv"'
    return response


# --------------------------------------------------------------------------- #
# Runtime settings
# --------------------------------------------------------------------------- #
@router.get("/admin/settings")
def get_runtime_settings(request):
    require_roles("admin")(request)
    return {"settings": get_settings()}


@router.put("/admin/settings")
def update_runtime_settings(request, payload: SettingsUpdateIn):
    principal = require_roles("admin")(request)
    db = db_of(request)

    editable = {
        "model_version",
        "uncertainty_threshold",
        "strong_match_threshold",
        "acceptable_match_threshold",
        "pdf_render_dpi",
        "model_ready_timeout_seconds",
        "warranty_alert_days",
        "disagreement_alert_rate",
        "manual_review_spike_rate",
    }
    updates = {k: v for k, v in (payload.settings or {}).items() if k in editable}
    if not updates:
        raise HttpError(400, f"No editable settings supplied. Allowed: {sorted(editable)}")

    if not update_settings(updates):
        raise HttpError(500, "Could not persist settings.")

    write_audit(
        db,
        action="Settings Updated",
        performed_by=principal.user_id,
        user_id=principal.user_id,
        entity_type="settings",
        entity_id="config",
        details={"updates": updates, "via": "rest_api"},
    )
    db.commit()
    return {"settings": get_settings()}
