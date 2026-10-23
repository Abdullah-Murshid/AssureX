"""Background model registry shared by every API request.

Mirrors the legacy FastAPI startup behaviour: the database is ready
immediately, while the tabular XGBoost model and the Teachable Machine vision
model load on a background thread. Claim evaluation endpoints block until the
models are ready (or return HTTP 503 after the configured timeout).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class ModelNotReady(RuntimeError):
    """Raised when a model dependent endpoint is called too early."""


class ModelRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._loaded = threading.Event()
        self.tabular = None
        self.vision = None
        self.fusion = None
        self.ocr = None
        self.error: Optional[str] = None
        self.load_seconds: Optional[float] = None

    # ------------------------------------------------------------------ #
    @property
    def python_model_ready(self) -> bool:
        return getattr(self.tabular, "best_model", None) is not None

    @property
    def gtm_model_ready(self) -> bool:
        return getattr(self.vision, "model", None) is not None

    @property
    def ready(self) -> bool:
        return self.python_model_ready and self.gtm_model_ready

    def status(self) -> dict:
        return {
            "models_ready": self.ready,
            "python_model_ready": self.python_model_ready,
            "gtm_model_ready": self.gtm_model_ready,
            "load_seconds": self.load_seconds,
            "error": self.error,
        }

    # ------------------------------------------------------------------ #
    def start_in_background(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._thread = threading.Thread(
                target=self._load, daemon=True, name="assurex-model-loader"
            )
            self._thread.start()

    def _load(self) -> None:
        started = time.time()
        try:
            # Framework-agnostic domain code, imported lazily so Django
            # management commands stay fast.
            from assurex_claim_engine.decision.fusion import DecisionFusionEngine
            from assurex_claim_engine.models.image_classifier import (
                ImageClassifierPipeline,
            )
            from assurex_claim_engine.models.tabular_model import TabularClaimClassifier
            from assurex_claim_engine.ocr.parser import DocumentOCRParser

            self.fusion = DecisionFusionEngine()
            self.ocr = DocumentOCRParser()

            tabular = TabularClaimClassifier()
            t0 = time.time()
            tabular.load_artifacts()
            logger.info("Tabular model loaded in %.2fs", time.time() - t0)

            vision = ImageClassifierPipeline()
            t1 = time.time()
            vision.load_model()
            logger.info("GTM vision model loaded in %.2fs", time.time() - t1)

            self.tabular = tabular
            self.vision = vision
        except Exception as exc:  # pragma: no cover - depends on local model files
            self.error = f"{type(exc).__name__}: {exc}"
            logger.exception("Failed to load AssureX models")
        finally:
            self.load_seconds = round(time.time() - started, 2)
            self._loaded.set()

    def ocr_parser(self):
        """Return the OCR parser, creating it on demand (it is lightweight)."""
        if self.ocr is None:
            from assurex_claim_engine.ocr.parser import DocumentOCRParser

            self.ocr = DocumentOCRParser()
        return self.ocr

    def ensure_ready(self) -> None:
        if self.ready:
            return
        self.start_in_background()
        if not self._loaded.wait(timeout=settings.MODEL_READY_TIMEOUT_SECONDS):
            raise ModelNotReady(
                "Models are still loading. Retry in a moment."
            )
        if not self.ready:
            raise ModelNotReady(
                self.error or "Models could not be loaded. Check server logs."
            )


registry = ModelRegistry()
