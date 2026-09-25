# PharmaTwin AI 🧬🫀

**Evidence-Aware Drug Risk Prediction Research Platform & Human Virtual Twin**

---

> ### ⚠️ Research Scope & Boundaries Disclaimer
> - **Research & Decision-Support Prototype**: PharmaTwin AI is designed exclusively for exploratory pharmacological research, multi-source evidence fusion, and computational modeling.
> - **Knowledge Graph Role**: The knowledge graph structures published biomedical facts and bioassays into an explicit heterogeneous network. **The platform does not claim the underlying biological data itself is novel; rather, the research contribution is how this graph is integrated into evidence-aware multi-modal risk reasoning.**
> - **NOT Clinical Diagnostics**: It is **not** a clinical diagnostic tool or medical device.
> - **NOT Treatment Recommendations**: It does **not** prescribe or recommend patient treatments.
> - **NOT a Replacement for Clinical Trials**: Computational representations and knowledge graphs do not substitute for preclinical or clinical safety trials.
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
│   │   ├── knowledge_graph.py        # Graph engine, multi-hop reasoning, ontology & exporter
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
│   │   ├── test_knowledge_graph.py   # Unit tests for knowledge graph & path reasoning
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
- **Source Adapters**: PubChem, ChEMBL, UniProt, OpenTargets, SIDER, PubMed.
- **Entity Resolution & Deduplication**: Merges duplicate entities, retains maximum confidence, and consolidates metadata.
- **Provenance Tracking**: Every evidence record includes source database, retrieval timestamp (ISO 8601), version, and evidence type.
- **Local SQLite Caching**: Persistent local cache in `database.py` prevents redundant network calls.
- **Offline Demo Mode**: Authentic, non-fabricated curated benchmark dataset for known drugs (Acetaminophen, Aspirin, Ibuprofen, Doxorubicin).

### Phase 3: Biomedical Knowledge Graph & Path Reasoning Layer
- **Graph Ontology**:
  - **Node Types**: `Drug`, `Target`, `Protein`, `Gene`, `Pathway`, `Tissue`, `Organ`, `AdverseEffect`, `Disease`, `Literature`.
  - **Relationship Types**: `TARGETS`, `INHIBITS`, `ACTIVATES`, `BINDS_TO`, `ENCODED_BY`, `METABOLIZED_BY`, `PARTICIPATES_IN_PATHWAY`, `ACTIVE_IN_TISSUE`, `PART_OF_ORGAN`, `AFFECTS_ORGAN`, `ASSOCIATED_WITH_ADVERSE_EFFECT`, `SUPPORTS_RELATIONSHIP`.
- **In-Memory & Neo4j Compatible Engine**: Pure-Python high-performance directed graph engine with adjacency indices, DFS multi-hop traversal, and Neo4j fallback interface.
- **Multi-Hop Mechanistic Path Reasoning**:
  - `Drug -> Target/Protein -> Gene -> Pathway -> Tissue -> Organ`
  - `Drug -> AdverseEffect -> Organ`
- **Transparent Evidence Weighting**: Path confidence is computed as the product of edge confidences $\prod c_i$ with provenance traceability for every transition.
- **Frontend-Ready Visualization Format**: Serializes subgraphs into node and edge collections compatible with Cytoscape.js, React Force Graph, and D3.

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
| `GET` | `/api/graph/drug/{drug_id}` | Retrieve frontend-ready biomedical knowledge subgraph |
| `GET` | `/api/graph/drug/{drug_id}/paths` | Extract multi-hop mechanistic reasoning paths to organs |
| `GET` | `/api/graph/search` | Search graph entities by keyword and entity type |

---

## 💻 Example API Calls & Responses

### 1. Retrieve Knowledge Subgraph (GET `/api/graph/drug/{drug_id}`)

**Request**:
```bash
curl "http://localhost:8000/api/graph/drug/CHEMBL112?depth=3&max_nodes=100"
```

**Response**:
```json
{
  "drug_id": "CHEMBL:CHEMBL112",
  "drug_name": "Acetaminophen",
  "canonical_smiles": "CC(=O)Nc1ccc(O)cc1",
  "engine": "InMemoryGraph",
  "total_nodes": 12,
  "total_edges": 14,
  "nodes": [
    {
      "id": "CHEMBL:CHEMBL112",
      "name": "Acetaminophen",
      "type": "Drug",
      "properties": {"formula": "C8H9NO2"}
    },
    {
      "id": "UNIPROT:P20813",
      "name": "Cytochrome P450 2E1 (CYP2E1)",
      "type": "Protein",
      "properties": {"gene": "CYP2E1"}
    },
    {
      "id": "PATHWAY:NAPQI_HEPATOTOX",
      "name": "NAPQI Bioactivation & Glutathione Depletion",
      "type": "Pathway",
      "properties": {"reactome_id": "REACT_71"}
    },
    {
      "id": "TISSUE:HEPATOCYTES",
      "name": "Hepatocytes",
      "type": "Tissue",
      "properties": {"organ": "Liver"}
    },
    {
      "id": "ORGAN:LIVER",
      "name": "Liver",
      "type": "Organ",
      "properties": {"system": "Hepatic"}
    }
  ],
  "edges": [
    {
      "id": "CHEMBL:CHEMBL112->METABOLIZED_BY->UNIPROT:P20813",
      "source": "CHEMBL:CHEMBL112",
      "target": "UNIPROT:P20813",
      "relation": "METABOLIZED_BY",
      "confidence": 0.95,
      "source_db": "UniProt",
      "evidence_type": "metabolic_pathway",
      "provenance_id": "UNIPROT_P20813"
    },
    {
      "id": "PATHWAY:NAPQI_HEPATOTOX->ACTIVE_IN_TISSUE->TISSUE:HEPATOCYTES",
      "source": "PATHWAY:NAPQI_HEPATOTOX",
      "target": "TISSUE:HEPATOCYTES",
      "relation": "ACTIVE_IN_TISSUE",
      "confidence": 0.96,
      "source_db": "UniProt",
      "evidence_type": "tissue_expression"
    }
  ],
  "paths": [
    {
      "path_id": "path_CHEMBL:CHEMBL112_ORGAN:LIVER_1",
      "path_type": "mechanistic_organ_path",
      "target_organ": "Liver",
      "nodes": ["CHEMBL:CHEMBL112", "UNIPROT:P20813", "GENE:CYP2E1", "PATHWAY:NAPQI_HEPATOTOX", "TISSUE:HEPATOCYTES", "ORGAN:LIVER"],
      "node_names": ["Acetaminophen", "Cytochrome P450 2E1 (CYP2E1)", "CYP2E1", "NAPQI Bioactivation & Glutathione Depletion", "Hepatocytes", "Liver"],
      "relations": ["METABOLIZED_BY", "ENCODED_BY", "PARTICIPATES_IN_PATHWAY", "ACTIVE_IN_TISSUE", "PART_OF_ORGAN"],
      "confidence": 0.8482,
      "confidence_tier": "high",
      "description": "Acetaminophen [METABOLIZED_BY] -> Cytochrome P450 2E1 (CYP2E1) [ENCODED_BY] -> CYP2E1 [PARTICIPATES_IN_PATHWAY] -> NAPQI Bioactivation & Glutathione Depletion [ACTIVE_IN_TISSUE] -> Hepatocytes [PART_OF_ORGAN] -> Liver"
    }
  ],
  "evidence_sources": ["ChEMBL", "UniProt", "SIDER", "PubMed", "OpenTargets"],
  "status": {
    "valid": true,
    "message": "Extracted subgraph with 12 nodes, 14 edges, and 3 reasoning paths."
  }
}
```

### 2. Extract Mechanistic Reasoning Paths (GET `/api/graph/drug/{drug_id}/paths`)

```bash
curl "http://localhost:8000/api/graph/drug/CHEMBL53/paths?target_organ=Heart"
```

### 3. Search Knowledge Graph Entities (GET `/api/graph/search`)

```bash
curl "http://localhost:8000/api/graph/search?query=Liver&entity_type=Organ"
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
# Run all 59 unit and API integration tests
pytest tests/ -v
```

### 3. Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
