# PharmaTwin AI — Researcher Decision-Support Frontend Architecture

## Overview
PharmaTwin AI is a research-grade decision-support platform for multi-source biomedical evidence fusion, mechanistic reasoning, and organ-level risk visualization.

### Architecture Highlights
1. **Candidate Drug Ingestion**: SMILES input, .SDF/.MOL structure dropzone, calibrated benchmark compound quick-selectors (Acetaminophen, Aspirin, Ibuprofen, Doxorubicin).
2. **2D Molecular Structure & Descriptors**: 2D chemical structure rendering with physicochemical descriptors (MW, LogP, TPSA, HBD, HBA, Rotatable Bonds, Aromatic Rings).
3. **2D Front-Facing Human Virtual Twin (`HumanVirtualTwin2D`)**:
   - Single coherent front-facing anatomical human silhouette (Head + Torso + Arms + Legs).
   - Visibly positioned internal risk-mapped organs: **Brain**, **Heart**, **Liver**, **Kidney**, and **Lung**.
   - Risk-calibrated dynamic coloring (🟢 Low, 🟠 Moderate, 🔴 High).
   - Interactive hover tooltips and synchronized click selection.
   - Precision connector lines to compact side callout labels.
   - Front view controls: Center and Reset View.
4. **Interactive Visual Knowledge Graph (`KnowledgeGraph`)**:
   - Multi-branch directed graph with distinct node styles (Drug, Target, Protein, Gene, Pathway, Tissue, Organ, Adverse Effect, Literature).
   - Directional edges with semantic relationship badges (*targets*, *binds to*, *regulates*, *participates in*, *active in*, *affects*, *supports*).
   - Active mechanistic pathway tracing (Drug → Target → Pathway → Tissue → Organ) with dynamic path illumination and non-relevant path muting.
   - Interactive pan, zoom, reset, center, and Node Inspector Drawer with provenance and metadata.
5. **Mechanistic Reasoning ("Why This Risk?")**:
   - Step-down biological reasoning cascade (Features → Target → Pathway → Tissue → Organ).
   - Biological mechanism summary & PubMed citations.
   - Model feature attribution (SHAP) strictly distinguished from biological causality.
6. **Multi-Source Evidence Vault**: Real-time integration across PubChem, ChEMBL, UniProt, OpenTargets, SIDER, and PubMed.

## Component Structure
```
frontend/
├── index.html
├── index.css
├── app.js
└── components/
    ├── HumanVirtualTwin2D/
    │   ├── HumanTwin2D.js      # Main 2D Human Virtual Twin component
    │   ├── Organ.js            # Anatomical SVG vector path renderers
    │   ├── OrganLabel.js       # SVG connector lines & compact side labels
    │   └── organMap.js         # 5-Organ ontology & benchmark risk defaults
    │
    ├── KnowledgeGraph/
    │   ├── KnowledgeGraph.js   # Interactive SVG/Canvas graph engine
    │   ├── GraphNode.js        # Node renderer for 9 biomedical entity types
    │   ├── GraphEdge.js        # Directed relationship curves & badges
    │   ├── GraphControls.js    # Zoom, pan, reset, & filter toolbar
    │   └── EvidencePath.js     # Multi-hop pathway tracer & subgraphs
    │
    ├── RiskAnalysis/
    │   └── RiskAnalysis.js     # Overall risk hero metrics & confidence
    ├── OrganRiskTable/
    │   └── OrganRiskTable.js   # 5-Organ risk table with click synchronization
    ├── MoleculeViewer/
    │   └── MoleculeViewer.js   # 2D structure depiction & properties grid
    ├── ExplanationPanel/
    │   └── ExplanationPanel.js # "Why This Risk?" cascade & [VIEW EVIDENCE GRAPH]
    └── EvidencePanel/
        └── EvidencePanel.js    # Biomedical database vault summary
```

## Running the Application
```bash
# Option A: Standalone static HTTP server
python -m http.server 5173 --directory frontend

# Option B: Integrated FastAPI backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# Access UI at: http://localhost:8000/app or http://localhost:8000/twin
```
