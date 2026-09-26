/**
 * PharmaTwin AI — 3D Interactive Human Virtual Twin Engine
 * 
 * Powered by Three.js & GLTFLoader
 * Renders an anatomical human model with spatially aligned internal organs.
 * Strictly a computational research decision-support visualization, NOT a clinical diagnostic system.
 */

export const ORGAN_MESH_MAP = {
  brain: ['Brain', 'brain', 'cns', 'cerebrum', 'cerebellum', 'hemisphere'],
  heart: ['Heart', 'heart', 'cardiac', 'myocardium', 'aorta'],
  lung: ['Left_Lung', 'Right_Lung', 'LeftLung', 'RightLung', 'Lung', 'lung', 'lungs'],
  liver: ['Liver', 'liver', 'hepatic'],
  kidney: ['Left_Kidney', 'Right_Kidney', 'LeftKidney', 'RightKidney', 'Kidney', 'kidney', 'kidneys'],
  gastrointestinal: ['Stomach', 'Intestine', 'GI_Tract', 'stomach', 'intestine', 'gastrointestinal', 'digestive'],
};

export class HumanVirtualTwin {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = Object.assign({
      onOrganClick: () => {},
      onOrganHover: () => {},
      isAutoRotate: false,
    }, options);

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    this.modelRoot = null;
    this.bodyMesh = null;
    this.organMeshes = {};
    this.organData = {};
    this.hoveredOrgan = null;
    this.selectedOrgan = null;
    this.isAutoRotate = this.options.isAutoRotate;

    this.animationFrameId = null;
    this.clock = new THREE.Clock();

    this.init();
  }

  init() {
    if (!this.container) return;

    const width = this.container.clientWidth || 360;
    const height = this.container.clientHeight || 380;

    // 1. Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xf8fafc); // Scientific clean light background

    // 2. Camera (Framed to show complete human figure from head to feet)
    this.camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 50);
    this.camera.position.set(0, 0.95, 2.75);

    // 3. Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    this.renderer.shadowMap.enabled = false;
    this.container.appendChild(this.renderer.domElement);

    // 4. OrbitControls
    if (typeof THREE.OrbitControls !== 'undefined') {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.08;
      this.controls.target.set(0, 0.90, 0); // Center of human body
      this.controls.minDistance = 0.8;
      this.controls.maxDistance = 5.0;
      this.controls.maxPolarAngle = Math.PI / 2 + 0.1; // Don't flip under floor
      this.controls.autoRotate = this.isAutoRotate;
      this.controls.autoRotateSpeed = 1.2;
    }

    // 5. Studio Lighting (Clean, Shadowless Medical Visualization)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    this.scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 0.7);
    keyLight.position.set(4, 6, 4);
    this.scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x94a3b8, 0.5);
    fillLight.position.set(-4, 3, -2);
    this.scene.add(fillLight);

    const rimLight = new THREE.PointLight(0x38bdf8, 0.4, 8);
    rimLight.position.set(0, 2.2, -1.8);
    this.scene.add(rimLight);

    // 6. Ground Grid Plate
    this.buildGridFloor();

    // 7. Load GLB Model
    this.loadGLBModel();

    // 8. Interaction Listeners
    this.bindEvents();

    // 9. Animation Loop
    this.animate();
  }

  buildGridFloor() {
    const gridHelper = new THREE.GridHelper(3.0, 12, 0xcbd5e1, 0xe2e8f0);
    gridHelper.position.y = -0.01; // Just beneath feet
    gridHelper.material.opacity = 0.45;
    gridHelper.material.transparent = true;
    this.scene.add(gridHelper);
  }

  loadGLBModel() {
    const showLoading = () => {
      const tooltip = document.getElementById('twin-hud-tooltip');
      if (tooltip) {
        tooltip.style.display = 'block';
        tooltip.style.left = '50%';
        tooltip.style.top = '50%';
        tooltip.style.transform = 'translate(-50%, -50%)';
        tooltip.innerHTML = '<span style="color:#64748b; font-size:0.75rem;">Loading Human Virtual Twin...</span>';
      }
    };

    const hideLoading = () => {
      const tooltip = document.getElementById('twin-hud-tooltip');
      if (tooltip) {
        tooltip.style.display = 'none';
        tooltip.style.transform = 'none';
      }
    };

    showLoading();

    const modelUrls = ['/models/human_twin.glb', '/public/models/human_twin.glb', 'models/human_twin.glb'];
    let attemptIdx = 0;

    const tryLoad = (url) => {
      if (typeof THREE.GLTFLoader === 'undefined') {
        console.warn('[PharmaTwin 3D] GLTFLoader not available on window.');
        hideLoading();
        return;
      }

      const loader = new THREE.GLTFLoader();
      loader.load(
        url,
        (gltf) => {
          hideLoading();
          this.setupAnatomicalModel(gltf.scene);
        },
        undefined,
        (err) => {
          attemptIdx++;
          if (attemptIdx < modelUrls.length) {
            tryLoad(modelUrls[attemptIdx]);
          } else {
            console.error('[PharmaTwin 3D] Failed to load human GLB asset from all paths:', err);
            hideLoading();
          }
        }
      );
    };

    tryLoad(modelUrls[0]);
  }

  setupAnatomicalModel(scene) {
    this.modelRoot = scene;
    this.organMeshes = {};

    // Neutral translucent medical silhouette material for outer body
    const bodyMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x94a3b8,
      transparent: true,
      opacity: 0.16,
      roughness: 0.25,
      metalness: 0.05,
      transmission: 0.75,
      ior: 1.2,
      depthWrite: false,
    });

    const devMeshNames = [];

    scene.traverse((child) => {
      if (child.isMesh) {
        const meshName = child.name || '';
        devMeshNames.push(meshName);

        // Identify organ vs body silhouette
        let matchedOrganId = null;
        for (const [organId, aliases] of Object.entries(ORGAN_MESH_MAP)) {
          if (aliases.some(alias => meshName.toLowerCase().includes(alias.toLowerCase()))) {
            matchedOrganId = organId;
            break;
          }
        }

        if (matchedOrganId) {
          if (!this.organMeshes[matchedOrganId]) {
            this.organMeshes[matchedOrganId] = [];
          }
          this.organMeshes[matchedOrganId].push(child);

          // Normal resting anatomical material (subtle resting tissue tone)
          child.material = new THREE.MeshStandardMaterial({
            color: 0x94a3b8,
            roughness: 0.4,
            metalness: 0.1,
            transparent: true,
            opacity: 0.85,
            emissive: 0x000000,
            emissiveIntensity: 0.0,
          });

          child.userData = {
            organId: matchedOrganId,
            meshName: meshName,
            isOrgan: true,
            baseColor: 0x94a3b8,
          };
        } else {
          // Body silhouette container
          this.bodyMesh = child;
          child.material = bodyMaterial;
          child.userData = { isBodySilhouette: true };
        }
      }
    });

    console.info(`[PharmaTwin 3D] Anatomical Human Virtual Twin loaded. Meshes: [${devMeshNames.join(', ')}]`);

    // Ensure model is centered at origin with feet at y=0
    const bbox = new THREE.Box3().setFromObject(scene);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    bbox.getSize(size);
    bbox.getCenter(center);

    // Adjust position so feet are on the floor grid (y=0) and center is at x=0, z=0
    scene.position.x = -center.x;
    scene.position.y = -bbox.min.y;
    scene.position.z = -center.z;

    this.scene.add(scene);

    // If organ risk data was set before GLB loaded, update now
    if (Object.keys(this.organData).length > 0) {
      this.updateOrganRisks(this.organData);
    }

    // Set initial full-body camera position
    this.setCameraPreset('all');
  }

  updateOrganRisks(organsData) {
    if (!organsData) return;
    this.organData = organsData;

    const riskColorMap = {
      Low: { color: 0x16a34a, emissive: 0x15803d, intensity: 0.35 },
      Moderate: { color: 0xd97706, emissive: 0xb45309, intensity: 0.55 },
      High: { color: 0xdc2626, emissive: 0xb91c1c, intensity: 0.85 },
    };

    const restingColor = { color: 0x94a3b8, emissive: 0x000000, intensity: 0.0 };

    for (const [organId, meshList] of Object.entries(this.organMeshes)) {
      const organDetail = organsData[organId];
      const hasElevatedRisk = organDetail && organDetail.risk > 0;
      const category = organDetail?.category || 'Low';

      const config = hasElevatedRisk ? (riskColorMap[category] || riskColorMap['Low']) : restingColor;

      meshList.forEach((mesh) => {
        if (mesh.material) {
          mesh.material.color.setHex(config.color);
          mesh.material.emissive.setHex(config.emissive);
          mesh.material.emissiveIntensity = config.intensity;
          mesh.userData.riskCategory = category;
          mesh.userData.hasElevatedRisk = hasElevatedRisk;
        }
      });
    }
  }

  bindEvents() {
    this.container.addEventListener('mousemove', (e) => {
      const rect = this.container.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      this.checkHover(e);
    });

    this.container.addEventListener('click', (e) => {
      this.handleClick(e);
    });

    window.addEventListener('resize', () => this.onWindowResize());
  }

  checkHover(e) {
    if (!this.modelRoot) return;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const organMeshes = this.getAllSelectableOrganMeshes();
    const intersects = this.raycaster.intersectObjects(organMeshes, false);

    const tooltip = document.getElementById('twin-hud-tooltip');

    if (intersects.length > 0) {
      const topMesh = intersects[0].object;
      const organId = topMesh.userData.organId;

      if (organId && this.hoveredOrgan !== organId) {
        this.hoveredOrgan = organId;
        this.container.style.cursor = 'pointer';

        if (tooltip && this.organData[organId]) {
          const detail = this.organData[organId];
          tooltip.style.display = 'block';
          tooltip.innerHTML = `
            <div style="font-weight:700;font-size:0.82rem;color:#0f172a;">${detail.name}</div>
            <div style="font-size:0.7rem;color:#64748b;">${detail.system || 'Organ System'}</div>
            <div style="margin-top:4px;display:flex;align-items:center;gap:6px;">
              <span class="badge-risk ${detail.category.toLowerCase()}">${detail.category}</span>
              <span style="font-family:monospace;font-size:0.78rem;font-weight:700;">${(detail.risk * 100).toFixed(1)}%</span>
            </div>
          `;
        }
      }

      if (tooltip) {
        const rect = this.container.getBoundingClientRect();
        tooltip.style.left = `${e.clientX - rect.left + 12}px`;
        tooltip.style.top = `${e.clientY - rect.top + 12}px`;
      }
    } else {
      if (this.hoveredOrgan) {
        this.hoveredOrgan = null;
        this.container.style.cursor = 'default';
        if (tooltip) tooltip.style.display = 'none';
      }
    }
  }

  handleClick(e) {
    if (!this.modelRoot) return;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const organMeshes = this.getAllSelectableOrganMeshes();
    const intersects = this.raycaster.intersectObjects(organMeshes, false);

    if (intersects.length > 0) {
      const topMesh = intersects[0].object;
      const organId = topMesh.userData.organId;
      if (organId) {
        this.selectedOrgan = organId;
        this.focusCameraOnOrgan(organId);
        this.options.onOrganClick(organId);
      }
    }
  }

  focusCameraOnOrgan(organId) {
    const targets = {
      brain: { y: 1.68, z: 1.05 },
      heart: { y: 1.30, z: 1.15 },
      lung: { y: 1.30, z: 1.25 },
      liver: { y: 1.10, z: 1.15 },
      kidney: { y: 0.98, z: 1.15 },
      gastrointestinal: { y: 0.95, z: 1.20 },
      default: { y: 0.90, z: 2.75 },
    };

    const target = targets[organId] || targets.default;
    this.animateCameraTo(target.y, target.z);
  }

  animateCameraTo(targetY, targetZ) {
    if (this.controls) {
      this.controls.target.set(0, targetY, 0);
    }

    const startY = this.camera.position.y;
    const startZ = this.camera.position.z;
    let t = 0;

    const step = () => {
      t += 0.08;
      this.camera.position.y = THREE.MathUtils.lerp(startY, targetY + 0.05, t);
      this.camera.position.z = THREE.MathUtils.lerp(startZ, targetZ, t);
      if (t < 1.0) {
        requestAnimationFrame(step);
      }
    };
    step();
  }

  getAllSelectableOrganMeshes() {
    const list = [];
    for (const meshList of Object.values(this.organMeshes)) {
      list.push(...meshList);
    }
    return list;
  }

  setCameraPreset(preset) {
    switch (preset) {
      case 'head':
        this.focusCameraOnOrgan('brain');
        break;
      case 'thorax':
        this.focusCameraOnOrgan('heart');
        break;
      case 'abdomen':
        this.focusCameraOnOrgan('liver');
        break;
      case 'all':
      default:
        if (this.controls) {
          this.controls.target.set(0, 0.90, 0);
        }
        this.animateCameraTo(0.90, 2.75);
        if (this.modelRoot) this.modelRoot.rotation.y = 0;
        break;
    }
  }

  toggleAutoRotate() {
    this.isAutoRotate = !this.isAutoRotate;
    if (this.controls) {
      this.controls.autoRotate = this.isAutoRotate;
    }
    return this.isAutoRotate;
  }

  onWindowResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  animate() {
    this.animationFrameId = requestAnimationFrame(() => this.animate());

    const time = this.clock.getElapsedTime();

    if (this.controls) {
      this.controls.update();
    }

    // High risk subtle pulse for critical organs
    for (const meshList of Object.values(this.organMeshes)) {
      meshList.forEach((mesh) => {
        if (mesh.userData.riskCategory === 'High' && mesh.material) {
          const pulse = 0.65 + 0.3 * Math.sin(time * 3.5);
          mesh.material.emissiveIntensity = pulse;
        }
      });
    }

    this.renderer.render(this.scene, this.camera);
  }

  destroy() {
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    if (this.renderer && this.renderer.domElement) {
      this.renderer.domElement.remove();
      this.renderer.dispose();
    }
  }
}
