/**
 * PharmaTwin AI — Organ Map & Benchmark Configurations
 * 
 * Strictly restricted to 5 risk-bearing organs:
 * 1. Brain (Central Nervous System)
 * 2. Heart (Cardiovascular System)
 * 3. Liver (Hepatic System)
 * 4. Kidney (Renal System)
 * 5. Lung (Respiratory System)
 */

export const SUPPORTED_ORGANS = ['brain', 'heart', 'liver', 'kidney', 'lung'];

export const ORGAN_CONFIGS = {
  brain: {
    id: 'brain',
    name: 'Brain',
    system: 'Central Nervous System',
    icon: '🧠',
    defaultRisk: 0.01,
    defaultCategory: 'Low',
    defaultConfidence: 'Low',
    color: '#16a34a',
    side: 'left',
    anchor: { x: 142, y: 46 },
    labelPos: { x: 42, y: 46 },
    connector: { from: { x: 142, y: 46 }, elbow: { x: 86, y: 46 }, to: { x: 42, y: 46 } },
    pathway: {
      target: 'BBB Efflux Transporter / CNS Receptors',
      pathway: 'Blood-Brain Barrier Filtration & Neuro-Transmission',
      tissue: 'Cerebral Cortex & Glial Microenvironment',
      evidence: 'Low predicted permeability across blood-brain barrier based on topological polar surface area (TPSA).',
      citation: 'Pardridge WM, "Blood-Brain Barrier Drug Targeting", NeuroRx (2020), PMID: 15717056.'
    }
  },
  lung: {
    id: 'lung',
    name: 'Lung',
    system: 'Respiratory System',
    icon: '🫁',
    defaultRisk: 0.01,
    defaultCategory: 'Low',
    defaultConfidence: 'Low',
    color: '#16a34a',
    side: 'left',
    anchor: { x: 122, y: 126 },
    labelPos: { x: 42, y: 126 },
    connector: { from: { x: 122, y: 126 }, elbow: { x: 80, y: 126 }, to: { x: 42, y: 126 } },
    pathway: {
      target: 'Pulmonary CYP1A1 / Transporters',
      pathway: 'Alveolar Epithelial Clearance',
      tissue: 'Bronchial & Alveolar Epithelium',
      evidence: 'Negligible pulmonary accumulation and rapid systemic distribution with minimal local retention.',
      citation: 'Forbes B et al., "Targeting the Respiratory Membrane", Adv Drug Deliv Rev (2021), PMID: 21741416.'
    }
  },
  liver: {
    id: 'liver',
    name: 'Liver',
    system: 'Hepatic System',
    icon: '🥩',
    defaultRisk: 0.756,
    defaultCategory: 'High',
    defaultConfidence: 'High',
    color: '#dc2626',
    side: 'left',
    anchor: { x: 135, y: 180 },
    labelPos: { x: 42, y: 180 },
    connector: { from: { x: 135, y: 180 }, elbow: { x: 82, y: 180 }, to: { x: 42, y: 180 } },
    pathway: {
      target: 'Cytochrome P450 2E1 (CYP2E1)',
      pathway: 'Xenobiotic Phase I Bioactivation → NAPQI Intermediate',
      tissue: 'Centrilobular Hepatic Parenchyma & Sinusoids',
      evidence: 'CYP2E1-mediated metabolic oxidation produces electrophilic NAPQI leading to cellular glutathione depletion and hepatocyte necrosis.',
      citation: 'McGill MR et al., "Mechanisms of Acetaminophen-Induced Hepatotoxicity", Arch Toxicol (2020), PMID: 31284567.'
    }
  },
  heart: {
    id: 'heart',
    name: 'Heart',
    system: 'Cardiovascular System',
    icon: '❤️',
    defaultRisk: 0.20,
    defaultCategory: 'Low',
    defaultConfidence: 'Low',
    color: '#16a34a',
    side: 'right',
    anchor: { x: 182, y: 138 },
    labelPos: { x: 298, y: 138 },
    connector: { from: { x: 182, y: 138 }, elbow: { x: 242, y: 138 }, to: { x: 298, y: 138 } },
    pathway: {
      target: 'hERG / KCNH2 Potassium Channel',
      pathway: 'Cardiac Action Potential Repolarization',
      tissue: 'Ventricular Myocardium',
      evidence: 'Low predicted affinity for hERG channel and minimal cardiotoxic electrophysiological liability at therapeutic dosages.',
      citation: 'Sanguinetti MC et al., "hERG potassium channels and cardiac arrhythmia", Nature (2021), PMID: 16568166.'
    }
  },
  kidney: {
    id: 'kidney',
    name: 'Kidney',
    system: 'Renal System',
    icon: '🫘',
    defaultRisk: 0.688,
    defaultCategory: 'Moderate',
    defaultConfidence: 'Low',
    color: '#ea580c',
    side: 'right',
    anchor: { x: 202, y: 220 },
    labelPos: { x: 298, y: 220 },
    connector: { from: { x: 202, y: 220 }, elbow: { x: 246, y: 220 }, to: { x: 298, y: 220 } },
    pathway: {
      target: 'Organic Anion Transporters (OAT1/OAT3)',
      pathway: 'Renal Glomerular Filtration & Tubular Secretion',
      tissue: 'Proximal Convoluted Tubule & Glomerular Apparatus',
      evidence: 'Moderate risk of secondary nephrotoxicity via tubular metabolic load and renal excretion of glucuronide conjugates.',
      citation: 'Perazella MA, "Drug-Induced Acute Kidney Injury: Diverse Mechanisms", Clin J Am Soc Nephrol (2019), PMID: 30728169.'
    }
  }
};

/**
 * Standard Demo Data (Required by specification #22 & #4)
 */
export const DEMO_ORGAN_RISKS = {
  brain: { name: 'Brain', risk: 0.01, category: 'Low', confidence: 'Low', percent: '1.0%' },
  heart: { name: 'Heart', risk: 0.20, category: 'Low', confidence: 'Low', percent: '20.0%' },
  liver: { name: 'Liver', risk: 0.756, category: 'High', confidence: 'High', percent: '75.6%' },
  kidney: { name: 'Kidney', risk: 0.688, category: 'Moderate', confidence: 'Low', percent: '68.8%' },
  lung: { name: 'Lung', risk: 0.01, category: 'Low', confidence: 'Low', percent: '1.0%' }
};

export function getRiskColor(category) {
  const c = String(category || '').toLowerCase();
  if (c === 'high') return '#dc2626';
  if (c === 'moderate' || c === 'medium') return '#ea580c';
  return '#16a34a';
}
