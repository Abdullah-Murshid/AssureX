"""JSON serialisers for the legacy SQLAlchemy models.

The legacy templates read attributes directly; the REST API exposes the same
information as plain dictionaries with stable snake_case field names.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from assurex_claim_engine.db.database import AuditLog, Claim, Document, Product, Repair, User


def _iso(value) -> Optional[str]:
    return value.isoformat() if value is not None else None


def user_out(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "phone_number": user.phone_number or "",
        "mailing_address": user.mailing_address or "",
        "created_at": _iso(user.created_at),
    }


def product_out(product: Product) -> dict:
    return {
        "product_id": product.product_id,
        "user_id": product.user_id,
        "product_name": product.product_name,
        "category": product.category,
        "brand": product.brand,
        "model_number": product.model_number,
        "serial_number": product.serial_number,
        "purchase_date": product.purchase_date,
        "purchase_price": product.purchase_price,
        "retailer": product.retailer,
        "warranty_duration_months": product.warranty_duration_months,
        "has_extended_warranty": bool(product.has_extended_warranty),
        "extended_warranty_provider": product.extended_warranty_provider or "",
        "extended_warranty_contract_number": product.extended_warranty_contract_number or "",
        "extended_warranty_duration_months": product.extended_warranty_duration_months or 0,
        "created_at": _iso(product.created_at),
    }


def warranty_out(row: dict) -> dict:
    """Serialise the ``enrich_product`` / ``warranty_info`` helper result."""
    product = row["product"]
    return {
        "product": product_out(product),
        "warranty_status": row.get("warranty_status"),
        "remaining_warranty_days": row.get("remaining_warranty_days"),
        "warranty_start_date": row.get("warranty_start_date"),
        "warranty_expiry_date": row.get("warranty_expiry_date"),
        "is_expiring_alert": (row.get("warranty") or {}).get("is_expiring_alert"),
        "coverage_provider": (row.get("warranty") or {}).get("coverage_provider")
        or (row.get("policy") or {}).get("category_name"),
        "policy": row.get("policy"),
    }


def document_out(doc: Document, duplicates: Optional[list] = None) -> dict:
    extracted: dict[str, Any] = {}
    if doc.extracted_data_json:
        try:
            extracted = json.loads(doc.extracted_data_json)
        except (ValueError, TypeError):
            extracted = {}
    return {
        "doc_id": doc.doc_id,
        "claim_id": doc.claim_id,
        "product_id": doc.product_id,
        "user_id": doc.user_id,
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "file_path": doc.file_path,
        "file_hash": doc.file_hash,
        "extracted_data": extracted,
        "verified_at": _iso(doc.verified_at),
        "verified_by": doc.verified_by,
        "created_at": _iso(doc.created_at),
        "duplicate_of": [d.doc_id for d in (duplicates or [])],
        "download_url": f"/api/v1/documents/{doc.doc_id}/download",
    }


def repair_out(repair: Repair) -> dict:
    return {
        "repair_id": repair.repair_id,
        "product_id": repair.product_id,
        "user_id": repair.user_id,
        "repair_date": repair.repair_date,
        "service_center_name": repair.service_center_name,
        "replaced_parts": repair.replaced_parts or "",
        "repair_cost": repair.repair_cost,
        "outcome": repair.outcome or "",
        "authorized": bool(repair.authorized),
        "created_at": _iso(repair.created_at),
    }


def audit_out(log: AuditLog) -> dict:
    details = {}
    if log.details_json:
        try:
            details = json.loads(log.details_json)
        except (ValueError, TypeError):
            details = {"raw": log.details_json}
    return {
        "id": log.id,
        "claim_id": log.claim_id,
        "user_id": log.user_id,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "action": log.action,
        "performed_by": log.performed_by,
        "details": details,
        "timestamp": _iso(log.timestamp),
    }


def claim_out(claim: Claim, product: Optional[Product] = None) -> dict:
    payload = {
        "claim_id": claim.claim_id,
        "user_id": claim.user_id,
        "product_id": claim.product_id,
        "fault_category": claim.fault_category,
        "damage_type": claim.damage_type,
        "fault_occurrence_date": claim.fault_occurrence_date,
        "claim_submission_date": claim.claim_submission_date,
        "description": claim.description,
        "status": claim.status,
        "python_predicted_class": claim.python_predicted_class,
        "python_top_confidence": claim.python_top_confidence,
        "vision_predicted_class": claim.vision_predicted_class,
        "vision_top_confidence": claim.vision_top_confidence,
        "confidence_difference": claim.confidence_difference,
        "consistency_status": claim.consistency_status,
        "final_decision": claim.final_decision,
        "reviewer_comments": claim.reviewer_comments,
        "reviewed_by": claim.reviewed_by,
        "override_flag": bool(claim.override_flag),
        "document_hash": claim.document_hash,
        "model_version": claim.model_version,
        "created_at": _iso(claim.created_at),
        "summary_card_url": f"/api/v1/claims/{claim.claim_id}/summary-card",
        "report_url": f"/api/v1/claims/{claim.claim_id}/report.pdf",
    }
    if product is not None:
        payload["product"] = {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "category": product.category,
            "brand": product.brand,
            "model_number": product.model_number,
            "serial_number": product.serial_number,
        }
    return payload


def claim_dossier(claim: Claim) -> dict:
    if not claim.decision_explanation_json:
        return {}
    try:
        return json.loads(claim.decision_explanation_json)
    except (ValueError, TypeError):
        return {"raw": claim.decision_explanation_json}


def pagination_out(pagination: dict, items: list) -> dict:
    return {
        "items": items,
        "page": pagination["page"],
        "per_page": pagination["per_page"],
        "total": pagination["total"],
        "total_pages": pagination["total_pages"],
        "has_prev": pagination["has_prev"],
        "has_next": pagination["has_next"],
    }


def status_history_out(row) -> dict:
    return {
        "id": row.id,
        "claim_id": row.claim_id,
        "from_status": row.from_status,
        "to_status": row.to_status,
        "actor_user_id": row.actor_user_id,
        "actor_role": row.actor_role,
        "note": row.note,
        "created_at": _iso(row.created_at),
    }


def notification_out(row) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "type": row.type,
        "title": row.title,
        "message": row.message,
        "claim_id": row.claim_id,
        "product_id": row.product_id,
        "is_read": bool(row.is_read),
        "created_at": _iso(row.created_at),
    }
