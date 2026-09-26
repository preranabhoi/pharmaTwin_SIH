/**
 * PharmaTwin AI — GraphNode Component
 * 
 * Renders distinct biomedical entity nodes:
 * - Drug (Large central blue node)
 * - Target (Purple node)
 * - Protein (Sky blue node)
 * - Gene (Emerald green node)
 * - Pathway (Violet node)
 * - Tissue (Teal node)
 * - Organ (Risk-colored node: Red/Orange/Green)
 * - Adverse Effect (Orange/Rose node)
 * - Literature (Document white/slate node)
 */

export const NODE_STYLES = {
  Drug: {
    fill: '#2563eb',
    stroke: '#1d4ed8',
    text: '#ffffff',
    icon: '💊',
    radius: 26,
    shape: 'hexagon'
  },
  Target: {
    fill: '#7c3aed',
    stroke: '#6d28d9',
    text: '#ffffff',
    icon: '🎯',
    radius: 22,
    shape: 'circle'
  },
  Protein: {
    fill: '#0284c7',
    stroke: '#0369a1',
    text: '#ffffff',
    icon: '🧬',
    radius: 20,
    shape: 'circle'
  },
  Gene: {
    fill: '#10b981',
    stroke: '#059669',
    text: '#ffffff',
    icon: '🔬',
    radius: 20,
    shape: 'circle'
  },
  Pathway: {
    fill: '#6366f1',
    stroke: '#4f46e5',
    text: '#ffffff',
    icon: '⚡',
    radius: 22,
    shape: 'rect'
  },
  Tissue: {
    fill: '#0d9488',
    stroke: '#0f766e',
    text: '#ffffff',
    icon: '🧫',
    radius: 20,
    shape: 'rect'
  },
  Organ: {
    fill: '#dc2626',
    stroke: '#b91c1c',
    text: '#ffffff',
    icon: '🫀',
    radius: 24,
    shape: 'circle'
  },
  AdverseEffect: {
    fill: '#e11d48',
    stroke: '#be123c',
    text: '#ffffff',
    icon: '⚠️',
    radius: 20,
    shape: 'rect'
  },
  Literature: {
    fill: '#ffffff',
    stroke: '#64748b',
    text: '#0f172a',
    icon: '📄',
    radius: 18,
    shape: 'rect'
  }
};

export class GraphNodeRenderer {
  static getNodeStyle(type, properties = {}) {
    const base = NODE_STYLES[type] || NODE_STYLES.Target;
    if (type === 'Organ') {
      const riskCat = (properties.risk_category || properties.category || '').toLowerCase();
      if (riskCat === 'high') {
        return Object.assign({}, base, { fill: '#dc2626', stroke: '#b91c1c' });
      } else if (riskCat === 'moderate' || riskCat === 'medium') {
        return Object.assign({}, base, { fill: '#ea580c', stroke: '#c2410c' });
      } else {
        return Object.assign({}, base, { fill: '#16a34a', stroke: '#15803d' });
      }
    }
    return base;
  }

  static render(node, isHighlighted = false, isSelected = false, isDimmed = false) {
    const style = this.getNodeStyle(node.type, node.properties);
    const radius = style.radius;
    const highlightClass = isHighlighted ? 'node-highlighted' : (isDimmed ? 'node-dimmed' : '');
    const selectedClass = isSelected ? 'node-selected' : '';
    const label = node.name || node.id;
    const shortLabel = label.length > 16 ? label.substring(0, 14) + '…' : label;

    let shapeSvg = '';
    if (style.shape === 'hexagon') {
      const r = radius * 1.15;
      const points = [
        `${node.x},${node.y - r}`,
        `${node.x + r * 0.866},${node.y - r * 0.5}`,
        `${node.x + r * 0.866},${node.y + r * 0.5}`,
        `${node.x},${node.y + r}`,
        `${node.x - r * 0.866},${node.y + r * 0.5}`,
        `${node.x - r * 0.866},${node.y - r * 0.5}`
      ].join(' ');
      shapeSvg = `
        <polygon points="${points}" 
                 class="kg-node-shape" 
                 fill="${style.fill}" 
                 stroke="${style.stroke}" 
                 stroke-width="${isSelected ? 3.5 : 2}" />
      `;
    } else if (style.shape === 'rect') {
      const w = radius * 2.4;
      const h = radius * 1.6;
      shapeSvg = `
        <rect x="${node.x - w / 2}" y="${node.y - h / 2}" width="${w}" height="${h}" rx="6"
              class="kg-node-shape" 
              fill="${style.fill}" 
              stroke="${style.stroke}" 
              stroke-width="${isSelected ? 3.5 : 2}" />
      `;
    } else {
      shapeSvg = `
        <circle cx="${node.x}" cy="${node.y}" r="${radius}"
                class="kg-node-shape" 
                fill="${style.fill}" 
                stroke="${style.stroke}" 
                stroke-width="${isSelected ? 3.5 : 2}" />
      `;
    }

    return `
      <g class="kg-node-group ${highlightClass} ${selectedClass}" 
         id="kg-node-${node.id.replace(/[^a-zA-Z0-9_-]/g, '_')}"
         data-node-id="${node.id}"
         data-node-type="${node.type}"
         tabindex="0">
        
        <!-- Outer Glow for highlighted path -->
        ${isHighlighted ? `<circle cx="${node.x}" cy="${node.y}" r="${radius + 6}" fill="none" stroke="${style.fill}" stroke-width="2.5" opacity="0.6" stroke-dasharray="3,3" />` : ''}

        ${shapeSvg}

        <!-- Icon -->
        <text x="${node.x}" y="${node.y - (style.shape === 'rect' ? 2 : 3)}" 
              text-anchor="middle" 
              alignment-baseline="middle" 
              font-size="12" 
              pointer-events="none">
          ${style.icon}
        </text>

        <!-- Label below node -->
        <g class="kg-node-label-group" transform="translate(${node.x}, ${node.y + radius + 12})">
          <rect x="-45" y="-9" width="90" height="15" rx="3" fill="#ffffff" stroke="#cbd5e1" stroke-width="0.8" opacity="0.9" />
          <text x="0" y="2" 
                text-anchor="middle" 
                alignment-baseline="middle"
                font-family="var(--font-sans)" 
                font-size="9" 
                font-weight="600" 
                fill="#0f172a">
            ${shortLabel}
          </text>
        </g>
      </g>
    `;
  }
}
