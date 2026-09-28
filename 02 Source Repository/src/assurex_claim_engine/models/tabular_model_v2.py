"""
AssureX Claim Engine - Tabular ML Classifier v2
Trains and benchmarks multiple algorithms on v2 overlapping dataset:
- Compares RandomForest, XGBoost, and LogisticRegression using 5-fold Stratified CV on TRAIN
- Selects best model based on VALIDATION set
- Evaluates selected model on unseen TEST set once
- Exports model artifacts to model/v2/
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import json
import joblib
import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

MODEL_V2_DIR = "model/v2"
os.makedirs(MODEL_V2_DIR, exist_ok=True)

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

class TabularClaimClassifierV2:
    def __init__(self):
        self.preprocessor = None
        self.label_encoder = None
        self.best_model = None
        self.model_name = "RandomForest"
        self.feature_names_out = None

    def build_preprocessor(self):
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), FEATURE_COLS_NUMERICAL),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), FEATURE_COLS_CATEGORICAL),
                ("bin", "passthrough", FEATURE_COLS_BINARY)
            ]
        )
        return preprocessor

    def train_and_benchmark(self, train_path="data/v2/train.csv", val_path="data/v2/val.csv", test_path="data/v2/test.csv"):
        print("=================================================================")
        print("  ASSUREX TABULAR ML MODEL V2 BENCHMARKING & RETRAINING")
        print("=================================================================")
        
        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)
        test_df = pd.read_csv(test_path)
        
        print(f"Loaded: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

        # Label Encoder
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(CLASSES)

        y_train = self.label_encoder.transform(train_df[TARGET_COL])
        y_val = self.label_encoder.transform(val_df[TARGET_COL])
        y_test = self.label_encoder.transform(test_df[TARGET_COL])

        # Preprocessing
        self.preprocessor = self.build_preprocessor()
        X_train = self.preprocessor.fit_transform(train_df)
        X_val = self.preprocessor.transform(val_df)
        X_test = self.preprocessor.transform(test_df)
        
        # Save feature names
        try:
            cat_encoder = self.preprocessor.named_transformers_["cat"]
            cat_feature_names = cat_encoder.get_feature_names_out(FEATURE_COLS_CATEGORICAL).tolist()
            self.feature_names_out = FEATURE_COLS_NUMERICAL + cat_feature_names + FEATURE_COLS_BINARY
        except Exception:
            self.feature_names_out = [f"feat_{i}" for i in range(X_train.shape[1])]

        # Define candidate algorithms
        candidate_models = {
            "RandomForest": RandomForestClassifier(
                n_estimators=120,
                max_depth=9,
                min_samples_split=6,
                min_samples_leaf=3,
                random_state=42
            ),
            "LogisticRegression": LogisticRegression(
                max_iter=1000,
                C=0.8,
                random_state=42
            )
        }
        if XGB_AVAILABLE:
            candidate_models["XGBoost"] = XGBClassifier(
                n_estimators=90,
                max_depth=4,
                learning_rate=0.07,
                subsample=0.85,
                colsample_bytree=0.85,
                eval_metric="mlogloss",
                random_state=42
            )

        print("\n--- 5-Fold Stratified Cross-Validation on TRAIN ---")
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_results = {}
        for name, model in candidate_models.items():
            scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
            cv_results[name] = {"mean": float(scores.mean()), "std": float(scores.std())}
            print(f"  {name:18s}: Mean Accuracy = {scores.mean():.4f} (+/- {scores.std():.4f})")

        print("\n--- Validation Set Evaluation ---")
        val_results = {}
        fitted_models = {}
        for name, model in candidate_models.items():
            model.fit(X_train, y_train)
            val_preds = model.predict(X_val)
            val_acc = accuracy_score(y_val, val_preds)
            val_results[name] = val_acc
            fitted_models[name] = model
            print(f"  {name:18s}: Validation Accuracy = {val_acc:.4f}")

        # Choose best model on VALIDATION
        best_name = max(val_results, key=val_results.get)
        self.model_name = best_name
        self.best_model = fitted_models[best_name]
        print(f"\n>> Selected Model: {best_name} (Val Accuracy: {val_results[best_name]:.4f})")

        # Evaluate on TEST once
        print("\n=================================================================")
        print(f"  FINAL EVALUATION ON UNSEEN TEST SET (Model: {best_name})")
        print("=================================================================")
        test_preds = self.best_model.predict(X_test)
        test_acc = accuracy_score(y_test, test_preds)
        prec, rec, f1, _ = precision_recall_fscore_support(y_test, test_preds, average=None)

        print(f"Test Accuracy: {test_acc:.4f} ({test_acc*100:.2f}%)")
        print("\nPer-Class Metrics on Test Set:")
        metrics_per_class = {}
        for idx, cls_name in enumerate(self.label_encoder.classes_):
            metrics_per_class[cls_name] = {
                "precision": float(round(prec[idx], 4)),
                "recall": float(round(rec[idx], 4)),
                "f1_score": float(round(f1[idx], 4))
            }
            print(f"  {cls_name:15s} | Precision: {prec[idx]:.4f} | Recall: {rec[idx]:.4f} | F1: {f1[idx]:.4f}")

        cm = confusion_matrix(y_test, test_preds)
        print("\nConfusion Matrix (Rows: Actual, Cols: Predicted):")
        print(f"               {self.label_encoder.classes_[0]:13s} {self.label_encoder.classes_[1]:13s} {self.label_encoder.classes_[2]:13s}")
        for r_idx, row in enumerate(cm):
            print(f"  {self.label_encoder.classes_[r_idx]:13s} {row[0]:13d} {row[1]:13d} {row[2]:13d}")

        # Feature Importances
        feature_importance_dict = {}
        if hasattr(self.best_model, "feature_importances_"):
            importances = self.best_model.feature_importances_
            indices = np.argsort(importances)[::-1][:15]
            print("\nTop 15 Most Informative Features:")
            for rank, i in enumerate(indices, 1):
                feat_name = self.feature_names_out[i] if i < len(self.feature_names_out) else f"feature_{i}"
                feature_importance_dict[feat_name] = float(round(importances[i], 4))
                print(f"  {rank:2d}. {feat_name:32s} : {importances[i]:.4f}")

        # Save artifacts to model/v2/
        joblib.dump(self.best_model, os.path.join(MODEL_V2_DIR, "best_python_model.joblib"))
        joblib.dump(self.preprocessor, os.path.join(MODEL_V2_DIR, "preprocessor.joblib"))
        joblib.dump(self.label_encoder, os.path.join(MODEL_V2_DIR, "label_encoder.joblib"))
        
        # Save evaluation report metadata
        eval_report = {
            "model_version": "v2",
            "selected_algorithm": best_name,
            "cv_train_results": cv_results,
            "validation_results": val_results,
            "test_accuracy": float(round(test_acc, 4)),
            "per_class_metrics": metrics_per_class,
            "confusion_matrix": cm.tolist(),
            "classes": self.label_encoder.classes_.tolist(),
            "top_features": feature_importance_dict
        }
        with open(os.path.join(MODEL_V2_DIR, "tabular_evaluation_report.json"), "w") as f:
            json.dump(eval_report, f, indent=2)
            
        print(f"\nSaved v2 model artifacts and evaluation report to '{MODEL_V2_DIR}/'")
        return eval_report

    def load_artifacts(self, model_dir=MODEL_V2_DIR):
        model_path = os.path.join(model_dir, "best_python_model.joblib")
        prep_path = os.path.join(model_dir, "preprocessor.joblib")
        le_path = os.path.join(model_dir, "label_encoder.joblib")

        if os.path.exists(model_path) and os.path.exists(prep_path) and os.path.exists(le_path):
            self.best_model = joblib.load(model_path)
            self.preprocessor = joblib.load(prep_path)
            self.label_encoder = joblib.load(le_path)
            return True
        return False

    def predict_single(self, claim_dict):
        if self.best_model is None or self.preprocessor is None:
            self.load_artifacts()

        df = pd.DataFrame([claim_dict])
        X = self.preprocessor.transform(df)
        probabilities = self.best_model.predict_proba(X)[0]

        prob_dict = {}
        for idx, cls_name in enumerate(self.label_encoder.classes_):
            prob_dict[cls_name] = float(round(probabilities[idx], 4))

        top_idx = int(np.argmax(probabilities))
        predicted_class = self.label_encoder.classes_[top_idx]
        top_confidence = float(round(probabilities[top_idx], 4))

        return {
            "predicted_class": predicted_class,
            "top_confidence": top_confidence,
            "probabilities": prob_dict
        }

if __name__ == "__main__":
    clf = TabularClaimClassifierV2()
    clf.train_and_benchmark()
