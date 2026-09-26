/**
 * PharmaTwin AI — GraphEdge Component
 * 
 * Renders directed graph relationships:
 * - Curved/straight SVG paths
 * - Relationship labels (targets, regulates, participates in, affects, etc.)
 * - Arrowheads
 * - Active path glow and pulse highlighting
 */

export class GraphEdgeRenderer {
  static formatRelationLabel(relation) {
    if (!relation) return '';
    const clean = relation.toLowerCase().replace(/_/g, ' ');
    if (clean === 'participates in pathway') return 'participates in';
    if (clean === 'active in tissue') return 'active in';
    if (clean === 'affects organ') return 'affects';
    if (clean === 'part of organ') return 'part of';
    if (clean === 'associated with adverse effect') return 'associated with';
    if (clean === 'supports relationship') return 'supports';
    return clean;
  }

  static render(edge, sourceNode, targetNode, isHighlighted = false, isDimmed = false) {
    if (!sourceNode || !targetNode) return '';

    const sx = sourceNode.x;
    const sy = sourceNode.y;
    const tx = targetNode.x;
    const ty = targetNode.y;

    const dx = tx - sx;
    const dy = ty - sy;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    // Shorten end points to not overlap node centers
    const srcRadius = sourceNode.radius || 22;
    const tgtRadius = targetNode.radius || 22;

    const startX = sx + (dx / dist) * srcRadius;
    const startY = sy + (dy / dist) * srcRadius;
    const endX = tx - (dx / dist) * (tgtRadius + 6); // slight offset for arrow
    const endY = ty - (dy / dist) * (tgtRadius + 6);

    // Calculate curve control point
    const midX = (startX + endX) / 2;
    const midY = (startY + endY) / 2;
    
    // Perpendicular slight offset for organic curvature
    const perpX = -dy / dist * 12;
    const perpY = dx / dist * 12;
    const ctrlX = midX + perpX;
    const ctrlY = midY + perpY;

    const pathD = `M ${startX} ${startY} Q ${ctrlX} ${ctrlY} ${endX} ${endY}`;

    const strokeColor = isHighlighted ? '#2563eb' : '#94a3b8';
    const strokeWidth = isHighlighted ? '2.8' : '1.4';
    const opacity = isDimmed ? '0.2' : (isHighlighted ? '1.0' : '0.75');
    const markerId = isHighlighted ? 'kg-arrow-highlight' : 'kg-arrow-default';
    const highlightClass = isHighlighted ? 'edge-highlighted' : (isDimmed ? 'edge-dimmed' : '');

    const label = this.formatRelationLabel(edge.relation);

    return `
      <g class="kg-edge-group ${highlightClass}" id="kg-edge-${edge.id.replace(/[^a-zA-Z0-9_-]/g, '_')}" opacity="${opacity}">
        
        <!-- Glow backing if highlighted -->
        ${isHighlighted ? `<path d="${pathD}" fill="none" stroke="#60a5fa" stroke-width="6" opacity="0.4" stroke-linecap="round" />` : ''}

        <!-- Edge Line -->
        <path d="${pathD}" 
              fill="none" 
              stroke="${strokeColor}" 
              stroke-width="${strokeWidth}" 
              stroke-linecap="round"
              marker-end="url(#${markerId})" />

        <!-- Relationship Text Badge -->
        ${label ? `
          <g transform="translate(${ctrlX}, ${ctrlY})">
            <rect x="-32" y="-7" width="64" height="13" rx="3" 
                  fill="${isHighlighted ? '#eff6ff' : '#ffffff'}" 
                  stroke="${isHighlighted ? '#3b82f6' : '#cbd5e1'}" 
                  stroke-width="0.8" />
            <text x="0" y="2" 
                  text-anchor="middle" 
                  alignment-baseline="middle"
                  font-family="var(--font-sans)" 
                  font-size="8" 
                  font-weight="${isHighlighted ? '700' : '500'}"
                  fill="${isHighlighted ? '#1d4ed8' : '#64748b'}">
              ${label}
            </text>
          </g>
        ` : ''}
      </g>
    `;
  }
}
