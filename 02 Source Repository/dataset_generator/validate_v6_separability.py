"""
Quick separability check for summary-card designs.

This is NOT the Teachable Machine model. It freezes a MobileNetV2 feature
extractor and fits a logistic-regression head, which mirrors how a Teachable
Machine image model learns from card images. Running it on v4 and v6 cards
isolates the effect of the card design.

Usage:
    uv run python dataset_generator/validate_v6_separability.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from tensorflow.keras.applications import MobileNetV2  # noqa: E402
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input  # noqa: E402

CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]


def image_paths(root, split, frame, variations=(1,)):
    paths, labels = [], []
    for _, row in frame.iterrows():
        cls = str(row["actual_class"])
        for variation in variations:
            path = os.path.join(root, split, cls, f"{row['claim_id']}_v{variation}.png")
            if not os.path.exists(path):
                raise SystemExit(f"Missing card: {path}")
            paths.append(path)
            labels.append(cls)
    return paths, labels


def extract(model, paths, batch_size=32):
    chunks = []
    for start in range(0, len(paths), batch_size):
        batch = paths[start : start + batch_size]
        arrays = [
            preprocess_input(
                np.asarray(Image.open(path).convert("RGB").resize((224, 224)), dtype=np.float32)
            )
            for path in batch
        ]
        chunks.append(model.predict(np.stack(arrays), verbose=0))
    return np.concatenate(chunks, axis=0)


def evaluate(name, root, train_frame, test_frame, model, variations):
    train_paths, train_labels = image_paths(root, "train", train_frame, variations)
    test_paths, test_labels = image_paths(root, "test", test_frame, (1,))
    train_features = extract(model, train_paths)
    test_features = extract(model, test_paths)

    classifier = LogisticRegression(max_iter=2000, C=1.0)
    classifier.fit(train_features, train_labels)
    predictions = classifier.predict(test_features)

    result = {
        "design": name,
        "train_images": len(train_paths),
        "test_images": len(test_paths),
        "accuracy": round(float(accuracy_score(test_labels, predictions)), 4),
        "per_class": classification_report(
            test_labels, predictions, labels=CLASSES, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(test_labels, predictions, labels=CLASSES).tolist(),
        "class_order": CLASSES,
    }
    print(
        f"{name}: accuracy={result['accuracy']:.4f} "
        f"(train={len(train_paths)}, test={len(test_paths)})"
    )
    for cls, scores in result["per_class"].items():
        if isinstance(scores, dict):
            print(
                f"  {cls:14s} precision={scores['precision']:.3f} "
                f"recall={scores['recall']:.3f} f1={scores['f1-score']:.3f}"
            )
    print("  confusion:", result["confusion_matrix"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--structured", default=os.path.join("..", "03 Common Dataset", "structured_v4"))
    parser.add_argument("--v4", default=os.path.join("..", "03 Common Dataset", "summary_cards_v4"))
    parser.add_argument("--v6", default=os.path.join("..", "03 Common Dataset", "summary_cards_v6"))
    parser.add_argument(
        "--out",
        default=os.path.join("..", "05 Teachable Machine Evidence", "v6_separability.json"),
    )
    parser.add_argument("--variations", default="1")
    args = parser.parse_args()

    variations = tuple(int(v) for v in args.variations.split(","))
    train_frame = pd.read_csv(os.path.join(args.structured, "train.csv"))
    test_frame = pd.read_csv(os.path.join(args.structured, "test.csv"))

    model = MobileNetV2(
        include_top=False, weights="imagenet", pooling="avg", input_shape=(224, 224, 3), alpha=0.35
    )

    results = [
        evaluate("v4 (deployed design)", args.v4, train_frame, test_frame, model, variations),
        evaluate("v6 (flags + damage tiles)", args.v6, train_frame, test_frame, model, variations),
    ]

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "method": "MobileNetV2(alpha=0.35, frozen) + logistic regression",
                "train_variations": list(variations),
                "results": results,
            },
            handle,
            indent=2,
        )
    print("saved", args.out)


if __name__ == "__main__":
    main()
