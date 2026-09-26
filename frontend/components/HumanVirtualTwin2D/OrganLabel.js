/**
 * PharmaTwin AI — OrganLabel Component
 * 
 * Renders compact, information-dense side callout labels with precision
 * SVG connector lines linked directly to anatomical organ anchors.
 */

import { ORGAN_CONFIGS, getRiskColor } from './organMap.js';

export class OrganLabelRenderer {
  /**
   * Renders SVG connector line and HTML/SVG callout label for an organ.
   */
  static renderConnector(organId, organData, isSelected = false) {
    const config = ORGAN_CONFIGS[organId];
    if (!config) return '';

    const riskColor = getRiskColor(organData?.category || config.defaultCategory);
    const strokeColor = isSelected ? riskColor : '#94a3b8';
    const strokeWidth = isSelected ? '2' : '1.2';
    const strokeDash = isSelected ? 'none' : '2,2';
    const activeClass = isSelected ? 'connector-active' : '';

    const { from, elbow, to } = config.connector;

    return `
      <g class="organ-connector-line ${activeClass}" id="connector-${organId}">
        <polyline points="${from.x},${from.y} ${elbow.x},${elbow.y} ${to.x},${to.y}"
                  fill="none"
                  stroke="${strokeColor}"
                  stroke-width="${strokeWidth}"
                  stroke-dasharray="${strokeDash}"
                  stroke-linecap="round"
                  stroke-linejoin="round" />
        <circle cx="${from.x}" cy="${from.y}" r="${isSelected ? 4 : 2.5}" fill="${riskColor}" />
        <circle cx="${to.x}" cy="${to.y}" r="${isSelected ? 3.5 : 2}" fill="${riskColor}" />
      </g>
    `;
  }

  /**
   * Renders the HTML overlay badge label for the twin container.
   */
  static renderLabelElement(organId, organData, isSelected = false) {
    const config = ORGAN_CONFIGS[organId];
    if (!config) return '';

    const name = organData?.name || config.name;
    const category = organData?.category || config.defaultCategory;
    const riskVal = organData?.risk !== undefined ? organData.risk : config.defaultRisk;
    const percent = (riskVal * 100).toFixed(1) + '%';
    const side = config.side; // 'left' or 'right'
    const color = getRiskColor(category);
    const selectedClass = isSelected ? 'selected' : '';

    return `
      <div class="twin-organ-label side-${side} ${selectedClass}" 
           id="twin-label-${organId}" 
           data-organ="${organId}"
           title="Click to inspect ${name} risk details">
        <div class="twin-label-header">
          <span class="twin-label-icon">${config.icon}</span>
          <span class="twin-label-name">${name}</span>
        </div>
        <div class="twin-label-meta">
          <span class="twin-label-badge" style="background:${color}15; color:${color}; border-color:${color}40;">
            ${category}
          </span>
          <span class="twin-label-score" style="color:${color}; font-weight:700;">
            ${percent}
          </span>
        </div>
      </div>
    `;
  }
}
