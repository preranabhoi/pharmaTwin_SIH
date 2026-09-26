/**
 * PharmaTwin AI — Interactive Visual Knowledge Graph Engine
 * 
 * Implements a real node-and-branch directed graph visualization:
 * - Multi-tiered branch layout (Drug → Targets → Pathways → Tissues → Organs)
 * - Distinct styling for 9 entity types (Drug, Target, Protein, Gene, Pathway, Tissue, Organ, AdverseEffect, Literature)
 * - Interactive Pan, Zoom, Reset, and Center
 * - Evidence Path Highlighting synchronized with selectedOrgan
 * - Node Click Inspector Drawer showing Provenance, Source DB, and Evidence Strength
 * - Bidirectional synchronization with 2D Human Virtual Twin
 */

import { GraphNodeRenderer } from './GraphNode.js';
import { GraphEdgeRenderer } from './GraphEdge.js';
import { GraphControls } from './GraphControls.js';
import { EvidencePathManager } from './EvidencePath.js';

export class KnowledgeGraph {
  constructor(containerId, options = {}) {
    this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    this.options = Object.assign({
      onOrganSelect: () => {},
      onNodeSelect: () => {},
      selectedOrgan: 'liver',
      drugName: 'Acetaminophen',
      drugId: 'CHEMBL112'
    }, options);

    this.selectedOrgan = this.options.selectedOrgan;
    this.selectedNodeId = null;
    this.drugName = this.options.drugName;
    this.drugId = this.options.drugId;

    // Transform State
    this.zoom = 1.0;
    this.pan = { x: 0, y: 0 };
    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };

    this.graphData = null;
    this.layoutNodes = [];
    this.layoutEdges = [];

    this.init();
  }

  init() {
    if (!this.container) return;
    this.loadGraphData();
    this.render();
    this.bindEvents();
  }

  loadGraphData(customData = null) {
    if (customData && customData.nodes && customData.edges && customData.nodes.length > 0) {
      this.graphData = customData;
    } else {
      this.graphData = EvidencePathManager.generateDefaultGraph(this.drugName, this.drugId);
    }
    this.computeLayout();
  }

  setDrug(drugName, drugId, backendData = null) {
    this.drugName = drugName;
    this.drugId = drugId;
    this.loadGraphData(backendData);
    this.updateVisuals();
  }

  setSelectedOrgan(organId) {
    this.selectedOrgan = organId;
    this.updateVisuals();
  }

  /**
   * Computes clean organic layered branching coordinates for nodes.
   */
  computeLayout() {
    if (!this.graphData) return;

    const width = 840;
    const height = 480;

    // Tiers layout (Left-to-Right Branching flow):
    // Tier 0 (x=80): Literature / Input
    // Tier 1 (x=160): Drug
    // Tier 2 (x=300): Targets, Adverse Effects
    // Tier 3 (x=460): Genes, Pathways, Proteins
    // Tier 4 (x=620): Tissues
    // Tier 5 (x=760): Organs

    const tierX = {
      Literature: 70,
      Drug: 160,
      Target: 320,
      AdverseEffect: 320,
      Gene: 480,
      Protein: 480,
      Pathway: 480,
      Tissue: 630,
      Organ: 770
    };

    // Group nodes by type
    const groups = {};
    this.graphData.nodes.forEach(n => {
      const t = n.type || 'Target';
      if (!groups[t]) groups[t] = [];
      groups[t].push(n);
    });

    const positionedNodes = [];
    const nodeMap = {};

    // 1. Position Drug
    if (groups.Drug) {
      groups.Drug.forEach((d, idx) => {
        d.x = tierX.Drug;
        d.y = height / 2;
        d.radius = 26;
        positionedNodes.push(d);
        nodeMap[d.id] = d;
      });
    }

    // 2. Position Literature
    if (groups.Literature) {
      groups.Literature.forEach((l, idx) => {
        l.x = tierX.Literature;
        l.y = height / 2 - 120 + idx * 70;
        l.radius = 18;
        positionedNodes.push(l);
        nodeMap[l.id] = l;
      });
    }

    // 3. Position Targets & Adverse Effects
    const tier2 = [...(groups.Target || []), ...(groups.AdverseEffect || [])];
    const t2Step = height / (tier2.length + 1);
    tier2.forEach((n, idx) => {
      n.x = tierX[n.type] || 320;
      n.y = t2Step * (idx + 1);
      n.radius = n.type === 'Target' ? 22 : 20;
      positionedNodes.push(n);
      nodeMap[n.id] = n;
    });

    // 4. Position Pathways, Genes, Proteins
    const tier3 = [...(groups.Pathway || []), ...(groups.Gene || []), ...(groups.Protein || [])];
    const t3Step = height / (tier3.length + 1);
    tier3.forEach((n, idx) => {
      n.x = tierX[n.type] || 480;
      n.y = t3Step * (idx + 1);
      n.radius = n.type === 'Pathway' ? 22 : 20;
      positionedNodes.push(n);
      nodeMap[n.id] = n;
    });

    // 5. Position Tissues
    if (groups.Tissue) {
      const t4Step = height / (groups.Tissue.length + 1);
      groups.Tissue.forEach((t, idx) => {
        t.x = tierX.Tissue;
        t.y = t4Step * (idx + 1);
        t.radius = 20;
        positionedNodes.push(t);
        nodeMap[t.id] = t;
      });
    }

    // 6. Position Organs
    if (groups.Organ) {
      const t5Step = height / (groups.Organ.length + 1);
      groups.Organ.forEach((o, idx) => {
        o.x = tierX.Organ;
        o.y = t5Step * (idx + 1);
        o.radius = 24;
        positionedNodes.push(o);
        nodeMap[o.id] = o;
      });
    }

    this.layoutNodes = positionedNodes;
    this.layoutEdges = (this.graphData.edges || []).map(e => {
      return Object.assign({}, e, {
        sourceNode: nodeMap[e.source],
        targetNode: nodeMap[e.target]
      });
    }).filter(e => e.sourceNode && e.targetNode);
  }

  render() {
    const stats = {
      nodes: this.layoutNodes.length || 18,
      edges: this.layoutEdges.length || 22
    };

    this.container.innerHTML = `
      <div class="kg-container-root" id="kg-visual-root">
        
        <!-- Toolbar Strip -->
        ${GraphControls.render(stats)}

        <!-- Active Path Banner -->
        <div class="kg-path-banner" id="kg-active-path-banner">
          <span class="kg-path-label">Active Mechanistic Path:</span>
          <span class="kg-path-value" id="kg-path-text">Loading pathway...</span>
        </div>

        <!-- Main Workspace (SVG Canvas + Inspector Drawer) -->
        <div class="kg-workspace-flex">
          
          <!-- SVG Graph Viewport -->
          <div class="kg-svg-viewport" id="kg-viewport">
            <svg id="kg-canvas-svg" 
                 viewBox="0 0 860 500" 
                 preserveAspectRatio="xMidYMid meet"
                 xmlns="http://www.w3.org/2000/svg">
              
              <defs>
                <!-- Default Marker Arrow -->
                <marker id="kg-arrow-default" viewBox="0 0 10 10" refX="8" refY="5"
                        markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#94a3b8" />
                </marker>

                <!-- Highlighted Marker Arrow -->
                <marker id="kg-arrow-highlight" viewBox="0 0 10 10" refX="8" refY="5"
                        markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#2563eb" />
                </marker>
              </defs>

              <!-- Zoom & Pan Group -->
              <g id="kg-transform-layer" transform="matrix(1 0 0 1 0 0)">
                <!-- Edges Layer -->
                <g id="kg-edges-layer"></g>

                <!-- Nodes Layer -->
                <g id="kg-nodes-layer"></g>
              </g>

            </svg>
          </div>

          <!-- Node Detail Inspector Drawer -->
          <aside class="kg-inspector-drawer" id="kg-inspector-drawer">
            <div class="kg-inspector-header">
              <span class="kg-inspector-title">Biomedical Entity Inspector</span>
              <button class="btn-close-mini" id="btn-close-inspector" title="Close details">&times;</button>
            </div>
            <div class="kg-inspector-body" id="kg-inspector-content">
              <div class="kg-empty-state">
                <span>Click any graph node to inspect biological properties, provenance, and supporting evidence.</span>
              </div>
            </div>
          </aside>

        </div>

      </div>
    `;

    this.updateVisuals();
  }

  bindEvents() {
    const root = this.container.querySelector('#kg-visual-root');
    if (!root) return;

    // Viewport Pan & Zoom
    const viewport = root.querySelector('#kg-viewport');
    if (viewport) {
      viewport.addEventListener('mousedown', (e) => {
        if (e.target.closest('.kg-node-group')) return;
        this.isDragging = true;
        this.dragStart = { x: e.clientX - this.pan.x, y: e.clientY - this.pan.y };
        viewport.style.cursor = 'grabbing';
      });

      window.addEventListener('mousemove', (e) => {
        if (!this.isDragging) return;
        this.pan.x = e.clientX - this.dragStart.x;
        this.pan.y = e.clientY - this.dragStart.y;
        this.applyTransform();
      });

      window.addEventListener('mouseup', () => {
        if (this.isDragging) {
          this.isDragging = false;
          viewport.style.cursor = 'grab';
        }
      });

      viewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        this.zoom = Math.max(0.4, Math.min(2.5, this.zoom + delta));
        this.applyTransform();
      });
    }

    // Zoom Buttons
    root.querySelector('#btn-kg-zoom-in')?.addEventListener('click', () => {
      this.zoom = Math.min(2.5, this.zoom + 0.15);
      this.applyTransform();
    });

    root.querySelector('#btn-kg-zoom-out')?.addEventListener('click', () => {
      this.zoom = Math.max(0.4, this.zoom - 0.15);
      this.applyTransform();
    });

    root.querySelector('#btn-kg-center')?.addEventListener('click', () => {
      this.pan = { x: 0, y: 0 };
      this.applyTransform();
    });

    root.querySelector('#btn-kg-reset')?.addEventListener('click', () => {
      this.zoom = 1.0;
      this.pan = { x: 0, y: 0 };
      this.selectedNodeId = null;
      this.applyTransform();
      this.updateVisuals();
    });

    // Close Inspector
    root.querySelector('#btn-close-inspector')?.addEventListener('click', () => {
      const drawer = root.querySelector('#kg-inspector-drawer');
      if (drawer) drawer.classList.remove('open');
    });
  }

  updateVisuals() {
    const root = this.container.querySelector('#kg-visual-root');
    if (!root) return;

    const drugNodeId = this.layoutNodes.find(n => n.type === 'Drug')?.id || `DRUG:${this.drugId}`;
    const activePathInfo = EvidencePathManager.getActiveOrganPath(this.selectedOrgan, drugNodeId);
    
    // Update Active Path text
    const pathTextElem = root.querySelector('#kg-path-text');
    if (pathTextElem) {
      pathTextElem.innerText = activePathInfo.summary;
    }

    const highlightedNodes = new Set(activePathInfo.nodeIds);
    const highlightedEdges = new Set(activePathInfo.edgeIds);

    // 1. Render Edges
    const edgesLayer = root.querySelector('#kg-edges-layer');
    if (edgesLayer) {
      edgesLayer.innerHTML = this.layoutEdges.map(edge => {
        const isHighlight = highlightedEdges.has(edge.id);
        const isDimmed = highlightedEdges.size > 0 && !isHighlight;
        return GraphEdgeRenderer.render(edge, edge.sourceNode, edge.targetNode, isHighlight, isDimmed);
      }).join('');
    }

    // 2. Render Nodes
    const nodesLayer = root.querySelector('#kg-nodes-layer');
    if (nodesLayer) {
      nodesLayer.innerHTML = this.layoutNodes.map(node => {
        const isHighlight = highlightedNodes.has(node.id);
        const isSelected = this.selectedNodeId === node.id;
        const isDimmed = highlightedNodes.size > 0 && !isHighlight;
        return GraphNodeRenderer.render(node, isHighlight, isSelected, isDimmed);
      }).join('');
    }

    // Bind Node Click Handlers
    root.querySelectorAll('.kg-node-group').forEach((nodeElem) => {
      const nodeId = nodeElem.getAttribute('data-node-id');
      const nodeType = nodeElem.getAttribute('data-node-type');

      nodeElem.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleNodeClick(nodeId, nodeType);
      });
    });
  }

  handleNodeClick(nodeId, nodeType) {
    this.selectedNodeId = nodeId;
    const node = this.layoutNodes.find(n => n.id === nodeId);
    if (!node) return;

    // If clicked an Organ node -> Synchronize global selectedOrgan!
    if (nodeType === 'Organ') {
      const organKey = (node.properties?.organ_id || node.name || '').toLowerCase();
      if (['brain', 'heart', 'liver', 'kidney', 'lung'].includes(organKey)) {
        this.selectedOrgan = organKey;
        if (typeof this.options.onOrganSelect === 'function') {
          this.options.onOrganSelect(organKey);
        }
      }
    }

    this.showNodeInspector(node);
    this.updateVisuals();

    if (typeof this.options.onNodeSelect === 'function') {
      this.options.onNodeSelect(node);
    }
  }

  showNodeInspector(node) {
    const drawer = this.container.querySelector('#kg-inspector-drawer');
    const content = this.container.querySelector('#kg-inspector-content');
    if (!drawer || !content) return;

    drawer.classList.add('open');

    // Find connected edges
    const incoming = this.layoutEdges.filter(e => e.target === node.id);
    const outgoing = this.layoutEdges.filter(e => e.source === node.id);

    const props = node.properties || {};
    const propsList = Object.entries(props).map(([k, v]) => `
      <div class="kg-prop-row">
        <span class="kg-prop-name">${k.replace(/_/g, ' ')}:</span>
        <span class="kg-prop-val">${typeof v === 'object' ? JSON.stringify(v) : v}</span>
      </div>
    `).join('');

    content.innerHTML = `
      <div class="kg-inspector-card">
        <div class="kg-node-badge-type type-${node.type.toLowerCase()}">${node.type}</div>
        <h4 class="kg-inspector-name">${node.name || node.id}</h4>
        <div class="kg-curie-id">CURIE: ${node.id}</div>

        <div class="kg-section-title">Biological Metadata &amp; Properties</div>
        <div class="kg-props-table">
          ${propsList || '<span style="color:var(--text-muted); font-size:0.75rem;">No extended attributes.</span>'}
        </div>

        <div class="kg-section-title">Relationships in Mechanistic Subgraph</div>
        <div class="kg-relations-list">
          ${outgoing.map(e => `
            <div class="kg-rel-item">
              <span class="kg-rel-verb">─[${e.relation}]─►</span>
              <strong>${e.targetNode?.name || e.target}</strong>
              <span class="kg-source-badge">${e.source_db || 'Graph'}</span>
            </div>
          `).join('')}
          ${incoming.map(e => `
            <div class="kg-rel-item">
              <strong>${e.sourceNode?.name || e.source}</strong>
              <span class="kg-rel-verb">─[${e.relation}]─►</span>
              <span class="kg-source-badge">${e.source_db || 'Graph'}</span>
            </div>
          `).join('')}
        </div>

        ${node.type === 'Organ' ? `
          <div style="margin-top:0.75rem;">
            <button class="btn-primary" id="btn-sync-twin-organ" style="width:100%; font-size:0.75rem; padding:0.4rem;">
              Focus 2D Human Twin on ${node.name}
            </button>
          </div>
        ` : ''}
      </div>
    `;

    const btnSync = content.querySelector('#btn-sync-twin-organ');
    if (btnSync) {
      btnSync.addEventListener('click', () => {
        const organKey = (node.properties?.organ_id || node.name || '').toLowerCase();
        if (typeof this.options.onOrganSelect === 'function') {
          this.options.onOrganSelect(organKey);
        }
      });
    }
  }

  applyTransform() {
    const layer = this.container.querySelector('#kg-transform-layer');
    if (layer) {
      layer.setAttribute('transform', `matrix(${this.zoom} 0 0 ${this.zoom} ${this.pan.x} ${this.pan.y})`);
    }
  }
}
