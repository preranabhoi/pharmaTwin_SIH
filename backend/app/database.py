"""
Database & Local Caching Module

Provides local SQLite-based persistent caching for biomedical evidence and
prediction audit logs, ensuring fast response times and reproducibility.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings


def get_db_connection() -> sqlite3.Connection:
    """Returns an open SQLite database connection with row factory."""
    db_path = settings.SQLITE_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes local SQLite database tables if they do not exist."""
    conn = get_db_connection()
    try:
        with conn:
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
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cache_drug_id 
                ON evidence_cache(drug_id);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cache_smiles 
                ON evidence_cache(canonical_smiles);
                """
            )
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
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pred_drug_id 
                ON risk_predictions(drug_id);
                """
            )
    finally:
        conn.close()


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
        now_iso = datetime.now(timezone.utc).isoformat()
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
        now_iso = datetime.now(timezone.utc).isoformat()
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
    finally:
        conn.close()
