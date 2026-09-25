"""
Biomedical Knowledge Graph Engine & Reasoning Layer (Phase 3)

Components:
- Explicit Node & Relationship Ontology
- In-Memory Graph Engine (with Neo4j fallback compatibility)
- Graph Builder & Multi-Hop Path Extractor
- Multi-Source Provenance & Evidence Weighting
- Frontend-Ready Visualization Exporter
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import settings
from app.data_ingestion import resolve_drug_identifier
from app.schemas import (
    GraphEdgeModel,
    GraphNodeModel,
    GraphPathModel,
    GraphPathsResponse,
    GraphSearchResultItem,
    GraphSearchResponse,
    GraphSubgraphResponse,
    ProcessingStatus,
)


def get_iso_now() -> str:
    """Returns current UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------
# 1. Graph Ontology: Node & Relationship Types
# ---------------------------------------------------------

class GraphNodeType(str, Enum):
    DRUG = "Drug"
    TARGET = "Target"
    PROTEIN = "Protein"
    GENE = "Gene"
    PATHWAY = "Pathway"
    TISSUE = "Tissue"
    ORGAN = "Organ"
    ADVERSE_EFFECT = "AdverseEffect"
    DISEASE = "Disease"
    LITERATURE = "Literature"


class GraphRelationType(str, Enum):
    TARGETS = "TARGETS"
    INHIBITS = "INHIBITS"
    ACTIVATES = "ACTIVATES"
    BINDS_TO = "BINDS_TO"
    ENCODED_BY = "ENCODED_BY"
    METABOLIZED_BY = "METABOLIZED_BY"
    PARTICIPATES_IN_PATHWAY = "PARTICIPATES_IN_PATHWAY"
    ACTIVE_IN_TISSUE = "ACTIVE_IN_TISSUE"
    EXPRESSED_IN = "EXPRESSED_IN"
    PART_OF_ORGAN = "PART_OF_ORGAN"
    AFFECTS_ORGAN = "AFFECTS_ORGAN"
    ASSOCIATED_WITH_ADVERSE_EFFECT = "ASSOCIATED_WITH_ADVERSE_EFFECT"
    SUPPORTS_RELATIONSHIP = "SUPPORTS_RELATIONSHIP"
    TREATS_DISEASE = "TREATS_DISEASE"


# ---------------------------------------------------------
# 2. In-Memory Graph Data Structures
# ---------------------------------------------------------

class GraphNode:
    """Internal node representation."""
    def __init__(self, node_id: str, name: str, node_type: str, properties: Optional[Dict[str, Any]] = None):
        self.id = node_id.strip()
        self.name = name.strip()
        self.type = node_type
        self.properties = properties or {}

    def to_model(self) -> GraphNodeModel:
        return GraphNodeModel(
            id=self.id,
            name=self.name,
            type=self.type,
            properties=self.properties,
        )


class GraphEdge:
    """Internal edge representation with provenance and confidence."""
    def __init__(
        self,
        source: str,
        target: str,
        relation: str,
        confidence: float = 1.0,
        source_db: str = "KnowledgeGraph",
        evidence_type: str = "curated_graph",
        provenance_id: Optional[str] = None,
        retrieved_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None,
    ):
        self.source = source.strip()
        self.target = target.strip()
        self.relation = relation.strip().upper()
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.source_db = source_db
        self.evidence_type = evidence_type
        self.provenance_id = provenance_id
        self.retrieved_at = retrieved_at or get_iso_now()
        self.metadata = metadata or {}
        self.id = edge_id or f"{self.source}->{self.relation}->{self.target}"

    def to_model(self) -> GraphEdgeModel:
        return GraphEdgeModel(
            id=self.id,
            source=self.source,
            target=self.target,
            relation=self.relation,
            confidence=self.confidence,
            source_db=self.source_db,
            evidence_type=self.evidence_type,
            provenance_id=self.provenance_id,
            retrieved_at=self.retrieved_at,
            metadata=self.metadata,
        )


# ---------------------------------------------------------
# 3. Graph Engine (In-Memory with Neo4j Fallback Compatibility)
# ---------------------------------------------------------

class InMemoryGraphEngine:
    """
    High-performance pure-Python directed graph engine providing
    adjacency indexing, multi-hop path reasoning, and neighborhood expansion.
    """

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.adj_out: Dict[str, Dict[str, List[GraphEdge]]] = {}
        self.adj_in: Dict[str, Dict[str, List[GraphEdge]]] = {}
        self.edges_by_id: Dict[str, GraphEdge] = {}

    def clear(self) -> None:
        """Clears all nodes and edges from the graph."""
        self.nodes.clear()
        self.adj_out.clear()
        self.adj_in.clear()
        self.edges_by_id.clear()

    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> GraphNode:
        """Adds or updates a node in the graph."""
        node_id = node_id.strip()
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.name = name
            node.type = node_type
            if properties:
                node.properties.update(properties)
            return node

        node = GraphNode(node_id, name, node_type, properties)
        self.nodes[node_id] = node
        self.adj_out[node_id] = {}
        self.adj_in[node_id] = {}
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        confidence: float = 1.0,
        source_db: str = "KnowledgeGraph",
        evidence_type: str = "curated_graph",
        provenance_id: Optional[str] = None,
        retrieved_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None,
    ) -> GraphEdge:
        """Adds a directed relationship between two entities."""
        source = source.strip()
        target = target.strip()
        relation = relation.strip().upper()

        if source not in self.nodes:
            self.add_node(source, source, "Unknown")
        if target not in self.nodes:
            self.add_node(target, target, "Unknown")

        edge = GraphEdge(
            source=source,
            target=target,
            relation=relation,
            confidence=confidence,
            source_db=source_db,
            evidence_type=evidence_type,
            provenance_id=provenance_id,
            retrieved_at=retrieved_at,
            metadata=metadata,
            edge_id=edge_id,
        )

        # Update adjacency structures
        if target not in self.adj_out[source]:
            self.adj_out[source][target] = []
        self.adj_out[source][target].append(edge)

        if source not in self.adj_in[target]:
            self.adj_in[target][source] = []
        self.adj_in[target][source].append(edge)

        self.edges_by_id[edge.id] = edge
        return edge

    def has_node(self, node_id: str) -> bool:
        return node_id.strip() in self.nodes

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id.strip())

    def get_neighbors(
        self, node_id: str, direction: str = "out"
    ) -> List[Tuple[str, str, GraphEdge]]:
        """
        Returns list of (neighbor_id, relation, edge) tuples.
        direction can be 'out', 'in', or 'both'.
        """
        node_id = node_id.strip()
        if node_id not in self.nodes:
            return []

        results: List[Tuple[str, str, GraphEdge]] = []
        if direction in ("out", "both"):
            for neighbor, edges in self.adj_out.get(node_id, {}).items():
                for edge in edges:
                    results.append((neighbor, edge.relation, edge))

        if direction in ("in", "both"):
            for neighbor, edges in self.adj_in.get(node_id, {}).items():
                for edge in edges:
                    results.append((neighbor, edge.relation, edge))

        return results

    def get_edges_between(
        self, source_id: str, target_id: str, relation: Optional[str] = None
    ) -> List[GraphEdge]:
        """Retrieves edges between two nodes matching optional relation filter."""
        source_id = source_id.strip()
        target_id = target_id.strip()
        edges = self.adj_out.get(source_id, {}).get(target_id, [])
        if relation:
            rel_upper = relation.strip().upper()
            return [e for e in edges if e.relation == rel_upper]
        return edges

    def find_all_paths(
        self, source_id: str, target_id: str, max_length: int = 5
    ) -> List[List[Tuple[str, GraphEdge, str]]]:
        """
        Finds all simple directed paths between source and target up to max_length edges.
        Returns list of paths where each path is a list of (u, edge, v) transitions.
        """
        source_id = source_id.strip()
        target_id = target_id.strip()

        if source_id not in self.nodes or target_id not in self.nodes:
            return []

        all_paths: List[List[Tuple[str, GraphEdge, str]]] = []

        def dfs(current: str, visited: Set[str], current_path: List[Tuple[str, GraphEdge, str]]):
            if len(current_path) > max_length:
                return
            if current == target_id:
                all_paths.append(list(current_path))
                return

            for neighbor, edges in self.adj_out.get(current, {}).items():
                if neighbor not in visited:
                    visited.add(neighbor)
                    for edge in edges:
                        current_path.append((current, edge, neighbor))
                        dfs(neighbor, visited, current_path)
                        current_path.pop()
                    visited.remove(neighbor)

        dfs(source_id, {source_id}, [])
        return all_paths

    def subgraph_for_node(
        self, start_node: str, depth: int = 3, max_nodes: int = 100
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Performs BFS exploration from start_node up to given depth,
        returning collected nodes and interconnecting edges.
        """
        start_node = start_node.strip()
        if start_node not in self.nodes:
            return [], []

        visited_nodes: Set[str] = {start_node}
        queue = deque([(start_node, 0)])

        while queue and len(visited_nodes) < max_nodes:
            curr, d = queue.popleft()
            if d >= depth:
                continue

            # Follow outgoing edges
            for nbr in self.adj_out.get(curr, {}):
                if nbr not in visited_nodes and len(visited_nodes) < max_nodes:
                    visited_nodes.add(nbr)
                    queue.append((nbr, d + 1))

            # Follow incoming edges for context (e.g. Literature supporting nodes)
            for nbr in self.adj_in.get(curr, {}):
                if nbr not in visited_nodes and len(visited_nodes) < max_nodes:
                    visited_nodes.add(nbr)
                    queue.append((nbr, d + 1))

        # Collect interconnecting edges
        collected_edges: List[GraphEdge] = []
        seen_edge_ids: Set[str] = set()

        for u in visited_nodes:
            for v, edges in self.adj_out.get(u, {}).items():
                if v in visited_nodes:
                    for e in edges:
                        if e.id not in seen_edge_ids:
                            seen_edge_ids.add(e.id)
                            collected_edges.append(e)

        collected_nodes = [self.nodes[n] for n in visited_nodes]
        return collected_nodes, collected_edges

    def search(
        self, query: str, entity_type: Optional[str] = None, limit: int = 20
    ) -> List[GraphSearchResultItem]:
        """Searches graph nodes by text match on ID, name, or properties."""
        q_lower = query.strip().lower()
        results: List[GraphSearchResultItem] = []

        for node in self.nodes.values():
            if entity_type and node.type.lower() != entity_type.strip().lower():
                continue

            matches = (
                q_lower in node.id.lower()
                or q_lower in node.name.lower()
                or any(q_lower in str(v).lower() for v in node.properties.values())
            )
            if matches:
                out_degree = len(self.adj_out.get(node.id, {}))
                in_degree = len(self.adj_in.get(node.id, {}))
                results.append(
                    GraphSearchResultItem(
                        id=node.id,
                        name=node.name,
                        type=node.type,
                        degree=out_degree + in_degree,
                        properties=node.properties,
                    )
                )
                if len(results) >= limit:
                    break

        return results


# ---------------------------------------------------------
# 4. Biomedical Knowledge Graph & Path Reasoner
# ---------------------------------------------------------

class BiomedicalKnowledgeGraph:
    """
    High-level Biomedical Knowledge Graph interface.
    Manages ontology registration, seeding, multi-hop mechanistic path reasoning,
    and transparent evidence-weight calculations.
    """

    def __init__(self):
        self.engine = InMemoryGraphEngine()
        self._seeded = False
        self.seed_graph_from_curated_data()

    def add_entity(
        self,
        node_id: str,
        node_type: str | GraphNodeType,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> GraphNodeModel:
        """Adds a standardized biomedical entity node."""
        type_str = node_type.value if isinstance(node_type, GraphNodeType) else str(node_type)
        node = self.engine.add_node(node_id, name, type_str, properties)
        return node.to_model()

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str | GraphRelationType,
        confidence: float = 1.0,
        source: str = "KnowledgeGraph",
        evidence_type: str = "curated_graph",
        provenance_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphEdgeModel:
        """Adds a directed relationship between two entities."""
        rel_str = relation_type.value if isinstance(relation_type, GraphRelationType) else str(relation_type)
        edge = self.engine.add_edge(
            source=source_id,
            target=target_id,
            relation=rel_str,
            confidence=confidence,
            source_db=source,
            evidence_type=evidence_type,
            provenance_id=provenance_id,
            metadata=metadata,
        )
        return edge.to_model()

    def get_neighbors(
        self, node_id: str, direction: str = "out"
    ) -> List[Dict[str, Any]]:
        """Returns direct neighbors for a node."""
        raw_nbrs = self.engine.get_neighbors(node_id, direction)
        return [
            {
                "neighbor_id": nbr_id,
                "relation": rel,
                "edge": edge.to_model().model_dump(),
                "node": self.engine.get_node(nbr_id).to_model().model_dump()
                if self.engine.has_node(nbr_id)
                else None,
            }
            for nbr_id, rel, edge in raw_nbrs
        ]

    def find_paths(
        self, source_id: str, target_id: str, max_length: int = 5
    ) -> List[GraphPathModel]:
        """Finds directed reasoning paths between two entities."""
        raw_paths = self.engine.find_all_paths(source_id, target_id, max_length)
        path_models: List[GraphPathModel] = []

        for idx, path in enumerate(raw_paths):
            nodes = [path[0][0]] + [transition[2] for transition in path]
            node_names = [
                self.engine.get_node(n).name if self.engine.has_node(n) else n
                for n in nodes
            ]
            relations = [transition[1].relation for transition in path]

            # Transparent evidence-strength confidence calculation
            path_conf = 1.0
            for transition in path:
                path_conf *= transition[1].confidence
            path_conf = round(path_conf, 4)

            tier = "high" if path_conf >= 0.75 else ("moderate" if path_conf >= 0.50 else "low")
            desc = " -> ".join(
                f"{node_names[i]} [{relations[i]}]" for i in range(len(relations))
            ) + f" -> {node_names[-1]}"

            target_organ = node_names[-1] if self.engine.get_node(nodes[-1]) and self.engine.get_node(nodes[-1]).type == "Organ" else None

            path_models.append(
                GraphPathModel(
                    path_id=f"path_{source_id}_{target_id}_{idx+1}",
                    path_type="mechanistic_organ_path" if target_organ else "entity_path",
                    target_organ=target_organ,
                    nodes=nodes,
                    node_names=node_names,
                    relations=relations,
                    confidence=path_conf,
                    confidence_tier=tier,
                    description=desc,
                )
            )

        return path_models

    def find_mechanistic_paths(
        self, drug_id: str, target_organ: Optional[str] = None
    ) -> List[GraphPathModel]:
        """
        Explores candidate mechanistic chains connecting the drug to target organs:
        - Mechanistic Pathway Chain: Drug -> Target -> Gene -> Pathway -> Tissue -> Organ
        - Adverse Phenotype Chain: Drug -> AdverseEffect -> Organ
        """
        resolved_key = resolve_drug_identifier(drug_id)
        clean_drug_id = f"CHEMBL:{resolved_key}" if resolved_key and not resolved_key.startswith("CHEMBL:") else (
            drug_id if drug_id.startswith("CHEMBL:") else f"CHEMBL:{drug_id.strip().upper()}"
        )

        all_paths: List[GraphPathModel] = []

        # Find all organ nodes in the graph
        organ_nodes = [
            n for n in self.engine.nodes.values()
            if n.type == GraphNodeType.ORGAN.value
        ]

        for organ in organ_nodes:
            if target_organ and target_organ.strip().lower() not in organ.name.lower():
                continue
            paths_to_organ = self.find_paths(clean_drug_id, organ.id, max_length=5)
            all_paths.extend(paths_to_organ)

        # Sort paths by confidence descending
        all_paths.sort(key=lambda p: p.confidence, reverse=True)
        return all_paths

    def build_drug_subgraph(
        self, drug_id: str, depth: int = 3, max_nodes: int = 100
    ) -> Dict[str, Any]:
        """
        Constructs a complete frontend-ready subgraph for visualization and reasoning:
        - Nodes list with types and labels
        - Directed edges with confidence and database provenance
        - Candidate multi-hop reasoning paths
        """
        resolved_key = resolve_drug_identifier(drug_id)
        target_key = resolved_key or drug_id.strip().upper()
        clean_drug_id = f"CHEMBL:{target_key}" if not target_key.startswith("CHEMBL:") else target_key

        if not self.engine.has_node(clean_drug_id):
            # Try plain target_key
            if self.engine.has_node(target_key):
                clean_drug_id = target_key

        if not self.engine.has_node(clean_drug_id):
            return {
                "drug_id": drug_id,
                "drug_name": None,
                "canonical_smiles": None,
                "engine": "InMemoryGraph",
                "total_nodes": 0,
                "total_edges": 0,
                "nodes": [],
                "edges": [],
                "paths": [],
                "evidence_sources": [],
                "status": ProcessingStatus(
                    valid=True,
                    message=f"No knowledge subgraph found for '{drug_id}'. Try demo drugs: CHEMBL112, CHEMBL25, CHEMBL521, CHEMBL53.",
                ).model_dump(),
            }

        nodes, edges = self.engine.subgraph_for_node(clean_drug_id, depth=depth, max_nodes=max_nodes)
        node_models = [n.to_model() for n in nodes]
        edge_models = [e.to_model() for e in edges]

        # Extract mechanistic reasoning paths
        paths = self.find_mechanistic_paths(clean_drug_id)

        evidence_sources = list(set(e.source_db for e in edge_models))
        drug_node = self.engine.get_node(clean_drug_id)
        drug_name = drug_node.name if drug_node else None
        canonical_smiles = drug_node.properties.get("canonical_smiles") if drug_node else None

        return {
            "drug_id": clean_drug_id,
            "drug_name": drug_name,
            "canonical_smiles": canonical_smiles,
            "engine": "InMemoryGraph",
            "total_nodes": len(node_models),
            "total_edges": len(edge_models),
            "nodes": [n.model_dump() for n in node_models],
            "edges": [e.model_dump() for e in edge_models],
            "paths": [p.model_dump() for p in paths],
            "evidence_sources": evidence_sources,
            "status": ProcessingStatus(
                valid=True,
                message=f"Extracted subgraph with {len(node_models)} nodes, {len(edge_models)} edges, and {len(paths)} reasoning paths.",
            ).model_dump(),
        }

    def get_evidence_for_relationship(
        self, source_id: str, target_id: str, relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves provenance and evidence records for a specific relationship."""
        edges = self.engine.get_edges_between(source_id, target_id, relation_type)
        return [e.to_model().model_dump() for e in edges]

    def search_entities(
        self, query: str, entity_type: Optional[str] = None, limit: int = 20
    ) -> Dict[str, Any]:
        """Searches graph entities by name or identifier."""
        results = self.engine.search(query, entity_type, limit)
        return {
            "query": query,
            "entity_type": entity_type,
            "total_results": len(results),
            "results": [r.model_dump() for r in results],
            "status": ProcessingStatus(
                valid=True,
                message=f"Found {len(results)} matching entities.",
            ).model_dump(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns total counts and distribution of nodes and edges."""
        type_counts: Dict[str, int] = {}
        for n in self.engine.nodes.values():
            type_counts[n.type] = type_counts.get(n.type, 0) + 1

        rel_counts: Dict[str, int] = {}
        for e in self.engine.edges_by_id.values():
            rel_counts[e.relation] = rel_counts.get(e.relation, 0) + 1

        return {
            "total_nodes": len(self.engine.nodes),
            "total_edges": len(self.engine.edges_by_id),
            "node_types": type_counts,
            "relationship_types": rel_counts,
        }

    # ---------------------------------------------------------
    # 5. Seed Benchmark Knowledge Graph
    # ---------------------------------------------------------

    def seed_graph_from_curated_data(self) -> None:
        """
        Populates the knowledge graph with authentic multi-hop biomedical chains
        for benchmark drugs: Acetaminophen, Aspirin, Ibuprofen, Doxorubicin.
        """
        if self._seeded:
            return

        # -----------------------------------------------------
        # Shared Anatomical Organs & Tissues
        # -----------------------------------------------------
        self.add_entity("ORGAN:LIVER", GraphNodeType.ORGAN, "Liver", {"system": "Hepatic"})
        self.add_entity("ORGAN:GASTROINTESTINAL", GraphNodeType.ORGAN, "Gastrointestinal Tract", {"system": "Digestive"})
        self.add_entity("ORGAN:KIDNEY", GraphNodeType.ORGAN, "Kidney", {"system": "Renal"})
        self.add_entity("ORGAN:HEART", GraphNodeType.ORGAN, "Heart", {"system": "Cardiovascular"})

        self.add_entity("TISSUE:HEPATOCYTES", GraphNodeType.TISSUE, "Hepatocytes", {"organ": "Liver"})
        self.add_relationship("TISSUE:HEPATOCYTES", "ORGAN:LIVER", GraphRelationType.PART_OF_ORGAN, 1.0, "UniProt", "anatomical_ontology")

        self.add_entity("TISSUE:GASTRIC_MUCOSA", GraphNodeType.TISSUE, "Gastric Mucosa", {"organ": "Gastrointestinal"})
        self.add_relationship("TISSUE:GASTRIC_MUCOSA", "ORGAN:GASTROINTESTINAL", GraphRelationType.PART_OF_ORGAN, 1.0, "UniProt", "anatomical_ontology")

        self.add_entity("TISSUE:RENAL_GLOMERULUS", GraphNodeType.TISSUE, "Renal Glomerulus & Tubules", {"organ": "Kidney"})
        self.add_relationship("TISSUE:RENAL_GLOMERULUS", "ORGAN:KIDNEY", GraphRelationType.PART_OF_ORGAN, 1.0, "UniProt", "anatomical_ontology")

        self.add_entity("TISSUE:CARDIOMYOCYTES", GraphNodeType.TISSUE, "Cardiomyocytes", {"organ": "Heart"})
        self.add_relationship("TISSUE:CARDIOMYOCYTES", "ORGAN:HEART", GraphRelationType.PART_OF_ORGAN, 1.0, "UniProt", "anatomical_ontology")

        # -----------------------------------------------------
        # DRUG 1: Acetaminophen (Paracetamol) CHEMBL112
        # -----------------------------------------------------
        drug_apap = "CHEMBL:CHEMBL112"
        self.add_entity(drug_apap, GraphNodeType.DRUG, "Acetaminophen", {
            "chembl_id": "CHEMBL112",
            "pubchem_cid": "1983",
            "canonical_smiles": "CC(=O)Nc1ccc(O)cc1",
            "formula": "C8H9NO2",
        })

        # Targets & Enzymes
        self.add_entity("CHEMBL:CHEMBL221", GraphNodeType.TARGET, "Prostaglandin G/H synthase 1 (PTGS1 / COX-1)", {"organism": "Homo sapiens"})
        self.add_entity("CHEMBL:CHEMBL230", GraphNodeType.TARGET, "Prostaglandin G/H synthase 2 (PTGS2 / COX-2)", {"organism": "Homo sapiens"})
        self.add_entity("UNIPROT:P20813", GraphNodeType.PROTEIN, "Cytochrome P450 2E1 (CYP2E1)", {"gene": "CYP2E1"})
        self.add_entity("GENE:CYP2E1", GraphNodeType.GENE, "CYP2E1", {"chromosome": "10q26.3"})

        self.add_relationship(drug_apap, "CHEMBL:CHEMBL221", GraphRelationType.INHIBITS, 0.85, "ChEMBL", "bioassay", "CHEMBL221_IC50_26uM")
        self.add_relationship(drug_apap, "CHEMBL:CHEMBL230", GraphRelationType.INHIBITS, 0.88, "ChEMBL", "bioassay", "CHEMBL230_IC50_50uM")
        self.add_relationship(drug_apap, "UNIPROT:P20813", GraphRelationType.METABOLIZED_BY, 0.95, "UniProt", "metabolic_pathway", "UNIPROT_P20813")
        self.add_relationship("UNIPROT:P20813", "GENE:CYP2E1", GraphRelationType.ENCODED_BY, 1.0, "UniProt", "genomic_annotation")

        # Pathway: NAPQI Bioactivation
        self.add_entity("PATHWAY:NAPQI_HEPATOTOX", GraphNodeType.PATHWAY, "NAPQI Bioactivation & Glutathione Depletion", {
            "reactome_id": "REACT_71",
            "mechanism": "NAPQI covalent binding to mitochondrial proteins drives hepatocyte oxidative stress",
        })
        self.add_relationship("GENE:CYP2E1", "PATHWAY:NAPQI_HEPATOTOX", GraphRelationType.PARTICIPATES_IN_PATHWAY, 0.94, "OpenTargets", "pathway_enrichment")
        self.add_relationship("PATHWAY:NAPQI_HEPATOTOX", "TISSUE:HEPATOCYTES", GraphRelationType.ACTIVE_IN_TISSUE, 0.96, "UniProt", "tissue_expression")

        # Adverse Effects
        self.add_entity("SIDER:UMLS:C0019202", GraphNodeType.ADVERSE_EFFECT, "Hepatotoxicity", {"meddra_id": "10019805"})
        self.add_entity("SIDER:UMLS:C0162557", GraphNodeType.ADVERSE_EFFECT, "Acute Hepatic Failure", {"meddra_id": "10000804"})
        self.add_relationship(drug_apap, "SIDER:UMLS:C0019202", GraphRelationType.ASSOCIATED_WITH_ADVERSE_EFFECT, 0.96, "SIDER", "clinical_side_effect")
        self.add_relationship(drug_apap, "SIDER:UMLS:C0162557", GraphRelationType.ASSOCIATED_WITH_ADVERSE_EFFECT, 0.91, "SIDER", "clinical_side_effect")
        self.add_relationship("SIDER:UMLS:C0019202", "ORGAN:LIVER", GraphRelationType.AFFECTS_ORGAN, 1.0, "SIDER", "organ_mapping")
        self.add_relationship("SIDER:UMLS:C0162557", "ORGAN:LIVER", GraphRelationType.AFFECTS_ORGAN, 1.0, "SIDER", "organ_mapping")

        # Literature
        self.add_entity("PMID:15214041", GraphNodeType.LITERATURE, "Acetaminophen-induced hepatotoxicity mechanisms", {"journal": "J Hepatol", "year": 2004})
        self.add_relationship("PMID:15214041", "PATHWAY:NAPQI_HEPATOTOX", GraphRelationType.SUPPORTS_RELATIONSHIP, 0.95, "PubMed", "peer_reviewed_literature", "PMID:15214041")

        # -----------------------------------------------------
        # DRUG 2: Aspirin CHEMBL25
        # -----------------------------------------------------
        drug_asa = "CHEMBL:CHEMBL25"
        self.add_entity(drug_asa, GraphNodeType.DRUG, "Aspirin", {
            "chembl_id": "CHEMBL25",
            "pubchem_cid": "2244",
            "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "formula": "C9H8O4",
        })

        self.add_entity("GENE:PTGS1", GraphNodeType.GENE, "PTGS1", {"chromosome": "9q34.3"})
        self.add_relationship(drug_asa, "CHEMBL:CHEMBL221", GraphRelationType.INHIBITS, 0.98, "ChEMBL", "bioassay", "Ser529_Acetylation")
        self.add_relationship(drug_asa, "CHEMBL:CHEMBL230", GraphRelationType.INHIBITS, 0.92, "ChEMBL", "bioassay", "Ser516_Acetylation")
        self.add_relationship("CHEMBL:CHEMBL221", "GENE:PTGS1", GraphRelationType.ENCODED_BY, 1.0, "UniProt", "genomic_annotation")

        self.add_entity("PATHWAY:GASTRIC_PGE2", GraphNodeType.PATHWAY, "Gastric Mucosal Cytoprotective Prostaglandin Synthesis", {
            "function": "Maintains mucosal blood flow and bicarbonate secretion",
        })
        self.add_relationship("GENE:PTGS1", "PATHWAY:GASTRIC_PGE2", GraphRelationType.PARTICIPATES_IN_PATHWAY, 0.95, "OpenTargets", "pathway_enrichment")
        self.add_relationship("PATHWAY:GASTRIC_PGE2", "TISSUE:GASTRIC_MUCOSA", GraphRelationType.ACTIVE_IN_TISSUE, 0.95, "UniProt", "tissue_expression")

        self.add_entity("SIDER:UMLS:C0038358", GraphNodeType.ADVERSE_EFFECT, "Gastric Ulceration", {"meddra_id": "10017772"})
        self.add_entity("SIDER:UMLS:C0017181", GraphNodeType.ADVERSE_EFFECT, "Gastrointestinal Hemorrhage", {"meddra_id": "10017955"})
        self.add_relationship(drug_asa, "SIDER:UMLS:C0038358", GraphRelationType.ASSOCIATED_WITH_ADVERSE_EFFECT, 0.93, "SIDER", "clinical_side_effect")
        self.add_relationship(drug_asa, "SIDER:UMLS:C0017181", GraphRelationType.ASSOCIATED_WITH_ADVERSE_EFFECT, 0.89, "SIDER", "clinical_side_effect")
        self.add_relationship("SIDER:UMLS:C0038358", "ORGAN:GASTROINTESTINAL", GraphRelationType.AFFECTS_ORGAN, 1.0, "SIDER", "organ_mapping")
        self.add_relationship("SIDER:UMLS:C0017181", "ORGAN:GASTROINTESTINAL", GraphRelationType.AFFECTS_ORGAN, 1.0, "SIDER", "organ_mapping")

        self.add_entity("PMID:12437648", GraphNodeType.LITERATURE, "COX-1/COX-2 inhibitors and GI injury mechanisms", {"journal": "Gastroenterology", "year": 2002})
        self.add_relationship("PMID:12437648", "CHEMBL:CHEMBL221", GraphRelationType.SUPPORTS_RELATIONSHIP, 0.94, "PubMed", "peer_reviewed_literature", "PMID:12437648")

        # -----------------------------------------------------
        # DRUG 3: Ibuprofen CHEMBL521
        # -----------------------------------------------------
        drug_ibu = "CHEMBL:CHEMBL521"
        self.add_entity(drug_ibu, GraphNodeType.DRUG, "Ibuprofen", {
            "chembl_id": "CHEMBL521",
            "pubchem_cid": "3672",
            "canonical_smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
            "formula": "C13H18O2",
        })

        self.add_relationship(drug_ibu, "CHEMBL:CHEMBL221", GraphRelationType.INHIBITS, 0.92, "ChEMBL", "bioassay")
        self.add_relationship(drug_ibu, "CHEMBL:CHEMBL230", GraphRelationType.INHIBITS, 0.90, "ChEMBL", "bioassay")

        self.add_entity("PATHWAY:RENAL_VASODILATION", GraphNodeType.PATHWAY, "Renal Prostaglandin Hemodynamics", {
            "function": "Prostaglandin E2 and I2 mediation of afferent arteriolar vasodilation",
        })
        self.add_relationship("GENE:PTGS1", "PATHWAY:RENAL_VASODILATION", GraphRelationType.PARTICIPATES_IN_PATHWAY, 0.92, "OpenTargets", "pathway_enrichment")
        self.add_relationship("PATHWAY:RENAL_VASODILATION", "TISSUE:RENAL_GLOMERULUS", GraphRelationType.ACTIVE_IN_TISSUE, 0.94, "UniProt", "tissue_expression")

        self.add_entity("SIDER:UMLS:C0035078", GraphNodeType.ADVERSE_EFFECT, "Renal Impairment", {"meddra_id": "10000806"})
        self.add_relationship(drug_ibu, "SIDER:UMLS:C0035078", GraphRelationType.ASSOCIATED_WITH_ADVERSE_EFFECT, 0.84, "SIDER", "clinical_side_effect")
        self.add_relationship("SIDER:UMLS:C0035078", "ORGAN:KIDNEY", GraphRelationType.AFFECTS_ORGAN, 1.0, "SIDER", "organ_mapping")

        self.add_entity("PMID:10477265", GraphNodeType.LITERATURE, "Renal effects of nonsteroidal anti-inflammatory drugs", {"journal": "Am J Kidney Dis", "year": 1999})
        self.add_relationship("PMID:10477265", "PATHWAY:RENAL_VASODILATION", GraphRelationType.SUPPORTS_RELATIONSHIP, 0.90, "PubMed", "peer_reviewed_literature", "PMID:10477265")

        # -----------------------------------------------------
        # DRUG 4: Doxorubicin CHEMBL53
        # -----------------------------------------------------
        drug_dox = "CHEMBL:CHEMBL53"
        self.add_entity(drug_dox, GraphNodeType.DRUG, "Doxorubicin", {
            "chembl_id": "CHEMBL53",
            "pubchem_cid": "31703",
            "canonical_smiles": "COC1=C(C(=O)C2=C(C1=O)C(=CC3=C2C(=O)C4=C(C3=O)C(=CC=C4)O)O)C(=O)CO",
            "formula": "C27H29NO11",
        })

        self.add_entity("CHEMBL:CHEMBL214", GraphNodeType.TARGET, "DNA topoisomerase 2-alpha (TOP2A)", {"gene": "TOP2A"})
        self.add_entity("CHEMBL:CHEMBL216", GraphNodeType.TARGET, "DNA topoisomerase 2-beta (TOP2B)", {"gene": "TOP2B"})
        self.add_entity("GENE:TOP2B", GraphNodeType.GENE, "TOP2B", {"chromosome": "3p24.2"})

        self.add_relationship(drug_dox, "CHEMBL:CHEMBL214", GraphRelationType.INHIBITS, 0.96, "ChEMBL", "bioassay")
        self.add_relationship(drug_dox, "CHEMBL:CHEMBL216", GraphRelationType.INHIBITS, 0.94, "ChEMBL", "bioassay")
        self.add_relationship("CHEMBL:CHEMBL216", "GENE:TOP2B", GraphRelationType.ENCODED_BY, 1.0, "UniProt", "genomic_annotation")

        self.add_entity("PATHWAY:CARDIAC_ROS_MITOCHONDRIA", GraphNodeType.PATHWAY, "Top2b DNA Double-Strand Breaks & Mitochondrial ROS", {
            "mechanism": "TOP2B cleavage complex stabilization in cardiomyocytes causes mitochondrial oxidative phosphorylation failure",
        })
        self.add_relationship("GENE:TOP2B", "PATHWAY:CARDIAC_ROS_MITOCHONDRIA", GraphRelationType.PARTICIPATES_IN_PATHWAY, 0.96, "OpenTargets", "pathway_enrichment")
        self.add_relationship("PATHWAY:CARDIAC_ROS_MITOCHONDRIA", "TISSUE:CARDIOMYOCYTES", GraphRelationType.ACTIVE_IN_TISSUE, 0.98, "UniProt", "tissue_expression")

        self.add_entity("SIDER:UMLS:C0878544", GraphNodeType.ADVERSE_EFFECT, "Cardiomyopathy", {"meddra_id": "10007636"})
        self.add_entity("SIDER:UMLS:C0018802", GraphNodeType.ADVERSE_EFFECT, "Congestive Heart Failure", {"meddra_id": "10010331"})
        self.add_relationship(drug_dox, "SIDER:UMLS:C0878544", GraphRelationType.ASSOCIATED_WITH_ADVERSE_EFFECT, 0.97, "SIDER", "clinical_side_effect")
        self.add_relationship(drug_dox, "SIDER:UMLS:C0018802", GraphRelationType.ASSOCIATED_WITH_ADVERSE_EFFECT, 0.92, "SIDER", "clinical_side_effect")
        self.add_relationship("SIDER:UMLS:C0878544", "ORGAN:HEART", GraphRelationType.AFFECTS_ORGAN, 1.0, "SIDER", "organ_mapping")
        self.add_relationship("SIDER:UMLS:C0018802", "ORGAN:HEART", GraphRelationType.AFFECTS_ORGAN, 1.0, "SIDER", "organ_mapping")

        self.add_entity("PMID:22080981", GraphNodeType.LITERATURE, "Topoisomerase 2-beta mediates cardiotoxicity of anthracyclines", {"journal": "Nature Medicine", "year": 2011})
        self.add_relationship("PMID:22080981", "CHEMBL:CHEMBL216", GraphRelationType.SUPPORTS_RELATIONSHIP, 0.97, "PubMed", "peer_reviewed_literature", "PMID:22080981")

        self._seeded = True


# Global singleton instance
knowledge_graph = BiomedicalKnowledgeGraph()


# ---------------------------------------------------------
# Public Module API
# ---------------------------------------------------------

def add_entity(
    node_id: str,
    node_type: str | GraphNodeType,
    name: str,
    properties: Optional[Dict[str, Any]] = None,
) -> GraphNodeModel:
    return knowledge_graph.add_entity(node_id, node_type, name, properties)


def add_relationship(
    source_id: str,
    target_id: str,
    relation_type: str | GraphRelationType,
    confidence: float = 1.0,
    source: str = "KnowledgeGraph",
    evidence_type: str = "curated_graph",
    provenance_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> GraphEdgeModel:
    return knowledge_graph.add_relationship(
        source_id, target_id, relation_type, confidence, source, evidence_type, provenance_id, metadata
    )


def build_drug_subgraph(
    drug_id: str, depth: int = 3, max_nodes: int = 100
) -> Dict[str, Any]:
    return knowledge_graph.build_drug_subgraph(drug_id, depth, max_nodes)


def get_neighbors(node_id: str, direction: str = "out") -> List[Dict[str, Any]]:
    return knowledge_graph.get_neighbors(node_id, direction)


def find_paths(
    source_id: str, target_id: str, max_length: int = 5
) -> List[GraphPathModel]:
    return knowledge_graph.find_paths(source_id, target_id, max_length)


def find_mechanistic_paths(
    drug_id: str, target_organ: Optional[str] = None
) -> List[GraphPathModel]:
    return knowledge_graph.find_mechanistic_paths(drug_id, target_organ)


def get_evidence_for_relationship(
    source_id: str, target_id: str, relation_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    return knowledge_graph.get_evidence_for_relationship(source_id, target_id, relation_type)


def search_graph(
    query: str, entity_type: Optional[str] = None, limit: int = 20
) -> Dict[str, Any]:
    return knowledge_graph.search_entities(query, entity_type, limit)
