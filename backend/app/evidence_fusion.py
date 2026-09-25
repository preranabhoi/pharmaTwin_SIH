"""
Evidence Fusion & Transparent Reasoning Engine (Phase 4)

Components:
- Standardized Numerical Evidence Alignment: Combines Molecular, Graph, Historical, Literature evidence.
- Transparent Confidence & Evidence Strength Calculation: Strictly separates prediction, evidence strength, and confidence.
- Molecular Similarity Engine: Tanimoto coefficient calculation over Morgan fingerprints.
- Evidence Sufficiency Gating: Flags sparse/insufficient evidence for expert review without inflating confidence.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.data_ingestion import fetch_drug_biomedical_data, resolve_drug_identifier
from app.knowledge_graph import build_drug_subgraph, find_mechanistic_paths
from app.molecular_processing import process_smiles, validate_smiles
from app.schemas import (
    EvidenceSufficiencyCheck,
    MolecularSimilarityMatch,
    NormalizedEvidence,
)


# ---------------------------------------------------------
# 1. Benchmark Reference Drugs for Similarity Evidence
# ---------------------------------------------------------

BENCHMARK_REFERENCE_DRUGS = [
    {
        "drug_id": "CHEMBL112",
        "name": "Acetaminophen",
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "known_organ_risks": ["Liver (Hepatotoxicity / NAPQI necrosis)", "Kidney (Tubular strain)"],
    },
    {
        "drug_id": "CHEMBL25",
        "name": "Aspirin",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "known_organ_risks": ["Gastrointestinal (Gastric ulceration / Hemorrhage)"],
    },
    {
        "drug_id": "CHEMBL521",
        "name": "Ibuprofen",
        "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "known_organ_risks": ["Kidney (Renal hemodynamic impairment)", "Gastrointestinal (Dyspepsia)"],
    },
    {
        "drug_id": "CHEMBL53",
        "name": "Doxorubicin",
        "smiles": "COC1=C(C(=O)C2=C(C1=O)C(=CC3=C2C(=O)C4=C(C3=O)C(=CC=C4)O)O)C(=O)CO",
        "known_organ_risks": ["Heart (Cardiomyopathy / TOP2B mitochondrial dysfunction)", "Bone Marrow"],
    },
]


# ---------------------------------------------------------
# 2. Tanimoto Molecular Similarity Engine
# ---------------------------------------------------------

def calculate_tanimoto_similarity(
    fp1: List[int], fp2: List[int]
) -> float:
    """
    Computes standard Tanimoto similarity coefficient between two binary bitvectors.
    T(A, B) = |A ∩ B| / |A ∪ B|
    """
    if not fp1 or not fp2 or len(fp1) != len(fp2):
        return 0.0

    a = np.array(fp1, dtype=bool)
    b = np.array(fp2, dtype=bool)

    intersection = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()

    if union == 0:
        return 0.0

    return round(float(intersection / union), 4)


def find_similar_benchmark_compounds(
    query_fp: List[int], top_k: int = 3
) -> List[MolecularSimilarityMatch]:
    """
    Compares query fingerprint against benchmark reference compounds.
    """
    matches: List[Tuple[float, Dict[str, Any]]] = []

    for ref in BENCHMARK_REFERENCE_DRUGS:
        try:
            ref_proc = process_smiles(ref["smiles"], include_svg=False)
            ref_fp = ref_proc["fingerprint"]["bits"]
            sim = calculate_tanimoto_similarity(query_fp, ref_fp)
            matches.append((sim, ref))
        except Exception:
            continue

    matches.sort(key=lambda x: x[0], reverse=True)

    results: List[MolecularSimilarityMatch] = []
    for sim, ref in matches[:top_k]:
        results.append(
            MolecularSimilarityMatch(
                reference_drug_id=ref["drug_id"],
                reference_drug_name=ref["name"],
                tanimoto_similarity=sim,
                known_organ_risks=ref["known_organ_risks"],
                disclaimer="Molecular similarity informs prior evidence retrieval, but does not prove clinical toxicity.",
            )
        )

    return results


# ---------------------------------------------------------
# 3. Standardized Multi-Modal Evidence Alignment
# ---------------------------------------------------------

class FusedEvidenceContext:
    """
    Container holding aligned heterogeneous multi-source evidence:
    - Molecular descriptors & fingerprint
    - Multi-source biomedical evidence records
    - Knowledge graph subgraphs & multi-hop paths
    - Similarity evidence
    """

    def __init__(
        self,
        drug_id: str,
        drug_name: Optional[str] = None,
        canonical_smiles: Optional[str] = None,
        descriptors: Optional[Dict[str, float | int]] = None,
        fingerprint: Optional[List[int]] = None,
        evidence_records: Optional[List[NormalizedEvidence]] = None,
        graph_paths: Optional[List[Any]] = None,
        similarity_matches: Optional[List[MolecularSimilarityMatch]] = None,
    ):
        self.drug_id = drug_id
        self.drug_name = drug_name
        self.canonical_smiles = canonical_smiles
        self.descriptors = descriptors or {}
        self.fingerprint = fingerprint or [0] * 2048
        self.evidence_records = evidence_records or []
        self.graph_paths = graph_paths or []
        self.similarity_matches = similarity_matches or []

    def to_feature_vector(self) -> np.ndarray:
        """
        Builds a normalized, fixed-dimension numerical feature vector (32 dimensions)
        for risk prediction models:
        - [0:10]: Physicochemical molecular descriptors (normalized)
        - [10:15]: Organ knowledge graph path counts (heart, liver, kidney, lung, brain)
        - [15:20]: Organ knowledge graph max confidence scores
        - [20:25]: SIDER clinical adverse effect counts per organ
        - [25:28]: Literature count & confidence metrics
        - [28:32]: Max Tanimoto similarity to organ reference toxicities
        """
        features = np.zeros(32, dtype=np.float32)

        # 1. Molecular Descriptors (Scaled/Normalized)
        d = self.descriptors
        features[0] = min(1.0, float(d.get("molecular_weight", 200.0)) / 800.0)
        features[1] = max(0.0, min(1.0, (float(d.get("logp", 1.0)) + 3.0) / 10.0))
        features[2] = min(1.0, float(d.get("tpsa", 50.0)) / 250.0)
        features[3] = min(1.0, float(d.get("hbd", 1)) / 10.0)
        features[4] = min(1.0, float(d.get("hba", 2)) / 15.0)
        features[5] = min(1.0, float(d.get("rotatable_bonds", 2)) / 15.0)
        features[6] = min(1.0, float(d.get("heavy_atom_count", 10)) / 50.0)
        features[7] = min(1.0, float(d.get("ring_count", 1)) / 8.0)
        features[8] = min(1.0, float(d.get("aromatic_ring_count", 1)) / 6.0)
        features[9] = float(sum(self.fingerprint)) / 2048.0  # active bit fraction

        # 2. Organ Knowledge Graph Features (Heart, Liver, Kidney, Lung, Brain)
        organs = ["heart", "liver", "kidney", "lung", "brain"]
        for i, organ in enumerate(organs):
            paths_for_organ = [
                p for p in self.graph_paths
                if getattr(p, "target_organ", "") and organ in getattr(p, "target_organ", "").lower()
            ]
            features[10 + i] = min(1.0, len(paths_for_organ) / 5.0)
            features[15 + i] = max([getattr(p, "confidence", 0.0) for p in paths_for_organ], default=0.0)

        # 3. SIDER Adverse Reactions per Organ
        for i, organ in enumerate(organs):
            adv_for_organ = [
                e for e in self.evidence_records
                if e.entity_type == "adverse_effect" and organ in str(e.metadata.get("target_organ", "")).lower()
            ]
            features[20 + i] = min(1.0, len(adv_for_organ) / 4.0)

        # 4. Literature Evidence Features
        lit_records = [e for e in self.evidence_records if e.entity_type == "paper"]
        features[25] = min(1.0, len(lit_records) / 5.0)
        features[26] = max([e.confidence for e in lit_records], default=0.0)
        features[27] = min(1.0, len(self.evidence_records) / 20.0)  # total evidence density

        # 5. Max Tanimoto Similarity Features
        if self.similarity_matches:
            features[28] = self.similarity_matches[0].tanimoto_similarity
        if len(self.similarity_matches) > 1:
            features[29] = self.similarity_matches[1].tanimoto_similarity
        features[30] = min(1.0, float(np.mean([m.tanimoto_similarity for m in self.similarity_matches])) if self.similarity_matches else 0.0)
        features[31] = 1.0 if any(m.tanimoto_similarity > 0.60 for m in self.similarity_matches) else 0.0

        return features


# ---------------------------------------------------------
# 4. Transparent Evidence-Weighting Calculation
# ---------------------------------------------------------

def calculate_evidence_strength(
    context: FusedEvidenceContext,
) -> float:
    """
    Computes a transparent evidence-strength score S in [0.0, 1.0]:
    S = 0.20 * S_mol + 0.30 * S_graph + 0.30 * S_hist + 0.20 * S_lit
    """
    # Molecular feature completeness
    s_mol = 1.0 if context.descriptors and sum(context.fingerprint) > 0 else 0.3

    # Graph evidence volume
    s_graph = min(1.0, len(context.graph_paths) / 3.0)

    # Historical / adverse clinical evidence
    adverse_records = [e for e in context.evidence_records if e.entity_type == "adverse_effect"]
    s_hist = min(1.0, len(adverse_records) / 2.0)

    # Literature citations
    lit_records = [e for e in context.evidence_records if e.entity_type == "paper"]
    s_lit = min(1.0, len(lit_records) / 2.0)

    strength = (
        0.20 * s_mol
        + 0.30 * s_graph
        + 0.30 * s_hist
        + 0.20 * s_lit
    )
    return round(float(strength), 4)


def calculate_prediction_confidence(
    model_raw_confidence: float,
    evidence_strength: float,
    sufficiency_passed: bool,
) -> float:
    """
    Calculates overall prediction confidence without inflating certainty:
    If evidence is insufficient, scales down confidence and never exceeds 0.55.
    """
    base_conf = 0.40 * model_raw_confidence + 0.60 * evidence_strength
    if not sufficiency_passed:
        base_conf = min(0.55, base_conf * 0.70)
    return round(max(0.10, min(0.99, float(base_conf))), 4)


# ---------------------------------------------------------
# 5. Evidence Sufficiency Gating
# ---------------------------------------------------------

def evaluate_evidence_sufficiency(
    context: FusedEvidenceContext,
) -> EvidenceSufficiencyCheck:
    """
    Evaluates multi-source evidence criteria.
    If criteria are not met, flags prediction for manual review.
    """
    has_structure = bool(context.canonical_smiles or context.descriptors)
    has_descriptors = len(context.descriptors) >= 8
    has_bio_evidence = len(context.evidence_records) >= 2
    has_graph_paths = len(context.graph_paths) >= 1
    has_literature = any(e.entity_type == "paper" for e in context.evidence_records)

    criteria = {
        "valid_structure": has_structure,
        "complete_descriptors": has_descriptors,
        "biological_evidence_present": has_bio_evidence,
        "knowledge_graph_paths_present": has_graph_paths,
        "literature_citations_present": has_literature,
    }

    reasons: List[str] = []
    if not has_bio_evidence:
        reasons.append("Sparse or missing multi-source biological target/assay records.")
    if not has_graph_paths:
        reasons.append("No traceable multi-hop knowledge graph paths to organ endpoints.")
    if not has_literature:
        reasons.append("No peer-reviewed literature citations indexed for this compound.")

    # Sufficiency threshold: must pass at least 3 criteria
    criteria_passed_count = sum(criteria.values())
    is_sufficient = criteria_passed_count >= 3
    flag_for_review = not is_sufficient

    return EvidenceSufficiencyCheck(
        is_sufficient=is_sufficient,
        flag_for_review=flag_for_review,
        review_reasons=reasons,
        criteria_met=criteria,
    )


# ---------------------------------------------------------
# 6. Public Evidence Fusion Pipeline
# ---------------------------------------------------------

def align_and_fuse_evidence(
    drug_id: Optional[str] = None,
    smiles: Optional[str] = None,
    name: Optional[str] = None,
) -> FusedEvidenceContext:
    """
    Collects, aligns, and standardizes multi-source evidence:
    - Normalizes molecular structure and descriptors via molecular_processing
    - Retrieves multi-source biomedical annotations via data_ingestion
    - Extracts knowledge graph paths via knowledge_graph
    - Calculates Tanimoto similarity against benchmark compounds
    """
    # 1. Resolve drug identifier & SMILES
    resolved_key = resolve_drug_identifier(drug_id or name or smiles or "")
    target_drug_id = resolved_key or (drug_id.strip().upper() if drug_id else "UNKNOWN_DRUG")

    canonical_smiles = smiles
    descriptors = {}
    fingerprint = [0] * 2048
    drug_name = name

    # 2. Molecular Processing
    if smiles:
        try:
            mol_proc = process_smiles(smiles, include_svg=False)
            canonical_smiles = mol_proc["canonical_smiles"]
            descriptors = mol_proc["descriptors"]
            fingerprint = mol_proc["fingerprint"]["bits"]
        except Exception:
            pass

    # 3. Biomedical Data Ingestion
    evidence_records: List[NormalizedEvidence] = []
    try:
        ev_data = fetch_drug_biomedical_data(
            drug_id=target_drug_id,
            smiles=canonical_smiles,
            name=name,
        )
        if ev_data and "evidence" in ev_data:
            evidence_records = [NormalizedEvidence(**e) for e in ev_data["evidence"]]
            if not drug_name and ev_data.get("drug_name"):
                drug_name = ev_data["drug_name"]
            if not canonical_smiles and ev_data.get("canonical_smiles"):
                canonical_smiles = ev_data["canonical_smiles"]
    except Exception:
        pass

    # If SMILES was not originally given but retrieved from evidence
    if canonical_smiles and (not descriptors or sum(fingerprint) == 0):
        try:
            mol_proc = process_smiles(canonical_smiles, include_svg=False)
            descriptors = mol_proc["descriptors"]
            fingerprint = mol_proc["fingerprint"]["bits"]
        except Exception:
            pass

    # 4. Knowledge Graph Reasoning Paths
    graph_paths = []
    try:
        graph_paths = find_mechanistic_paths(target_drug_id)
    except Exception:
        pass

    # 5. Similarity Matches
    similarity_matches = []
    if sum(fingerprint) > 0:
        similarity_matches = find_similar_benchmark_compounds(fingerprint, top_k=3)

    return FusedEvidenceContext(
        drug_id=target_drug_id,
        drug_name=drug_name or target_drug_id,
        canonical_smiles=canonical_smiles,
        descriptors=descriptors,
        fingerprint=fingerprint,
        evidence_records=evidence_records,
        graph_paths=graph_paths,
        similarity_matches=similarity_matches,
    )
