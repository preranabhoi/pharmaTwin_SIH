/**
 * PharmaTwin AI — 2D Front-Facing Human Virtual Twin Component
 * 
 * Replaces 3D WebGL model with a unified front-facing anatomical vector visualization:
 * - Single coherent human silhouette (Head + Torso + Arms + Legs)
 * - 5 internal risk-bearing organs visibly positioned inside: Brain, Lungs, Heart, Liver, Kidneys
 * - Interactive hover tooltips & click handlers updating global selectedOrgan state
 * - Precision SVG connector lines to compact organ labels
 * - Reset View / Center / View: Front controls
 */

import { SUPPORTED_ORGANS, ORGAN_CONFIGS, DEMO_ORGAN_RISKS, getRiskColor } from './organMap.js';
import { OrganRenderer } from './Organ.js';
import { OrganLabelRenderer } from './OrganLabel.js';

export class HumanTwin2D {
  constructor(containerId, options = {}) {
    this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    this.options = Object.assign({
      onOrganSelect: () => {},
      selectedOrgan: 'liver',
      initialData: DEMO_ORGAN_RISKS
    }, options);

    this.selectedOrgan = this.options.selectedOrgan;
    this.organData = Object.assign({}, DEMO_ORGAN_RISKS, this.options.initialData);
    this.zoomLevel = 1.0;
    this.panOffset = { x: 0, y: 0 };
    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };

    this.init();
  }

  init() {
    if (!this.container) return;
    this.render();
    this.bindEvents();
  }

  setOrganData(data) {
    if (!data) return;
    
    // Normalize data if coming from API
    if (data.organs) {
      this.organData = {};
      for (const [id, val] of Object.entries(data.organs)) {
        if (SUPPORTED_ORGANS.includes(id)) {
          this.organData[id] = {
            name: val.name || ORGAN_CONFIGS[id]?.name || id,
            risk: val.risk ?? val.risk_score ?? 0,
            category: val.category || (val.risk > 0.65 ? 'High' : (val.risk > 0.35 ? 'Moderate' : 'Low')),
            confidence: val.confidence_tier || val.confidence || 'Low',
            percent: `${((val.risk ?? 0) * 100).toFixed(1)}%`
          };
        }
      }
    } else {
      this.organData = Object.assign({}, this.organData, data);
    }

    this.updateVisuals();
  }

  setSelectedOrgan(organId) {
    if (!SUPPORTED_ORGANS.includes(organId)) return;
    this.selectedOrgan = organId;
    this.updateVisuals();
  }

  render() {
    this.container.innerHTML = `
      <div class="human-twin-wrapper" id="twin-2d-root">
        
        <!-- Twin Viewport -->
        <div class="human-twin-viewport" id="twin-2d-viewport">
          
          <!-- Side Organ Labels (Left Column: Brain, Lung, Liver) -->
          <div class="twin-labels-column left-labels">
            ${OrganLabelRenderer.renderLabelElement('brain', this.organData.brain, this.selectedOrgan === 'brain')}
            ${OrganLabelRenderer.renderLabelElement('lung', this.organData.lung, this.selectedOrgan === 'lung')}
            ${OrganLabelRenderer.renderLabelElement('liver', this.organData.liver, this.selectedOrgan === 'liver')}
          </div>

          <!-- SVG Anatomical Human Body -->
          <div class="twin-svg-stage" id="twin-svg-stage">
            <svg id="human-anatomical-svg" 
                 viewBox="0 0 340 460" 
                 preserveAspectRatio="xMidYMid meet"
                 xmlns="http://www.w3.org/2000/svg">
              
              <defs>
                <!-- Subtle Body Shading Linear Gradient -->
                <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#e2e8f0" />
                  <stop offset="50%" stop-color="#f1f5f9" />
                  <stop offset="100%" stop-color="#e2e8f0" />
                </linearGradient>

                <!-- High Risk Organ Pulse Glow -->
                <filter id="organGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              <!-- Transform Container for Pan/Zoom -->
              <g id="twin-transform-group" transform="matrix(1 0 0 1 0 0)">

                <!-- ==============================================================
                     1. COHERENT HUMAN SILHOUETTE (Head + Torso + Arms + Legs)
                     ============================================================== -->
                <g class="human-silhouette-group">
                  
                  <!-- Full Body Anatomical Outline -->
                  <path class="human-silhouette-body" d="
                    M 170 12 
                    C 185 12, 196 22, 196 42 
                    C 196 58, 188 68, 180 72 
                    C 181 77, 184 82, 189 85 
                    C 202 89, 222 98, 235 110 
                    C 245 119, 248 135, 246 160 
                    C 244 185, 240 215, 238 245 
                    C 236 260, 232 275, 228 280 
                    C 225 284, 222 280, 222 272 
                    C 224 250, 226 220, 226 195 
                    C 226 175, 224 148, 218 132 
                    C 214 145, 212 170, 210 195 
                    C 208 215, 206 235, 205 250 
                    C 204 265, 208 280, 208 300 
                    C 208 335, 205 375, 203 410 
                    C 202 428, 200 445, 208 450 
                    C 212 452, 212 455, 202 455 
                    C 190 455, 186 448, 186 430 
                    C 186 395, 188 355, 188 320 
                    C 188 290, 182 270, 178 262 
                    C 174 258, 170 258, 166 262 
                    C 162 270, 156 290, 156 320 
                    C 156 355, 158 395, 158 430 
                    C 158 448, 154 455, 142 455 
                    C 132 455, 132 452, 136 450 
                    C 144 445, 142 428, 141 410 
                    C 139 375, 136 335, 136 300 
                    C 136 280, 140 265, 139 250 
                    C 138 235, 136 215, 134 195 
                    C 132 170, 130 145, 126 132 
                    C 120 148, 118 175, 118 195 
                    C 118 220, 120 250, 122 272 
                    C 122 280, 119 284, 116 280 
                    C 112 275, 108 260, 106 245 
                    C 104 215, 100 185, 98 160 
                    C 96 135, 99 119, 109 110 
                    C 122 98, 142 89, 155 85 
                    C 160 82, 163 77, 164 72 
                    C 156 68, 148 58, 148 42 
                    C 148 22, 159 12, 170 12 Z
                  " 
                  fill="url(#bodyGrad)" 
                  stroke="#94a3b8" 
                  stroke-width="1.6" />

                  <!-- Clavicles / Ribcage Aesthetic Contours (Subtle Context) -->
                  <g class="anatomical-subtle-lines" stroke="#cbd5e1" stroke-width="1" fill="none" opacity="0.8">
                    <!-- Clavicles -->
                    <path d="M 148 88 C 158 92, 166 90, 170 91 C 174 90, 182 92, 192 88" />
                    <!-- Sternum -->
                    <path d="M 170 92 L 170 148" />
                    <!-- Rib contours -->
                    <path d="M 144 115 C 155 118, 165 118, 170 115 C 175 118, 185 118, 196 115" />
                    <path d="M 140 135 C 152 140, 165 140, 170 137 C 175 140, 188 140, 200 135" />
                    <path d="M 142 158 C 154 164, 165 164, 170 160 C 175 164, 186 164, 198 158" />
                    <!-- Pelvis / Hip subtle curves -->
                    <path d="M 144 246 C 156 254, 184 254, 196 246" />
                  </g>
                </g>

                <!-- ==============================================================
                     2. FIVE INTERNAL ORGANS (Brain, Lungs, Heart, Liver, Kidneys)
                     ============================================================== -->
                <g id="twin-organs-layer">
                  ${OrganRenderer.renderOrgan('brain', this.organData.brain, this.selectedOrgan === 'brain')}
                  ${OrganRenderer.renderOrgan('lung', this.organData.lung, this.selectedOrgan === 'lung')}
                  ${OrganRenderer.renderOrgan('heart', this.organData.heart, this.selectedOrgan === 'heart')}
                  ${OrganRenderer.renderOrgan('liver', this.organData.liver, this.selectedOrgan === 'liver')}
                  ${OrganRenderer.renderOrgan('kidney', this.organData.kidney, this.selectedOrgan === 'kidney')}
                </g>

                <!-- ==============================================================
                     3. PRECISION CONNECTOR LINES
                     ============================================================== -->
                <g id="twin-connectors-layer">
                  ${OrganLabelRenderer.renderConnector('brain', this.organData.brain, this.selectedOrgan === 'brain')}
                  ${OrganLabelRenderer.renderConnector('lung', this.organData.lung, this.selectedOrgan === 'lung')}
                  ${OrganLabelRenderer.renderConnector('heart', this.organData.heart, this.selectedOrgan === 'heart')}
                  ${OrganLabelRenderer.renderConnector('liver', this.organData.liver, this.selectedOrgan === 'liver')}
                  ${OrganLabelRenderer.renderConnector('kidney', this.organData.kidney, this.selectedOrgan === 'kidney')}
                </g>

              </g>
            </svg>
          </div>

          <!-- Side Organ Labels (Right Column: Heart, Kidney) -->
          <div class="twin-labels-column right-labels">
            ${OrganLabelRenderer.renderLabelElement('heart', this.organData.heart, this.selectedOrgan === 'heart')}
            ${OrganLabelRenderer.renderLabelElement('kidney', this.organData.kidney, this.selectedOrgan === 'kidney')}
          </div>

          <!-- Dynamic Tooltip -->
          <div class="twin-hud-tooltip" id="twin-2d-tooltip" style="display:none;"></div>
        </div>

        <!-- Compact Bottom Controls & Risk Legend -->
        <div class="twin-footer-bar">
          
          <!-- Risk Legend -->
          <div class="twin-legend-pills">
            <div class="legend-pill"><span class="legend-dot" style="background:#16a34a;"></span><span>Low (&lt;35%)</span></div>
            <div class="legend-pill"><span class="legend-dot" style="background:#ea580c;"></span><span>Moderate (35-65%)</span></div>
            <div class="legend-pill"><span class="legend-dot" style="background:#dc2626;"></span><span>High (&gt;65%)</span></div>
          </div>

          <!-- 2D Viewport Controls -->
          <div class="twin-control-buttons">
            <span class="view-chip" title="2D Front Anatomical View">View: Front</span>
            <button class="btn-twin-action" id="btn-twin-center" title="Center 2D Twin">
              <span>🎯 Center</span>
            </button>
            <button class="btn-twin-action" id="btn-twin-reset" title="Reset Scale and Selection">
              <span>🔄 Reset View</span>
            </button>
          </div>

        </div>

      </div>
    `;
  }

  bindEvents() {
    const root = this.container.querySelector('#twin-2d-root');
    if (!root) return;

    // Organ SVG Clicks & Hovers
    const organGroups = root.querySelectorAll('.organ-interactive-group');
    const tooltip = root.querySelector('#twin-2d-tooltip');

    organGroups.forEach((elem) => {
      const organId = elem.getAttribute('data-organ');

      elem.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleOrganClick(organId);
      });

      elem.addEventListener('mouseenter', (e) => {
        this.showTooltip(organId, e);
      });

      elem.addEventListener('mousemove', (e) => {
        this.moveTooltip(e);
      });

      elem.addEventListener('mouseleave', () => {
        this.hideTooltip();
      });
    });

    // Side Label Clicks
    root.querySelectorAll('.twin-organ-label').forEach((labelElem) => {
      const organId = labelElem.getAttribute('data-organ');
      labelElem.addEventListener('click', () => {
        this.handleOrganClick(organId);
      });
    });

    // Control Buttons
    const btnReset = root.querySelector('#btn-twin-reset');
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        this.resetView();
      });
    }

    const btnCenter = root.querySelector('#btn-twin-center');
    if (btnCenter) {
      btnCenter.addEventListener('click', () => {
        this.centerView();
      });
    }
  }

  handleOrganClick(organId) {
    if (!SUPPORTED_ORGANS.includes(organId)) return;
    this.selectedOrgan = organId;
    this.updateVisuals();

    if (typeof this.options.onOrganSelect === 'function') {
      this.options.onOrganSelect(organId, this.organData[organId]);
    }
  }

  showTooltip(organId, event) {
    const tooltip = this.container.querySelector('#twin-2d-tooltip');
    if (!tooltip) return;

    const data = this.organData[organId] || DEMO_ORGAN_RISKS[organId];
    const config = ORGAN_CONFIGS[organId];
    if (!data || !config) return;

    const color = getRiskColor(data.category);
    tooltip.innerHTML = `
      <div style="font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:4px; font-size:0.8rem;">
        <span>${config.icon}</span>
        <span>${data.name}</span>
      </div>
      <div style="margin-top:2px; font-size:0.75rem; display:flex; justify-content:space-between; gap:8px;">
        <span style="color:${color}; font-weight:700;">${data.category} Risk</span>
        <span style="font-family:var(--font-mono); font-weight:700;">${(data.risk * 100).toFixed(1)}%</span>
      </div>
      <div style="font-size:0.68rem; color:var(--text-muted); margin-top:2px;">
        Confidence: ${data.confidence || 'Moderate'}
      </div>
    `;

    tooltip.style.display = 'block';
    this.moveTooltip(event);
  }

  moveTooltip(event) {
    const tooltip = this.container.querySelector('#twin-2d-tooltip');
    const viewport = this.container.querySelector('#twin-2d-viewport');
    if (!tooltip || !viewport) return;

    const rect = viewport.getBoundingClientRect();
    const x = event.clientX - rect.left + 12;
    const y = event.clientY - rect.top + 12;

    tooltip.style.left = `${Math.min(x, rect.width - 150)}px`;
    tooltip.style.top = `${Math.min(y, rect.height - 70)}px`;
  }

  hideTooltip() {
    const tooltip = this.container.querySelector('#twin-2d-tooltip');
    if (tooltip) tooltip.style.display = 'none';
  }

  updateVisuals() {
    // 1. Update SVG Organs
    const organsLayer = this.container.querySelector('#twin-organs-layer');
    if (organsLayer) {
      organsLayer.innerHTML = SUPPORTED_ORGANS
        .map(id => OrganRenderer.renderOrgan(id, this.organData[id], this.selectedOrgan === id))
        .join('');
    }

    // 2. Update SVG Connectors
    const connectorsLayer = this.container.querySelector('#twin-connectors-layer');
    if (connectorsLayer) {
      connectorsLayer.innerHTML = SUPPORTED_ORGANS
        .map(id => OrganLabelRenderer.renderConnector(id, this.organData[id], this.selectedOrgan === id))
        .join('');
    }

    // 3. Update Side Label Elements
    SUPPORTED_ORGANS.forEach((id) => {
      const label = this.container.querySelector(`#twin-label-${id}`);
      if (label) {
        label.classList.toggle('selected', this.selectedOrgan === id);
        const data = this.organData[id];
        if (data) {
          const badge = label.querySelector('.twin-label-badge');
          const score = label.querySelector('.twin-label-score');
          const color = getRiskColor(data.category);
          if (badge) {
            badge.innerText = data.category;
            badge.style.background = `${color}15`;
            badge.style.color = color;
            badge.style.borderColor = `${color}40`;
          }
          if (score) {
            score.innerText = `${(data.risk * 100).toFixed(1)}%`;
            score.style.color = color;
          }
        }
      }
    });

    // Re-bind hover & click handlers on updated DOM
    const organGroups = this.container.querySelectorAll('.organ-interactive-group');
    organGroups.forEach((elem) => {
      const organId = elem.getAttribute('data-organ');
      elem.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleOrganClick(organId);
      });
      elem.addEventListener('mouseenter', (e) => this.showTooltip(organId, e));
      elem.addEventListener('mousemove', (e) => this.moveTooltip(e));
      elem.addEventListener('mouseleave', () => this.hideTooltip());
    });
  }

  resetView() {
    this.zoomLevel = 1.0;
    this.panOffset = { x: 0, y: 0 };
    this.selectedOrgan = 'liver';
    this.applyTransform();
    this.updateVisuals();
    if (typeof this.options.onOrganSelect === 'function') {
      this.options.onOrganSelect('liver', this.organData.liver);
    }
  }

  centerView() {
    this.zoomLevel = 1.0;
    this.panOffset = { x: 0, y: 0 };
    this.applyTransform();
  }

  applyTransform() {
    const group = this.container.querySelector('#twin-transform-group');
    if (group) {
      group.setAttribute('transform', `matrix(${this.zoomLevel} 0 0 ${this.zoomLevel} ${this.panOffset.x} ${this.panOffset.y})`);
    }
  }
}
