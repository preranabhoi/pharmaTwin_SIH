# PharmaTwin AI 🧬🫀

**Evidence-Aware Drug Risk Prediction Research Platform & Human Virtual Twin**

---

> ### ⚠️ Research Scope & Boundaries Disclaimer
> - **Research & Decision-Support Prototype**: PharmaTwin AI is designed exclusively for exploratory pharmacological research, multi-source evidence fusion, and computational modeling.
> - **NOT Clinical Diagnostics**: It is **not** a clinical diagnostic tool or medical device.
> - **NOT Treatment Recommendations**: It does **not** prescribe or recommend patient treatments.
> - **NOT a Replacement for Clinical Trials**: Computational representations and biomedical knowledge graphs do not substitute for preclinical or clinical safety trials.
> - **Human Virtual Twin Scope**: The Human Virtual Twin represents an **interactive 3D anatomical visualization of predicted organ-level risk probabilities and mechanistic evidence**, rather than a full physiological whole-body digital simulation.

---

## 🔬 System Pipeline Architecture

```
[Phase 1] Drug Input (SMILES / SDF / MOL / Drug ID)
   │
   ▼
[Phase 1] Molecular Normalization & Evidence Extraction (RDKit Descriptors & Morgan Fingerprints)
   │
   ▼
[Phase 2] Biomedical Data Ingestion (PubChem, ChEMBL, UniProt, OpenTargets, SIDER, PubMed)
   │
   ▼
[Phase 3] Biomedical Knowledge Graph (Compound-Target-Pathway-Phenotype Networks)
   │
   ▼
[Phase 4] Evidence Fusion & Risk Reasoning (Multi-Modal Contextual Reasoning)
   │
   ▼
[Phase 5] Multi-Target Risk Prediction (Organ Toxicity Probabilities & Confidence)
   │
   ▼
[Phase 6] Explainability & Attribution (Substructure Alerts, SHAP/Toxicophore Highlighting)
   │
   ▼
[Phase 7] Organ Risk Mapping (Aggregated Scores for Liver, Heart, Kidney, CNS, etc.)
   │
   ▼
[Phase 8] Human Virtual Twin (Interactive 3D Organ Risk Visualization)
```

---

## 📁 Repository Structure

```text
PharmaTwin/
├── backend/
│   ├── app/
│   │   ├── __init__.py               # Application package definition
│   │   ├── main.py                   # FastAPI application & route registration
│   │   ├── config.py                 # Centralized configuration & environment loader
│   │   ├── schemas.py                # Pydantic request/response data models
│   │   ├── molecular_processing.py   # RDKit validation, normalization, descriptors, fingerprints
│   │   ├── data_ingestion.py         # Multi-source biomedical adapters & normalization
│   │   ├── knowledge_graph.py        # Knowledge subgraph constructor (Phase 3 Foundation)
│   │   ├── evidence_fusion.py        # Multi-modal evidence fusion engine (Phase 4 Foundation)
│   │   ├── risk_prediction.py        # Toxicity & adverse risk predictor (Phase 5 Foundation)
│   │   ├── explainability.py         # Toxicophore attribution & explainability (Phase 6 Foundation)
│   │   ├── organ_mapping.py          # Organ-level risk aggregation (Phase 7 Foundation)
│   │   └── database.py               # SQLite local persistent caching engine
│   ├── data/
│   │   ├── raw/                      # Raw bioassay data & external data cache
│   │   ├── processed/                # Normalized features & pre-computed embeddings
│   │   └── demo/                     # Demo molecules & authentic biomedical evidence dataset
│   ├── models/                       # Model checkpoints & serialized weights
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # Pytest fixtures & FastAPI TestClient
│   │   ├── test_molecular_processing.py # Unit tests for cheminformatics logic
│   │   ├── test_data_ingestion.py    # Unit tests for multi-source adapters & normalization
│   │   └── test_api.py               # FastAPI integration and endpoint tests
│   └── requirements.txt              # Backend dependencies
│
├── frontend/                         # Interactive React/Vite dashboard & 3D viewport
│   └── README.md
│
├── docker/
│   ├── Dockerfile.backend            # Container definition for backend
│   ├── Dockerfile.frontend           # Container definition for frontend
│   └── docker-compose.yml            # Multi-container orchestration
│
├── .env.example                      # Template for environment variables
├── .gitignore                        # Git exclusion rules
└── README.md                         # Project documentation
```

---

## 🧪 Implemented Modules

### Phase 1: Drug Input + Molecular Evidence Layer
- **Input Formats**: SMILES strings, `.sdf` structure files, `.mol` connection tables, and optional Drug IDs/names.
- **Normalization**: Canonical SMILES, IUPAC InChI, InChIKey, Hill Molecular Formula, Atom counts.
- **Descriptors**: 9 physicochemical descriptors (Molecular Weight, LogP, TPSA, HBD, HBA, Rotatable Bonds, Heavy Atom Count, Ring Count, Aromatic Ring Count).
- **Fingerprints**: 2048-bit Morgan circular fingerprints ($\text{radius}=2$, $\text{ECFP4}$ equivalent).
- **2D Depictions**: Real-time vector SVG and binary PNG rendering.

### Phase 2: Biomedical Data Ingestion & Normalization Layer
- **Source Adapters**:
  - `PubChemAdapter`: Chemical properties, compound CIDs, IUPAC nomenclature.
  - `ChEMBLAdapter`: Bioactivity assays, binding affinities ($IC_{50}$), target mechanisms of action.
  - `UniProtAdapter`: Curated human protein details, gene symbols, and metabolic enzymes (e.g. CYP2E1, CYP3A4).
  - `OpenTargetsAdapter`: Disease-target associations and biological pathways.
  - `SIDERAdapter`: Clinical adverse drug reactions, MedDRA / UMLS concepts, and organ system mappings.
  - `PubMedAdapter`: Peer-reviewed scientific literature citations and mechanistic findings.
- **Entity Resolution & Deduplication**: Consolidates duplicate records across adapters, retains maximum confidence scores, and merges contextual metadata.
- **Provenance Tracking**: Every evidence record includes source database, retrieval timestamp (ISO 8601), version, and evidence type.
- **Local SQLite Caching**: Persistent local cache in `database.py` prevents redundant network calls.
- **Offline Demo Mode**: Authentic, non-fabricated curated benchmark dataset for known drugs (Acetaminophen `CHEMBL112`, Aspirin `CHEMBL25`, Ibuprofen `CHEMBL521`, Doxorubicin `CHEMBL53`).

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status & active phase metadata |
| `GET` | `/health` | System health check |
| `GET` | `/api/molecular/demo-drugs` | Pre-loaded benchmark molecules |
| `POST` | `/api/molecular/process` | Process SMILES into molecular evidence |
| `POST` | `/api/molecular/process-file` | Upload and process `.sdf` / `.mol` file |
| `GET` | `/api/molecular/render-image` | 2D structure depiction (PNG / SVG) |
| `POST` | `/api/molecular/render-image` | 2D structure depiction from JSON body |
| `POST` | `/api/evidence/drug/{drug_id}` | Ingest and normalize multi-source biomedical evidence |
| `GET` | `/api/evidence/drug/{drug_id}` | Retrieve biomedical evidence via GET query |

---

## 💻 Example API Calls & Responses

### 1. Ingest Multi-Source Biomedical Evidence (POST `/api/evidence/drug/{drug_id}`)

**Request**:
```bash
curl -X POST "http://localhost:8000/api/evidence/drug/CHEMBL112" \
     -H "Content-Type: application/json" \
     -d '{
       "force_refresh": false
     }'
```

**Standard Response**:
```json
{
  "drug_id": "CHEMBL112",
  "drug_name": "Acetaminophen",
  "canonical_smiles": "CC(=O)Nc1ccc(O)cc1",
  "cached": false,
  "demo_mode": true,
  "summary": {
    "total_evidence_count": 12,
    "sources_contacted": ["PubChem", "ChEMBL", "UniProt", "OpenTargets", "SIDER", "PubMed"],
    "sources_succeeded": ["PubChem", "ChEMBL", "UniProt", "OpenTargets", "SIDER", "PubMed"],
    "sources_failed": [],
    "entity_type_counts": {
      "drug": 1,
      "target": 2,
      "protein": 3,
      "pathway": 1,
      "adverse_effect": 3,
      "paper": 2
    },
    "target_count": 5,
    "adverse_effect_count": 3,
    "pathway_count": 1,
    "literature_count": 2
  },
  "evidence": [
    {
      "source": "ChEMBL",
      "entity_type": "target",
      "entity_id": "CHEMBL:CHEMBL221",
      "entity_name": "Prostaglandin G/H synthase 1 (PTGS1 / COX-1)",
      "relation": "inhibits",
      "object_id": "CHEMBL:CHEMBL112",
      "confidence": 0.85,
      "evidence_type": "bioassay",
      "retrieved_at": "2026-09-25T12:00:00Z",
      "source_version": "v33",
      "metadata": {
        "assay_type": "Binding",
        "ic50_um": 26.0,
        "organism": "Homo sapiens"
      }
    },
    {
      "source": "UniProt",
      "entity_type": "protein",
      "entity_id": "UNIPROT:P20813",
      "entity_name": "Cytochrome P450 2E1 (CYP2E1)",
      "relation": "metabolized_by",
      "object_id": "CHEMBL:CHEMBL112",
      "confidence": 0.95,
      "evidence_type": "metabolic_pathway",
      "retrieved_at": "2026-09-25T12:00:00Z",
      "source_version": "2026_01",
      "metadata": {
        "gene_symbol": "CYP2E1",
        "tissue_expression": "Liver (Hepatocytes)",
        "pathway_note": "Bioactivates acetaminophen into reactive N-acetyl-p-benzoquinone imine (NAPQI)"
      }
    },
    {
      "source": "SIDER",
      "entity_type": "adverse_effect",
      "entity_id": "SIDER:UMLS:C0019202",
      "entity_name": "Hepatotoxicity",
      "relation": "associated_with_adverse_effect",
      "object_id": "CHEMBL:CHEMBL112",
      "confidence": 0.96,
      "evidence_type": "clinical_side_effect",
      "retrieved_at": "2026-09-25T12:00:00Z",
      "source_version": "4.1",
      "metadata": {
        "meddra_id": "10019805",
        "target_organ": "Liver",
        "severity": "High / Critical"
      }
    },
    {
      "source": "PubMed",
      "entity_type": "paper",
      "entity_id": "PMID:15214041",
      "entity_name": "Acetaminophen-induced hepatotoxicity: molecular mechanisms and clinical implications",
      "relation": "reported_in_literature",
      "object_id": "CHEMBL:CHEMBL112",
      "confidence": 0.95,
      "evidence_type": "peer_reviewed_literature",
      "retrieved_at": "2026-09-25T12:00:00Z",
      "source_version": "2004",
      "metadata": {
        "journal": "Journal of Hepatology",
        "year": 2004,
        "key_finding": "NAPQI covalent binding to mitochondrial proteins drives hepatocyte oxidative stress and necrosis."
      }
    }
  ],
  "status": {
    "valid": true,
    "message": "Successfully ingested 12 biomedical evidence records."
  }
}
```

---

## 🚀 Running & Testing

### 1. Setup Backend Environment
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
# Run all 41 unit and API integration tests
pytest tests/ -v
```

### 3. Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
