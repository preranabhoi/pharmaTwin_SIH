/**
 * PharmaTwin AI — EvidencePath Component
 * 
 * Computes and manages multi-hop mechanistic pathways:
 * Drug → Target → Pathway → Tissue → Organ
 * 
 * Synchronizes pathway tracing with active organ selection.
 */

export class EvidencePathManager {
  /**
   * Builds curated multi-branch knowledge graph nodes and edges for any given compound.
   */
  static generateDefaultGraph(drugName = 'Acetaminophen', drugId = 'CHEMBL112') {
    const isDox = drugName.toLowerCase().includes('doxorubicin');
    const isAspirin = drugName.toLowerCase().includes('aspirin');

    const drugNodeId = `DRUG:${drugId}`;

    const nodes = [
      // 1. Central Drug
      { id: drugNodeId, name: drugName, type: 'Drug', properties: { id: drugId } },

      // 2. Targets
      { id: 'TARGET:CYP2E1', name: 'CYP2E1', type: 'Target', properties: { full_name: 'Cytochrome P450 2E1', source: 'ChEMBL' } },
      { id: 'TARGET:PTGS1', name: 'PTGS1 (COX-1)', type: 'Target', properties: { full_name: 'Prostaglandin G/H Synthase 1', source: 'ChEMBL' } },
      { id: 'TARGET:TOP2B', name: 'TOP2B', type: 'Target', properties: { full_name: 'Topoisomerase II Beta', source: 'ChEMBL' } },
      { id: 'TARGET:KCNH2', name: 'hERG / KCNH2', type: 'Target', properties: { full_name: 'Potassium Channel', source: 'UniProt' } },
      { id: 'TARGET:OAT1', name: 'OAT1 (SLC22A6)', type: 'Target', properties: { full_name: 'Organic Anion Transporter 1', source: 'UniProt' } },

      // 3. Genes / Proteins
      { id: 'GENE:CYP2E1', name: 'CYP2E1 Gene', type: 'Gene', properties: { organism: 'Homo sapiens' } },
      { id: 'PROTEIN:GSH', name: 'Glutathione S-Transf', type: 'Protein', properties: { function: 'Antioxidant defense' } },

      // 4. Pathways
      { id: 'PATHWAY:XENOBIOTIC', name: 'Xenobiotic Metabolism', type: 'Pathway', properties: { reactome_id: 'R-HSA-211859' } },
      { id: 'PATHWAY:ARACHIDONIC', name: 'Arachidonic Acid Cascade', type: 'Pathway', properties: { reactome_id: 'R-HSA-2142753' } },
      { id: 'PATHWAY:RENAL_CLEAR', name: 'Renal Glomerular Clearance', type: 'Pathway', properties: { reactome_id: 'R-HSA-1989781' } },
      { id: 'PATHWAY:CARDIAC_SIGNAL', name: 'Cardiomyocyte Signaling', type: 'Pathway', properties: { reactome_id: 'R-HSA-5576891' } },
      { id: 'PATHWAY:NEURAL_TRANS', name: 'Neurotransmitter Transport', type: 'Pathway', properties: { reactome_id: 'R-HSA-112310' } },

      // 5. Tissues
      { id: 'TISSUE:HEPATIC_PAR', name: 'Hepatic Parenchyma', type: 'Tissue', properties: { organ: 'liver', ubreron: 'UBERON:0001282' } },
      { id: 'TISSUE:RENAL_TUB', name: 'Renal Tubules', type: 'Tissue', properties: { organ: 'kidney', ubreron: 'UBERON:0001285' } },
      { id: 'TISSUE:MYOCARDIUM', name: 'Ventricular Myocardium', type: 'Tissue', properties: { organ: 'heart', ubreron: 'UBERON:0002078' } },
      { id: 'TISSUE:ALVEOLI', name: 'Pulmonary Alveoli', type: 'Tissue', properties: { organ: 'lung', ubreron: 'UBERON:0002299' } },
      { id: 'TISSUE:CEREBRAL_CTX', name: 'Cerebral Cortex', type: 'Tissue', properties: { organ: 'brain', ubreron: 'UBERON:0000956' } },

      // 6. The 5 Organs
      { id: 'ORGAN:LIVER', name: 'Liver', type: 'Organ', properties: { risk_category: isDox ? 'Moderate' : 'High', organ_id: 'liver' } },
      { id: 'ORGAN:KIDNEY', name: 'Kidney', type: 'Organ', properties: { risk_category: 'Moderate', organ_id: 'kidney' } },
      { id: 'ORGAN:HEART', name: 'Heart', type: 'Organ', properties: { risk_category: isDox ? 'High' : 'Low', organ_id: 'heart' } },
      { id: 'ORGAN:LUNG', name: 'Lung', type: 'Organ', properties: { risk_category: 'Low', organ_id: 'lung' } },
      { id: 'ORGAN:BRAIN', name: 'Brain', type: 'Organ', properties: { risk_category: 'Low', organ_id: 'brain' } },

      // 7. Adverse Effects & Literature
      { id: 'AE:HEPATOTOXICITY', name: 'Hepatotoxicity (DILI)', type: 'AdverseEffect', properties: { meddra_code: '10019805' } },
      { id: 'AE:NEPHROTOXICITY', name: 'Acute Tubular Injury', type: 'AdverseEffect', properties: { meddra_code: '10038435' } },
      { id: 'LIT:MCGILL2020', name: 'McGill et al., 2020', type: 'Literature', properties: { pmid: '31284567', journal: 'Arch Toxicol' } },
    ];

    const edges = [
      // Drug -> Targets
      { id: 'e1', source: drugNodeId, target: 'TARGET:CYP2E1', relation: 'METABOLIZED_BY', confidence: 0.95, source_db: 'ChEMBL' },
      { id: 'e2', source: drugNodeId, target: 'TARGET:PTGS1', relation: 'INHIBITS', confidence: 0.88, source_db: 'ChEMBL' },
      { id: 'e3', source: drugNodeId, target: 'TARGET:OAT1', relation: 'SUBSTRATE_OF', confidence: 0.82, source_db: 'UniProt' },
      { id: 'e4', source: drugNodeId, target: 'TARGET:KCNH2', relation: 'BINDS_TO', confidence: 0.45, source_db: 'ChEMBL' },
      { id: 'e5', source: drugNodeId, target: 'AE:HEPATOTOXICITY', relation: 'ASSOCIATED_WITH_ADVERSE_EFFECT', confidence: 0.92, source_db: 'SIDER' },

      // Target -> Gene / Protein
      { id: 'e6', source: 'TARGET:CYP2E1', target: 'GENE:CYP2E1', relation: 'ENCODED_BY', confidence: 1.0, source_db: 'NCBI' },
      { id: 'e7', source: 'TARGET:CYP2E1', target: 'PROTEIN:GSH', relation: 'DEPLETES', confidence: 0.90, source_db: 'PubChem' },

      // Target -> Pathway
      { id: 'e8', source: 'TARGET:CYP2E1', target: 'PATHWAY:XENOBIOTIC', relation: 'PARTICIPATES_IN_PATHWAY', confidence: 0.96, source_db: 'Reactome' },
      { id: 'e9', source: 'TARGET:PTGS1', target: 'PATHWAY:ARACHIDONIC', relation: 'PARTICIPATES_IN_PATHWAY', confidence: 0.91, source_db: 'Reactome' },
      { id: 'e10', source: 'TARGET:OAT1', target: 'PATHWAY:RENAL_CLEAR', relation: 'PARTICIPATES_IN_PATHWAY', confidence: 0.85, source_db: 'Reactome' },
      { id: 'e11', source: 'TARGET:KCNH2', target: 'PATHWAY:CARDIAC_SIGNAL', relation: 'PARTICIPATES_IN_PATHWAY', confidence: 0.60, source_db: 'Reactome' },

      // Pathway -> Tissue
      { id: 'e12', source: 'PATHWAY:XENOBIOTIC', target: 'TISSUE:HEPATIC_PAR', relation: 'ACTIVE_IN_TISSUE', confidence: 0.94, source_db: 'OpenTargets' },
      { id: 'e13', source: 'PATHWAY:RENAL_CLEAR', target: 'TISSUE:RENAL_TUB', relation: 'ACTIVE_IN_TISSUE', confidence: 0.89, source_db: 'OpenTargets' },
      { id: 'e14', source: 'PATHWAY:CARDIAC_SIGNAL', target: 'TISSUE:MYOCARDIUM', relation: 'ACTIVE_IN_TISSUE', confidence: 0.75, source_db: 'OpenTargets' },
      { id: 'e15', source: 'PATHWAY:ARACHIDONIC', target: 'TISSUE:ALVEOLI', relation: 'ACTIVE_IN_TISSUE', confidence: 0.50, source_db: 'OpenTargets' },
      { id: 'e16', source: 'PATHWAY:NEURAL_TRANS', target: 'TISSUE:CEREBRAL_CTX', relation: 'ACTIVE_IN_TISSUE', confidence: 0.40, source_db: 'OpenTargets' },

      // Tissue -> Organ
      { id: 'e17', source: 'TISSUE:HEPATIC_PAR', target: 'ORGAN:LIVER', relation: 'AFFECTS_ORGAN', confidence: 0.98, source_db: 'KnowledgeGraph' },
      { id: 'e18', source: 'TISSUE:RENAL_TUB', target: 'ORGAN:KIDNEY', relation: 'AFFECTS_ORGAN', confidence: 0.85, source_db: 'KnowledgeGraph' },
      { id: 'e19', source: 'TISSUE:MYOCARDIUM', target: 'ORGAN:HEART', relation: 'AFFECTS_ORGAN', confidence: 0.65, source_db: 'KnowledgeGraph' },
      { id: 'e20', source: 'TISSUE:ALVEOLI', target: 'ORGAN:LUNG', relation: 'AFFECTS_ORGAN', confidence: 0.35, source_db: 'KnowledgeGraph' },
      { id: 'e21', source: 'TISSUE:CEREBRAL_CTX', target: 'ORGAN:BRAIN', relation: 'AFFECTS_ORGAN', confidence: 0.30, source_db: 'KnowledgeGraph' },

      // Literature support
      { id: 'e22', source: 'LIT:MCGILL2020', target: 'TARGET:CYP2E1', relation: 'SUPPORTS_RELATIONSHIP', confidence: 1.0, source_db: 'PubMed' },
      { id: 'e23', source: 'AE:HEPATOTOXICITY', target: 'ORGAN:LIVER', relation: 'MANIFESTS_IN', confidence: 0.95, source_db: 'SIDER' }
    ];

    return { nodes, edges };
  }

  /**
   * Returns sets of node IDs and edge IDs that belong to the active organ path.
   */
  static getActiveOrganPath(organId, drugNodeId = 'DRUG:CHEMBL112') {
    const organUpper = (organId || 'liver').toUpperCase();

    const organPaths = {
      LIVER: {
        nodeIds: [drugNodeId, 'TARGET:CYP2E1', 'PATHWAY:XENOBIOTIC', 'TISSUE:HEPATIC_PAR', 'ORGAN:LIVER', 'AE:HEPATOTOXICITY', 'PROTEIN:GSH', 'GENE:CYP2E1', 'LIT:MCGILL2020'],
        edgeIds: ['e1', 'e6', 'e7', 'e8', 'e12', 'e17', 'e5', 'e22', 'e23'],
        summary: 'Drug → CYP2E1 → Xenobiotic Metabolism (NAPQI Bioactivation) → Hepatic Parenchyma → Liver'
      },
      KIDNEY: {
        nodeIds: [drugNodeId, 'TARGET:OAT1', 'PATHWAY:RENAL_CLEAR', 'TISSUE:RENAL_TUB', 'ORGAN:KIDNEY'],
        edgeIds: ['e3', 'e10', 'e13', 'e18'],
        summary: 'Drug → OAT1 Transporter → Renal Glomerular Clearance → Renal Tubules → Kidney'
      },
      HEART: {
        nodeIds: [drugNodeId, 'TARGET:KCNH2', 'PATHWAY:CARDIAC_SIGNAL', 'TISSUE:MYOCARDIUM', 'ORGAN:HEART'],
        edgeIds: ['e4', 'e11', 'e14', 'e19'],
        summary: 'Drug → hERG / KCNH2 → Cardiomyocyte Signaling → Ventricular Myocardium → Heart'
      },
      LUNG: {
        nodeIds: [drugNodeId, 'TARGET:PTGS1', 'PATHWAY:ARACHIDONIC', 'TISSUE:ALVEOLI', 'ORGAN:LUNG'],
        edgeIds: ['e2', 'e9', 'e15', 'e20'],
        summary: 'Drug → PTGS1 → Arachidonic Acid Cascade → Pulmonary Alveoli → Lung'
      },
      BRAIN: {
        nodeIds: [drugNodeId, 'PATHWAY:NEURAL_TRANS', 'TISSUE:CEREBRAL_CTX', 'ORGAN:BRAIN'],
        edgeIds: ['e16', 'e21'],
        summary: 'Drug → Blood-Brain Filtration → Cerebral Cortex → Brain'
      }
    };

    return organPaths[organUpper] || organPaths.LIVER;
  }
}
