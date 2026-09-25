from datetime import datetime
import pytest

from app.data_ingestion import (
    ChEMBLAdapter,
    PubChemAdapter,
    PubMedAdapter,
    SIDERAdapter,
    UniProtAdapter,
    fetch_drug_biomedical_data,
    load_curated_demo_dataset,
    resolve_and_deduplicate_evidence,
    resolve_drug_identifier,
)
from app.database import clear_cache
from app.schemas import NormalizedEvidence


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure clean cache before each test."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------
# 1. Adapter Unit Tests
# ---------------------------------------------------------

def test_pubchem_adapter_normalize():
    adapter = PubChemAdapter()
    raw_mock = {"id": {"id": {"cid": 1983}}}
    parsed = adapter.parse({"PC_Compounds": [raw_mock]})
    records = adapter.normalize(parsed, subject_id="CHEMBL:CHEMBL112")

    assert len(records) == 1
    rec = records[0]
    assert rec.source == "PubChem"
    assert rec.entity_type == "drug"
    assert rec.entity_id == "PUBCHEM:CID1983"
    assert rec.confidence == 1.0
    assert rec.retrieved_at is not None


def test_chembl_adapter_normalize():
    adapter = ChEMBLAdapter()
    raw_mock = [
        {
            "target_chembl_id": "CHEMBL221",
            "action_type": "INHIBITOR",
            "mechanism_of_action": "Cyclooxygenase-1 inhibitor",
        }
    ]
    records = adapter.normalize(raw_mock, subject_id="CHEMBL:CHEMBL112")

    assert len(records) == 1
    rec = records[0]
    assert rec.source == "ChEMBL"
    assert rec.entity_type == "target"
    assert rec.entity_id == "CHEMBL:CHEMBL221"
    assert rec.relation == "inhibitor"
    assert rec.confidence == 0.90


def test_uniprot_adapter_normalize():
    adapter = UniProtAdapter()
    raw_mock = [
        {
            "primaryAccession": "P23219",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Prostaglandin G/H synthase 1"}
                }
            },
        }
    ]
    records = adapter.normalize(raw_mock, subject_id="CHEMBL:CHEMBL112")

    assert len(records) == 1
    rec = records[0]
    assert rec.source == "UniProt"
    assert rec.entity_type == "protein"
    assert rec.entity_id == "UNIPROT:P23219"
    assert "Prostaglandin" in rec.entity_name


def test_pubmed_adapter_normalize():
    adapter = PubMedAdapter()
    records = adapter.normalize(["15214041", "18451734"], subject_id="CHEMBL:CHEMBL112")

    assert len(records) == 2
    assert records[0].entity_id == "PMID:15214041"
    assert records[0].entity_type == "paper"
    assert records[0].source == "PubMed"


# ---------------------------------------------------------
# 2. Provenance Tracking & Timestamps
# ---------------------------------------------------------

def test_provenance_tracking():
    adapter = ChEMBLAdapter()
    prov = adapter.get_provenance()
    assert prov["source"] == "ChEMBL"
    assert prov["source_version"] == "v33"
    assert "retrieved_at" in prov
    # Validate ISO timestamp parse
    dt = datetime.fromisoformat(prov["retrieved_at"])
    assert dt is not None


# ---------------------------------------------------------
# 3. Duplicate Resolution & Entity Resolution
# ---------------------------------------------------------

def test_duplicate_resolution_and_confidence_fusion():
    ev1 = NormalizedEvidence(
        source="ChEMBL",
        entity_type="target",
        entity_id="CHEMBL:CHEMBL221",
        entity_name="COX-1",
        relation="inhibits",
        object_id="CHEMBL:CHEMBL112",
        confidence=0.75,
        evidence_type="bioassay",
        retrieved_at="2026-09-25T12:00:00Z",
        metadata={"assay": "A1"},
    )
    # Duplicate with higher confidence and additional metadata
    ev2 = NormalizedEvidence(
        source="ChEMBL",
        entity_type="target",
        entity_id="CHEMBL:CHEMBL221",
        entity_name="COX-1",
        relation="inhibits",
        object_id="CHEMBL:CHEMBL112",
        confidence=0.92,
        evidence_type="bioassay",
        retrieved_at="2026-09-25T12:05:00Z",
        metadata={"ic50_um": 26.0},
    )
    # Distinct record
    ev3 = NormalizedEvidence(
        source="UniProt",
        entity_type="protein",
        entity_id="UNIPROT:P23219",
        entity_name="PTGS1",
        relation="targets",
        object_id="CHEMBL:CHEMBL112",
        confidence=0.90,
        evidence_type="curated_protein_database",
        retrieved_at="2026-09-25T12:00:00Z",
    )

    deduped = resolve_and_deduplicate_evidence([ev1, ev2, ev3])
    assert len(deduped) == 2

    # Check that highest confidence was retained and metadata merged
    chembl_rec = next(r for r in deduped if r.entity_id == "CHEMBL:CHEMBL221")
    assert chembl_rec.confidence == 0.92
    assert "ic50_um" in chembl_rec.metadata
    assert "assay" in chembl_rec.metadata


# ---------------------------------------------------------
# 4. Adapter Failure Handling (Resilience)
# ---------------------------------------------------------

def test_adapter_failure_graceful_handling():
    class BrokenAdapter(PubChemAdapter):
        def fetch(self, query: str, **kwargs):
            raise ConnectionError("Simulated network failure")

    adapter = BrokenAdapter()
    evidence = adapter.get_evidence(query="aspirin", subject_id="CHEMBL:CHEMBL25")
    assert evidence == []


# ---------------------------------------------------------
# 5. Identifier Resolution (Synonyms, SMILES, Names)
# ---------------------------------------------------------

def test_resolve_drug_identifiers():
    assert resolve_drug_identifier("CHEMBL112") == "CHEMBL112"
    assert resolve_drug_identifier("chembl112") == "CHEMBL112"
    assert resolve_drug_identifier("Paracetamol") == "CHEMBL112"
    assert resolve_drug_identifier("Acetaminophen") == "CHEMBL112"
    assert resolve_drug_identifier("Aspirin") == "CHEMBL25"
    assert resolve_drug_identifier("CC(=O)Oc1ccccc1C(=O)O") == "CHEMBL25"
    assert resolve_drug_identifier("Ibuprofen") == "CHEMBL521"
    assert resolve_drug_identifier("Doxorubicin") == "CHEMBL53"
    assert resolve_drug_identifier("NON_EXISTENT_COMPOUND_XYZ") is None


# ---------------------------------------------------------
# 6. Demo Dataset Retrieval (Offline Mode)
# ---------------------------------------------------------

def test_curated_demo_dataset_loading():
    dataset = load_curated_demo_dataset()
    assert "CHEMBL112" in dataset
    assert "CHEMBL25" in dataset
    assert "CHEMBL521" in dataset
    assert "CHEMBL53" in dataset

    apap = dataset["CHEMBL112"]
    assert len(apap["evidence"]) >= 8

    # Verify real pharmacological associations
    sources = {e["source"] for e in apap["evidence"]}
    assert "PubChem" in sources
    assert "ChEMBL" in sources
    assert "UniProt" in sources
    assert "SIDER" in sources
    assert "PubMed" in sources


def test_ingest_drug_evidence_acetaminophen():
    result = fetch_drug_biomedical_data(drug_id="CHEMBL112")
    assert result["drug_id"] == "CHEMBL112"
    assert result["drug_name"] == "Acetaminophen"
    assert len(result["evidence"]) >= 8
    assert result["summary"]["target_count"] > 0
    assert result["summary"]["adverse_effect_count"] > 0
    assert result["summary"]["literature_count"] > 0

    # Check for SIDER Hepatotoxicity
    adverse = [e for e in result["evidence"] if e["entity_type"] == "adverse_effect"]
    assert any("Hepatotoxicity" in e["entity_name"] for e in adverse)

    # Check for CYP2E1 metabolic pathway
    cyp2e1 = [e for e in result["evidence"] if "P20813" in e["entity_id"]]
    assert len(cyp2e1) == 1
    assert cyp2e1[0]["relation"] == "metabolized_by"


def test_ingest_drug_evidence_doxorubicin_cardiotoxicity():
    result = fetch_drug_biomedical_data(drug_id="CHEMBL53")
    assert result["drug_id"] == "CHEMBL53"
    assert "Doxorubicin" in result["drug_name"]

    # Check for TOP2B target and Cardiotoxicity side effect
    targets = [e for e in result["evidence"] if "TOP2B" in e["entity_name"]]
    assert len(targets) >= 1

    side_effects = [e for e in result["evidence"] if e["entity_type"] == "adverse_effect"]
    assert any("Cardiomyopathy" in e["entity_name"] for e in side_effects)


# ---------------------------------------------------------
# 7. Local Caching
# ---------------------------------------------------------

def test_evidence_local_caching():
    # First call: fresh ingestion (cached=False)
    res1 = fetch_drug_biomedical_data(drug_id="CHEMBL25")
    assert res1["cached"] is False

    # Second call: retrieved from local SQLite cache (cached=True)
    res2 = fetch_drug_biomedical_data(drug_id="CHEMBL25")
    assert res2["cached"] is True
    assert res2["drug_id"] == "CHEMBL25"
    assert len(res2["evidence"]) == len(res1["evidence"])

    # Third call with force_refresh=True: bypasses cache
    res3 = fetch_drug_biomedical_data(drug_id="CHEMBL25", force_refresh=True)
    assert res3["cached"] is False


# ---------------------------------------------------------
# 8. Missing Data / Unknown Drug
# ---------------------------------------------------------

def test_unknown_drug_evidence():
    result = fetch_drug_biomedical_data(drug_id="CHEMBL999999999")
    assert result["drug_id"] == "CHEMBL999999999"
    assert result["evidence"] == []
    assert result["summary"]["total_evidence_count"] == 0
    assert result["status"]["valid"] is True
    assert "No biomedical evidence found" in result["status"]["message"]
