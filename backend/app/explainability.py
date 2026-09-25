"""
Explainability & Evidence Traceability Engine (Phase 5)

Primary Method:
- SHAP (Shapley Additive Explanations) for local model feature attribution.
- Multi-source evidence linkage (Molecular, Graph, Historical adverse, Literature).
- Explanation quality metadata (diversity, sufficiency, confidence, base value).
- Explicit scientific boundary distinguishing statistical feature contribution from biological causality.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from app.database import get_risk_prediction
from app.evidence_fusion import (
    FusedEvidenceContext,
    align_and_fuse_evidence,
    calculate_evidence_strength,
    calculate_prediction_confidence,
    evaluate_evidence_sufficiency,
)
from app.risk_prediction import (
    BaseRiskModel,
    FEATURE_NAMES,
    ORGAN_SYSTEMS,
    classify_risk_category,
    get_or_train_predictor,
)
from app.schemas import (
    DrugRiskPredictionRequest,
    DrugRiskPredictionResponse,
    EvidenceSufficiencyCheck,
    ExplanationQualityMetadata,
    FeatureSHAPExplanation,
    GraphPathModel,
    MolecularSimilarityMatch,
    NormalizedEvidence,
    PredictionExplanationResponse,
)
from app.training import generate_benchmark_training_data


# ---------------------------------------------------------
# 1. Feature Descriptions Dictionary
# ---------------------------------------------------------

FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "molecular_weight_norm": "Normalized Molecular Weight: Reflects compound mass, steric bulk, and oral bioavailability range.",
    "logp_norm": "Calculated Octanol-Water Partition Coefficient (LogP): High values increase lipophilicity and membrane accumulation.",
    "tpsa_norm": "Topological Polar Surface Area (TPSA): Reflects molecular polarity, hydrogen bonding, and barrier permeation.",
    "hbd_norm": "Hydrogen Bond Donors (HBD): Count of OH and NH hydrogen donors influencing binding specificity.",
    "hba_norm": "Hydrogen Bond Acceptors (HBA): Count of N and O acceptors influencing hydrogen bond network formation.",
    "rotatable_bonds_norm": "Rotatable Bonds: Conformational flexibility and binding pocket entropic penalty.",
    "heavy_atom_count_norm": "Heavy Atom Count: Total non-hydrogen skeleton size and structural complexity.",
    "ring_count_norm": "Total Ring Count: Molecular rigidity and scaffold stability.",
    "aromatic_ring_count_norm": "Aromatic Ring Count: Planar pi-stacking capability and reactive aromatic liabilities.",
    "fingerprint_density": "Morgan Circular Fingerprint Density: Proportion of active 2048-bit structural circular fragments.",
    "kg_paths_heart": "Cardiovascular Multi-Hop Paths: Count of traceable Knowledge Graph paths terminating in Heart tissue.",
    "kg_paths_liver": "Hepatic Multi-Hop Paths: Count of traceable Knowledge Graph paths terminating in Liver tissue.",
    "kg_paths_kidney": "Renal Multi-Hop Paths: Count of traceable Knowledge Graph paths terminating in Kidney tissue.",
    "kg_paths_lung": "Respiratory Multi-Hop Paths: Count of traceable Knowledge Graph paths terminating in Lung tissue.",
    "kg_paths_brain": "Central Nervous System Multi-Hop Paths: Count of traceable Knowledge Graph paths terminating in Brain tissue.",
    "kg_conf_heart": "Knowledge Graph Max Path Confidence (Heart): Confidence of the highest-scoring cardiovascular path.",
    "kg_conf_liver": "Knowledge Graph Max Path Confidence (Liver): Confidence of the highest-scoring hepatic path.",
    "kg_conf_kidney": "Knowledge Graph Max Path Confidence (Kidney): Confidence of the highest-scoring renal path.",
    "kg_conf_lung": "Knowledge Graph Max Path Confidence (Lung): Confidence of the highest-scoring respiratory path.",
    "kg_conf_brain": "Knowledge Graph Max Path Confidence (Brain): Confidence of the highest-scoring neuro path.",
    "adverse_heart_count": "SIDER Clinical Adverse Cardiac Reactions: Recorded clinical frequency of cardiovascular adverse events.",
    "adverse_liver_count": "SIDER Clinical Adverse Hepatic Reactions: Recorded clinical frequency of hepatic adverse events.",
    "adverse_kidney_count": "SIDER Clinical Adverse Renal Reactions: Recorded clinical frequency of renal adverse events.",
    "adverse_lung_count": "SIDER Clinical Adverse Respiratory Reactions: Recorded clinical frequency of pulmonary adverse events.",
    "adverse_brain_count": "SIDER Clinical Adverse Neuro Reactions: Recorded clinical frequency of neurological adverse events.",
    "literature_count": "PubMed Literature Citation Density: Indexed count of peer-reviewed biomedical literature citations.",
    "literature_max_confidence": "Max Literature Source Confidence: Peak bibliographic validation confidence across citations.",
    "evidence_density": "Aggregate Biomedical Evidence Density: Cross-database integration and annotation completeness score.",
    "tanimoto_sim_top1": "Tanimoto Similarity (Top-1 Benchmark): Morgan fingerprint structural similarity to nearest benchmark drug.",
    "tanimoto_sim_top2": "Tanimoto Similarity (Top-2 Benchmark): Morgan fingerprint structural similarity to second nearest benchmark drug.",
    "tanimoto_sim_mean": "Mean Benchmark Structural Similarity: Average Tanimoto coefficient across reference toxicological panel.",
    "high_similarity_flag": "High Structural Similarity Indicator: Flag indicating strong structural alignment (>0.60 Tanimoto) to a benchmark toxicant.",
}


# ---------------------------------------------------------
# 2. SHAP (Shapley Additive Explanations) Engine
# ---------------------------------------------------------

class SHAPExplainer:
    """
    Computes local feature attributions using the Shapley Additive Explanations (SHAP) formulation.
    For an instance x and background baseline X_bg:
    - Base Value E[f(x)] = Mean model prediction over background dataset.
    - Local SHAP Values phi_i = Marginal additive contribution of feature i.
    - Additive Efficiency: sum(phi_i) = f(x) - E[f(x)].
    """

    def __init__(self, model: BaseRiskModel, background_data: Optional[np.ndarray] = None):
        self.model = model
        if background_data is not None:
            self.background_data = np.asarray(background_data, dtype=np.float32)
        else:
            X_bg, _, _ = generate_benchmark_training_data(n_samples=50, random_state=42)
            self.background_data = X_bg

        # Compute baseline expected value
        bg_preds = self.model.predict_proba(self.background_data)
        self.base_value = float(np.mean(bg_preds))

    def explain_instance(
        self, x: np.ndarray, n_samples: int = 100, random_state: int = 42
    ) -> Tuple[float, float, np.ndarray]:
        """
        Computes local SHAP attribution values phi for feature vector x.
        Returns:
        - pred_val: Model prediction probability f(x)
        - base_val: Background expected prediction E[f(x)]
        - shap_values: 32-element array of Shapley values phi_i
        """
        x = np.asarray(x, dtype=np.float32).ravel()
        n_features = len(x)
        pred_val = float(self.model.predict_proba(x.reshape(1, -1))[0])
        delta = pred_val - self.base_value

        # Marginal sampling-based Shapley value computation
        rng = np.random.RandomState(random_state)
        n_bg = len(self.background_data)
        marginal_contributions = np.zeros(n_features, dtype=np.float64)
        feature_counts = np.zeros(n_features, dtype=np.int32)

        # Permutation sampling
        for _ in range(n_samples):
            perm = rng.permutation(n_features)
            bg_idx = rng.randint(0, n_bg)
            current_sample = self.background_data[bg_idx].copy()
            prev_pred = float(self.model.predict_proba(current_sample.reshape(1, -1))[0])

            for feat in perm:
                current_sample[feat] = x[feat]
                new_pred = float(self.model.predict_proba(current_sample.reshape(1, -1))[0])
                marginal_contributions[feat] += (new_pred - prev_pred)
                feature_counts[feat] += 1
                prev_pred = new_pred

        shap_values = np.zeros(n_features, dtype=np.float64)
        valid_mask = feature_counts > 0
        shap_values[valid_mask] = marginal_contributions[valid_mask] / feature_counts[valid_mask]

        # Enforce exact additive efficiency: sum(phi_i) = f(x) - E[f(x)]
        sum_shap = np.sum(shap_values)
        if abs(sum_shap) > 1e-6:
            shap_values = shap_values * (delta / sum_shap)
        elif abs(delta) > 1e-6:
            # Fallback uniform allocation if all marginals were zero
            shap_values = np.full(n_features, delta / n_features, dtype=np.float64)

        return pred_val, self.base_value, shap_values


# ---------------------------------------------------------
# 3. High-Level Explanation Report Generator
# ---------------------------------------------------------

def generate_prediction_explanation(
    prediction_dict_or_id: Union[str, Dict[str, Any]],
) -> PredictionExplanationResponse:
    """
    Generates a full Phase 5 Explainability and Traceability Report:
    - SHAP local feature attributions (contributions, directions, ranks, descriptions).
    - Multi-source evidence linkage (Molecular, Knowledge Graph paths, SIDER clinical adverse, PubMed literature).
    - Explanation quality metadata (evidence count, source diversity, confidence, sufficiency).
    - Clear distinction between statistical model attribution vs biological causality.
    """
    # 1. Resolve prediction data
    if isinstance(prediction_dict_or_id, str):
        pred_id = prediction_dict_or_id.strip()
        pred_data = get_risk_prediction(pred_id)
        if not pred_data:
            raise ValueError(f"Prediction '{pred_id}' not found in audit logs.")
    else:
        pred_data = prediction_dict_or_id

    prediction_id = pred_data.get("prediction_id", "")
    drug_id = pred_data.get("drug_id", "")
    drug_name = pred_data.get("drug_name") or drug_id
    canonical_smiles = pred_data.get("canonical_smiles")
    model_used = pred_data.get("model_used", "random_forest")
    overall_risk = float(pred_data.get("overall_risk", 0.5))
    overall_category = pred_data.get("overall_risk_category", classify_risk_category(overall_risk))
    confidence = float(pred_data.get("confidence", 0.5))
    evidence_strength = float(pred_data.get("evidence_strength", 0.5))
    created_at = pred_data.get("created_at", datetime.now(timezone.utc).isoformat())

    # 2. Re-align evidence context
    context = align_and_fuse_evidence(
        drug_id=drug_id,
        smiles=canonical_smiles,
        name=drug_name,
    )
    feature_vector = context.to_feature_vector()

    # 3. Compute SHAP feature attributions
    predictor = get_or_train_predictor(model_used)
    overall_model = predictor.models.get("overall", predictor._create_model())
    explainer = SHAPExplainer(overall_model)

    pred_val, base_val, shap_values = explainer.explain_instance(feature_vector)

    # 4. Construct feature attribution items
    ranked_indices = np.argsort(np.abs(shap_values))[::-1]
    all_features: List[FeatureSHAPExplanation] = []

    for rank, idx in enumerate(ranked_indices, start=1):
        feat_name = FEATURE_NAMES[idx]
        feat_val = float(feature_vector[idx])
        contrib = float(shap_values[idx])
        direction = "increases_risk" if contrib >= 0.0 else "decreases_risk"
        desc = FEATURE_DESCRIPTIONS.get(feat_name, f"Feature: {feat_name}")

        all_features.append(
            FeatureSHAPExplanation(
                feature_name=feat_name,
                feature_value=round(feat_val, 4),
                contribution=round(contrib, 4),
                direction=direction,
                rank=rank,
                description=desc,
                attribution_type="statistical_feature_contribution",
            )
        )

    # Top 8 most impactful features for UI display
    top_features = all_features[:8]

    # 5. Extract multi-source evidence linkages
    graph_path_models: List[GraphPathModel] = []
    for p in context.graph_paths[:10]:
        if isinstance(p, GraphPathModel):
            graph_path_models.append(p)
        elif isinstance(p, dict):
            graph_path_models.append(GraphPathModel(**p))

    literature_records = [
        e.metadata
        for e in context.evidence_records
        if e.entity_type == "paper" and isinstance(e.metadata, dict)
    ]

    # Source diversity calculation
    sources = set()
    for e in context.evidence_records:
        if e.source:
            sources.add(e.source)
    for p in context.graph_paths:
        if getattr(p, "source", None):
            sources.add(getattr(p, "source"))
    if not sources:
        sources.add("MolecularStructureAnalysis")

    # Sufficiency
    sufficiency = evaluate_evidence_sufficiency(context)

    # Total evidence items count
    evidence_count = (
        len(context.descriptors)
        + len(context.evidence_records)
        + len(context.graph_paths)
        + len(literature_records)
        + len(context.similarity_matches)
    )

    quality_meta = ExplanationQualityMetadata(
        evidence_count=evidence_count,
        evidence_source_diversity=sorted(list(sources)),
        confidence=confidence,
        evidence_sufficiency=sufficiency,
        base_value=round(base_val, 4),
        prediction_value=round(pred_val, 4),
    )

    return PredictionExplanationResponse(
        prediction_id=prediction_id,
        drug_id=drug_id,
        drug_name=drug_name,
        canonical_smiles=canonical_smiles,
        model_used=model_used,
        overall_risk=overall_risk,
        overall_risk_category=overall_category,
        confidence=confidence,
        evidence_strength=evidence_strength,
        base_value=round(base_val, 4),
        top_features=top_features,
        all_feature_contributions=all_features,
        supporting_paths=graph_path_models,
        supporting_evidence=context.evidence_records,
        supporting_literature=literature_records,
        similarity_matches=context.similarity_matches,
        quality_metadata=quality_meta,
        causality_distinction=(
            "Statistical feature attributions (SHAP) quantify how input variables shifted the statistical model "
            "score relative to the background baseline. They do NOT constitute proven biological causality. "
            "Traceable biological hypotheses are represented separately via Knowledge Graph mechanistic paths."
        ),
        disclaimer=(
            "Research-grade decision-support prototype. Predictions and feature attributions are computational "
            "hypotheses and must be experimentally validated. Not a clinical diagnostic or treatment recommendation system."
        ),
        created_at=created_at,
    )
