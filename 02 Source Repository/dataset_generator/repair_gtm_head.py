"""
Repair the underfit Teachable Machine head (candidate only).

The deployed GTM export is a MobileNetV2 base + Dense(100) + Dense(3). It scores
only ~78.6% on its own training cards, i.e. it never fit the data. This script
keeps the base frozen, extracts its 1280-d features once, retrains the small
head, evaluates on the held-out test cards, and writes a CANDIDATE model to
``GTM Models/keras_model_headfix.h5``. The deployed ``keras_model.h5`` is not
modified.

Usage:
    uv run python dataset_generator/repair_gtm_head.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from assurex_claim_engine.models.image_classifier import ImageClassifierPipeline  # noqa: E402

CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]


def load_batch(paths, start, size):
    arrays = []
    for path in paths[start : start + size]:
        image = Image.open(path).convert("RGB").resize((224, 224))
        arrays.append((np.asarray(image, dtype=np.float32) / 127.5) - 1.0)
    return np.stack(arrays)


def features(base_model, paths, batch_size=32):
    chunks = []
    for start in range(0, len(paths), batch_size):
        chunks.append(base_model.predict(load_batch(paths, start, batch_size), verbose=0))
    return np.concatenate(chunks, axis=0)


def main():
    pipeline = ImageClassifierPipeline()
    pipeline.load_model()
    model = pipeline.model
    class_names = pipeline.class_names

    base = model.layers[0]  # MobileNetV2 + global average pooling -> (None, 1280)
    head = model.layers[1]  # Dense(100) + Dense(3)

    structured = os.path.join("..", "03 Common Dataset", "structured_v4")
    images = os.path.join("..", "03 Common Dataset", "summary_cards_v4")
    train = pd.read_csv(os.path.join(structured, "train.csv"))
    test = pd.read_csv(os.path.join(structured, "test.csv"))

    train_paths, train_labels = [], []
    for _, row in train.iterrows():
        cls = str(row["actual_class"])
        for variation in (1, 2):
            train_paths.append(os.path.join(images, "train", cls, f"{row['claim_id']}_v{variation}.png"))
            train_labels.append(class_names.index(cls))

    test_paths, test_labels = [], []
    for _, row in test.iterrows():
        cls = str(row["actual_class"])
        test_paths.append(os.path.join(images, "test", cls, f"{row['claim_id']}_v1.png"))
        test_labels.append(class_names.index(cls))

    cache_path = os.path.join(tempfile.gettempdir(), "gtm_headfix_features.npz")
    if os.path.exists(cache_path):
        cached = np.load(cache_path)
        train_features, test_features = cached["train"], cached["test"]
        print("loaded cached features", train_features.shape, test_features.shape)
    else:
        print("extracting frozen base features…")
        train_features = features(base, train_paths)
        test_features = features(base, test_paths)
        np.savez_compressed(cache_path, train=train_features, test=test_features)
        print("train features:", train_features.shape, "test features:", test_features.shape)

    from tensorflow import keras

    new_head = keras.Sequential(
        [
            keras.layers.Input(shape=(train_features.shape[1],)),
            keras.layers.Dense(100, activation="relu"),
            keras.layers.Dense(3, activation="softmax", use_bias=False),
        ],
        name="retrained_head",
    )
    new_head.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    new_head.fit(
        train_features,
        np.asarray(train_labels),
        epochs=150,
        batch_size=32,
        validation_split=0.1,
        verbose=0,
    )

    probabilities = new_head.predict(test_features, verbose=0)
    predictions = [class_names[int(np.argmax(p))] for p in probabilities]
    actual = [class_names[i] for i in test_labels]

    report = {
        "candidate": "GTM Models/keras_model_headfix.h5",
        "base": "deployed MobileNetV2 (frozen)",
        "head": "Dense(100) + Dense(3), retrained on 2,100 v4 train cards",
        "test_accuracy": round(float(accuracy_score(actual, predictions)), 4),
        "confusion_matrix": confusion_matrix(actual, predictions, labels=class_names).tolist(),
        "per_class": classification_report(
            actual, predictions, labels=class_names, output_dict=True, zero_division=0
        ),
        "class_order": class_names,
    }
    print(json.dumps({k: report[k] for k in ("test_accuracy", "confusion_matrix")}, indent=2))
    print(classification_report(actual, predictions, labels=class_names, zero_division=0))

    head.set_weights(new_head.get_weights())
    candidate_path = os.path.join("GTM Models", "keras_model_headfix.h5")
    model.save(candidate_path)
    print("saved", candidate_path)

    # Reload the saved file exactly the way the application does, then verify.
    check = ImageClassifierPipeline(model_path=candidate_path)
    check.load_model()
    candidate_preds = []
    for start in range(0, len(test_paths), 32):
        batch = load_batch(test_paths, start, 32)
        probs = check.model.predict(batch, verbose=0)
        candidate_preds.extend(class_names[int(np.argmax(p))] for p in probs)
    candidate_acc = accuracy_score(actual, candidate_preds)
    print("candidate reload accuracy:", round(float(candidate_acc), 4))
    report["candidate_reload_accuracy"] = round(float(candidate_acc), 4)

    with open(
        os.path.join("..", "05 Teachable Machine Evidence", "gtm_headfix_evaluation.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(report, handle, indent=2)


if __name__ == "__main__":
    main()
