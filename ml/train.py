"""
ml/train.py
Train Logistic Regression and Random Forest models.
Compares metrics and saves the best model.

Usage:
    python ml/train.py
"""
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix
)
from imblearn.over_sampling import SMOTE

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from ml.features import build_features, FEATURE_COLS, TARGET_COL
from ml.model_utils import save_model
from ml.evaluate import compute_metrics, print_metrics


def train() -> None:
    # ── 1. Build features ─────────────────────────────────
    logger.info("[train] Building feature matrix...")
    df = build_features()

    X = df[FEATURE_COLS].copy()
    y = df[TARGET_COL].copy()

    logger.info(f"[train] Dataset: {len(df)} patients | "
                f"Drop-off rate: {y.mean():.2%} | "
                f"Features: {len(FEATURE_COLS)}")

    # ── 2. Split ────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # ── 3. Handle class imbalance ───────────────────────────
    sm = SMOTE(random_state=42)
    X_train_res, y_train_res = sm.fit_resample(X_train, y_train)
    logger.info(f"[train] After SMOTE: {len(X_train_res)} training samples")

    # ── 4. Model 1: Logistic Regression ────────────────────
    logger.info("[train] Training Logistic Regression...")
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model",  LogisticRegression(max_iter=500, random_state=42, C=1.0)),
    ])
    lr_pipeline.fit(X_train_res, y_train_res)
    lr_preds  = lr_pipeline.predict(X_test)
    lr_proba  = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_metrics = compute_metrics(y_test, lr_preds, lr_proba, "Logistic Regression")

    # ── 5. Model 2: Random Forest ───────────────────────────
    logger.info("[train] Training Random Forest...")
    rf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model",  RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_leaf=10,
            random_state=42, n_jobs=-1, class_weight="balanced"
        )),
    ])
    rf_pipeline.fit(X_train_res, y_train_res)
    rf_preds  = rf_pipeline.predict(X_test)
    rf_proba  = rf_pipeline.predict_proba(X_test)[:, 1]
    rf_metrics = compute_metrics(y_test, rf_preds, rf_proba, "Random Forest")

    # ── 6. Compare ──────────────────────────────────────────
    logger.info("\n" + "=" * 55)
    logger.info("MODEL COMPARISON")
    logger.info("=" * 55)
    print_metrics(lr_metrics)
    print_metrics(rf_metrics)

    # Select winner: prioritise ROC-AUC then Recall
    if rf_metrics["roc_auc"] >= lr_metrics["roc_auc"]:
        best_model, best_metrics, best_name = rf_pipeline, rf_metrics, "random_forest"
    else:
        best_model, best_metrics, best_name = lr_pipeline, lr_metrics, "logistic_regression"

    logger.info(f"\n[train] Selected model: {best_name} "
                f"(ROC-AUC={best_metrics['roc_auc']:.4f})")

    # ── 7. Feature importance (RF only) ────────────────────
    if best_name == "random_forest":
        importances = rf_pipeline.named_steps["model"].feature_importances_
        fi = pd.Series(importances, index=FEATURE_COLS).sort_values(ascending=False)
        logger.info("\nTop 10 Feature Importances:")
        for feat, imp in fi.head(10).items():
            logger.info(f"  {feat:<35} {imp:.4f}")
        best_metrics["feature_importances"] = fi.head(15).to_dict()

    # ── 8. Save model ───────────────────────────────────────
    version = datetime.now().strftime("v%Y%m%d")
    metadata = {
        "model_type":   best_name,
        "feature_cols": FEATURE_COLS,
        "target_col":   TARGET_COL,
        "metrics":      best_metrics,
        "n_train":      len(X_train),
        "n_test":       len(X_test),
    }
    save_model(best_model, best_name, version, metadata)

    # Also save as "champion" for easy loading
    save_model(best_model, "champion", version, metadata)

    logger.info("[train] Training complete.")


if __name__ == "__main__":
    train()
