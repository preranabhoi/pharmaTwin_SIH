/**
 * PharmaTwin AI — Organ Component (SVG Representation)
 * 
 * Anatomically accurate vector paths for the 5 risk-bearing organs:
 * 1. Brain (Cerebral hemispheres + cerebellum)
 * 2. Lungs (Bilateral lobular lungs)
 * 3. Heart (Cardiac contours with aortic arch)
 * 4. Liver (Triangular right-hypochondriac wedge)
 * 5. Kidneys (Bilateral retroperitoneal renal contours)
 */

import { getRiskColor } from './organMap.js';

export class OrganRenderer {
  /**
   * Generates the SVG group for an organ with proper anatomical paths.
   */
  static renderOrgan(organId, organData, isSelected = false) {
    const riskColor = getRiskColor(organData?.category);
    const selectedClass = isSelected ? 'selected-organ' : '';
    const name = organData?.name || organId;
    const score = organData ? (organData.risk * 100).toFixed(1) + '%' : '--%';
    const category = organData?.category || 'Low';

    switch (organId) {
      case 'brain':
        return `
          <g id="svg-organ-brain" class="organ-interactive-group ${selectedClass}" data-organ="brain"
             tabindex="0" role="button" aria-label="Brain: ${category} risk (${score})">
            <!-- Brain Glow Filter Target -->
            <path class="organ-base-path" d="M 155 36 
                     C 155 24, 163 18, 170 18 
                     C 177 18, 185 24, 185 36 
                     C 192 38, 195 48, 193 56 
                     C 190 64, 182 66, 178 65 
                     C 174 67, 166 67, 162 65 
                     C 158 66, 150 64, 147 56 
                     C 145 48, 148 38, 155 36 Z" 
                  fill="${riskColor}" 
                  stroke="#ffffff" 
                  stroke-width="1.5" />
            <!-- Sulci / Gyri Details -->
            <path d="M 170 20 L 170 63 
                     M 160 32 C 165 35, 166 42, 163 48
                     M 180 32 C 175 35, 174 42, 177 48
                     M 155 45 C 160 48, 162 55, 159 58
                     M 185 45 C 180 48, 178 55, 181 58" 
                  fill="none" 
                  stroke="rgba(255,255,255,0.6)" 
                  stroke-width="1.2" 
                  stroke-linecap="round" />
            <!-- Anchor Dot -->
            <circle cx="142" cy="46" r="3.5" class="organ-anchor-dot" fill="${riskColor}" stroke="#ffffff" stroke-width="1" />
          </g>
        `;

      case 'lung':
        return `
          <g id="svg-organ-lung" class="organ-interactive-group ${selectedClass}" data-organ="lung"
             tabindex="0" role="button" aria-label="Lungs: ${category} risk (${score})">
            <!-- Left Lung (Viewer Right) -->
            <path class="organ-base-path" d="M 186 106 
                     C 188 100, 198 100, 201 106 
                     C 214 116, 218 136, 215 152 
                     C 212 162, 202 165, 196 162 
                     C 192 160, 190 152, 188 145 
                     C 186 136, 185 120, 186 106 Z" 
                  fill="${riskColor}" 
                  stroke="#ffffff" 
                  stroke-width="1.5" />
            <!-- Right Lung (Viewer Left) -->
            <path class="organ-base-path" d="M 154 106 
                     C 152 100, 142 100, 139 106 
                     C 126 116, 122 136, 125 152 
                     C 128 162, 138 165, 144 162 
                     C 148 160, 150 152, 152 145 
                     C 154 136, 155 120, 154 106 Z" 
                  fill="${riskColor}" 
                  stroke="#ffffff" 
                  stroke-width="1.5" />
            <!-- Bronchial Tree Hints -->
            <path d="M 170 100 L 170 114 
                     M 170 114 L 160 125 M 160 125 L 152 138 M 160 125 L 164 136
                     M 170 114 L 180 125 M 180 125 L 188 138 M 180 125 L 176 136" 
                  fill="none" 
                  stroke="rgba(255,255,255,0.7)" 
                  stroke-width="1.2" 
                  stroke-linecap="round" />
            <!-- Anchor Dot -->
            <circle cx="122" cy="126" r="3.5" class="organ-anchor-dot" fill="${riskColor}" stroke="#ffffff" stroke-width="1" />
          </g>
        `;

      case 'heart':
        return `
          <g id="svg-organ-heart" class="organ-interactive-group ${selectedClass}" data-organ="heart"
             tabindex="0" role="button" aria-label="Heart: ${category} risk (${score})">
            <!-- Cardiac Silhouette (Anatomical orientation tilted towards left ventricle) -->
            <path class="organ-base-path" d="M 166 122 
                     C 166 114, 176 114, 180 120 
                     C 184 114, 194 114, 194 122 
                     C 194 134, 185 146, 175 156 
                     C 165 146, 166 134, 166 122 Z" 
                  fill="${riskColor}" 
                  stroke="#ffffff" 
                  stroke-width="1.5" />
            <!-- Aorta and Pulmonary Trunk Arc -->
            <path d="M 174 120 C 174 112, 184 110, 186 116
                     M 178 126 C 176 134, 172 142, 175 152" 
                  fill="none" 
                  stroke="rgba(255,255,255,0.7)" 
                  stroke-width="1.2" 
                  stroke-linecap="round" />
            <!-- Anchor Dot -->
            <circle cx="182" cy="138" r="3.5" class="organ-anchor-dot" fill="${riskColor}" stroke="#ffffff" stroke-width="1" />
          </g>
        `;

      case 'liver':
        return `
          <g id="svg-organ-liver" class="organ-interactive-group ${selectedClass}" data-organ="liver"
             tabindex="0" role="button" aria-label="Liver: ${category} risk (${score})">
            <!-- Anatomical Hepatic Wedge -->
            <path class="organ-base-path" d="M 142 166 
                     C 158 162, 184 162, 196 172 
                     C 198 180, 192 192, 185 194 
                     C 168 196, 150 192, 140 186 
                     C 134 180, 134 172, 142 166 Z" 
                  fill="${riskColor}" 
                  stroke="#ffffff" 
                  stroke-width="1.5" />
            <!-- Hepatic Lobes Separation & Gallbladder Notch -->
            <path d="M 170 164 C 172 174, 171 184, 168 193
                     M 152 172 C 160 174, 178 174, 186 180" 
                  fill="none" 
                  stroke="rgba(255,255,255,0.6)" 
                  stroke-width="1.1" 
                  stroke-linecap="round" />
            <!-- Anchor Dot -->
            <circle cx="135" cy="180" r="3.5" class="organ-anchor-dot" fill="${riskColor}" stroke="#ffffff" stroke-width="1" />
          </g>
        `;

      case 'kidney':
        return `
          <g id="svg-organ-kidney" class="organ-interactive-group ${selectedClass}" data-organ="kidney"
             tabindex="0" role="button" aria-label="Kidneys: ${category} risk (${score})">
            <!-- Left Kidney (Viewer Left) -->
            <path class="organ-base-path" d="M 144 208 
                     C 152 208, 154 216, 152 224 
                     C 150 230, 144 232, 139 228 
                     C 134 224, 134 214, 139 209 
                     C 141 208, 143 208, 144 208 Z" 
                  fill="${riskColor}" 
                  stroke="#ffffff" 
                  stroke-width="1.5" />
            <!-- Right Kidney (Viewer Right) -->
            <path class="organ-base-path" d="M 196 212 
                     C 204 212, 206 220, 204 228 
                     C 202 234, 196 236, 191 232 
                     C 186 228, 186 218, 191 213 
                     C 193 212, 195 212, 196 212 Z" 
                  fill="${riskColor}" 
                  stroke="#ffffff" 
                  stroke-width="1.5" />
            <!-- Renal Hilum and Cortex details -->
            <path d="M 148 218 C 146 222, 145 224, 148 226
                     M 192 222 C 194 226, 195 228, 192 230" 
                  fill="none" 
                  stroke="rgba(255,255,255,0.7)" 
                  stroke-width="1.1" 
                  stroke-linecap="round" />
            <!-- Anchor Dot -->
            <circle cx="202" cy="220" r="3.5" class="organ-anchor-dot" fill="${riskColor}" stroke="#ffffff" stroke-width="1" />
          </g>
        `;

      default:
        return '';
    }
  }
}
