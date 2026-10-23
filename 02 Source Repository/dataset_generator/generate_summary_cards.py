"""
AssureX Claim Engine - Claim Summary Card Renderer v4

Renders a clean, square Claim Summary Card (600x600) from structured claim data.
The same function is used for offline dataset generation and live web inference, so
the training and deployment distributions cannot drift.

Card contract (SRS 1.6 xx):
- Four large status tiles: warranty, documents, repairs, serial.
- Claim details: product, fault/damage, age/warranty, contradiction/duplicate.
- MUST NOT show the Python prediction, confidence score, or final decision.
- No class-dependent colours, layout, or text; colours encode claim facts only.

Dataset contract (SRS 1.2 / 1.10.3):
- 1,050 train claims x 2 visual variations = 2,100 images
- 225 validation x 1 = 225 images
- 225 test x 1 = 225 images
- Validation/test use variation 1, the same style the web application renders.
"""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# Canonical card size. Square avoids aspect-ratio distortion in the 224x224 GTM input.
CARD_WIDTH = 600
CARD_HEIGHT = 600
CARD_VERSION = "v4"
RENDERER_NAME = "dataset_generator/generate_summary_cards.py"

SPLITS = ["train", "val", "test"]
CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]

DATA_DIR = "data"
OUTPUT_DIR = "data/summary_cards"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_val(row, *keys, default=""):
    """Read a value from a pandas Series or a plain dict, trying several keys."""
    for k in keys:
        try:
            if hasattr(row, "get"):
                v = row.get(k)
            else:
                v = row[k]
        except (KeyError, IndexError, TypeError):
            continue
        if v is not None and str(v).strip() != "" and str(v).lower() != "nan":
            return v
    return default


def _is_true(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y", "t")


def _load_font(size, bold=False):
    names = ["arialbd.ttf", "Arial Bold.ttf"] if bold else ["arial.ttf", "Arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _truncate(draw, text, font, max_width):
    text = str(text)
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "..."
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if draw.textlength(candidate, font=font) <= max_width:
            lo = mid + 1
        else:
            hi = mid
    return text[: max(0, lo - 1)].rstrip() + ellipsis


def _wrap(draw, text, font, max_width, max_lines=2):
    """Wrap text to at most max_lines, truncating the last line with an ellipsis."""
    text = " ".join(str(text).split())
    if not text:
        return [""]
    if draw.textlength(text, font=font) <= max_width:
        return [text]

    words = text.split(" ")
    lines = []
    current = ""
    idx = 0
    while idx < len(words) and len(lines) < max_lines:
        word = words[idx]
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            idx += 1
        else:
            if current:
                lines.append(current)
                current = ""
            else:
                lines.append(_truncate(draw, word, font, max_width))
                idx += 1
                break
    if current and len(lines) < max_lines:
        lines.append(current)

    if idx < len(words) and lines:
        lines[-1] = _truncate(draw, lines[-1] + "...", font, max_width)
    return lines[:max_lines]


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _theme(variation_id):
    if variation_id == 1:
        return {
            "bg": (238, 242, 247),
            "card": (255, 255, 255),
            "tile": (246, 249, 252),
            "text": (20, 30, 45),
            "secondary": (70, 85, 105),
            "accent": (14, 116, 144),
            "border": (216, 224, 234),
            "header_text": (255, 255, 255),
            "good": (21, 128, 61),
            "warn": (180, 83, 9),
            "bad": (185, 28, 28),
        }
    return {
        "bg": (10, 16, 28),
        "card": (30, 41, 59),
        "tile": (24, 34, 52),
        "text": (248, 250, 252),
        "secondary": (168, 184, 204),
        "accent": (56, 189, 248),
        "border": (51, 65, 85),
        "header_text": (8, 18, 30),
        "good": (74, 222, 128),
        "warn": (251, 191, 36),
        "bad": (248, 113, 113),
    }


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _fit_font(draw, text, max_width, max_size=40, min_size=22):
    text = str(text)
    for size in range(max_size, min_size - 1, -2):
        font = _load_font(size, bold=True)
        if draw.textlength(text, font=font) <= max_width:
            return font
    return _load_font(min_size, bold=True)


def render_claim_card(row, variation_id=1):
    """Render a 600x600 status-tile claim card as a PIL Image.

    ``row`` may be a pandas Series (dataset path) or a dict (web path).
    """
    variation_id = 2 if int(variation_id) == 2 else 1
    theme = _theme(variation_id)

    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), theme["bg"])
    draw = ImageDraw.Draw(img)

    font_title = _load_font(22, bold=True)
    font_section = _load_font(13, bold=True)
    font_tile_label = _load_font(13, bold=True)
    font_tile_sub = _load_font(14)
    font_detail_label = _load_font(15, bold=True)
    font_detail = _load_font(20)

    # Card and header
    draw.rounded_rectangle([16, 16, 584, 584], radius=14, fill=theme["card"], outline=theme["border"], width=2)
    draw.rounded_rectangle([30, 28, 570, 82], radius=8, fill=theme["accent"])

    claim_id = str(_get_val(row, "claim_id", default="CLM-UNKNOWN"))
    title = f"CLAIM SUMMARY CARD  |  {claim_id}"
    draw.text((44, 42), _truncate(draw, title, font_title, 512), fill=theme["header_text"], font=font_title)

    def tile(x, y, w, h, label, value, sub, color):
        draw.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=theme["tile"], outline=theme["border"], width=1)
        draw.text((x + 14, y + 9), label, fill=theme["secondary"], font=font_tile_label)
        value_font = _fit_font(draw, value, w - 28, 40, 22)
        draw.text((x + 14, y + 31), value, fill=color, font=value_font)
        draw.text(
            (x + 14, y + h - 24),
            _truncate(draw, sub, font_tile_sub, w - 28),
            fill=theme["secondary"],
            font=font_tile_sub,
        )

    product_name = _get_val(row, "product_name", default="Unknown product")
    fault = str(_get_val(row, "fault_category", default="unspecified defect")).replace("_", " ").replace("-", " ").title()
    damage = str(_get_val(row, "damage_type", default="none")).replace("_", " ").replace("-", " ").title()
    warranty_months = _get_val(row, "warranty_duration_months", "warranty_months", default="N/A")
    expiry = _get_val(row, "warranty_expiry_date", default="N/A")
    age_days = _get_val(row, "product_age_days", default="N/A")
    remaining = _to_int(_get_val(row, "remaining_warranty_days", default=0))
    repairs = _to_int(_get_val(row, "previous_repairs_count", "previous_repair_count", default=0))
    unauthorized = _is_true(_get_val(row, "has_unauthorized_repairs", "has_previous_unauthorized_repair", default=False))
    serial_raw = str(_get_val(row, "serial_match_status", default="Unverified")).strip().lower()
    missing = _to_int(_get_val(row, "missing_documents_count", default=0))
    contradiction = _is_true(_get_val(row, "contradiction_flag", default=False))
    duplicate_flag = _is_true(_get_val(row, "duplicate_claim_flag", default=False))

    if not expiry or str(expiry).lower() == "nan":
        expiry = "N/A"
    expiry = str(expiry)[:10]

    # Warranty tile
    if remaining < 0:
        warranty_value, warranty_color = "EXPIRED", theme["bad"]
        warranty_sub = f"{abs(remaining)} days past | ended {expiry}"
    elif remaining <= 30:
        warranty_value, warranty_color = "EXPIRING", theme["warn"]
        warranty_sub = f"{remaining} days left | ends {expiry}"
    else:
        warranty_value, warranty_color = "ACTIVE", theme["good"]
        warranty_sub = f"{remaining} days left | ends {expiry}"

    # Documents tile
    if missing > 0:
        documents_value = "MISSING" if missing == 1 else f"MISSING {missing}"
        documents_color, documents_sub = theme["bad"], f"{missing} mandatory doc(s)"
    else:
        documents_value, documents_color, documents_sub = "COMPLETE", theme["good"], "all documents"

    # Repairs tile
    if unauthorized:
        repairs_value, repairs_color, repairs_sub = "UNAUTHORIZED", theme["bad"], f"{repairs} prior repair(s)"
    elif repairs >= 2:
        repairs_value, repairs_color, repairs_sub = "2+ REPAIRS", theme["warn"], f"{repairs} prior, authorized"
    else:
        repairs_value, repairs_color, repairs_sub = "AUTHORIZED", theme["good"], f"{repairs} prior repair(s)"

    # Serial tile
    if serial_raw == "mismatch":
        serial_value, serial_color, serial_sub = "MISMATCH", theme["bad"], "serial number check"
    elif serial_raw == "partial":
        serial_value, serial_color, serial_sub = "PARTIAL", theme["warn"], "serial number check"
    elif serial_raw == "exact":
        serial_value, serial_color, serial_sub = "MATCH", theme["good"], "serial number check"
    else:
        serial_value, serial_color, serial_sub = "UNVERIFIED", theme["warn"], "serial number check"

    tile(28, 92, 266, 112, "WARRANTY", warranty_value, warranty_sub, warranty_color)
    tile(306, 92, 266, 112, "DOCUMENTS", documents_value, documents_sub, documents_color)
    tile(28, 216, 266, 112, "REPAIRS", repairs_value, repairs_sub, repairs_color)
    tile(306, 216, 266, 112, "SERIAL", serial_value, serial_sub, serial_color)

    # Details below the tiles: secondary facts only.
    label_x = 34
    value_x = 178
    value_width = 390

    draw.text((label_x, 342), "CLAIM DETAILS", fill=theme["accent"], font=font_section)

    def field(y, label, value):
        draw.text((label_x, y + 2), label, fill=theme["secondary"], font=font_detail_label)
        lines = _wrap(draw, value, font_detail, value_width, max_lines=2)
        for line_idx, line in enumerate(lines):
            draw.text((value_x, y + line_idx * 22), line, fill=theme["text"], font=font_detail)

    field(362, "Product", product_name)
    field(406, "Fault / Damage", f"{fault}  |  {damage}")
    field(450, "Age / Warranty", f"{age_days} days old  |  {warranty_months} months")
    field(494, "Flags", f"contradiction {'Yes' if contradiction else 'No'}  |  duplicate {'Yes' if duplicate_flag else 'No'}")

    return img


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _combined_digest(paths):
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(os.path.basename(path).encode("utf-8"))
        digest.update(_sha256_file(path).encode("ascii"))
    return digest.hexdigest()


def generate_all_cards(data_dir=None, output_dir=None, metadata_dir=None, write_metadata=True):
    data_dir = os.path.abspath(data_dir or DATA_DIR)
    output_dir = os.path.abspath(output_dir or OUTPUT_DIR)
    metadata_dir = os.path.abspath(metadata_dir or output_dir)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)

    mapping_rows = []
    image_paths = []
    record_frames = {}
    split_counts = {}
    class_distribution = {}

    for split in SPLITS:
        csv_path = os.path.join(data_dir, f"{split}.csv")
        df = pd.read_csv(csv_path)
        record_frames[split] = df
        split_counts[split] = int(len(df))
        variations = [1, 2] if split == "train" else [1]

        for _, row in df.iterrows():
            claim_id = str(row["claim_id"])
            actual_class = str(row["actual_class"])
            if actual_class not in CLASSES:
                raise ValueError(f"Unexpected class '{actual_class}' in {csv_path}")
            for variation_id in variations:
                relative_path = os.path.join(split, actual_class, f"{claim_id}_v{variation_id}.png")
                image_path = os.path.join(output_dir, relative_path)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                render_claim_card(row, variation_id=variation_id).save(image_path, "PNG")
                image_paths.append(image_path)
                mapping_rows.append(
                    {
                        "claim_id": claim_id,
                        "split": split,
                        "actual_class": actual_class,
                        "variation_id": variation_id,
                        "image_filename": os.path.basename(relative_path),
                        "image_relative_path": relative_path.replace(os.sep, "/"),
                    }
                )
                class_distribution[actual_class] = class_distribution.get(actual_class, 0) + 1

        print(f"Generated {len(df) * len(variations)} cards for split: {split}", flush=True)

    if not write_metadata:
        return None

    mapping_path = os.path.join(metadata_dir, f"claim_id_to_image_mapping_{CARD_VERSION}.csv")
    mapping_df = pd.DataFrame(mapping_rows)
    mapping_df.to_csv(mapping_path, index=False)

    all_records = pd.concat(record_frames.values(), ignore_index=True)
    statistics = {
        "dataset_version": CARD_VERSION,
        "card_size_px": [CARD_WIDTH, CARD_HEIGHT],
        "total_unique_claim_records": int(len(all_records)),
        "split_counts": split_counts,
        "class_distribution_records": {c: int((all_records["actual_class"] == c).sum()) for c in CLASSES},
        "class_distribution_images": class_distribution,
        "total_summary_card_images": int(len(mapping_rows)),
        "train_card_images": class_distribution.get("train", None),
        "images_per_split": {
            split: int(sum(1 for r in mapping_rows if r["split"] == split)) for split in SPLITS
        },
        "average_product_age_days": round(float(all_records["product_age_days"].mean()), 2),
        "average_remaining_warranty_days": round(float(all_records["remaining_warranty_days"].mean()), 2),
        "contradiction_claims_count": int(all_records["contradiction_flag"].sum()),
        "duplicate_claims_count": int(all_records["duplicate_claim_flag"].sum()),
        "renderer": RENDERER_NAME,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    # `train_card_images` is the number of images whose split is train (2,100).
    statistics["train_card_images"] = statistics["images_per_split"]["train"]
    stats_path = os.path.join(metadata_dir, f"dataset_statistics_{CARD_VERSION}.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(statistics, f, indent=2)

    csv_hashes = {split: _sha256_file(os.path.join(data_dir, f"{split}.csv")) for split in SPLITS}
    manifest = {
        "dataset_version": CARD_VERSION,
        "renderer": RENDERER_NAME,
        "card_size_px": [CARD_WIDTH, CARD_HEIGHT],
        "created_utc": statistics["created_utc"],
        "counts": {
            "records": statistics["total_unique_claim_records"],
            "images": statistics["total_summary_card_images"],
            "per_split_records": split_counts,
            "per_split_images": statistics["images_per_split"],
            "per_class_images": class_distribution,
        },
        "csv_sha256": csv_hashes,
        "mapping_sha256": _sha256_file(mapping_path),
        "image_set_sha256": _combined_digest(image_paths),
        "contract": {
            "card_shows": [
                "claim_id",
                "warranty status (active/expiring/expired)",
                "remaining warranty days and expiry",
                "document status and missing count",
                "repair count and authorization",
                "serial match status",
                "product name",
                "fault category",
                "damage type",
                "product age",
                "warranty duration",
                "contradiction flag",
                "duplicate flag",
            ],
            "card_does_not_show": ["python prediction", "python confidence", "final decision", "actual_class"],
            "variations": {"train": 2, "val": 1, "test": 1},
        },
    }
    manifest_path = os.path.join(metadata_dir, f"dataset_manifest_{CARD_VERSION}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Mapping:  {mapping_path}", flush=True)
    print(f"Stats:    {stats_path}", flush=True)
    print(f"Manifest: {manifest_path}", flush=True)
    print(json.dumps(statistics, indent=2), flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Claim Summary Cards from structured CSVs.")
    parser.add_argument("--data-dir", default=DATA_DIR, help="Directory containing train.csv/val.csv/test.csv")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Directory for generated card images")
    parser.add_argument("--metadata-dir", default=None, help="Directory for mapping/statistics/manifest")
    parser.add_argument("--no-metadata", action="store_true", help="Only render images")
    args = parser.parse_args()
    generate_all_cards(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        metadata_dir=args.metadata_dir,
        write_metadata=not args.no_metadata,
    )
