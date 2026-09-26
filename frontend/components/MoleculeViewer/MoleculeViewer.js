/**
 * PharmaTwin AI — MoleculeViewer Component
 * 
 * Renders 2D Chemical Structure SVG depiction and physicochemical property grid.
 */

export class MoleculeViewer {
  static render(molData = null, smiles = 'CC(=O)Nc1ccc(O)cc1') {
    const formula = molData?.formula || molData?.molecule?.formula || 'C8H9NO2';
    const d = molData?.descriptors || {
      molecular_weight: 151.16,
      logp: 1.35,
      tpsa: 49.33,
      hbd: 2,
      hba: 2,
      rotatable_bonds: 1,
      aromatic_rings: 1
    };

    const mw = typeof d.molecular_weight === 'number' ? d.molecular_weight.toFixed(2) : '151.16';
    const logp = typeof d.logp === 'number' ? d.logp.toFixed(2) : '1.35';
    const tpsa = typeof d.tpsa === 'number' ? d.tpsa.toFixed(1) : '49.3';
    const hbdHba = `${d.hbd ?? 2} / ${d.hba ?? 2}`;
    const rotbonds = d.rotatable_bonds ?? 1;
    const rings = d.aromatic_ring_count ?? d.aromatic_rings ?? 1;

    let svgHtml = molData?.svg_image || molData?.svg_depiction || '';
    if (!svgHtml) {
      // Default clean fallback 2D depiction for Acetaminophen / candidate
      svgHtml = `
        <svg viewBox="0 0 200 120" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <!-- Benzene Ring -->
          <polygon points="100,35 125,50 125,80 100,95 75,80 75,50" fill="none" stroke="#2563eb" stroke-width="2.5" />
          <polygon points="100,42 119,53 119,77 100,88 81,77 81,53" fill="none" stroke="#2563eb" stroke-width="1.2" stroke-dasharray="3,3" />
          <!-- Hydroxyl (-OH) -->
          <line x1="100" y1="95" x2="100" y2="112" stroke="#dc2626" stroke-width="2.5" />
          <text x="100" y="120" font-family="var(--font-sans)" font-size="11" font-weight="700" fill="#dc2626" text-anchor="middle">OH</text>
          <!-- Amide (-NH-CO-CH3) -->
          <line x1="100" y1="35" x2="100" y2="20" stroke="#7c3aed" stroke-width="2.5" />
          <text x="100" y="16" font-family="var(--font-sans)" font-size="11" font-weight="700" fill="#7c3aed" text-anchor="middle">NH</text>
          <line x1="108" y1="12" x2="128" y2="12" stroke="#0f172a" stroke-width="2.5" />
          <line x1="128" y1="12" x2="140" y2="24" stroke="#0f172a" stroke-width="2.5" />
          <line x1="126" y1="12" x2="126" y2="0" stroke="#dc2626" stroke-width="2.5" />
          <line x1="130" y1="12" x2="130" y2="0" stroke="#dc2626" stroke-width="2.5" />
          <text x="128" y="-2" font-family="var(--font-sans)" font-size="9" font-weight="700" fill="#dc2626" text-anchor="middle">O</text>
          <text x="148" y="32" font-family="var(--font-sans)" font-size="10" font-weight="700" fill="#0f172a" text-anchor="middle">CH3</text>
        </svg>
      `;
    }

    return `
      <div class="card" id="card-mol-view-root">
        <div class="card-header">
          <div class="card-title">
            <span class="card-title-icon">🔬</span>
            <span>2D Molecular Structure</span>
          </div>
          <span class="badge-risk low" id="mol-formula-badge">${formula}</span>
        </div>

        <div class="mol-view-container">
          <div class="mol-svg-frame" id="mol-svg-frame">
            ${svgHtml}
          </div>

          <div class="prop-grid">
            <div class="prop-card">
              <span class="prop-label">Mol Weight</span>
              <span class="prop-val" id="prop-mw">${mw}</span>
            </div>
            <div class="prop-card">
              <span class="prop-label">LogP</span>
              <span class="prop-val" id="prop-logp">${logp}</span>
            </div>
            <div class="prop-card">
              <span class="prop-label">TPSA (Å²)</span>
              <span class="prop-val" id="prop-tpsa">${tpsa}</span>
            </div>
            <div class="prop-card">
              <span class="prop-label">HBD / HBA</span>
              <span class="prop-val" id="prop-hbd-hba">${hbdHba}</span>
            </div>
            <div class="prop-card">
              <span class="prop-label">Rot. Bonds</span>
              <span class="prop-val" id="prop-rotbonds">${rotbonds}</span>
            </div>
            <div class="prop-card">
              <span class="prop-label">Aromatic</span>
              <span class="prop-val" id="prop-aromatic">${rings} ring${rings > 1 ? 's' : ''}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
