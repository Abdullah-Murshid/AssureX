"""
AssureX Claim Engine - Visual Summary Card Image Classifier (GTM Version)
Provides single-image inference for Claim Summary Cards:
- Uses Google Teachable Machine (TensorFlow/Keras)
- Predicts 3 classes: 'Valid Claim', 'Invalid Claim', 'Manual Review'
"""

import os

# The exported H5 is a Keras 2.x model. TensorFlow 2.16+ defaults to Keras 3,
# which cannot deserialize it; route tf.keras through the tf-keras bridge.
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import numpy as np
from PIL import Image

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("TensorFlow is not installed. Please run `pip install tensorflow`")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../"))

def _resolve_gtm_dir():
    candidates = [
        os.path.join(PROJECT_ROOT, "06. Google Teachable Machine Model Files"),
        os.path.join(PROJECT_ROOT, "Google Teachable Machine Model Files"),
        os.path.join(PROJECT_ROOT, "GTM Models"),
        os.path.join(PROJECT_ROOT, "Google Teachable Machine Evidence"),
        os.path.join(PROJECT_ROOT, "02. Complete Source Code", "GTM Models"),
        os.path.join(PROJECT_ROOT, "Source Code", "GTM Models"),
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "keras_model.h5")):
            return c
    return os.path.join(PROJECT_ROOT, "GTM Models")

GTM_DIR = _resolve_gtm_dir()
MODEL_PATH = os.path.join(GTM_DIR, "keras_model.h5")
LABELS_PATH = os.path.join(GTM_DIR, "labels.txt")

class ImageClassifierPipeline:
    def __init__(self, model_path=MODEL_PATH, labels_path=LABELS_PATH):
        self.model_path = model_path
        self.labels_path = labels_path
        self.model = None
        self.class_names = []
        self._loaded = False

    def load_model(self, force_reload=False):
        if not TF_AVAILABLE:
            return
        if self._loaded and not force_reload:
            return
            
        if not os.path.exists(self.model_path):
            print(f"Warning: GTM Model not found at {self.model_path}")
            return

        try:
            class PatchedDepthwiseConv2D(tf.keras.layers.DepthwiseConv2D):
                def __init__(self, *args, **kwargs):
                    kwargs.pop('groups', None)
                    super().__init__(*args, **kwargs)

            try:
                self.model = tf.keras.models.load_model(self.model_path, compile=False)
            except Exception:
                self.model = tf.keras.models.load_model(
                    self.model_path,
                    compile=False,
                    custom_objects={"DepthwiseConv2D": PatchedDepthwiseConv2D}
                )
            
            self.class_names = []
            if os.path.exists(self.labels_path):
                with open(self.labels_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(" ", 1)
                        if len(parts) > 1:
                            self.class_names.append(parts[1])
                        else:
                            self.class_names.append(parts[0])
            else:
                self.class_names = ["Valid Claim", "Invalid Claim", "Manual Review"]
                
            self._loaded = True
            print("GTM Model loaded successfully!")
        except Exception as e:
            print(f"Error loading GTM Model: {e}")

    def predict_image(self, image_path_or_pil):
        """
        Predicts class and probabilities for a visual Claim Summary Card image.
        Returns a dict matching the structure required by fusion.py
        """
        if not TF_AVAILABLE:
            raise RuntimeError("TensorFlow is required for the Teachable Machine model")
        if self.model is None:
            self.load_model()
        if self.model is None:
            raise RuntimeError("Teachable Machine model is unavailable")

        try:
            if isinstance(image_path_or_pil, str):
                image = Image.open(image_path_or_pil).convert("RGB")
            else:
                image = image_path_or_pil.convert("RGB")

            image = image.resize((224, 224))
            image_array = np.asarray(image)

            normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1.0

            data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
            data[0] = normalized_image_array

            prediction = self.model.predict(data, verbose=0)
            probabilities = prediction[0]

            top_index = int(np.argmax(probabilities))
            
            if top_index < len(self.class_names):
                top_class = self.class_names[top_index]
            else:
                top_class = "Manual Review"
                
            top_confidence = float(round(float(probabilities[top_index]), 4))

            prob_dict = {}
            for i, cls_name in enumerate(self.class_names):
                if i < len(probabilities):
                    prob_dict[cls_name] = float(round(float(probabilities[i]), 4))

            return {
                "predicted_class": top_class,
                "top_confidence": top_confidence,
                "probabilities": prob_dict
            }
        except Exception as e:
            print(f"GTM Vision prediction error: {e}")
            raise RuntimeError("Teachable Machine inference failed") from e

if __name__ == "__main__":
    pipeline = ImageClassifierPipeline()
    pipeline.load_model()
