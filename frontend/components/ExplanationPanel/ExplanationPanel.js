/**
 * PharmaTwin AI — ExplanationPanel Component ("Why This Risk?")
 * 
 * Renders:
 * 1. Mechanistic Step-Down Biological Reasoning Cascade
 *    (Molecular Features → Biomedical Target → Pathway → Tissue → Organ)
 * 2. Key Biological Mechanism Details & Literature Citation
 * 3. SHAP Statistical Feature Attribution (Separated from biological causality)
 * 4. [ VIEW EVIDENCE GRAPH ] trigger button
 */

import { ORGAN_CONFIGS, DEMO_ORGAN_RISKS, getRiskColor } from '../HumanVirtualTwin2D/organMap.js';

export class ExplanationPanel {
  static render(selectedOrgan = 'liver', organData = null, expData = null) {
    const config = ORGAN_CONFIGS[selectedOrgan] || ORGAN_CONFIGS.liver;
    const currentOrganData = organData?.[selectedOrgan] || DEMO_ORGAN_RISKS[selectedOrgan];
    const pathwayInfo = config.pathway;
    const riskPercent = ((currentOrganData?.risk ?? config.defaultRisk) * 100).toFixed(1);
    const category = currentOrganData?.category || config.defaultCategory;
    const color = getRiskColor(category);

    const topFeatures = expData?.top_features || [
      { feature_name: 'CYP2E1_Bioactivation_Index', feature_value: 0.88, contribution: 0.34, direction: 'increases_risk' },
      { feature_name: 'LogP_Lipophilicity', feature_value: 1.35, contribution: 0.18, direction: 'increases_risk' },
      { feature_name: 'TopologicalPolarSurfaceArea', feature_value: 49.33, contribution: -0.12, direction: 'decreases_risk' },
    ];

    return `
      <div class="card" id="card-explanation-root">
        <div class="card-header">
          <div class="card-title">
            <span class="card-title-icon">💡</span>
            <span>Why This Risk? — Mechanistic Explanation &amp; Trace</span>
          </div>
          <div class="header-right-actions">
            <span class="badge-risk ${category.toLowerCase()}">${config.name}: ${category.toUpperCase()} (${riskPercent}%)</span>
            <button class="btn-primary-highlight" id="btn-open-evidence-graph-main" title="Open Interactive Biomedical Knowledge Graph">
              <span>🕸️ VIEW EVIDENCE GRAPH</span>
            </button>
          </div>
        </div>

        <div class="explanation-body">
          
          <!-- 1. Mechanistic Step-Down Cascade -->
          <div class="cascade-container">
            <div class="cascade-step">
              <span class="cascade-step-num">Step 1</span>
              <span class="cascade-step-title">Molecular Features</span>
              <span class="cascade-step-val" id="cascade-feat">Descriptors &amp; Fingerprint</span>
            </div>
            <span class="cascade-arrow">→</span>
            
            <div class="cascade-step">
              <span class="cascade-step-num">Step 2</span>
              <span class="cascade-step-title">Biomedical Target</span>
              <span class="cascade-step-val" id="cascade-target">${pathwayInfo.target}</span>
            </div>
            <span class="cascade-arrow">→</span>

            <div class="cascade-step">
              <span class="cascade-step-num">Step 3</span>
              <span class="cascade-step-title">Pathway</span>
              <span class="cascade-step-val" id="cascade-pathway">${pathwayInfo.pathway}</span>
            </div>
            <span class="cascade-arrow">→</span>

            <div class="cascade-step">
              <span class="cascade-step-num">Step 4</span>
              <span class="cascade-step-title">Tissue</span>
              <span class="cascade-step-val" id="cascade-tissue">${pathwayInfo.tissue}</span>
            </div>
            <span class="cascade-arrow">→</span>

            <div class="cascade-step highlight-organ">
              <span class="cascade-step-num">Step 5</span>
              <span class="cascade-step-title">Target Organ</span>
              <span class="cascade-step-val" id="cascade-organ" style="color:${color}; font-weight:700;">
                ${config.icon} ${config.name}
              </span>
            </div>
          </div>

          <!-- 2. Dual Column: Mechanistic Evidence Details + Feature Attribution -->
          <div class="explanation-details-grid">
            
            <!-- Left: Mechanistic Evidence & Citation -->
            <div class="exp-subpanel">
              <span class="subpanel-title">Biological Mechanism &amp; Evidence</span>
              <div class="exp-mechanism-box" id="exp-mechanism-text">
                • ${pathwayInfo.evidence}
              </div>
              <div class="exp-citation-box" id="exp-citation-text">
                <strong>Key Citation:</strong> <em>${pathwayInfo.citation}</em>
              </div>
            </div>

            <!-- Right: SHAP Feature Attribution -->
            <div class="exp-subpanel">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="subpanel-title">Model Feature Contributions (SHAP)</span>
                <span style="font-size:0.7rem; color:var(--text-muted);">Statistical Importance</span>
              </div>
              <div class="shap-mini-list" id="exp-shap-list">
                ${topFeatures.map(f => {
                  const isPos = f.direction === 'increases_risk' || f.contribution > 0;
                  const valColor = isPos ? 'var(--risk-high-text)' : 'var(--risk-low-text)';
                  const sign = isPos ? '+' : '';
                  return `
                    <div class="shap-mini-item">
                      <span class="shap-feat-name">${f.feature_name}</span>
                      <span class="shap-feat-val" style="color:${valColor}; font-weight:700; font-family:var(--font-mono);">
                        ${sign}${(Math.abs(f.contribution) * 100).toFixed(1)}%
                      </span>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>

          </div>

        </div>
      </div>
    `;
  }
}
