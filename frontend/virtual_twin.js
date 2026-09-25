/**
 * PharmaTwin AI — 3D Interactive Human Virtual Twin Engine
 * 
 * Powered by Three.js
 * Visualizes AI-derived organ risk outputs on an interactive 3D anatomical model.
 * Strictly presents computational risk signals, not a clinical diagnostic digital twin.
 */

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

    const width = this.container.clientWidth || 600;
    const height = this.container.clientHeight || 550;

    // 1. Scene
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x07090e, 0.12);

    // 2. Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    this.camera.position.set(0, 1.0, 4.5);

    // 3. Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.2;
    this.container.appendChild(this.renderer.domElement);

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    this.scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 2.0);
    dirLight1.position.set(5, 8, 5);
    this.scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xa855f7, 1.5);
    dirLight2.position.set(-5, -2, -5);
    this.scene.add(dirLight2);

    const pointLight = new THREE.PointLight(0x06b6d4, 2.5, 8);
    pointLight.position.set(0, 1.2, 1.5);
    this.scene.add(pointLight);

    // 5. Build Holographic Body & Anatomical Organs
    this.buildBodySilhouette();
    this.buildAnatomicalOrgans();
    this.buildGridFloor();

    // 6. Interaction Listeners
    this.bindEvents();

    // 7. Animation Loop
    this.animate();
  }

  buildGridFloor() {
    const gridHelper = new THREE.GridHelper(6, 24, 0x06b6d4, 0x1e293b);
    gridHelper.position.y = -1.5;
    gridHelper.material.opacity = 0.35;
    gridHelper.material.transparent = true;
    this.scene.add(gridHelper);
  }

  buildBodySilhouette() {
    const bodyGroup = new THREE.Group();
    const bodyMat = new THREE.MeshPhysicalMaterial({
      color: 0x0ea5e9,
      transparent: true,
      opacity: 0.12,
      roughness: 0.2,
      transmission: 0.7,
      ior: 1.3,
      wireframe: false,
    });

    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.08,
    });

    // Head
    const headGeo = new THREE.SphereGeometry(0.38, 24, 24);
    const head = new THREE.Mesh(headGeo, bodyMat);
    head.position.set(0, 1.82, 0);
    head.scale.set(0.9, 1.15, 1.0);
    bodyGroup.add(head);

    // Neck
    const neckGeo = new THREE.CylinderGeometry(0.16, 0.18, 0.22, 16);
    const neck = new THREE.Mesh(neckGeo, bodyMat);
    neck.position.set(0, 1.48, 0);
    bodyGroup.add(neck);

    // Torso / Chest
    const chestGeo = new THREE.CylinderGeometry(0.48, 0.40, 0.85, 24);
    const chest = new THREE.Mesh(chestGeo, bodyMat);
    chest.position.set(0, 1.05, 0);
    chest.scale.set(1.1, 1.0, 0.65);
    bodyGroup.add(chest);

    // Abdomen & Pelvis
    const abdomenGeo = new THREE.CylinderGeometry(0.38, 0.44, 0.75, 24);
    const abdomen = new THREE.Mesh(abdomenGeo, bodyMat);
    abdomen.position.set(0, 0.4, 0);
    abdomen.scale.set(1.05, 1.0, 0.65);
    bodyGroup.add(abdomen);

    // Spine line
    const spineGeo = new THREE.CylinderGeometry(0.03, 0.03, 1.6, 8);
    const spineMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, opacity: 0.3, transparent: true });
    const spine = new THREE.Mesh(spineGeo, spineMat);
    spine.position.set(0, 0.85, -0.15);
    bodyGroup.add(spine);

    // Upper Limbs (Shoulders & Arms)
    const armMat = bodyMat.clone();
    armMat.opacity = 0.08;
    const lArmGeo = new THREE.CylinderGeometry(0.1, 0.08, 1.1, 12);
    const lArm = new THREE.Mesh(lArmGeo, armMat);
    lArm.position.set(-0.62, 0.85, 0);
    lArm.rotation.z = 0.15;
    bodyGroup.add(lArm);

    const rArm = new THREE.Mesh(lArmGeo, armMat);
    rArm.position.set(0.62, 0.85, 0);
    rArm.rotation.z = -0.15;
    bodyGroup.add(rArm);

    // Lower Limbs (Legs)
    const legGeo = new THREE.CylinderGeometry(0.14, 0.1, 1.4, 16);
    const lLeg = new THREE.Mesh(legGeo, armMat);
    lLeg.position.set(-0.24, -0.65, 0);
    bodyGroup.add(lLeg);

    const rLeg = new THREE.Mesh(legGeo, armMat);
    rLeg.position.set(0.24, -0.65, 0);
    rLeg.add(new THREE.Mesh(legGeo, wireMat));
    bodyGroup.add(rLeg);

    this.scene.add(bodyGroup);
  }

  buildAnatomicalOrgans() {
    const createOrganMaterial = (defaultColor = 0x10b981) => {
      return new THREE.MeshStandardMaterial({
        color: defaultColor,
        emissive: defaultColor,
        emissiveIntensity: 0.35,
        roughness: 0.3,
        metalness: 0.1,
        transparent: true,
        opacity: 0.92,
      });
    };

    // 1. BRAIN
    const brainGroup = new THREE.Group();
    const hemisphereGeo = new THREE.SphereGeometry(0.25, 20, 20);
    const lHem = new THREE.Mesh(hemisphereGeo, createOrganMaterial(0x10b981));
    lHem.position.set(-0.08, 0, 0);
    lHem.scale.set(0.7, 0.9, 1.1);

    const rHem = new THREE.Mesh(hemisphereGeo, createOrganMaterial(0x10b981));
    rHem.position.set(0.08, 0, 0);
    rHem.scale.set(0.7, 0.9, 1.1);

    brainGroup.add(lHem, rHem);
    brainGroup.position.set(0, 1.82, 0);
    brainGroup.userData = { organId: 'brain', name: 'Brain', system: 'Central Nervous System' };
    this.scene.add(brainGroup);
    this.organMeshes['brain'] = brainGroup;

    // 2. HEART
    const heartGroup = new THREE.Group();
    const heartGeo = new THREE.SphereGeometry(0.14, 20, 20);
    const heartMesh = new THREE.Mesh(heartGeo, createOrganMaterial(0x10b981));
    heartMesh.scale.set(0.9, 1.25, 0.85);
    heartMesh.rotation.z = -0.25;
    heartMesh.rotation.y = 0.2;

    // Aorta arch
    const aortaGeo = new THREE.TorusGeometry(0.07, 0.025, 12, 20, Math.PI);
    const aortaMesh = new THREE.Mesh(aortaGeo, createOrganMaterial(0x10b981));
    aortaMesh.position.set(0, 0.12, 0);
    aortaMesh.rotation.z = Math.PI / 2;

    heartGroup.add(heartMesh, aortaMesh);
    heartGroup.position.set(-0.08, 1.15, 0.12);
    heartGroup.userData = { organId: 'heart', name: 'Heart', system: 'Cardiovascular System' };
    this.scene.add(heartGroup);
    this.organMeshes['heart'] = heartGroup;

    // 3. LUNGS
    const lungsGroup = new THREE.Group();
    const lungGeo = new THREE.ConeGeometry(0.18, 0.46, 16);

    const lLung = new THREE.Mesh(lungGeo, createOrganMaterial(0x10b981));
    lLung.position.set(-0.24, 0, 0.05);
    lLung.rotation.z = -0.15;
    lLung.rotation.x = 0.1;
    lLung.scale.set(0.85, 1.0, 0.7);

    const rLung = new THREE.Mesh(lungGeo, createOrganMaterial(0x10b981));
    rLung.position.set(0.24, 0, 0.05);
    rLung.rotation.z = 0.15;
    rLung.rotation.x = 0.1;
    rLung.scale.set(0.95, 1.0, 0.75);

    lungsGroup.add(lLung, rLung);
    lungsGroup.position.set(0, 1.14, 0);
    lungsGroup.userData = { organId: 'lung', name: 'Lung', system: 'Respiratory System' };
    this.scene.add(lungsGroup);
    this.organMeshes['lung'] = lungsGroup;

    // 4. LIVER
    const liverGroup = new THREE.Group();
    const liverGeo = new THREE.BoxGeometry(0.34, 0.22, 0.24);
    const liverMesh = new THREE.Mesh(liverGeo, createOrganMaterial(0x10b981));
    liverMesh.rotation.z = -0.2;
    liverMesh.rotation.y = 0.15;
    liverMesh.scale.set(1.0, 0.9, 0.8);

    liverGroup.add(liverMesh);
    liverGroup.position.set(0.16, 0.68, 0.1);
    liverGroup.userData = { organId: 'liver', name: 'Liver', system: 'Hepatic System' };
    this.scene.add(liverGroup);
    this.organMeshes['liver'] = liverGroup;

    // 5. KIDNEYS
    const kidneysGroup = new THREE.Group();
    const kidneyGeo = new THREE.SphereGeometry(0.09, 16, 16);

    const lKidney = new THREE.Mesh(kidneyGeo, createOrganMaterial(0x10b981));
    lKidney.position.set(-0.22, 0, -0.06);
    lKidney.scale.set(0.65, 1.15, 0.8);
    lKidney.rotation.z = 0.15;

    const rKidney = new THREE.Mesh(kidneyGeo, createOrganMaterial(0x10b981));
    rKidney.position.set(0.22, -0.04, -0.06);
    rKidney.scale.set(0.65, 1.15, 0.8);
    rKidney.rotation.z = -0.15;

    kidneysGroup.add(lKidney, rKidney);
    kidneysGroup.position.set(0, 0.45, 0);
    kidneysGroup.userData = { organId: 'kidney', name: 'Kidney', system: 'Renal System' };
    this.scene.add(kidneysGroup);
    this.organMeshes['kidney'] = kidneysGroup;

    // 6. GASTROINTESTINAL TRACT (Stomach & Intestines)
    const giGroup = new THREE.Group();
    const stomachGeo = new THREE.TorusGeometry(0.12, 0.06, 12, 20, Math.PI * 1.2);
    const stomachMesh = new THREE.Mesh(stomachGeo, createOrganMaterial(0x10b981));
    stomachMesh.position.set(-0.06, 0.14, 0.08);
    stomachMesh.rotation.z = 0.5;

    const intestineGeo = new THREE.CylinderGeometry(0.16, 0.2, 0.28, 16);
    const intestineMesh = new THREE.Mesh(intestineGeo, createOrganMaterial(0x10b981));
    intestineMesh.position.set(0, -0.08, 0.08);
    intestineMesh.scale.set(1.1, 0.8, 0.7);

    giGroup.add(stomachMesh, intestineMesh);
    giGroup.position.set(0, 0.32, 0);
    giGroup.userData = { organId: 'gastrointestinal', name: 'Gastrointestinal Tract', system: 'Digestive System' };
    this.scene.add(giGroup);
    this.organMeshes['gastrointestinal'] = giGroup;
  }

  updateOrganRisks(organsData) {
    if (!organsData) return;
    this.organData = organsData;

    const colorMap = {
      Low: { color: 0x10b981, emissive: 0x047857, intensity: 0.35 },
      Moderate: { color: 0xf59e0b, emissive: 0xb45309, intensity: 0.55 },
      High: { color: 0xef4444, emissive: 0xb91c1c, intensity: 0.85 },
    };

    for (const [organId, detail] of Object.entries(organsData)) {
      const group = this.organMeshes[organId];
      if (!group) continue;

      const category = detail.category || 'Low';
      const config = colorMap[category] || colorMap['Low'];

      group.traverse((child) => {
        if (child.isMesh && child.material) {
          child.material.color.setHex(config.color);
          child.material.emissive.setHex(config.emissive);
          child.material.emissiveIntensity = config.intensity;
          child.userData.riskCategory = category;
        }
      });
    }
  }

  bindEvents() {
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    this.container.addEventListener('mousedown', (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    this.container.addEventListener('mousemove', (e) => {
      const rect = this.container.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (isDragging) {
        const deltaX = e.clientX - previousMousePosition.x;
        const deltaY = e.clientY - previousMousePosition.y;

        this.scene.rotation.y += deltaX * 0.008;
        this.camera.position.y -= deltaY * 0.005;
        this.camera.position.y = Math.max(-0.5, Math.min(2.5, this.camera.position.y));

        previousMousePosition = { x: e.clientX, y: e.clientY };
      } else {
        this.checkHover(e);
      }
    });

    this.container.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.camera.position.z += e.deltaY * 0.003;
      this.camera.position.z = Math.max(1.5, Math.min(6.5, this.camera.position.z));
    }, { passive: false });

    this.container.addEventListener('click', (e) => {
      this.handleClick(e);
    });

    window.addEventListener('resize', () => this.onWindowResize());
  }

  checkHover(e) {
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = this.getAllSelectableMeshes();
    const intersects = this.raycaster.intersectObjects(meshes, false);

    const tooltip = document.getElementById('twin-hud-tooltip');

    if (intersects.length > 0) {
      const topMesh = intersects[0].object;
      const organId = topMesh.parent.userData.organId;

      if (this.hoveredOrgan !== organId) {
        this.hoveredOrgan = organId;
        this.container.style.cursor = 'pointer';

        if (tooltip && this.organData[organId]) {
          const detail = this.organData[organId];
          tooltip.style.display = 'block';
          tooltip.innerHTML = `
            <div style="font-weight:700;font-size:0.9rem;margin-bottom:2px;">${detail.name}</div>
            <div style="font-size:0.75rem;color:#94a3b8;">${detail.system}</div>
            <div style="margin-top:4px;display:flex;align-items:center;gap:6px;">
              <span class="badge-risk ${detail.category.toLowerCase()}">${detail.category}</span>
              <span style="font-family:monospace;font-size:0.8rem;">${(detail.risk * 100).toFixed(1)}%</span>
            </div>
          `;
        }
      }

      if (tooltip) {
        const rect = this.container.getBoundingClientRect();
        tooltip.style.left = `${e.clientX - rect.left}px`;
        tooltip.style.top = `${e.clientY - rect.top}px`;
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
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = this.getAllSelectableMeshes();
    const intersects = this.raycaster.intersectObjects(meshes, false);

    if (intersects.length > 0) {
      const topMesh = intersects[0].object;
      const organId = topMesh.parent.userData.organId;
      this.selectedOrgan = organId;
      this.focusCameraOnOrgan(organId);
      this.options.onOrganClick(organId);
    }
  }

  focusCameraOnOrgan(organId) {
    const targets = {
      brain: { y: 1.82, z: 2.2 },
      heart: { y: 1.15, z: 2.2 },
      lung: { y: 1.14, z: 2.4 },
      liver: { y: 0.68, z: 2.2 },
      kidney: { y: 0.45, z: 2.2 },
      gastrointestinal: { y: 0.35, z: 2.2 },
      default: { y: 1.0, z: 4.5 },
    };

    const target = targets[organId] || targets.default;
    this.animateCameraTo(target.y, target.z);
  }

  animateCameraTo(targetY, targetZ) {
    const startY = this.camera.position.y;
    const startZ = this.camera.position.z;
    let t = 0;

    const step = () => {
      t += 0.05;
      this.camera.position.y = THREE.MathUtils.lerp(startY, targetY, t);
      this.camera.position.z = THREE.MathUtils.lerp(startZ, targetZ, t);
      if (t < 1.0) {
        requestAnimationFrame(step);
      }
    };
    step();
  }

  getAllSelectableMeshes() {
    const list = [];
    for (const group of Object.values(this.organMeshes)) {
      group.traverse((child) => {
        if (child.isMesh) list.push(child);
      });
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
        this.animateCameraTo(1.0, 4.5);
        this.scene.rotation.y = 0;
        break;
    }
  }

  toggleAutoRotate() {
    this.isAutoRotate = !this.isAutoRotate;
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

    const delta = this.clock.getDelta();
    const time = this.clock.getElapsedTime();

    if (this.isAutoRotate) {
      this.scene.rotation.y += delta * 0.35;
    }

    // High risk pulsing glow
    for (const group of Object.values(this.organMeshes)) {
      group.traverse((child) => {
        if (child.isMesh && child.userData.riskCategory === 'High') {
          const pulse = 0.6 + 0.35 * Math.sin(time * 4.0);
          child.material.emissiveIntensity = pulse;
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
