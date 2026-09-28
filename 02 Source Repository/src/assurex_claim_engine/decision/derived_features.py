"""
AssureX Claim Engine - Shared Derived Feature Computation Module
Computes standardized derived claim features (ages, remaining warranty, serial status,
contradiction flags, missing document counts) identically for dataset generation,
offline evaluation, and live web application claim submission.
"""

from datetime import datetime, timedelta, timezone
from assurex_claim_engine.decision.contradiction import ContradictionAndDuplicateDetector

CATEGORY_DEFAULTS = {
    "electronics": {"warranty_months": 24},
    "appliances": {"warranty_months": 36},
    "automotive": {"warranty_months": 12},
}

def _parse_bool(val, default=True):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    s = str(val).strip().lower()
    if s in ("true", "1", "yes", "t", "y"):
        return True
    if s in ("false", "0", "no", "f", "n"):
        return False
    return default

def compute_derived_claim_features(raw_claim: dict) -> dict:
    """
    Computes standard derived fields for claim processing and card rendering.
    Calculates age, remaining warranty, serial status, contradiction flags,
    and missing document counts using identical formulas used during dataset generation.
    """
    claim = dict(raw_claim)
    
    cat_key = str(claim.get("product_category", "electronics")).lower()
    cat_default_warranty = CATEGORY_DEFAULTS.get(cat_key, {}).get("warranty_months", 24)
    
    # 1. Warranty duration
    raw_w_months = claim.get("warranty_duration_months") if claim.get("warranty_duration_months") is not None else claim.get("warranty_months")
    try:
        warranty_months = int(raw_w_months) if raw_w_months is not None else cat_default_warranty
    except Exception:
        warranty_months = cat_default_warranty

    has_ext = _parse_bool(claim.get("has_extended_warranty"), default=False)
    ext_provider = str(claim.get("extended_warranty_provider") or "").strip()
    ext_contract = str(claim.get("extended_warranty_contract_number") or claim.get("extended_contract_number") or "").strip()
    try:
        ext_months = int(claim.get("extended_warranty_duration_months") or 0)
    except Exception:
        ext_months = 0
    if ext_provider or ext_contract:
        has_ext = True

    effective_warranty_months = warranty_months + (ext_months if has_ext else 0)
        
    user_sn = str(claim.get("user_serial_number") or claim.get("serial_number") or "").strip()
    ocr_sn = str(claim.get("ocr_serial_number") or user_sn).strip()
    
    purchase_date_str = str(claim.get("purchase_date") or claim.get("warranty_start_date") or "2026-01-01").strip()
    fault_date_str = str(claim.get("fault_occurrence_date") or purchase_date_str).strip()
    claim_date_str = str(claim.get("claim_submission_date") or datetime.now().strftime("%Y-%m-%d")).strip()
    
    # 2. Date parsing & warranty calculations (using 30-day month formula used in dataset generation)
    try:
        p_date = datetime.strptime(purchase_date_str, "%Y-%m-%d")
        f_date = datetime.strptime(fault_date_str, "%Y-%m-%d")
        c_date = datetime.strptime(claim_date_str, "%Y-%m-%d")
        
        if claim.get("warranty_expiry_date") and str(claim.get("warranty_expiry_date")).strip():
            try:
                w_expiry = datetime.strptime(str(claim["warranty_expiry_date"]).strip(), "%Y-%m-%d")
            except Exception:
                w_expiry = p_date + timedelta(days=30 * effective_warranty_months)
        else:
            w_expiry = p_date + timedelta(days=30 * effective_warranty_months)
            
        product_age_days = (c_date - p_date).days
        remaining_warranty_days = (w_expiry - c_date).days
        reporting_delay_days = (c_date - f_date).days
        std_expiry = p_date + timedelta(days=30 * warranty_months)
        standard_remaining_days = (std_expiry - c_date).days
        w_expiry_str = w_expiry.strftime("%Y-%m-%d")
        w_start_str = p_date.strftime("%Y-%m-%d")
    except Exception:
        product_age_days = int(claim.get("product_age_days", 100))
        remaining_warranty_days = int(claim.get("remaining_warranty_days", 200))
        reporting_delay_days = int(claim.get("reporting_delay_days", 5))
        standard_remaining_days = remaining_warranty_days
        w_expiry_str = str(claim.get("warranty_expiry_date", "2026-12-31"))
        w_start_str = purchase_date_str

    # 3. Document flags & count
    has_receipt = _parse_bool(claim.get("has_receipt"), default=True)
    has_warranty_card = _parse_bool(claim.get("has_warranty_card"), default=True)
    has_product_photo = _parse_bool(claim.get("has_product_photo"), default=True)
    has_serial_photo = _parse_bool(claim.get("has_serial_photo"), default=True)
    
    if "missing_documents_count" in claim and claim["missing_documents_count"] is not None:
        try:
            missing_docs_count = int(claim["missing_documents_count"])
        except Exception:
            missing_docs_count = sum([not has_receipt, not has_warranty_card, not has_product_photo, not has_serial_photo])
    else:
        missing_docs_count = sum([not has_receipt, not has_warranty_card, not has_product_photo, not has_serial_photo])

    # 4. Serial match status
    if "serial_match_status" in claim and claim["serial_match_status"]:
        serial_status = str(claim["serial_match_status"])
    else:
        if user_sn and ocr_sn and user_sn.upper() != ocr_sn.upper():
            serial_status = "Mismatch"
        else:
            serial_status = "Exact"

    # 5. Contradictions (reuse ContradictionAndDuplicateDetector)
    raw_contradiction = _parse_bool(claim.get("contradiction_flag"), default=False)
    temp_check = {
        "purchase_date": purchase_date_str,
        "fault_occurrence_date": fault_date_str,
        "claim_submission_date": claim_date_str,
        "user_serial_number": user_sn,
        "ocr_serial_number": ocr_sn,
        "contradiction_flag": raw_contradiction
    }
    contra_res = ContradictionAndDuplicateDetector.detect_contradictions(temp_check)
    contradiction_flag = contra_res["has_contradictions"] or raw_contradiction

    updated = dict(claim)
    updated["claim_id"] = str(claim.get("claim_id", "CLM-2026-0001"))
    updated["user_id"] = str(claim.get("user_id", "USR-1001"))
    updated["product_id"] = str(claim.get("product_id", "PRD-00001"))
    updated["product_name"] = str(claim.get("product_name") or f"{claim.get('brand', 'Generic')} {claim.get('model_number', 'Model')}")
    updated["product_category"] = cat_key
    updated["brand"] = str(claim.get("brand", "Generic"))
    updated["model_number"] = str(claim.get("model_number", "Model"))
    updated["user_serial_number"] = user_sn
    updated["ocr_serial_number"] = ocr_sn
    updated["serial_match_status"] = serial_status
    updated["purchase_date"] = purchase_date_str
    try:
        updated["purchase_price"] = float(claim.get("purchase_price", 500.0))
    except Exception:
        updated["purchase_price"] = 500.0
    updated["retailer"] = str(claim.get("retailer", "Retailer"))
    updated["warranty_duration_months"] = warranty_months
    updated["has_extended_warranty"] = has_ext
    updated["extended_warranty_provider"] = ext_provider
    updated["extended_warranty_contract_number"] = ext_contract
    updated["extended_warranty_duration_months"] = ext_months
    updated["standard_remaining_days"] = standard_remaining_days
    updated["warranty_start_date"] = w_start_str
    updated["warranty_expiry_date"] = w_expiry_str
    updated["fault_occurrence_date"] = fault_date_str
    updated["claim_submission_date"] = claim_date_str
    updated["fault_category"] = str(claim.get("fault_category", "general_defect"))
    updated["damage_type"] = str(claim.get("damage_type", "none"))
    try:
        updated["previous_repairs_count"] = int(claim.get("previous_repairs_count", 0))
    except Exception:
        updated["previous_repairs_count"] = 0
    updated["has_unauthorized_repairs"] = _parse_bool(claim.get("has_unauthorized_repairs"), default=False)
    updated["has_receipt"] = has_receipt
    updated["has_warranty_card"] = has_warranty_card
    updated["has_product_photo"] = has_product_photo
    updated["has_serial_photo"] = has_serial_photo
    updated["missing_documents_count"] = missing_docs_count
    updated["contradiction_flag"] = contradiction_flag
    updated["duplicate_claim_flag"] = _parse_bool(claim.get("duplicate_claim_flag"), default=False)
    updated["product_age_days"] = product_age_days
    updated["remaining_warranty_days"] = remaining_warranty_days
    updated["reporting_delay_days"] = reporting_delay_days
    
    return updated


def compute_warranty_status(
    product_or_claim: dict,
    today: datetime = None,
    alert_days: int = 30,
    grace_period_days: int = 15,
) -> dict:
    """Classify warranty coverage for a registered product using the same 30-day-month math."""
    today = today or datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    payload = dict(product_or_claim)
    if "product_category" not in payload and payload.get("category"):
        payload["product_category"] = payload["category"]
    payload.setdefault("claim_submission_date", today_str)
    payload.setdefault("fault_occurrence_date", payload.get("purchase_date") or today_str)
    derived = compute_derived_claim_features(payload)
    remaining = int(derived.get("remaining_warranty_days", 0) or 0)
    std_remaining = int(derived.get("standard_remaining_days", remaining) or remaining)
    has_ext = derived.get("has_extended_warranty", False)
    if remaining >= alert_days:
        if has_ext and std_remaining < alert_days:
            status = "Extended Warranty Active"
        else:
            status = "Active"
    elif remaining >= 0:
        if has_ext and std_remaining < 0:
            status = "Extended Warranty Active"
        else:
            status = "Expiring Soon"
    elif remaining >= -int(grace_period_days):
        status = "Grace Period Active"
    else:
        status = "Expired"
    derived["warranty_status"] = status
    derived["alert_days"] = alert_days
    derived["grace_period_days"] = grace_period_days
    derived["is_alert"] = status in ("Expiring Soon", "Grace Period Active", "Expired")
    derived["is_expiring_alert"] = status == "Expiring Soon"
    return derived

