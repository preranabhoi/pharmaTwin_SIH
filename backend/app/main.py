from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Path as FastApiPath,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_risk_prediction
from app.data_ingestion import fetch_drug_biomedical_data
from app.knowledge_graph import (
    build_drug_subgraph,
    find_mechanistic_paths,
    search_graph,
)
from app.molecular_processing import (
    load_molecule_from_file,
    process_molecule,
    process_smiles,
    render_molecule_png,
    render_molecule_svg,
    validate_smiles,
)
from app.explainability import generate_prediction_explanation
from app.risk_prediction import predict_drug_risk
from app.schemas import (
    DemoDrugItem,
    DrugEvidenceQuery,
    DrugEvidenceResponse,
    DrugRiskPredictionRequest,
    DrugRiskPredictionResponse,
    DrugSmilesInput,
    GraphPathsResponse,
    GraphSearchResponse,
    GraphSubgraphResponse,
    HealthResponse,
    MolecularProcessingResponse,
    PredictionExplanationResponse,
    ProcessingStatus,
)


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# ROOT & HEALTH ENDPOINTS
# ---------------------------------------------------------

@app.get("/")
def root() -> dict[str, str]:
    """Root entrypoint returning system status and active pipeline phases."""
    return {
        "message": "PharmaTwin AI API is running.",
        "status": "healthy",
        "version": settings.APP_VERSION,
        "phase": "Phase 5: Explainability and Evidence Traceability Engine",
    }


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Detailed health check endpoint."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


# ---------------------------------------------------------
# DEMO DATA ENDPOINT
# ---------------------------------------------------------

@app.get(
    "/api/molecular/demo-drugs",
    response_model=List[DemoDrugItem],
    summary="Get preloaded benchmark demo compounds",
)
def get_demo_drugs() -> List[dict]:
    """
    Returns curated benchmark drugs (Acetaminophen, Aspirin, Ibuprofen, Doxorubicin)
    for quick demonstration and testing.
    """
    demo_file = settings.DEMO_DATA_DIR / "sample_drugs.json"
    if demo_file.exists():
        try:
            with open(demo_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read demo drugs: {str(exc)}",
            ) from exc
    return []


# ---------------------------------------------------------
# PHASE 1: MOLECULAR PROCESSING ENDPOINTS
# ---------------------------------------------------------

@app.post(
    "/api/molecular/process",
    response_model=MolecularProcessingResponse,
    status_code=status.HTTP_200_OK,
    summary="Process SMILES into standardized molecular evidence",
)
def process_drug(
    drug: DrugSmilesInput,
) -> dict:
    """
    Validate and extract molecular evidence from a SMILES string:
    - Chemically validate SMILES structure
    - Generate Canonical SMILES, InChI, InChIKey, and Molecular Formula
    - Compute 9 physicochemical descriptors (Lipinski, TPSA, Ring Counts)
    - Generate 2048-bit Morgan Circular Fingerprint (ECFP4 equivalent)
    - Include 2D SVG vector rendering for frontend visualization
    """
    try:
        return process_smiles(
            smiles=drug.smiles,
            drug_id=drug.drug_id,
            name=drug.name,
            include_svg=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/molecular/process-file",
    response_model=MolecularProcessingResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and process SDF or MOL molecular structure file",
)
async def process_drug_file(
    file: UploadFile = File(..., description="Molecular structure file (.sdf or .mol)"),
    drug_id: Optional[str] = Form(default=None, description="Optional drug/compound identifier"),
    name: Optional[str] = Form(default=None, description="Optional compound common name"),
) -> dict:
    """
    Upload and parse an SDF (.sdf, .sd) or MOL (.mol) file.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file name is missing.",
        )

    extension = Path(file.filename).suffix.lower()
    allowed_extensions = {".sdf", ".mol", ".sd"}

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file extension '{extension}'. "
                "Please upload a valid .sdf or .mol chemical file."
            ),
        )

    temp_path = None
    try:
        contents = await file.read()

        if not contents or len(contents.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded molecular file is empty.",
            )

        with NamedTemporaryFile(
            suffix=extension,
            delete=False,
        ) as temp_file:
            temp_file.write(contents)
            temp_path = temp_file.name

        mol = load_molecule_from_file(temp_path)
        result = process_molecule(
            mol=mol,
            drug_id=drug_id,
            name=name or Path(file.filename).stem,
            input_type="sdf" if extension in (".sdf", ".sd") else "mol",
            input_value=file.filename,
            include_svg=True,
        )
        result["filename"] = file.filename
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading molecular file: {str(exc)}",
        ) from exc

    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


@app.get(
    "/api/molecular/render-image",
    summary="Render 2D molecular depiction as PNG or SVG",
)
def render_drug_image_get(
    smiles: str = Query(..., description="SMILES string to render", examples=["CC(=O)NC1=CC=C(O)C=C1"]),
    width: int = Query(default=350, ge=50, le=1200, description="Image width in pixels"),
    height: int = Query(default=350, ge=50, le=1200, description="Image height in pixels"),
    format: str = Query(default="png", description="Output format ('png' or 'svg')"),
) -> Response:
    """
    Renders 2D depiction of a chemical molecule for frontend display.
    """
    try:
        mol = validate_smiles(smiles)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    fmt = format.lower().strip()
    if fmt == "svg":
        svg_content = render_molecule_svg(mol, width=width, height=height)
        return Response(content=svg_content, media_type="image/svg+xml")
    elif fmt == "png":
        png_bytes = render_molecule_png(mol, width=width, height=height)
        return Response(content=png_bytes, media_type="image/png")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format}'. Use 'png' or 'svg'.",
        )


@app.post(
    "/api/molecular/render-image",
    summary="Render 2D molecular depiction from JSON payload",
)
def render_drug_image_post(
    drug: DrugSmilesInput,
    width: int = Query(default=350, ge=50, le=1200),
    height: int = Query(default=350, ge=50, le=1200),
    format: str = Query(default="png"),
) -> Response:
    """
    POST endpoint to render 2D depiction from JSON input payload.
    """
    return render_drug_image_get(
        smiles=drug.smiles,
        width=width,
        height=height,
        format=format,
    )


# ---------------------------------------------------------
# PHASE 2: BIOMEDICAL DATA INGESTION ENDPOINTS
# ---------------------------------------------------------

@app.post(
    "/api/evidence/drug/{drug_id}",
    response_model=DrugEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest and normalize multi-source biomedical evidence for a drug",
)
def ingest_drug_evidence_post(
    drug_id: str = FastApiPath(..., description="Target drug identifier (e.g. CHEMBL112, Acetaminophen)"),
    query: Optional[DrugEvidenceQuery] = None,
) -> dict:
    """
    Fuses multi-source biomedical evidence (PubChem, ChEMBL, UniProt, OpenTargets, SIDER, PubMed)
    for a target drug candidate.
    """
    smiles = query.smiles if query else None
    name = query.name if query else None
    force_refresh = query.force_refresh if query else False

    return fetch_drug_biomedical_data(
        drug_id=drug_id,
        smiles=smiles,
        name=name,
        force_refresh=force_refresh,
    )


@app.get(
    "/api/evidence/drug/{drug_id}",
    response_model=DrugEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve biomedical evidence for a drug (GET query)",
)
def ingest_drug_evidence_get(
    drug_id: str = FastApiPath(..., description="Target drug identifier (e.g. CHEMBL112, Acetaminophen)"),
    smiles: Optional[str] = Query(default=None, description="Optional SMILES string"),
    name: Optional[str] = Query(default=None, description="Optional drug name"),
    force_refresh: bool = Query(default=False, description="Bypass local cache"),
) -> dict:
    """
    GET query endpoint for biomedical evidence retrieval.
    """
    return fetch_drug_biomedical_data(
        drug_id=drug_id,
        smiles=smiles,
        name=name,
        force_refresh=force_refresh,
    )


# ---------------------------------------------------------
# PHASE 3: BIOMEDICAL KNOWLEDGE GRAPH ENDPOINTS
# ---------------------------------------------------------

@app.get(
    "/api/graph/drug/{drug_id}",
    response_model=GraphSubgraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve frontend-ready biomedical knowledge subgraph for a drug",
)
def get_drug_subgraph(
    drug_id: str = FastApiPath(..., description="Drug identifier (e.g. CHEMBL112, Aspirin)"),
    depth: int = Query(default=3, ge=1, le=6, description="Neighborhood traversal depth"),
    max_nodes: int = Query(default=100, ge=10, le=500, description="Maximum node limit"),
) -> dict:
    """
    Constructs an interactive, frontend-ready biomedical knowledge subgraph for a drug:
    - Nodes with ontological classifications (Drug, Target, Gene, Pathway, Tissue, Organ, AdverseEffect, Literature)
    - Directed edges with confidence and source database provenance
    - Multi-hop causal and adverse reasoning paths
    """
    return build_drug_subgraph(drug_id=drug_id, depth=depth, max_nodes=max_nodes)


@app.get(
    "/api/graph/drug/{drug_id}/paths",
    response_model=GraphPathsResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract candidate multi-hop mechanistic paths connecting drug to organs",
)
def get_drug_mechanistic_paths(
    drug_id: str = FastApiPath(..., description="Drug identifier (e.g. CHEMBL112, Acetaminophen)"),
    target_organ: Optional[str] = Query(default=None, description="Optional filter by organ name (e.g. Liver, Heart)"),
) -> dict:
    """
    Extracts traceable multi-hop paths:
    - Drug -> Target -> Gene -> Pathway -> Tissue -> Organ
    - Drug -> AdverseEffect -> Organ
    """
    paths = find_mechanistic_paths(drug_id=drug_id, target_organ=target_organ)
    return {
        "drug_id": drug_id,
        "drug_name": drug_id,
        "total_paths": len(paths),
        "paths": [p.model_dump() for p in paths],
        "status": ProcessingStatus(
            valid=True,
            message=f"Extracted {len(paths)} candidate mechanistic reasoning paths.",
        ).model_dump(),
    }


@app.get(
    "/api/graph/search",
    response_model=GraphSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search biomedical knowledge graph nodes by query string and entity type",
)
def search_knowledge_graph(
    query: str = Query(..., min_length=1, description="Keyword search query (e.g. Liver, CYP2E1, COX-1)"),
    entity_type: Optional[str] = Query(default=None, description="Optional filter by entity type (e.g. Organ, Gene, Target)"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results limit"),
) -> dict:
    """
    Searches entities across the knowledge graph with keyword matching and degree metrics.
    """
    return search_graph(query=query, entity_type=entity_type, limit=limit)


# ---------------------------------------------------------
# PHASE 4: EVIDENCE FUSION & RISK REASONING ENDPOINTS
# ---------------------------------------------------------

@app.post(
    "/api/risk/predict",
    response_model=DrugRiskPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run evidence fusion and multi-organ adverse risk prediction",
)
def predict_risk(
    request: DrugRiskPredictionRequest,
) -> DrugRiskPredictionResponse:
    """
    Primary Phase 4 Multi-Modal Risk Reasoning & Organ Risk Prediction Pipeline:
    - Fuses molecular descriptors, fingerprint similarity, knowledge graph paths, adverse events, and literature.
    - Strictly separates model prediction, confidence, and evidence strength.
    - Employs evidence sufficiency gating (flags sparse evidence without inflating confidence).
    - Outputs decomposed organ-level risks (Heart, Liver, Kidney, Lung, Brain).
    - Returns full explainability attributions and saves an immutable audit record.
    """
    if not request.drug_id and not request.smiles and not request.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one drug identifier ('drug_id', 'smiles', or 'name') must be provided.",
        )

    try:
        return predict_drug_risk(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk prediction failed: {str(exc)}",
        ) from exc


@app.get(
    "/api/risk/{prediction_id}",
    response_model=DrugRiskPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an audited risk prediction report by prediction UUID",
)
def get_prediction_report(
    prediction_id: str = FastApiPath(..., description="Unique prediction UUID"),
) -> dict:
    """
    Retrieves stored immutable risk prediction audit record from SQLite.
    """
    record = get_risk_prediction(prediction_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk prediction report '{prediction_id}' not found in audit logs.",
        )
    return record


# ---------------------------------------------------------
# PHASE 5: EXPLAINABILITY & EVIDENCE TRACEABILITY ENDPOINTS
# ---------------------------------------------------------

@app.get(
    "/api/explanations/{prediction_id}",
    response_model=PredictionExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate UI-ready SHAP feature attributions and multi-source evidence traceability report",
)
def get_prediction_explanation(
    prediction_id: str = FastApiPath(..., description="Target prediction UUID to explain"),
) -> PredictionExplanationResponse:
    """
    Answers: 'WHY DID PHARMATWIN PREDICT THIS RISK?'
    - Computes local SHAP feature attributions (contribution, direction, rank, description).
    - Links supporting Knowledge Graph mechanistic paths (Drug -> Target -> Gene -> Pathway -> Tissue -> Organ).
    - Links supporting SIDER historical adverse reactions and PubMed literature citations.
    - Provides explanation quality metadata (source diversity, evidence count, baseline expected value).
    - Strictly differentiates statistical feature attribution from biological causality.
    """
    try:
        return generate_prediction_explanation(prediction_id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanation report: {str(exc)}",
        ) from exc


