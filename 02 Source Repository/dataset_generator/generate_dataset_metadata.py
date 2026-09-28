"""
AssureX Claim Engine - Dataset Metadata & Mapping Generator
Generates mandatory SRS dataset deliverables:
1. data/claim_id_to_image_mapping.csv (Mapping Claim ID <-> Visual Summary Card Image Filename)
2. data/dataset_statistics.json (Class counts, category splits, missing doc stats)
3. data/data_dictionary.json (Feature definitions, types, allowed values)
"""

import os
import json
import pandas as pd

DATA_DIR = "data"

def generate_metadata():
    print("Generating dataset metadata and mapping files...")
    
    # Load splits
    train_df = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    val_df = pd.read_csv(os.path.join(DATA_DIR, "val.csv"))
    test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))
    
    train_df["split"] = "train"
    val_df["split"] = "val"
    test_df["split"] = "test"
    
    full_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
    
    # 1. Claim ID to Image Mapping
    mapping_rows = []
    for idx, row in full_df.iterrows():
        claim_id = row["claim_id"]
        split = row["split"]
        cls = row["actual_class"]
        
        # Train has 2 visual variations, Val/Test have 1 variation
        variations = [1, 2] if split == "train" else [1]
        
        for var_id in variations:
            filename = f"{claim_id}_v{var_id}.png"
            rel_path = f"summary_cards/{split}/{cls}/{filename}"
            
            mapping_rows.append({
                "claim_id": claim_id,
                "split": split,
                "actual_class": cls,
                "variation_id": var_id,
                "image_filename": filename,
                "image_relative_path": rel_path
            })
            
    mapping_df = pd.DataFrame(mapping_rows)
    mapping_df.to_csv(os.path.join(DATA_DIR, "claim_id_to_image_mapping.csv"), index=False)
    print(f"Saved {len(mapping_df)} mapping records to 'data/claim_id_to_image_mapping.csv'")
    
    # 2. Dataset Statistics
    stats = {
        "total_unique_claim_records": int(len(full_df)),
        "split_counts": {
            "train": int(len(train_df)),
            "validation": int(len(val_df)),
            "test": int(len(test_df))
        },
        "class_distribution": {
            "Valid Claim": int(sum(full_df["actual_class"] == "Valid Claim")),
            "Invalid Claim": int(sum(full_df["actual_class"] == "Invalid Claim")),
            "Manual Review": int(sum(full_df["actual_class"] == "Manual Review"))
        },
        "category_distribution": full_df["product_category"].value_counts().to_dict(),
        "total_summary_card_images": int(len(mapping_df)),
        "train_card_images": int(sum(mapping_df["split"] == "train")),
        "val_card_images": int(sum(mapping_df["split"] == "val")),
        "test_card_images": int(sum(mapping_df["split"] == "test")),
        "average_product_age_days": float(round(full_df["product_age_days"].mean(), 2)),
        "average_remaining_warranty_days": float(round(full_df["remaining_warranty_days"].mean(), 2)),
        "contradiction_claims_count": int(sum(full_df["contradiction_flag"] == True)),
        "duplicate_claims_count": int(sum(full_df["duplicate_claim_flag"] == True))
    }
    
    with open(os.path.join(DATA_DIR, "dataset_statistics.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print("Saved dataset statistics to 'data/dataset_statistics.json'")
    
    # 3. Data Dictionary
    dictionary = {
        "dataset_name": "AssureX Claim Engine Common Warranty Dataset",
        "version": "1.0",
        "description": "Structured tabular claims and visual summary cards for dual-model adjudication.",
        "features": [
            {"name": "claim_id", "type": "string", "description": "Unique identifier assigned to each claim (e.g., CLM-2026-0001)."},
            {"name": "user_id", "type": "string", "description": "Unique identifier of claimant customer or service station."},
            {"name": "product_id", "type": "string", "description": "Unique identifier of registered product under warranty."},
            {"name": "product_name", "type": "string", "description": "Name of product model and brand."},
            {"name": "product_category", "type": "string", "allowed_values": ["electronics", "appliances", "automotive"], "description": "Product warranty category."},
            {"name": "brand", "type": "string", "description": "Manufacturer brand name."},
            {"name": "model_number", "type": "string", "description": "Product model designation."},
            {"name": "user_serial_number", "type": "string", "description": "Serial number provided by user."},
            {"name": "ocr_serial_number", "type": "string", "description": "Serial number extracted via document OCR."},
            {"name": "serial_match_status", "type": "string", "allowed_values": ["Exact", "Mismatch", "Partial"], "description": "Serial verification match status."},
            {"name": "purchase_date", "type": "date", "description": "Date product was purchased."},
            {"name": "purchase_price", "type": "float", "description": "Retail purchase price in USD."},
            {"name": "retailer", "type": "string", "description": "Authorized merchant or store name."},
            {"name": "warranty_duration_months", "type": "integer", "description": "Total warranty coverage period in months."},
            {"name": "warranty_expiry_date", "type": "date", "description": "Calculated end date of warranty coverage."},
            {"name": "fault_occurrence_date", "type": "date", "description": "Date fault symptom was observed."},
            {"name": "claim_submission_date", "type": "date", "description": "Date claim was submitted to engine."},
            {"name": "fault_category", "type": "string", "description": "Reported fault defect category."},
            {"name": "damage_type", "type": "string", "description": "Excluded physical damage type if any."},
            {"name": "previous_repairs_count", "type": "integer", "description": "Number of previous repair logs for this product."},
            {"name": "has_unauthorized_repairs", "type": "boolean", "description": "Flag indicating unauthorized service attempts."},
            {"name": "has_receipt", "type": "boolean", "description": "True if receipt invoice document attached."},
            {"name": "has_warranty_card", "type": "boolean", "description": "True if warranty card attached."},
            {"name": "has_product_photo", "type": "boolean", "description": "True if product damage photo attached."},
            {"name": "has_serial_photo", "type": "boolean", "description": "True if serial number photo attached."},
            {"name": "missing_documents_count", "type": "integer", "description": "Total count of missing mandatory documents."},
            {"name": "contradiction_flag", "type": "boolean", "description": "True if timeline contradiction detected."},
            {"name": "duplicate_claim_flag", "type": "boolean", "description": "True if duplicate serial/hash detected."},
            {"name": "product_age_days", "type": "integer", "description": "Derived days between purchase and submission."},
            {"name": "remaining_warranty_days", "type": "integer", "description": "Derived days remaining in warranty coverage."},
            {"name": "reporting_delay_days", "type": "integer", "description": "Derived days between fault occurrence and submission."},
            {"name": "actual_class", "type": "string", "allowed_values": ["Valid Claim", "Invalid Claim", "Manual Review"], "description": "Ground truth adjudication label."}
        ]
    }
    
    with open(os.path.join(DATA_DIR, "data_dictionary.json"), "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=2)
    print("Saved data dictionary to 'data/data_dictionary.json'")

if __name__ == "__main__":
    generate_metadata()
