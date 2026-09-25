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
### Phase 5: Explainability & Evidence Traceability Engine
- **Core Objective**: Answers the researcher's key question: *"WHY DID PHARMATWIN PREDICT THIS RISK?"*
- **Primary Method — SHAP (Shapley Additive Explanations)**:
  - Local feature attribution engine based on marginal Shapley contributions:
    $$\sum_{i=1}^{M} \phi_i = f(x) - E[f(X_{\text{bg}})]$$
  - Provides for each feature: `feature_name`, `feature_value`, `contribution` ($\phi_i$), `direction` (`increases_risk` / `decreases_risk`), `rank`, and human-readable domain explanation.
- **Traceable Multi-Source Evidence Linkage**:
  - **Molecular Evidence**: Structural physicochemical parameters & Morgan fingerprint descriptors.
  - **Knowledge Graph Paths**: Multi-hop mechanistic routes:
    $$\text{Drug} \rightarrow \text{Target} \rightarrow \text{Gene} \rightarrow \text{Pathway} \rightarrow \text{Tissue} \rightarrow \text{Organ}$$
  - **Historical Clinical Evidence**: SIDER adverse drug reactions mapped by organ system.
  - **Peer-Reviewed Literature**: PubMed indexed articles with PMIDs, titles, journals, publication years, and source confidence.
  - **Similarity Matches**: Nearest benchmark toxicological reference matches with scientific disclaimer.
- **Quality & Provenance Metadata**:
  - `evidence_count`: Total supporting items.
  - `evidence_source_diversity`: Distinct upstream databases contributing evidence (`ChEMBL`, `UniProt`, `OpenTargets`, `SIDER`, `PubMed`, etc.).
  - `base_value`: Background expected value $E[f(x)]$.
  - `confidence` & `evidence_sufficiency`: Evidence gating status.
- **Preventing Misleading Explanations**:
  - Explicitly distinguishes:
    $$\text{“feature contributed to statistical model prediction (SHAP)”} \quad \neq \quad \text{“biological mechanism caused clinical toxicity”}$$
### Phase 6: Organ Risk Mapping & Anatomical Localization
- **Core Biological Trace**:
  $$\text{Drug} \rightarrow \text{Target} \rightarrow \text{Gene / Protein} \rightarrow \text{Pathway} \rightarrow \text{Tissue} \rightarrow \text{Organ}$$
- **Organ Ontology & Anatomical Systems**:
  - **Brain** (Central Nervous System — Head & Cranium)
  - **Heart** (Cardiovascular System — Thorax / Mediastinum)
  - **Liver** (Hepatic System — Right Upper Abdominal Quadrant)
  - **Kidney** (Renal System — Retroperitoneal Space)
  - **Lung** (Respiratory System — Thoracic Cavity)
  - **Gastrointestinal Tract** (Digestive System — Abdomen & Pelvis)
  - **Bone Marrow & Blood** (Hematological & Immune System — Systemic / Skeletal)
  - **Skin** (Integumentary System — External Surface)
- **Path-to-Organ Mapping & Aggregation**:
  - Transparently maps multi-hop knowledge graph paths and SIDER clinical adverse events to anatomical cavities.
  - Automatically deduplicates records and computes per-organ continuous evidence strength scores and tiers (`Low`, `Medium`, `High`).
- **Avoiding Overclaiming**:
  - Organ risk mapping represents potential computational risk signals and biomedical hypotheses for 3D visualization in the Human Virtual Twin.
  - Mandatory disclaimer: *It is not a clinical diagnosis or treatment recommendation.*

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
| `POST` | `/api/risk/predict` | Multi-modal evidence fusion and organ risk prediction |
| `GET` | `/api/risk/{prediction_id}` | Retrieve audited risk prediction report by UUID |
| `GET` | `/api/explanations/{prediction_id}` | UI-ready SHAP explanation and multi-source evidence traceability report |
| `GET` | `/api/organ-risk/{prediction_id}` | **Phase 6**: Full anatomical organ-level risk profile for 3D Virtual Twin |

---

## 💻 Example API Calls & Responses

### 1. Retrieve Organ Risk Profile (GET `/api/organ-risk/{prediction_id}`)

**Request**:
```bash
curl "http://localhost:8000/api/organ-risk/dc6ece59-05c6-4aca-9f92-9a227d879b85"
```

**Response**:
```json
{
  "prediction_id": "dc6ece59-05c6-4aca-9f92-9a227d879b85",
  "drug_id": "CHEMBL112",
  "drug_name": "Acetaminophen",
  "canonical_smiles": "CC(=O)Nc1ccc(O)cc1",
  "highest_risk_organ": "liver",
  "overall_risk_score": 0.8282,
  "overall_risk_category": "High",
  "organs": {
    "liver": {
      "organ_id": "liver",
      "name": "Liver",
      "system": "Hepatic System",
      "anatomical_region": "Abdomen (Right Upper Quadrant)",
      "risk": 0.7559,
      "category": "High",
      "confidence": 0.9024,
      "evidence_strength": "High",
      "evidence_strength_score": 0.95,
      "evidence_count": 5,
      "primary_mechanisms": [
        "Acetaminophen [METABOLIZED_BY] -> Cytochrome P450 2E1 (CYP2E1) [ENCODED_BY] -> CYP2E1 [PARTICIPATES_IN_PATHWAY] -> NAPQI Bioactivation & Glutathione Depletion [ACTIVE_IN_TISSUE] -> Hepatocytes [PART_OF_ORGAN] -> Liver",
        "Reported Reaction: Hepatotoxicity",
        "Reported Reaction: Acute Hepatic Failure"
      ],
      "paths": [ ... ],
      "adverse_effects": [ ... ],
      "literature_citations": [ ... ]
    },
    "heart": {
      "organ_id": "heart",
      "name": "Heart",
      "system": "Cardiovascular System",
      "anatomical_region": "Thorax / Mediastinum",
      "risk": 0.3201,
      "category": "Low",
      "confidence": 0.8720,
      "evidence_strength": "Medium",
      "evidence_strength_score": 0.20,
      "evidence_count": 1,
      "primary_mechanisms": ["No specific high-affinity heart liability detected"]
    },
    "gastrointestinal": {
      "organ_id": "gastrointestinal",
      "name": "Gastrointestinal Tract",
      "system": "Digestive System",
      "anatomical_region": "Abdomen & Pelvis",
      "risk": 0.4512,
      "category": "Moderate",
      "confidence": 0.8195,
      "evidence_strength": "Medium",
      "evidence_strength_score": 0.42,
      "evidence_count": 2,
      "primary_mechanisms": ["Secondary mucosal prostaglandin pathway interaction"]
    }
  },
  "supported_organs": ["brain", "heart", "liver", "kidney", "lung", "gastrointestinal", "blood", "skin"],
  "evidence_sufficiency": {
    "is_sufficient": true,
    "flag_for_review": false,
    "review_reasons": []
  },
  "disclaimer": "Research-grade prototype. Organ risk mapping represents potential risk signals derived from computational models and biomedical evidence fusion. It is not a clinical diagnosis or treatment recommendation.",
  "created_at": "2026-09-25T21:43:16.000000+00:00"
}
```

---

### Phase 7: Interactive Human Virtual Twin & Evidence Dashboard
- **Modular 3D Anatomical Twin Engine**:
  - Built on Three.js WebGL with holographic anatomical silhouette and separate modular 3D organ meshes: `brain` (CNS), `heart` (Cardiovascular), `lung` (Respiratory), `liver` (Hepatic), `kidney` (Renal), and `gastrointestinal` (Digestive).
  - Dynamic visual state mapping based on AI prediction:
    - **Low Risk (<35%)**: Emerald Green (`#10B981`)
    - **Moderate Risk (35–65%)**: Amber Orange (`#F59E0B`)
    - **High Risk (>65%)**: Crimson Red (`#EF4444`) with real-time sinusoidal pulsing emissive glow.
- **Rich 3D Viewport Controls & Interaction**:
  - Full orbit rotation, smooth zoom, and pan.
  - Interactive Raycaster hover tooltips showing organ name, physiological system, and risk percentage.
  - Camera anatomical view presets (`Full Body`, `Head / CNS`, `Thorax / Cardio`, `Abdomen / Hepatic`).
  - Auto-rotate mode and one-click camera reset.
- **Slide-Over Organ Evidence Inspector Drawer**:
  - On organ selection, reveals detailed breakdown: Organ system, predicted risk score, prototype category, confidence, and continuous evidence strength.
  - Answers *"Why Did PharmaTwin Predict This Risk?"* with primary mechanistic pathways.
  - Traceable Knowledge Graph biological paths (e.g. `Drug -> Target -> Pathway -> Tissue -> Organ`).
  - Known clinical adverse reactions from SIDER and peer-reviewed literature citations from PubMed.
- **Strict Scientific Direction of Causality & Workflow**:
  - Pipeline flow: $\text{Drug Candidate} \rightarrow \text{Multi-Modal AI Prediction} \rightarrow \text{Organ Risk Mapping} \rightarrow \text{Highlighted 3D Virtual Twin}$.
  - Strictly prevents organ-first manual bias workflows.
- **Graceful 2D Anatomical SVG Fallback**:
  - Provides a clean, responsive vector-based 2D anatomical SVG fallback when WebGL is unavailable or when 2D mode is toggled.

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
# Run all 110 unit and API integration tests
pytest tests/ -v
```

### 3. Launch Interactive Human Virtual Twin & API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **Interactive 3D Virtual Twin App**: `http://localhost:8000/app` or `http://localhost:8000/twin`
- **Interactive API Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **ReDoc Technical Schema Reference**: `http://localhost:8000/redoc`




