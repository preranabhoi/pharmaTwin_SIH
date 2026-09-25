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

### Phase 4: Evidence Fusion & Risk Reasoning Engine (Primary Research Module)
- **Standardized Multi-Modal Alignment**: Standardizes heterogeneous evidence into a fixed 32-dimensional numerical feature representation across molecular descriptors, knowledge graph paths, SIDER clinical adverse reports, literature citations, and Tanimoto similarity metrics.
- **Transparent Confidence & Evidence Weighting**:
  - Strictly separates **Model Prediction** ($\hat{y} \in [0, 1]$), **Confidence** ($C \in [0, 1]$), and **Evidence Strength** ($S \in [0, 1]$) to avoid misleading single "medical certainty" metrics.
  - Evidence strength formula: $S = 0.20 \cdot S_{\text{mol}} + 0.30 \cdot S_{\text{graph}} + 0.30 \cdot S_{\text{hist}} + 0.20 \cdot S_{\text{lit}}$.
- **Molecular Similarity Retrieval**:
  - Tanimoto coefficient calculation over Morgan fingerprints against benchmark drugs.
  - Explicit scientific disclaimer: *Molecular similarity informs prior evidence retrieval, but does not prove clinical toxicity.*
- **Pluggable Risk Model Abstraction (`BaseRiskModel`)**:
  - Implementations: `RandomForestRiskModel` (decision tree ensemble), `LogisticRegressionRiskModel` (L2-regularized), and `EnsembleRiskModel` (consensus predictor).
  - Deterministic training, serialization (`save`/`load`), and feature importances.
- **Evaluation & Validation Pipeline**:
  - Metrics: Accuracy, Precision, Recall, F1, ROC-AUC (NumPy 2.x trapezoid rank integration), and Confusion Matrix.
  - Reproducible splitting: `train_test_split` (fixed random state) and `temporal_split` (historical vs prospective chronological evaluation).
- **Evidence Sufficiency Gate**:
  - Multi-criteria gate evaluating structural validity, target assays, graph paths, and literature citations.
  - Sufficient evidence $\rightarrow$ standard prediction.
  - Insufficient/sparse evidence $\rightarrow$ prediction flagged for manual review (`flag_for_review = True`, explicit review reasons, and confidence dampened to $\le 0.55$).
- **Multi-Organ Toxicity Decomposition**:
  - Evaluates individual organ systems: **Heart**, **Liver**, **Kidney**, **Lung**, and **Brain** along with **Overall Adverse Risk**.
  - Prototype Risk Categories: `Low` ($< 0.35$), `Moderate` ($0.35 - 0.69$), `High` ($\ge 0.70$).
  - Mandatory disclaimer: Categories are research prototype thresholds, not clinically validated diagnostic conclusions.
- **Traceable Explainability & Persistence**:
  - Attributions for top contributing features, supporting evidence records, knowledge graph paths, literature citations, and similarity matches.
  - Persisted to local SQLite audit log (`risk_predictions` table).

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
| `POST` | `/api/risk/predict` | **Phase 4**: Multi-modal evidence fusion and organ risk prediction |
| `GET` | `/api/risk/{prediction_id}` | **Phase 4**: Retrieve audited risk prediction report by UUID |

---

## 💻 Example API Calls & Responses

### 1. Multi-Organ Risk Prediction (POST `/api/risk/predict`)

**Request**:
```bash
curl -X POST "http://localhost:8000/api/risk/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "drug_id": "CHEMBL112",
    "smiles": "CC(=O)NC1=CC=C(O)C=C1",
    "name": "Acetaminophen",
    "model_type": "random_forest"
  }'
```

**Response**:
```json
{
  "prediction_id": "dc6ece59-05c6-4aca-9f92-9a227d879b85",
  "drug_id": "CHEMBL112",
  "drug_name": "Acetaminophen",
  "canonical_smiles": "CC(=O)Nc1ccc(O)cc1",
  "model_used": "random_forest",
  "overall_risk": 0.8282,
  "overall_risk_category": "High",
  "confidence": 0.9313,
  "evidence_strength": 1.0,
  "organ_risks": {
    "heart": {
      "organ": "heart",
      "organ_name": "Heart (Cardiovascular System)",
      "risk_score": 0.3201,
      "risk_category": "Low",
      "confidence": 0.8720,
      "evidence_strength": 1.0,
      "primary_mechanisms": ["No specific high-affinity heart liability detected"],
      "graph_paths_count": 0,
      "adverse_effects_count": 0,
      "literature_citations_count": 1
    },
    "liver": {
      "organ": "liver",
      "organ_name": "Liver (Hepatic System)",
      "risk_score": 0.7559,
      "risk_category": "High",
      "confidence": 0.9024,
      "evidence_strength": 1.0,
      "primary_mechanisms": [
        "Acetaminophen [ASSOCIATED_WITH_ADVERSE_EFFECT] -> Hepatotoxicity [AFFECTS_ORGAN] -> Liver",
        "Acetaminophen [ASSOCIATED_WITH_ADVERSE_EFFECT] -> Acute Hepatic Failure [AFFECTS_ORGAN] -> Liver",
        "Reported Reaction: Hepatotoxicity",
        "Reported Reaction: Acute Hepatic Failure"
      ],
      "graph_paths_count": 2,
      "adverse_effects_count": 2,
      "literature_citations_count": 1
    },
    "kidney": {
      "organ": "kidney",
      "organ_name": "Kidney (Renal System)",
      "risk_score": 0.4512,
      "risk_category": "Moderate",
      "confidence": 0.8195,
      "evidence_strength": 1.0,
      "primary_mechanisms": ["Secondary metabolic clearance strain"],
      "graph_paths_count": 0,
      "adverse_effects_count": 0,
      "literature_citations_count": 1
    },
    "lung": {
      "organ": "lung",
      "organ_name": "Lung (Respiratory System)",
      "risk_score": 0.1245,
      "risk_category": "Low",
      "confidence": 0.9500,
      "evidence_strength": 1.0,
      "primary_mechanisms": ["No specific high-affinity lung liability detected"],
      "graph_paths_count": 0,
      "adverse_effects_count": 0,
      "literature_citations_count": 1
    },
    "brain": {
      "organ": "brain",
      "organ_name": "Brain (Central Nervous System)",
      "risk_score": 0.1873,
      "risk_category": "Low",
      "confidence": 0.9251,
      "evidence_strength": 1.0,
      "primary_mechanisms": ["No specific high-affinity brain liability detected"],
      "graph_paths_count": 0,
      "adverse_effects_count": 0,
      "literature_citations_count": 1
    }
  },
  "evidence_sufficiency": {
    "is_sufficient": true,
    "flag_for_review": false,
    "review_reasons": [],
    "criteria_met": {
      "valid_structure": true,
      "complete_descriptors": true,
      "biological_evidence_present": true,
      "knowledge_graph_paths_present": true,
      "literature_citations_present": true
    }
  },
  "explainability": {
    "contributing_features": [
      {"feature_index": 11, "feature_name": "kg_paths_liver", "feature_value": 0.4, "importance_weight": 0.185},
      {"feature_index": 21, "feature_name": "adverse_liver_count", "feature_value": 0.5, "importance_weight": 0.162},
      {"feature_index": 1, "feature_name": "logp_norm", "feature_value": 0.391, "importance_weight": 0.114}
    ],
    "similarity_matches": [
      {
        "reference_drug_id": "CHEMBL112",
        "reference_drug_name": "Acetaminophen",
        "tanimoto_similarity": 1.0,
        "known_organ_risks": ["Liver (Hepatotoxicity / NAPQI necrosis)", "Kidney (Tubular strain)"],
        "disclaimer": "Molecular similarity informs prior evidence retrieval, but does not prove clinical toxicity."
      }
    ]
  },
  "disclaimer": "Research-grade decision-support prototype. Categories ('Low', 'Moderate', 'High') are research prototype thresholds and must be validated on appropriate preclinical and clinical datasets. Not a clinical diagnostic or treatment recommendation system.",
  "status": {
    "valid": true,
    "message": "Evidence fusion and multi-organ risk reasoning completed successfully."
  },
  "created_at": "2026-09-25T21:43:16.000000+00:00"
}
```

### 2. Retrieve Audited Risk Report (GET `/api/risk/{prediction_id}`)

```bash
curl "http://localhost:8000/api/risk/dc6ece59-05c6-4aca-9f92-9a227d879b85"
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
# Run all 84 unit and API integration tests
pytest tests/ -v
```

### 3. Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

