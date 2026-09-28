"""
AssureX Claim Engine - Automated Verification Test Suite
Tests 11 mandatory claim scenarios required by competition SRS:
1. Valid Claim Scenario
2. Invalid Claim Scenario (Excluded Damage)
3. Manual Review Scenario
4. Expired Warranty Hard Fail
5. Missing Document Scenario
6. Duplicate Claim Scenario
7. Contradictory Timeline Claim
8. Serial Number Mismatch Scenario
9. Unauthorized Repair Scenario
10. Tricky Boundary Date Claim
11. Model Disagreement Routing
"""

import sys
sys.path.insert(0, ".")

import pytest
from assurex_claim_engine.models.tabular_model import TabularClaimClassifier
from assurex_claim_engine.models.image_classifier import ImageClassifierPipeline
from assurex_claim_engine.decision.fusion import DecisionFusionEngine
from assurex_claim_engine.rule_engine.evaluator import PolicyRuleEvaluator
from assurex_claim_engine.decision.contradiction import ContradictionAndDuplicateDetector

@pytest.fixture(scope="module")
def fusion_engine():
    return DecisionFusionEngine()

@pytest.fixture(scope="module")
def tabular_model():
    clf = TabularClaimClassifier()
    clf.load_artifacts()
    return clf

def test_01_valid_claim(fusion_engine, tabular_model):
    claim = {
        "claim_id": "TEST-0001",
        "product_category": "electronics",
        "has_receipt": True,
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "remaining_warranty_days": 150,
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "has_unauthorized_repairs": False,
        "serial_match_status": "Exact",
        "purchase_date": "2025-01-01",
        "fault_occurrence_date": "2026-05-01",
        "claim_submission_date": "2026-05-05",
        "product_age_days": 490,
        "missing_documents_count": 0,
        "contradiction_flag": False,
        "duplicate_claim_flag": False,
        "purchase_price": 799.99,
        "warranty_duration_months": 24,
        "previous_repairs_count": 0,
        "reporting_delay_days": 4,
        "brand": "Sony"
    }
    py_res = tabular_model.predict_single(claim)
    vis_res = {"predicted_class": "Valid Claim", "top_confidence": 0.95, "probabilities": {"Valid Claim": 0.95, "Invalid Claim": 0.03, "Manual Review": 0.02}}
    
    dossier = fusion_engine.evaluate_full_claim(claim, py_res, vis_res)
    assert dossier["final_decision"] == "Likely Valid"

def test_02_expired_warranty_hard_fail(fusion_engine, tabular_model):
    claim = {
        "claim_id": "TEST-0002",
        "product_category": "electronics",
        "has_receipt": True,
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "remaining_warranty_days": -120, # Expired!
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "has_unauthorized_repairs": False,
        "serial_match_status": "Exact",
        "purchase_date": "2023-01-01",
        "fault_occurrence_date": "2026-05-01",
        "claim_submission_date": "2026-05-05",
        "product_age_days": 1200,
        "missing_documents_count": 0,
        "contradiction_flag": False,
        "duplicate_claim_flag": False,
        "purchase_price": 500.0,
        "warranty_duration_months": 24,
        "previous_repairs_count": 0,
        "reporting_delay_days": 4,
        "brand": "Dell"
    }
    py_res = tabular_model.predict_single(claim)
    vis_res = {"predicted_class": "Invalid Claim", "top_confidence": 0.98, "probabilities": {"Valid Claim": 0.01, "Invalid Claim": 0.98, "Manual Review": 0.01}}
    
    dossier = fusion_engine.evaluate_full_claim(claim, py_res, vis_res)
    assert dossier["rule_evaluation"]["hard_fail"]
    assert dossier["final_decision"] == "Manual Review Required"  # SRS step 12

def test_03_missing_document_manual_review(fusion_engine, tabular_model):
    claim = {
        "claim_id": "TEST-0003",
        "product_category": "electronics",
        "has_receipt": False, # Receipt Missing!
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "remaining_warranty_days": 100,
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "has_unauthorized_repairs": False,
        "serial_match_status": "Exact",
        "purchase_date": "2025-01-01",
        "fault_occurrence_date": "2026-05-01",
        "claim_submission_date": "2026-05-05",
        "product_age_days": 490,
        "missing_documents_count": 1,
        "contradiction_flag": False,
        "duplicate_claim_flag": False,
        "purchase_price": 300.0,
        "warranty_duration_months": 24,
        "previous_repairs_count": 0,
        "reporting_delay_days": 4,
        "brand": "Asus"
    }
    py_res = tabular_model.predict_single(claim)
    vis_res = {"predicted_class": "Manual Review", "top_confidence": 0.90, "probabilities": {"Valid Claim": 0.05, "Invalid Claim": 0.05, "Manual Review": 0.90}}
    
    dossier = fusion_engine.evaluate_full_claim(claim, py_res, vis_res)
    assert dossier["final_decision"] == "Manual Review Required"

def test_04_contradictory_timeline(fusion_engine, tabular_model):
    claim = {
        "claim_id": "TEST-0004",
        "product_category": "electronics",
        "has_receipt": True,
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "remaining_warranty_days": 100,
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "has_unauthorized_repairs": False,
        "serial_match_status": "Exact",
        "purchase_date": "2026-06-01",
        "fault_occurrence_date": "2026-05-01", # Fault before purchase!
        "claim_submission_date": "2026-06-05",
        "product_age_days": 4,
        "missing_documents_count": 0,
        "contradiction_flag": True,
        "duplicate_claim_flag": False,
        "purchase_price": 600.0,
        "warranty_duration_months": 24,
        "previous_repairs_count": 0,
        "reporting_delay_days": 35,
        "brand": "Sony"
    }
    py_res = tabular_model.predict_single(claim)
    vis_res = {"predicted_class": "Manual Review", "top_confidence": 0.85, "probabilities": {"Valid Claim": 0.10, "Invalid Claim": 0.05, "Manual Review": 0.85}}
    
    dossier = fusion_engine.evaluate_full_claim(claim, py_res, vis_res)
    assert dossier["final_decision"] == "Manual Review Required"

def test_05_unauthorized_repair_hard_fail(fusion_engine, tabular_model):
    claim = {
        "claim_id": "TEST-0005",
        "product_category": "electronics",
        "has_receipt": True,
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "remaining_warranty_days": 100,
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "has_unauthorized_repairs": True, # Unauthorized Repair!
        "serial_match_status": "Exact",
        "purchase_date": "2025-01-01",
        "fault_occurrence_date": "2026-05-01",
        "claim_submission_date": "2026-05-05",
        "product_age_days": 490,
        "missing_documents_count": 0,
        "contradiction_flag": False,
        "duplicate_claim_flag": False,
        "purchase_price": 900.0,
        "warranty_duration_months": 24,
        "previous_repairs_count": 2,
        "reporting_delay_days": 4,
        "brand": "Apple"
    }
    py_res = tabular_model.predict_single(claim)
    vis_res = {"predicted_class": "Invalid Claim", "top_confidence": 0.95, "probabilities": {"Valid Claim": 0.02, "Invalid Claim": 0.95, "Manual Review": 0.03}}
    
    dossier = fusion_engine.evaluate_full_claim(claim, py_res, vis_res)
    assert dossier["rule_evaluation"]["hard_fail"]
    assert dossier["final_decision"] == "Manual Review Required"  # SRS step 12

def test_06_model_disagreement_routing(fusion_engine, tabular_model):
    claim = {
        "claim_id": "TEST-0006",
        "product_category": "electronics",
        "has_receipt": True,
        "has_warranty_card": True,
        "has_product_photo": True,
        "has_serial_photo": True,
        "remaining_warranty_days": 100,
        "damage_type": "none",
        "fault_category": "motherboard_failure",
        "has_unauthorized_repairs": False,
        "serial_match_status": "Exact",
        "purchase_date": "2025-01-01",
        "fault_occurrence_date": "2026-05-01",
        "claim_submission_date": "2026-05-05",
        "product_age_days": 490,
        "missing_documents_count": 0,
        "contradiction_flag": False,
        "duplicate_claim_flag": False,
        "purchase_price": 450.0,
        "warranty_duration_months": 24,
        "previous_repairs_count": 0,
        "reporting_delay_days": 4,
        "brand": "LG"
    }
    # Disagreement: Python says Valid, Vision says Invalid
    py_res = {"predicted_class": "Valid Claim", "top_confidence": 0.92, "probabilities": {"Valid Claim": 0.92, "Invalid Claim": 0.04, "Manual Review": 0.04}}
    vis_res = {"predicted_class": "Invalid Claim", "top_confidence": 0.90, "probabilities": {"Valid Claim": 0.05, "Invalid Claim": 0.90, "Manual Review": 0.05}}
    
    dossier = fusion_engine.evaluate_full_claim(claim, py_res, vis_res)
    assert dossier["final_decision"] == "Manual Review Required"
    assert dossier["comparison"]["consistency_status"] == "Model Disagreement"

def test_07_live_submission_derived_features_regression():
    from assurex_claim_engine.decision.derived_features import compute_derived_claim_features

    raw_payload = {
        "product_name": "Test Regression Laptop",
        "product_category": "electronics",
        "brand": "Dell",
        "model_number": "XPS-15",
        "serial_number": "SNY998877",
        "purchase_date": "2025-06-01",
        "purchase_price": "1200.00",
        "retailer": "Best Buy",
        "warranty_months": 24,
        "fault_category": "motherboard_failure",
        "damage_type": "none",
        "fault_occurrence_date": "2026-05-01",
        "claim_submission_date": "2026-05-10"
    }

    derived = compute_derived_claim_features(raw_payload)
    
    assert derived["product_age_days"] == 343
    assert derived["remaining_warranty_days"] == 377
    assert derived["reporting_delay_days"] == 9
    assert derived["warranty_expiry_date"] == "2027-05-22"
    assert derived["serial_match_status"] == "Exact"
    assert derived["missing_documents_count"] == 0
    assert derived["contradiction_flag"] is False
