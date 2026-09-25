"""
Risk Prediction & Reasoning Engine (Phase 4)

Provides:
- Abstract Risk Model Interface (BaseRiskModel)
- Pluggable ML Model Architectures:
    - RandomForestRiskModel (Random Forest ensemble)
    - LogisticRegressionRiskModel (Regularized Logistic Regression)
    - EnsembleRiskModel (Multi-model consensus)
- Multi-Organ Toxicity Risk Predictor (Heart, Liver, Kidney, Lung, Brain, Overall)
- Multi-Modal Evidence Alignment & Feature Integration
- Evidence Sufficiency Gating
- Traceable Explainability Metadata & Feature Importances
- SQLite Audit Trail & Persistence
"""

from __future__ import annotations

import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from app.config import settings
from app.database import get_risk_prediction, save_risk_prediction
from app.evidence_fusion import (
    FusedEvidenceContext,
    align_and_fuse_evidence,
    calculate_evidence_strength,
    calculate_prediction_confidence,
    evaluate_evidence_sufficiency,
)
from app.schemas import (
    DrugRiskPredictionRequest,
    DrugRiskPredictionResponse,
    EvidenceSufficiencyCheck,
    GraphPathModel,
    MolecularSimilarityMatch,
    NormalizedEvidence,
    OrganRiskAssessment,
    ProcessingStatus,
    RiskExplainabilityMetadata,
)
from app.training import generate_benchmark_training_data


# ---------------------------------------------------------
# Feature Names Mapping (32 Aligned Dimensions)
# ---------------------------------------------------------

FEATURE_NAMES = [
    "molecular_weight_norm",
    "logp_norm",
    "tpsa_norm",
    "hbd_norm",
    "hba_norm",
    "rotatable_bonds_norm",
    "heavy_atom_count_norm",
    "ring_count_norm",
    "aromatic_ring_count_norm",
    "fingerprint_density",
    "kg_paths_heart",
    "kg_paths_liver",
    "kg_paths_kidney",
    "kg_paths_lung",
    "kg_paths_brain",
    "kg_conf_heart",
    "kg_conf_liver",
    "kg_conf_kidney",
    "kg_conf_lung",
    "kg_conf_brain",
    "adverse_heart_count",
    "adverse_liver_count",
    "adverse_kidney_count",
    "adverse_lung_count",
    "adverse_brain_count",
    "literature_count",
    "literature_max_confidence",
    "evidence_density",
    "tanimoto_sim_top1",
    "tanimoto_sim_top2",
    "tanimoto_sim_mean",
    "high_similarity_flag",
]

ORGAN_SYSTEMS = {
    "heart": "Heart (Cardiovascular System)",
    "liver": "Liver (Hepatic System)",
    "kidney": "Kidney (Renal System)",
    "lung": "Lung (Respiratory System)",
    "brain": "Brain (Central Nervous System)",
}

ORGAN_PATH_INDEX = {
    "heart": 10,
    "liver": 11,
    "kidney": 12,
    "lung": 13,
    "brain": 14,
}


def classify_risk_category(score: float) -> str:
    """
    Maps numerical risk probability to research prototype tiers:
    - Low: score < 0.35
    - Moderate: 0.35 <= score < 0.70
    - High: score >= 0.70
    """
    if score >= 0.70:
        return "High"
    elif score >= 0.35:
        return "Moderate"
    return "Low"


# ---------------------------------------------------------
# 1. Base Risk Model Abstraction
# ---------------------------------------------------------

class BaseRiskModel(ABC):
    """Abstract interface for all PharmaTwin risk reasoning classifiers."""

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaseRiskModel":
        """Trains the risk model on feature matrix X and labels y."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts binary classification labels (0 or 1)."""
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predicts risk probability estimates in [0.0, 1.0]."""
        pass

    @abstractmethod
    def get_feature_importances(self) -> np.ndarray:
        """Returns relative importance weights for the 32 feature dimensions."""
        pass

    @abstractmethod
    def save(self, filepath: Union[str, Path]) -> None:
        """Serializes model parameters to disk."""
        pass

    @abstractmethod
    def load(self, filepath: Union[str, Path]) -> "BaseRiskModel":
        """Loads serialized model parameters from disk."""
        pass


# ---------------------------------------------------------
# 2. Decision Tree & Random Forest Implementation
# ---------------------------------------------------------

class _DecisionTreeNode:
    def __init__(
        self,
        feature: Optional[int] = None,
        threshold: Optional[float] = None,
        left: Optional["_DecisionTreeNode"] = None,
        right: Optional["_DecisionTreeNode"] = None,
        *,
        value: Optional[float] = None,
    ):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value

    @property
    def is_leaf(self) -> bool:
        return self.value is not None

    def to_dict(self) -> Dict[str, Any]:
        if self.is_leaf:
            return {"value": float(self.value) if self.value is not None else None}
        return {
            "feature": int(self.feature) if self.feature is not None else None,
            "threshold": float(self.threshold) if self.threshold is not None else None,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["_DecisionTreeNode"]:
        if d is None:
            return None
        if "value" in d and d["value"] is not None:
            return cls(value=float(d["value"]))
        return cls(
            feature=int(d["feature"]) if d.get("feature") is not None else None,
            threshold=float(d["threshold"]) if d.get("threshold") is not None else None,
            left=cls.from_dict(d.get("left")),
            right=cls.from_dict(d.get("right")),
        )


class _DecisionTreeClassifier:
    def __init__(
        self,
        max_depth: int = 5,
        min_samples_split: int = 2,
        max_features: Optional[int] = None,
        random_state: Optional[int] = None,
    ):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.random_state = random_state
        self.root: Optional[_DecisionTreeNode] = None
        self.feature_importances_ = np.zeros(32, dtype=np.float64)

    def _gini(self, y: np.ndarray) -> float:
        if len(y) == 0:
            return 0.0
        p = np.mean(y)
        return 1.0 - (p ** 2 + (1.0 - p) ** 2)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_DecisionTreeClassifier":
        rng = np.random.RandomState(self.random_state)
        n_features = X.shape[1]
        self.feature_importances_ = np.zeros(n_features, dtype=np.float64)
        self.root = self._grow_tree(X, y, depth=0, rng=rng)
        
        # Normalize feature importances
        total = np.sum(self.feature_importances_)
        if total > 0:
            self.feature_importances_ /= total
        return self

    def _grow_tree(
        self, X: np.ndarray, y: np.ndarray, depth: int, rng: np.random.RandomState
    ) -> _DecisionTreeNode:
        n_samples, n_features = X.shape
        n_labels = len(np.unique(y))

        # Stopping conditions
        if (
            depth >= self.max_depth
            or n_labels <= 1
            or n_samples < self.min_samples_split
        ):
            leaf_value = float(np.mean(y)) if len(y) > 0 else 0.0
            return _DecisionTreeNode(value=leaf_value)

        # Feature subset selection
        max_f = self.max_features or int(np.sqrt(n_features))
        max_f = max(1, min(n_features, max_f))
        feature_indices = rng.choice(n_features, size=max_f, replace=False)

        best_gain = -1.0
        best_feat, best_thresh = None, None
        current_gini = self._gini(y)

        for feat in feature_indices:
            thresholds = np.unique(X[:, feat])
            if len(thresholds) > 10:
                thresholds = np.quantile(thresholds, np.linspace(0.1, 0.9, 9))
            for thresh in thresholds:
                left_mask = X[:, feat] <= thresh
                right_mask = ~left_mask
                if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
                    continue

                gini_left = self._gini(y[left_mask])
                gini_right = self._gini(y[right_mask])
                w_left = np.sum(left_mask) / n_samples
                w_right = np.sum(right_mask) / n_samples
                gain = current_gini - (w_left * gini_left + w_right * gini_right)

                if gain > best_gain:
                    best_gain = gain
                    best_feat = feat
                    best_thresh = float(thresh)

        if best_gain <= 1e-6 or best_feat is None:
            return _DecisionTreeNode(value=float(np.mean(y)))

        self.feature_importances_[best_feat] += best_gain * n_samples

        left_mask = X[:, best_feat] <= best_thresh
        right_mask = ~left_mask
        left_child = self._grow_tree(X[left_mask], y[left_mask], depth + 1, rng)
        right_child = self._grow_tree(X[right_mask], y[right_mask], depth + 1, rng)
        return _DecisionTreeNode(
            feature=best_feat,
            threshold=best_thresh,
            left=left_child,
            right=right_child,
        )

    def _predict_sample(self, x: np.ndarray, node: Optional[_DecisionTreeNode]) -> float:
        if node is None:
            return 0.5
        if node.is_leaf:
            return float(node.value if node.value is not None else 0.5)
        if x[node.feature] <= node.threshold:
            return self._predict_sample(x, node.left)
        return self._predict_sample(x, node.right)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        return np.array([self._predict_sample(x, self.root) for x in X])


class RandomForestRiskModel(BaseRiskModel):
    """
    Random Forest Risk Classifier:
    Ensemble of decorrelated decision trees with bagging and feature subsampling.
    """

    def __init__(
        self,
        n_estimators: int = 15,
        max_depth: int = 6,
        min_samples_split: int = 2,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.random_state = random_state
        self.trees: List[_DecisionTreeClassifier] = []
        self.feature_importances_ = np.zeros(32, dtype=np.float64)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestRiskModel":
        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y, dtype=np.int32)
        n_samples, n_features = X.shape
        rng = np.random.RandomState(self.random_state)

        self.trees = []
        accumulated_importances = np.zeros(n_features, dtype=np.float64)

        for i in range(self.n_estimators):
            # Bootstrap sample
            boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
            X_boot, y_boot = X[boot_idx], y[boot_idx]

            tree = _DecisionTreeClassifier(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                max_features=int(np.sqrt(n_features)),
                random_state=int(rng.randint(0, 100000)),
            )
            tree.fit(X_boot, y_boot)
            self.trees.append(tree)
            accumulated_importances += tree.feature_importances_

        total_imp = np.sum(accumulated_importances)
        if total_imp > 0:
            self.feature_importances_ = accumulated_importances / total_imp
        else:
            self.feature_importances_ = np.ones(n_features, dtype=np.float64) / n_features
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        if not self.trees:
            return np.full(len(X), 0.5, dtype=np.float32)
        all_tree_preds = np.array([tree.predict_proba(X) for tree in self.trees])
        return np.mean(all_tree_preds, axis=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        probas = self.predict_proba(X)
        return (probas >= 0.5).astype(np.int32)

    def get_feature_importances(self) -> np.ndarray:
        return self.feature_importances_

    def save(self, filepath: Union[str, Path]) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "n_estimators": int(self.n_estimators),
            "max_depth": int(self.max_depth),
            "min_samples_split": int(self.min_samples_split),
            "random_state": int(self.random_state),
            "feature_importances": [float(x) for x in self.feature_importances_],
            "trees": [
                {
                    "max_depth": int(t.max_depth),
                    "min_samples_split": int(t.min_samples_split),
                    "max_features": int(t.max_features) if t.max_features is not None else None,
                    "feature_importances": [float(x) for x in t.feature_importances_],
                    "root": t.root.to_dict() if t.root else None,
                }
                for t in self.trees
            ],
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self, filepath: Union[str, Path]) -> "RandomForestRiskModel":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.n_estimators = data["n_estimators"]
        self.max_depth = data["max_depth"]
        self.min_samples_split = data["min_samples_split"]
        self.random_state = data["random_state"]
        self.feature_importances_ = np.array(data["feature_importances"], dtype=np.float64)
        self.trees = []
        for td in data.get("trees", []):
            tree = _DecisionTreeClassifier(
                max_depth=td["max_depth"],
                min_samples_split=td["min_samples_split"],
                max_features=td["max_features"],
            )
            tree.feature_importances_ = np.array(td["feature_importances"], dtype=np.float64)
            tree.root = _DecisionTreeNode.from_dict(td["root"])
            self.trees.append(tree)
        return self


# ---------------------------------------------------------
# 3. Logistic Regression Implementation (L2 Regularized)
# ---------------------------------------------------------

class LogisticRegressionRiskModel(BaseRiskModel):
    """
    Regularized Logistic Regression Risk Model with Gradient Descent Optimization.
    """

    def __init__(
        self,
        learning_rate: float = 0.05,
        l2_lambda: float = 0.01,
        max_iter: int = 400,
        random_state: int = 42,
    ):
        self.learning_rate = learning_rate
        self.l2_lambda = l2_lambda
        self.max_iter = max_iter
        self.random_state = random_state
        self.weights: Optional[np.ndarray] = None
        self.bias: float = 0.0
        self.feature_importances_ = np.zeros(32, dtype=np.float64)

    def _sigmoid(self, z: np.ndarray) -> np.ndarray:
        z = np.clip(z, -35.0, 35.0)
        return 1.0 / (1.0 + np.exp(-z))

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegressionRiskModel":
        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y, dtype=np.float32)
        n_samples, n_features = X.shape

        rng = np.random.RandomState(self.random_state)
        self.weights = rng.normal(0, 0.01, size=n_features).astype(np.float32)
        self.bias = 0.0

        for _ in range(self.max_iter):
            linear_output = np.dot(X, self.weights) + self.bias
            y_pred = self._sigmoid(linear_output)

            error = y_pred - y
            dw = (np.dot(X.T, error) + self.l2_lambda * self.weights) / n_samples
            db = np.sum(error) / n_samples

            self.weights -= self.learning_rate * dw
            self.bias -= self.learning_rate * db

        abs_weights = np.abs(self.weights)
        total_w = np.sum(abs_weights)
        if total_w > 0:
            self.feature_importances_ = abs_weights / total_w
        else:
            self.feature_importances_ = np.ones(n_features, dtype=np.float64) / n_features
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        if self.weights is None:
            return np.full(len(X), 0.5, dtype=np.float32)
        linear_output = np.dot(X, self.weights) + self.bias
        return self._sigmoid(linear_output)

    def predict(self, X: np.ndarray) -> np.ndarray:
        probas = self.predict_proba(X)
        return (probas >= 0.5).astype(np.int32)

    def get_feature_importances(self) -> np.ndarray:
        return self.feature_importances_

    def save(self, filepath: Union[str, Path]) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "learning_rate": self.learning_rate,
            "l2_lambda": self.l2_lambda,
            "max_iter": self.max_iter,
            "random_state": self.random_state,
            "weights": self.weights.tolist() if self.weights is not None else [],
            "bias": float(self.bias),
            "feature_importances": self.feature_importances_.tolist(),
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self, filepath: Union[str, Path]) -> "LogisticRegressionRiskModel":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.learning_rate = data["learning_rate"]
        self.l2_lambda = data["l2_lambda"]
        self.max_iter = data["max_iter"]
        self.random_state = data["random_state"]
        self.weights = np.array(data["weights"], dtype=np.float32)
        self.bias = float(data["bias"])
        self.feature_importances_ = np.array(data["feature_importances"], dtype=np.float64)
        return self


# ---------------------------------------------------------
# 4. Ensemble Risk Model (RF + LR consensus)
# ---------------------------------------------------------

class EnsembleRiskModel(BaseRiskModel):
    """
    Ensemble Risk Predictor:
    Combines Random Forest non-linear partitioning with Logistic Regression linear margins.
    """

    def __init__(self, random_state: int = 42):
        self.rf = RandomForestRiskModel(random_state=random_state)
        self.lr = LogisticRegressionRiskModel(random_state=random_state)
        self.random_state = random_state

    def fit(self, X: np.ndarray, y: np.ndarray) -> "EnsembleRiskModel":
        self.rf.fit(X, y)
        self.lr.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p_rf = self.rf.predict_proba(X)
        p_lr = self.lr.predict_proba(X)
        return 0.65 * p_rf + 0.35 * p_lr

    def predict(self, X: np.ndarray) -> np.ndarray:
        probas = self.predict_proba(X)
        return (probas >= 0.5).astype(np.int32)

    def get_feature_importances(self) -> np.ndarray:
        return 0.65 * self.rf.get_feature_importances() + 0.35 * self.lr.get_feature_importances()

    def save(self, filepath: Union[str, Path]) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.rf.save(p.with_suffix(".rf.json"))
        self.lr.save(p.with_suffix(".lr.json"))

    def load(self, filepath: Union[str, Path]) -> "EnsembleRiskModel":
        p = Path(filepath)
        self.rf.load(p.with_suffix(".rf.json"))
        self.lr.load(p.with_suffix(".lr.json"))
        return self


# ---------------------------------------------------------
# 5. Multi-Organ Risk Predictor Engine
# ---------------------------------------------------------

class MultiOrganRiskPredictor:
    """
    Coordinates training and multi-organ endpoint risk reasoning.
    Predicts:
    - Overall adverse risk
    - Heart, Liver, Kidney, Lung, Brain toxicity risks
    """

    def __init__(self, model_type: str = "random_forest", random_state: int = 42):
        self.model_type = model_type.lower()
        self.random_state = random_state
        self.models: Dict[str, BaseRiskModel] = {}
        self._init_models()

    def _create_model(self) -> BaseRiskModel:
        if self.model_type == "logistic_regression":
            return LogisticRegressionRiskModel(random_state=self.random_state)
        elif self.model_type == "ensemble":
            return EnsembleRiskModel(random_state=self.random_state)
        return RandomForestRiskModel(random_state=self.random_state)

    def _init_models(self) -> None:
        endpoints = ["overall", "heart", "liver", "kidney", "lung", "brain"]
        for ep in endpoints:
            self.models[ep] = self._create_model()

    def fit_all(self, X: np.ndarray, labels: Dict[str, np.ndarray]) -> "MultiOrganRiskPredictor":
        for ep, model in self.models.items():
            if ep in labels:
                model.fit(X, labels[ep])
        return self

    def predict_endpoint(self, endpoint: str, X: np.ndarray) -> float:
        if endpoint not in self.models:
            return 0.5
        probs = self.models[endpoint].predict_proba(X)
        return float(probs[0]) if len(probs) > 0 else 0.5

    def get_feature_importances(self, endpoint: str = "overall") -> np.ndarray:
        if endpoint in self.models:
            return self.models[endpoint].get_feature_importances()
        return np.ones(32, dtype=np.float64) / 32.0


# Cache of instantiated predictors
_PREDICTOR_CACHE: Dict[str, MultiOrganRiskPredictor] = {}


def get_or_train_predictor(model_type: str = "random_forest") -> MultiOrganRiskPredictor:
    """
    Returns a trained MultiOrganRiskPredictor instance.
    Uses benchmark pharmacological training data with fixed seed for determinism.
    """
    key = model_type.lower()
    if key not in ["random_forest", "logistic_regression", "ensemble"]:
        key = "random_forest"

    if key in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[key]

    X, labels, _ = generate_benchmark_training_data(n_samples=250, random_state=42)
    predictor = MultiOrganRiskPredictor(model_type=key, random_state=42)
    predictor.fit_all(X, labels)
    _PREDICTOR_CACHE[key] = predictor
    return predictor


# ---------------------------------------------------------
# 6. High-Level Risk Prediction & Reasoning Orchestrator
# ---------------------------------------------------------

def predict_drug_risk(
    request: DrugRiskPredictionRequest,
) -> DrugRiskPredictionResponse:
    """
    Full Phase 4 Evidence Fusion and Risk Reasoning Pipeline:
    1. Multi-source evidence ingestion & alignment
    2. Numerical feature representation (32 dimensions)
    3. Multi-organ risk inference
    4. Transparent evidence-weighting & confidence calculation
    5. Evidence sufficiency gating
    6. Traceable explainability payload generation
    7. SQLite persistence
    """
    prediction_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Align and fuse heterogeneous evidence
    context = align_and_fuse_evidence(
        drug_id=request.drug_id,
        smiles=request.smiles,
        name=request.name,
    )

    # 2. Extract 32-dimensional aligned numerical feature vector
    feature_vector = context.to_feature_vector()
    X = np.atleast_2d(feature_vector)

    # 3. Model Inference
    model_type = (request.model_type or "random_forest").lower()
    predictor = get_or_train_predictor(model_type)

    overall_prob = predictor.predict_endpoint("overall", X)
    overall_prob = round(float(np.clip(overall_prob, 0.01, 0.99)), 4)
    overall_category = classify_risk_category(overall_prob)

    # 4. Evidence Strength & Sufficiency Gating
    evidence_strength = calculate_evidence_strength(context)
    sufficiency = evaluate_evidence_sufficiency(context)

    # Raw model certainty based on distance from decision boundary (0.5)
    model_raw_confidence = float(np.clip(0.5 + abs(overall_prob - 0.5) * 1.0, 0.5, 0.98))
    overall_confidence = calculate_prediction_confidence(
        model_raw_confidence=model_raw_confidence,
        evidence_strength=evidence_strength,
        sufficiency_passed=sufficiency.is_sufficient,
    )

    # 5. Organ-Level Risk Assessments
    organ_risks: Dict[str, OrganRiskAssessment] = {}
    for organ_key, organ_name in ORGAN_SYSTEMS.items():
        ep_risk = predictor.predict_endpoint(organ_key, X)
        ep_risk = round(float(np.clip(ep_risk, 0.01, 0.99)), 4)
        ep_category = classify_risk_category(ep_risk)

        # Count multi-hop paths to this organ
        paths_for_organ = [
            p for p in context.graph_paths
            if getattr(p, "target_organ", "") and organ_key in getattr(p, "target_organ", "").lower()
        ]

        # Count clinical adverse effects for this organ
        adv_for_organ = [
            e for e in context.evidence_records
            if e.entity_type == "adverse_effect" and organ_key in str(e.metadata.get("target_organ", "")).lower()
        ]

        # Extract primary mechanisms
        mechanisms: List[str] = []
        for p in paths_for_organ[:2]:
            if getattr(p, "description", None):
                mechanisms.append(getattr(p, "description"))
            elif getattr(p, "node_names", None):
                mechanisms.append(" -> ".join(getattr(p, "node_names")))
        for a in adv_for_organ[:2]:
            mechanisms.append(f"Reported Reaction: {a.entity_name}")

        if not mechanisms:
            if ep_risk >= 0.70:
                mechanisms.append(f"Predicted structural liability for {organ_key} toxicity")
            else:
                mechanisms.append(f"No specific high-affinity {organ_key} liability detected")

        # Organ specific confidence
        ep_conf = round(float(np.clip(0.40 * (0.5 + abs(ep_risk - 0.5)) + 0.60 * evidence_strength, 0.1, 0.95)), 4)
        if not sufficiency.is_sufficient:
            ep_conf = min(0.55, ep_conf)

        organ_risks[organ_key] = OrganRiskAssessment(
            organ=organ_key,
            organ_name=organ_name,
            risk_score=ep_risk,
            risk_category=ep_category,
            confidence=ep_conf,
            evidence_strength=evidence_strength,
            primary_mechanisms=mechanisms,
            graph_paths_count=len(paths_for_organ),
            adverse_effects_count=len(adv_for_organ),
            literature_citations_count=sum(1 for e in context.evidence_records if e.entity_type == "paper"),
        )

    # 6. Feature Attributions & Explainability
    importances = predictor.get_feature_importances("overall")
    top_indices = np.argsort(importances)[::-1][:6]
    contributing_features: List[Dict[str, Any]] = []
    for idx in top_indices:
        feat_name = FEATURE_NAMES[idx]
        contributing_features.append(
            {
                "feature_index": int(idx),
                "feature_name": feat_name,
                "feature_value": round(float(feature_vector[idx]), 4),
                "importance_weight": round(float(importances[idx]), 4),
            }
        )

    # Convert graph paths to schema models
    graph_path_models: List[GraphPathModel] = []
    for p in context.graph_paths[:10]:
        if isinstance(p, GraphPathModel):
            graph_path_models.append(p)
        elif isinstance(p, dict):
            graph_path_models.append(GraphPathModel(**p))

    literature_refs = [
        e.metadata
        for e in context.evidence_records
        if e.entity_type == "paper" and isinstance(e.metadata, dict)
    ]

    explainability = RiskExplainabilityMetadata(
        contributing_features=contributing_features,
        contributing_evidence=context.evidence_records,
        graph_paths=graph_path_models,
        literature_references=literature_refs,
        similarity_matches=context.similarity_matches,
    )

    response = DrugRiskPredictionResponse(
        prediction_id=prediction_id,
        drug_id=context.drug_id,
        drug_name=context.drug_name,
        canonical_smiles=context.canonical_smiles,
        model_used=model_type,
        overall_risk=overall_prob,
        overall_risk_category=overall_category,
        confidence=overall_confidence,
        evidence_strength=evidence_strength,
        organ_risks=organ_risks,
        evidence_sufficiency=sufficiency,
        explainability=explainability,
        disclaimer=(
            "Research-grade decision-support prototype. Categories ('Low', 'Moderate', 'High') "
            "are research prototype thresholds and must be validated on appropriate preclinical "
            "and clinical datasets. Not a clinical diagnostic or treatment recommendation system."
        ),
        status=ProcessingStatus(
            valid=True,
            message="Evidence fusion and multi-organ risk reasoning completed successfully.",
        ),
        created_at=now_iso,
    )

    # 7. Persist to SQLite
    save_risk_prediction(
        prediction_id=prediction_id,
        drug_id=context.drug_id,
        canonical_smiles=context.canonical_smiles,
        overall_risk=overall_prob,
        confidence=overall_confidence,
        prediction_data=response.model_dump(),
    )

    return response
