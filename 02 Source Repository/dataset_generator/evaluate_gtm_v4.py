"""
Evaluate a Google Teachable Machine H5 on the v4 dataset.

Two gates:
1. 225 held-out v4 test cards on disk (600x600, variation 1)
2. 30 cards rendered by the live application renderer from the same test rows

Usage (from 02 Source Repository):
    uv run python dataset_generator/evaluate_gtm_v4.py
    uv run python dataset_generator/evaluate_gtm_v4.py --model "GTM Models/keras_model.h5" --out "..\\05 Teachable Machine Evidence\\v4_evaluation.json"

The script only reads the model and writes the JSON report; it does not train.
"""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _path in (os.path.join(_PROJECT_ROOT, "src"), _PROJECT_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from assurex_claim_engine.models.image_classifier import ImageClassifierPipeline  # noqa: E402
from dataset_generator.generate_summary_cards import render_claim_card  # noqa: E402
from dataset_generator.generate_summary_cards_v6 import render_claim_card_v6  # noqa: E402

CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Evaluate a GTM model on the v4 cards.")
    parser.add_argument("--model", default=os.path.join("GTM Models", "keras_model.h5"))
    parser.add_argument("--labels", default=os.path.join("GTM Models", "labels.txt"))
    parser.add_argument("--structured", default=os.path.join("..", "03 Common Dataset", "structured_v4"))
    parser.add_argument("--images", default=os.path.join("..", "03 Common Dataset", "summary_cards_v4"))
    parser.add_argument(
        "--out",
        default=os.path.join("..", "05 Teachable Machine Evidence", "v4_evaluation.json"),
    )
    parser.add_argument("--live-count", type=int, default=30)
    parser.add_argument("--renderer", choices=["auto", "v4", "v6"], default="auto")
    args = parser.parse_args()

    model_path = os.path.abspath(args.model)
    labels_path = os.path.abspath(args.labels)
    structured = os.path.abspath(args.structured)
    images = os.path.abspath(args.images)

    renderer_version = args.renderer
    if renderer_version == "auto":
        renderer_version = (
            "v6" if "v6" in os.path.basename(os.path.normpath(args.images)) else "v4"
        )
    render_card = render_claim_card_v6 if renderer_version == "v6" else render_claim_card

    pipeline = ImageClassifierPipeline(model_path=model_path, labels_path=labels_path)
    pipeline.load_model()
    if pipeline.model is None:
        raise SystemExit(f"Could not load GTM model at {model_path}")

    df = pd.read_csv(os.path.join(structured, "test.csv"))
    if len(df) != 225:
        raise SystemExit(f"Expected 225 test rows, found {len(df)}")

    y_true, y_pred, rows, misclassified = [], [], [], []
    for _, row in df.iterrows():
        actual = str(row["actual_class"])
        image_path = os.path.join(
            images, "test", actual, f"{row['claim_id']}_v1.png"
        )
        if not os.path.exists(image_path):
            raise SystemExit(f"Missing test card: {image_path}")
        result = pipeline.predict_image(image_path)
        y_true.append(actual)
        y_pred.append(result["predicted_class"])
        rows.append(
            {
                "claim_id": row["claim_id"],
                "actual_class": actual,
                "predicted_class": result["predicted_class"],
                "top_confidence": result["top_confidence"],
                "probabilities": result["probabilities"],
                "card": os.path.relpath(image_path, os.path.dirname(structured)),
            }
        )
        if result["predicted_class"] != actual:
            misclassified.append(rows[-1])

    accuracy = float(accuracy_score(y_true, y_pred))
    report = classification_report(
        y_true, y_pred, labels=CLASSES, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y_true, y_pred, labels=CLASSES).tolist()
    per_class = {
        c: {
            "precision": round(float(report[c]["precision"]), 4),
            "recall": round(float(report[c]["recall"]), 4),
            "f1": round(float(report[c]["f1-score"]), 4),
            "support": int(report[c]["support"]),
        }
        for c in CLASSES
    }

    live_rows = []
    live_ok = 0
    for _, row in df.head(args.live_count).iterrows():
        actual = str(row["actual_class"])
        image = render_card(row, variation_id=1)
        result = pipeline.predict_image(image)
        live_rows.append(
            {
                "claim_id": row["claim_id"],
                "actual_class": actual,
                "predicted_class": result["predicted_class"],
                "top_confidence": result["top_confidence"],
                "probabilities": result["probabilities"],
            }
        )
        if result["predicted_class"] == actual:
            live_ok += 1

    live_accuracy = live_ok / len(live_rows) if live_rows else 0.0
    summary = {
        "model": os.path.basename(model_path),
        "model_sha256": sha256(model_path),
        "labels_file": os.path.basename(labels_path),
        "labels": pipeline.class_names,
        "test": {
            "count": len(df),
            "accuracy": round(accuracy, 4),
            "passes_85_percent": accuracy >= 0.85,
            "per_class": per_class,
            "confusion_matrix": matrix,
            "class_order": CLASSES,
            "predicted_distribution": dict(Counter(y_pred)),
        },
        "live_render": {
            "count": len(live_rows),
            "accuracy": round(live_accuracy, 4),
            "passes_85_percent": live_accuracy >= 0.85,
            "predicted_distribution": dict(Counter(r["predicted_class"] for r in live_rows)),
        },
        "misclassified_count": len(misclassified),
        "misclassified_examples": misclassified[:12],
        "cases": rows,
        "live_cases": live_rows,
        "dataset": {
            "version": renderer_version,
            "card_size_px": [600, 600],
            "test_cards": os.path.relpath(images, os.path.dirname(structured)),
        },
    }

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps({k: summary[k] for k in ("model", "test", "live_render")}, indent=2))
    print(f"Report: {out_path}")
    if not summary["test"]["passes_85_percent"]:
        print("GATE FAILED: test accuracy < 85%")
    if not summary["live_render"]["passes_85_percent"]:
        print("GATE FAILED: live-render accuracy < 85%")


if __name__ == "__main__":
    main()

