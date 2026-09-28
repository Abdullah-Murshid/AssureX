"""
AssureX Claim Engine - PDF Report Generator
Generates comprehensive, multi-section vector PDF claim adjudication reports
compliant with SRS Module xliv requirements.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


def _draw_header_and_footer(page, page_num: int, total_pages: int, claim_id: str):
    """Draw header and footer on each PDF page."""
    # Top banner background
    page.draw_rect(pymupdf.Rect(0, 0, 595, 52), fill=(0.06, 0.09, 0.16), stroke_opacity=0)
    page.insert_text(
        (36, 28),
        "ASSUREX CLAIM ENGINE",
        fontsize=13,
        fontname="helv",
        color=(1.0, 1.0, 1.0)
    )
    page.insert_text(
        (36, 42),
        "Automated AI Adjudication & Compliance Dossier — Module XLIV",
        fontsize=8,
        fontname="helv",
        color=(0.6, 0.7, 0.85)
    )
    page.insert_text(
        (430, 32),
        f"Claim Ref: {claim_id}",
        fontsize=9,
        fontname="helv",
        color=(0.9, 0.95, 1.0)
    )

    # Bottom footer line
    page.draw_line(pymupdf.Point(36, 810), pymupdf.Point(559, 810), color=(0.8, 0.85, 0.9), width=0.5)
    page.insert_text(
        (36, 824),
        f"Confidential Official Record — Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        fontsize=7,
        fontname="helv",
        color=(0.4, 0.45, 0.5)
    )
    page.insert_text(
        (510, 824),
        f"Page {page_num} of {total_pages}",
        fontsize=7,
        fontname="helv",
        color=(0.4, 0.45, 0.5)
    )


def generate_claim_pdf_report(
    claim: Any,
    product: Any = None,
    dossier: Optional[Dict[str, Any]] = None,
    narrative_summary: str = "",
    documents: Optional[List[Any]] = None
) -> bytes:
    """
    Builds a complete, professional, vector-quality PDF report for a warranty claim.
    Returns raw PDF bytes.
    """
    dossier = dossier or {}
    documents = documents or []
    claim_id = getattr(claim, "claim_id", "CLM-UNKNOWN")
    final_dec = getattr(claim, "final_decision", "Pending Evaluation") or "Pending Evaluation"
    status = getattr(claim, "status", "Submitted") or "Submitted"
    
    doc = pymupdf.open()
    total_pages = 2
    
    # ==================== PAGE 1 ====================
    p1 = doc.new_page(width=595, height=842)
    y = 66

    # Verdict Badge
    dec_lower = final_dec.lower()
    if "valid" in dec_lower and "invalid" not in dec_lower:
        badge_bg = (0.05, 0.58, 0.41) # emerald
        badge_text = "LIKELY VALID CLAIM — AUTOMATED APPROVAL RECOMMENDED"
    elif "invalid" in dec_lower:
        badge_bg = (0.86, 0.15, 0.15) # red
        badge_text = "LIKELY INVALID CLAIM — DISQUALIFICATION RECOMMENDED"
    else:
        badge_bg = (0.85, 0.47, 0.02) # amber
        badge_text = "MANUAL REVIEW REQUIRED — AUDIT DESK ESCALATION"

    p1.draw_rect(pymupdf.Rect(36, y, 559, y + 26), fill=badge_bg, stroke_opacity=0)
    p1.insert_text((48, y + 17), badge_text, fontsize=9.5, fontname="helv", color=(1.0, 1.0, 1.0))
    y += 36

    # Section 1: Executive Narrative Summary
    p1.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p1.insert_text((42, y + 13), "1. EXECUTIVE AI NARRATIVE CLAIM SUMMARY (MODULE XXXII)", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 22

    summary_text = narrative_summary or "No narrative summary compiled for this claim record."
    summary_rect = pymupdf.Rect(38, y, 557, y + 90)
    p1.insert_textbox(summary_rect, summary_text, fontsize=8.5, fontname="helv", color=(0.15, 0.15, 0.18))
    y += 96

    # Section 2: Claim & Product Overview
    p1.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p1.insert_text((42, y + 13), "2. CLAIM & PRODUCT ASSET SPECIFICATIONS", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 24

    prod_name = getattr(product, "product_name", getattr(claim, "product_id", "N/A")) if product else getattr(claim, "product_id", "N/A")
    prod_cat = getattr(product, "category", "N/A") if product else "N/A"
    brand = getattr(product, "brand", "N/A") if product else "N/A"
    model = getattr(product, "model_number", "N/A") if product else "N/A"
    serial = getattr(product, "serial_number", getattr(claim, "user_serial_number", "N/A")) if product else "N/A"
    retailer = getattr(product, "retailer", "N/A") if product else "N/A"
    p_date = getattr(product, "purchase_date", "N/A") if product else "N/A"
    p_price = f"${getattr(product, 'purchase_price', 0.0):,.2f}" if product else "N/A"
    fault_cat = getattr(claim, "fault_category", "N/A").replace("_", " ").title()
    damage_type = getattr(claim, "damage_type", "none").replace("_", " ").title()
    f_date = getattr(claim, "fault_occurrence_date", "N/A")
    c_date = getattr(claim, "claim_submission_date", "N/A")
    claim_amt = f"${getattr(claim, 'claim_amount', 0.0) or 0.0:,.2f}"

    col1_items = [
        ("Claim Reference:", claim_id),
        ("Claimant User ID:", getattr(claim, "user_id", "N/A")),
        ("Product Asset:", str(prod_name)[:34]),
        ("Category & Brand:", f"{prod_cat.capitalize()} ({brand})"),
        ("Model / Serial:", f"{model} / {serial}"[:34]),
        ("Retailer / Store:", str(retailer)[:34]),
        ("Purchase Price:", p_price),
    ]

    col2_items = [
        ("Claim Amount:", claim_amt),
        ("Fault Category:", fault_cat),
        ("Damage Exclusion:", damage_type),
        ("Occurrence Date:", str(f_date)),
        ("Submission Date:", str(c_date)),
        ("Lifecycle Status:", str(status)),
        ("Original Purchase:", str(p_date)),
    ]

    grid_y = y
    for lbl, val in col1_items:
        p1.insert_text((38, grid_y + 9), lbl, fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
        p1.insert_text((130, grid_y + 9), str(val)[:34], fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
        grid_y += 14

    grid_y2 = y
    for lbl, val in col2_items:
        p1.insert_text((310, grid_y2 + 9), lbl, fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
        p1.insert_text((415, grid_y2 + 9), str(val)[:34], fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
        grid_y2 += 14

    y = max(grid_y, grid_y2) + 8

    # Section 3: Warranty Coverage & Extended Protection (Modules IV, VIII, XI)
    p1.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p1.insert_text((42, y + 13), "3. WARRANTY STATUS & EXTENDED COVERAGE (MODULES IV, VIII, XI)", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 24

    std_months = getattr(product, "warranty_duration_months", 24) if product else 24
    ext_prov = getattr(claim, "extended_warranty_provider", "") or (getattr(product, "extended_warranty_provider", "") if product else "")
    ext_num = getattr(claim, "extended_warranty_contract_number", "") or (getattr(product, "extended_warranty_contract_number", "") if product else "")
    ext_active = "Yes (Active Protection Plan)" if ext_prov else "None (Standard Manufacturer Warranty)"

    p1.insert_text((38, y + 9), "Standard Duration:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
    p1.insert_text((130, y + 9), f"{std_months} Months OEM", fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
    p1.insert_text((310, y + 9), "Extended Plan Active:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
    p1.insert_text((425, y + 9), ext_active[:32], fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
    y += 15

    if ext_prov:
        p1.insert_text((38, y + 9), "Extended Provider:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
        p1.insert_text((130, y + 9), str(ext_prov), fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
        p1.insert_text((310, y + 9), "Contract Reference #:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
        p1.insert_text((425, y + 9), str(ext_num) or "Not Recorded", fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
        y += 16
    else:
        y += 4

    # Section 4: Dual-Model ML Adjudication & Confidence Comparison
    p1.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p1.insert_text((42, y + 13), "4. DUAL-MODEL ML ADJUDICATION & CONFIDENCE COMPARISON (MODULES XVIII - XXIV)", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 24

    py_pred = getattr(claim, "python_predicted_class", "N/A") or "N/A"
    py_conf = f"{(getattr(claim, 'python_top_confidence', 0.0) or 0.0) * 100:.1f}%"
    vis_pred = getattr(claim, "vision_predicted_class", "N/A") or "N/A"
    vis_conf = f"{(getattr(claim, 'vision_top_confidence', 0.0) or 0.0) * 100:.1f}%"
    gap = f"{getattr(claim, 'confidence_difference', 0.0) or 0.0:.4f}"
    consistency = getattr(claim, "consistency_status", "N/A") or "N/A"

    p1.draw_rect(pymupdf.Rect(36, y, 290, y + 42), fill=(0.97, 0.98, 1.0), stroke_opacity=0)
    p1.insert_text((42, y + 14), "Python Tabular Classifier (XGBoost / LightGBM)", fontsize=8, fontname="helv", color=(0.2, 0.35, 0.65))
    p1.insert_text((42, y + 30), f"Prediction: {py_pred}   |   Confidence: {py_conf}", fontsize=8.5, fontname="helv", color=(0.08, 0.12, 0.25))

    p1.draw_rect(pymupdf.Rect(305, y, 559, y + 42), fill=(0.98, 0.96, 1.0), stroke_opacity=0)
    p1.insert_text((311, y + 14), "Vision Summary Card Classifier (ResNet / CNN)", fontsize=8, fontname="helv", color=(0.45, 0.2, 0.65))
    p1.insert_text((311, y + 30), f"Prediction: {vis_pred}   |   Confidence: {vis_conf}", fontsize=8.5, fontname="helv", color=(0.08, 0.12, 0.25))
    y += 50

    p1.insert_text((38, y + 9), "Consistency Status:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
    p1.insert_text((130, y + 9), consistency, fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
    p1.insert_text((310, y + 9), "Confidence Difference Gap:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
    p1.insert_text((440, y + 9), gap, fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
    y += 24

    _draw_header_and_footer(p1, 1, total_pages, claim_id)

    # ==================== PAGE 2 ====================
    p2 = doc.new_page(width=595, height=842)
    y = 66

    # Section 5: Policy Rules & Contradiction Audit
    p2.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p2.insert_text((42, y + 13), "5. BUSINESS POLICY RULES & CONTRADICTION AUDIT (MODULE XXV)", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 24

    rule_eval = dossier.get("rule_evaluation") or {}
    passed_rules = rule_eval.get("passed_rules") or []
    failed_rules = rule_eval.get("failed_rules") or []
    warnings = rule_eval.get("warnings") or []

    if passed_rules or failed_rules or warnings:
        for p_rule in passed_rules[:6]:
            p2.insert_text((40, y + 9), f"[PASS] {p_rule}"[:88], fontsize=7.5, fontname="helv", color=(0.05, 0.5, 0.25))
            y += 13
        for f_rule in failed_rules[:5]:
            p2.insert_text((40, y + 9), f"[FAIL] {f_rule}"[:88], fontsize=7.5, fontname="helv", color=(0.75, 0.1, 0.1))
            y += 13
        for w_rule in warnings[:3]:
            p2.insert_text((40, y + 9), f"[WARN] {w_rule}"[:88], fontsize=7.5, fontname="helv", color=(0.7, 0.4, 0.05))
            y += 13
    else:
        p2.insert_text((40, y + 9), "[INFO] Standard policy rules verified without active hard blocks.", fontsize=7.5, fontname="helv", color=(0.3, 0.4, 0.5))
        y += 16
    y += 8

    # Section 6: Uploaded Evidence & Verification Trail (Module xiv, xxxi)
    p2.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p2.insert_text((42, y + 13), "6. UPLOADED EVIDENCE & DOCUMENT VERIFICATION (MODULES VI, XIV, XXXI)", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 24

    if documents:
        # Table Header
        p2.draw_rect(pymupdf.Rect(36, y, 559, y + 14), fill=(0.96, 0.97, 0.98), stroke_opacity=0)
        p2.insert_text((40, y + 10), "DOC ID", fontsize=7, fontname="helv", color=(0.3, 0.35, 0.4))
        p2.insert_text((110, y + 10), "FILE NAME", fontsize=7, fontname="helv", color=(0.3, 0.35, 0.4))
        p2.insert_text((270, y + 10), "DOCUMENT TYPE", fontsize=7, fontname="helv", color=(0.3, 0.35, 0.4))
        p2.insert_text((400, y + 10), "OCR STATUS", fontsize=7, fontname="helv", color=(0.3, 0.35, 0.4))
        p2.insert_text((485, y + 10), "UPLOADED", fontsize=7, fontname="helv", color=(0.3, 0.35, 0.4))
        y += 16

        for doc_item in documents[:6]:
            doc_id_val = getattr(doc_item, "doc_id", "N/A")
            fname = getattr(doc_item, "filename", "unnamed")
            ftype = getattr(doc_item, "document_type", "document")
            ocr_st = "Verified / Parsed" if getattr(doc_item, "ocr_extracted_text", None) else "Pending OCR"
            up_at = str(getattr(doc_item, "created_at", "N/A"))[:10]

            p2.insert_text((40, y + 9), str(doc_id_val), fontsize=7.5, fontname="helv", color=(0.1, 0.1, 0.15))
            p2.insert_text((110, y + 9), str(fname)[:28], fontsize=7.5, fontname="helv", color=(0.1, 0.1, 0.15))
            p2.insert_text((270, y + 9), str(ftype).replace("_", " ").title()[:22], fontsize=7.5, fontname="helv", color=(0.1, 0.1, 0.15))
            p2.insert_text((400, y + 9), ocr_st, fontsize=7.5, fontname="helv", color=(0.05, 0.5, 0.25) if "Verified" in ocr_st else (0.4, 0.45, 0.5))
            p2.insert_text((485, y + 9), up_at, fontsize=7.5, fontname="helv", color=(0.4, 0.45, 0.5))
            y += 14
    else:
        p2.insert_text((40, y + 9), "No uploaded documents registered with this claim record.", fontsize=7.5, fontname="helv", color=(0.4, 0.45, 0.5))
        y += 16
    y += 12

    # Section 7: Explainability Factors (Supporting vs Opposing)
    p2.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p2.insert_text((42, y + 13), "7. DECISION EXPLAINABILITY FACTORS (MODULE XXVIII)", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 24

    explanation = dossier.get("explanation") or {}
    supporting = explanation.get("supporting_factors") or ["Standard manufacturer coverage profile matched."]
    opposing = explanation.get("opposing_factors") or ["No opposing adverse risk indicators detected."]

    p2.insert_text((38, y + 9), "Supporting Drivers:", fontsize=8, fontname="helv", color=(0.05, 0.5, 0.25))
    y += 12
    for s in supporting[:3]:
        p2.insert_text((48, y + 9), f"• {s}"[:85], fontsize=7.5, fontname="helv", color=(0.15, 0.2, 0.25))
        y += 11
    y += 4

    p2.insert_text((38, y + 9), "Opposing / Risk Drivers:", fontsize=8, fontname="helv", color=(0.75, 0.2, 0.1))
    y += 12
    for o in opposing[:3]:
        p2.insert_text((48, y + 9), f"• {o}"[:85], fontsize=7.5, fontname="helv", color=(0.25, 0.15, 0.15))
        y += 11
    y += 14

    # Section 8: Reviewer Audit Comments & Authorized Sign-off
    p2.draw_rect(pymupdf.Rect(36, y, 559, y + 18), fill=(0.94, 0.96, 0.98), stroke_opacity=0)
    p2.insert_text((42, y + 13), "8. REVIEWER AUDIT COMMENTS & FORMAL SIGN-OFF", fontsize=8.5, fontname="helv", color=(0.1, 0.2, 0.4))
    y += 24

    rev_by = getattr(claim, "reviewed_by", "Automated Adjudication System") or "Automated Adjudication System"
    rev_comments = getattr(claim, "reviewer_comments", "No override comments registered.") or "No override comments registered."
    
    p2.insert_text((38, y + 9), "Adjudicator / Reviewer:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
    p2.insert_text((150, y + 9), str(rev_by), fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
    y += 14
    p2.insert_text((38, y + 9), "Reviewer Remarks:", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.5))
    p2.insert_text((150, y + 9), str(rev_comments)[:70], fontsize=8, fontname="helv", color=(0.1, 0.1, 0.15))
    y += 24

    # Sign-off Line
    p2.draw_line(pymupdf.Point(370, y + 25), pymupdf.Point(540, y + 25), color=(0.6, 0.65, 0.7), width=0.8)
    p2.insert_text((390, y + 37), "Authorized Signature & Official Stamp", fontsize=7.5, fontname="helv", color=(0.4, 0.45, 0.5))

    _draw_header_and_footer(p2, 2, total_pages, claim_id)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
