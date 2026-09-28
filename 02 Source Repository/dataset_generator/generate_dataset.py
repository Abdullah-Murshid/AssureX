"""
AssureX Claim Engine - Synthetic Dataset Generator
Generates 1,500 realistic, structured claim records with equal class distribution:
- 500 Valid Claim
- 500 Invalid Claim
- 500 Manual Review

Stratified Split:
- 70% Train: 1,050 records (350 per class)
- 15% Validation: 225 records (75 per class)
- 15% Test: 225 records (75 per class)
"""

import os
import random
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from assurex_claim_engine.decision.derived_features import compute_derived_claim_features

# Seed for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

CATEGORIES = {
    "electronics": {
        "brands": ["Sony", "Samsung", "Apple", "Dell", "LG", "Asus", "Bose"],
        "models": ["Pro-X100", "UltraView-55", "MacBook-Air-M2", "XPS-15", "OLED-C2", "QuietComfort-45"],
        "faults": ["screen_flicker_defect", "motherboard_failure", "battery_charging_failure", "audio_speaker_malfunction", "overheating_shutdown"],
        "exclusions": ["liquid_spill_damage", "physical_drop_crack", "unauthorized_repair_attempt", "normal_cosmetic_wear"],
        "warranty_months": 24
    },
    "appliances": {
        "brands": ["Whirlpool", "Bosch", "Panasonic", "Haier", "GE Appliances", "Samsung"],
        "models": ["FrostFree-500L", "EcoSilence-Drive", "Inverter-AC-1.5T", "Convection-Microwave-30L"],
        "faults": ["compressor_failure", "motor_burnout", "cooling_leakage", "control_board_malfunction", "thermostat_failure"],
        "exclusions": ["voltage_fluctuation_damage", "improper_installation", "pest_infestation_damage", "commercial_use_overload"],
        "warranty_months": 36
    },
    "automotive": {
        "brands": ["Bosch", "Garmin", "Pioneer", "Exide", "Varta", "Kenwood"],
        "models": ["Matrix-Battery-12V", "GPS-DriveSmart-65", "AVH-Z5200BT-Infotainment", "ProStarter-80A"],
        "faults": ["battery_dead_cell", "alternator_failure", "starter_motor_defect", "gps_module_failure", "sensor_malfunction"],
        "exclusions": ["accident_collision_damage", "racing_track_misuse", "improper_wiring_modifications", "water_submersion"],
        "warranty_months": 12
    }
}

RETAILERS = ["Amazon Retail", "Best Buy", "Target", "Walmart", "Direct Brand Store", "TechZone Distributors"]

def random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, max(0, delta.days))
    return start_date + timedelta(days=random_days)

def generate_record(claim_id_idx, target_class, forced_scenario=None):
    claim_id = f"CLM-2026-{claim_id_idx:04d}"
    user_id = f"USR-{random.randint(1000, 9999)}"
    product_id = f"PRD-{random.randint(10000, 99999)}"
    
    category = random.choice(list(CATEGORIES.keys()))
    cat_info = CATEGORIES[category]
    
    brand = random.choice(cat_info["brands"])
    model_number = random.choice(cat_info["models"])
    
    # Generate matching serial base
    serial_base = f"{brand[:3].upper()}{random.randint(100000, 999999)}"
    user_serial = serial_base
    ocr_serial = serial_base
    
    warranty_months = cat_info["warranty_months"]
    
    # Anchor dates around 2024 - 2026
    base_now = datetime(2026, 6, 1)
    
    # Standard valid purchase date within active warranty
    purchase_date = random_date(base_now - timedelta(days=365 * 2), base_now - timedelta(days=60))
    warranty_expiry_date = purchase_date + timedelta(days=30 * warranty_months)
    
    # Defaults
    fault_date = random_date(purchase_date + timedelta(days=10), warranty_expiry_date - timedelta(days=10))
    submission_date = random_date(fault_date, fault_date + timedelta(days=14))
    
    fault_type = random.choice(cat_info["faults"])
    damage_type = "none"
    
    previous_repairs = random.randint(0, 1)
    has_unauthorized_repair = False
    
    has_receipt = True
    has_warranty_card = True
    has_product_photo = True
    has_serial_photo = True
    
    serial_match_status = "Exact"
    contradiction_flag = False
    duplicate_claim_flag = False
    
    # Apply class specific generation logic or forced scenarios
    if forced_scenario == "valid" or (forced_scenario is None and target_class == "Valid Claim"):
        # Perfect valid record
        pass
    elif forced_scenario == "expired_warranty" or (forced_scenario is None and target_class == "Invalid Claim" and random.random() < 0.4):
        # Claim date after warranty expiry
        submission_date = warranty_expiry_date + timedelta(days=random.randint(45, 180))
        fault_date = submission_date - timedelta(days=5)
    elif forced_scenario == "excluded_damage" or (forced_scenario is None and target_class == "Invalid Claim" and random.random() < 0.7):
        # Excluded damage type
        damage_type = random.choice(cat_info["exclusions"])
    elif forced_scenario == "unauthorized_repair" or (forced_scenario is None and target_class == "Invalid Claim"):
        has_unauthorized_repair = True
        previous_repairs = random.randint(1, 3)
    elif forced_scenario == "missing_document" or (forced_scenario is None and target_class == "Manual Review" and random.random() < 0.35):
        # Missing receipt or serial photo
        has_receipt = random.choice([True, False])
        if has_receipt:
            has_serial_photo = False
    elif forced_scenario == "contradiction" or (forced_scenario is None and target_class == "Manual Review" and random.random() < 0.65):
        # Contradiction: fault date before purchase date or claim date before fault date
        contradiction_flag = True
        fault_date = purchase_date - timedelta(days=random.randint(5, 30))
    elif forced_scenario == "serial_mismatch" or (forced_scenario is None and target_class == "Manual Review" and random.random() < 0.85):
        serial_match_status = "Mismatch"
        ocr_serial = serial_base[:-2] + "99"
    elif forced_scenario == "duplicate" or (forced_scenario is None and target_class == "Manual Review"):
        duplicate_claim_flag = True
    elif forced_scenario == "boundary_date":
        # Claim filed on exact last day of warranty
        submission_date = warranty_expiry_date
        fault_date = submission_date - timedelta(days=1)
        target_class = "Valid Claim"

    # Derived numerical features
    product_age_days = (submission_date - purchase_date).days
    remaining_warranty_days = (warranty_expiry_date - submission_date).days
    reporting_delay_days = (submission_date - fault_date).days
    
    missing_docs_count = sum([not has_receipt, not has_warranty_card, not has_product_photo, not has_serial_photo])
    
    purchase_price = round(random.uniform(150.0, 1800.0), 2)
    retailer = random.choice(RETAILERS)
    
    return {
        "claim_id": claim_id,
        "user_id": user_id,
        "product_id": product_id,
        "product_name": f"{brand} {model_number}",
        "product_category": category,
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
        "fault_category": fault_type,
        "damage_type": damage_type,
        "previous_repairs_count": previous_repairs,
        "has_unauthorized_repairs": has_unauthorized_repair,
        "has_receipt": has_receipt,
        "has_warranty_card": has_warranty_card,
        "has_product_photo": has_product_photo,
        "has_serial_photo": has_serial_photo,
        "missing_documents_count": missing_docs_count,
        "contradiction_flag": contradiction_flag,
        "duplicate_claim_flag": duplicate_claim_flag,
        "product_age_days": product_age_days,
        "remaining_warranty_days": remaining_warranty_days,
        "reporting_delay_days": reporting_delay_days,
        "actual_class": target_class
    }

def generate_full_dataset():
    records = []
    
    # Include mandatory test case scenarios explicitly first
    mandatory_scenarios = [
        ("valid", "Valid Claim"),
        ("expired_warranty", "Invalid Claim"),
        ("missing_document", "Manual Review"),
        ("expired_warranty", "Invalid Claim"),
        ("missing_document", "Manual Review"),
        ("duplicate", "Manual Review"),
        ("contradiction", "Manual Review"),
        ("serial_mismatch", "Manual Review"),
        ("unauthorized_repair", "Invalid Claim"),
        ("boundary_date", "Valid Claim"),
        ("excluded_damage", "Invalid Claim")
    ]
    
    claim_counter = 1
    for scen, cls in mandatory_scenarios:
        records.append(generate_record(claim_counter, cls, forced_scenario=scen))
        claim_counter += 1
        
    # Now generate remaining to reach exactly 1,500 total (500 Valid, 500 Invalid, 500 Manual Review)
    current_counts = pd.DataFrame(records)["actual_class"].value_counts().to_dict()
    valid_needed = 500 - current_counts.get("Valid Claim", 0)
    invalid_needed = 500 - current_counts.get("Invalid Claim", 0)
    review_needed = 500 - current_counts.get("Manual Review", 0)
    
    for _ in range(valid_needed):
        records.append(generate_record(claim_counter, "Valid Claim"))
        claim_counter += 1
        
    for _ in range(invalid_needed):
        records.append(generate_record(claim_counter, "Invalid Claim"))
        claim_counter += 1

    for _ in range(review_needed):
        records.append(generate_record(claim_counter, "Manual Review"))
        claim_counter += 1
        
    df = pd.DataFrame(records)
    
    # Shuffle dataset maintaining seed
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    # Re-assign Claim IDs sequentially
    df["claim_id"] = [f"CLM-2026-{i+1:04d}" for i in range(len(df))]
    
    return df

def save_splits(df):
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Save full processed dataset
    df.to_csv("data/processed/claims_dataset.csv", index=False)
    
    # Stratified split: 70% Train (1050), 15% Val (225), 15% Test (225)
    train_df = pd.DataFrame()
    val_df = pd.DataFrame()
    test_df = pd.DataFrame()
    
    for cls in ["Valid Claim", "Invalid Claim", "Manual Review"]:
        cls_df = df[df["actual_class"] == cls].sample(frac=1, random_state=SEED)
        
        # 350 train, 75 val, 75 test per class
        t_cls = cls_df.iloc[:350]
        v_cls = cls_df.iloc[350:425]
        ts_cls = cls_df.iloc[425:500]
        
        train_df = pd.concat([train_df, t_cls])
        val_df = pd.concat([val_df, v_cls])
        test_df = pd.concat([test_df, ts_cls])
        
    train_df = train_df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    val_df = val_df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    test_df = test_df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    
    train_df.to_csv("data/train.csv", index=False)
    val_df.to_csv("data/val.csv", index=False)
    test_df.to_csv("data/test.csv", index=False)
    
    print(f"Dataset generated successfully!")
    print(f"Total Records: {len(df)}")
    print(f"Train Records: {len(train_df)} (Valid: {sum(train_df['actual_class']=='Valid Claim')}, Invalid: {sum(train_df['actual_class']=='Invalid Claim')}, Review: {sum(train_df['actual_class']=='Manual Review')})")
    print(f"Val Records:   {len(val_df)}")
    print(f"Test Records:  {len(test_df)}")

if __name__ == "__main__":
    df = generate_full_dataset()
    save_splits(df)
