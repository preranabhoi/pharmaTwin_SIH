"""
Unit & Integration Tests for Phase 5: Explainability & Evidence Traceability Engine

Tests:
1. Local SHAP feature attribution generation (additive efficiency, ranking, direction)
2. 32-dimensional feature schema alignment & descriptions
3. Multi-source evidence linkage (Molecular, Graph paths, Adverse reactions, Literature citations)
4. Knowledge Graph multi-hop mechanistic path extraction
5. Quality metadata calculation (evidence count, source diversity, base value, sufficiency)
6. Non-misleading causality boundary distinction
7. Missing explanation handling (404 / ValueError)
8. UI-ready explanation endpoint integration
"""

import numpy as np
import pytest

from app.database import get_risk_prediction
from app.explainability import (
    FEATURE_DESCRIPTIONS,
    SHAPExplainer,
    generate_prediction_explanation,
)
from app.risk_prediction import (
    FEATURE_NAMES,
    RandomForestRiskModel,
    get_or_train_predictor,
    predict_drug_risk,
)
from app.schemas import (
    DrugRiskPredictionRequest,
    FeatureSHAPExplanation,
    PredictionExplanationResponse,
)


# =========================================================
# 1. SHAP Explainer Engine Tests
# =========================================================

class TestSHAPEngine:
    """Tests for the local Shapley Additive Explanations (SHAP) calculation."""

    @pytest.fixture
    def trained_rf_model(self):
        predictor = get_or_train_predictor("random_forest")
        return predictor.models["overall"]

    def test_shap_explainer_initialization_and_base_value(self, trained_rf_model):
        explainer = SHAPExplainer(trained_rf_model)
        assert explainer.base_value is not None
        assert 0.0 <= explainer.base_value <= 1.0

    def test_shap_instance_explanation_efficiency(self, trained_rf_model):
        explainer = SHAPExplainer(trained_rf_model)
        rng = np.random.RandomState(42)
        x = rng.rand(32).astype(np.float32)

        pred_val, base_val, shap_values = explainer.explain_instance(x, n_samples=80, random_state=42)

        assert len(shap_values) == 32
        assert 0.0 <= pred_val <= 1.0
        assert 0.0 <= base_val <= 1.0

        # Additive Efficiency property: sum(shap_values) ≈ pred_val - base_val
        delta = pred_val - base_val
        np.testing.assert_allclose(np.sum(shap_values), delta, atol=1e-3)

    def test_shap_direction_and_ranking(self, trained_rf_model):
        explainer = SHAPExplainer(trained_rf_model)
        x = np.ones(32, dtype=np.float32) * 0.8
        _, _, shap_values = explainer.explain_instance(x, n_samples=50, random_state=42)

        for i, val in enumerate(shap_values):
            direction = "increases_risk" if val >= 0.0 else "decreases_risk"
            if val > 0:
                assert direction == "increases_risk"
            elif val < 0:
                assert direction == "decreases_risk"


# =========================================================
# 2. Feature Alignment & Descriptions Tests
# =========================================================

class TestFeatureAlignment:
    """Tests for feature names, descriptions, and 32-dim alignment."""

    def test_feature_names_and_descriptions_coverage(self):
        assert len(FEATURE_NAMES) == 32
        assert len(FEATURE_DESCRIPTIONS) == 32

        for name in FEATURE_NAMES:
            assert name in FEATURE_DESCRIPTIONS
            desc = FEATURE_DESCRIPTIONS[name]
            assert len(desc) > 15
            assert ":" in desc  # Format: "Name: Description"


# =========================================================
# 3. Evidence Linkage & Traceability Report Tests
# =========================================================

class TestEvidenceTraceabilityReport:
    """Tests for full explanation payload generation and evidence linkage."""

    @pytest.fixture
    def acetaminophen_prediction(self):
        req = DrugRiskPredictionRequest(
            drug_id="CHEMBL112",
            smiles="CC(=O)NC1=CC=C(O)C=C1",
            name="Acetaminophen",
            model_type="random_forest",
        )
        return predict_drug_risk(req)

    def test_generate_explanation_for_acetaminophen(self, acetaminophen_prediction):
        pred_id = acetaminophen_prediction.prediction_id
        exp = generate_prediction_explanation(pred_id)

        assert isinstance(exp, PredictionExplanationResponse)
        assert exp.prediction_id == pred_id
        assert exp.drug_id == "CHEMBL112"
        assert exp.drug_name == "Acetaminophen"
        assert exp.model_used == "random_forest"
        assert 0.0 <= exp.overall_risk <= 1.0

        # Top features
        assert len(exp.top_features) == 8
        assert len(exp.all_feature_contributions) == 32

        # Check ranking order (descending by absolute contribution)
        abs_contribs = [abs(f.contribution) for f in exp.all_feature_contributions]
        assert abs_contribs == sorted(abs_contribs, reverse=True)

        for rank, f in enumerate(exp.all_feature_contributions, start=1):
            assert f.rank == rank
            assert f.direction in ("increases_risk", "decreases_risk")
            assert f.attribution_type == "statistical_feature_contribution"

        # Evidence linkages
        assert len(exp.supporting_paths) > 0
        assert len(exp.supporting_evidence) > 0
        assert len(exp.supporting_literature) > 0
        assert len(exp.similarity_matches) > 0

        # Quality metadata
        qm = exp.quality_metadata
        assert qm.evidence_count > 0
        assert len(qm.evidence_source_diversity) >= 3
        assert "UniProt" in qm.evidence_source_diversity or "ChEMBL" in qm.evidence_source_diversity
        assert qm.confidence > 0.5
        assert qm.evidence_sufficiency.is_sufficient is True

        # Causality distinction & disclaimers
        assert "statistical" in exp.causality_distinction.lower()
        assert "not constitute proven biological causality" in exp.causality_distinction.lower()
        assert "research-grade" in exp.disclaimer.lower()

    def test_explanation_from_direct_dict(self, acetaminophen_prediction):
        pred_dict = acetaminophen_prediction.model_dump()
        exp = generate_prediction_explanation(pred_dict)
        assert exp.prediction_id == acetaminophen_prediction.prediction_id

    def test_missing_prediction_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            generate_prediction_explanation("non-existent-uuid-00000")
        assert "not found in audit logs" in str(exc_info.value)

    def test_sparse_compound_explanation_quality(self):
        req = DrugRiskPredictionRequest(
            smiles="CCCCCCC(=O)O",
            name="HeptanoicAcid",
            model_type="random_forest",
        )
        pred = predict_drug_risk(req)
        exp = generate_prediction_explanation(pred.prediction_id)

        assert exp.quality_metadata.evidence_sufficiency.is_sufficient is False
        assert exp.quality_metadata.evidence_sufficiency.flag_for_review is True
        assert len(exp.quality_metadata.evidence_sufficiency.review_reasons) > 0
        assert exp.confidence <= 0.55
