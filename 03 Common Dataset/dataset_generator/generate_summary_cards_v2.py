"""
AssureX Claim Engine - Claim Summary Card Renderer v2
Renders visual Claim Summary Cards (PNG) for v2 dataset.

Enforces:
1. Displays ONLY objective claim facts (no prediction, confidence, or class label).
2. Generates 2 visual variations per training claim record (2,100 training images).
3. Validation & Test cards rendered into separate splits (225 each).
4. Generates data/v2/claim_id_to_image_mapping.csv.
"""

import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

DATA_V2_DIR = "data/v2"
OUTPUT_DIR = os.path.join(DATA_V2_DIR, "summary_cards")
SPLITS = ["train", "val", "test"]
CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]

for s in SPLITS:
    for c in CLASSES:
        os.makedirs(os.path.join(OUTPUT_DIR, s, c), exist_ok=True)

def _get_val(row, *keys, default=""):
    for k in keys:
        if hasattr(row, "get"):
            v = row.get(k)
            if v is not None and str(v).strip() != "":
                return v
        elif hasattr(row, "__getitem__"):
            try:
                v = row[k]
                if v is not None and str(v).strip() != "":
                    return v
            except (KeyError, IndexError, TypeError):
                pass
    return default

def render_claim_card(row, variation_id=1):
    """
    Renders a visual Claim Summary Card image for a given claim record.
    Displays purely objective claim specifications with clean typography, balanced spacing,
    and no watermarks, footer text, or classification labels.
    """
    width, height = 840, 500
    
    if variation_id == 1:
        bg_color = (245, 247, 250)      # Clean Light Blue-Gray
        card_bg = (255, 255, 255)       # Pure White Card
        text_primary = (20, 30, 45)     # Deep Slate
        text_secondary = (70, 85, 105)  # Muted Blue Gray
        accent_color = (14, 116, 144)   # Cyan Teal Accent
        border_color = (226, 232, 240)
    else:
        bg_color = (15, 23, 42)         # Modern Dark Slate
        card_bg = (30, 41, 59)          # Card Dark Gray
        text_primary = (248, 250, 252)  # Bright Off-White
        text_secondary = (148, 163, 184)# Soft Silver
        accent_color = (56, 189, 248)   # Vivid Sky Blue Accent
        border_color = (51, 65, 85)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Outer Card Container
    card_rect = [20, 20, width - 20, height - 20]
    draw.rounded_rectangle(card_rect, radius=12, fill=card_bg, outline=border_color, width=2)
    
    # Card Header Banner
    draw.rounded_rectangle([32, 32, width - 32, 90], radius=8, fill=accent_color)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 20)
        font_header = ImageFont.truetype("arialbd.ttf", 14)
        font_body = ImageFont.truetype("arial.ttf", 14)
        font_bold = ImageFont.truetype("arialbd.ttf", 14)
    except IOError:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        
    claim_id_val = _get_val(row, "claim_id", default="CLM-SPEC")
    draw.text((45, 48), f"CLAIM SUMMARY CARD  •  {claim_id_val}", fill=(255, 255, 255), font=font_title)
    
    # Column 1: Product & Purchase Details
    col1_x = 42
    col1_val_x = 180
    y_curr = 115
    
    draw.text((col1_x, y_curr), "PRODUCT & WARRANTY SPECIFICATIONS", fill=accent_color, font=font_header)
    y_curr += 28
    
    prod_name = _get_val(row, "product_name", default="N/A")
    cat_val = _get_val(row, "product_category", "category", default="General")
    brand_val = _get_val(row, "brand", default="")
    model_val = _get_val(row, "model_number", default="N/A")
    serial_val = _get_val(row, "user_serial_number", "serial_number", default="N/A")
    purch_date = _get_val(row, "purchase_date", default="N/A")
    retailer_val = _get_val(row, "retailer", default="Authorized Dealer")
    warranty_months = _get_val(row, "warranty_duration_months", "warranty_duration", default="12")
    expiry_val = str(_get_val(row, "warranty_expiry_date", default="N/A"))[:10]
    
    age_days = _get_val(row, "product_age_days", default=0)
    try:
        age_days_int = int(age_days)
        age_str = f"{age_days_int} Days ({round(age_days_int/365, 1)} Yrs)"
    except (ValueError, TypeError):
        age_str = f"{age_days} Days"
        
    rem_days = _get_val(row, "remaining_warranty_days", default="0")
    
    items_col1 = [
        ("Product Name:", str(prod_name)),
        ("Category & Brand:", f"{str(cat_val).title()} ({brand_val})"),
        ("Model / Serial:", f"{model_val} / {serial_val}"),
        ("Purchase Date:", str(purch_date)),
        ("Retailer:", str(retailer_val)),
        ("Warranty Duration:", f"{warranty_months} Months (Exp: {expiry_val})"),
        ("Product Age:", age_str),
        ("Remaining Coverage:", f"{rem_days} Days")
    ]
    
    for label, val in items_col1:
        draw.text((col1_x, y_curr), label, fill=text_secondary, font=font_bold)
        draw.text((col1_val_x, y_curr), val, fill=text_primary, font=font_body)
        y_curr += 25
        
    # Divider Line
    draw.line([415, 110, 415, height - 35], fill=border_color, width=2)
    
    # Column 2: Fault Report & Audit Facts
    col2_x = 435
    col2_val_x = 590
    y_curr = 115
    
    draw.text((col2_x, y_curr), "FAULT REPORT & EVIDENCE AUDIT", fill=accent_color, font=font_header)
    y_curr += 28
    
    has_rcpt = _get_val(row, "has_receipt", default=False)
    receipt_str = "Verified Uploaded" if str(has_rcpt).lower() in ("true", "1", "yes") else "MISSING RECEIPT"
    
    serial_match = _get_val(row, "serial_match_status", default="Unverified")
    ocr_serial = _get_val(row, "ocr_serial_number", default="N/A")
    serial_match_str = f"{serial_match} ({ocr_serial})"
    
    repairs_cnt = _get_val(row, "previous_repairs_count", default=0)
    has_unauth = _get_val(row, "has_unauthorized_repairs", default=False)
    unauth_str = " [UNAUTHORIZED]" if str(has_unauth).lower() in ("true", "1", "yes") else " [Authorized]"
    repair_hist_str = f"{repairs_cnt} Prior Repair(s){unauth_str}"
    
    missing_cnt = _get_val(row, "missing_documents_count", default=0)
    contra_flag = _get_val(row, "contradiction_flag", default=False)
    contra_str = "YES (Timeline Issue)" if str(contra_flag).lower() in ("true", "1", "yes") else "None Detected"
    
    items_col2 = [
        ("Fault Category:", str(_get_val(row, "fault_category", default="Defect")).replace("_", " ").title()),
        ("Damage Type:", str(_get_val(row, "damage_type", default="None")).replace("_", " ").title()),
        ("Fault Date:", str(_get_val(row, "fault_occurrence_date", default="N/A"))),
        ("Claim Date:", str(_get_val(row, "claim_submission_date", default="N/A"))),
        ("Receipt Status:", receipt_str),
        ("Serial OCR Match:", serial_match_str),
        ("Repair History:", repair_hist_str),
        ("Missing Docs Count:", f"{missing_cnt} Mandatory Doc(s) Missing"),
        ("Contradiction Flag:", contra_str)
    ]
    
    for label, val in items_col2:
        draw.text((col2_x, y_curr), label, fill=text_secondary, font=font_bold)
        draw.text((col2_val_x, y_curr), val, fill=text_primary, font=font_body)
        y_curr += 25
        
    return img

def generate_all_cards_v2():
    print("Generating visual Claim Summary Cards for Dataset v2...")
    mapping_records = []
    
    for split in SPLITS:
        csv_path = os.path.join(DATA_V2_DIR, f"{split}.csv")
        df = pd.read_csv(csv_path)
        count = 0
        variations = [1, 2] if split == "train" else [1]
        
        for idx, row in df.iterrows():
            claim_id = row["claim_id"]
            cls_name = row["actual_class"]
            
            for var_id in variations:
                filename = f"{claim_id}_v{var_id}.png"
                rel_path = os.path.join("data", "v2", "summary_cards", split, cls_name, filename).replace("\\", "/")
                abs_path = os.path.join(OUTPUT_DIR, split, cls_name, filename)
                
                img = render_claim_card(row, variation_id=var_id)
                img.save(abs_path)
                count += 1
                
                mapping_records.append({
                    "claim_id": claim_id,
                    "split": split,
                    "actual_class": cls_name,
                    "variation_id": var_id,
                    "image_filename": filename,
                    "image_path": rel_path
                })
                
        print(f"Generated {count} images for split: {split}")
        
    # Write claim_id_to_image_mapping.csv
    mapping_df = pd.DataFrame(mapping_records)
    map_path = os.path.join(DATA_V2_DIR, "claim_id_to_image_mapping.csv")
    mapping_df.to_csv(map_path, index=False)
    print(f"Saved claim_id to image mapping to {map_path} ({len(mapping_df)} entries).")

if __name__ == "__main__":
    generate_all_cards_v2()
