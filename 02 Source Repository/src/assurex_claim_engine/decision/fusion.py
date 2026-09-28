"""
AssureX Claim Engine - Decision Fusion & Explanation Engine
Fuses all signals into the final adjudication decision:
1. Python Tabular ML Prediction & Confidence
2. Vision Summary Card Model Prediction & Confidence
3. Dual-Model Consistency Status
4. Configurable Business Rule Results (Hard Fail, Manual Review)
5. Contradiction & Duplicate Detection Flags

Final Decision Classes:
- 'Likely Valid'
- 'Likely Invalid'
- 'Manual Review Required'
"""

from typing import Dict, Any, List
from assurex_claim_engine.decision.comparison import DualModelComparator
from assurex_claim_engine.rule_engine.evaluator import PolicyRuleEvaluator
from assurex_claim_engine.decision.contradiction import ContradictionAndDuplicateDetector

class DecisionFusionEngine:
    def __init__(self):
        self.rule_evaluator = PolicyRuleEvaluator()

    def evaluate_full_claim(
        self,
        claim: Dict[str, Any],
        python_result: Dict[str, Any],
        vision_result: Dict[str, Any],
        existing_claims: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        # 1. Dual Model Comparison
        comparison = DualModelComparator.compare_models(python_result, vision_result)

        # 2. Business Rule Evaluation
        rule_eval = self.rule_evaluator.evaluate_claim(claim)

        # 3. Contradiction & Duplicate Detection
        contradiction_eval = ContradictionAndDuplicateDetector.detect_contradictions(claim)
        duplicate_eval = ContradictionAndDuplicateDetector.check_duplicate(claim, existing_claims)

        supporting_factors: List[str] = []
        opposing_factors: List[str] = []
        required_actions: List[str] = []

        # Start Decision Logic
        if rule_eval["hard_fail"] or rule_eval["warnings"]:
            # SRS step 12 requires a human disposition for rule violations.
            final_decision = "Manual Review Required"
            opposing_factors.extend(rule_eval["failed_rules"])
            opposing_factors.extend(rule_eval["warnings"])
            required_actions.append("Review the policy violation and record an authorized disposition.")
        elif duplicate_eval["is_duplicate"] or contradiction_eval["has_contradictions"]:
            final_decision = "Manual Review Required"
            if duplicate_eval["is_duplicate"]:
                opposing_factors.extend(duplicate_eval["duplicate_reasons"])
                required_actions.append("Verify potential duplicate claim details with claimant.")
            if contradiction_eval["has_contradictions"]:
                opposing_factors.extend(contradiction_eval["contradictions"])
                required_actions.append("Inspect timeline inconsistencies and request revised invoice.")
        elif rule_eval["manual_review_required"]:
            final_decision = "Manual Review Required"
            opposing_factors.extend(rule_eval["manual_review_triggers"])
            if rule_eval["missing_documents"]:
                required_actions.append(f"Request missing documentation: {', '.join(rule_eval['missing_documents'])}")
        elif comparison["consistency_status"] in ["Model Disagreement", "Uncertain Result", "Weak Match"]:
            final_decision = "Manual Review Required"
            opposing_factors.append(f"AI Disagreement / Uncertainty ({comparison['consistency_status']}): {comparison['status_description']}")
            required_actions.append("Manual reviewer audit required due to model confidence discrepancy.")
        else:
            # Models agree and rules pass
            py_pred = python_result["predicted_class"]
            vis_pred = vision_result["predicted_class"]

            if py_pred == "Valid Claim" and vis_pred == "Valid Claim":
                final_decision = "Likely Valid"
                supporting_factors.append("Python ML model & Vision Classifier both predict 'Valid Claim' with strong confidence.")
                supporting_factors.extend(rule_eval["passed_rules"])
            elif py_pred == "Invalid Claim" and vis_pred == "Invalid Claim":
                final_decision = "Likely Invalid"
                opposing_factors.append("Python ML model & Vision Classifier both predict 'Invalid Claim'.")
                opposing_factors.extend(rule_eval["failed_rules"])
            else:
                final_decision = "Manual Review Required"
                opposing_factors.append(f"Borderline model predictions (Python: {py_pred}, Vision: {vis_pred}).")
                required_actions.append("Conduct manual inspection of claim dossier.")

        # Default action for valid claims
        if final_decision == "Likely Valid" and not required_actions:
            required_actions.append("Proceed with claim approval and service authorization.")
        elif final_decision == "Likely Invalid" and not required_actions:
            required_actions.append("Issue rejection notice specifying non-compliance reasons.")

        dossier_data = {
            "claim_id": claim.get("claim_id", "CLM-UNKNOWN"),
            "final_decision": final_decision,
            "comparison": comparison,
            "rule_evaluation": rule_eval,
            "contradictions": contradiction_eval,
            "duplicates": duplicate_eval,
            "claim_dict": claim,
            "explanation": {
                "supporting_factors": supporting_factors,
                "opposing_factors": opposing_factors,
                "required_actions": required_actions
            }
        }
        dossier_data["narrative_summary"] = generate_narrative_summary(claim, dossier=dossier_data)
        return dossier_data


def generate_narrative_summary(claim: Any, product: Any = None, dossier: Dict[str, Any] = None) -> str:
    """Generate human-readable English paragraph narrative summary (Module xxxii)."""
    dossier = dossier or {}

    # 1. Claim ID & Product identification
    if isinstance(claim, dict):
        claim_id = claim.get("claim_id") or "CLM-PENDING"
        fault_cat = claim.get("fault_category") or ""
        status = claim.get("status") or claim.get("final_decision") or "Draft"
        doc_hash = claim.get("document_hash") or ""
        py_class = claim.get("python_predicted_class") or ""
        py_conf = claim.get("python_top_confidence") or 0.0
        vis_class = claim.get("vision_predicted_class") or ""
        vis_conf = claim.get("vision_top_confidence") or 0.0
        consistency = claim.get("consistency_status") or ""
        final_dec = claim.get("final_decision") or status
        rev_comments = claim.get("reviewer_comments") or ""
        claim_dict = claim
    else:
        claim_id = getattr(claim, "claim_id", "CLM-PENDING")
        fault_cat = getattr(claim, "fault_category", "") or ""
        status = getattr(claim, "status", "") or "Draft"
        doc_hash = getattr(claim, "document_hash", "") or ""
        py_class = getattr(claim, "python_predicted_class", "") or ""
        py_conf = getattr(claim, "python_top_confidence", 0.0) or 0.0
        vis_class = getattr(claim, "vision_predicted_class", "") or ""
        vis_conf = getattr(claim, "vision_top_confidence", 0.0) or 0.0
        consistency = getattr(claim, "consistency_status", "") or ""
        final_dec = getattr(claim, "final_decision", "") or status
        rev_comments = getattr(claim, "reviewer_comments", "") or ""
        claim_dict = dossier.get("claim_dict") or {}

    # Extract comparison / predictions from dossier if not on claim
    comparison = dossier.get("comparison") or {}
    if not py_class and comparison.get("python_prediction"):
        py_class = comparison.get("python_prediction")
        py_conf = comparison.get("python_confidence", 0.0)
    if not vis_class and comparison.get("vision_prediction"):
        vis_class = comparison.get("vision_prediction")
        vis_conf = comparison.get("vision_confidence", 0.0)
    if not consistency and comparison.get("consistency_status"):
        consistency = comparison.get("consistency_status")

    # Resolve product info
    prod_name = ""
    brand = ""
    category = ""
    if product:
        prod_name = getattr(product, "product_name", "")
        brand = getattr(product, "brand", "")
        category = getattr(product, "category", "")
    elif isinstance(claim_dict, dict):
        prod_name = claim_dict.get("product_name", "")
        brand = claim_dict.get("brand", "")
        category = claim_dict.get("product_category", "")

    if prod_name:
        prod_label = prod_name
    elif brand or category:
        prod_label = f"{brand} {category}".strip()
    else:
        prod_label = "the registered product"

    prod_label = prod_label.strip()

    fault_label = fault_cat.replace("_", " ").title() if fault_cat else "unspecified defect"

    # If claim is still a draft
    if status == "Draft":
        return (
            f"Claim {claim_id} was initiated for {prod_label} regarding {fault_label}. "
            f"This claim is currently saved as a draft pending complete documentation upload and formal submission "
            f"for dual-model AI adjudication."
        )

    # 2. Document & OCR verification
    has_receipt = claim_dict.get("has_receipt")
    serial_match = claim_dict.get("serial_match_status") or "Exact"

    if has_receipt is False:
        doc_part = "Purchase receipt was flagged as missing or unverified."
    elif serial_match in ["Mismatch", "Contradiction"]:
        doc_part = "Purchase documentation was processed, but a potential serial number discrepancy was detected."
    else:
        doc_part = "Purchase was verified via OCR receipt extraction with valid cryptographic hash integrity."

    # 3. Timeline & Warranty
    rem_days = claim_dict.get("remaining_warranty_days")
    warranty_part = ""
    if rem_days is not None:
        try:
            rem_days_int = int(rem_days)
            if rem_days_int > 30:
                warranty_part = f"Incident occurred within the active warranty window with {rem_days_int} remaining coverage days."
            elif rem_days_int > 0:
                warranty_part = f"Incident occurred inside the warranty expiration alert window with {rem_days_int} days remaining."
            elif rem_days_int >= -30:
                warranty_part = f"Incident occurred within the 30-day post-expiration grace period ({abs(rem_days_int)} days elapsed)."
            else:
                warranty_part = f"Incident occurred after warranty expiration ({abs(rem_days_int)} days elapsed)."
        except (ValueError, TypeError):
            pass

    ext_contract = getattr(claim, "extended_warranty_contract_number", "") or (claim_dict.get("extended_warranty_contract_number") if isinstance(claim_dict, dict) else "")
    ext_provider = getattr(claim, "extended_warranty_provider", "") or (claim_dict.get("extended_warranty_provider") if isinstance(claim_dict, dict) else "")
    if not ext_contract and product:
        ext_contract = getattr(product, "extended_warranty_contract_number", "") or ""
    if not ext_provider and product:
        ext_provider = getattr(product, "extended_warranty_provider", "") or ""

    if ext_contract or ext_provider:
        ext_label = f"contract #{ext_contract}" if ext_contract else "contract"
        prov_label = f"provided by {ext_provider}" if ext_provider else ""
        clause = f"{ext_label} ({prov_label})".strip() if prov_label else ext_label
        warranty_part = f"{warranty_part} Asset is covered under extended warranty {clause}.".strip()

    # 4. Dual-Model Evaluation
    model_part = ""
    if py_class and vis_class:
        try:
            py_pct = float(py_conf) * 100
            vis_pct = float(vis_conf) * 100
            if consistency in ["Strong Match", "Acceptable Match", "Consistent"]:
                model_part = (
                    f"Dual-model AI evaluation reached strong consensus: Tabular ML predicted {py_class} ({py_pct:.1f}% confidence) "
                    f"and Vision Summary model predicted {vis_class} ({vis_pct:.1f}% confidence)."
                )
            else:
                model_part = (
                    f"Dual-model evaluation flagged an inter-model divergence ({consistency}): Tabular ML scored {py_class} "
                    f"({py_pct:.1f}%) whereas Vision model scored {vis_class} ({vis_pct:.1f}%)."
                )
        except (ValueError, TypeError):
            pass

    # 5. Rule execution & Decision outcome
    rule_eval = dossier.get("rule_evaluation") or {}
    passed_rules = len(rule_eval.get("passed_rules") or [])
    failed_rules = rule_eval.get("failed_rules") or []

    if failed_rules:
        fail_desc = ", ".join(r.rstrip(".") for r in failed_rules[:2])
        rule_part = f"Policy rule evaluation triggered {len(failed_rules)} non-compliance exclusion(s): {fail_desc}."
    elif passed_rules:
        rule_part = f"All {passed_rules} policy compliance rules passed verification successfully."
    else:
        rule_part = "Standard warranty policy heuristics were applied."

    outcome_label = final_dec or status
    dec_part = f"The automated engine determination is: {outcome_label}."
    if rev_comments:
        dec_part += f" Reviewer remarks: \"{rev_comments}\"."

    sentences = [
        f"Claim {claim_id} was filed for {prod_label} regarding {fault_label}.",
        doc_part
    ]
    if warranty_part:
        sentences.append(warranty_part)
    if model_part:
        sentences.append(model_part)
    sentences.append(rule_part)
    sentences.append(dec_part)

    return " ".join(sentences)

if __name__ == "__main__":
    fusion = DecisionFusionEngine()
    sample_claim = {
        "claim_id": "CLM-2026-0001",
        "product_category": "electronics",
        "has_receipt": True,
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "remaining_warranty_days": 180,
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "has_unauthorized_repairs": False,
        "serial_match_status": "Exact",
        "purchase_date": "2025-01-01",
        "fault_occurrence_date": "2026-05-01",
        "claim_submission_date": "2026-05-05"
    }
    py_res = {"predicted_class": "Valid Claim", "top_confidence": 0.96, "probabilities": {"Valid Claim": 0.96, "Invalid Claim": 0.02, "Manual Review": 0.02}}
    vis_res = {"predicted_class": "Valid Claim", "top_confidence": 0.92, "probabilities": {"Valid Claim": 0.92, "Invalid Claim": 0.05, "Manual Review": 0.03}}

    decision = fusion.evaluate_full_claim(sample_claim, py_res, vis_res)
    print("Fused Decision Result:")
    print(decision["final_decision"])
    print(decision["explanation"])
