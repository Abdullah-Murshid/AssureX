"""Shared web helpers: IDs, audit, warranties, files, RBAC-scoped queries."""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from assurex_claim_engine.db.database import (
    AuditLog,
    Claim,
    Document,
    Product,
    Repair,
    User,
)
from assurex_claim_engine.decision.derived_features import compute_warranty_status
from assurex_claim_engine.rule_engine.evaluator import PolicyRuleEvaluator
from config.settings_loader import get as settings_get

ALLOWED_DOC_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_DOC_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/pjpeg",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
POLICY_DIR = "policies"
POLICY_REQUIRED_KEYS = (
    "product_category",
    "coverage_duration_months",
    "grace_period_days",
    "reporting_deadline_days",
    "covered_faults",
    "exclusions",
    "mandatory_documents",
)

CLAIM_STATUS_STEPS = [
    "Draft",
    "Submitted",
    "Under Evaluation",
    "Manual Review",
    "Approved",
    "Rejected",
    "Request More Info",
    "Closed",
]


def next_prefixed_id(db: Session, model, field: str, prefix: str, width: int) -> str:
    values = [row[0] for row in db.query(getattr(model, field)).all() if row[0]]
    max_n = 0
    for val in values:
        tail = str(val).split("-")[-1]
        if tail.isdigit():
            max_n = max(max_n, int(tail))
    return f"{prefix}{max_n + 1:0{width}d}"


def next_claim_id(db: Session, year: int = 2026) -> str:
    prefix = f"CLM-{year}-"
    max_n = 0
    for (val,) in db.query(Claim.claim_id).all():
        if val and val.startswith(prefix):
            tail = val.split("-")[-1]
            if tail.isdigit():
                max_n = max(max_n, int(tail))
    next_num = max_n + 1
    while db.query(Claim).filter(Claim.claim_id == f"{prefix}{next_num:04d}").first():
        next_num += 1
    return f"{prefix}{next_num:04d}"


def write_audit(
    db: Session,
    action: str,
    performed_by: str,
    *,
    claim_id: Optional[str] = None,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    db.add(AuditLog(
        action=action,
        performed_by=performed_by,
        claim_id=claim_id,
        user_id=user_id or performed_by,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=json.dumps(details or {}),
    ))


def scoped_products(db: Session, user: User):
    q = db.query(Product)
    if user.role in ("customer", "service_center"):
        q = q.filter(Product.user_id == user.user_id)
    return q


def scoped_documents(db: Session, user: User):
    q = db.query(Document)
    if user.role in ("customer", "service_center"):
        q = q.filter(Document.user_id == user.user_id)
    return q


def scoped_repairs(db: Session, user: User):
    q = db.query(Repair)
    if user.role in ("customer", "service_center"):
        q = q.filter(Repair.user_id == user.user_id)
    return q


def scoped_claims(db: Session, user: User):
    q = db.query(Claim)
    if user.role == "customer":
        q = q.filter(Claim.user_id == user.user_id)
    return q


def can_access_product(user: User, product: Product) -> bool:
    if user.role in ("admin", "reviewer"):
        return True
    return product.user_id == user.user_id


def load_policy(category: str) -> dict:
    evaluator = PolicyRuleEvaluator()
    cat = (category or "electronics").lower()
    return evaluator.policies.get(cat, evaluator.policies.get("electronics", {}))


def warranty_info(product: Product, alert_days: Optional[int] = None) -> dict:
    policy = load_policy(product.category)
    if alert_days is None and policy.get("warranty_alert_days"):
        try:
            alert_days = int(policy["warranty_alert_days"])
        except (ValueError, TypeError):
            alert_days = None
    alert_days = alert_days if alert_days is not None else int(settings_get("warranty_alert_days", 30))
    grace = int(policy.get("grace_period_days", 15))
    info = compute_warranty_status(
        {
            "product_category": product.category,
            "purchase_date": product.purchase_date,
            "warranty_duration_months": product.warranty_duration_months,
        },
        alert_days=alert_days,
        grace_period_days=grace,
    )
    info["coverage_provider"] = policy.get("category_name", "Manufacturer Warranty")
    info["exclusions"] = policy.get("exclusions", [])
    info["authorized_service_required"] = policy.get("authorized_service_center_required", True)
    info["mandatory_documents"] = policy.get("mandatory_documents", [])
    info["reporting_deadline_days"] = policy.get("reporting_deadline_days", 30)
    info["product"] = product
    return info


def list_warranty_alerts(db: Session, user: User) -> List[dict]:
    alerts = []
    for product in scoped_products(db, user).all():
        info = warranty_info(product)
        if info.get("is_expiring_alert") or info.get("warranty_status") == "Expiring Soon":
            alerts.append(info)
    return alerts


def validate_upload(filename: str, content_type: Optional[str], size: int) -> Optional[str]:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        return "Invalid file format. Allowed: PDF, JPG, JPEG, PNG."
    if content_type and content_type.split(";")[0].strip().lower() not in ALLOWED_DOC_MIMES and ext not in ALLOWED_DOC_EXTENSIONS:
        return "Invalid file MIME type."
    if size > MAX_UPLOAD_BYTES:
        return "File exceeds the 10MB size limit."
    if size <= 0:
        return "Uploaded file is empty."
    return None


def find_hash_duplicates(db: Session, file_hash: str, exclude_doc_id: Optional[str] = None) -> List[Document]:
    q = db.query(Document).filter(Document.file_hash == file_hash)
    if exclude_doc_id:
        q = q.filter(Document.doc_id != exclude_doc_id)
    return q.all()


def product_repair_summary(db: Session, product_id: str) -> Tuple[int, bool]:
    repairs = db.query(Repair).filter(Repair.product_id == product_id).all()
    unauthorized = any(not r.authorized for r in repairs)
    return len(repairs), unauthorized


def attach_flags_from_docs(docs: List[Document]) -> Dict[str, bool]:
    types = {d.file_type for d in docs}
    return {
        "has_receipt": "receipt" in types or "purchase_receipt" in types,
        "has_warranty_card": "warranty_card" in types,
        "has_product_photo": "product_photo" in types or "product_image" in types,
        "has_serial_photo": "serial_photo" in types or "serial_number_photo" in types,
    }


def policy_file_map() -> Dict[str, str]:
    return {
        "electronics": os.path.join(POLICY_DIR, "electronics_policy.json"),
        "appliances": os.path.join(POLICY_DIR, "appliances_policy.json"),
        "automotive": os.path.join(POLICY_DIR, "automotive_policy.json"),
    }


def validate_policy_payload(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return "Policy must be a JSON object."
    missing = [k for k in POLICY_REQUIRED_KEYS if k not in data]
    if missing:
        return f"Missing required keys: {', '.join(missing)}"
    return None


def monitoring_snapshot(db: Session) -> dict:
    total = db.query(Claim).count()
    disagreements = db.query(Claim).filter(Claim.consistency_status == "Model Disagreement").count()
    reviews = db.query(Claim).filter(Claim.final_decision == "Manual Review Required").count()
    hashes = [h[0] for h in db.query(Document.file_hash).all() if h[0]]
    dup_hashes = len(hashes) - len(set(hashes))
    disagreement_rate = (disagreements / total) if total else 0.0
    review_rate = (reviews / total) if total else 0.0
    flags = []
    if total and disagreement_rate > 0.20:
        flags.append(f"High model disagreement rate ({disagreement_rate:.0%}).")
    if dup_hashes > 0:
        flags.append(f"{dup_hashes} duplicate document hash collision(s) detected.")
    if total >= 5 and review_rate > 0.50:
        flags.append(f"Elevated manual review share ({review_rate:.0%}).")
    return {
        "total": total,
        "disagreements": disagreements,
        "disagreement_rate": disagreement_rate,
        "reviews": reviews,
        "review_rate": review_rate,
        "duplicate_hash_count": dup_hashes,
        "flags": flags,
    }


def apply_claim_filters(q, params: dict):
    claim_id = (params.get("claim_id") or "").strip()
    product_id = (params.get("product_id") or "").strip()
    serial = (params.get("serial") or "").strip()
    category = (params.get("category") or "").strip()
    status = (params.get("status") or "").strip()
    date_from = (params.get("date_from") or "").strip()
    date_to = (params.get("date_to") or "").strip()
    if claim_id:
        q = q.filter(Claim.claim_id.contains(claim_id))
    if product_id:
        q = q.filter(Claim.product_id.contains(product_id))
    if status:
        q = q.filter(Claim.status == status)
    if date_from:
        q = q.filter(Claim.claim_submission_date >= date_from)
    if date_to:
        q = q.filter(Claim.claim_submission_date <= date_to)
    if serial or category:
        q = q.join(Product, Product.product_id == Claim.product_id)
        if serial:
            q = q.filter(Product.serial_number.contains(serial))
        if category:
            q = q.filter(Product.category == category)
    return q


def status_step_index(status: Optional[str]) -> int:
    if not status:
        return 0
    try:
        return CLAIM_STATUS_STEPS.index(status)
    except ValueError:
        return 0


SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    base = os.path.basename(name or "upload.bin")
    return SAFE_FILENAME.sub("_", base)[:120]
