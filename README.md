# PharmaTwin AI 🧬🫀

**Evidence-Aware Drug Risk Prediction Research Platform & Human Virtual Twin**

---

> ### ⚠️ Research Scope & Boundaries Disclaimer
> - **Research & Decision-Support Prototype**: PharmaTwin AI is designed exclusively for exploratory pharmacological research and computational modeling.
> - **Molecular Feature Extraction Only**: Phase 1 provides standardized chemical representations, topological descriptors, and fingerprints. **Molecular descriptors themselves do not constitute clinical toxicity predictions or clinical risk scores.**
> - **NOT Clinical Diagnostics**: It is **not** a clinical diagnostic tool or medical device.
> - **NOT Treatment Recommendations**: It does **not** prescribe or recommend patient treatments.
> - **NOT a Replacement for Clinical Trials**: Computational representations do not replace in vitro, in vivo, or clinical safety trials.
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
[Phase 2] Biomedical Data Integration (PubChem, ChEMBL, UniProt, STRING-DB)
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
│   │   ├── data_ingestion.py         # Biomedical data source integration (Phase 2 Foundation)
│   │   ├── knowledge_graph.py        # Knowledge subgraph constructor (Phase 3 Foundation)
│   │   ├── evidence_fusion.py        # Multi-modal evidence fusion engine (Phase 4 Foundation)
│   │   ├── risk_prediction.py        # Toxicity & adverse risk predictor (Phase 5 Foundation)
│   │   ├── explainability.py         # Toxicophore attribution & explainability (Phase 6 Foundation)
│   │   ├── organ_mapping.py          # Organ-level risk aggregation (Phase 7 Foundation)
│   │   └── database.py               # Cache & persistence provider (Foundation)
│   ├── data/
│   │   ├── raw/                      # Raw bioassay data & external data cache
│   │   ├── processed/                # Normalized features & pre-computed embeddings
│   │   └── demo/                     # Demo molecules (aspirin.sdf, ibuprofen.mol, sample_drugs.json)
│   ├── models/                       # Model checkpoints & serialized weights
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # Pytest fixtures & FastAPI TestClient
│   │   ├── test_molecular_processing.py # Unit tests for cheminformatics logic
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

## 🧪 Phase 1: Drug Input + Molecular Evidence Layer

### Supported Inputs
1. **SMILES Strings**: Arbitrary chemical SMILES (e.g., `CC(=O)NC1=CC=C(O)C=C1`).
2. **SDF Files**: `.sdf` / `.sd` structure-data files.
3. **MOL Files**: `.mol` MDL Molfile format.
4. **Drug Identifiers & Names**: Optional `drug_id` (e.g. `CHEMBL112`) and compound `name`.

### Extracted Molecular Evidence
- **Normalization & Identifiers**: Canonical SMILES, IUPAC InChI, InChIKey, Hill Molecular Formula, Atom Counts.
- **Physicochemical Descriptors**:
  - Molecular Weight ($g/mol$)
  - Wildman-Crippen Partition Coefficient ($\text{LogP}$)
  - Topological Polar Surface Area ($\text{TPSA}$ in $\text{Å}^2$)
  - Hydrogen Bond Donors ($\text{HBD}$)
  - Hydrogen Bond Acceptors ($\text{HBA}$)
  - Rotatable Single Bonds
  - Heavy (Non-Hydrogen) Atom Count
  - Total Ring Count
  - Aromatic Ring Count
- **Molecular Fingerprints**: 2048-bit Morgan circular fingerprints ($\text{radius} = 2$, equivalent to $\text{ECFP4}$).
- **2D Visual Depictions**: Real-time vector SVG rendering and binary PNG images.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status and root greeting |
| `GET` | `/health` | Health check endpoint with version info |
| `GET` | `/api/molecular/demo-drugs` | Pre-loaded benchmark molecules for rapid evaluation |
| `POST` | `/api/molecular/process` | Processes SMILES into standardized molecular evidence |
| `POST` | `/api/molecular/process-file` | Parses `.sdf` or `.mol` file and returns molecular evidence |
| `GET` | `/api/molecular/render-image` | Generates 2D molecular image (`png` or `svg`) via query parameters |
| `POST` | `/api/molecular/render-image` | Generates 2D molecular image from JSON body |

---

## 💻 Example API Calls & Responses

### 1. Process SMILES (POST `/api/molecular/process`)

**Request**:
```bash
curl -X POST "http://localhost:8000/api/molecular/process" \
     -H "Content-Type: application/json" \
     -d '{
       "smiles": "CC(=O)NC1=CC=C(O)C=C1",
       "drug_id": "CHEMBL112",
       "name": "Acetaminophen"
     }'
```

**Standard Response**:
```json
{
  "drug": {
    "drug_id": "CHEMBL112",
    "name": "Acetaminophen",
    "input_type": "smiles",
    "input_value": "CC(=O)NC1=CC=C(O)C=C1"
  },
  "molecule": {
    "canonical_smiles": "CC(=O)Nc1ccc(O)cc1",
    "inchi": "InChI=1S/C8H9NO2/c1-6(10)9-7-2-4-8(11)5-3-7/h2-5,11H,1H3,(H,9,10)",
    "inchi_key": "RZVAJINKPMORJF-UHFFFAOYSA-N",
    "formula": "C8H9NO2",
    "num_atoms": 20,
    "num_heavy_atoms": 11
  },
  "descriptors": {
    "molecular_weight": 151.165,
    "logp": 1.3506,
    "tpsa": 49.33,
    "hbd": 2,
    "hba": 2,
    "rotatable_bonds": 1,
    "heavy_atom_count": 11,
    "ring_count": 1,
    "aromatic_ring_count": 1
  },
  "fingerprint": {
    "type": "Morgan",
    "radius": 2,
    "size": 2048,
    "active_bits": 19,
    "bits": [0, 0, 1, 0, 0, "... 2048 binary bits ..."]
  },
  "status": {
    "valid": true,
    "message": "Molecular evidence extracted successfully."
  },
  "valid": true,
  "canonical_smiles": "CC(=O)Nc1ccc(O)cc1",
  "input_smiles": "CC(=O)NC1=CC=C(O)C=C1",
  "fingerprint_size": 2048,
  "active_fingerprint_bits": 19,
  "filename": null,
  "svg_image": "<svg ...></svg>"
}
```

### 2. Upload Molecular File (POST `/api/molecular/process-file`)

```bash
curl -X POST "http://localhost:8000/api/molecular/process-file" \
     -F "file=@backend/data/demo/aspirin.sdf" \
     -F "drug_id=CHEMBL25" \
     -F "name=Aspirin"
```

### 3. Render 2D Molecular Image (GET `/api/molecular/render-image`)

```bash
# Render PNG image (350x350)
curl -o acetaminophen.png "http://localhost:8000/api/molecular/render-image?smiles=CC(=O)NC1=CC=C(O)C=C1&format=png"

# Render SVG markup
curl "http://localhost:8000/api/molecular/render-image?smiles=CC(=O)NC1=CC=C(O)C=C1&format=svg"
```

---

## 🚀 Running & Testing

### 1. Setup Backend
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
pytest tests/ -v
```

### 3. Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive OpenAPI documentation will be accessible at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
