"""
AssureX Claim Engine - Scenario Definitions
Defines rules, features, and target classifications for all claim test scenarios required by Aptech SRS v1.0.
"""

SCENARIOS = {
    "SCENARIO_01_VALID_CLAIM": {
        "name": "Standard Valid Claim",
        "expected_class": "Valid Claim",
        "description": "Product is well within warranty period, damage is non-excluded, receipt and serial number match, zero unauthorized repairs.",
        "characteristics": {
            "remaining_warranty_days": "> 60",
            "damage_type": "none",
            "has_receipt": True,
            "has_unauthorized_repairs": False,
            "serial_match_status": "Exact",
            "contradiction_flag": False
        }
    },
    "SCENARIO_02_EXPIRED_WARRANTY": {
        "name": "Expired Warranty Hard Fail",
        "expected_class": "Invalid Claim",
        "description": "Claim submitted post warranty expiration plus grace period.",
        "characteristics": {
            "remaining_warranty_days": "< -15",
            "rule_result": "Hard Fail (Warranty Expired)"
        }
    },
    "SCENARIO_03_EXCLUDED_DAMAGE": {
        "name": "Excluded Damage Exclusion",
        "expected_class": "Invalid Claim",
        "description": "Reported damage is liquid spill, physical drop, or unauthorized tampering.",
        "characteristics": {
            "damage_type": ["liquid_spill_damage", "physical_drop_crack"],
            "rule_result": "Hard Fail (Excluded Damage)"
        }
    },
    "SCENARIO_04_UNAUTHORIZED_REPAIR": {
        "name": "Unauthorized Repair Attempt",
        "expected_class": "Invalid Claim",
        "description": "Product serviced previously by non-authorized repair center.",
        "characteristics": {
            "has_unauthorized_repairs": True,
            "rule_result": "Hard Fail (Unauthorized Service)"
        }
    },
    "SCENARIO_05_MISSING_DOCUMENT": {
        "name": "Missing Mandatory Receipt / Serial Evidence",
        "expected_class": "Manual Review",
        "description": "Mandatory proof of purchase or serial number photo missing.",
        "characteristics": {
            "has_receipt": False,
            "missing_documents_count": ">= 1",
            "rule_result": "Manual Review Required"
        }
    },
    "SCENARIO_06_CONTRADICTORY_TIMELINE": {
        "name": "Timeline Contradiction Anomaly",
        "expected_class": "Manual Review",
        "description": "Fault occurrence date registered prior to product purchase date.",
        "characteristics": {
            "fault_date": "< purchase_date",
            "contradiction_flag": True
        }
    },
    "SCENARIO_07_DUPLICATE_CLAIM": {
        "name": "Duplicate Claim Document Hash Match",
        "expected_class": "Manual Review",
        "description": "Matching receipt SHA-256 hash or active Serial + Invoice combination.",
        "characteristics": {
            "duplicate_claim_flag": True,
            "rule_result": "Manual Review Required (Duplicate Alert)"
        }
    },
    "SCENARIO_08_SERIAL_MISMATCH": {
        "name": "Serial Number Optical OCR Mismatch",
        "expected_class": "Manual Review",
        "description": "Serial number typed by user differs from serial number extracted by document OCR.",
        "characteristics": {
            "serial_match_status": "Mismatch",
            "rule_result": "Manual Review Required"
        }
    },
    "SCENARIO_09_BOUNDARY_DATE": {
        "name": "Tricky Warranty Boundary Claim",
        "expected_class": "Valid Claim",
        "description": "Claim submitted on the exact final day of active warranty coverage.",
        "characteristics": {
            "remaining_warranty_days": "0",
            "rule_result": "Within Coverage Period"
        }
    },
    "SCENARIO_10_MODEL_DISAGREEMENT": {
        "name": "Dual-Model Prediction Disagreement",
        "expected_class": "Manual Review",
        "description": "Python ML predicts Valid Claim while Vision Summary Card model predicts Invalid Claim.",
        "characteristics": {
            "python_predicted_class": "Valid Claim",
            "vision_predicted_class": "Invalid Claim",
            "consistency_status": "Model Disagreement"
        }
    },
    "SCENARIO_11_BORDERLINE_FEATURE": {
        "name": "High Repair Frequency Borderline Claim",
        "expected_class": "Manual Review",
        "description": "Multiple previous repairs logged within a short timeframe.",
        "characteristics": {
            "previous_repairs_count": ">= 2",
            "rule_result": "Manual Review Triggered"
        }
    }
}

if __name__ == "__main__":
    print(f"Total Scenario Definitions Registered: {len(SCENARIOS)}")
    for k, v in SCENARIOS.items():
        print(f"[{k}] -> Expected: {v['expected_class']} | Name: {v['name']}")
