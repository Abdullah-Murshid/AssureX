"""
AssureX Claim Engine - Tabular ML Classifier Module
Trains, benchmarks, and provides inference for Python ML classification models:
- Benchmarks Random Forest, XGBoost, and LightGBM / MLP classifiers
- Evaluates Accuracy, Precision, Recall, F1-Score, and Confusion Matrix
- Exports best model, scaler, and label encoder to disk
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import joblib
import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None

MODEL_DIR = "model"
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURE_COLS_NUMERICAL = [
    "purchase_price",
    "warranty_duration_months",
    "previous_repairs_count",
    "missing_documents_count",
    "product_age_days",
    "remaining_warranty_days",
    "reporting_delay_days"
]

FEATURE_COLS_CATEGORICAL = [
    "product_category",
    "brand",
    "fault_category",
    "damage_type",
    "serial_match_status"
]

FEATURE_COLS_BINARY = [
    "has_unauthorized_repairs",
    "has_receipt",
    "has_warranty_card",
    "has_product_photo",
    "has_serial_photo",
    "contradiction_flag",
    "duplicate_claim_flag"
]

TARGET_COL = "actual_class"
CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]

class TabularClaimClassifier:
    def __init__(self):
        self.preprocessor = None
        self.label_encoder = None
        self.best_model = None
        self.model_name = "RandomForest"

    def build_preprocessor(self):
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), FEATURE_COLS_NUMERICAL),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), FEATURE_COLS_CATEGORICAL),
                ("bin", "passthrough", FEATURE_COLS_BINARY)
            ]
        )
        return preprocessor

    def train_and_benchmark(self, train_path="data/train.csv", val_path="data/val.csv", test_path="data/test.csv"):
        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)
        test_df = pd.read_csv(test_path)

        # Label Encoder for Target
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(CLASSES)

        y_train = self.label_encoder.transform(train_df[TARGET_COL])
        y_val = self.label_encoder.transform(val_df[TARGET_COL])
        y_test = self.label_encoder.transform(test_df[TARGET_COL])

        # Preprocessing Features
        self.preprocessor = self.build_preprocessor()
        X_train = self.preprocessor.fit_transform(train_df)
        X_val = self.preprocessor.transform(val_df)
        X_test = self.preprocessor.transform(test_df)

        models_to_test = {
            "RandomForest": RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42)
        }

        if XGBClassifier is not None:
            models_to_test["XGBoost"] = XGBClassifier(n_estimators=120, max_depth=6, learning_rate=0.08, random_state=42, eval_metric="mlogloss")
        
        if LGBMClassifier is not None:
            models_to_test["LightGBM"] = LGBMClassifier(n_estimators=100, max_depth=6, learning_rate=0.08, random_state=42, verbose=-1)

        best_acc = 0.0
        results_summary = {}

        print("--- BENCHMARKING PYTHON ML ALGORITHMS ---")
        for name, clf in models_to_test.items():
            clf.fit(X_train, y_train)
            val_preds = clf.predict(X_val)
            acc = accuracy_score(y_val, val_preds)
            
            p, r, f1, _ = precision_recall_fscore_support(y_val, val_preds, average="weighted")
            
            results_summary[name] = {
                "val_accuracy": float(acc),
                "val_precision": float(p),
                "val_recall": float(r),
                "val_f1": float(f1)
            }
            print(f"Algorithm [{name}]: Val Accuracy = {acc:.4f} | F1-Score = {f1:.4f}")

            if acc > best_acc:
                best_acc = acc
                self.best_model = clf
                self.model_name = name

        # Final Evaluation on Test Set
        test_preds = self.best_model.predict(X_test)
        test_acc = accuracy_score(y_test, test_preds)
        cm = confusion_matrix(y_test, test_preds)
        
        print(f"\n--- WINNING MODEL: {self.model_name} ---")
        print(f"Test Accuracy: {test_acc:.4f}")
        print("\nClassification Report (Test Set):")
        print(classification_report(y_test, test_preds, target_names=self.label_encoder.classes_))
        
        # Save Artifacts
        self.save_artifacts()
        
        return {
            "best_model_name": self.model_name,
            "test_accuracy": float(test_acc),
            "benchmark_results": results_summary,
            "confusion_matrix": cm.tolist()
        }

    def save_artifacts(self):
        joblib.dump(self.best_model, os.path.join(MODEL_DIR, "best_python_model.joblib"))
        joblib.dump(self.preprocessor, os.path.join(MODEL_DIR, "preprocessor.joblib"))
        joblib.dump(self.label_encoder, os.path.join(MODEL_DIR, "label_encoder.joblib"))
        print(f"Saved best model and preprocessing artifacts to '{MODEL_DIR}/'")

    def load_artifacts(self, model_dir=None):
        if model_dir is None:
            candidates = [
                os.path.join("model", "v2"),
                "model",
                os.path.join("02. Complete Source Code", "model", "v2"),
                os.path.join("02. Complete Source Code", "model"),
                os.path.join("05. Python Model Files", "v2"),
                "05. Python Model Files",
                os.path.join(os.path.dirname(__file__), "../../../model/v2"),
                os.path.join(os.path.dirname(__file__), "../../../model"),
                os.path.join(os.path.dirname(__file__), "../../../05. Python Model Files/v2"),
                os.path.join(os.path.dirname(__file__), "../../../05. Python Model Files"),
            ]
            for c in candidates:
                if os.path.exists(os.path.join(c, "best_python_model.joblib")):
                    model_dir = os.path.abspath(c)
                    break
            if not model_dir:
                model_dir = MODEL_DIR
        self.best_model = joblib.load(os.path.join(model_dir, "best_python_model.joblib"))
        self.preprocessor = joblib.load(os.path.join(model_dir, "preprocessor.joblib"))
        self.label_encoder = joblib.load(os.path.join(model_dir, "label_encoder.joblib"))

    def predict_single(self, claim_dict):
        """
        Predicts class and probabilities for a single claim dictionary.
        Returns:
            predicted_class: str ('Valid Claim', 'Invalid Claim', 'Manual Review')
            probabilities: dict ({'Valid Claim': 0.85, 'Invalid Claim': 0.10, 'Manual Review': 0.05})
            top_confidence: float
        """
        if self.best_model is None or self.preprocessor is None:
            self.load_artifacts()

        df_single = pd.DataFrame([claim_dict])
        
        # Compute derived fields if missing
        if "missing_documents_count" not in df_single.columns:
            evidence_cols = ["has_receipt", "has_warranty_card", "has_product_photo", "has_serial_photo"]
            df_single["missing_documents_count"] = sum(not bool(claim_dict.get(key, False)) for key in evidence_cols)

        X_processed = self.preprocessor.transform(df_single)
        probs = self.best_model.predict_proba(X_processed)[0]
        
        prob_dict = {}
        for idx, cls_name in enumerate(self.label_encoder.classes_):
            prob_dict[cls_name] = float(round(probs[idx], 4))

        top_class_idx = np.argmax(probs)
        predicted_class = str(self.label_encoder.classes_[top_class_idx])
        top_confidence = float(round(probs[top_class_idx], 4))

        return {
            "predicted_class": predicted_class,
            "top_confidence": top_confidence,
            "probabilities": prob_dict
        }

if __name__ == "__main__":
    clf_engine = TabularClaimClassifier()
    clf_engine.train_and_benchmark()
