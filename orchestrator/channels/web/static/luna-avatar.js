// LUNA 3D-Hologramm/Avatar -- prozedurale, holografische Bueste (Three.js, lokal vendored, kein CDN).
// Geteiltes ES-Modul fuer V1 + V2. Look nach CEO-Referenzbild: elektrisch-blaue Frauen-Bueste als
// Punkt-/Konstellations-Netz, leuchtendes Haar, helle Augen, Stirn-Gem, Sichelmond, Orbit-Ringe,
// Ripple-Sockel, Sterne. Lip-Sync ueber setEnergy(0..1). States idle/listening/thinking/speaking/error.
//
// API:  const av = createAvatar(container, { reducedMotion });  -> null wenn kein WebGL
//       av.setState("idle"|"listening"|"thinking"|"speaking"|"error");  av.setEnergy(0..1);  av.dispose();
import * as THREE from "./vendor/three/three.module.min.js";

const COL = { main: 0x3f8cff, bright: 0xcfe6ff, deep: 0x1e56c8, eye: 0xd6ecff, warn: 0xff5c7a };

// Runde, weiche Glut-Textur (fuer Points/Sprites) -- einmalig erzeugt.
function glowTexture() {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"); const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, "rgba(255,255,255,1)"); grd.addColorStop(0.35, "rgba(180,215,255,0.85)");
  grd.addColorStop(1, "rgba(120,170,255,0)");
  g.fillStyle = grd; g.beginPath(); g.arc(32, 32, 32, 0, Math.PI * 2); g.fill();
  const t = new THREE.CanvasTexture(c); return t;
}

export function createAvatar(container, opts = {}) {
  const reduced = !!opts.reducedMotion;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    if (!renderer.getContext()) throw new Error("no gl");
  } catch (e) { return null; }   // kein WebGL -> Caller behaelt Orb

  const size = () => ({ w: Math.max(80, container.clientWidth || 180), h: Math.max(80, container.clientHeight || 180) });
  let { w, h } = size();
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h, false);
  renderer.setClearColor(0x000000, 0);
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 100);
  camera.position.set(0, 0.05, 4.15);

  const tex = glowTexture();
  const disposables = [tex];
  const track = (o) => { disposables.push(o); return o; };
  const addMat = (m) => track(m);
  const root = new THREE.Group(); scene.add(root);          // fuer Schweben/Atmen
  const head = new THREE.Group(); root.add(head);

  // -- Kopf-Volumen: Punktwolke auf einem Ellipsoid (holografische "Haut") --
  function ellipsoidPoints(n, rx, ry, rz, cy) {
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, s = Math.sqrt(1 - u * u);
      pos[i * 3] = s * Math.cos(th) * rx; pos[i * 3 + 1] = u * ry + cy; pos[i * 3 + 2] = s * Math.sin(th) * rz;
    }
    const g = track(new THREE.BufferGeometry()); g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    return g;
  }
  const headMat = addMat(new THREE.PointsMaterial({ color: COL.bright, size: 0.05, map: tex, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
  head.add(new THREE.Points(ellipsoidPoints(760, 0.62, 0.8, 0.55, 0.15), headMat));
  // Dichteres Front-Cluster (Gesichtsflaeche) -> Kopf wird zum hellen Hero.
  function facePoints(n) {
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { const a = Math.random() * Math.PI * 2, rr = Math.pow(Math.random(), 0.6) * 0.5; pos[i * 3] = Math.cos(a) * rr * 0.62; pos[i * 3 + 1] = 0.15 + Math.sin(a) * rr * 0.82; pos[i * 3 + 2] = 0.42 + Math.random() * 0.1; }
    const g = track(new THREE.BufferGeometry()); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); return g;
  }
  head.add(new THREE.Points(facePoints(280), headMat));
  // Weicher Halo hinter dem Kopf -> Gesicht leuchtet als Hero.
  const headGlow = new THREE.Sprite(addMat(new THREE.SpriteMaterial({ color: COL.main, map: tex, transparent: true, opacity: 0.5, depthWrite: false, blending: THREE.AdditiveBlending })));
  headGlow.scale.set(2.6, 2.9, 1); headGlow.position.set(0, 0.15, -0.3); head.add(headGlow);
  const headWire = new THREE.Mesh(track(new THREE.IcosahedronGeometry(0.78, 2)),
    addMat(new THREE.MeshBasicMaterial({ color: COL.deep, wireframe: true, transparent: true, opacity: 0.10 })));
  headWire.scale.set(0.82, 1.03, 0.72); headWire.position.y = 0.15; head.add(headWire);

  // -- Augen (helle Glut) + Blinzeln --
  const eyeMat = addMat(new THREE.SpriteMaterial({ color: COL.eye, map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  const eyes = [-0.19, 0.19].map(x => { const s = new THREE.Sprite(eyeMat); s.scale.set(0.24, 0.15, 1); s.position.set(x, 0.2, 0.56); head.add(s); return s; });

  // -- Stirn-Gem (Diamant) --
  const gem = new THREE.Mesh(track(new THREE.OctahedronGeometry(0.07)),
    addMat(new THREE.MeshBasicMaterial({ color: COL.bright, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false })));
  gem.position.set(0, 0.5, 0.5); gem.scale.set(1, 1.5, 1); head.add(gem);

  // -- Mund (waechst mit Energie) --
  const mouth = new THREE.Sprite(addMat(new THREE.SpriteMaterial({ color: COL.bright, map: tex, transparent: true, opacity: 0.85, depthWrite: false, blending: THREE.AdditiveBlending })));
  mouth.position.set(0, -0.16, 0.5); mouth.scale.set(0.22, 0.03, 1); head.add(mouth);

  // -- Haar: leuchtende Straehnen (Roehren entlang Kurven) --
  const hairMat = addMat(new THREE.MeshBasicMaterial({ color: COL.main, transparent: true, opacity: 0.62, blending: THREE.AdditiveBlending, depthWrite: false }));
  for (let i = 0; i < 9; i++) {
    const side = i < 4 ? -1 : 1, k = (i % 4) / 3;
    const x0 = side * (0.1 + k * 0.15);
    const pts = [new THREE.Vector3(x0, 0.9, 0.1), new THREE.Vector3(side * (0.55 + k * 0.25), 0.5, -0.05 + k * 0.1),
      new THREE.Vector3(side * (0.6 + k * 0.2), 0.0, -0.1), new THREE.Vector3(side * (0.45 + k * 0.15), -0.4 - k * 0.2, -0.05)];
    const curve = new THREE.CatmullRomCurve3(pts);
    const tube = new THREE.Mesh(track(new THREE.TubeGeometry(curve, 24, 0.012 + 0.006 * (1 - k), 6, false)), hairMat);
    head.add(tube);
  }

  // -- Bueste/Schultern: Konstellations-Netz (Punkte + naechste-Nachbar-Linien) --
  const bustGroup = new THREE.Group(); root.add(bustGroup);
  const bp = [], BN = 70;
  for (let i = 0; i < BN; i++) {
    const y = -0.7 - Math.random() * 0.9, spread = 0.5 + (-0.7 - y) * 0.9;
    bp.push(new THREE.Vector3((Math.random() * 2 - 1) * spread, y, (Math.random() * 2 - 1) * 0.35 + 0.1));
  }
  const bpos = new Float32Array(BN * 3); bp.forEach((p, i) => { bpos[i * 3] = p.x; bpos[i * 3 + 1] = p.y; bpos[i * 3 + 2] = p.z; });
  const bGeo = track(new THREE.BufferGeometry()); bGeo.setAttribute("position", new THREE.BufferAttribute(bpos, 3));
  bustGroup.add(new THREE.Points(bGeo, addMat(new THREE.PointsMaterial({ color: COL.bright, size: 0.05, map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }))));
  const seg = [];
  for (let i = 0; i < BN; i++) for (let j = i + 1; j < BN; j++) if (bp[i].distanceTo(bp[j]) < 0.34) { seg.push(bp[i], bp[j]); }
  const lGeo = track(new THREE.BufferGeometry()).setFromPoints(seg);
  bustGroup.add(new THREE.LineSegments(lGeo, addMat(new THREE.LineBasicMaterial({ color: COL.main, transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending }))));

  // -- Sichelmond hinter dem Kopf (Luna-Motiv) --
  const cs = new THREE.Shape(); cs.absarc(0, 0, 1.34, 0, Math.PI * 2, false);
  const hole = new THREE.Path(); hole.absarc(0.28, 0.06, 1.2, 0, Math.PI * 2, true); cs.holes.push(hole);
  const crescent = new THREE.Mesh(track(new THREE.ShapeGeometry(cs, 96)),
    addMat(new THREE.MeshBasicMaterial({ color: COL.main, transparent: true, opacity: 0.42, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })));
  crescent.position.set(-0.05, 0.32, -0.9); root.add(crescent);

  // -- Orbit-Ringe (HUD) mit Node-Punkten --
  const rings = new THREE.Group(); root.add(rings);
  [[1.9, 0.02], [2.4, 0.05], [1.55, -0.04]].forEach(([r, tilt], i) => {
    const ring = new THREE.Mesh(track(new THREE.TorusGeometry(r, 0.006, 6, 120)),
      addMat(new THREE.MeshBasicMaterial({ color: COL.main, transparent: true, opacity: 0.28, blending: THREE.AdditiveBlending, depthWrite: false })));
    ring.rotation.x = Math.PI / 2 + tilt; ring.rotation.z = i * 0.4; rings.add(ring);
    const nn = 5, np = new Float32Array(nn * 3);
    for (let k = 0; k < nn; k++) { const a = Math.random() * Math.PI * 2; np[k * 3] = Math.cos(a) * r; np[k * 3 + 1] = 0; np[k * 3 + 2] = Math.sin(a) * r; }
    const ng = track(new THREE.BufferGeometry()); ng.setAttribute("position", new THREE.BufferAttribute(np, 3));
    const nodes = new THREE.Points(ng, addMat(new THREE.PointsMaterial({ color: COL.bright, size: 0.06, map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
    nodes.rotation.copy(ring.rotation); rings.add(nodes);
  });

  // -- Ripple-Sockel unten + Zentrumspunkt --
  const base = new THREE.Group(); base.position.y = -1.55; root.add(base);
  for (let i = 0; i < 4; i++) {
    const rr = 0.4 + i * 0.4;
    const ring = new THREE.Mesh(track(new THREE.RingGeometry(rr, rr + 0.02, 64)),
      addMat(new THREE.MeshBasicMaterial({ color: COL.main, transparent: true, opacity: 0.3 - i * 0.06, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })));
    ring.rotation.x = -Math.PI / 2; base.add(ring);
  }
  const centerPt = new THREE.Sprite(addMat(new THREE.SpriteMaterial({ color: COL.bright, map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
  centerPt.scale.set(0.5, 0.5, 1); centerPt.position.y = 0.02; base.add(centerPt);

  // -- Sterne/Partikel --
  const SN = reduced ? 90 : 260, sp = new Float32Array(SN * 3);
  for (let i = 0; i < SN; i++) { sp[i * 3] = (Math.random() * 2 - 1) * 3.2; sp[i * 3 + 1] = (Math.random() * 2 - 1) * 3; sp[i * 3 + 2] = (Math.random() * 2 - 1) * 2 - 0.5; }
  const sGeo = track(new THREE.BufferGeometry()); sGeo.setAttribute("position", new THREE.BufferAttribute(sp, 3));
  const stars = new THREE.Points(sGeo, addMat(new THREE.PointsMaterial({ color: COL.main, size: 0.028, map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
  root.add(stars);

  // -- Zustand + Animation --
  let state = "idle", energy = 0, raf = 0, running = true, t0 = performance.now();
  let nextBlink = 1400 + Math.random() * 3000, blinkT = -1;
  const allMats = disposables.filter(o => o.isMaterial);
  const baseOpacity = new Map(allMats.map(m => [m, m.opacity != null ? m.opacity : 1]));

  function tick() {
    if (!running) return;
    raf = requestAnimationFrame(tick);
    const now = performance.now(), t = (now - t0) / 1000;
    const spd = state === "thinking" ? 2.4 : state === "listening" ? 1.5 : 1;
    const glow = state === "listening" ? 1.25 : state === "speaking" ? (1 + energy * 0.9) : 1;

    if (!reduced) {
      root.position.y = Math.sin(t * 1.1) * 0.045;
      root.rotation.y = Math.sin(t * 0.35) * 0.06;
      head.scale.setScalar(1 + Math.sin(t * 1.6) * 0.012);           // Atmen
      rings.rotation.y += 0.0032 * spd; rings.rotation.z = Math.sin(t * 0.2) * 0.05;
      stars.rotation.y += 0.0006; stars.rotation.x = Math.sin(t * 0.1) * 0.03;
      gem.rotation.y += 0.02 * spd; gem.rotation.x += 0.01;
      base.children.forEach((r, i) => { if (r.isMesh) r.scale.setScalar(1 + Math.sin(t * 1.4 - i * 0.6) * 0.06); });
    }
    // Blinzeln
    if (blinkT < 0 && now - t0 > nextBlink) { blinkT = now; nextBlink = now - t0 + 2200 + Math.random() * 4000; }
    let eyeS = 1; if (blinkT > 0) { const bp2 = (now - blinkT) / 140; if (bp2 >= 1) blinkT = -1; else eyeS = Math.abs(Math.cos(bp2 * Math.PI)); }
    eyes.forEach(e => e.scale.y = 0.15 * Math.max(0.06, eyeS));

    // Lip-Sync / Glow
    const mo = state === "speaking" ? 0.03 + energy * 0.42 : 0.03;
    mouth.scale.y += (mo - mouth.scale.y) * 0.4;
    mouth.scale.x = 0.22 - (mouth.scale.y - 0.03) * 0.18;
    const tint = state === "error" ? COL.warn : (state === "listening" ? COL.bright : COL.main);
    for (const m of allMats) { if (m.opacity != null && m !== eyeMat) m.opacity = baseOpacity.get(m) * (state === "error" ? 1 : glow); }
    eyeMat.color.setHex(state === "error" ? COL.warn : COL.eye);
    crescent.material.color.setHex(tint);

    renderer.render(scene, camera);
  }
  raf = requestAnimationFrame(tick);

  // Resize
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
      for (const o of disposables) { try { o.dispose && o.dispose(); } catch { } }
      try { renderer.dispose(); } catch { }
      if (renderer.domElement && renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
    },
  };
}
