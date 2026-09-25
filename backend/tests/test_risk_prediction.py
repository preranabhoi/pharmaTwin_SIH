"""
Unit & Integration Tests for Phase 4: Evidence Fusion & Risk Reasoning Engine

Tests:
1. Model abstraction, fitting, deterministic prediction, serialization & loading
2. Evaluation metrics (Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix)
3. Dataset splitting (train_test_split, temporal_split)
4. Multi-modal feature alignment (32-dim vector)
5. Evidence weighting & confidence separation
6. Tanimoto molecular similarity matching with disclaimer
7. Evidence sufficiency gating (flag_for_review on sparse data)
8. Organ-level risk decomposition (Heart, Liver, Kidney, Lung, Brain)
9. End-to-end prediction orchestrator and SQLite persistence
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from app.database import get_risk_prediction, save_risk_prediction
from app.evidence_fusion import (
    FusedEvidenceContext,
    align_and_fuse_evidence,
    calculate_evidence_strength,
    calculate_prediction_confidence,
    calculate_tanimoto_similarity,
    evaluate_evidence_sufficiency,
    find_similar_benchmark_compounds,
)
from app.risk_prediction import (
    BaseRiskModel,
    EnsembleRiskModel,
    LogisticRegressionRiskModel,
    MultiOrganRiskPredictor,
    RandomForestRiskModel,
    classify_risk_category,
    get_or_train_predictor,
    predict_drug_risk,
)
from app.schemas import (
    DrugRiskPredictionRequest,
    DrugRiskPredictionResponse,
    NormalizedEvidence,
)
from app.training import (
    accuracy_score,
    confusion_matrix,
    evaluate_classifier,
    f1_score,
    generate_benchmark_training_data,
    precision_score,
    recall_score,
    roc_auc_score,
    temporal_split,
    train_test_split,
)


# =========================================================
# 1. Base Model & ML Architectures Tests
# =========================================================

class TestRiskModels:
    """Tests for pluggable ML models: RandomForest, LogisticRegression, Ensemble."""

    @pytest.fixture
    def sample_data(self):
        rng = np.random.RandomState(42)
        X = rng.rand(60, 32).astype(np.float32)
        y = (X[:, 0] + X[:, 1] > 1.0).astype(np.int32)
        return X, y

    def test_random_forest_fit_predict(self, sample_data):
        X, y = sample_data
        model = RandomForestRiskModel(n_estimators=10, max_depth=4, random_state=42)
        model.fit(X, y)

        preds = model.predict(X)
        probas = model.predict_proba(X)

        assert len(preds) == len(y)
        assert len(probas) == len(y)
        assert all(0.0 <= p <= 1.0 for p in probas)
        assert all(p in (0, 1) for p in preds)

        importances = model.get_feature_importances()
        assert len(importances) == 32
        assert np.isclose(np.sum(importances), 1.0, atol=1e-3)

    def test_logistic_regression_fit_predict(self, sample_data):
        X, y = sample_data
        model = LogisticRegressionRiskModel(learning_rate=0.05, max_iter=200, random_state=42)
        model.fit(X, y)

        preds = model.predict(X)
        probas = model.predict_proba(X)

        assert len(preds) == len(y)
        assert len(probas) == len(y)
        assert all(0.0 <= p <= 1.0 for p in probas)

        importances = model.get_feature_importances()
        assert len(importances) == 32
        assert np.isclose(np.sum(importances), 1.0, atol=1e-3)

    def test_ensemble_model_fit_predict(self, sample_data):
        X, y = sample_data
        model = EnsembleRiskModel(random_state=42)
        model.fit(X, y)

        probas = model.predict_proba(X)
        assert len(probas) == len(y)
        assert all(0.0 <= p <= 1.0 for p in probas)

        importances = model.get_feature_importances()
        assert len(importances) == 32
        assert np.isclose(np.sum(importances), 1.0, atol=1e-3)

    def test_model_serialization_and_loading(self, sample_data):
        X, y = sample_data
        rf = RandomForestRiskModel(n_estimators=5, max_depth=3, random_state=42)
        rf.fit(X, y)
        orig_probas = rf.predict_proba(X[:5])

        with tempfile.TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "rf_model.json"
            rf.save(model_file)
            assert model_file.exists()

            loaded_rf = RandomForestRiskModel().load(model_file)
            loaded_probas = loaded_rf.predict_proba(X[:5])
            np.testing.assert_allclose(orig_probas, loaded_probas, rtol=1e-4)

    def test_deterministic_inference(self, sample_data):
        X, y = sample_data
        m1 = RandomForestRiskModel(n_estimators=10, random_state=123).fit(X, y)
        m2 = RandomForestRiskModel(n_estimators=10, random_state=123).fit(X, y)

        p1 = m1.predict_proba(X)
        p2 = m2.predict_proba(X)
        np.testing.assert_array_equal(p1, p2)


# =========================================================
# 2. Validation Metrics & Dataset Splitting Tests
# =========================================================

class TestTrainingAndValidation:
    """Tests for evaluation metrics and reproducible dataset splitting."""

    def test_classification_metrics(self):
        y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0])
        y_pred = np.array([1, 0, 1, 0, 0, 1, 1, 0])
        y_prob = np.array([0.9, 0.1, 0.8, 0.4, 0.2, 0.7, 0.85, 0.15])

        acc = accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred)
        rec = recall_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        auc = roc_auc_score(y_true, y_prob)
        cm = confusion_matrix(y_true, y_pred)

        assert 0.0 <= acc <= 1.0
        assert 0.0 <= prec <= 1.0
        assert 0.0 <= rec <= 1.0
        assert 0.0 <= f1 <= 1.0
        assert 0.5 <= auc <= 1.0
        assert cm["tp"] == 3
        assert cm["tn"] == 3
        assert cm["fp"] == 1
        assert cm["fn"] == 1

        report = evaluate_classifier(y_true, y_pred, y_prob)
        assert "accuracy" in report
        assert "f1" in report
        assert "roc_auc" in report
        assert "confusion_matrix" in report

    def test_train_test_split_reproducibility(self):
        X, labels, _ = generate_benchmark_training_data(n_samples=100, random_state=42)
        y = labels["overall"]

        X_train1, X_test1, y_train1, y_test1 = train_test_split(X, y, test_size=0.2, random_state=42)
        X_train2, X_test2, y_train2, y_test2 = train_test_split(X, y, test_size=0.2, random_state=42)

        assert len(X_train1) == 80
        assert len(X_test1) == 20
        np.testing.assert_array_equal(X_train1, X_train2)
        np.testing.assert_array_equal(y_test1, y_test2)

    def test_temporal_split(self):
        X, labels, years = generate_benchmark_training_data(n_samples=100, random_state=42)
        y = labels["overall"]

        split_yr = 2010
        X_train, X_test, y_train, y_test = temporal_split(X, y, years, split_year=split_yr)

        train_years = years[years <= split_yr]
        test_years = years[years > split_yr]

        assert len(X_train) == len(train_years)
        assert len(X_test) == len(test_years)
        assert len(X_train) + len(X_test) == 100


# =========================================================
# 3. Evidence Fusion & Feature Alignment Tests
# =========================================================

class TestEvidenceFusion:
    """Tests for multi-source evidence fusion and 32-dim feature alignment."""

    def test_feature_vector_dimension_and_bounds(self):
        context = FusedEvidenceContext(
            drug_id="CHEMBL112",
            drug_name="Acetaminophen",
            canonical_smiles="CC(=O)NC1=CC=C(O)C=C1",
            descriptors={
                "molecular_weight": 151.16,
                "logp": 0.91,
                "tpsa": 49.33,
                "hbd": 2,
                "hba": 2,
                "rotatable_bonds": 1,
                "heavy_atom_count": 11,
                "ring_count": 1,
                "aromatic_ring_count": 1,
            },
            fingerprint=[1] * 50 + [0] * 1998,
        )

        vec = context.to_feature_vector()
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (32,)
        assert all(0.0 <= v <= 1.0 for v in vec)

    def test_missing_features_graceful_handling(self):
        # Empty context with minimal info
        sparse_context = FusedEvidenceContext(drug_id="UNKNOWN")
        vec = sparse_context.to_feature_vector()

        assert vec.shape == (32,)
        assert not np.isnan(vec).any()
        assert not np.isinf(vec).any()

    def test_tanimoto_similarity_calculation(self):
        fp1 = [1, 1, 0, 0, 1]
        fp2 = [1, 1, 0, 1, 0]
        # intersection = 2 (bits 0, 1)
        # union = 4 (bits 0, 1, 3, 4)
        # T = 2 / 4 = 0.5
        sim = calculate_tanimoto_similarity(fp1, fp2)
        assert np.isclose(sim, 0.5)

        # Disjoint
        assert calculate_tanimoto_similarity([1, 0], [0, 1]) == 0.0
        # Identical
        assert calculate_tanimoto_similarity([1, 1, 0], [1, 1, 0]) == 1.0

    def test_similarity_matches_have_disclaimer(self):
        dummy_fp = [1] * 100 + [0] * 1948
        matches = find_similar_benchmark_compounds(dummy_fp, top_k=2)

        assert len(matches) > 0
        for m in matches:
            assert m.disclaimer is not None
            assert "similarity" in m.disclaimer.lower()
            assert "does not prove" in m.disclaimer.lower()


# =========================================================
# 4. Evidence Weighting & Sufficiency Gating Tests
# =========================================================

class TestEvidenceWeightingAndSufficiency:
    """Tests for transparent evidence weighting and sufficiency gating."""

    def test_evidence_strength_separation(self):
        context = align_and_fuse_evidence(
            drug_id="CHEMBL112",
            smiles="CC(=O)NC1=CC=C(O)C=C1",
            name="Acetaminophen",
        )
        strength = calculate_evidence_strength(context)
        assert 0.0 <= strength <= 1.0
        assert strength > 0.5  # Curated demo drug should have rich evidence

    def test_evidence_sufficiency_gate_sufficient(self):
        context = align_and_fuse_evidence(
            drug_id="CHEMBL112",
            smiles="CC(=O)NC1=CC=C(O)C=C1",
            name="Acetaminophen",
        )
        sufficiency = evaluate_evidence_sufficiency(context)
        assert sufficiency.is_sufficient is True
        assert sufficiency.flag_for_review is False
        assert len(sufficiency.review_reasons) == 0

    def test_evidence_sufficiency_gate_sparse_review_flag(self):
        # Novel hypothetical compound without bio/graph/literature records
        sparse_context = FusedEvidenceContext(
            drug_id="NOVEL_MOL_999",
            canonical_smiles="CCCCCCCC(=O)O",
            descriptors={"molecular_weight": 144.2},
            fingerprint=[0] * 2048,
        )
        sufficiency = evaluate_evidence_sufficiency(sparse_context)
        assert sufficiency.is_sufficient is False
        assert sufficiency.flag_for_review is True
        assert len(sufficiency.review_reasons) > 0

    def test_confidence_dampening_on_insufficient_evidence(self):
        # If model has high raw confidence but evidence is insufficient,
        # overall confidence must be scaled down and not exceed 0.55
        raw_conf = 0.95
        sparse_strength = 0.15
        conf = calculate_prediction_confidence(
            model_raw_confidence=raw_conf,
            evidence_strength=sparse_strength,
            sufficiency_passed=False,
        )
        assert conf <= 0.55
        assert conf < raw_conf


# =========================================================
# 5. Organ-Level Risk & End-to-End Prediction Tests
# =========================================================

class TestOrganRiskAndPipeline:
    """Tests for decomposed organ risk assessment and end-to-end API logic."""

    def test_risk_category_thresholds(self):
        assert classify_risk_category(0.20) == "Low"
        assert classify_risk_category(0.34) == "Low"
        assert classify_risk_category(0.35) == "Moderate"
        assert classify_risk_category(0.69) == "Moderate"
        assert classify_risk_category(0.70) == "High"
        assert classify_risk_category(0.95) == "High"

    def test_predict_drug_risk_demo_compound(self):
        req = DrugRiskPredictionRequest(
            drug_id="CHEMBL112",
            smiles="CC(=O)NC1=CC=C(O)C=C1",
            name="Acetaminophen",
            model_type="random_forest",
        )
        res = predict_drug_risk(req)

        assert isinstance(res, DrugRiskPredictionResponse)
        assert res.prediction_id is not None
        assert res.drug_id == "CHEMBL112"
        assert 0.0 <= res.overall_risk <= 1.0
        assert res.overall_risk_category in ("Low", "Moderate", "High")
        assert 0.0 <= res.confidence <= 1.0
        assert 0.0 <= res.evidence_strength <= 1.0

        # Organ systems presence
        expected_organs = {"heart", "liver", "kidney", "lung", "brain"}
        assert set(res.organ_risks.keys()) == expected_organs

        for organ_key, organ_eval in res.organ_risks.items():
            assert organ_eval.organ == organ_key
            assert 0.0 <= organ_eval.risk_score <= 1.0
            assert organ_eval.risk_category in ("Low", "Moderate", "High")
            assert len(organ_eval.primary_mechanisms) > 0

        # Explainability metadata
        assert len(res.explainability.contributing_features) > 0
        assert len(res.explainability.contributing_evidence) > 0
        assert len(res.explainability.graph_paths) > 0
        assert len(res.explainability.similarity_matches) > 0

        # Disclaimer presence
        assert "research" in res.disclaimer.lower()
        assert "not a clinical" in res.disclaimer.lower()

    def test_prediction_sqlite_persistence_and_retrieval(self):
        req = DrugRiskPredictionRequest(
            drug_id="CHEMBL25",
            smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            name="Aspirin",
            model_type="logistic_regression",
        )
        res = predict_drug_risk(req)
        pred_id = res.prediction_id

        # Retrieve directly from DB
        stored = get_risk_prediction(pred_id)
        assert stored is not None
        assert stored["prediction_id"] == pred_id
        assert stored["drug_id"] == "CHEMBL25"
        assert np.isclose(stored["overall_risk"], res.overall_risk, atol=1e-4)

    def test_alternative_models_execution(self):
        req_rf = DrugRiskPredictionRequest(drug_id="CHEMBL521", smiles="CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", model_type="random_forest")
        req_lr = DrugRiskPredictionRequest(drug_id="CHEMBL521", smiles="CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", model_type="logistic_regression")
        req_ens = DrugRiskPredictionRequest(drug_id="CHEMBL521", smiles="CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", model_type="ensemble")

        res_rf = predict_drug_risk(req_rf)
        res_lr = predict_drug_risk(req_lr)
        res_ens = predict_drug_risk(req_ens)

        assert res_rf.model_used == "random_forest"
        assert res_lr.model_used == "logistic_regression"
        assert res_ens.model_used == "ensemble"
