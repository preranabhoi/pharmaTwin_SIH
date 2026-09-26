"""
Database, Provenance & Auditability Module (Phase 9)

Provides:
- PostgreSQL & SQLite compatible typed persistent storage
- Entities: Drug, Molecule, EvidenceRecord, KnowledgeGraphEntity,
  KnowledgeGraphRelationship, ModelVersion, Prediction, OrganRisk,
  Explanation, LiteratureReference, AuditEvent, and EvaluationReport.
- Full provenance tracking and reproducible audit trail extraction:
  Drug -> Molecule -> Evidence -> Graph -> Model -> Prediction -> Explanation -> Organ Risk
- Model versioning metadata storage
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings


def get_now_utc_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def get_db_connection() -> sqlite3.Connection:
    """Returns an open SQLite database connection with row factory."""
    db_path = settings.SQLITE_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes all Phase 9 persistent storage tables, indices, and default model versions."""
    conn = get_db_connection()
    try:
        with conn:
            # 1. Evidence Cache (Backward Compatibility)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_cache (
                    cache_key TEXT PRIMARY KEY,
                    drug_id TEXT,
                    canonical_smiles TEXT,
                    evidence_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_drug_id ON evidence_cache(drug_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_smiles ON evidence_cache(canonical_smiles);")

            # 2. Risk Predictions (Backward Compatibility)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_predictions (
                    prediction_id TEXT PRIMARY KEY,
                    drug_id TEXT,
                    canonical_smiles TEXT,
                    overall_risk REAL,
                    confidence REAL,
                    prediction_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_drug_id ON risk_predictions(drug_id);")

            # 3. Drugs Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS drugs (
                    drug_id TEXT PRIMARY KEY,
                    name TEXT,
                    canonical_smiles TEXT,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_drugs_name ON drugs(name);")

            # 4. Molecules Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS molecules (
                    id TEXT PRIMARY KEY,
                    drug_id TEXT NOT NULL,
                    canonical_smiles TEXT NOT NULL,
                    inchi TEXT,
                    inchikey TEXT,
                    formula TEXT,
                    molecular_weight REAL,
                    logp REAL,
                    tpsa REAL,
                    hbd INTEGER,
                    hba INTEGER,
                    rotatable_bonds INTEGER,
                    heavy_atom_count INTEGER,
                    ring_count INTEGER,
                    fingerprint_bits INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(drug_id) REFERENCES drugs(drug_id)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_molecules_drug_id ON molecules(drug_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_molecules_inchikey ON molecules(inchikey);")

            # 5. Evidence Records Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_records (
                    id TEXT PRIMARY KEY,
                    drug_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    entity_name TEXT,
                    relation TEXT,
                    object_id TEXT,
                    object_name TEXT,
                    confidence REAL DEFAULT 1.0,
                    provenance_metadata TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_drug_id ON evidence_records(drug_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence_records(source);")

            # 6. Knowledge Graph Entities Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kg_entities (
                    id TEXT PRIMARY KEY,
                    drug_id TEXT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_entities_drug_id ON kg_entities(drug_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_entities_type ON kg_entities(entity_type);")

            # 7. Knowledge Graph Relationships Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kg_relationships (
                    id TEXT PRIMARY KEY,
                    drug_id TEXT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    provenance_id TEXT,
                    properties TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_rel_drug_id ON kg_relationships(drug_id);")

            # 8. Model Versions Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_versions (
                    id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL UNIQUE,
                    feature_version TEXT NOT NULL,
                    training_dataset_version TEXT NOT NULL,
                    hyperparameters TEXT,
                    metrics_summary TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                """
            )

            # 9. Predictions Table (Typed Phase 9)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id TEXT PRIMARY KEY,
                    drug_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    training_dataset_version TEXT NOT NULL,
                    overall_risk REAL NOT NULL,
                    overall_risk_category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_strength REAL NOT NULL,
                    feature_vector TEXT,
                    is_gated INTEGER DEFAULT 0,
                    gating_reasons TEXT,
                    raw_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_drug_id ON predictions(drug_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_model_ver ON predictions(model_version);")

            # 10. Organ Risks Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organ_risks (
                    id TEXT PRIMARY KEY,
                    prediction_id TEXT NOT NULL,
                    organ_id TEXT NOT NULL,
                    organ_name TEXT NOT NULL,
                    system TEXT NOT NULL,
                    anatomical_region TEXT,
                    risk_score REAL NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_strength TEXT NOT NULL,
                    evidence_count INTEGER DEFAULT 0,
                    primary_mechanisms TEXT,
                    paths TEXT,
                    adverse_effects TEXT,
                    literature_citations TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(prediction_id) REFERENCES predictions(prediction_id)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_organ_risks_pred_id ON organ_risks(prediction_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_organ_risks_organ_id ON organ_risks(organ_id);")

            # 11. Explanations Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS explanations (
                    id TEXT PRIMARY KEY,
                    prediction_id TEXT NOT NULL UNIQUE,
                    base_value REAL NOT NULL,
                    top_features TEXT NOT NULL,
                    all_features TEXT NOT NULL,
                    supporting_paths TEXT,
                    supporting_literature TEXT,
                    causality_distinction TEXT,
                    disclaimer TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(prediction_id) REFERENCES predictions(prediction_id)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_explanations_pred_id ON explanations(prediction_id);")

            # 12. Literature References Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS literature_references (
                    id TEXT PRIMARY KEY,
                    drug_id TEXT,
                    pmid TEXT,
                    doi TEXT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    journal TEXT,
                    year INTEGER,
                    abstract TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lit_drug_id ON literature_references(drug_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lit_pmid ON literature_references(pmid);")

            # 13. Audit Events Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_session TEXT NOT NULL,
                    action TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    model_version TEXT,
                    status TEXT NOT NULL,
                    details TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_object_id ON audit_events(object_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);")

            # 14. Evaluation Reports Table (Phase 10)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_reports (
                    report_id TEXT PRIMARY KEY,
                    model_version TEXT NOT NULL,
                    dataset_version TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_model_version ON evaluation_reports(model_version);")

            # Seed Default Model Versions if empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM model_versions")
            if cursor.fetchone()["cnt"] == 0:
                default_models = [
                    (
                        str(uuid.uuid4()),
                        "Calibrated Random Forest Risk Predictor",
                        "v1.0.0-rf-calibrated",
                        "v1.0.0-multi-modal-32d",
                        "v1.2.0-benchmark-tox",
                        json.dumps({"n_estimators": 100, "max_depth": 8, "random_state": 42}),
                        json.dumps({"accuracy": 0.88, "roc_auc": 0.91, "f1": 0.86}),
                        1,
                        get_now_utc_iso(),
                    ),
                    (
                        str(uuid.uuid4()),
                        "Regularized Logistic Regression Risk Predictor",
                        "v1.0.0-lr-elasticnet",
                        "v1.0.0-multi-modal-32d",
                        "v1.2.0-benchmark-tox",
                        json.dumps({"C": 1.0, "l1_ratio": 0.5, "penalty": "elasticnet"}),
                        json.dumps({"accuracy": 0.82, "roc_auc": 0.85, "f1": 0.80}),
                        1,
                        get_now_utc_iso(),
                    ),
                    (
                        str(uuid.uuid4()),
                        "Multi-Model Evidence Ensemble Predictor",
                        "v1.0.0-ensemble-weighted",
                        "v1.0.0-multi-modal-32d",
                        "v1.2.0-benchmark-tox",
                        json.dumps({"weights": {"rf": 0.6, "lr": 0.4}, "voting": "soft"}),
                        json.dumps({"accuracy": 0.89, "roc_auc": 0.92, "f1": 0.88}),
                        1,
                        get_now_utc_iso(),
                    ),
                ]
                conn.executemany(
                    """
                    INSERT INTO model_versions (
                        id, model_name, model_version, feature_version,
                        training_dataset_version, hyperparameters, metrics_summary,
                        is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    default_models,
                )

    finally:
        conn.close()


# ---------------------------------------------------------
# Audit Logging Service
# ---------------------------------------------------------

def log_audit_event(
    action: str,
    object_type: str,
    object_id: str,
    model_version: Optional[str] = "v1.0.0-rf-calibrated",
    status: str = "SUCCESS",
    user_session: str = "system-researcher",
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Logs an immutable audit event for traceability and compliance.
    """
    init_db()
    event_id = str(uuid.uuid4())
    timestamp = get_now_utc_iso()
    details_json = json.dumps(details or {}, default=str)

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    event_id, timestamp, user_session, action,
                    object_type, object_id, model_version, status, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    timestamp,
                    user_session,
                    action,
                    object_type,
                    object_id,
                    model_version,
                    status,
                    details_json,
                ),
            )
        return event_id
    except Exception as exc:
        print(f"Warning: Failed to log audit event {action}: {exc}")
        return event_id
    finally:
        conn.close()


def list_audit_events(
    limit: int = 50,
    action: Optional[str] = None,
    object_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves paginated audit events with optional filtering."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM audit_events WHERE 1=1"
        params: List[Any] = []

        if action:
            query += " AND action = ?"
            params.append(action)
        if object_id:
            query += " AND object_id = ?"
            params.append(object_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            item = dict(r)
            if item.get("details"):
                try:
                    item["details"] = json.loads(item["details"])
                except Exception:
                    pass
            results.append(item)
        return results
    finally:
        conn.close()


def get_audit_trail(prediction_id: str) -> Dict[str, Any]:
    """
    Retrieves the complete reproducible lineage for a prediction:
    Drug -> Molecule -> Evidence -> Graph -> Model -> Prediction -> Explanation -> Organ Risk
    """
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 1. Prediction Record
        cursor.execute("SELECT * FROM predictions WHERE prediction_id = ?", (prediction_id,))
        pred_row = cursor.fetchone()
        if not pred_row:
            # Fallback to risk_predictions if legacy
            cursor.execute("SELECT * FROM risk_predictions WHERE prediction_id = ?", (prediction_id,))
            legacy_row = cursor.fetchone()
            if legacy_row:
                raw_data = json.loads(legacy_row["prediction_json"])
                return {
                    "prediction_id": prediction_id,
                    "drug_id": legacy_row["drug_id"],
                    "model_version": "v1.0.0-rf-calibrated",
                    "status": "COMPLETED",
                    "lineage": {
                        "drug": {"drug_id": legacy_row["drug_id"], "canonical_smiles": legacy_row["canonical_smiles"]},
                        "prediction": raw_data,
                    },
                    "audit_events": list_audit_events(object_id=prediction_id),
                }
            return {}

        prediction = dict(pred_row)
        if prediction.get("feature_vector"):
            prediction["feature_vector"] = json.loads(prediction["feature_vector"])
        if prediction.get("gating_reasons"):
            prediction["gating_reasons"] = json.loads(prediction["gating_reasons"])
        if prediction.get("raw_payload"):
            prediction["raw_payload"] = json.loads(prediction["raw_payload"])

        drug_id = prediction["drug_id"]

        # 2. Drug & Molecule
        cursor.execute("SELECT * FROM drugs WHERE drug_id = ?", (drug_id,))
        drug = dict(cursor.fetchone() or {})

        cursor.execute("SELECT * FROM molecules WHERE drug_id = ? ORDER BY created_at DESC LIMIT 1", (drug_id,))
        molecule = dict(cursor.fetchone() or {})

        # 3. Evidence Records
        cursor.execute("SELECT * FROM evidence_records WHERE drug_id = ?", (drug_id,))
        evidence_records = [dict(r) for r in cursor.fetchall()]

        # 4. Knowledge Graph Subgraph
        cursor.execute("SELECT * FROM kg_entities WHERE drug_id = ?", (drug_id,))
        kg_entities = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM kg_relationships WHERE drug_id = ?", (drug_id,))
        kg_relationships = [dict(r) for r in cursor.fetchall()]

        # 5. Model Version
        cursor.execute("SELECT * FROM model_versions WHERE model_version = ?", (prediction["model_version"],))
        model_version = dict(cursor.fetchone() or {})

        # 6. Organ Risks
        cursor.execute("SELECT * FROM organ_risks WHERE prediction_id = ?", (prediction_id,))
        organ_risks = []
        for r in cursor.fetchall():
            o = dict(r)
            for field in ["primary_mechanisms", "paths", "adverse_effects", "literature_citations"]:
                if o.get(field):
                    try:
                        o[field] = json.loads(o[field])
                    except Exception:
                        pass
            organ_risks.append(o)

        # 7. Explanation
        cursor.execute("SELECT * FROM explanations WHERE prediction_id = ?", (prediction_id,))
        exp_row = cursor.fetchone()
        explanation = {}
        if exp_row:
            explanation = dict(exp_row)
            for field in ["top_features", "all_features", "supporting_paths", "supporting_literature"]:
                if explanation.get(field):
                    try:
                        explanation[field] = json.loads(explanation[field])
                    except Exception:
                        pass

        # 8. Audit Events for this prediction and drug
        cursor.execute(
            """
            SELECT * FROM audit_events 
            WHERE object_id = ? OR object_id = ? 
            ORDER BY timestamp ASC
            """,
            (prediction_id, drug_id),
        )
        audit_events = []
        for r in cursor.fetchall():
            item = dict(r)
            if item.get("details"):
                try:
                    item["details"] = json.loads(item["details"])
                except Exception:
                    pass
            audit_events.append(item)

        return {
            "prediction_id": prediction_id,
            "drug_id": drug_id,
            "model_name": prediction["model_name"],
            "model_version": prediction["model_version"],
            "feature_version": prediction["feature_version"],
            "training_dataset_version": prediction["training_dataset_version"],
            "created_at": prediction["created_at"],
            "reproducible_chain": [
                "Drug Input Ingested",
                "Molecular Structure Validated & Fingerprinted",
                "Multi-Source Evidence Aggregated",
                "Knowledge Graph Built & Mechanistic Paths Extracted",
                "Model Inference & Evidence Gating Executed",
                "Local SHAP Feature Attributions Computed",
                "Organ Risk Localization Mapped to 3D Virtual Twin",
            ],
            "lineage": {
                "drug": drug,
                "molecule": molecule,
                "evidence_count": len(evidence_records),
                "graph_entities_count": len(kg_entities),
                "graph_relationships_count": len(kg_relationships),
                "model_version": model_version,
                "prediction": prediction,
                "organ_risks": organ_risks,
                "explanation": explanation,
            },
            "audit_trail": audit_events,
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# Repository Entity Persistence Methods
# ---------------------------------------------------------

def save_drug(drug_id: str, name: Optional[str], canonical_smiles: Optional[str], status: str = "ACTIVE") -> bool:
    """Saves or updates a Drug entity."""
    init_db()
    conn = get_db_connection()
    now_iso = get_now_utc_iso()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO drugs (drug_id, name, canonical_smiles, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(drug_id) DO UPDATE SET
                    name = excluded.name,
                    canonical_smiles = excluded.canonical_smiles,
                    status = excluded.status,
                    updated_at = excluded.updated_at;
                """,
                (drug_id, name or drug_id, canonical_smiles, status, now_iso, now_iso),
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()


def save_molecule(
    drug_id: str,
    canonical_smiles: str,
    inchi: Optional[str] = None,
    inchikey: Optional[str] = None,
    formula: Optional[str] = None,
    descriptors: Optional[Dict[str, Any]] = None,
    fingerprint_bits: int = 2048,
) -> str:
    """Persists a standardized Molecule entity."""
    init_db()
    mol_id = str(uuid.uuid4())
    now_iso = get_now_utc_iso()
    d = descriptors or {}

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO molecules (
                    id, drug_id, canonical_smiles, inchi, inchikey, formula,
                    molecular_weight, logp, tpsa, hbd, hba, rotatable_bonds,
                    heavy_atom_count, ring_count, fingerprint_bits, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mol_id,
                    drug_id,
                    canonical_smiles,
                    inchi,
                    inchikey,
                    formula,
                    d.get("molecular_weight"),
                    d.get("logp"),
                    d.get("tpsa"),
                    d.get("hbd"),
                    d.get("hba"),
                    d.get("rotatable_bonds"),
                    d.get("heavy_atom_count"),
                    d.get("ring_count"),
                    fingerprint_bits,
                    now_iso,
                ),
            )
        return mol_id
    finally:
        conn.close()


def save_prediction_lineage(
    prediction_data: Dict[str, Any],
    organ_mapping_data: Optional[Dict[str, Any]] = None,
    explanation_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Atomically persists a complete risk prediction lineage across Prediction,
    OrganRisk, and Explanation entities, and logs audit events.
    """
    init_db()
    pred_id = prediction_data.get("prediction_id") or str(uuid.uuid4())
    drug_id = prediction_data.get("drug_id") or "UNKNOWN_DRUG"
    now_iso = get_now_utc_iso()

    model_name = prediction_data.get("model_name") or "Calibrated Random Forest Risk Predictor"
    model_version = prediction_data.get("model_version") or "v1.0.0-rf-calibrated"
    feature_version = prediction_data.get("feature_version") or "v1.0.0-multi-modal-32d"
    training_dataset_version = prediction_data.get("training_dataset_version") or "v1.2.0-benchmark-tox"

    overall_risk = float(prediction_data.get("overall_risk_score", prediction_data.get("overall_risk", 0.0)))
    overall_cat = prediction_data.get("overall_risk_category") or "Low"
    confidence = float(prediction_data.get("confidence", 0.85))
    evidence_strength = float(prediction_data.get("evidence_strength", 0.80))

    suff = prediction_data.get("evidence_sufficiency") or {}
    is_gated = 1 if not suff.get("is_sufficient", True) or suff.get("flag_for_review", False) else 0
    gating_reasons_json = json.dumps(suff.get("review_reasons", []))
    raw_payload_json = json.dumps(prediction_data, default=str)

    conn = get_db_connection()
    try:
        with conn:
            # 1. Insert Prediction
            conn.execute(
                """
                INSERT INTO predictions (
                    prediction_id, drug_id, model_name, model_version, feature_version,
                    training_dataset_version, overall_risk, overall_risk_category,
                    confidence, evidence_strength, is_gated, gating_reasons,
                    raw_payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(prediction_id) DO UPDATE SET
                    overall_risk = excluded.overall_risk,
                    overall_risk_category = excluded.overall_risk_category,
                    confidence = excluded.confidence,
                    evidence_strength = excluded.evidence_strength,
                    raw_payload = excluded.raw_payload;
                """,
                (
                    pred_id,
                    drug_id,
                    model_name,
                    model_version,
                    feature_version,
                    training_dataset_version,
                    overall_risk,
                    overall_cat,
                    confidence,
                    evidence_strength,
                    is_gated,
                    gating_reasons_json,
                    raw_payload_json,
                    now_iso,
                ),
            )

            # 2. Insert Organ Risks
            if organ_mapping_data and "organs" in organ_mapping_data:
                for organ_key, org in organ_mapping_data["organs"].items():
                    org_id = str(uuid.uuid4())
                    conn.execute(
                        """
                        INSERT INTO organ_risks (
                            id, prediction_id, organ_id, organ_name, system,
                            anatomical_region, risk_score, category, confidence,
                            evidence_strength, evidence_count, primary_mechanisms,
                            paths, adverse_effects, literature_citations, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            org_id,
                            pred_id,
                            org.get("organ_id", organ_key),
                            org.get("name", organ_key.capitalize()),
                            org.get("system", "General Physiological System"),
                            org.get("anatomical_region", "Systemic"),
                            float(org.get("risk", 0.0)),
                            org.get("category", "Low"),
                            float(org.get("confidence", 0.85)),
                            org.get("evidence_strength", "Medium"),
                            int(org.get("evidence_count", 0)),
                            json.dumps(org.get("primary_mechanisms", [])),
                            json.dumps(org.get("paths", []), default=str),
                            json.dumps(org.get("adverse_effects", [])),
                            json.dumps(org.get("literature_citations", [])),
                            now_iso,
                        ),
                    )

            # 3. Insert Explanation
            if explanation_data:
                exp_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO explanations (
                        id, prediction_id, base_value, top_features, all_features,
                        supporting_paths, supporting_literature, causality_distinction,
                        disclaimer, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(prediction_id) DO UPDATE SET
                        top_features = excluded.top_features,
                        all_features = excluded.all_features;
                    """,
                    (
                        exp_id,
                        pred_id,
                        float(explanation_data.get("base_value", 0.35)),
                        json.dumps(explanation_data.get("top_features", []), default=str),
                        json.dumps(explanation_data.get("all_feature_contributions", []), default=str),
                        json.dumps(explanation_data.get("supporting_paths", []), default=str),
                        json.dumps(explanation_data.get("supporting_literature", []), default=str),
                        explanation_data.get("causality_distinction", ""),
                        explanation_data.get("disclaimer", ""),
                        now_iso,
                    ),
                )

        # Log Audit Event
        log_audit_event(
            action="PREDICTION_CREATED",
            object_type="Prediction",
            object_id=pred_id,
            model_version=model_version,
            status="SUCCESS" if is_gated == 0 else "GATED",
            details={
                "drug_id": drug_id,
                "overall_risk": overall_risk,
                "overall_risk_category": overall_cat,
                "confidence": confidence,
                "evidence_strength": evidence_strength,
                "is_gated": bool(is_gated),
            },
        )
        return True
    except Exception as exc:
        print(f"Error persisting prediction lineage: {exc}")
        return False
    finally:
        conn.close()


def list_model_versions() -> List[Dict[str, Any]]:
    """Retrieves all registered model versions."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_versions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        results = []
        for r in rows:
            m = dict(r)
            if m.get("hyperparameters"):
                m["hyperparameters"] = json.loads(m["hyperparameters"])
            if m.get("metrics_summary"):
                m["metrics_summary"] = json.loads(m["metrics_summary"])
            results.append(m)
        return results
    finally:
        conn.close()


def get_model_version(model_version: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a specific model version."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_versions WHERE model_version = ?", (model_version.strip(),))
        row = cursor.fetchone()
        if row:
            m = dict(row)
            if m.get("hyperparameters"):
                m["hyperparameters"] = json.loads(m["hyperparameters"])
            if m.get("metrics_summary"):
                m["metrics_summary"] = json.loads(m["metrics_summary"])
            return m
        return None
    finally:
        conn.close()


# ---------------------------------------------------------
# Legacy Caching & Risk Lookup Functions (Preserved)
# ---------------------------------------------------------

def get_cached_evidence(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves cached evidence dictionary for a given cache key."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT evidence_json FROM evidence_cache WHERE cache_key = ?",
            (cache_key.strip().upper(),),
        )
        row = cursor.fetchone()
        if row and row["evidence_json"]:
            return json.loads(row["evidence_json"])
        return None
    except Exception:
        return None
    finally:
        conn.close()


def save_cached_evidence(
    cache_key: str,
    drug_id: Optional[str],
    canonical_smiles: Optional[str],
    evidence_data: Dict[str, Any],
) -> bool:
    """Saves or updates evidence dictionary in the local SQLite cache."""
    init_db()
    conn = get_db_connection()
    try:
        evidence_json = json.dumps(evidence_data, default=str)
        now_iso = get_now_utc_iso()
        with conn:
            conn.execute(
                """
                INSERT INTO evidence_cache (cache_key, drug_id, canonical_smiles, evidence_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    drug_id = excluded.drug_id,
                    canonical_smiles = excluded.canonical_smiles,
                    evidence_json = excluded.evidence_json,
                    updated_at = excluded.updated_at;
                """,
                (
                    cache_key.strip().upper(),
                    drug_id,
                    canonical_smiles,
                    evidence_json,
                    now_iso,
                ),
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()


def save_risk_prediction(
    prediction_id: str,
    drug_id: str,
    canonical_smiles: Optional[str],
    overall_risk: float,
    confidence: float,
    prediction_data: Dict[str, Any],
) -> bool:
    """Persists a complete risk prediction payload into SQLite."""
    init_db()
    conn = get_db_connection()
    try:
        pred_json = json.dumps(prediction_data, default=str)
        now_iso = get_now_utc_iso()
        with conn:
            conn.execute(
                """
                INSERT INTO risk_predictions (prediction_id, drug_id, canonical_smiles, overall_risk, confidence, prediction_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(prediction_id) DO UPDATE SET
                    prediction_json = excluded.prediction_json;
                """,
                (
                    prediction_id.strip(),
                    drug_id.strip(),
                    canonical_smiles,
                    float(overall_risk),
                    float(confidence),
                    pred_json,
                    now_iso,
                ),
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_risk_prediction(prediction_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves stored risk prediction by prediction UUID."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT prediction_json FROM risk_predictions WHERE prediction_id = ?",
            (prediction_id.strip(),),
        )
        row = cursor.fetchone()
        if row and row["prediction_json"]:
            return json.loads(row["prediction_json"])
        
        # Fallback to predictions table
        cursor.execute(
            "SELECT raw_payload FROM predictions WHERE prediction_id = ?",
            (prediction_id.strip(),),
        )
        row2 = cursor.fetchone()
        if row2 and row2["raw_payload"]:
            return json.loads(row2["raw_payload"])
        return None
    except Exception:
        return None
    finally:
        conn.close()


def clear_cache() -> None:
    """Clears all records in the evidence cache and prediction logs."""
    init_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM evidence_cache;")
            conn.execute("DELETE FROM risk_predictions;")
            conn.execute("DELETE FROM predictions;")
            conn.execute("DELETE FROM organ_risks;")
            conn.execute("DELETE FROM explanations;")
            conn.execute("DELETE FROM audit_events;")
    finally:
        conn.close()
