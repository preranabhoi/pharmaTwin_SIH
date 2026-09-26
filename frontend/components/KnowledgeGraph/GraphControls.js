/**
 * PharmaTwin AI — GraphControls Component
 * 
 * Interactive control bar for zoom, pan, center, reset, and entity filtering in the Knowledge Graph.
 */

export class GraphControls {
  static render(stats = { nodes: 18, edges: 22 }) {
    return `
      <div class="kg-toolbar-strip">
        <div class="kg-stats-badge">
          <span class="kg-dot-live"></span>
          <span id="kg-stat-counts">${stats.nodes} Nodes • ${stats.edges} Relationships</span>
        </div>

        <div class="kg-action-group">
          <button class="btn-icon-kg" id="btn-kg-zoom-in" title="Zoom In (+)">➕</button>
          <button class="btn-icon-kg" id="btn-kg-zoom-out" title="Zoom Out (-)">➖</button>
          <button class="btn-icon-kg" id="btn-kg-center" title="Center Graph">🎯</button>
          <button class="btn-icon-kg" id="btn-kg-reset" title="Reset View &amp; Scale">🔄</button>
        </div>

        <div class="kg-legend-mini">
          <span class="kg-chip-mini chip-drug">Drug</span>
          <span class="kg-chip-mini chip-target">Target</span>
          <span class="kg-chip-mini chip-pathway">Pathway</span>
          <span class="kg-chip-mini chip-tissue">Tissue</span>
          <span class="kg-chip-mini chip-organ">Organ</span>
        </div>
      </div>
    `;
  }
}
