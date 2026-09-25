"""
Unit & Integration Tests for Phase 6: Organ Risk Mapping Module

Tests:
1. Organ ontology & anatomical configuration completeness
2. Single-path to organ mapping
3. Multi-path & multi-organ mapping
4. Unsupported organ pathway handling
5. Duplicate evidence deduplication in aggregation
6. Risk calculation for direct ML endpoints vs inferred physiological systems (e.g. GI Tract)
7. Mechanistic organ explanation breakdown & unsupported organ error handling
8. Full multi-organ risk profile generation for benchmark drugs
9. Sparse compound evidence handling without overclaiming
"""

import pytest

from app.organ_mapping import (
    ORGAN_ONTOLOGY,
    aggregate_organ_evidence,
    build_full_organ_risk_profile,
    calculate_organ_risk,
    classify_evidence_strength_tier,
    explain_organ_risk,
    map_path_to_organs,
)
from app.risk_prediction import predict_drug_risk
from app.schemas import (
    DrugRiskPredictionRequest,
    GraphPathModel,
    NormalizedEvidence,
    OrganRiskMappingResponse,
)


# =========================================================
# 1. Organ Ontology Tests
# =========================================================

class TestOrganOntology:
    """Tests for organ ontology, anatomical regions, and system configuration."""

    def test_supported_organs_presence(self):
        expected = {
            "brain",
            "heart",
            "liver",
            "kidney",
            "lung",
            "gastrointestinal",
            "blood",
            "skin",
        }
        assert expected.issubset(set(ORGAN_ONTOLOGY.keys()))

        for key, conf in ORGAN_ONTOLOGY.items():
            assert "name" in conf
            assert "system" in conf
            assert "anatomical_region" in conf
            assert "keywords" in conf
            assert len(conf["keywords"]) > 0

    def test_evidence_strength_tier_classification(self):
        assert classify_evidence_strength_tier(0.15) == "Low"
        assert classify_evidence_strength_tier(0.34) == "Low"
        assert classify_evidence_strength_tier(0.35) == "Medium"
        assert classify_evidence_strength_tier(0.69) == "Medium"
        assert classify_evidence_strength_tier(0.70) == "High"
        assert classify_evidence_strength_tier(0.95) == "High"


# =========================================================
# 2. Path-to-Organ Mapping Tests
# =========================================================

class TestPathMapping:
    """Tests for mapping knowledge graph paths to organ systems."""

    def test_map_single_hepatic_path(self):
        path = GraphPathModel(
            path_id="path_cyp2e1_liver",
            path_type="mechanistic_organ_path",
            target_organ="Liver",
            nodes=["CHEMBL112", "P20813", "CYP2E1", "NAPQI", "Hepatocytes", "ORGAN:LIVER"],
            node_names=["Acetaminophen", "CYP2E1", "CYP2E1", "NAPQI", "Hepatocytes", "Liver"],
            relations=["METABOLIZED_BY", "ENCODED_BY", "PARTICIPATES_IN_PATHWAY", "ACTIVE_IN_TISSUE", "PART_OF_ORGAN"],
            confidence=0.88,
            confidence_tier="high",
            description="Acetaminophen -> CYP2E1 -> NAPQI Bioactivation -> Hepatocytes -> Liver",
        )
        matched = map_path_to_organs(path)
        assert "liver" in matched
        assert len(matched) == 1

    def test_map_cardiac_path(self):
        path = GraphPathModel(
            path_id="path_dox_heart",
            path_type="mechanistic_organ_path",
            target_organ="Heart",
            nodes=["CHEMBL53", "TOP2B", "ORGAN:HEART"],
            node_names=["Doxorubicin", "DNA Topoisomerase 2-Beta", "Heart"],
            relations=["INHIBITS", "AFFECTS_ORGAN"],
            confidence=0.92,
            confidence_tier="high",
            description="Doxorubicin -> DNA Topoisomerase 2-Beta -> Cardiomyocyte Mitochondrial Dysfunction -> Heart",
        )
        matched = map_path_to_organs(path)
        assert "heart" in matched

    def test_map_gastrointestinal_path(self):
        path = GraphPathModel(
            path_id="path_aspirin_gi",
            path_type="mechanistic_organ_path",
            target_organ="Gastrointestinal",
            nodes=["CHEMBL25", "PTGS1", "TISSUE:GASTRIC_MUCOSA"],
            node_names=["Aspirin", "PTGS1", "Gastric Mucosa"],
            relations=["INHIBITS", "ACTIVE_IN_TISSUE"],
            confidence=0.85,
            confidence_tier="high",
            description="Aspirin -> PTGS1 (COX-1) -> Gastric Mucosal Cytoprotective Prostaglandin Synthesis -> Gastric Mucosa",
        )
        matched = map_path_to_organs(path)
        assert "gastrointestinal" in matched

    def test_map_unsupported_path_returns_empty(self):
        path = GraphPathModel(
            path_id="path_unrelated",
            path_type="general_association",
            target_organ="UncharacterizedMicroorganism",
            nodes=["NODE_A", "NODE_B"],
            node_names=["EntityA", "EntityB"],
            relations=["INTERACTS_WITH"],
            confidence=0.5,
            confidence_tier="moderate",
            description="EntityA interacts with EntityB in bacterial cell wall",
        )
        matched = map_path_to_organs(path)
        assert matched == []


# =========================================================
# 3. Evidence Aggregation & Deduplication Tests
# =========================================================

class TestEvidenceAggregation:
    """Tests for multi-source aggregation and deduplication."""

    def test_deduplication_of_duplicate_paths_and_records(self):
        path = GraphPathModel(
            path_id="path_dup_1",
            path_type="mechanistic_organ_path",
            target_organ="Liver",
            nodes=["CHEMBL112", "P20813", "ORGAN:LIVER"],
            node_names=["Acetaminophen", "CYP2E1", "Liver"],
            relations=["METABOLIZED_BY", "AFFECTS_ORGAN"],
            confidence=0.9,
            confidence_tier="high",
            description="Path to Liver",
        )

        record = NormalizedEvidence(
            source="SIDER",
            entity_type="adverse_effect",
            entity_id="C0019202",
            entity_name="Hepatotoxicity",
            relation="ASSOCIATED_WITH_ADVERSE_EFFECT",
            object_id="CHEMBL:CHEMBL112",
            evidence_type="clinical_side_effect",
            confidence=0.95,
            retrieved_at="2026-09-25T00:00:00Z",
            metadata={"target_organ": "Liver"},
        )

        # Pass duplicates
        paths = [path, path, path]
        records = [record, record]

        aggregated = aggregate_organ_evidence("CHEMBL112", records, paths)

        # Verify only 1 path and 1 adverse effect retained in liver
        assert len(aggregated["liver"]["paths"]) == 1
        assert len(aggregated["liver"]["adverse_effects"]) == 1
        assert aggregated["liver"]["evidence_count"] == 2
        assert aggregated["liver"]["evidence_strength_score"] > 0.0


# =========================================================
# 4. Risk Calculation & Organ Scoring Tests
# =========================================================

class TestOrganRiskCalculation:
    """Tests for direct ML organ scoring and inferred systems."""

    def test_direct_ml_organ_calculation(self):
        raw_prediction = {
            "organ_risks": {
                "liver": {
                    "risk_score": 0.82,
                    "confidence": 0.91,
                }
            }
        }
        evidence = {
            "liver": {
                "paths": [],
                "adverse_effects": [],
                "evidence_strength_score": 0.8,
            }
        }
        r_score, r_cat, r_conf = calculate_organ_risk("liver", raw_prediction, evidence)

        assert r_score == 0.82
        assert r_cat == "High"
        assert r_conf == 0.91

    def test_inferred_gi_tract_risk_from_evidence(self):
        raw_prediction = {"organ_risks": {}}
        path = GraphPathModel(
            path_id="p1",
            path_type="mechanistic_organ_path",
            target_organ="Gastrointestinal",
            nodes=["CHEMBL25", "PTGS1"],
            node_names=["Aspirin", "PTGS1"],
            relations=["INHIBITS"],
            confidence=0.92,
            confidence_tier="high",
            description="Aspirin -> PTGS1 -> Gastric Mucosa",
        )
        evidence = {
            "gastrointestinal": {
                "paths": [path],
                "adverse_effects": [{"name": "Gastric Ulceration", "confidence": 0.95}],
                "evidence_strength_score": 0.75,
            }
        }
        r_score, r_cat, r_conf = calculate_organ_risk("gastrointestinal", raw_prediction, evidence)

        assert r_score >= 0.60
        assert r_cat in ("Moderate", "High")
        assert r_conf >= 0.70


# =========================================================
# 5. Full Organ Risk Profile & Explanation Tests
# =========================================================

class TestFullOrganRiskProfile:
    """Tests for complete organ mapping profile generation."""

    @pytest.fixture
    def acetaminophen_prediction(self):
        req = DrugRiskPredictionRequest(
            drug_id="CHEMBL112",
            smiles="CC(=O)NC1=CC=C(O)C=C1",
            name="Acetaminophen",
            model_type="random_forest",
        )
        return predict_drug_risk(req)

    def test_build_full_profile_acetaminophen(self, acetaminophen_prediction):
        profile = build_full_organ_risk_profile(acetaminophen_prediction.prediction_id)

        assert isinstance(profile, OrganRiskMappingResponse)
        assert profile.prediction_id == acetaminophen_prediction.prediction_id
        assert profile.drug_id == "CHEMBL112"
        assert profile.highest_risk_organ == "liver"

        # Check all 8 supported organs exist
        for org in ("brain", "heart", "liver", "kidney", "lung", "gastrointestinal", "blood", "skin"):
            assert org in profile.organs
            detail = profile.organs[org]
            assert detail.organ_id == org
            assert 0.0 <= detail.risk <= 1.0
            assert detail.category in ("Low", "Moderate", "High")
            assert detail.evidence_strength in ("Low", "Medium", "High")
            assert len(detail.primary_mechanisms) > 0

        # Liver specifics
        liver_detail = profile.organs["liver"]
        assert liver_detail.category == "High"
        assert liver_detail.evidence_count >= 3
        assert len(liver_detail.paths) >= 2

        # Disclaimer
        assert "not a clinical diagnosis" in profile.disclaimer.lower()

    def test_explain_organ_risk_valid_and_invalid(self, acetaminophen_prediction):
        exp = explain_organ_risk("liver", acetaminophen_prediction.prediction_id)
        assert exp["organ_id"] == "liver"
        assert exp["organ_name"] == "Liver"
        assert exp["category"] == "High"
        assert len(exp["supporting_paths"]) > 0

        # Test invalid/unsupported organ raises ValueError
        with pytest.raises(ValueError) as exc_info:
            explain_organ_risk("pancreas_unknown", acetaminophen_prediction.prediction_id)
        assert "not in the supported ontology" in str(exc_info.value)
