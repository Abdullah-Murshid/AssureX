"""
Tests for central settings loader and configurable thresholds in comparison engine.
"""

import os
import yaml
import pytest
from unittest.mock import patch
import config.settings_loader as sl
from assurex_claim_engine.decision.comparison import DualModelComparator


def test_default_settings_loaded():
    """Verify default thresholds are correctly loaded."""
    settings = sl.get_settings()
    assert settings["uncertainty_threshold"] == 0.60
    assert settings["strong_match_threshold"] == 0.10
    assert settings["acceptable_match_threshold"] == 0.25
    assert settings["pdf_render_dpi"] == 200


def test_temp_config_override(tmp_path):
    """Verify changing a threshold in a temporary config alters comparison behavior."""
    # Write custom config
    temp_config = tmp_path / "custom_settings.yaml"
    custom_data = {
        "model_version": "v2-custom",
        "uncertainty_threshold": 0.85, # higher threshold!
        "strong_match_threshold": 0.05,
        "acceptable_match_threshold": 0.15,
        "pdf_render_dpi": 300,
    }
    with open(temp_config, "w", encoding="utf-8") as f:
        yaml.dump(custom_data, f)

    # Clear cache and patch CONFIG_PATH
    sl.get_settings.cache_clear()
    with patch("config.settings_loader.CONFIG_PATH", str(temp_config)):
        loaded = sl.get_settings()
        assert loaded["uncertainty_threshold"] == 0.85
        assert loaded["strong_match_threshold"] == 0.05

        # With 0.75 confidence and default threshold (0.60), this would be valid match.
        # But with 0.85 threshold, it must become 'Uncertain Result'.
        py_res = {"predicted_class": "Valid Claim", "top_confidence": 0.75, "probabilities": {}}
        vis_res = {"predicted_class": "Valid Claim", "top_confidence": 0.75, "probabilities": {}}
        cmp_result = DualModelComparator.compare_models(py_res, vis_res)

        assert cmp_result["consistency_status"] == "Uncertain Result"

    # Reset cache back to original
    sl.get_settings.cache_clear()
    orig = sl.get_settings()
    assert orig["uncertainty_threshold"] == 0.60
