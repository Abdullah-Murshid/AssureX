"""
Validate the v4 dataset and its Claim Summary Cards.

Hard failures (exit code 1):
- missing/duplicated records, wrong split or class counts
- Claim-ID overlap between splits
- missing images, wrong image size, mapping/path class mismatch
- offline-vs-live render parity failure

Warnings (reported, not fatal):
- deterministic labels
- constant columns
- duplicate flags without supporting evidence
- thin boundary coverage
"""

import argparse
import json
import os
import sys
from collections import Counter

import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dataset_generator.generate_summary_cards import (  # noqa: E402
    CARD_HEIGHT,
    CARD_WIDTH,
    CLASSES,
    SPLITS,
    render_claim_card,
)

EXPECTED_SPLIT_ROWS = {"train": 1050, "val": 225, "test": 225}
EXPECTED_CLASS_PER_SPLIT = {"train": 350, "val": 75, "test": 75}


def deterministic_label(row):
    damage = str(row.get("damage_type", "none")).lower()
    unauthorized = str(row.get("has_unauthorized_repairs", False)).lower() in ("true", "1", "yes")
    if damage != "none" or unauthorized:
        return "Invalid Claim"
    if (
        str(row.get("contradiction_flag", False)).lower() in ("true", "1", "yes")
        or str(row.get("duplicate_claim_flag", False)).lower() in ("true", "1", "yes")
        or str(row.get("serial_match_status", "")) == "Mismatch"
        or int(row.get("missing_documents_count", 0)) > 0
    ):
        return "Manual Review"
    if float(row.get("remaining_warranty_days", 0)) < 0:
        return "Invalid Claim"
    return "Valid Claim"


def main():
    parser = argparse.ArgumentParser(description="Validate the v4 structured dataset and cards.")
    parser.add_argument("--structured", default=os.path.join("..", "03 Common Dataset", "structured_v4"))
    parser.add_argument("--images", default=os.path.join("..", "03 Common Dataset", "summary_cards_v4"))
    args = parser.parse_args()

    structured = os.path.abspath(args.structured)
    images = os.path.abspath(args.images)
    failures = []
    warnings = []
    report = {}

    # 1. Records and splits
    frames = {}
    for split in SPLITS:
        path = os.path.join(structured, f"{split}.csv")
        if not os.path.exists(path):
            failures.append(f"Missing {path}")
            continue
        df = pd.read_csv(path)
        frames[split] = df
        if len(df) != EXPECTED_SPLIT_ROWS[split]:
            failures.append(f"{split}: {len(df)} rows, expected {EXPECTED_SPLIT_ROWS[split]}")
        counts = df["actual_class"].value_counts().to_dict()
        for cls in CLASSES:
            if counts.get(cls, 0) != EXPECTED_CLASS_PER_SPLIT[split]:
                failures.append(f"{split}/{cls}: {counts.get(cls, 0)} rows, expected {EXPECTED_CLASS_PER_SPLIT[split]}")

    if len(frames) == len(SPLITS):
        all_ids = pd.concat([frames[s]["claim_id"] for s in SPLITS])
        if all_ids.duplicated().any():
            failures.append(f"{int(all_ids.duplicated().sum())} duplicate Claim IDs across splits")
        if len(all_ids) != 1500:
            failures.append(f"Total records {len(all_ids)}, expected 1500")
        for i, a in enumerate(SPLITS):
            for b in SPLITS[i + 1 :]:
                overlap = set(frames[a]["claim_id"]) & set(frames[b]["claim_id"])
                if overlap:
                    failures.append(f"{a}/{b} Claim-ID overlap: {len(overlap)}")
        combined = pd.concat([frames[s] for s in SPLITS], ignore_index=True)
        report["records"] = {
            "total": int(len(combined)),
            "splits": {s: int(len(frames[s])) for s in SPLITS},
            "classes": combined["actual_class"].value_counts().to_dict(),
        }
        null_columns = combined.columns[combined.isna().any()].tolist()
        if null_columns:
            failures.append(f"Null values in columns: {null_columns}")

        # 2. Label-quality warnings (do not fail; reported for the retraining decision)
        predicted = combined.apply(deterministic_label, axis=1)
        agreement = float((predicted == combined["actual_class"]).mean())
        report["label_rule_agreement"] = round(agreement, 4)
        if agreement == 1.0:
            warnings.append("Labels are 100% reproducible from six deterministic conditions.")

        constant_columns = [c for c in combined.columns if combined[c].nunique(dropna=False) <= 1]
        report["constant_columns"] = constant_columns
        if constant_columns:
            warnings.append(f"Constant columns: {constant_columns}")

        flagged = combined[combined["duplicate_claim_flag"].astype(str).str.lower().isin(["true", "1", "yes"])]
        serial_counts = combined["user_serial_number"].value_counts()
        flagged_with_evidence = int(sum(serial_counts.get(s, 0) > 1 for s in flagged["user_serial_number"]))
        report["duplicate_flags"] = {
            "flagged": int(len(flagged)),
            "with_matching_serial_evidence": flagged_with_evidence,
        }
        if len(flagged) and flagged_with_evidence < len(flagged):
            warnings.append(
                f"{len(flagged) - flagged_with_evidence}/{len(flagged)} duplicate flags lack a matching serial."
            )

        bad_mismatch = combined[
            (combined["serial_match_status"].astype(str) == "Mismatch")
            & (
                combined["user_serial_number"].astype(str).str.upper()
                == combined["ocr_serial_number"].astype(str).str.upper()
            )
        ]
        report["impossible_serial_mismatches"] = int(len(bad_mismatch))
        if len(bad_mismatch):
            failures.append(f"{len(bad_mismatch)} 'Mismatch' rows have identical user/OCR serials.")

        boundary = int((combined["remaining_warranty_days"] == 0).sum())
        report["remaining_days_zero"] = boundary
        if boundary < 10:
            warnings.append(f"Only {boundary} records sit exactly on remaining_warranty_days == 0.")

    # 3. Mapping and images
    mapping_path = os.path.join(structured, "claim_id_to_image_mapping_v4.csv")
    if not os.path.exists(mapping_path):
        failures.append(f"Missing mapping: {mapping_path}")
    else:
        mapping = pd.read_csv(mapping_path)
        report["mapping_rows"] = int(len(mapping))
        if len(mapping) != 2550:
            failures.append(f"Mapping has {len(mapping)} rows, expected 2550")
        if mapping.duplicated(["claim_id", "variation_id"]).any():
            failures.append("Duplicate claim_id/variation_id mapping rows")
        missing_files = 0
        wrong_size = 0
        path_mismatch = 0
        missing_label = 0
        for _, row in mapping.iterrows():
            image_path = os.path.join(images, str(row["image_relative_path"]).replace("/", os.sep))
            if not os.path.exists(image_path):
                missing_files += 1
                continue
            with Image.open(image_path) as im:
                if im.size != (CARD_WIDTH, CARD_HEIGHT):
                    wrong_size += 1
            parts = str(row["image_relative_path"]).replace("\\", "/").split("/")
            if row["split"] not in parts or row["actual_class"] not in parts:
                path_mismatch += 1
            if str(row["actual_class"]) not in CLASSES:
                missing_label += 1
        report["images"] = {
            "missing": missing_files,
            "wrong_size": wrong_size,
            "path_class_mismatch": path_mismatch,
            "bad_labels": missing_label,
        }
        if missing_files:
            failures.append(f"{missing_files} mapping rows point to missing images")
        if wrong_size:
            failures.append(f"{wrong_size} images are not {CARD_WIDTH}x{CARD_HEIGHT}")
        if path_mismatch:
            failures.append(f"{path_mismatch} mapping paths disagree with their class/split")
        if missing_label:
            failures.append(f"{missing_label} mapping rows have an invalid class label")

        counts = mapping.groupby(["split", "actual_class"]).size().to_dict()
        expected = {
            ("train", "Valid Claim"): 700,
            ("train", "Invalid Claim"): 700,
            ("train", "Manual Review"): 700,
            ("val", "Valid Claim"): 75,
            ("val", "Invalid Claim"): 75,
            ("val", "Manual Review"): 75,
            ("test", "Valid Claim"): 75,
            ("test", "Invalid Claim"): 75,
            ("test", "Manual Review"): 75,
        }
        for key, value in expected.items():
            if counts.get(key, 0) != value:
                failures.append(f"{key}: {counts.get(key, 0)} images, expected {value}")

        # 4. Offline vs live render parity
        if len(frames) == len(SPLITS):
            combined = pd.concat([frames[s] for s in SPLITS], ignore_index=True)
            sample = combined.sample(n=min(30, len(combined)), random_state=42)
            parity_failures = 0
            for _, row in sample.iterrows():
                a = render_claim_card(row, variation_id=1)
                b = render_claim_card(row.to_dict(), variation_id=1)
                if a.tobytes() != b.tobytes():
                    parity_failures += 1
            report["render_parity_failures"] = parity_failures
            if parity_failures:
                failures.append(f"{parity_failures}/30 offline-vs-dict renders differ")

    report["warnings"] = warnings
    report["failures"] = failures
    report["passed"] = not failures

    out_path = os.path.join(structured, "validation_report_v4.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"\nReport: {out_path}")
    if failures:
        print(f"\nFAILED: {len(failures)} hard check(s)")
        raise SystemExit(1)
    print("\nPASSED hard checks" + (f" ({len(warnings)} warning(s))" if warnings else ""))


if __name__ == "__main__":
    main()

