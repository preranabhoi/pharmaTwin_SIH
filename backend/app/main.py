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
from app.data_ingestion import fetch_drug_biomedical_data
from app.molecular_processing import (
    load_molecule_from_file,
    process_molecule,
    process_smiles,
    render_molecule_png,
    render_molecule_svg,
    validate_smiles,
)
from app.schemas import (
    DemoDrugItem,
    DrugEvidenceQuery,
    DrugEvidenceResponse,
    DrugSmilesInput,
    HealthResponse,
    MolecularProcessingResponse,
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
        "phase": "Phase 2: Biomedical Data Ingestion and Normalization Layer",
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
    for a target drug candidate:
    - Resolves duplicate entities & merges confidence
    - Attaches complete provenance and timestamps
    - Checks and updates local persistent cache
    - Operates offline in DEMO_MODE with authentic curated pharmacological data
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
