"""
Entry-point wrappers for all uv/pyproject.toml script commands.
Each function is a thin shim that delegates to the real module's __main__ block
so that `uv run <command>` works without needing to reference the raw file path.
"""

import runpy
import sys
from pathlib import Path

# Resolve the project root (two levels up from this file's package)
_SRC = Path(__file__).resolve().parent.parent       # src/
_ROOT = _SRC.parent                                  # project root


def _run(rel_path: str) -> None:
    """Execute a script relative to the project root via runpy."""
    target = _ROOT / rel_path
    if not target.exists():
        print(f"[assurex] ERROR: script not found: {target}", file=sys.stderr)
        sys.exit(1)
    runpy.run_path(str(target), run_name="__main__")


# ── Entry-points ────────────────────────────────────────────────────────────

def init_db() -> None:
    """Initialize the SQLite / SQLAlchemy database."""
    _run("src/assurex_claim_engine/db/database.py")


def generate_dataset() -> None:
    """Generate the 1,500-claim synthetic dataset."""
    _run("dataset_generator/generate_dataset.py")


def generate_summary_cards() -> None:
    """Render summary-card PNG images for every claim."""
    _run("dataset_generator/generate_summary_cards.py")


def train_tabular() -> None:
    """Train the tabular (scikit-learn) ML models."""
    _run("src/assurex_claim_engine/models/tabular_model.py")


def train_vision() -> None:
    """Train the vision image-classification model."""
    _run("src/assurex_claim_engine/models/image_classifier.py")


def generate_report() -> None:
    """Generate the 30-claim evaluation report."""
    _run("reports/generate_30_claim_report.py")
