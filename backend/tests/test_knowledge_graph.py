import pytest

from app.knowledge_graph import (
    BiomedicalKnowledgeGraph,
    GraphNodeType,
    GraphRelationType,
    InMemoryGraphEngine,
    add_entity,
    add_relationship,
    build_drug_subgraph,
    find_mechanistic_paths,
    find_paths,
    get_evidence_for_relationship,
    get_neighbors,
    search_graph,
)


# ---------------------------------------------------------
# 1. In-Memory Graph Engine Unit Tests
# ---------------------------------------------------------

def test_engine_node_and_edge_creation():
    engine = InMemoryGraphEngine()

    # Add nodes
    n1 = engine.add_node("DRUG:1", "Compound A", "Drug", {"mw": 200.0})
    n2 = engine.add_node("TARGET:1", "Receptor X", "Target", {"family": "GPCR"})

    assert engine.has_node("DRUG:1")
    assert engine.has_node("TARGET:1")
    assert n1.name == "Compound A"
    assert n2.properties["family"] == "GPCR"

    # Add edge
    e = engine.add_edge(
        source="DRUG:1",
        target="TARGET:1",
        relation="BINDS_TO",
        confidence=0.88,
        source_db="ChEMBL",
        evidence_type="bioassay",
        provenance_id="ASSAY_123",
    )

    assert e.source == "DRUG:1"
    assert e.target == "TARGET:1"
    assert e.relation == "BINDS_TO"
    assert e.confidence == 0.88
    assert e.source_db == "ChEMBL"
    assert e.provenance_id == "ASSAY_123"


def test_engine_duplicate_node_and_edge_handling():
    engine = InMemoryGraphEngine()

    # Add node and update properties
    engine.add_node("NODE:1", "Old Name", "Drug", {"key1": "val1"})
    engine.add_node("NODE:1", "New Name", "Drug", {"key2": "val2"})

    node = engine.get_node("NODE:1")
    assert node.name == "New Name"
    assert node.properties["key1"] == "val1"
    assert node.properties["key2"] == "val2"
    assert len(engine.nodes) == 1


def test_engine_path_finding_dfs():
    engine = InMemoryGraphEngine()

    # Chain: A -> B -> C -> D
    engine.add_edge("A", "B", "REL_1", confidence=0.9)
    engine.add_edge("B", "C", "REL_2", confidence=0.8)
    engine.add_edge("C", "D", "REL_3", confidence=0.7)

    # Alternative direct path: A -> D
    engine.add_edge("A", "D", "REL_DIRECT", confidence=0.95)

    paths = engine.find_all_paths("A", "D", max_length=5)
    assert len(paths) == 2

    # Check that A -> D direct path is length 1 and multi-hop is length 3
    lengths = [len(p) for p in paths]
    assert 1 in lengths
    assert 3 in lengths


def test_engine_empty_and_missing_lookups():
    engine = InMemoryGraphEngine()
    assert not engine.has_node("NONEXISTENT")
    assert engine.get_node("NONEXISTENT") is None
    assert engine.get_neighbors("NONEXISTENT") == []
    assert engine.find_all_paths("NONEXISTENT", "ANOTHER") == []
    nodes, edges = engine.subgraph_for_node("NONEXISTENT")
    assert nodes == []
    assert edges == []


# ---------------------------------------------------------
# 2. High-Level Knowledge Graph API Tests
# ---------------------------------------------------------

def test_kg_add_entity_and_relationship():
    kg = BiomedicalKnowledgeGraph()
    n = kg.add_entity("TEST:COMPOUND", GraphNodeType.DRUG, "Test Molecule", {"smiles": "CC"})
    assert n.id == "TEST:COMPOUND"
    assert n.type == "Drug"

    e = kg.add_relationship(
        source_id="TEST:COMPOUND",
        target_id="ORGAN:LIVER",
        relation_type=GraphRelationType.AFFECTS_ORGAN,
        confidence=0.75,
        source="SIDER",
    )
    assert e.source == "TEST:COMPOUND"
    assert e.target == "ORGAN:LIVER"
    assert e.confidence == 0.75

    # Retrieve evidence for relationship
    ev_list = kg.get_evidence_for_relationship("TEST:COMPOUND", "ORGAN:LIVER")
    assert len(ev_list) >= 1
    assert ev_list[0]["source_db"] == "SIDER"


def test_kg_get_neighbors():
    kg = BiomedicalKnowledgeGraph()
    nbrs = kg.get_neighbors("CHEMBL:CHEMBL112", direction="out")
    assert len(nbrs) >= 3

    # Ensure relations exist
    rel_types = {nbr["relation"] for nbr in nbrs}
    assert "INHIBITS" in rel_types or "METABOLIZED_BY" in rel_types


# ---------------------------------------------------------
# 3. Seeded Benchmark Knowledge Graph & Path Reasoning
# ---------------------------------------------------------

def test_acetaminophen_mechanistic_paths_to_liver():
    paths = find_mechanistic_paths("CHEMBL:CHEMBL112")
    assert len(paths) >= 2

    # Check for multi-hop mechanistic path:
    # Acetaminophen -> CYP2E1 -> NAPQI pathway -> Hepatocytes -> Liver
    mechanistic_path = next(
        (p for p in paths if any("NAPQI" in str(name) for name in p.node_names)), None
    )
    assert mechanistic_path is not None
    assert mechanistic_path.target_organ == "Liver"
    assert mechanistic_path.confidence > 0.60
    assert len(mechanistic_path.nodes) >= 4

    # Check for AdverseEffect path:
    # Acetaminophen -> Hepatotoxicity -> Liver
    adverse_path = next(
        (p for p in paths if any("Hepatotoxicity" in str(name) for name in p.node_names)), None
    )
    assert adverse_path is not None
    assert adverse_path.target_organ == "Liver"


def test_doxorubicin_cardiotoxicity_path_to_heart():
    paths = find_mechanistic_paths("CHEMBL:CHEMBL53")
    assert len(paths) >= 2

    # Path to Heart
    heart_paths = [p for p in paths if p.target_organ == "Heart"]
    assert len(heart_paths) >= 2

    # Check TOP2B & Cardiomyocytes chain
    top2b_path = next(
        (p for p in heart_paths if any("TOP2B" in str(name) for name in p.node_names)), None
    )
    assert top2b_path is not None
    assert top2b_path.confidence > 0.70


def test_aspirin_path_to_gastrointestinal():
    paths = find_mechanistic_paths("CHEMBL:CHEMBL25")
    assert len(paths) >= 2

    gi_paths = [p for p in paths if p.target_organ == "Gastrointestinal Tract"]
    assert len(gi_paths) >= 2

    # Check Gastric Ulceration adverse path
    ulcer_path = next(
        (p for p in gi_paths if any("Gastric Ulceration" in str(name) for name in p.node_names)), None
    )
    assert ulcer_path is not None


def test_ibuprofen_path_to_kidney():
    paths = find_mechanistic_paths("CHEMBL:CHEMBL521")
    assert len(paths) >= 1

    kidney_paths = [p for p in paths if p.target_organ == "Kidney"]
    assert len(kidney_paths) >= 1

    # Check renal impairment
    renal_path = next(
        (p for p in kidney_paths if any("Renal" in str(name) for name in p.node_names)), None
    )
    assert renal_path is not None


# ---------------------------------------------------------
# 4. Subgraph Construction & Provenance
# ---------------------------------------------------------

def test_build_drug_subgraph_acetaminophen():
    subgraph = build_drug_subgraph("CHEMBL:CHEMBL112", depth=4, max_nodes=50)

    assert subgraph["drug_id"] == "CHEMBL:CHEMBL112"
    assert subgraph["drug_name"] == "Acetaminophen"
    assert subgraph["total_nodes"] >= 8
    assert subgraph["total_edges"] >= 8
    assert len(subgraph["paths"]) >= 2
    assert "ChEMBL" in subgraph["evidence_sources"]
    assert "UniProt" in subgraph["evidence_sources"]
    assert "SIDER" in subgraph["evidence_sources"]

    # Verify node types present
    node_types = {n["type"] for n in subgraph["nodes"]}
    assert "Drug" in node_types
    assert "Target" in node_types
    assert "Protein" in node_types
    assert "Pathway" in node_types
    assert "Organ" in node_types
    assert "AdverseEffect" in node_types


def test_build_drug_subgraph_unknown_drug():
    subgraph = build_drug_subgraph("CHEMBL:UNKNOWN_999")
    assert subgraph["total_nodes"] == 0
    assert subgraph["total_edges"] == 0
    assert subgraph["nodes"] == []
    assert subgraph["paths"] == []
    assert subgraph["status"]["valid"] is True


# ---------------------------------------------------------
# 5. Graph Search Functionality
# ---------------------------------------------------------

def test_search_graph_by_keyword():
    res = search_graph(query="Liver")
    assert res["total_results"] >= 1
    assert any(item["name"] == "Liver" for item in res["results"])

    # Search with entity_type filter
    res_organ = search_graph(query="Liver", entity_type="Organ")
    assert len(res_organ["results"]) >= 1
    assert res_organ["results"][0]["type"] == "Organ"

    # Search for gene
    res_gene = search_graph(query="CYP2E1", entity_type="Gene")
    assert len(res_gene["results"]) >= 1
    assert res_gene["results"][0]["name"] == "CYP2E1"
