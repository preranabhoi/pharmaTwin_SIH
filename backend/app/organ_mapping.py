"""
Organ Risk Mapping Module (Phase 6)

Role in Pipeline:
    Explainability -> Organ Risk Mapping -> Human Virtual Twin

Purpose:
    Converts multi-modal biomedical evidence and machine learning risk predictions
    into structured, organ-level risk visualization profiles across physiological systems:
    - Brain (Central Nervous System)
    - Heart (Cardiovascular System)
    - Liver (Hepatic System)
    - Kidney (Renal System)
    - Lung (Respiratory System)
    - Gastrointestinal Tract (Digestive System)
    - Bone Marrow & Blood (Hematological System)
    - Skin (Integumentary System)

Core Biological Trace:
    Drug -> Target -> Gene / Protein -> Pathway -> Tissue -> Organ
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from app.database import get_risk_prediction
from app.evidence_fusion import (
    FusedEvidenceContext,
    align_and_fuse_evidence,
    evaluate_evidence_sufficiency,
)
from app.risk_prediction import (
    classify_risk_category,
    predict_drug_risk,
)
from app.schemas import (
    DrugRiskPredictionRequest,
    EvidenceSufficiencyCheck,
    GraphPathModel,
    NormalizedEvidence,
    OrganDetailRiskModel,
    OrganRiskAssessment,
    OrganRiskMappingResponse,
)


# ---------------------------------------------------------
# 1. Organ Ontology & Anatomical Configuration
# ---------------------------------------------------------

ORGAN_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    "brain": {
        "name": "Brain",
        "system": "Central Nervous System",
        "anatomical_region": "Head & Cranium",
        "keywords": ["brain", "cerebral", "cortex", "cerebellum", "hippocampus", "neuron", "cns", "neuro", "synapse", "dopamine", "gaba"],
    },
    "heart": {
        "name": "Heart",
        "system": "Cardiovascular System",
        "anatomical_region": "Thorax / Mediastinum",
        "keywords": ["heart", "cardiac", "myocardium", "ventricle", "atrium", "cardiomyocyte", "coronary", "arrhythmia", "herg", "qt_prolongation", "top2b"],
    },
    "liver": {
        "name": "Liver",
        "system": "Hepatic System",
        "anatomical_region": "Abdomen (Right Upper Quadrant)",
        "keywords": ["liver", "hepatic", "hepatocyte", "biliary", "bile", "kupffer", "cyp", "cyp2e1", "cyp3a4", "napqi", "hepatotoxicity"],
    },
    "kidney": {
        "name": "Kidney",
        "system": "Renal System",
        "anatomical_region": "Retroperitoneal Space",
        "keywords": ["kidney", "renal", "nephron", "glomerulus", "tubule", "nephrotoxicity", "creatinine", "clearance"],
    },
    "lung": {
        "name": "Lung",
        "system": "Respiratory System",
        "anatomical_region": "Thoracic Cavity",
        "keywords": ["lung", "pulmonary", "alveoli", "bronchial", "respiratory", "bronchi", "pneumonitis"],
    },
    "gastrointestinal": {
        "name": "Gastrointestinal Tract",
        "system": "Digestive System",
        "anatomical_region": "Abdomen & Pelvis",
        "keywords": ["gastrointestinal", "gastric", "stomach", "intestine", "gut", "colon", "duodenum", "ulcer", "mucosa", "prostaglandin", "ptgs1", "ptgs2"],
    },
    "blood": {
        "name": "Bone Marrow & Blood",
        "system": "Hematological & Immune System",
        "anatomical_region": "Systemic Skeletal & Circulatory Cavities",
        "keywords": ["blood", "bone marrow", "plasma", "leukocyte", "platelet", "marrow", "hematological", "anemia", "myelosuppression"],
    },
    "skin": {
        "name": "Skin",
        "system": "Integumentary System",
        "anatomical_region": "External Surface",
        "keywords": ["skin", "dermal", "epidermis", "cutaneous", "dermatitis", "rash", "keratinocyte"],
    },
}


def classify_evidence_strength_tier(score: float) -> str:
    """Classifies continuous evidence score into standard tier: Low, Medium, High."""
    if score >= 0.70:
        return "High"
    elif score >= 0.35:
        return "Medium"
    return "Low"


# ---------------------------------------------------------
# 2. Path-to-Organ Mapping Engine
# ---------------------------------------------------------

def map_path_to_organs(path: Union[GraphPathModel, Dict[str, Any]]) -> List[str]:
    """
    Maps a knowledge graph reasoning path to one or more anatomical organ systems:
    Core biological trace: Drug -> Target -> Gene / Protein -> Pathway -> Tissue -> Organ
    """
    if isinstance(path, dict):
        target_organ = str(path.get("target_organ", "")).lower()
        desc = str(path.get("description", "")).lower()
        node_names = [str(n).lower() for n in path.get("node_names", [])]
        nodes = [str(n).lower() for n in path.get("nodes", [])]
    else:
        target_organ = str(getattr(path, "target_organ", "") or "").lower()
        desc = str(getattr(path, "description", "") or "").lower()
        node_names = [str(n).lower() for n in (getattr(path, "node_names", []) or [])]
        nodes = [str(n).lower() for n in (getattr(path, "nodes", []) or [])]

    matched_organs: Set[str] = set()

    for organ_key, config in ORGAN_ONTOLOGY.items():
        # Check target organ field
        if organ_key in target_organ or config["name"].lower() in target_organ:
            matched_organs.add(organ_key)
            continue

        # Check keywords against description and node names
        for kw in config["keywords"]:
            if (
                kw in target_organ
                or kw in desc
                or any(kw in n for n in node_names)
                or any(kw in n for n in nodes)
            ):
                matched_organs.add(organ_key)
                break

    return sorted(list(matched_organs))


# ---------------------------------------------------------
# 3. Organ Evidence Aggregation
# ---------------------------------------------------------

def aggregate_organ_evidence(
    drug_id: str,
    evidence_records: List[NormalizedEvidence],
    graph_paths: List[Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregates multi-source evidence (Graph paths, SIDER clinical adverse reactions,
    PubMed literature, Bioassays) across physiological organ systems.
    Transparently combines multiple paths and deduplicates records.
    """
    aggregated: Dict[str, Dict[str, Any]] = {
        organ_key: {
            "paths": [],
            "adverse_effects": [],
            "literature": [],
            "mechanisms": [],
            "evidence_count": 0,
            "evidence_strength_score": 0.0,
            "seen_provenance": set(),
        }
        for organ_key in ORGAN_ONTOLOGY
    }

    # 1. Aggregate Knowledge Graph Paths
    for p in graph_paths:
        path_model = p if isinstance(p, GraphPathModel) else GraphPathModel(**p)
        matched_organs = map_path_to_organs(path_model)

        for organ_key in matched_organs:
            path_id = path_model.path_id
            if path_id not in aggregated[organ_key]["seen_provenance"]:
                aggregated[organ_key]["seen_provenance"].add(path_id)
                aggregated[organ_key]["paths"].append(path_model)
                if path_model.description:
                    aggregated[organ_key]["mechanisms"].append(path_model.description)
                elif path_model.node_names:
                    aggregated[organ_key]["mechanisms"].append(" -> ".join(path_model.node_names))

    # 2. Aggregate Multi-Source Evidence Records (Adverse Effects & Literature)
    for record in evidence_records:
        rec_id = f"{record.source}_{record.entity_type}_{record.entity_id}"
        rec_organ_hint = str(record.metadata.get("target_organ", "")).lower() if record.metadata else ""
        entity_name_lower = record.entity_name.lower()

        for organ_key, config in ORGAN_ONTOLOGY.items():
            is_match = False
            if organ_key in rec_organ_hint or config["name"].lower() in rec_organ_hint:
                is_match = True
            else:
                for kw in config["keywords"]:
                    if kw in entity_name_lower or kw in rec_organ_hint:
                        is_match = True
                        break

            if is_match and rec_id not in aggregated[organ_key]["seen_provenance"]:
                aggregated[organ_key]["seen_provenance"].add(rec_id)
                if record.entity_type == "adverse_effect":
                    aggregated[organ_key]["adverse_effects"].append(
                        {
                            "name": record.entity_name,
                            "source": record.source,
                            "confidence": record.confidence,
                            "metadata": record.metadata,
                        }
                    )
                    aggregated[organ_key]["mechanisms"].append(f"Reported Reaction: {record.entity_name}")
                elif record.entity_type == "paper":
                    aggregated[organ_key]["literature"].append(record.metadata or {"title": record.entity_name})

    # 3. Calculate Evidence Strength and Total Evidence Count per Organ
    for organ_key, data in aggregated.items():
        n_paths = len(data["paths"])
        n_adv = len(data["adverse_effects"])
        n_lit = len(data["literature"])
        total_items = n_paths + n_adv + n_lit
        data["evidence_count"] = total_items

        # Continuous evidence strength formula
        # 0.45 * paths + 0.35 * adverse + 0.20 * literature
        s_paths = min(1.0, n_paths / 2.0)
        s_adv = min(1.0, n_adv / 2.0)
        s_lit = min(1.0, n_lit / 1.0)
        score = 0.45 * s_paths + 0.35 * s_adv + 0.20 * s_lit
        data["evidence_strength_score"] = round(float(score), 4)
        data["evidence_strength_tier"] = classify_evidence_strength_tier(score)

    return aggregated


# ---------------------------------------------------------
# 4. Organ Risk Calculation & Scoring
# ---------------------------------------------------------

def calculate_organ_risk(
    organ_key: str,
    raw_prediction: Dict[str, Any],
    aggregated_evidence: Dict[str, Any],
) -> Tuple[float, str, float]:
    """
    Computes (risk_score, risk_category, confidence) for a specific organ:
    - Direct ML endpoints (Heart, Liver, Kidney, Lung, Brain) utilize model predictions.
    - Additional organs (Gastrointestinal, Bone Marrow, Skin) infer risk from evidence density & path confidence.
    """
    organ_risks = raw_prediction.get("organ_risks", {})
    evidence_data = aggregated_evidence.get(organ_key, {})
    ev_strength_score = evidence_data.get("evidence_strength_score", 0.0)

    # 1. Direct ML Target Organ
    if organ_key in organ_risks:
        ep_data = organ_risks[organ_key]
        if isinstance(ep_data, dict):
            risk_score = float(ep_data.get("risk_score", 0.30))
            conf = float(ep_data.get("confidence", 0.70))
        elif isinstance(ep_data, OrganRiskAssessment):
            risk_score = float(ep_data.risk_score)
            conf = float(ep_data.confidence)
        else:
            risk_score = 0.30
            conf = 0.70
    else:
        # 2. Inferred Physiological Organ (e.g. Gastrointestinal, Blood, Skin)
        # Score inferred from knowledge graph path confidences and adverse effect counts
        paths = evidence_data.get("paths", [])
        adverse = evidence_data.get("adverse_effects", [])

        if paths or adverse:
            max_path_conf = max([getattr(p, "confidence", 0.8) for p in paths], default=0.0)
            risk_score = min(0.95, 0.40 * max_path_conf + 0.35 * min(1.0, len(adverse) / 2.0) + 0.25 * ev_strength_score)
            conf = min(0.90, 0.50 + 0.50 * ev_strength_score)
        else:
            # Baseline low risk
            risk_score = 0.15
            conf = 0.65

    risk_score = round(float(np.clip(risk_score, 0.01, 0.99)), 4)
    category = classify_risk_category(risk_score)
    conf = round(float(np.clip(conf, 0.10, 0.98)), 4)

    return risk_score, category, conf


# ---------------------------------------------------------
# 5. Full Organ Risk Profile Builder & Explainer
# ---------------------------------------------------------

def build_full_organ_risk_profile(
    prediction_id_or_dict: Union[str, Dict[str, Any]],
) -> OrganRiskMappingResponse:
    """
    Constructs the complete Phase 6 Organ Risk Profile across all supported systems:
    - Heart, Liver, Kidney, Lung, Brain, Gastrointestinal Tract, Blood & Bone Marrow, Skin.
    - Aggregates multi-source evidence transparently without overclaiming.
    - Formats output for the 3D Human Virtual Twin.
    """
    # 1. Resolve prediction data
    if isinstance(prediction_id_or_dict, str):
        pred_id = prediction_id_or_dict.strip()
        pred_data = get_risk_prediction(pred_id)
        if not pred_data:
            raise ValueError(f"Prediction '{pred_id}' not found in audit logs.")
    else:
        pred_data = prediction_id_or_dict

    prediction_id = pred_data.get("prediction_id", "")
    drug_id = pred_data.get("drug_id", "")
    drug_name = pred_data.get("drug_name") or drug_id
    canonical_smiles = pred_data.get("canonical_smiles")
    overall_risk = float(pred_data.get("overall_risk", 0.5))
    overall_category = pred_data.get("overall_risk_category", classify_risk_category(overall_risk))
    created_at = pred_data.get("created_at", datetime.now(timezone.utc).isoformat())

    # 2. Re-align evidence context
    context = align_and_fuse_evidence(
        drug_id=drug_id,
        smiles=canonical_smiles,
        name=drug_name,
    )

    # 3. Aggregate evidence across all organs
    aggregated_evidence = aggregate_organ_evidence(
        drug_id=drug_id,
        evidence_records=context.evidence_records,
        graph_paths=context.graph_paths,
    )

    # 4. Calculate organ risk models
    organ_models: Dict[str, OrganDetailRiskModel] = {}
    highest_risk_organ = "liver"
    max_organ_risk = -1.0

    for organ_key, config in ORGAN_ONTOLOGY.items():
        r_score, r_cat, r_conf = calculate_organ_risk(
            organ_key=organ_key,
            raw_prediction=pred_data,
            aggregated_evidence=aggregated_evidence,
        )

        if r_score > max_organ_risk:
            max_organ_risk = r_score
            highest_risk_organ = organ_key

        ev_data = aggregated_evidence[organ_key]
        mechanisms = ev_data.get("mechanisms", [])
        if not mechanisms:
            if r_score >= 0.70:
                mechanisms.append(f"Predicted structural liability for {config['name'].lower()} toxicity")
            else:
                mechanisms.append(f"No specific high-affinity {config['name'].lower()} liability detected")

        organ_models[organ_key] = OrganDetailRiskModel(
            organ_id=organ_key,
            name=config["name"],
            system=config["system"],
            anatomical_region=config["anatomical_region"],
            risk=r_score,
            category=r_cat,
            confidence=r_conf,
            evidence_strength=ev_data["evidence_strength_tier"],
            evidence_strength_score=ev_data["evidence_strength_score"],
            evidence_count=ev_data["evidence_count"],
            primary_mechanisms=mechanisms[:4],
            paths=ev_data.get("paths", []),
            adverse_effects=ev_data.get("adverse_effects", []),
            literature_citations=ev_data.get("literature", []),
        )

    # 5. Sufficiency Check
    sufficiency = evaluate_evidence_sufficiency(context)

    return OrganRiskMappingResponse(
        prediction_id=prediction_id,
        drug_id=drug_id,
        drug_name=drug_name,
        canonical_smiles=canonical_smiles,
        highest_risk_organ=highest_risk_organ,
        overall_risk_score=overall_risk,
        overall_risk_category=overall_category,
        organs=organ_models,
        supported_organs=list(ORGAN_ONTOLOGY.keys()),
        evidence_sufficiency=sufficiency,
        disclaimer=(
            "Research-grade prototype. Organ risk mapping represents potential risk signals derived from "
            "computational models and biomedical evidence fusion. It is not a clinical diagnosis or treatment recommendation."
        ),
        created_at=created_at,
    )


def explain_organ_risk(
    organ_key: str,
    prediction_id_or_dict: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Returns an in-depth mechanistic explanation for a specific organ risk assessment.
    """
    profile = build_full_organ_risk_profile(prediction_id_or_dict)
    organ_key_norm = organ_key.strip().lower()

    if organ_key_norm not in profile.organs:
        raise ValueError(
            f"Organ '{organ_key}' is not in the supported ontology: {list(ORGAN_ONTOLOGY.keys())}"
        )

    organ_detail = profile.organs[organ_key_norm]
    return {
        "prediction_id": profile.prediction_id,
        "drug_id": profile.drug_id,
        "drug_name": profile.drug_name,
        "organ_id": organ_detail.organ_id,
        "organ_name": organ_detail.name,
        "system": organ_detail.system,
        "risk_score": organ_detail.risk,
        "category": organ_detail.category,
        "confidence": organ_detail.confidence,
        "evidence_strength": organ_detail.evidence_strength,
        "evidence_strength_score": organ_detail.evidence_strength_score,
        "evidence_count": organ_detail.evidence_count,
        "primary_mechanisms": organ_detail.primary_mechanisms,
        "supporting_paths": [p.model_dump() for p in organ_detail.paths],
        "adverse_effects": organ_detail.adverse_effects,
        "literature_citations": organ_detail.literature_citations,
        "disclaimer": profile.disclaimer,
    }
