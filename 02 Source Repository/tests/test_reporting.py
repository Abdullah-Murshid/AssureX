"""
Tests for PDF and printable report generation (Module xliv).
"""

import os
from types import SimpleNamespace
from assurex_claim_engine.reporting.pdf_generator import generate_claim_pdf_report


def test_generate_claim_pdf_report():
    claim = SimpleNamespace(
        claim_id="CLM-2026-TEST01",
        user_id="USR-TEST",
        product_id="PRD-TEST01",
        claim_amount=450.00,
        fault_category="motherboard_failure",
        damage_type="none",
        fault_occurrence_date="2026-03-01",
        claim_submission_date="2026-03-05",
        status="Under Review",
        final_decision="Likely Valid",
        python_predicted_class="Likely Valid",
        python_top_confidence=0.942,
        vision_predicted_class="Likely Valid",
        vision_top_confidence=0.915,
        confidence_difference=0.027,
        consistency_status="Consistent",
        model_version="v2",
        reviewer_comments="Automated checks confirmed authentic receipt and active warranty.",
        reviewed_by="Reviewer Desk",
        extended_warranty_provider="SquareTrade Protection",
        extended_warranty_contract_number="SQ-99210",
    )

    product = SimpleNamespace(
        product_id="PRD-TEST01",
        product_name="Ultra HD Smart TV",
        category="Television",
        brand="Sony",
        model_number="KD-65X85K",
        serial_number="SN-7721890",
        retailer="Best Buy",
        purchase_date="2025-06-15",
        purchase_price=1200.00,
        warranty_duration_months=24,
        extended_warranty_provider="SquareTrade Protection",
        extended_warranty_contract_number="SQ-99210",
    )

    dossier = {
        "rule_evaluation": {
            "passed_rules": ["Claim filed within active warranty window", "No excluded physical damage recorded"],
            "failed_rules": [],
            "warnings": [],
        },
        "explanation": {
            "supporting_factors": ["Receipt OCR verified by retailer", "Low historical defect risk score"],
            "opposing_factors": ["High claim value exceeding $400 threshold"],
        }
    }

    doc = SimpleNamespace(
        doc_id="DOC-001",
        filename="purchase_receipt.pdf",
        document_type="receipt",
        ocr_extracted_text="Purchased from Best Buy on 2025-06-15",
        created_at="2026-03-05",
    )

    narrative = "Claim CLM-2026-TEST01 was filed for Sony Ultra HD Smart TV regarding motherboard failure. Purchase verified via OCR receipt. Policy rules passed."

    pdf_bytes = generate_claim_pdf_report(
        claim=claim,
        product=product,
        dossier=dossier,
        narrative_summary=narrative,
        documents=[doc],
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF files start with %PDF header
    assert pdf_bytes.startswith(b"%PDF")
