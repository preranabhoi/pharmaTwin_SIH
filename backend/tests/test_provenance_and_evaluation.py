"""
Unit and Integration Tests for Phase 9 & Phase 10
- Phase 9: Persistent Storage, Provenance & Auditability
- Phase 10: Model Validation & Research Evaluation
"""

import json
import pytest
from app.database import (
    clear_cache,
    get_audit_trail,
    get_model_version,
    list_audit_events,
    list_model_versions,
    log_audit_event,
    save_drug,
    save_molecule,
    save_prediction_lineage,
)
from app.evaluation import (
    DatasetRegistry,
    ModelEvaluationPipeline,
    generate_evaluation_csv,
    generate_human_readable_summary,
    get_latest_evaluation_report,
)


# ---------------------------------------------------------
# 1. PHASE 9: AUDITABILITY & PROVENANCE TESTS
# ---------------------------------------------------------

def test_audit_event_logging():
    """Test logging and retrieving immutable audit events."""
    event_id = log_audit_event(
        action="DRUG_PROCESSED",
        object_type="Molecule",
        object_id="CHEMBL112",
        model_version="v1.0.0-rf-calibrated",
        status="SUCCESS",
        details={"smiles": "CC(=O)Nc1ccc(O)cc1", "mw": 151.16},
    )
    assert event_id is not None

    events = list_audit_events(limit=10, action="DRUG_PROCESSED")
    assert len(events) >= 1
    target = next((e for e in events if e["event_id"] == event_id), None)
    assert target is not None
    assert target["object_id"] == "CHEMBL112"
    assert target["action"] == "DRUG_PROCESSED"
    assert target["status"] == "SUCCESS"
    assert target["details"]["smiles"] == "CC(=O)Nc1ccc(O)cc1"


def test_prediction_lineage_and_audit_trail(client):
    """Test complete reproducible lineage and audit trail extraction."""
    # 1. Execute prediction via API
    payload = {
        "drug_id": "CHEMBL112",
        "smiles": "CC(=O)Nc1ccc(O)cc1",
        "name": "Acetaminophen",
        "model_type": "random_forest",
    }
    pred_res = client.post("/api/risk/predict", json=payload)
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    pred_id = pred_data["prediction_id"]

    # 2. Ingest organ mapping
    organ_res = client.get(f"/api/organ-risk/{pred_id}")
    assert organ_res.status_code == 200
    organ_data = organ_res.json()

    # 3. Retrieve audit trail
    trail_res = client.get(f"/api/audit/trail/{pred_id}")
    assert trail_res.status_code == 200
    trail = trail_res.json()

    assert trail["prediction_id"] == pred_id
    assert trail["drug_id"] == "CHEMBL112"
    assert len(trail["reproducible_chain"]) >= 5
    assert "Drug Input Ingested" in trail["reproducible_chain"]
    assert "Organ Risk Localization Mapped to 3D Virtual Twin" in trail["reproducible_chain"]

    # Verify nested lineage items
    lineage = trail["lineage"]
    assert "prediction" in lineage
    assert lineage["prediction"]["overall_risk_category"] in ("Low", "Moderate", "High")


def test_model_version_registry(client):
    """Test listing and querying registered model versions."""
    models_res = client.get("/api/models")
    assert models_res.status_code == 200
    models = models_res.json()
    assert len(models) >= 3

    rf_model = next((m for m in models if m["model_version"] == "v1.0.0-rf-calibrated"), None)
    assert rf_model is not None
    assert rf_model["feature_version"] == "v1.0.0-multi-modal-32d"
    assert "n_estimators" in rf_model["hyperparameters"]

    single_res = client.get("/api/models/v1.0.0-rf-calibrated")
    assert single_res.status_code == 200
    assert single_res.json()["model_version"] == "v1.0.0-rf-calibrated"


# ---------------------------------------------------------
# 2. PHASE 10: MODEL VALIDATION & EVALUATION TESTS
# ---------------------------------------------------------

def test_model_evaluation_pipeline_metrics():
    """Test authentic evaluation metrics computation across baseline models."""
    pipeline = ModelEvaluationPipeline(dataset_version="v1.2.0-benchmark-tox", random_state=42)
    report = pipeline.run_evaluation(split_type="random")

    assert report["report_id"].startswith("eval-")
    assert report["test_sample_count"] > 0
    assert report["positive_sample_count"] > 0

    models = report["models"]
    for expected_key in ["v1.0.0-rf-calibrated", "v1.0.0-lr-elasticnet", "v1.0.0-ensemble-weighted"]:
        assert expected_key in models
        m = models[expected_key]["metrics"]
        assert 0.0 <= m["accuracy"] <= 1.0
        assert 0.0 <= m["precision"] <= 1.0
        assert 0.0 <= m["recall"] <= 1.0
        assert 0.0 <= m["f1_score"] <= 1.0
        assert 0.0 <= m["roc_auc"] <= 1.0
        assert 0.0 <= m["pr_auc"] <= 1.0
        assert 0.0 <= m["brier_score"] <= 1.0
        assert "tp" in m["confusion_matrix"]


def test_temporal_split_evaluation():
    """Test time-based chronological data splitting and validation."""
    pipeline = ModelEvaluationPipeline(dataset_version="v1.2.0-benchmark-tox", random_state=42)
    temporal_report = pipeline.run_evaluation(split_type="temporal")

    assert temporal_report["split_type"] == "temporal"
    assert temporal_report["test_sample_count"] > 0
    rf_metrics = temporal_report["models"]["v1.0.0-rf-calibrated"]["metrics"]
    assert rf_metrics["roc_auc"] > 0.50


def test_organ_and_explainability_evaluation():
    """Test organ-level evaluation and explainability coverage tracking."""
    pipeline = ModelEvaluationPipeline()
    report = pipeline.run_evaluation()

    organs = report["organ_level_evaluation"]
    assert "liver" in organs
    assert organs["liver"]["evaluation_status"] == "ground_truth_validated"
    assert "metrics" in organs["liver"]

    assert "gastrointestinal" in organs
    assert organs["gastrointestinal"]["evaluation_status"] == "prototype_evidence_mapping"

    exp = report["explainability_evaluation"]
    assert exp["explanation_completeness_rate"] == 1.0
    assert exp["evidence_linkage_coverage"] > 0.0
    assert "causality_distinction" in exp


def test_evaluation_api_endpoints(client):
    """Test evaluation API endpoints (run, model lookup, latest, csv, summary)."""
    # 1. Trigger evaluation run
    run_res = client.post("/api/evaluation/run?split_type=random")
    assert run_res.status_code == 200
    report = run_res.json()
    assert "report_id" in report

    # 2. Get latest evaluation
    latest_res = client.get("/api/evaluation/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["report_id"] == report["report_id"]

    # 3. Get evaluation by model version
    model_eval_res = client.get("/api/evaluation/model/v1.0.0-rf-calibrated")
    assert model_eval_res.status_code == 200
    assert "models" in model_eval_res.json()

    # 4. CSV Download
    csv_res = client.get("/api/evaluation/report/csv")
    assert csv_res.status_code == 200
    assert "model_version,model_name" in csv_res.text

    # 5. Markdown Summary
    md_res = client.get("/api/evaluation/report/summary")
    assert md_res.status_code == 200
    assert "PharmaTwin AI" in md_res.text
    assert "Binary Toxicity Classification Metrics" in md_res.text
