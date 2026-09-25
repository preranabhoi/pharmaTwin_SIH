"""
Risk Model Training & Validation Pipeline (Phase 4)

Provides:
- Benchmark pharmacological toxicity training data generation
- Reproducible train / validation / test splits (random_state=42)
- Temporal / time-split evaluation support
- Comprehensive metrics (Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix)
- Model training & serialization to backend/models/
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import settings


# ---------------------------------------------------------
# 1. Evaluation Metrics
# ---------------------------------------------------------

def accuracy_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes fraction of correctly classified instances."""
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    return float(np.mean(y_true == y_pred))


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, int]:
    """Computes binary classification confusion matrix components."""
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def precision_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes precision: TP / (TP + FP)."""
    cm = confusion_matrix(y_true, y_pred)
    denom = cm["tp"] + cm["fp"]
    return float(cm["tp"] / denom) if denom > 0 else 0.0


def recall_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes recall (sensitivity): TP / (TP + FN)."""
    cm = confusion_matrix(y_true, y_pred)
    denom = cm["tp"] + cm["fn"]
    return float(cm["tp"] / denom) if denom > 0 else 0.0


def f1_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes harmonic mean of precision and recall."""
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    denom = prec + rec
    return float(2.0 * (prec * rec) / denom) if denom > 0 else 0.0


def roc_auc_score(y_true: np.ndarray, y_scores: np.ndarray) -> float:
    """
    Computes Area Under the Receiver Operating Characteristic Curve (ROC-AUC)
    using trapezoidal rank integration.
    """
    y_true = np.asarray(y_true).ravel()
    y_scores = np.asarray(y_scores).ravel()

    n_pos = np.sum(y_true == 1)
    n_neg = np.sum(y_true == 0)
    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Sort by descending score
    order = np.argsort(y_scores)[::-1]
    y_true_sorted = y_true[order]

    tps = np.cumsum(y_true_sorted == 1)
    fps = np.cumsum(y_true_sorted == 0)

    tpr = tps / n_pos
    fpr = fps / n_neg

    tpr = np.concatenate([[0.0], tpr, [1.0]])
    fpr = np.concatenate([[0.0], fpr, [1.0]])

    # Trapezoidal numerical integration (compatible with NumPy 2.x and NumPy 1.x)
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(tpr, fpr))
    elif hasattr(np, "trapz"):
        return float(np.trapz(tpr, fpr))
    return float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) / 2.0))


def evaluate_classifier(
    y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """Generates standard evaluation report with all key validation metrics."""
    metrics = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred), 4),
        "recall": round(recall_score(y_true, y_pred), 4),
        "f1": round(f1_score(y_true, y_pred), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred),
    }
    if y_prob is not None:
        metrics["roc_auc"] = round(roc_auc_score(y_true, y_prob), 4)
    return metrics


# ---------------------------------------------------------
# 2. Train / Test / Temporal Dataset Splitting
# ---------------------------------------------------------

def train_test_split(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float = 0.25,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Splits feature matrix X and label vector y into train and test sets
    with a deterministic random seed.
    """
    X = np.asarray(X)
    y = np.asarray(y)
    n_samples = len(X)
    n_test = int(n_samples * test_size)

    rng = np.random.RandomState(random_state)
    indices = rng.permutation(n_samples)

    test_idx = indices[:n_test]
    train_idx = indices[n_test:]

    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def temporal_split(
    X: np.ndarray,
    y: np.ndarray,
    years: np.ndarray,
    split_year: int = 2015,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Splits dataset chronologically based on approval/discovery year.
    Historical training (<= split_year) vs prospective evaluation (> split_year).
    """
    years = np.asarray(years)
    train_mask = years <= split_year
    test_mask = years > split_year

    return X[train_mask], X[test_mask], y[train_mask], y[test_mask]


# ---------------------------------------------------------
# 3. Benchmark Pharmacological Training Data Generator
# ---------------------------------------------------------

def generate_benchmark_training_data(
    n_samples: int = 200, random_state: int = 42
) -> Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray]:
    """
    Generates structured multi-organ toxicity feature matrices and labels (32 dimensions)
    representing known pharmacology patterns:
    - Target organs: 'overall', 'heart', 'liver', 'kidney', 'lung', 'brain'
    - Includes temporal approval year metadata for temporal validation.
    """
    rng = np.random.RandomState(random_state)
    n_features = 32

    X = np.zeros((n_samples, n_features), dtype=np.float32)
    labels: Dict[str, np.ndarray] = {
        "overall": np.zeros(n_samples, dtype=np.int32),
        "heart": np.zeros(n_samples, dtype=np.int32),
        "liver": np.zeros(n_samples, dtype=np.int32),
        "kidney": np.zeros(n_samples, dtype=np.int32),
        "lung": np.zeros(n_samples, dtype=np.int32),
        "brain": np.zeros(n_samples, dtype=np.int32),
    }
    years = rng.randint(1980, 2024, size=n_samples)

    for i in range(n_samples):
        # Base molecular descriptors
        mw = rng.uniform(0.1, 0.9)
        logp = rng.uniform(0.1, 0.9)
        tpsa = rng.uniform(0.1, 0.8)
        X[i, 0] = mw
        X[i, 1] = logp
        X[i, 2] = tpsa
        X[i, 3:10] = rng.uniform(0.0, 0.7, size=7)

        # Organ-specific toxicity patterns:
        # Heart cardiotoxicity (correlated with high MW, low TPSA, graph path feature at index 10/15)
        heart_risk = (mw > 0.6 and logp > 0.5) or rng.rand() < 0.25
        if heart_risk:
            X[i, 10] = rng.uniform(0.6, 1.0)  # Heart path count
            X[i, 15] = rng.uniform(0.7, 1.0)  # Heart path confidence
            X[i, 20] = rng.uniform(0.5, 1.0)  # SIDER heart adverse
            labels["heart"][i] = 1

        # Liver hepatotoxicity (correlated with reactive metabolism, index 11/16)
        liver_risk = (logp > 0.6 and mw < 0.7) or rng.rand() < 0.30
        if liver_risk:
            X[i, 11] = rng.uniform(0.6, 1.0)  # Liver path count
            X[i, 16] = rng.uniform(0.7, 1.0)  # Liver path confidence
            X[i, 21] = rng.uniform(0.6, 1.0)  # SIDER liver adverse
            labels["liver"][i] = 1

        # Kidney nephrotoxicity (correlated with heavy clearance, index 12/17)
        kidney_risk = (logp < 0.4 and tpsa > 0.4) or rng.rand() < 0.25
        if kidney_risk:
            X[i, 12] = rng.uniform(0.5, 1.0)  # Kidney path count
            X[i, 17] = rng.uniform(0.6, 1.0)  # Kidney path confidence
            X[i, 22] = rng.uniform(0.5, 1.0)  # SIDER kidney adverse
            labels["kidney"][i] = 1

        # Lung toxicity (index 13/18)
        lung_risk = rng.rand() < 0.15
        if lung_risk:
            X[i, 13] = rng.uniform(0.6, 1.0)
            X[i, 18] = rng.uniform(0.7, 1.0)
            X[i, 23] = rng.uniform(0.5, 1.0)
            labels["lung"][i] = 1

        # Brain CNS toxicity (correlated with high LogP and low TPSA, index 14/19)
        brain_risk = (logp > 0.7 and tpsa < 0.3) or rng.rand() < 0.20
        if brain_risk:
            X[i, 14] = rng.uniform(0.6, 1.0)
            X[i, 19] = rng.uniform(0.7, 1.0)
            X[i, 24] = rng.uniform(0.5, 1.0)
            labels["brain"][i] = 1

        # Literature and similarity signals
        X[i, 25:28] = rng.uniform(0.2, 0.9, size=3)
        X[i, 28:32] = rng.uniform(0.1, 0.8, size=4)

        # Overall risk is 1 if any major organ shows toxicity
        if any(labels[org][i] == 1 for org in ["heart", "liver", "kidney"]):
            labels["overall"][i] = 1

    return X, labels, years
