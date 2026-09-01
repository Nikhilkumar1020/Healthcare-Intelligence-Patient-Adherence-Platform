"""
ml/model_utils.py
Model save/load utilities with versioning.
"""
import os
import json
import joblib
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def save_model(model: Any, model_name: str, version: str,
               metadata: Optional[Dict] = None) -> Path:
    """Save model artifact with versioned filename and metadata JSON."""
    fname = MODELS_DIR / f"{model_name}_{version}.joblib"
    joblib.dump(model, fname)

    meta = {
        "model_name":  model_name,
        "version":     version,
        "saved_at":    datetime.now().isoformat(),
        **(metadata or {}),
    }
    meta_path = MODELS_DIR / f"{model_name}_{version}_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"[model_utils] Saved: {fname.name}")
    return fname


def load_model(model_name: str, version: Optional[str] = None) -> Any:
    """Load the latest (or versioned) model. Raises FileNotFoundError if missing."""
    if version:
        path = MODELS_DIR / f"{model_name}_{version}.joblib"
    else:
        # Find latest
        candidates = sorted(MODELS_DIR.glob(f"{model_name}_*.joblib"))
        if not candidates:
            raise FileNotFoundError(
                f"No saved model found for '{model_name}'. "
                "Run `python ml/train.py` first."
            )
        path = candidates[-1]

    logger.info(f"[model_utils] Loading: {path.name}")
    return joblib.load(path)


def load_model_metadata(model_name: str, version: Optional[str] = None) -> Dict:
    """Load metadata JSON for a model."""
    if version:
        path = MODELS_DIR / f"{model_name}_{version}_meta.json"
    else:
        candidates = sorted(MODELS_DIR.glob(f"{model_name}_*_meta.json"))
        if not candidates:
            return {}
        path = candidates[-1]
    with open(path) as f:
        return json.load(f)


def list_models() -> list:
    """List all saved model files."""
    return [p.stem for p in sorted(MODELS_DIR.glob("*.joblib"))]
