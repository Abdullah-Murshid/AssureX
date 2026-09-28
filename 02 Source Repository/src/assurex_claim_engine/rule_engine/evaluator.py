"""
AssureX Claim Engine - Configurable Business Rule Evaluator with Rule-Type Registry
Loads category policy JSON files and dynamically evaluates business rules via registered handlers:
- Hard Fail Rules (e.g. warranty expired, excluded damage, unauthorized repair)
- Warning Rules (e.g. late reporting, slight serial mismatch, high repair frequency)
- Manual Review Rules (e.g. missing mandatory documents, unlisted fault category, custom wiring)
"""

import os
import json
from typing import Dict, Any, List, Tuple, Callable

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

# Rule Type Registry
RULE_REGISTRY: Dict[str, Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any]], Tuple[bool, str, str]]] = {}


def register_rule_type(rule_type_name: str):
    """Decorator to register a function as the evaluator for a specific rule_type."""
    def decorator(fn: Callable):
        RULE_REGISTRY[rule_type_name] = fn
        return fn
    return decorator


@register_rule_type("warranty_expiry")
def evaluate_warranty_expiry(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    remaining_days = claim.get("remaining_warranty_days", 0)
    grace_period = policy.get("grace_period_days", 15)
    if remaining_days < -grace_period:
        return True, f"Warranty Expired: Claim submitted {abs(remaining_days)} days post-coverage.", "Warranty Coverage Active / Within Grace Period"
    return False, "", "Warranty Coverage Active / Within Grace Period"


@register_rule_type("excluded_damage")
def evaluate_excluded_damage(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    damage_type = str(claim.get("damage_type", "none")).lower()
    exclusions = [e.lower() for e in policy.get("exclusions", [])]
    if damage_type != "none" and damage_type in exclusions:
        return True, f"Excluded Damage Type: '{damage_type}' is excluded from coverage.", "Damage Type Eligible"
    return False, "", "Damage Type Eligible"


@register_rule_type("unauthorized_repair")
def evaluate_unauthorized_repair(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    has_unauth = claim.get("has_unauthorized_repairs", False) or claim.get("has_previous_unauthorized_repair", False)
    if has_unauth:
        return True, "Unauthorized Repair Detected: Product serviced by non-certified center.", "No Unauthorized Repair History"
    return False, "", "No Unauthorized Repair History"


@register_rule_type("commercial_usage")
def evaluate_commercial_usage(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    usage = str(claim.get("usage_type", "personal")).lower()
    if usage == "commercial":
        return True, "Commercial Usage Exclusion: Appliance used in commercial setting violating home warranty.", "Usage Type Eligible (Personal)"
    return False, "", "Usage Type Eligible"


@register_rule_type("late_reporting")
def evaluate_late_reporting(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    reporting_delay = claim.get("reporting_delay_days", 0)
    deadline = policy.get("reporting_deadline_days", 30)
    if reporting_delay > deadline:
        return True, f"Late Fault Reporting: Fault reported {reporting_delay} days after occurrence (Deadline: {deadline} days).", "Fault Reported Within Allowable Period"
    return False, "", "Fault Reported Within Allowable Period"


@register_rule_type("serial_mismatch")
def evaluate_serial_mismatch(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    serial_status = claim.get("serial_match_status", "Exact")
    serial_score = claim.get("serial_match_score", 1.0)
    vin_match = claim.get("vin_match", True)
    if serial_status == "Mismatch" or serial_score < 0.90 or vin_match is False:
        return True, "Serial Number Mismatch: User input does not match OCR/Photo.", "Serial Number Match Verified"
    return False, "", "Serial Number Match Verified"


@register_rule_type("missing_documents")
def evaluate_missing_documents(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    mandatory_docs = policy.get("mandatory_documents", ["purchase_receipt", "warranty_card"])
    missing_docs = []
    if not claim.get("has_receipt", True) and "purchase_receipt" in mandatory_docs:
        missing_docs.append("purchase_receipt")
    if not claim.get("has_warranty_card", True) and "warranty_card" in mandatory_docs:
        missing_docs.append("warranty_card")
    if not claim.get("has_product_photo", True) and "product_image" in mandatory_docs:
        missing_docs.append("product_image")
    if not claim.get("has_serial_photo", True) and "serial_number_photo" in mandatory_docs:
        missing_docs.append("serial_number_photo")
    if not claim.get("has_vehicle_registration", True) and "vehicle_registration" in mandatory_docs:
        missing_docs.append("vehicle_registration")
    if not claim.get("has_installation_cert", True) and "installation_certificate" in mandatory_docs:
        missing_docs.append("installation_certificate")

    if missing_docs or claim.get("missing_documents_count", 0) > 0:
        docs_str = ", ".join(missing_docs) if missing_docs else f"{claim.get('missing_documents_count')} document(s)"
        return True, f"Missing mandatory documents: {docs_str}", "Mandatory Documents Complete"
    return False, "", "Mandatory Documents Complete"


@register_rule_type("repair_frequency")
def evaluate_repair_frequency(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    repairs = claim.get("previous_repairs_count", claim.get("previous_repair_count", claim.get("recent_repair_count", 0)))
    if repairs >= 2:
        return True, f"High Repair Frequency: {repairs} previous repairs logged for product.", "Repair Frequency Normal"
    return False, "", "Repair Frequency Normal"


@register_rule_type("custom_wiring")
def evaluate_custom_wiring(claim: Dict[str, Any], policy: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, str, str]:
    if claim.get("custom_wiring_flag", False):
        return True, "Custom Wiring Alert: Third-party wiring modification detected.", "Wiring Certified OEM"
    return False, "", "Wiring Certified OEM"


# Policy Rule Evaluator Class
class PolicyRuleEvaluator:
    def __init__(self, policy_dir: str = POLICY_DIR):
        self.policy_dir = policy_dir
        self.policies = self._load_policies()

    def _load_policies(self) -> Dict[str, Any]:
        policies = {}
        if not os.path.exists(self.policy_dir):
            return policies

        for fname in os.listdir(self.policy_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.policy_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cat = data.get("product_category", "").lower()
                        if cat:
                            policies[cat] = data
                except Exception as e:
                    print(f"Error loading policy {fname}: {e}")
        return policies

    def _get_rule_type(self, rule: Dict[str, Any]) -> str:
        """Resolves rule_type either from explicit field or inferred from rule_id / condition."""
        if "rule_type" in rule:
            return rule["rule_type"]
        rid = rule.get("rule_id", "").upper()
        cond = rule.get("condition", "").lower()
        if "FAIL_01" in rid or "warranty" in cond:
            return "warranty_expiry"
        if "FAIL_02" in rid or "exclusion" in cond:
            return "excluded_damage"
        if "FAIL_03" in rid or "unauthorized" in cond:
            return "unauthorized_repair"
        if "WARN_01" in rid or "reporting" in cond:
            return "late_reporting"
        if "WARN_02" in rid or "serial" in cond or "vin" in cond:
            return "serial_mismatch"
        if "REV_01" in rid or "missing" in cond:
            return "missing_documents"
        if "REV_02" in rid or "repair" in cond:
            return "repair_frequency"
        return "generic"

    def evaluate_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        category = str(claim.get("product_category", "electronics")).lower()
        policy = self.policies.get(category, self.policies.get("electronics", {}))

        passed_rules: List[str] = []
        failed_rules: List[str] = []
        warnings: List[str] = []
        manual_review_triggers: List[str] = []

        hard_fail = False
        manual_review_required = False

        # Compute missing documents list
        mandatory_docs = policy.get("mandatory_documents", ["purchase_receipt", "warranty_card"])
        missing_docs = []
        if not claim.get("has_receipt", True) and "purchase_receipt" in mandatory_docs:
            missing_docs.append("purchase_receipt")
        if not claim.get("has_warranty_card", True) and "warranty_card" in mandatory_docs:
            missing_docs.append("warranty_card")
        if not claim.get("has_product_photo", True) and "product_image" in mandatory_docs:
            missing_docs.append("product_image")
        if not claim.get("has_serial_photo", True) and "serial_number_photo" in mandatory_docs:
            missing_docs.append("serial_number_photo")
        if not claim.get("has_vehicle_registration", True) and "vehicle_registration" in mandatory_docs:
            missing_docs.append("vehicle_registration")
        if not claim.get("has_installation_cert", True) and "installation_certificate" in mandatory_docs:
            missing_docs.append("installation_certificate")

        # 1. Evaluate Hard Fail Rules via Registry
        for rule in policy.get("hard_fail_rules", []):
            rtype = self._get_rule_type(rule)
            handler = RULE_REGISTRY.get(rtype)
            if handler:
                triggered, trig_msg, pass_msg = handler(claim, policy, rule)
                if triggered:
                    hard_fail = True
                    failed_rules.append(trig_msg)
                elif pass_msg and pass_msg not in passed_rules:
                    passed_rules.append(pass_msg)

        # 2. Evaluate Warning Rules via Registry
        for rule in policy.get("warning_rules", []):
            rtype = self._get_rule_type(rule)
            handler = RULE_REGISTRY.get(rtype)
            if handler:
                triggered, trig_msg, pass_msg = handler(claim, policy, rule)
                if triggered:
                    warnings.append(trig_msg)
                elif pass_msg and pass_msg not in passed_rules:
                    passed_rules.append(pass_msg)

        # 3. Evaluate Manual Review Rules via Registry
        for rule in policy.get("manual_review_rules", []):
            rtype = self._get_rule_type(rule)
            handler = RULE_REGISTRY.get(rtype)
            if handler:
                triggered, trig_msg, pass_msg = handler(claim, policy, rule)
                if triggered:
                    manual_review_required = True
                    manual_review_triggers.append(trig_msg)
                elif pass_msg and pass_msg not in passed_rules:
                    passed_rules.append(pass_msg)

        # 4. Covered Fault Check
        fault_cat = str(claim.get("fault_category", "")).lower()
        covered_faults = [f.lower() for f in policy.get("covered_faults", [])]
        if covered_faults and fault_cat and fault_cat not in covered_faults:
            manual_review_required = True
            manual_review_triggers.append(f"Unlisted Fault Category: '{fault_cat}' requires verification.")
        elif covered_faults and "Fault Category Covered" not in passed_rules:
            passed_rules.append("Fault Category Covered")

        # If missing documents found but not yet in manual_review_triggers, add them
        if missing_docs:
            manual_review_required = True
            msg = f"Missing mandatory documents: {', '.join(missing_docs)}"
            if msg not in manual_review_triggers:
                manual_review_triggers.append(msg)
            if "Mandatory Documents Complete" in passed_rules:
                passed_rules.remove("Mandatory Documents Complete")

        return {
            "category_policy": policy.get("category_name", category),
            "hard_fail": hard_fail,
            "manual_review_required": manual_review_required,
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "warnings": warnings,
            "manual_review_triggers": manual_review_triggers,
            "missing_documents": missing_docs
        }


if __name__ == "__main__":
    evaluator = PolicyRuleEvaluator()
    sample_claim = {
        "product_category": "electronics",
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "remaining_warranty_days": 120,
        "has_receipt": True,
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "has_unauthorized_repairs": False,
        "serial_match_status": "Exact",
        "reporting_delay_days": 5
    }
    res = evaluator.evaluate_claim(sample_claim)
    print("Rule Evaluation Result:")
    print(res)
