from io import BytesIO
from pathlib import Path


# ---------------------------------------------------------
# 1. Health & Root Endpoints
# ---------------------------------------------------------

def test_api_root(client):
    """Test GET / returns healthy status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "PharmaTwin AI API is running" in data["message"]
    assert data["status"] == "healthy"


def test_api_health(client):
    """Test GET /health returns structured metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "PharmaTwin AI"
    assert "version" in data


def test_api_demo_drugs(client):
    """Test GET /api/molecular/demo-drugs returns list of benchmark drugs."""
    response = client.get("/api/molecular/demo-drugs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert any(d["name"].startswith("Acetaminophen") for d in data)


# ---------------------------------------------------------
# 2. SMILES Processing Endpoint
# ---------------------------------------------------------

def test_api_process_smiles_valid(client):
    """Test POST /api/molecular/process with Acetaminophen."""
    payload = {
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "drug_id": "CHEMBL112",
        "name": "Acetaminophen",
    }
    response = client.post("/api/molecular/process", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Nested Standard Evidence Response
    assert data["drug"]["drug_id"] == "CHEMBL112"
    assert data["drug"]["name"] == "Acetaminophen"
    assert data["drug"]["input_type"] == "smiles"

    assert data["molecule"]["canonical_smiles"] == "CC(=O)Nc1ccc(O)cc1"
    assert data["molecule"]["inchi"].startswith("InChI=1S/C8H9NO2/")
    assert data["molecule"]["inchi_key"] == "RZVAJINKPMORJF-UHFFFAOYSA-N"
    assert data["molecule"]["formula"] == "C8H9NO2"

    assert data["descriptors"]["molecular_weight"] == 151.165
    assert data["descriptors"]["hbd"] == 2
    assert data["descriptors"]["hba"] == 2
    assert data["descriptors"]["rotatable_bonds"] == 1
    assert data["descriptors"]["ring_count"] == 1

    assert data["fingerprint"]["type"] == "Morgan"
    assert data["fingerprint"]["size"] == 2048
    assert len(data["fingerprint"]["bits"]) == 2048
    assert data["fingerprint"]["active_bits"] > 0

    assert data["status"]["valid"] is True


def test_api_process_smiles_invalid(client):
    """Test POST /api/molecular/process with invalid SMILES returns 400."""
    response = client.post(
        "/api/molecular/process",
        json={"smiles": "INVALID_NOT_A_SMILES_STRING"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid SMILES" in data["detail"]


def test_api_process_smiles_empty(client):
    """Test POST /api/molecular/process with empty string returns 422 or 400."""
    response = client.post(
        "/api/molecular/process",
        json={"smiles": ""},
    )
    assert response.status_code in (400, 422)


# ---------------------------------------------------------
# 3. File Processing Endpoints (SDF & MOL)
# ---------------------------------------------------------

def test_api_process_sdf_file_upload(client):
    """Test POST /api/molecular/process-file with Aspirin SDF file."""
    sdf_path = Path(__file__).resolve().parent.parent / "data" / "demo" / "aspirin.sdf"
    if sdf_path.exists():
        with open(sdf_path, "rb") as f:
            file_bytes = f.read()

        response = client.post(
            "/api/molecular/process-file",
            files={"file": ("aspirin.sdf", BytesIO(file_bytes), "chemical/x-mdl-sdfile")},
            data={"drug_id": "CHEMBL25", "name": "Aspirin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["drug"]["drug_id"] == "CHEMBL25"
        assert data["filename"] == "aspirin.sdf"
        assert data["molecule"]["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
        assert data["descriptors"]["molecular_weight"] > 170


def test_api_process_mol_file_upload(client):
    """Test POST /api/molecular/process-file with Ibuprofen MOL file."""
    mol_path = Path(__file__).resolve().parent.parent / "data" / "demo" / "ibuprofen.mol"
    if mol_path.exists():
        with open(mol_path, "rb") as f:
            file_bytes = f.read()

        response = client.post(
            "/api/molecular/process-file",
            files={"file": ("ibuprofen.mol", BytesIO(file_bytes), "chemical/x-mdl-molfile")},
            data={"drug_id": "CHEMBL521", "name": "Ibuprofen"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["drug"]["drug_id"] == "CHEMBL521"
        assert data["filename"] == "ibuprofen.mol"
        assert data["descriptors"]["molecular_weight"] > 200


def test_api_process_file_invalid_extension(client):
    """Test POST /api/molecular/process-file with invalid extension returns 400."""
    response = client.post(
        "/api/molecular/process-file",
        files={"file": ("test.txt", BytesIO(b"fake data"), "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_api_process_file_empty(client):
    """Test POST /api/molecular/process-file with empty file returns 400."""
    response = client.post(
        "/api/molecular/process-file",
        files={"file": ("empty.sdf", BytesIO(b""), "chemical/x-mdl-sdfile")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


# ---------------------------------------------------------
# 4. 2D Molecular Image Rendering Endpoints
# ---------------------------------------------------------

def test_api_render_image_png_get(client):
    """Test GET /api/molecular/render-image with PNG format."""
    response = client.get("/api/molecular/render-image", params={"smiles": "CCO", "format": "png"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:4] == b"\x89PNG"


def test_api_render_image_svg_get(client):
    """Test GET /api/molecular/render-image with SVG format."""
    response = client.get("/api/molecular/render-image", params={"smiles": "CCO", "format": "svg"})
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    text = response.text
    assert "<svg" in text
    assert "</svg>" in text


def test_api_render_image_post(client):
    """Test POST /api/molecular/render-image returns PNG image."""
    response = client.post(
        "/api/molecular/render-image",
        json={"smiles": "CC(=O)NC1=CC=C(O)C=C1"},
        params={"format": "png"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:4] == b"\x89PNG"


def test_api_render_image_invalid_smiles(client):
    """Test GET /api/molecular/render-image with malformed SMILES returns 400."""
    response = client.get("/api/molecular/render-image", params={"smiles": "INVALID_SMILES_123"})
    assert response.status_code == 400
    assert "Invalid SMILES" in response.json()["detail"]


# ---------------------------------------------------------
# 5. Phase 2: Biomedical Evidence Ingestion Endpoints
# ---------------------------------------------------------

def test_api_ingest_evidence_post_chembl112(client):
    """Test POST /api/evidence/drug/CHEMBL112 returns normalized evidence."""
    response = client.post(
        "/api/evidence/drug/CHEMBL112",
        json={"force_refresh": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["drug_id"] == "CHEMBL112"
    assert data["drug_name"] == "Acetaminophen"
    assert len(data["evidence"]) >= 8
    assert data["summary"]["total_evidence_count"] >= 8
    assert data["status"]["valid"] is True

    # Verify provenance on records
    for ev in data["evidence"]:
        assert ev["source"] in ("PubChem", "ChEMBL", "UniProt", "OpenTargets", "SIDER", "PubMed")
        assert "retrieved_at" in ev
        assert "entity_type" in ev


def test_api_ingest_evidence_post_by_name(client):
    """Test POST /api/evidence/drug/aspirin resolves common name."""
    response = client.post(
        "/api/evidence/drug/aspirin",
        json={"force_refresh": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["drug_id"] == "CHEMBL25"
    assert data["drug_name"] == "Aspirin"
    assert data["summary"]["adverse_effect_count"] > 0


def test_api_ingest_evidence_get_chembl53(client):
    """Test GET /api/evidence/drug/CHEMBL53 (Doxorubicin cardiotoxicity evidence)."""
    response = client.get("/api/evidence/drug/CHEMBL53")
    assert response.status_code == 200
    data = response.json()
    assert data["drug_id"] == "CHEMBL53"
    assert "Doxorubicin" in data["drug_name"]
    assert any(e["entity_type"] == "adverse_effect" for e in data["evidence"])


def test_api_ingest_evidence_unknown_drug(client):
    """Test POST /api/evidence/drug/CHEMBL999999 returns empty evidence with informative message."""
    response = client.post("/api/evidence/drug/CHEMBL999999")
    assert response.status_code == 200
    data = response.json()
    assert data["drug_id"] == "CHEMBL999999"
    assert data["evidence"] == []
    assert data["summary"]["total_evidence_count"] == 0


# ---------------------------------------------------------
# 6. Phase 3: Biomedical Knowledge Graph Endpoints
# ---------------------------------------------------------

def test_api_graph_drug_subgraph_chembl112(client):
    """Test GET /api/graph/drug/CHEMBL112 returns complete subgraph with paths."""
    response = client.get("/api/graph/drug/CHEMBL112")
    assert response.status_code == 200
    data = response.json()

    assert data["drug_id"] == "CHEMBL:CHEMBL112"
    assert data["drug_name"] == "Acetaminophen"
    assert data["total_nodes"] >= 8
    assert data["total_edges"] >= 8
    assert len(data["nodes"]) == data["total_nodes"]
    assert len(data["edges"]) == data["total_edges"]
    assert len(data["paths"]) >= 2
    assert data["status"]["valid"] is True

    # Check node schema
    first_node = data["nodes"][0]
    assert "id" in first_node
    assert "name" in first_node
    assert "type" in first_node

    # Check edge schema & provenance
    first_edge = data["edges"][0]
    assert "source" in first_edge
    assert "target" in first_edge
    assert "relation" in first_edge
    assert "confidence" in first_edge
    assert "source_db" in first_edge


def test_api_graph_drug_subgraph_by_name_aspirin(client):
    """Test GET /api/graph/drug/aspirin resolves drug name to subgraph."""
    response = client.get("/api/graph/drug/aspirin")
    assert response.status_code == 200
    data = response.json()
    assert data["drug_id"] == "CHEMBL:CHEMBL25"
    assert data["drug_name"] == "Aspirin"
    assert data["total_nodes"] >= 5


def test_api_graph_drug_paths_chembl53(client):
    """Test GET /api/graph/drug/CHEMBL53/paths returns mechanistic paths to Heart."""
    response = client.get("/api/graph/drug/CHEMBL53/paths")
    assert response.status_code == 200
    data = response.json()
    assert data["total_paths"] >= 2
    assert len(data["paths"]) == data["total_paths"]
    assert any(p["target_organ"] == "Heart" for p in data["paths"])


def test_api_graph_search(client):
    """Test GET /api/graph/search queries nodes across the graph."""
    response = client.get("/api/graph/search", params={"query": "Liver"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] >= 1
    assert any(item["name"] == "Liver" for item in data["results"])


def test_api_graph_drug_unknown(client):
    """Test GET /api/graph/drug/UNKNOWN_DRUG returns empty graph structure."""
    response = client.get("/api/graph/drug/UNKNOWN_DRUG")
    assert response.status_code == 200
    data = response.json()
    assert data["total_nodes"] == 0
    assert data["total_edges"] == 0
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["paths"] == []


# ---------------------------------------------------------
# PHASE 4: RISK PREDICTION API TESTS
# ---------------------------------------------------------

def test_api_risk_predict_demo_acetaminophen(client):
    """Test POST /api/risk/predict for Acetaminophen returns complete multi-organ assessment."""
    payload = {
        "drug_id": "CHEMBL112",
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "name": "Acetaminophen",
        "model_type": "random_forest",
    }
    response = client.post("/api/risk/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["prediction_id"] is not None
    assert data["drug_id"] == "CHEMBL112"
    assert "overall_risk" in data
    assert 0.0 <= data["overall_risk"] <= 1.0
    assert data["overall_risk_category"] in ("Low", "Moderate", "High")
    assert 0.0 <= data["confidence"] <= 1.0
    assert 0.0 <= data["evidence_strength"] <= 1.0

    # Organ level risks
    organs = data["organ_risks"]
    for organ in ("heart", "liver", "kidney", "lung", "brain"):
        assert organ in organs
        assert 0.0 <= organs[organ]["risk_score"] <= 1.0
        assert organs[organ]["risk_category"] in ("Low", "Moderate", "High")

    # Sufficiency & Explainability
    assert data["evidence_sufficiency"]["is_sufficient"] is True
    assert data["evidence_sufficiency"]["flag_for_review"] is False
    assert len(data["explainability"]["contributing_features"]) > 0
    assert len(data["explainability"]["graph_paths"]) > 0
    assert len(data["explainability"]["similarity_matches"]) > 0
    assert "research-grade" in data["disclaimer"].lower()


def test_api_risk_get_by_id(client):
    """Test GET /api/risk/{prediction_id} retrieves audited prediction."""
    payload = {
        "drug_id": "CHEMBL25",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "name": "Aspirin",
        "model_type": "ensemble",
    }
    post_res = client.post("/api/risk/predict", json=payload)
    assert post_res.status_code == 200
    pred_id = post_res.json()["prediction_id"]

    get_res = client.get(f"/api/risk/{pred_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["prediction_id"] == pred_id
    assert data["drug_id"] == "CHEMBL25"
    assert data["model_used"] == "ensemble"


def test_api_risk_get_by_id_not_found(client):
    """Test GET /api/risk/{prediction_id} returns 404 for nonexistent UUID."""
    response = client.get("/api/risk/non-existent-uuid-99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_risk_predict_empty_payload(client):
    """Test POST /api/risk/predict returns 400 when no identifier is provided."""
    response = client.post("/api/risk/predict", json={})
    assert response.status_code == 400
    assert "at least one drug identifier" in response.json()["detail"].lower()


def test_api_risk_predict_unseen_compound_sufficiency_flag(client):
    """Test POST /api/risk/predict correctly flags sparse novel compound for review."""
    payload = {
        "smiles": "CCCCCCCCCC(=O)O",
        "name": "DecanoicAcidDerivative",
    }
    response = client.post("/api/risk/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["evidence_sufficiency"]["is_sufficient"] is False
    assert data["evidence_sufficiency"]["flag_for_review"] is True
    assert len(data["evidence_sufficiency"]["review_reasons"]) > 0
    assert data["confidence"] <= 0.55


# ---------------------------------------------------------
# PHASE 5: EXPLAINABILITY & TRACEABILITY API TESTS
# ---------------------------------------------------------

def test_api_explain_prediction_acetaminophen(client):
    """Test GET /api/explanations/{prediction_id} returns UI-ready SHAP explanation & evidence linkages."""
    payload = {
        "drug_id": "CHEMBL112",
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "name": "Acetaminophen",
        "model_type": "random_forest",
    }
    post_res = client.post("/api/risk/predict", json=payload)
    assert post_res.status_code == 200
    pred_id = post_res.json()["prediction_id"]

    exp_res = client.get(f"/api/explanations/{pred_id}")
    assert exp_res.status_code == 200
    data = exp_res.json()

    assert data["prediction_id"] == pred_id
    assert data["drug_id"] == "CHEMBL112"
    assert data["drug_name"] == "Acetaminophen"
    assert len(data["top_features"]) == 8
    assert len(data["all_feature_contributions"]) == 32
    assert len(data["supporting_paths"]) > 0
    assert len(data["supporting_evidence"]) > 0
    assert len(data["supporting_literature"]) > 0
    assert len(data["similarity_matches"]) > 0

    # Validate causality distinction
    assert "statistical" in data["causality_distinction"].lower()
    assert "not constitute proven biological causality" in data["causality_distinction"].lower()

    # Validate quality metadata
    assert data["quality_metadata"]["evidence_count"] > 0
    assert len(data["quality_metadata"]["evidence_source_diversity"]) > 0


def test_api_explain_prediction_not_found(client):
    """Test GET /api/explanations/{prediction_id} returns 404 for unknown prediction UUID."""
    response = client.get("/api/explanations/unknown-pred-uuid-00000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------
# PHASE 6: ORGAN RISK MAPPING API TESTS
# ---------------------------------------------------------

def test_api_organ_risk_acetaminophen(client):
    """Test GET /api/organ-risk/{prediction_id} returns structured multi-organ risk profiles."""
    payload = {
        "drug_id": "CHEMBL112",
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "name": "Acetaminophen",
        "model_type": "random_forest",
    }
    post_res = client.post("/api/risk/predict", json=payload)
    assert post_res.status_code == 200
    pred_id = post_res.json()["prediction_id"]

    organ_res = client.get(f"/api/organ-risk/{pred_id}")
    assert organ_res.status_code == 200
    data = organ_res.json()

    assert data["prediction_id"] == pred_id
    assert data["drug_id"] == "CHEMBL112"
    assert data["highest_risk_organ"] == "liver"

    # Check 8 physiological systems exist
    expected_organs = {"brain", "heart", "liver", "kidney", "lung", "gastrointestinal", "blood", "skin"}
    assert expected_organs.issubset(set(data["organs"].keys()))

    liver = data["organs"]["liver"]
    assert liver["name"] == "Liver"
    assert liver["category"] == "High"
    assert liver["evidence_strength"] in ("Medium", "High")
    assert len(liver["primary_mechanisms"]) > 0

    assert "not a clinical diagnosis" in data["disclaimer"].lower()


def test_api_organ_risk_not_found(client):
    """Test GET /api/organ-risk/{prediction_id} returns 404 for unknown prediction UUID."""
    response = client.get("/api/organ-risk/unknown-pred-uuid-99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()



