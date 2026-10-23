"""
AssureX Claim Engine - Claim Summary Card Renderer v6 (experimental)

Same 600x600 contract as v4, but the two signals that only existed as small
detail text now get their own large status tiles:

    FLAGS    NONE / CONTRADICTION / DUPLICATE / BOTH FLAGS
    DAMAGE   NONE / DAMAGE (accidental damage reported)
    WARRANTY ACTIVE / EXPIRING / EXPIRED
    DOCUMENTS COMPLETE / MISSING n
    REPAIRS  AUTHORIZED / 2+ REPAIRS / UNAUTHORIZED
    SERIAL   MATCH / PARTIAL / MISMATCH / UNVERIFIED

Nothing here is used by the live application yet; ``render_claim_card`` (v4)
remains the deployed renderer until a model is trained on v6 cards.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd
from PIL import Image, ImageDraw

try:  # package import (dataset_generator.generate_summary_cards_v6)
    from .generate_summary_cards import (
        CARD_HEIGHT,
        CARD_WIDTH,
        CLASSES,
        SPLITS,
        _fit_font,
        _get_val,
        _is_true,
        _load_font,
        _theme,
        _to_int,
        _truncate,
        _wrap,
    )
except ImportError:  # direct script execution
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from generate_summary_cards import (
        CARD_HEIGHT,
        CARD_WIDTH,
        CLASSES,
        SPLITS,
        _fit_font,
        _get_val,
        _is_true,
        _load_font,
        _theme,
        _to_int,
        _truncate,
        _wrap,
    )

CARD_VERSION = "v6"
RENDERER_NAME = "dataset_generator/generate_summary_cards_v6.py"


def _blend(base, color, ratio):
    return tuple(round(a * (1 - ratio) + b * ratio) for a, b in zip(base, color))


def _humanize(value):
    return str(value).replace("_", " ").replace("-", " ").strip().title()


def render_claim_card_v6(row, variation_id=1):
    """Render the 600x600 six-tile claim card."""
    variation_id = 2 if int(variation_id) == 2 else 1
    theme = _theme(variation_id)

    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), theme["bg"])
    draw = ImageDraw.Draw(img)

    font_title = _load_font(22, bold=True)
    font_section = _load_font(13, bold=True)
    font_tile_label = _load_font(12, bold=True)
    font_tile_sub = _load_font(11)
    font_detail_label = _load_font(13, bold=True)
    font_detail = _load_font(18)

    draw.rounded_rectangle(
        [16, 16, 584, 584], radius=14, fill=theme["card"], outline=theme["border"], width=2
    )
    draw.rounded_rectangle([30, 28, 570, 82], radius=8, fill=theme["accent"])

    claim_id = str(_get_val(row, "claim_id", default="CLM-UNKNOWN"))
    title = f"CLAIM SUMMARY CARD  |  {claim_id}"
    draw.text(
        (44, 42), _truncate(draw, title, font_title, 512), fill=theme["header_text"], font=font_title
    )

    def tile(x, y, w, h, label, value, sub, color):
        fill = _blend(theme["tile"], color, 0.10)
        outline = _blend(theme["border"], color, 0.35)
        draw.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=fill, outline=outline, width=1)
        draw.text((x + 14, y + 8), label, fill=theme["secondary"], font=font_tile_label)
        value_font = _fit_font(draw, value, w - 28, 34, 20)
        draw.text((x + 14, y + 26), value, fill=color, font=value_font)
        draw.text(
            (x + 14, y + h - 20),
            _truncate(draw, sub, font_tile_sub, w - 28),
            fill=theme["secondary"],
            font=font_tile_sub,
        )

    product_name = _get_val(row, "product_name", default="Unknown product")
    fault = _humanize(_get_val(row, "fault_category", default="unspecified defect"))
    damage_raw = str(_get_val(row, "damage_type", default="none")).strip().lower()
    damage_reported = damage_raw not in ("", "none", "nan")
    damage_text = _humanize(damage_raw) if damage_reported else "no accidental damage"
    warranty_months = _get_val(row, "warranty_duration_months", "warranty_months", default="N/A")
    expiry = str(_get_val(row, "warranty_expiry_date", default="N/A"))[:10]
    age_days = _get_val(row, "product_age_days", default="N/A")
    remaining = _to_int(_get_val(row, "remaining_warranty_days", default=0))
    repairs = _to_int(_get_val(row, "previous_repairs_count", "previous_repair_count", default=0))
    unauthorized = _is_true(
        _get_val(row, "has_unauthorized_repairs", "has_previous_unauthorized_repair", default=False)
    )
    serial_raw = str(_get_val(row, "serial_match_status", default="Unverified")).strip().lower()
    missing = _to_int(_get_val(row, "missing_documents_count", default=0))
    contradiction = _is_true(_get_val(row, "contradiction_flag", default=False))
    duplicate = _is_true(_get_val(row, "duplicate_claim_flag", default=False))

    # FLAGS tile
    if contradiction and duplicate:
        flags_value, flags_sub = "BOTH FLAGS", "contradiction + duplicate"
    elif contradiction:
        flags_value, flags_sub = "CONTRADICTION", "timeline inconsistency"
    elif duplicate:
        flags_value, flags_sub = "DUPLICATE", "possible duplicate claim"
    else:
        flags_value, flags_sub = "NONE", "no flags"
    flags_color = theme["bad"] if (contradiction or duplicate) else theme["good"]

    # DAMAGE tile
    if damage_reported:
        damage_value, damage_color = "DAMAGE", theme["bad"]
    else:
        damage_value, damage_color = "NONE", theme["good"]

    # WARRANTY tile
    if remaining < 0:
        warranty_value, warranty_color = "EXPIRED", theme["bad"]
        warranty_sub = f"{abs(remaining)} days past | ended {expiry}"
    elif remaining <= 30:
        warranty_value, warranty_color = "EXPIRING", theme["warn"]
        warranty_sub = f"{remaining} days left | ends {expiry}"
    else:
        warranty_value, warranty_color = "ACTIVE", theme["good"]
        warranty_sub = f"{remaining} days left | ends {expiry}"

    # DOCUMENTS tile
    if missing > 0:
        documents_value = "MISSING" if missing == 1 else f"MISSING {missing}"
        documents_color, documents_sub = theme["bad"], f"{missing} mandatory doc(s)"
    else:
        documents_value, documents_color, documents_sub = "COMPLETE", theme["good"], "all documents"

    # REPAIRS tile
    if unauthorized:
        repairs_value, repairs_color, repairs_sub = "UNAUTHORIZED", theme["bad"], f"{repairs} prior repair(s)"
    elif repairs >= 2:
        repairs_value, repairs_color, repairs_sub = "2+ REPAIRS", theme["warn"], f"{repairs} prior, authorized"
    else:
        repairs_value, repairs_color, repairs_sub = "AUTHORIZED", theme["good"], f"{repairs} prior repair(s)"

    # SERIAL tile
    if serial_raw == "mismatch":
        serial_value, serial_color = "MISMATCH", theme["bad"]
    elif serial_raw == "partial":
        serial_value, serial_color = "PARTIAL", theme["warn"]
    elif serial_raw == "exact":
        serial_value, serial_color = "MATCH", theme["good"]
    else:
        serial_value, serial_color = "UNVERIFIED", theme["warn"]

    # 2 columns x 3 rows
    rows_y = (92, 190, 288)
    tile_w, tile_h = 266, 92
    tile(28, rows_y[0], tile_w, tile_h, "FLAGS", flags_value, flags_sub, flags_color)
    tile(306, rows_y[0], tile_w, tile_h, "DAMAGE", damage_value, damage_text, damage_color)
    tile(28, rows_y[1], tile_w, tile_h, "WARRANTY", warranty_value, warranty_sub, warranty_color)
    tile(306, rows_y[1], tile_w, tile_h, "DOCUMENTS", documents_value, documents_sub, documents_color)
    tile(28, rows_y[2], tile_w, tile_h, "REPAIRS", repairs_value, repairs_sub, repairs_color)
    tile(306, rows_y[2], tile_w, tile_h, "SERIAL", serial_value, "serial number check", serial_color)

    label_x, value_x, value_width = 34, 170, 400
    draw.text((label_x, 398), "CLAIM DETAILS", fill=theme["accent"], font=font_section)

    def field(y, label, value):
        draw.text((label_x, y + 2), label, fill=theme["secondary"], font=font_detail_label)
        for line_idx, line in enumerate(_wrap(draw, value, font_detail, value_width, max_lines=2)):
            draw.text((value_x, y + line_idx * 20), line, fill=theme["text"], font=font_detail)

    field(418, "Product", product_name)
    field(458, "Fault / Damage", f"{fault}  |  {_humanize(damage_raw) if damage_reported else 'None'}")
    field(498, "Age / Warranty", f"{age_days} days old  |  {warranty_months} months")

    return img


def generate(structured_dir, output_dir, splits=("train", "val", "test")):
    os.makedirs(output_dir, exist_ok=True)
    mapping = []
    counts = {}
    for split in splits:
        csv_path = os.path.join(structured_dir, f"{split}.csv")
        if not os.path.exists(csv_path):
            continue
        df = pd.read_csv(csv_path)
        counts[split] = {}
        for _, row in df.iterrows():
            cls = str(row["actual_class"])
            cls_dir = os.path.join(output_dir, split, cls)
            os.makedirs(cls_dir, exist_ok=True)
            variations = (1, 2) if split == "train" else (1,)
            for variation in variations:
                card = render_claim_card_v6(row, variation_id=variation)
                name = f"{row['claim_id']}_v{variation}.png"
                card.save(os.path.join(cls_dir, name), optimize=True)
                mapping.append(
                    {
                        "claim_id": row["claim_id"],
                        "actual_class": cls,
                        "split": split,
                        "variation": variation,
                        "image_path": os.path.join(split, cls, name),
                    }
                )
            counts[split][cls] = counts[split].get(cls, 0) + 1

    pd.DataFrame(mapping).to_csv(os.path.join(output_dir, "claim_id_to_image_mapping_v6.csv"), index=False)
    stats = {
        "dataset_version": CARD_VERSION,
        "renderer": RENDERER_NAME,
        "card_size_px": [CARD_WIDTH, CARD_HEIGHT],
        "source_structured": os.path.abspath(structured_dir),
        "splits": counts,
        "total_images": len(mapping),
        "classes": CLASSES,
    }
    with open(os.path.join(output_dir, "dataset_statistics_v6.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))
    return stats


def main():
    parser = argparse.ArgumentParser(description="Render v6 six-tile claim cards.")
    parser.add_argument("--structured", default=os.path.join("..", "03 Common Dataset", "structured_v4"))
    parser.add_argument("--output", default=os.path.join("..", "03 Common Dataset", "summary_cards_v6"))
    parser.add_argument("--splits", default="train,val,test")
    args = parser.parse_args()
    generate(args.structured, args.output, tuple(s.strip() for s in args.splits.split(",")))


if __name__ == "__main__":
    main()
