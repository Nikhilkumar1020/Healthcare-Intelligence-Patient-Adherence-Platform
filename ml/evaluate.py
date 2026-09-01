"""
ml/evaluate.py
Model evaluation utilities.
Computes and prints all standard classification metrics.
"""
import logging
from typing import Dict, Any
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix
)

logger = logging.getLogger(__name__)


def compute_metrics(y_true, y_pred, y_proba, model_name: str = "") -> Dict[str, Any]:
    """Compute all classification metrics. Returns dict."""
    cm = confusion_matrix(y_true, y_pred)
    return {
        "model_name": model_name,
        "accuracy":   round(float(accuracy_score(y_true, y_pred)), 4),
        "precision":  round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall":     round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score":   round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc":    round(float(roc_auc_score(y_true, y_proba)), 4),
        "confusion_matrix": cm.tolist(),
        "tn": int(cm[0][0]), "fp": int(cm[0][1]),
        "fn": int(cm[1][0]), "tp": int(cm[1][1]),
    }


def print_metrics(metrics: Dict[str, Any]) -> None:
    name = metrics.get("model_name", "Model")
    logger.info(f"\n  {name}:")
    logger.info(f"    Accuracy:  {metrics['accuracy']:.4f}")
    logger.info(f"    Precision: {metrics['precision']:.4f}")
    logger.info(f"    Recall:    {metrics['recall']:.4f}   ← key for risk prioritization")
    logger.info(f"    F1 Score:  {metrics['f1_score']:.4f}")
    logger.info(f"    ROC-AUC:   {metrics['roc_auc']:.4f}  ← key for risk prioritization")
    cm = metrics["confusion_matrix"]
    logger.info(f"    Confusion Matrix:")
    logger.info(f"      TN={metrics['tn']}  FP={metrics['fp']}")
    logger.info(f"      FN={metrics['fn']}  TP={metrics['tp']}")
