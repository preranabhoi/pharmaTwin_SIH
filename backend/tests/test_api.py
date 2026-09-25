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
