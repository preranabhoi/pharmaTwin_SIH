/**
 * PharmaTwin AI — OrganRiskTable Component
 * 
 * Renders the 5 risk-bearing organs in a researcher-friendly table:
 * 1. Brain (Low • 1.0% • Confidence: Low)
 * 2. Heart (Low • 20.0% • Confidence: Low)
 * 3. Liver (High • 75.6% • Confidence: High)
 * 4. Kidney (Moderate • 68.8% • Confidence: Low)
 * 5. Lung (Low • 1.0% • Confidence: Low)
 * 
 * Synchronized with global selectedOrgan state.
 */

import { SUPPORTED_ORGANS, ORGAN_CONFIGS, DEMO_ORGAN_RISKS, getRiskColor } from '../HumanVirtualTwin2D/organMap.js';

export class OrganRiskTable {
  constructor(containerId, options = {}) {
    this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    this.options = Object.assign({
      onOrganSelect: () => {},
      selectedOrgan: 'liver',
      initialData: DEMO_ORGAN_RISKS
    }, options);

    this.selectedOrgan = this.options.selectedOrgan;
    this.organData = Object.assign({}, DEMO_ORGAN_RISKS, this.options.initialData);

    this.init();
  }

  init() {
    if (!this.container) return;
    this.render();
    this.bindEvents();
  }

  setOrganData(data) {
    if (!data) return;
    if (data.organs) {
      this.organData = {};
      for (const [id, val] of Object.entries(data.organs)) {
        if (SUPPORTED_ORGANS.includes(id)) {
          this.organData[id] = {
            name: val.name || ORGAN_CONFIGS[id]?.name || id,
            risk: val.risk ?? val.risk_score ?? 0,
            category: val.category || (val.risk > 0.65 ? 'High' : (val.risk > 0.35 ? 'Moderate' : 'Low')),
            confidence: val.confidence_tier || val.confidence || 'Low',
            percent: `${((val.risk ?? 0) * 100).toFixed(1)}%`,
            evidence_strength: val.evidence_strength || 'Low'
          };
        }
      }
    } else {
      this.organData = Object.assign({}, this.organData, data);
    }
    this.render();
    this.bindEvents();
  }

  setSelectedOrgan(organId) {
    if (!SUPPORTED_ORGANS.includes(organId)) return;
    this.selectedOrgan = organId;
    this.updateSelection();
  }

  render() {
    this.container.innerHTML = `
      <div class="card" id="card-organ-table-root">
        <div class="card-header">
          <div class="card-title">
            <span class="card-title-icon">🫀</span>
            <span>Organ Risk Breakdown</span>
          </div>
          <span class="card-subtitle">Click organ to inspect evidence trace</span>
        </div>

        <div class="organ-table-container">
          <div class="organ-table-header">
            <span>Target Organ</span>
            <span>Risk Level</span>
            <span>Probability Score</span>
            <span>Confidence</span>
          </div>

          <div class="organ-list-rows" id="organ-rows-host">
            ${SUPPORTED_ORGANS.map(id => this.renderRow(id)).join('')}
          </div>
        </div>
      </div>
    `;
  }

  renderRow(organId) {
    const config = ORGAN_CONFIGS[organId];
    const data = this.organData[organId] || DEMO_ORGAN_RISKS[organId];
    const isSelected = this.selectedOrgan === organId;
    const catClass = (data.category || 'Low').toLowerCase();
    const riskPercent = (data.risk * 100).toFixed(1);
    const color = getRiskColor(data.category);

    return `
      <div class="organ-row ${isSelected ? 'selected' : ''}" 
           data-organ-id="${organId}"
           id="organ-row-${organId}"
           tabindex="0"
           role="button">
        
        <div class="organ-name-col">
          <span class="organ-icon">${config.icon}</span>
          <div>
            <strong class="organ-name-text">${data.name || config.name}</strong>
            <span class="organ-system-text">${config.system}</span>
          </div>
        </div>

        <div>
          <span class="badge-risk ${catClass}">${data.category}</span>
        </div>

        <div class="organ-progress-wrap">
          <div class="organ-bar-track">
            <div class="organ-bar-fill ${catClass}" style="width: ${Math.max(6, data.risk * 100)}%;"></div>
          </div>
          <span class="organ-score-text" style="color:${color};">${riskPercent}%</span>
        </div>

        <div class="organ-evidence-text">
          <span class="conf-pill tier-${(data.confidence || 'low').toLowerCase()}">${data.confidence || 'Low'}</span>
        </div>

      </div>
    `;
  }

  bindEvents() {
    const rows = this.container.querySelectorAll('.organ-row');
    rows.forEach((row) => {
      const organId = row.getAttribute('data-organ-id');
      row.addEventListener('click', () => {
        this.setSelectedOrgan(organId);
        if (typeof this.options.onOrganSelect === 'function') {
          this.options.onOrganSelect(organId, this.organData[organId]);
        }
      });
    });
  }

  updateSelection() {
    this.container.querySelectorAll('.organ-row').forEach((row) => {
      const id = row.getAttribute('data-organ-id');
      row.classList.toggle('selected', id === this.selectedOrgan);
    });
  }
}
