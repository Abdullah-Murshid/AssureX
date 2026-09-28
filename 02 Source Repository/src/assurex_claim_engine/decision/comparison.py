"""
AssureX Claim Engine - Dual Model Comparison Engine
Calculates confidence differences and evaluates agreement status between:
1. Python Tabular ML Model
2. Visual Claim Summary Card Image Model (Google Teachable Machine / PyTorch Vision Model)

Implements SRS Step 10 & Functional Requirements xxii - xxiv:
- Confidence Difference = | Python Top Confidence - Vision Top Confidence |
- Model Consistency Status: Strong Match, Acceptable Match, Weak Match, Model Disagreement, Uncertain Result
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from typing import Dict, Any

try:
    from config.settings_loader import get
except ImportError:
    def get(key, default=None):  # fallback if config not on path
        return {"uncertainty_threshold": 0.60,
                "strong_match_threshold": 0.10,
                "acceptable_match_threshold": 0.25}.get(key, default)


class DualModelComparator:
    @staticmethod
    def compare_models(python_result: Dict[str, Any], vision_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares predictions and confidence scores from both models.
        
        python_result format:
            {"predicted_class": "Valid Claim", "top_confidence": 0.92, "probabilities": {...}}
            
        vision_result format:
            {"predicted_class": "Valid Claim", "top_confidence": 0.88, "probabilities": {...}}
        """
        # Load thresholds from config/settings.yaml (cached)
        uncertainty_thresh = get("uncertainty_threshold", 0.60)
        strong_thresh = get("strong_match_threshold", 0.10)
        acceptable_thresh = get("acceptable_match_threshold", 0.25)

        py_class = python_result["predicted_class"]
        py_conf = float(python_result["top_confidence"])
        
        vis_class = vision_result["predicted_class"]
        vis_conf = float(vision_result["top_confidence"])
        
        classes_match = (py_class == vis_class)
        confidence_diff = round(abs(py_conf - vis_conf), 4)
        
        # Determine Consistency Status
        if py_conf < uncertainty_thresh or vis_conf < uncertainty_thresh:
            status = "Uncertain Result"
            description = f"One or both models produced low-confidence predictions (< {uncertainty_thresh})."
        elif not classes_match:
            status = "Model Disagreement"
            description = f"Models predicted different classes (Python: '{py_class}', Vision: '{vis_class}')."
        elif confidence_diff < strong_thresh:
            status = "Strong Match"
            description = f"Both models agree on the class with a very close confidence score (diff < {strong_thresh})."
        elif confidence_diff <= acceptable_thresh:
            status = "Acceptable Match"
            description = f"Both models agree on the class with acceptable confidence alignment (diff {strong_thresh} - {acceptable_thresh})."
        else:
            status = "Weak Match"
            description = f"Both models agree on class but exhibit a large confidence disparity (diff > {acceptable_thresh})."
            
        return {
            "classes_match": classes_match,
            "python_predicted_class": py_class,
            "python_top_confidence": py_conf,
            "python_probabilities": python_result.get("probabilities", {}),
            "vision_predicted_class": vis_class,
            "vision_top_confidence": vis_conf,
            "vision_probabilities": vision_result.get("probabilities", {}),
            "confidence_difference": confidence_diff,
            "consistency_status": status,
            "status_description": description
        }

if __name__ == "__main__":
    # Quick sanity test
    py_res = {"predicted_class": "Valid Claim", "top_confidence": 0.94, "probabilities": {"Valid Claim": 0.94, "Invalid Claim": 0.04, "Manual Review": 0.02}}
    vis_res = {"predicted_class": "Valid Claim", "top_confidence": 0.89, "probabilities": {"Valid Claim": 0.89, "Invalid Claim": 0.08, "Manual Review": 0.03}}
    
    comp = DualModelComparator.compare_models(py_res, vis_res)
    print("Sanity Check Comparison Result:")
    print(comp)

