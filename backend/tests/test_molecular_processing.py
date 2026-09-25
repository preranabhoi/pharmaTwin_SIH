from pathlib import Path
import pytest

from app.molecular_processing import (
    calculate_descriptors,
    extract_molecule_identifiers,
    generate_morgan_fingerprint,
    load_molecule_from_file,
    load_sdf_file,
    process_molecule,
    process_smiles,
    render_molecule_png,
    render_molecule_svg,
    validate_smiles,
)


# ---------------------------------------------------------
# Test 1: Valid SMILES (Ethanol)
# ---------------------------------------------------------

def test_valid_smiles():
    mol = validate_smiles("CCO")
    assert mol is not None


# ---------------------------------------------------------
# Test 2: Empty SMILES
# ---------------------------------------------------------

def test_empty_smiles():
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_smiles("")

    with pytest.raises(ValueError, match="cannot be empty"):
        validate_smiles("   ")


# ---------------------------------------------------------
# Test 3: Invalid SMILES
# ---------------------------------------------------------

def test_invalid_smiles():
    with pytest.raises(ValueError, match="Invalid SMILES structure"):
        validate_smiles("THIS_IS_NOT_A_VALID_MOLECULE")

    with pytest.raises(ValueError, match="Invalid SMILES structure"):
        validate_smiles("C=C=C=C=C=C(=O)(O)(O)(O)(O)")


# ---------------------------------------------------------
# Test 4: Descriptor Calculation (All 9 Descriptors)
# ---------------------------------------------------------

def test_descriptor_calculation():
    mol = validate_smiles("CC(=O)NC1=CC=C(O)C=C1")  # Acetaminophen
    descriptors = calculate_descriptors(mol)

    # Check presence of all 9 required descriptors
    required_keys = [
        "molecular_weight",
        "logp",
        "tpsa",
        "hbd",
        "hba",
        "rotatable_bonds",
        "heavy_atom_count",
        "ring_count",
        "aromatic_ring_count",
    ]
    for key in required_keys:
        assert key in descriptors, f"Missing descriptor: {key}"

    # Verify quantitative accuracy
    assert descriptors["molecular_weight"] == 151.165
    assert descriptors["hbd"] == 2
    assert descriptors["hba"] == 2
    assert descriptors["rotatable_bonds"] == 1
    assert descriptors["heavy_atom_count"] == 11
    assert descriptors["ring_count"] == 1
    assert descriptors["aromatic_ring_count"] == 1
    assert descriptors["tpsa"] > 40.0
    assert isinstance(descriptors["logp"], float)


# ---------------------------------------------------------
# Test 5: Morgan Fingerprint Length & Values
# ---------------------------------------------------------

def test_morgan_fingerprint():
    mol = validate_smiles("CCO")
    fingerprint = generate_morgan_fingerprint(mol)

    assert len(fingerprint) == 2048
    assert all(bit in (0, 1) for bit in fingerprint)
    assert sum(fingerprint) > 0


# ---------------------------------------------------------
# Test 6: InChI, InChIKey & Molecular Identifiers
# ---------------------------------------------------------

def test_molecule_identifiers():
    mol = validate_smiles("CC(=O)NC1=CC=C(O)C=C1")  # Acetaminophen
    identifiers = extract_molecule_identifiers(mol)

    assert identifiers["canonical_smiles"] == "CC(=O)Nc1ccc(O)cc1"
    assert identifiers["inchi"].startswith("InChI=1S/C8H9NO2/")
    assert identifiers["inchi_key"] == "RZVAJINKPMORJF-UHFFFAOYSA-N"
    assert identifiers["formula"] == "C8H9NO2"
    assert identifiers["num_atoms"] == 20
    assert identifiers["num_heavy_atoms"] == 11


# ---------------------------------------------------------
# Test 7: Complete SMILES Processing & Standard Schema
# ---------------------------------------------------------

def test_process_smiles_complete():
    result = process_smiles(
        smiles="CC(=O)NC1=CC=C(O)C=C1",
        drug_id="CHEMBL112",
        name="Acetaminophen",
    )

    # Standard nested structure
    assert "drug" in result
    assert result["drug"]["drug_id"] == "CHEMBL112"
    assert result["drug"]["name"] == "Acetaminophen"
    assert result["drug"]["input_type"] == "smiles"

    assert "molecule" in result
    assert result["molecule"]["canonical_smiles"] == "CC(=O)Nc1ccc(O)cc1"
    assert result["molecule"]["inchi_key"] == "RZVAJINKPMORJF-UHFFFAOYSA-N"

    assert "descriptors" in result
    assert result["descriptors"]["molecular_weight"] == 151.165

    assert "fingerprint" in result
    assert result["fingerprint"]["size"] == 2048
    assert result["fingerprint"]["active_bits"] > 0
    assert len(result["fingerprint"]["bits"]) == 2048

    assert "status" in result
    assert result["status"]["valid"] is True

    # Backwards compatibility top-level fields
    assert result["valid"] is True
    assert result["canonical_smiles"] == "CC(=O)Nc1ccc(O)cc1"
    assert result["fingerprint_size"] == 2048
    assert result["active_fingerprint_bits"] > 0
    assert result["svg_image"] is not None
    assert "<svg" in result["svg_image"]


# ---------------------------------------------------------
# Test 8: SDF File Loading & Processing
# ---------------------------------------------------------

def test_load_sdf_file():
    demo_sdf = Path(__file__).resolve().parent.parent / "data" / "demo" / "aspirin.sdf"
    if demo_sdf.exists():
        mol = load_molecule_from_file(demo_sdf)
        assert mol is not None
        result = process_molecule(mol, input_type="sdf", input_value=demo_sdf.name)
        assert result["valid"] is True
        assert "descriptors" in result
        assert result["descriptors"]["molecular_weight"] > 170
        assert result["molecule"]["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"


# ---------------------------------------------------------
# Test 9: MOL File Loading & Processing
# ---------------------------------------------------------

def test_load_mol_file():
    demo_mol = Path(__file__).resolve().parent.parent / "data" / "demo" / "ibuprofen.mol"
    if demo_mol.exists():
        mol = load_molecule_from_file(demo_mol)
        assert mol is not None
        result = process_molecule(mol, input_type="mol", input_value=demo_mol.name)
        assert result["valid"] is True
        assert "descriptors" in result
        assert result["descriptors"]["molecular_weight"] > 200
        assert result["molecule"]["canonical_smiles"] == "CC(C)Cc1ccc(C(C)C(=O)O)cc1"


# ---------------------------------------------------------
# Test 10: 2D Image Rendering (PNG and SVG)
# ---------------------------------------------------------

def test_molecule_image_rendering():
    mol = validate_smiles("CCO")

    svg = render_molecule_svg(mol, width=200, height=200)
    assert isinstance(svg, str)
    assert "<svg" in svg
    assert "</svg>" in svg

    png_bytes = render_molecule_png(mol, width=200, height=200)
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 100
    # PNG signature check (first 8 bytes)
    assert png_bytes[:4] == b"\x89PNG"
