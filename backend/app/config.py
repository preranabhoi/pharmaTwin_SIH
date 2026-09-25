from __future__ import annotations

import os
from pathlib import Path
from typing import List


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DEMO_DATA_DIR = DATA_DIR / "demo"
MODELS_DIR = BASE_DIR / "models"


class Settings:
    """
    Application configuration settings.
    Loads values from environment variables with sensible defaults.
    """

    APP_NAME: str = os.getenv("APP_NAME", "PharmaTwin AI")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.2.0")
    DESCRIPTION: str = (
        "Evidence-aware drug risk prediction, biomedical data ingestion, "
        "and organ-level visualization platform."
    )
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Ingestion & Execution Modes
    ENABLE_EXTERNAL_SOURCES: bool = os.getenv(
        "ENABLE_EXTERNAL_SOURCES", "False"
    ).lower() in ("true", "1", "t")
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "True").lower() in ("true", "1", "t")
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))

    # CORS settings
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:8000",
        ).split(",")
        if origin.strip()
    ]

    # Database & Caching
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'pharmatwin.db'}",
    )
    SQLITE_PATH: Path = BASE_DIR / "pharmatwin.db"

    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    RAW_DATA_DIR: Path = RAW_DATA_DIR
    PROCESSED_DATA_DIR: Path = PROCESSED_DATA_DIR
    DEMO_DATA_DIR: Path = DEMO_DATA_DIR
    MODELS_DIR: Path = MODELS_DIR
    DEMO_EVIDENCE_PATH: Path = DEMO_DATA_DIR / "biomedical_evidence_demo.json"

    # External Biomedical Data API Endpoints
    PUBCHEM_API_BASE: str = os.getenv(
        "PUBCHEM_API_BASE",
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
    )
    CHEMBL_API_BASE: str = os.getenv(
        "CHEMBL_API_BASE",
        "https://www.ebi.ac.uk/chembl/api/data",
    )
    UNIPROT_API_BASE: str = os.getenv(
        "UNIPROT_API_BASE",
        "https://rest.uniprot.org",
    )
    OPENTARGETS_API_BASE: str = os.getenv(
        "OPENTARGETS_API_BASE",
        "https://api.platform.opentargets.org/api/v4/graphql",
    )
    PUBMED_API_BASE: str = os.getenv(
        "PUBMED_API_BASE",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
    )
    STRING_DB_API_BASE: str = os.getenv(
        "STRING_DB_API_BASE",
        "https://version-12-0.string-db.org/api",
    )


settings = Settings()
