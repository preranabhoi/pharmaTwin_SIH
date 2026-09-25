from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Draw, Lipinski, rdMolDescriptors
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Draw import rdMolDraw2D


# ---------------------------------------------------------
# Morgan Fingerprint Generator Configuration
# ---------------------------------------------------------

MORGAN_GENERATOR = rdFingerprintGenerator.GetMorganGenerator(
    radius=2,
    fpSize=2048,
)


# ---------------------------------------------------------
# 1. SMILES VALIDATION
# ---------------------------------------------------------

def validate_smiles(smiles: str) -> Chem.Mol:
    """
    Validate a SMILES string and convert it into
    an RDKit molecule object.

    Raises:
        ValueError: If the SMILES is empty, non-string, or chemically invalid.
    """
    if not isinstance(smiles, str):
        raise ValueError("SMILES must be a string.")

    smiles = smiles.strip()

    if not smiles:
        raise ValueError("SMILES cannot be empty.")

    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        raise ValueError(
            f"Invalid SMILES structure: '{smiles}'. Unable to parse chemical graph."
        )

    return mol


# ---------------------------------------------------------
# 2. MOLECULAR DESCRIPTORS
# ---------------------------------------------------------

def calculate_descriptors(
    mol: Chem.Mol,
) -> Dict[str, float | int]:
    """
    Calculate selected 2D/3D physicochemical descriptors.

    These descriptors serve as standardized molecular evidence
    for downstream machine learning and multi-target reasoning.
    """
    if mol is None:
        raise ValueError("Cannot calculate descriptors for None molecule.")

    # Normalize to non-explicit hydrogen representation for consistent descriptors
    norm_mol = Chem.RemoveHs(mol) if mol.GetNumAtoms() > mol.GetNumHeavyAtoms() else mol

    return {
        "molecular_weight": round(
            Descriptors.MolWt(norm_mol), 4
        ),
        "logp": round(
            Crippen.MolLogP(norm_mol), 4
        ),
        "tpsa": round(
            rdMolDescriptors.CalcTPSA(norm_mol), 4
        ),
        "hbd": int(
            Lipinski.NumHDonors(norm_mol)
        ),
        "hba": int(
            Lipinski.NumHAcceptors(norm_mol)
        ),
        "rotatable_bonds": int(
            Lipinski.NumRotatableBonds(norm_mol)
        ),
        "heavy_atom_count": int(
            norm_mol.GetNumHeavyAtoms()
        ),
        "ring_count": int(
            rdMolDescriptors.CalcNumRings(norm_mol)
        ),
        "aromatic_ring_count": int(
            rdMolDescriptors.CalcNumAromaticRings(norm_mol)
        ),
    }


# ---------------------------------------------------------
# 3. MORGAN FINGERPRINT
# ---------------------------------------------------------

def generate_morgan_fingerprint(
    mol: Chem.Mol,
) -> List[int]:
    """
    Generate a 2048-bit Morgan fingerprint (radius = 2, equivalent to ECFP4).

    Returns:
        List of 2048 integer bit values (0 or 1).
    """
    if mol is None:
        raise ValueError("Cannot generate fingerprint for None molecule.")

    norm_mol = Chem.RemoveHs(mol) if mol.GetNumAtoms() > mol.GetNumHeavyAtoms() else mol
    fingerprint = MORGAN_GENERATOR.GetFingerprint(norm_mol)
    return list(fingerprint)


# ---------------------------------------------------------
# 4. MOLECULAR IDENTIFIERS & NORMALIZATION
# ---------------------------------------------------------

def extract_molecule_identifiers(
    mol: Chem.Mol,
) -> Dict[str, Any]:
    """
    Extract standardized chemical representations:
    - Canonical SMILES
    - InChI (IUPAC International Chemical Identifier)
    - InChIKey (Hashed 27-character standard key)
    - Molecular Formula (Hill System)
    - Atom counts (total with H, heavy non-H)
    """
    if mol is None:
        raise ValueError("Cannot extract identifiers for None molecule.")

    norm_mol = Chem.RemoveHs(mol) if mol.GetNumAtoms() > mol.GetNumHeavyAtoms() else mol

    canonical_smiles = Chem.MolToSmiles(norm_mol)

    # InChI & InChIKey with graceful error handling
    try:
        inchi_str = Chem.MolToInchi(norm_mol)
    except Exception:
        inchi_str = None

    try:
        inchi_key_str = Chem.MolToInchiKey(norm_mol) if inchi_str else None
    except Exception:
        inchi_key_str = None

    try:
        formula_str = rdMolDescriptors.CalcMolFormula(norm_mol)
    except Exception:
        formula_str = None

    # Calculate atom counts
    try:
        mol_with_h = Chem.AddHs(norm_mol)
        num_atoms = mol_with_h.GetNumAtoms()
    except Exception:
        num_atoms = norm_mol.GetNumAtoms()

    num_heavy_atoms = norm_mol.GetNumHeavyAtoms()

    return {
        "canonical_smiles": canonical_smiles,
        "inchi": inchi_str,
        "inchi_key": inchi_key_str,
        "formula": formula_str,
        "num_atoms": num_atoms,
        "num_heavy_atoms": num_heavy_atoms,
    }


# ---------------------------------------------------------
# 5. MOLECULAR 2D RENDERING
# ---------------------------------------------------------

def render_molecule_svg(
    mol: Chem.Mol,
    width: int = 350,
    height: int = 350,
) -> str:
    """
    Render 2D depiction of the molecule as an SVG string.
    """
    if mol is None:
        raise ValueError("Cannot render SVG for None molecule.")

    norm_mol = Chem.RemoveHs(mol) if mol.GetNumAtoms() > mol.GetNumHeavyAtoms() else mol
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.drawOptions().addStereoAnnotation = True
    drawer.DrawMolecule(norm_mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def render_molecule_png(
    mol: Chem.Mol,
    width: int = 350,
    height: int = 350,
) -> bytes:
    """
    Render 2D depiction of the molecule as raw PNG bytes.
    """
    if mol is None:
        raise ValueError("Cannot render PNG for None molecule.")

    norm_mol = Chem.RemoveHs(mol) if mol.GetNumAtoms() > mol.GetNumHeavyAtoms() else mol
    img = Draw.MolToImage(norm_mol, size=(width, height))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------
# 6. LOAD SDF / MOL FILE
# ---------------------------------------------------------

def load_molecule_from_file(
    file_path: str | Path,
) -> Chem.Mol:
    """
    Read the first valid molecule from an SDF or MOL file.

    Supports:
        - .sdf / .sd files (SDMolSupplier)
        - .mol files (MolFromMolFile / SDMolSupplier)

    Raises:
        ValueError: If file does not exist or contains no valid molecular structure.
    """
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"Molecular file not found: {path}")

    suffix = path.suffix.lower()

    if suffix in (".sdf", ".sd"):
        supplier = Chem.SDMolSupplier(str(path), removeHs=False)
        for mol in supplier:
            if mol is not None:
                return mol

        mol = Chem.MolFromMolFile(str(path), removeHs=False)
        if mol is not None:
            return mol

    elif suffix == ".mol":
        mol = Chem.MolFromMolFile(str(path), removeHs=False)
        if mol is not None:
            return mol

        supplier = Chem.SDMolSupplier(str(path), removeHs=False)
        for mol in supplier:
            if mol is not None:
                return mol
    else:
        raise ValueError(
            f"Unsupported molecular file extension '{suffix}'. Expected .sdf or .mol"
        )

    raise ValueError(
        f"No valid chemical molecule could be parsed from '{path.name}'."
    )


def load_sdf_file(
    file_path: str | Path,
) -> Chem.Mol:
    """
    Read the first valid molecule from an SDF or MOL file.
    Maintained for backward compatibility.
    """
    return load_molecule_from_file(file_path)


# ---------------------------------------------------------
# 7. PROCESS RDKit MOLECULE OBJECT
# ---------------------------------------------------------

def process_molecule(
    mol: Chem.Mol,
    drug_id: Optional[str] = None,
    name: Optional[str] = None,
    input_type: str = "mol_object",
    input_value: Optional[str] = None,
    include_svg: bool = True,
) -> Dict[str, Any]:
    """
    Process an RDKit molecule object into standardized Phase 1 molecular evidence:
    - Normalization & Identifiers (Canonical SMILES, InChI, InChIKey, Formula)
    - 9 Physicochemical Descriptors
    - 2048-bit Morgan Fingerprint
    - 2D SVG vector rendering (optional)
    """
    if mol is None:
        raise ValueError("Invalid or empty molecule object.")

    norm_mol = Chem.RemoveHs(mol) if mol.GetNumAtoms() > mol.GetNumHeavyAtoms() else mol

    identifiers = extract_molecule_identifiers(norm_mol)
    canonical_smiles = identifiers["canonical_smiles"]
    descriptors = calculate_descriptors(norm_mol)
    fingerprint = generate_morgan_fingerprint(norm_mol)
    active_bits = sum(fingerprint)

    svg_str = render_molecule_svg(norm_mol) if include_svg else None

    # Standard nested evidence structure
    drug_metadata = {
        "drug_id": drug_id,
        "name": name,
        "input_type": input_type,
        "input_value": input_value,
    }

    molecule_data = identifiers

    fingerprint_data = {
        "type": "Morgan",
        "radius": 2,
        "size": len(fingerprint),
        "active_bits": active_bits,
        "bits": fingerprint,
    }

    status_data = {
        "valid": True,
        "message": "Molecular evidence extracted successfully.",
    }

    return {
        # Nested standard evidence representation
        "drug": drug_metadata,
        "molecule": molecule_data,
        "descriptors": descriptors,
        "fingerprint": fingerprint_data,
        "status": status_data,

        # Top-level backward compatibility fields
        "valid": True,
        "input_smiles": input_value if input_type == "smiles" else None,
        "canonical_smiles": canonical_smiles,
        "fingerprint_size": len(fingerprint),
        "active_fingerprint_bits": active_bits,
        "svg_image": svg_str,
    }


# ---------------------------------------------------------
# 8. PROCESS SMILES
# ---------------------------------------------------------

def process_smiles(
    smiles: str,
    drug_id: Optional[str] = None,
    name: Optional[str] = None,
    include_svg: bool = True,
) -> Dict[str, Any]:
    """
    Complete SMILES processing pipeline:

        SMILES Input
            ->
        Validation
            ->
        Canonical SMILES / InChI / InChIKey
            ->
        Physicochemical Descriptors
            ->
        Morgan Fingerprint
            ->
        Standardized Molecular Evidence
    """
    mol = validate_smiles(smiles)
    return process_molecule(
        mol=mol,
        drug_id=drug_id,
        name=name,
        input_type="smiles",
        input_value=smiles.strip(),
        include_svg=include_svg,
    )
