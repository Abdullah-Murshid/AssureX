"""
AssureX Claim Engine - Visual Summary Card Image Classifier v2
Retrains MobileNetV2 on v2 visual summary cards with realistic overlapping scenarios:
- Trains on data/v2/summary_cards/train (2,100 images with visual variations)
- Validates on data/v2/summary_cards/val (225 images)
- Reports final accuracy, per-class metrics, and confusion matrix on data/v2/summary_cards/test (225 images)
- Saves artifacts in model/v2/image_classifier/
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms, models
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
from PIL import Image

MODEL_V2_DIR = "model/v2/image_classifier"
os.makedirs(MODEL_V2_DIR, exist_ok=True)

CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]

class SummaryCardImageClassifierV2(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        self.backbone = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier[1] = nn.Sequential(
            nn.Dropout(p=0.35),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)

class ImageClassifierPipelineV2:
    def __init__(self, model_dir=MODEL_V2_DIR):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SummaryCardImageClassifierV2(num_classes=3).to(self.device)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def train_model(self, train_dir="data/v2/summary_cards/train", val_dir="data/v2/summary_cards/val", test_dir="data/v2/summary_cards/test", epochs=4):
        print("=================================================================")
        print("  ASSUREX COMPUTER VISION MODEL V2 TRAINING (MobileNetV2)")
        print("=================================================================")
        
        train_dataset = ImageFolder(root=train_dir, transform=self.transform)
        val_dataset = ImageFolder(root=val_dir, transform=self.transform)
        test_dataset = ImageFolder(root=test_dir, transform=self.transform)

        print(f"Loaded datasets: Train={len(train_dataset)}, Val={len(val_dataset)}, Test={len(test_dataset)}")
        print(f"ImageFolder class_to_idx: {train_dataset.class_to_idx}")

        # Save labels.json in model directory
        with open(os.path.join(self.model_dir, "labels.json"), "w") as f:
            json.dump(train_dataset.class_to_idx, f, indent=2)

        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(self.model.parameters(), lr=8e-4, weight_decay=1e-4)

        best_val_acc = 0.0

        for epoch in range(epochs):
            self.model.train()
            running_loss = 0.0
            correct_train = 0
            total_train = 0

            for images, labels in train_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                optimizer.zero_grad()
                outputs = self.model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                running_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                correct_train += (preds == labels).sum().item()
                total_train += labels.size(0)

            train_loss = running_loss / total_train
            train_acc = correct_train / total_train

            # Validation
            self.model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for images, labels in val_loader:
                    images, labels = images.to(self.device), labels.to(self.device)
                    outputs = self.model(images)
                    _, preds = torch.max(outputs, 1)
                    val_correct += (preds == labels).sum().item()
                    val_total += labels.size(0)

            val_acc = val_correct / val_total if val_total > 0 else 0.0
            print(f"Epoch [{epoch+1}/{epochs}] - Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | Val Acc: {val_acc:.4f}")

            if val_acc >= best_val_acc:
                best_val_acc = val_acc
                torch.save(self.model.state_dict(), os.path.join(self.model_dir, "best_image_model.pt"))
                print(f"  --> Saved new best checkpoint (Val Acc: {val_acc:.4f})")

        # Load best checkpoint for test evaluation
        print("\nLoading best checkpoint for final evaluation on unseen TEST cards...")
        self.model.load_state_dict(torch.load(os.path.join(self.model_dir, "best_image_model.pt"), map_location=self.device))
        self.model.eval()

        all_preds = []
        all_labels = []

        with torch.no_grad():
            for images, labels in test_loader:
                images = images.to(self.device)
                outputs = self.model(images)
                _, preds = torch.max(outputs, 1)
                all_preds.extend(preds.cpu().numpy().tolist())
                all_labels.extend(labels.numpy().tolist())

        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)

        test_acc = float(np.mean(all_preds == all_labels))
        print("=================================================================")
        print("  IMAGE CLASSIFIER V2 TEST SET EVALUATION")
        print("=================================================================")
        print(f"Test Accuracy: {test_acc:.4f} ({test_acc*100:.2f}%)")

        idx_to_class = {v: k for k, v in train_dataset.class_to_idx.items()}
        class_names = [idx_to_class[i] for i in range(len(idx_to_class))]

        # Confusion Matrix
        from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
        cm = confusion_matrix(all_labels, all_preds)
        prec, rec, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average=None)

        print("\nPer-Class Metrics on Test Cards:")
        per_class_metrics = {}
        for i, c_name in enumerate(class_names):
            per_class_metrics[c_name] = {
                "precision": float(round(prec[i], 4)),
                "recall": float(round(rec[i], 4)),
                "f1_score": float(round(f1[i], 4))
            }
            print(f"  {c_name:15s} | Precision: {prec[i]:.4f} | Recall: {rec[i]:.4f} | F1: {f1[i]:.4f}")

        print("\nConfusion Matrix (Rows: Actual, Cols: Predicted):")
        print(f"               {class_names[0]:13s} {class_names[1]:13s} {class_names[2]:13s}")
        for r_idx, row in enumerate(cm):
            print(f"  {class_names[r_idx]:13s} {row[0]:13d} {row[1]:13d} {row[2]:13d}")

        eval_summary = {
            "model_version": "v2",
            "best_val_accuracy": float(round(best_val_acc, 4)),
            "test_accuracy": float(round(test_acc, 4)),
            "per_class_metrics": per_class_metrics,
            "confusion_matrix": cm.tolist(),
            "class_names": class_names
        }
        with open(os.path.join(self.model_dir, "vision_evaluation_report.json"), "w") as f:
            json.dump(eval_summary, f, indent=2)

        print(f"\nSaved v2 vision model artifacts and evaluation report to '{self.model_dir}/'")
        return eval_summary

    def load_model(self):
        weight_path = os.path.join(self.model_dir, "best_image_model.pt")
        if os.path.exists(weight_path):
            self.model.load_state_dict(torch.load(weight_path, map_location=self.device))
            self.model.eval()
            return True
        return False

    def predict_image(self, image_path_or_pil):
        self.load_model()
        self.model.eval()

        if isinstance(image_path_or_pil, str):
            image = Image.open(image_path_or_pil).convert("RGB")
        else:
            image = image_path_or_pil.convert("RGB")

        tensor_img = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(tensor_img)
            probabilities = torch.softmax(outputs, dim=1)[0].cpu().numpy()

        labels_path = os.path.join(self.model_dir, "labels.json")
        if os.path.exists(labels_path):
            try:
                with open(labels_path, "r", encoding="utf-8") as f:
                    class_to_idx = json.load(f)
                idx_to_class = {v: k for k, v in class_to_idx.items()}
                class_names = [idx_to_class[i] for i in range(len(idx_to_class))]
            except Exception:
                class_names = sorted(CLASSES)
        else:
            class_names = sorted(CLASSES)

        prob_dict = {}
        for idx, cls_name in enumerate(class_names):
            prob_dict[cls_name] = float(round(probabilities[idx], 4))

        top_idx = int(np.argmax(probabilities))
        predicted_class = class_names[top_idx]
        top_confidence = float(round(probabilities[top_idx], 4))

        return {
            "predicted_class": predicted_class,
            "top_confidence": top_confidence,
            "probabilities": prob_dict
        }

if __name__ == "__main__":
    pipeline = ImageClassifierPipelineV2()
    pipeline.train_model(epochs=4)
