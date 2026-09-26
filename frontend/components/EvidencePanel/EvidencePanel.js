/**
 * PharmaTwin AI — EvidencePanel Component
 * 
 * Renders Multi-Source Biomedical Evidence Summary:
 * - PubChem Compound Identifiers
 * - ChEMBL Bioactivity Assays
 * - UniProt Functional Annotations
 * - OpenTargets Genetics & Pathways
 * - SIDER Clinical Adverse Reactions
 * - PubMed Peer-Reviewed Literature
 */

export class EvidencePanel {
  static render(evidenceData = null) {
    const s = evidenceData?.sources || {};

    const sources = [
      { name: 'PubChem', desc: 'Structure & Identifiers', count: s.pubchem?.evidence_count ?? 1, icon: '🧪', unit: 'Record' },
      { name: 'ChEMBL', desc: 'Bioactivities & Assays', count: s.chembl?.evidence_count ?? 4, icon: '🎯', unit: 'Targets' },
      { name: 'UniProt', desc: 'Protein Annotations', count: s.uniprot?.evidence_count ?? 4, icon: '🧬', unit: 'Proteins' },
      { name: 'OpenTargets', desc: 'Genetics & Disease Paths', count: s.opentargets?.evidence_count ?? 3, icon: '⚡', unit: 'Pathways' },
      { name: 'SIDER', desc: 'Post-Market ADRs', count: s.sider?.evidence_count ?? 8, icon: '⚠️', unit: 'Events' },
      { name: 'PubMed', desc: 'Literature Citations', count: s.pubmed?.evidence_count ?? 5, icon: '📄', unit: 'Articles' }
    ];

    return `
      <div class="card" id="card-evidence-summary-root">
        <div class="card-header">
          <div class="card-title">
            <span class="card-title-icon">📚</span>
            <span>Biomedical Evidence Sources</span>
          </div>
          <button id="btn-open-evidence-vault-modal" class="btn-secondary" style="padding:0.2rem 0.5rem; font-size:0.7rem;">
            Open Vault
          </button>
        </div>

        <div class="evidence-sources-strip">
          ${sources.map(src => `
            <div class="ev-source-chip">
              <span class="ev-src-icon">${src.icon}</span>
              <div class="ev-src-info">
                <span class="ev-src-name">${src.name}</span>
                <span class="ev-src-count">${src.count} ${src.unit}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}
