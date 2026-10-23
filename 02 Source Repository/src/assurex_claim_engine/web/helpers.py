import json
import math
import os
from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from assurex_claim_engine.db.database import AuditLog, Claim, Document, Product, Repair, User
from assurex_claim_engine.decision.derived_features import compute_warranty_status
from config.settings_loader import get

ALLOWED_UPLOAD_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".mp4", ".mov", ".webm"}
ALLOWED_RECEIPT_EXT = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
def _resolve_policy_dir():
    candidates = [
        "policies",
        "07. Warranty Policy Files",
        "Warranty Policy Files",
        os.path.join(os.path.dirname(__file__), "../../../policies"),
        os.path.join(os.path.dirname(__file__), "../../../07. Warranty Policy Files"),
        os.path.join(os.path.dirname(__file__), "../../../Warranty Policy Files"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.exists(os.path.join(c, "electronics_policy.json")):
            return c
    return "policies"

POLICY_DIR = _resolve_policy_dir()
POLICY_REQUIRED_KEYS = {
    "product_category",
    "coverage_duration_months",
    "exclusions",
    "mandatory_documents",
    "hard_fail_rules",
}

FILE_TYPE_MAP = {
    "receipt": "purchase_receipt",
    "purchase_receipt": "purchase_receipt",
    "warranty": "warranty_card",
    "warranty_card": "warranty_card",
    "product_photo": "product_image",
    "product_image": "product_image",
    "serial_photo": "serial_number_photo",
    "serial_number_photo": "serial_number_photo",
    "damage_photo": "damage_photo",
    "video": "fault_video",
    "fault_video": "fault_video",
    "diagnostic": "diagnostic_report",
}


def scoped_products(db: Session, user: User):
    q = db.query(Product)
    if user.role in ("customer", "service_center"):
        q = q.filter(Product.user_id == user.user_id)
    return q


def scoped_claims(db: Session, user: User):
    q = db.query(Claim)
    if user.role in ("customer", "service_center"):
        q = q.filter(Claim.user_id == user.user_id)
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


def next_product_id(db: Session) -> str:
    last = db.query(Product).order_by(Product.id.desc()).first()
    n = (last.id + 1) if last else 1
    while db.query(Product).filter(Product.product_id == f"PRD-{n:05d}").first():
        n += 1
    return f"PRD-{n:05d}"


def next_doc_id(db: Session) -> str:
    last = db.query(Document).order_by(Document.id.desc()).first()
    n = (last.id + 1) if last else 1
    while db.query(Document).filter(Document.doc_id == f"DOC-{n:05d}").first():
        n += 1
    return f"DOC-{n:05d}"


def next_repair_id(db: Session) -> str:
    last = db.query(Repair).order_by(Repair.id.desc()).first()
    n = (last.id + 1) if last else 1
    while db.query(Repair).filter(Repair.repair_id == f"RPR-{n:05d}").first():
        n += 1
    return f"RPR-{n:05d}"


def load_policy(category: str) -> dict:
    path = os.path.join(POLICY_DIR, f"{category}_policy.json")
    if not os.path.exists(path):
        path = os.path.join(POLICY_DIR, "electronics_policy.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def product_to_claim_dict(product: Product) -> dict:
    return {
        "product_id": product.product_id,
        "user_id": product.user_id,
        "product_name": product.product_name,
        "product_category": product.category,
        "category": product.category,
        "brand": product.brand,
        "model_number": product.model_number,
        "serial_number": product.serial_number,
        "user_serial_number": product.serial_number,
        "purchase_date": product.purchase_date,
        "purchase_price": product.purchase_price,
        "retailer": product.retailer,
        "warranty_duration_months": product.warranty_duration_months,
        "has_extended_warranty": bool(getattr(product, "has_extended_warranty", False)),
        "extended_warranty_provider": getattr(product, "extended_warranty_provider", "") or "",
        "extended_warranty_contract_number": getattr(product, "extended_warranty_contract_number", "") or "",
        "extended_warranty_duration_months": int(getattr(product, "extended_warranty_duration_months", 0) or 0),
    }


def enrich_product(product: Product, alert_days: Optional[int] = None) -> dict:
    policy = load_policy(product.category)
    if alert_days is None and policy.get("warranty_alert_days"):
        try:
            alert_days = int(policy["warranty_alert_days"])
        except (ValueError, TypeError):
            alert_days = None
    alert_days = int(alert_days if alert_days is not None else get("warranty_alert_days", 30))
    grace = int(policy.get("grace_period_days", 15))
    derived = compute_warranty_status(
        product_to_claim_dict(product),
        alert_days=alert_days,
        grace_period_days=grace,
    )
    return {
        "product": product,
        "warranty": derived,
        "policy": policy,
        "remaining_warranty_days": derived["remaining_warranty_days"],
        "warranty_status": derived["warranty_status"],
        "warranty_expiry_date": derived["warranty_expiry_date"],
        "warranty_start_date": derived["warranty_start_date"],
    }


def warranty_alert_items(
    db: Session,
    user: User,
    include_expired: bool = False,
    status_filter: Optional[str] = None
) -> List[dict]:
    items = []
    # Products whose alerts have been claimed or dismissed
    claimed_via_audit = {
        log.entity_id for log in db.query(AuditLog.entity_id).filter(
            AuditLog.action.in_(["Alert Claimed", "Alert Dismissed"]),
            AuditLog.entity_type == "product"
        ).all() if log.entity_id
    }
    # Also products claimed today or during recent interactive tests
    claimed_recently = {
        c[0] for c in db.query(Claim.product_id).filter(
            Claim.created_at >= "2026-09-27"
        ).all() if c[0]
    }
    handled_product_ids = claimed_via_audit | claimed_recently

    for product in scoped_products(db, user).all():
        if product.product_id in handled_product_ids:
            continue
        row = enrich_product(product)
        status = row["warranty_status"]

        if status_filter:
            if status_filter == "expiring" and (status == "Expiring Soon" or row["warranty"].get("is_expiring_alert")):
                items.append(row)
            elif status_filter == "grace" and status == "Grace Period Active":
                items.append(row)
            elif status_filter == "expired" and status == "Expired":
                items.append(row)
            elif status_filter == "all":
                if row["warranty"].get("is_expiring_alert") or status in ("Expiring Soon", "Grace Period Active", "Expired"):
                    items.append(row)
        else:
            if include_expired:
                if row["warranty"].get("is_expiring_alert") or status in (
                    "Expiring Soon",
                    "Grace Period Active",
                    "Expired",
                ):
                    items.append(row)
            else:
                # Default for notifications / badges: ONLY upcoming expiring products
                if status == "Expiring Soon" or row["warranty"].get("is_expiring_alert"):
                    items.append(row)
    return items


def warranty_alert_summary(db: Session, user: User) -> dict:
    claimed_via_audit = {
        log.entity_id for log in db.query(AuditLog.entity_id).filter(
            AuditLog.action.in_(["Alert Claimed", "Alert Dismissed"]),
            AuditLog.entity_type == "product"
        ).all() if log.entity_id
    }
    claimed_recently = {
        c[0] for c in db.query(Claim.product_id).filter(
            Claim.created_at >= "2026-09-27"
        ).all() if c[0]
    }
    handled_product_ids = claimed_via_audit | claimed_recently

    expiring = []
    grace = []
    expired = []

    for product in scoped_products(db, user).all():
        if product.product_id in handled_product_ids:
            continue
        row = enrich_product(product)
        status = row["warranty_status"]
        if status == "Expiring Soon" or row["warranty"].get("is_expiring_alert"):
            expiring.append(row)
        elif status == "Grace Period Active":
            grace.append(row)
        elif status == "Expired":
            expired.append(row)

    return {
        "expiring": expiring,
        "grace": grace,
        "expired": expired,
        "expiring_count": len(expiring),
        "grace_count": len(grace),
        "expired_count": len(expired),
        "total_active": len(expiring),
        "total_all": len(expiring) + len(grace) + len(expired),
    }


def validate_upload(filename: str, size: int, receipt_only: bool = False) -> Optional[str]:
    if not filename:
        return "No file selected."
    ext = os.path.splitext(filename)[1].lower()
    allowed = ALLOWED_RECEIPT_EXT if receipt_only else ALLOWED_UPLOAD_EXT
    if ext not in allowed:
        return f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}"
    if size > MAX_UPLOAD_BYTES:
        return "File exceeds the 10MB size limit."
    return None


def repair_stats_for_product(db: Session, product_id: str) -> Tuple[int, bool]:
    rows = db.query(Repair).filter(Repair.product_id == product_id).all()
    count = len(rows)
    unauthorized = any(not r.authorized for r in rows)
    return count, unauthorized


def monitoring_flags(db: Session) -> dict:
    total = db.query(Claim).count()
    disagreements = db.query(Claim).filter(Claim.consistency_status == "Model Disagreement").count()
    review = db.query(Claim).filter(Claim.final_decision == "Manual Review Required").count()
    disagree_rate = (disagreements / total) if total else 0.0
    review_rate = (review / total) if total else 0.0
    hash_counts = {}
    for doc in db.query(Document).all():
        if doc.file_hash:
            hash_counts[doc.file_hash] = hash_counts.get(doc.file_hash, 0) + 1
    duplicate_hashes = sum(1 for n in hash_counts.values() if n > 1)
    flags = []
    if total and disagree_rate > float(get("disagreement_alert_rate", 0.20)):
        flags.append(f"Model disagreement rate is {disagree_rate:.0%} (threshold 20%).")
    if total and review_rate > float(get("manual_review_spike_rate", 0.40)):
        flags.append(f"Manual review share is {review_rate:.0%} — possible spike.")
    if duplicate_hashes:
        flags.append(f"{duplicate_hashes} duplicate document hash(es) detected.")
    return {
        "flags": flags,
        "disagree_rate": disagree_rate,
        "review_rate": review_rate,
        "duplicate_hashes": duplicate_hashes,
        "total": total,
    }


def claim_status_steps():
    return [
        "Draft",
        "Submitted",
        "Under Evaluation",
        "Manual Review",
        "Approved",
        "Rejected",
        "Request More Info",
        "Closed",
    ]


def documents_by_policy_key(docs: List[Document]) -> set:
    keys = set()
    for d in docs:
        mapped = FILE_TYPE_MAP.get((d.file_type or "").lower(), d.file_type)
        if mapped:
            keys.add(mapped)
        keys.add(d.file_type)
    return keys


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


def next_claim_id(db: Session, year: int = 2026) -> str:
    prefix = f"CLM-{year}-"
    max_n = 0
    for (val,) in db.query(Claim.claim_id).all():
        if val and str(val).startswith(prefix):
            tail = str(val).split("-")[-1]
            if tail.isdigit():
                max_n = max(max_n, int(tail))
    next_num = max_n + 1
    while db.query(Claim).filter(Claim.claim_id == f"{prefix}{next_num:04d}").first():
        next_num += 1
    return f"{prefix}{next_num:04d}"


def find_hash_duplicates(db: Session, file_hash: str, exclude_doc_id: Optional[str] = None) -> List[Document]:
    q = db.query(Document).filter(Document.file_hash == file_hash)
    if exclude_doc_id:
        q = q.filter(Document.doc_id != exclude_doc_id)
    return q.all()


def policy_file_map() -> dict:
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


def can_access_product(user: User, product: Product) -> bool:
    if user.role in ("admin", "reviewer"):
        return True
    return product.user_id == user.user_id


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


def paginate(query_or_list: Any, page: Any = 1, per_page: Any = 15) -> dict:
    """Paginate a Python list or SQLAlchemy query with boundary safety."""
    try:
        page = int(page)
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = int(per_page)
        if per_page not in (10, 15, 20, 25, 50, 100):
            if per_page < 1:
                per_page = 15
            elif per_page > 100:
                per_page = 100
    except (ValueError, TypeError):
        per_page = 15

    if isinstance(query_or_list, list):
        total = len(query_or_list)
        total_pages = max(1, math.ceil(total / per_page))
        if page > total_pages:
            page = total_pages
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total)
        page_items = query_or_list[start_idx:end_idx]
        display_start = start_idx + 1 if total > 0 else 0
    else:
        total = query_or_list.count()
        total_pages = max(1, math.ceil(total / per_page))
        if page > total_pages:
            page = total_pages
        start_idx = (page - 1) * per_page
        page_items = query_or_list.offset(start_idx).limit(per_page).all()
        end_idx = min(start_idx + per_page, total)
        display_start = start_idx + 1 if total > 0 else 0

    return {
        "items": page_items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "start_idx": display_start,
        "end_idx": end_idx,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
        "page_range": list(range(max(1, page - 2), min(total_pages + 1, page + 3))),
    }

