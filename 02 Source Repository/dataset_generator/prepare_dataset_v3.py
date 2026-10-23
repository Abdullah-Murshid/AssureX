"""
Prepare the v3 structured dataset from the frozen v1 CSVs.

What this script changes (and nothing else):
1. Fixes the single impossible serial-mismatch record: CLM-2026-0874 has
   serial_match_status='Mismatch' but identical user/OCR serials. The OCR value
   is changed to a near-match so the label and the evidence agree.
2. Adds the missing `warranty_start_date` feature to the data dictionary.
3. Copies train/val/test unchanged otherwise, plus a combined processed file.
4. Writes a machine-readable change log (`data_fixes_v3.json`).

Labels, counts, splits, and all other feature values are preserved.
Duplicate-flag and constant-field issues are reported by validate_dataset_v3.py,
not silently rewritten.
"""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import pandas as pd

SPLITS = ["train", "val", "test"]
BROKEN_MISMATCH_CLAIM = "CLM-2026-0874"
CORRECTED_OCR_SERIAL = "APP239398"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dictionary_with_start_date(source_dict):
    with open(source_dict, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    if not any(item.get("name") == "warranty_start_date" for item in features):
        entry = {
            "name": "warranty_start_date",
            "type": "date",
            "description": "Date warranty coverage starts. In this dataset it equals the purchase date.",
        }
        # Insert after warranty_duration_months, before warranty_expiry_date.
        insert_at = len(features)
        for idx, item in enumerate(features):
            if item.get("name") == "warranty_expiry_date":
                insert_at = idx
                break
        features.insert(insert_at, entry)

    data["version"] = "1.1"
    data["card_version"] = "v3"
    data["card_size_px"] = [600, 600]
    data["description"] = (
        "Structured tabular claims and visual summary cards for dual-model adjudication. "
        "v3 fixes the card renderer/size and documents warranty_start_date."
    )
    return data


def main():
    parser = argparse.ArgumentParser(description="Build the v3 structured dataset from frozen v1 CSVs.")
    parser.add_argument("--source", default=os.path.join("..", "03 Common Dataset", "structured"))
    parser.add_argument("--output", default=os.path.join("..", "03 Common Dataset", "structured_v3"))
    args = parser.parse_args()

    source = os.path.abspath(args.source)
    output = os.path.abspath(args.output)
    os.makedirs(output, exist_ok=True)

    fixes = []
    frames = {}
    for split in SPLITS:
        src = os.path.join(source, f"{split}.csv")
        df = pd.read_csv(src)
        before = df.copy()

        mask = df["claim_id"] == BROKEN_MISMATCH_CLAIM
        if mask.any():
            if str(df.loc[mask, "user_serial_number"].iloc[0]).upper() == str(
                df.loc[mask, "ocr_serial_number"].iloc[0]
            ).upper():
                df.loc[mask, "ocr_serial_number"] = CORRECTED_OCR_SERIAL
                df.loc[mask, "serial_match_status"] = "Mismatch"
                fixes.append(
                    {
                        "claim_id": BROKEN_MISMATCH_CLAIM,
                        "split": split,
                        "field": "ocr_serial_number",
                        "old": str(before.loc[mask, "ocr_serial_number"].iloc[0]),
                        "new": CORRECTED_OCR_SERIAL,
                        "reason": "Mismatch label had identical user and OCR serials.",
                    }
                )

        df.to_csv(os.path.join(output, f"{split}.csv"), index=False)
        frames[split] = df
        print(f"{split}: {len(df)} rows -> {os.path.join(output, split + '.csv')}")

    combined = pd.concat([frames[s] for s in SPLITS], ignore_index=True)
    combined.to_csv(os.path.join(output, "claims_dataset_v3.csv"), index=False)

    dictionary = _dictionary_with_start_date(os.path.join(source, "data_dictionary.json"))
    dict_path = os.path.join(output, "data_dictionary.json")
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=2)

    change_log = {
        "dataset_version": "v3",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": os.path.relpath(source, output).replace(os.sep, "/"),
        "fixes": fixes,
        "preserved": {
            "records": int(len(combined)),
            "class_distribution": {c: int((combined["actual_class"] == c).sum()) for c in combined["actual_class"].unique()},
            "split_counts": {s: int(len(frames[s])) for s in SPLITS},
        },
        "known_limitations_not_changed": [
            "Labels remain deterministic from the generator's six conditions.",
            "has_warranty_card and has_product_photo are constant True.",
            "duplicate_claim_flag rows do not yet have matching serial/invoice evidence.",
            "Only two records sit exactly on remaining_warranty_days == 0.",
        ],
        "csv_sha256": {s: _sha256(os.path.join(output, f"{s}.csv")) for s in SPLITS},
    }
    with open(os.path.join(output, "data_fixes_v3.json"), "w", encoding="utf-8") as f:
        json.dump(change_log, f, indent=2)

    print(f"Fixes applied: {len(fixes)}")
    print(f"Dictionary: {dict_path}")
    print(f"Change log: {os.path.join(output, 'data_fixes_v3.json')}")


if __name__ == "__main__":
    main()
