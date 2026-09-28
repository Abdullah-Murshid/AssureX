"""
AssureX Claim Engine - Synthetic Dataset Generator v2
Generates 1,500 realistic, structured claim records with overlapping feature spaces
and scenario templates to replace trivial if-else memorization:
- 500 Valid Claim
- 500 Invalid Claim
- 500 Manual Review

Stratified 70/15/15 Split:
- 1,050 Train (350 Valid, 350 Invalid, 350 Manual Review)
- 225 Val (75 Valid, 75 Invalid, 75 Manual Review)
- 225 Test (75 Valid, 75 Invalid, 75 Manual Review)
"""

import os
import random
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from assurex_claim_engine.decision.derived_features import compute_derived_claim_features

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

DATA_V2_DIR = "data/v2"
PROCESSED_DIR = os.path.join(DATA_V2_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

CATEGORIES = {
    "electronics": {
        "brands": ["Sony", "Samsung", "Apple", "Dell", "LG", "Asus", "Bose"],
        "models": ["Pro-X100", "UltraView-55", "MacBook-Air-M2", "XPS-15", "OLED-C2", "QuietComfort-45"],
        "faults": ["screen_flicker_defect", "motherboard_failure", "battery_charging_failure", "audio_speaker_malfunction", "overheating_shutdown"],
        "exclusions": ["liquid_spill_damage", "physical_drop_crack", "unauthorized_repair_attempt", "normal_cosmetic_wear"],
        "ambiguous_faults": ["intermittent_flicker_wear", "power_surge_flicker", "audio_distortion_scratch"],
        "warranty_months": 24,
        "grace_days": 15,
        "deadline_days": 30
    },
    "appliances": {
        "brands": ["Whirlpool", "Bosch", "Panasonic", "Haier", "GE Appliances", "Samsung"],
        "models": ["FrostFree-500L", "EcoSilence-Drive", "Inverter-AC-1.5T", "Convection-Microwave-30L"],
        "faults": ["compressor_failure", "motor_burnout", "cooling_leakage", "control_board_malfunction", "thermostat_failure"],
        "exclusions": ["voltage_fluctuation_damage", "improper_installation", "pest_infestation_damage", "commercial_use_overload"],
        "ambiguous_faults": ["seal_gasket_wear", "minor_fan_vibration", "mild_frost_accumulation"],
        "warranty_months": 36,
        "grace_days": 15,
        "deadline_days": 30
    },
    "automotive": {
        "brands": ["Bosch", "Garmin", "Pioneer", "Exide", "Varta", "Kenwood"],
        "models": ["Matrix-Battery-12V", "GPS-DriveSmart-65", "AVH-Z5200BT-Infotainment", "ProStarter-80A"],
        "faults": ["battery_dead_cell", "alternator_failure", "starter_motor_defect", "gps_module_failure", "sensor_malfunction"],
        "exclusions": ["accident_collision_damage", "racing_track_misuse", "improper_wiring_modifications", "water_submersion"],
        "ambiguous_faults": ["terminal_surface_oxidation", "slow_crank_cold_weather", "gps_antenna_signal_loss"],
        "warranty_months": 12,
        "grace_days": 15,
        "deadline_days": 30
    }
}

RETAILERS = ["Amazon Retail", "Best Buy", "Target", "Walmart", "Direct Brand Store", "TechZone Distributors"]

def random_date(start_date, end_date):
    delta = end_date - start_date
    if delta.days <= 0:
        return start_date
    return start_date + timedelta(days=random.randint(0, delta.days))

def make_ocr_typo(serial_str):
    """Produces realistic 1-character OCR recognition typo."""
    substitutions = {'0': 'O', 'O': '0', '1': 'I', 'I': '1', '5': 'S', 'S': '5', '8': 'B', 'B': '8'}
    chars = list(serial_str)
    for i in range(len(chars) - 1, -1, -1):
        if chars[i] in substitutions:
            chars[i] = substitutions[chars[i]]
            return "".join(chars)
    # Fallback: alter last digit
    if chars[-1].isdigit():
        chars[-1] = str((int(chars[-1]) + 1) % 10)
    else:
        chars[-1] = 'X'
    return "".join(chars)

def generate_claim(claim_id_num, target_class, scenario_type):
    claim_id = f"CLM-2026-{claim_id_num:04d}"
    user_id = f"USR-{random.randint(1000, 9999)}"
    product_id = f"PRD-{random.randint(10000, 99999)}"
    
    cat_key = random.choice(list(CATEGORIES.keys()))
    cat_info = CATEGORIES[cat_key]
    brand = random.choice(cat_info["brands"])
    model_number = random.choice(cat_info["models"])
    
    serial_base = f"{brand[:3].upper()}{random.randint(100000, 999999)}"
    user_serial = serial_base
    ocr_serial = serial_base
    serial_match_status = "Exact"
    
    warranty_months = cat_info["warranty_months"]
    base_now = datetime(2026, 6, 1)
    
    # Baseline dates
    purchase_date = random_date(base_now - timedelta(days=365 * 2), base_now - timedelta(days=60))
    warranty_expiry_date = purchase_date + timedelta(days=30 * warranty_months)
    
    # Standard fault and submission
    fault_date = random_date(purchase_date + timedelta(days=15), warranty_expiry_date - timedelta(days=15))
    submission_date = random_date(fault_date, fault_date + timedelta(days=12))
    
    fault_category = random.choice(cat_info["faults"])
    damage_type = "none"
    previous_repairs = random.randint(0, 1)
    has_unauthorized_repairs = False
    
    has_receipt = True
    has_warranty_card = True
    has_product_photo = True
    has_serial_photo = True
    
    contradiction_flag = False
    duplicate_claim_flag = False
    purchase_price = round(random.uniform(150.0, 1900.0), 2)
    retailer = random.choice(RETAILERS)
    
    # ── SPECIFIC SCENARIO LOGIC ────────────────────────────────────────────────
    if scenario_type == "standard_valid":
        # Clear valid claim
        pass
    
    elif scenario_type == "grace_period_valid":
        # Expired by 1-7 days, within 15-day grace period; clean documentation -> Valid
        submission_date = warranty_expiry_date + timedelta(days=random.randint(1, 7))
        fault_date = submission_date - timedelta(days=random.randint(2, 6))
        previous_repairs = 0
        
    elif scenario_type == "grace_period_manual_review":
        # Expired by 8-14 days (end of grace period) -> Manual Review
        submission_date = warranty_expiry_date + timedelta(days=random.randint(8, 14))
        fault_date = submission_date - timedelta(days=random.randint(3, 8))
        
    elif scenario_type == "grace_period_expired_invalid":
        # Expired by 16-45 days (past grace period) -> Invalid
        submission_date = warranty_expiry_date + timedelta(days=random.randint(16, 45))
        fault_date = submission_date - timedelta(days=random.randint(4, 10))

    elif scenario_type == "near_deadline_valid":
        # Reported at day 26-29 (deadline 30 days) -> Valid
        submission_date = fault_date + timedelta(days=random.randint(26, 29))

    elif scenario_type == "near_deadline_manual_review":
        # Reported at day 31-38 (just over 30-day deadline) -> Manual Review
        submission_date = fault_date + timedelta(days=random.randint(31, 38))

    elif scenario_type == "missing_noncritical_doc_valid":
        # Missing only product photo or serial photo, but receipt & warranty card valid -> Valid (commercial concession)
        if random.random() < 0.5:
            has_product_photo = False
        else:
            has_serial_photo = False
        previous_repairs = 0

    elif scenario_type == "missing_critical_doc_manual_review":
        # Missing receipt or warranty card -> Manual Review
        has_receipt = random.choice([True, False])
        if has_receipt:
            has_warranty_card = False
        has_product_photo = random.choice([True, False])

    elif scenario_type == "ocr_typo_valid":
        # Single-character OCR typo (e.g. 0 vs O), real user serial is exact -> Valid
        ocr_serial = make_ocr_typo(user_serial)
        serial_match_status = "Partial"

    elif scenario_type == "ocr_typo_manual_review":
        # OCR typo with slight ambiguity -> Manual Review
        ocr_serial = make_ocr_typo(user_serial)
        serial_match_status = "Mismatch"

    elif scenario_type == "real_serial_mismatch_invalid":
        # Completely fabricated or different serial -> Invalid
        ocr_serial = f"FAKE{random.randint(100000, 999999)}"
        serial_match_status = "Mismatch"

    elif scenario_type == "ambiguous_damage_manual_review":
        # Ambiguous damage near boundary (e.g. normal wear vs defect) -> Manual Review
        fault_category = random.choice(cat_info["ambiguous_faults"])
        damage_type = "cosmetic_scratch" if random.random() < 0.5 else "none"

    elif scenario_type == "unrelated_unauthorized_repair_manual_review":
        # Minor unauthorized repair (e.g. accessory/case) flagged -> Manual Review
        has_unauthorized_repairs = True
        previous_repairs = 1

    elif scenario_type == "major_unauthorized_repair_invalid":
        # Critical unauthorized repair (component tampering) -> Invalid
        has_unauthorized_repairs = True
        previous_repairs = random.randint(2, 4)

    elif scenario_type == "minor_spelling_contradiction_manual_review":
        # Model name slight spelling variance -> Manual Review
        model_number = model_number + "-RevB"
        contradiction_flag = True

    elif scenario_type == "major_timeline_contradiction_invalid":
        # Fault date prior to purchase date -> Invalid
        contradiction_flag = True
        fault_date = purchase_date - timedelta(days=random.randint(5, 30))
        submission_date = purchase_date + timedelta(days=random.randint(10, 20))

    elif scenario_type == "similar_repeat_claim_manual_review":
        # Recurring repair on similar component -> Manual Review
        duplicate_claim_flag = True
        previous_repairs = 2

    elif scenario_type == "risky_high_cost_manual_review":
        # High purchase price + 3 previous repairs -> Manual Review for inspection
        purchase_price = round(random.uniform(1600.0, 2500.0), 2)
        previous_repairs = 3
        submission_date = fault_date + timedelta(days=random.randint(22, 28))

    elif scenario_type == "standard_excluded_invalid":
        # Clear exclusion (liquid spill, physical crack, collision)
        damage_type = random.choice(cat_info["exclusions"])

    elif scenario_type == "standard_missing_all_manual_review":
        has_receipt = False
        has_warranty_card = False
        has_product_photo = False
        has_serial_photo = False

    raw_record = {
        "claim_id": claim_id,
        "user_id": user_id,
        "product_id": product_id,
        "product_name": f"{brand} {model_number}",
        "product_category": cat_key,
        "brand": brand,
        "model_number": model_number,
        "user_serial_number": user_serial,
        "ocr_serial_number": ocr_serial,
        "serial_match_status": serial_match_status,
        "purchase_date": purchase_date.strftime("%Y-%m-%d"),
        "purchase_price": purchase_price,
        "retailer": retailer,
        "warranty_duration_months": warranty_months,
        "warranty_start_date": purchase_date.strftime("%Y-%m-%d"),
        "warranty_expiry_date": warranty_expiry_date.strftime("%Y-%m-%d"),
        "fault_occurrence_date": fault_date.strftime("%Y-%m-%d"),
        "claim_submission_date": submission_date.strftime("%Y-%m-%d"),
        "fault_category": fault_category,
        "damage_type": damage_type,
        "previous_repairs_count": previous_repairs,
        "has_unauthorized_repairs": has_unauthorized_repairs,
        "has_receipt": has_receipt,
        "has_warranty_card": has_warranty_card,
        "has_product_photo": has_product_photo,
        "has_serial_photo": has_serial_photo,
        "missing_documents_count": missing_docs_count,
        "contradiction_flag": contradiction_flag,
        "duplicate_claim_flag": duplicate_claim_flag
    }
    
    derived = compute_derived_claim_features(raw_record)
    derived["actual_class"] = target_class
    derived["_scenario"] = scenario_type
    return derived

def generate_v2_dataset():
    print("Generating v2 synthetic dataset with overlapping scenarios...")
    
    # 500 Valid Scenarios
    valid_scenarios = (
        ["standard_valid"] * 300 +
        ["grace_period_valid"] * 45 +
        ["near_deadline_valid"] * 45 +
        ["missing_noncritical_doc_valid"] * 55 +
        ["ocr_typo_valid"] * 55
    )
    assert len(valid_scenarios) == 500

    # 500 Invalid Scenarios
    invalid_scenarios = (
        ["standard_excluded_invalid"] * 290 +
        ["grace_period_expired_invalid"] * 65 +
        ["major_unauthorized_repair_invalid"] * 50 +
        ["major_timeline_contradiction_invalid"] * 50 +
        ["real_serial_mismatch_invalid"] * 45
    )
    assert len(invalid_scenarios) == 500

    # 500 Manual Review Scenarios
    manual_scenarios = (
        ["missing_critical_doc_manual_review"] * 100 +
        ["grace_period_manual_review"] * 55 +
        ["near_deadline_manual_review"] * 55 +
        ["ocr_typo_manual_review"] * 55 +
        ["ambiguous_damage_manual_review"] * 55 +
        ["unrelated_unauthorized_repair_manual_review"] * 50 +
        ["minor_spelling_contradiction_manual_review"] * 45 +
        ["similar_repeat_claim_manual_review"] * 45 +
        ["risky_high_cost_manual_review"] * 40
    )
    assert len(manual_scenarios) == 500

    raw_records = []
    
    # Generate balanced records
    for i, scen in enumerate(valid_scenarios):
        raw_records.append(("Valid Claim", scen))
    for i, scen in enumerate(invalid_scenarios):
        raw_records.append(("Invalid Claim", scen))
    for i, scen in enumerate(manual_scenarios):
        raw_records.append(("Manual Review", scen))
        
    random.shuffle(raw_records)
    
    claims = []
    noise_log = []
    
    # Reviewer judgement noise: 4% of records (~60 records)
    # Valid <-> Manual Review, Invalid <-> Manual Review, NEVER Valid <-> Invalid
    noise_indices = set(random.sample(range(1500), k=60))
    
    for idx, (cls_name, scen) in enumerate(raw_records, start=1):
        actual_class = cls_name
        has_noise = False
        orig_class = cls_name
        
        if idx - 1 in noise_indices:
            has_noise = True
            if orig_class == "Valid Claim":
                actual_class = "Manual Review"
            elif orig_class == "Invalid Claim":
                actual_class = "Manual Review"
            elif orig_class == "Manual Review":
                actual_class = random.choice(["Valid Claim", "Invalid Claim"])
            noise_log.append({
                "claim_id": f"CLM-2026-{idx:04d}",
                "original_intended_class": orig_class,
                "noisy_reviewer_class": actual_class,
                "scenario": scen
            })
            
        record = generate_claim(idx, actual_class, scen)
        claims.append(record)

    df = pd.DataFrame(claims)
    
    # Save hidden reviewer noise log
    with open(os.path.join(DATA_V2_DIR, "reviewer_noise_log.json"), "w") as f:
        json.dump(noise_log, f, indent=2)

    # Save scenario definitions
    scenario_defs = {
        "Valid Claim Scenarios": [
            "standard_valid: standard covered fault, active warranty, all documents present",
            "grace_period_valid: submitted within 1-7 days past warranty under active grace period with strong evidence",
            "near_deadline_valid: reported at 26-29 days near the 30-day reporting deadline",
            "missing_noncritical_doc_valid: single non-critical photo missing (e.g. serial photo) but verified receipt and invoice",
            "ocr_typo_valid: single-character OCR scan substitution (0 vs O) with authentic underlying hardware serial"
        ],
        "Invalid Claim Scenarios": [
            "standard_excluded_invalid: explicitly excluded damage (liquid spill, physical crack, collision)",
            "grace_period_expired_invalid: claim submitted 16-45 days after warranty expiry (beyond grace period)",
            "major_unauthorized_repair_invalid: multiple unauthorized repairs on core operational components",
            "major_timeline_contradiction_invalid: fault date precedes original retail purchase date",
            "real_serial_mismatch_invalid: completely mismatched serial number indicating fraud or counterfeit hardware"
        ],
        "Manual Review Scenarios": [
            "missing_critical_doc_manual_review: missing primary purchase receipt or official warranty certificate",
            "grace_period_manual_review: claim submitted at the tail boundary of grace period (8-14 days)",
            "near_deadline_manual_review: claim filed just past the 30-day deadline (31-38 days) requiring adjuster discretion",
            "ocr_typo_manual_review: OCR serial mismatch requiring human eyesight verification",
            "ambiguous_damage_manual_review: fault on borderline between normal wear & tear and defective component",
            "unrelated_unauthorized_repair_manual_review: single third-party repair on non-critical component",
            "minor_spelling_contradiction_manual_review: slight discrepancy in model name designation",
            "similar_repeat_claim_manual_review: recurring claim on related component with prior repair history",
            "risky_high_cost_manual_review: high purchase value accompanied by multiple prior warranty claims"
        ]
    }
    with open(os.path.join(DATA_V2_DIR, "scenario_definitions.json"), "w") as f:
        json.dump(scenario_defs, f, indent=2)

    # Ensure exactly 500 per class in final dataset
    counts = df["actual_class"].value_counts().to_dict()
    print("Class distribution before balance correction:", counts)
    
    # Perform exact balancing if noise introduced small class shifts
    target_count = 500
    classes = ["Valid Claim", "Invalid Claim", "Manual Review"]
    
    # Stratified 70/15/15 Split: 1050 train, 225 val, 225 test
    # Per class: 350 train, 75 val, 75 test
    # If counts deviate slightly due to random noise, adjust records without cross-class valid<->invalid flip
    while df["actual_class"].value_counts()["Valid Claim"] != 500 or \
          df["actual_class"].value_counts()["Invalid Claim"] != 500 or \
          df["actual_class"].value_counts()["Manual Review"] != 500:
        counts = df["actual_class"].value_counts().to_dict()
        if counts["Valid Claim"] < 500 and counts["Manual Review"] > 500:
            mr_indices = df[(df["actual_class"] == "Manual Review") & (df["_scenario"].str.contains("valid"))].index
            if len(mr_indices) > 0:
                df.loc[mr_indices[0], "actual_class"] = "Valid Claim"
            else:
                mr_any = df[df["actual_class"] == "Manual Review"].index
                df.loc[mr_any[0], "actual_class"] = "Valid Claim"
        elif counts["Valid Claim"] > 500:
            val_indices = df[(df["actual_class"] == "Valid Claim") & (~df["_scenario"].str.contains("standard"))].index
            df.loc[val_indices[0], "actual_class"] = "Manual Review"
        elif counts["Invalid Claim"] < 500 and counts["Manual Review"] > 500:
            mr_indices = df[(df["actual_class"] == "Manual Review") & (df["_scenario"].str.contains("invalid"))].index
            if len(mr_indices) > 0:
                df.loc[mr_indices[0], "actual_class"] = "Invalid Claim"
            else:
                mr_any = df[df["actual_class"] == "Manual Review"].index
                df.loc[mr_any[0], "actual_class"] = "Invalid Claim"
        elif counts["Invalid Claim"] > 500:
            inv_indices = df[(df["actual_class"] == "Invalid Claim") & (~df["_scenario"].str.contains("standard"))].index
            df.loc[inv_indices[0], "actual_class"] = "Manual Review"
        elif counts["Manual Review"] < 500:
            if counts["Valid Claim"] > 500:
                v_idx = df[df["actual_class"] == "Valid Claim"].index[0]
                df.loc[v_idx, "actual_class"] = "Manual Review"
            elif counts["Invalid Claim"] > 500:
                i_idx = df[df["actual_class"] == "Invalid Claim"].index[0]
                df.loc[i_idx, "actual_class"] = "Manual Review"

    print("Final balanced class counts:", df["actual_class"].value_counts().to_dict())
    
    # Remove internal generator tracking column before saving
    export_df = df.drop(columns=["_scenario"])
    
    # Save full claims dataset
    full_path = os.path.join(PROCESSED_DIR, "claims_dataset.csv")
    export_df.to_csv(full_path, index=False)
    print(f"Saved full dataset to {full_path} ({len(export_df)} records)")

    # Stratified Split 70/15/15: 350/75/75 per class
    train_dfs = []
    val_dfs = []
    test_dfs = []

    for cls in classes:
        cls_df = export_df[export_df["actual_class"] == cls].sample(frac=1, random_state=SEED)
        train_dfs.append(cls_df.iloc[:350])
        val_dfs.append(cls_df.iloc[350:425])
        test_dfs.append(cls_df.iloc[425:500])

    train_df = pd.concat(train_dfs).sample(frac=1, random_state=SEED).reset_index(drop=True)
    val_df = pd.concat(val_dfs).sample(frac=1, random_state=SEED).reset_index(drop=True)
    test_df = pd.concat(test_dfs).sample(frac=1, random_state=SEED).reset_index(drop=True)

    train_df.to_csv(os.path.join(DATA_V2_DIR, "train.csv"), index=False)
    val_df.to_csv(os.path.join(DATA_V2_DIR, "val.csv"), index=False)
    test_df.to_csv(os.path.join(DATA_V2_DIR, "test.csv"), index=False)
    
    print(f"Saved splits: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

    # Copy / update data dictionary
    with open("data/data_dictionary.json", "r") as f:
        data_dict = json.load(f)
    data_dict["version"] = "2.0"
    data_dict["description"] = "AssureX Claim Engine Common Warranty Dataset v2 with overlapping scenario templates and boundary noise."
    with open(os.path.join(DATA_V2_DIR, "data_dictionary.json"), "w") as f:
        json.dump(data_dict, f, indent=2)

    # Compute and save dataset statistics
    stats = {
        "version": "2.0",
        "total_claims": len(export_df),
        "class_distribution": export_df["actual_class"].value_counts().to_dict(),
        "splits": {
            "train": {"total": len(train_df), "distribution": train_df["actual_class"].value_counts().to_dict()},
            "val": {"total": len(val_df), "distribution": val_df["actual_class"].value_counts().to_dict()},
            "test": {"total": len(test_df), "distribution": test_df["actual_class"].value_counts().to_dict()}
        },
        "category_distribution": export_df["product_category"].value_counts().to_dict(),
        "average_purchase_price": round(float(export_df["purchase_price"].mean()), 2),
        "average_product_age_days": round(float(export_df["product_age_days"].mean()), 1),
        "average_reporting_delay_days": round(float(export_df["reporting_delay_days"].mean()), 1),
        "reviewer_noise_records_count": len(noise_log)
    }
    with open(os.path.join(DATA_V2_DIR, "dataset_statistics.json"), "w") as f:
        json.dump(stats, f, indent=2)
        
    print("Dataset statistics written successfully.")

if __name__ == "__main__":
    generate_v2_dataset()
