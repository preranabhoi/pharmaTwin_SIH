# PharmaTwin AI - Frontend Architecture (Planned Phase)

## Overview
The PharmaTwin AI Frontend is designed as a modern, interactive dashboard providing:
1. **Drug Input Console**: SMILES input, file upload (.sdf / .mol), structure drawer, and demo molecule quick-select.
2. **Molecular Properties & Descriptors Viewer**: Lipinski rule of five evaluation, radar charts, 2D structure render.
3. **Biomedical Knowledge Graph Explorer**: Interactive node-link graph visualization of compound-target-pathway associations.
4. **Evidence & Explainability Trail**: Feature importance, toxicophore substructure highlighting, and literature citations.
5. **Human Virtual Twin 3D Viewport**: Interactive 3D anatomical organ-risk map (Three.js / React Three Fiber) with color-coded toxicity heatmaps and multi-organ risk cards.

## Technology Stack
- **Framework**: React 18+ / TypeScript / Vite
- **3D Visualization**: Three.js / React Three Fiber / Drei
- **Graph Visualization**: Cytoscape.js / D3.js / React Force Graph
- **State Management & Data Fetching**: TanStack Query (React Query) + Zustand
- **Styling**: Modern design system with responsive CSS and glassmorphism styling
