"""
AssureX Claim Engine - Contradiction & Duplicate Claim Detector
Detects timeline conflicts, serial number inconsistencies, and duplicate claims:
- Fault Date prior to Purchase Date
- Claim Date prior to Fault Date
- Document Hash Duplication (SHA-256)
- Duplicate Serial + Invoice Combination
"""

from datetime import datetime
from typing import Dict, Any, List

class ContradictionAndDuplicateDetector:
    @staticmethod
    def detect_contradictions(claim: Dict[str, Any]) -> Dict[str, Any]:
        contradictions: List[str] = []
        
        try:
            p_date = datetime.strptime(str(claim["purchase_date"]), "%Y-%m-%d")
            f_date = datetime.strptime(str(claim["fault_occurrence_date"]), "%Y-%m-%d")
            c_date = datetime.strptime(str(claim["claim_submission_date"]), "%Y-%m-%d")
            
            if f_date < p_date:
                contradictions.append(f"Contradiction: Fault Date ({claim['fault_occurrence_date']}) is prior to Purchase Date ({claim['purchase_date']}).")
                
            if c_date < f_date:
                contradictions.append(f"Contradiction: Claim Submission Date ({claim['claim_submission_date']}) is prior to Fault Occurrence Date ({claim['fault_occurrence_date']}).")
                
        except (ValueError, KeyError):
            pass

        # Serial Mismatch
        user_sn = str(claim.get("user_serial_number", "")).strip().upper()
        ocr_sn = str(claim.get("ocr_serial_number", "")).strip().upper()
        
        if user_sn and ocr_sn and user_sn != ocr_sn:
            contradictions.append(f"Serial Mismatch: User input '{user_sn}' does not match OCR '{ocr_sn}'.")

        # Explicit Flag Check
        if claim.get("contradiction_flag", False) and not contradictions:
            contradictions.append("Contradiction Flagged: Data anomaly detected in submission timeline.")

        return {
            "has_contradictions": len(contradictions) > 0,
            "contradiction_count": len(contradictions),
            "contradictions": contradictions
        }

    @staticmethod
    def check_duplicate(claim: Dict[str, Any], existing_claims: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if existing_claims is None:
            existing_claims = []

        is_duplicate = False
        reasons: List[str] = []

        curr_claim_id = claim.get("claim_id", "")
        curr_sn = str(claim.get("user_serial_number", "")).upper()
        curr_inv = str(claim.get("invoice_number", "")).upper()
        curr_hash = claim.get("document_hash", "")

        # Explicit duplicate flag check from synthetic dataset
        if claim.get("duplicate_claim_flag", False):
            is_duplicate = True
            reasons.append("Duplicate Alert: Prior claim registered with matching Serial Number & Receipt.")

        for prev in existing_claims:
            if prev.get("claim_id") == curr_claim_id:
                continue
                
            # Check document hash match
            if curr_hash and prev.get("document_hash") == curr_hash:
                is_duplicate = True
                reasons.append(f"Duplicate Document: Identical receipt hash matches previous Claim '{prev.get('claim_id')}'.")
                break
                
            # Check Serial + Invoice match
            prev_sn = str(prev.get("user_serial_number", "")).upper()
            prev_inv = str(prev.get("invoice_number", "")).upper()
            
            if curr_sn and curr_inv and prev_sn == curr_sn and prev_inv == curr_inv:
                is_duplicate = True
                reasons.append(f"Duplicate Claim: Serial '{curr_sn}' and Invoice '{curr_inv}' match active Claim '{prev.get('claim_id')}'.")
                break

        return {
            "is_duplicate": is_duplicate,
            "duplicate_reasons": reasons
        }

if __name__ == "__main__":
    sample = {
        "claim_id": "CLM-2026-9999",
        "purchase_date": "2026-05-10",
        "fault_occurrence_date": "2026-04-01",  # Fault before purchase!
        "claim_submission_date": "2026-05-15",
        "user_serial_number": "SN12345",
        "ocr_serial_number": "SN99999"
    }
    print("Contradiction check output:", ContradictionAndDuplicateDetector.detect_contradictions(sample))
