// LUNA 3D-Hologramm/Avatar -- ECHTES 3D-Modell (Ready-Player-Me-GLB, lokal vendored) holografisch blau geshadet,
// gerahmt von Sichelmond + Orbit-Ringen (LUNA-Identitaet). Geteiltes ES-Modul fuer V1 + V2.
// Lip-Sync ueber Morph-Targets (jawOpen/Visemes) aus setEnergy(0..1); Blinzeln ueber eyeBlink*. Three.js vendored.
//
// API:  const av = createAvatar(container, { reducedMotion });  -> null wenn kein WebGL
//       av.setState("idle"|"listening"|"thinking"|"speaking"|"error");  av.setEnergy(0..1);  av.dispose();
import * as THREE from "three";
import { GLTFLoader } from "./vendor/three/loaders/GLTFLoader.js";

const MODEL_URL = "/static/vendor/models/luna-avatar.glb";
const COL = { main: 0x4f97ff, bright: 0xdfefff, deep: 0x1e56c8, warn: 0xff5c7a };

function glowTexture() {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"); const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, "rgba(255,255,255,1)"); grd.addColorStop(0.35, "rgba(180,215,255,0.85)"); grd.addColorStop(1, "rgba(120,170,255,0)");
  g.fillStyle = grd; g.beginPath(); g.arc(32, 32, 32, 0, Math.PI * 2); g.fill();
  return new THREE.CanvasTexture(c);
}

export function createAvatar(container, opts = {}) {
  const reduced = !!opts.reducedMotion;
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" }); if (!renderer.getContext()) throw 0; }
  catch (e) { return null; }
  const size = () => ({ w: Math.max(80, container.clientWidth || 190), h: Math.max(80, container.clientHeight || 200) });
  let { w, h } = size();
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h, false); renderer.setClearColor(0x000000, 0);
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(0x2a4a80, 0.7));   // schwaches Grundlicht -> Emissive/Fresnel tragen den Look
  const camera = new THREE.PerspectiveCamera(30, w / h, 0.01, 100);
  camera.position.set(0, 0.0, 0.74);
  const tex = glowTexture();
  const disposables = [tex];
  const track = (o) => { disposables.push(o); return o; };
  const addMat = (m) => track(m);
  const root = new THREE.Group(); scene.add(root);   // Schweben/Atmen
  const framing = new THREE.Group(); root.add(framing);

  // -- Holografische Rahmung (Sichelmond, Ringe, Glow, Partikel, Ripple) um den Kopf --
  const csS = new THREE.Shape(); csS.absarc(0, 0, 0.6, 0, Math.PI * 2, false);
  const hole = new THREE.Path(); hole.absarc(0.13, 0.02, 0.53, 0, Math.PI * 2, true); csS.holes.push(hole);
  const crescent = new THREE.Mesh(track(new THREE.ShapeGeometry(csS, 96)),
    addMat(new THREE.MeshBasicMaterial({ color: COL.bright, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })));
  crescent.position.set(-0.02, 0.06, -0.45); framing.add(crescent);
  const headGlow = new THREE.Sprite(addMat(new THREE.SpriteMaterial({ color: COL.main, map: tex, transparent: true, opacity: 0.6, depthWrite: false, blending: THREE.AdditiveBlending })));
  headGlow.scale.set(1.15, 1.25, 1); headGlow.position.set(0, 0.03, -0.2); framing.add(headGlow);
  const rings = new THREE.Group(); framing.add(rings);
  [[0.66, 0.02], [0.84, 0.05], [0.52, -0.03]].forEach(([r, tilt], i) => {
    const ring = new THREE.Mesh(track(new THREE.TorusGeometry(r, 0.004, 6, 140)),
      addMat(new THREE.MeshBasicMaterial({ color: COL.main, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false })));
    ring.rotation.x = Math.PI / 2 + tilt; ring.rotation.z = i * 0.5; rings.add(ring);
  });
  const SN = reduced ? 60 : 160, sp = new Float32Array(SN * 3);
  for (let i = 0; i < SN; i++) { sp[i * 3] = (Math.random() * 2 - 1) * 1.1; sp[i * 3 + 1] = (Math.random() * 2 - 1) * 1.0; sp[i * 3 + 2] = (Math.random() * 2 - 1) * 0.7 - 0.2; }
  const sGeo = track(new THREE.BufferGeometry()); sGeo.setAttribute("position", new THREE.BufferAttribute(sp, 3));
  const stars = new THREE.Points(sGeo, addMat(new THREE.PointsMaterial({ color: COL.main, size: 0.012, map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
  framing.add(stars);
  const base = new THREE.Group(); base.position.y = -0.42; framing.add(base);
  for (let i = 0; i < 3; i++) { const rr = 0.12 + i * 0.13;
    const rg = new THREE.Mesh(track(new THREE.RingGeometry(rr, rr + 0.006, 64)), addMat(new THREE.MeshBasicMaterial({ color: COL.main, transparent: true, opacity: 0.28 - i * 0.07, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }))); rg.rotation.x = -Math.PI / 2; base.add(rg); }

  // -- Holografisches Material: dunkler Koerper, blau EMISSIV (Gesichtsdetails aus der Textur leuchten),
  //    + FRESNEL-Rand-Gluehen (leuchtende Kanten) + Transluzenz -> echter Hologramm-Look. --
  function holoMat(orig) {
    const map = orig && orig.map ? orig.map : null;
    const m = new THREE.MeshStandardMaterial({
      color: 0x08142c, emissive: new THREE.Color(0x2f6bff), emissiveMap: map, emissiveIntensity: 1.35,
      metalness: 0, roughness: 1, transparent: true, opacity: 0.58, depthWrite: false, blending: THREE.NormalBlending,
    });
    m.onBeforeCompile = (sh) => {
      sh.fragmentShader = sh.fragmentShader.replace("#include <emissivemap_fragment>",
        "#include <emissivemap_fragment>\n float _fres = pow(1.0 - abs(dot(normalize(vNormal), normalize(vViewPosition))), 2.2);\n totalEmissiveRadiance += _fres * vec3(0.45,0.72,1.0) * 1.9;");
    };
    return addMat(m);
  }

  // -- GLB laden --
  const avatarGroup = new THREE.Group(); root.add(avatarGroup);
  const morphMeshes = []; let MOUTH = null, ready = false;
  const loader = new GLTFLoader();
  loader.load(MODEL_URL, (gltf) => {
    const m = gltf.scene;
    m.traverse((o) => {
      if (o.isMesh || o.isSkinnedMesh) {
        o.frustumCulled = false;
        o.material = holoMat(o.material);
        if (o.morphTargetDictionary) morphMeshes.push(o);
      }
    });
    // Kopf zentrieren + Kamera darauf ausrichten (Kopf-und-Schultern).
    const box = new THREE.Box3().setFromObject(m); const headY = box.max.y - 0.12;
    m.position.y = -headY; avatarGroup.add(m);
    // Lip-Sync-Morph waehlen (jawOpen bevorzugt, sonst Vokal-Visem).
    const has = (n) => morphMeshes.some(mm => mm.morphTargetDictionary && n in mm.morphTargetDictionary);
    MOUTH = ["jawOpen", "mouthOpen", "viseme_aa", "viseme_O"].find(has) || null;
    ready = true;
  }, undefined, (err) => { console.warn("[luna] GLB-Ladefehler", err); });

  function setMorph(name, v) { for (const mm of morphMeshes) { const d = mm.morphTargetDictionary; if (!d || !mm.morphTargetInfluences) continue; const i = d[name]; if (i !== undefined) mm.morphTargetInfluences[i] = v; } }

  // -- Animation / Zustand --
  let state = "idle", energy = 0, raf = 0, running = true, t0 = performance.now();
  let nextBlink = 1200 + Math.random() * 2600, blinkT = -1;
  const framingMats = disposables.filter(o => o.isMaterial);
  const baseOp = new Map(framingMats.map(mm => [mm, mm.opacity != null ? mm.opacity : 1]));

  function tick() {
    if (!running) return; raf = requestAnimationFrame(tick);
    const now = performance.now(), t = (now - t0) / 1000;
    const spd = state === "thinking" ? 2.4 : state === "listening" ? 1.5 : 1;
    const glow = state === "listening" ? 1.3 : state === "speaking" ? (1 + energy * 0.8) : 1;
    if (!reduced) {
      root.position.y = Math.sin(t * 1.1) * 0.012;
      avatarGroup.rotation.y = Math.sin(t * 0.4) * 0.08;
      rings.rotation.y += 0.004 * spd; stars.rotation.y += 0.0008;
      base.children.forEach((r, i) => { r.scale.setScalar(1 + Math.sin(t * 1.4 - i * 0.6) * 0.08); });
    }
    if (ready) {
      // Blinzeln
      if (blinkT < 0 && now - t0 > nextBlink) { blinkT = now; nextBlink = now - t0 + 2000 + Math.random() * 4000; }
      let b = 0; if (blinkT > 0) { const p = (now - blinkT) / 130; if (p >= 1) blinkT = -1; else b = Math.sin(Math.min(1, p) * Math.PI); }
      setMorph("eyeBlinkLeft", b); setMorph("eyeBlinkRight", b);
      // Lip-Sync
      if (MOUTH) setMorph(MOUTH, state === "speaking" ? Math.min(1, energy * 1.3) : 0);
    }
    const tint = state === "error" ? COL.warn : (state === "listening" ? COL.bright : COL.main);
    for (const mm of framingMats) if (mm.opacity != null) mm.opacity = baseOp.get(mm) * glow;
    crescent.material.color.setHex(tint);
    renderer.render(scene, camera);
  }
  raf = requestAnimationFrame(tick);

  const ro = new ResizeObserver(() => { const s = size(); w = s.w; h = s.h; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); });
  try { ro.observe(container); } catch { }
  const onVis = () => { const vis = !document.hidden; if (vis && !running) { running = true; t0 = performance.now(); raf = requestAnimationFrame(tick); } else if (!vis) { running = false; cancelAnimationFrame(raf); } };
  document.addEventListener("visibilitychange", onVis);

  return {
    ok: true,
    setState(s) { state = s || "idle"; },
    setEnergy(e) { energy = Math.max(0, Math.min(1, e || 0)); },
    dispose() {
      running = false; cancelAnimationFrame(raf);
      try { ro.disconnect(); } catch { }
      document.removeEventListener("visibilitychange", onVis);
      avatarGroup.traverse((o) => { if (o.geometry) { try { o.geometry.dispose(); } catch { } } if (o.material) { const ms = Array.isArray(o.material) ? o.material : [o.material]; ms.forEach(mm => { try { mm.dispose(); } catch { } }); } });
      for (const o of disposables) { try { o.dispose && o.dispose(); } catch { } }
      try { renderer.dispose(); } catch { }
      if (renderer.domElement && renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
    },
  };
}
