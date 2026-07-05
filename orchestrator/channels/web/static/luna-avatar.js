// LUNA-Hologramm -- 2D-LIVING-PORTRAIT: nutzt DAS Kunstbild direkt (kein 3D, kein WebGL, kein Three.js).
// Das Bild liegt als Ebene, darueber ein Canvas fuer holografischen Glow, Scanline-Sweep, pulsende Augen-Glints
// und einen Mund-Bloom, der live auf die Stimme ("Lola") reagiert. Screen-Blend macht dunkle Bildteile
// transparent -> Hologramm-Look auf dunklem Grund. Geteiltes ES-Modul fuer V1 + V2.
//
// API (unveraendert):  const av = createAvatar(container, { reducedMotion });   // gibt immer ein Objekt (ok:true)
//       av.setState("idle"|"listening"|"thinking"|"speaking"|"error");  av.setEnergy(0..1);  av.dispose();
//
// Bild ablegen unter EINEM dieser Pfade (PNG mit transparentem/dunklem Hintergrund ist ideal):
//   orchestrator/channels/web/static/luna-portrait.png  (bevorzugt) | .webp | .jpg

const PORTRAIT_SRCS = ["/static/luna-portrait.png", "/static/luna-portrait.webp", "/static/luna-portrait.jpg"];
// Ungefaehre Gesichtspunkte im Bild (0..1). Nach dem echten Bild leicht nachjustierbar.
const EYE_L = [0.40, 0.42], EYE_R = [0.60, 0.42], MOUTH = [0.50, 0.66];
const COL = { main: [90, 165, 255], bright: [200, 230, 255], warn: [255, 96, 120] };

function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }

export function createAvatar(container, opts = {}) {
  const reduced = !!opts.reducedMotion;

  // -- Ebenen: Bild (screen-blend) + Canvas-Overlay (additive Effekte) --
  const stage = document.createElement("div");
  stage.style.cssText = "position:absolute;inset:0;overflow:hidden;";
  const img = document.createElement("img");
  img.alt = "LUNA";
  img.style.cssText =
    "position:absolute;inset:0;width:100%;height:100%;object-fit:contain;object-position:center 42%;" +
    "mix-blend-mode:screen;filter:saturate(1.12) brightness(1.05) drop-shadow(0 0 14px rgba(90,160,255,.5));" +
    "will-change:transform,opacity;transition:opacity .4s ease;opacity:0;";
  const fx = document.createElement("canvas");
  fx.style.cssText = "position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none;";
  stage.appendChild(img); stage.appendChild(fx); container.appendChild(stage);

  let hasImg = false;
  img.addEventListener("load", () => { hasImg = true; img.style.opacity = "1"; });
  (function tryLoad(i) {
    if (i >= PORTRAIT_SRCS.length) { console.warn("[luna] kein Portrait-Bild gefunden -> Hologramm-Rahmen ohne Gesicht. Lege luna-portrait.png in static/ ab."); return; }
    img.onerror = () => tryLoad(i + 1);
    img.src = PORTRAIT_SRCS[i];
  })(0);

  const ctx = fx.getContext("2d");
  let W = 0, H = 0, DPR = Math.min(window.devicePixelRatio || 1, 2);
  function resize() {
    const w = Math.max(80, container.clientWidth || 190), h = Math.max(80, container.clientHeight || 210);
    W = w; H = h; fx.width = Math.round(w * DPR); fx.height = Math.round(h * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  resize();

  function bloom(x, y, r, col, a) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(col, a)); g.addColorStop(0.5, rgba(col, a * 0.4)); g.addColorStop(1, rgba(col, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  }

  // -- Zustand / Animation --
  let state = "idle", energy = 0, raf = 0, running = true, t0 = performance.now();
  let nextBlink = 1400 + Math.random() * 2600, blink = 0, blinkT = -1;

  function tick() {
    if (!running) return; raf = requestAnimationFrame(tick);
    const now = performance.now(), t = (now - t0) / 1000;
    const tint = state === "error" ? COL.warn : (state === "listening" ? COL.bright : COL.main);
    const speaking = state === "speaking";
    const glow = state === "listening" ? 1.35 : speaking ? (1 + energy * 0.9) : state === "thinking" ? 1.15 : 1;

    // Bild: sanftes Schweben + Hologramm-Flackern
    if (!reduced && hasImg) {
      const floatY = Math.sin(t * 1.1) * 2.2;
      const flick = 1 - (Math.random() < 0.06 ? Math.random() * 0.12 : 0);   // gelegentliches Flackern
      img.style.transform = "translateY(" + floatY.toFixed(2) + "px)";
      img.style.opacity = (0.94 * flick).toFixed(3);
    } else if (hasImg) { img.style.opacity = "1"; }

    // Blinzeln (kurzes Abdunkeln der Augen-Glints)
    if (blinkT < 0 && now - t0 > nextBlink) { blinkT = now; nextBlink = now - t0 + 2400 + Math.random() * 4200; }
    if (blinkT > 0) { const p = (now - blinkT) / 150; if (p >= 1) { blinkT = -1; blink = 0; } else blink = Math.sin(Math.min(1, p) * Math.PI); }

    ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = "lighter";

    // Weicher Grund-Halo hinter dem Kopf
    bloom(W * 0.5, H * 0.40, Math.min(W, H) * 0.62, tint, 0.10 * glow);

    // Leuchtende Augen (Referenz: leuchtende Augen) -- pulsieren, blinzeln
    if (!reduced || speaking || state === "listening") {
      const pulse = 0.55 + Math.sin(t * 3.4) * 0.18 + (state === "listening" ? 0.2 : 0);
      const eyeA = Math.max(0, (0.5 + pulse * 0.5) * (1 - blink)) * (state === "error" ? 0.5 : 1);
      const er = Math.max(6, Math.min(W, H) * 0.06);
      bloom(W * EYE_L[0], H * EYE_L[1], er, tint, 0.5 * eyeA);
      bloom(W * EYE_R[0], H * EYE_R[1], er, tint, 0.5 * eyeA);
    }

    // Mund-Bloom -- reagiert live auf die Stimme
    if (speaking && energy > 0.02) {
      const mr = Math.max(8, Math.min(W, H) * (0.05 + energy * 0.12));
      bloom(W * MOUTH[0], H * MOUTH[1], mr, tint, Math.min(0.85, 0.25 + energy * 0.7));
    }

    // (Scanline-Sweep entfernt -- erzeugte einen sichtbaren horizontalen Streifen ueber dem Bild.
    //  Die feine statische Scanline-Textur kommt weiterhin dezent aus CSS `.luna-holo::after`.)

    // Basis-Ring (Projektions-Sockel unten)
    ctx.globalCompositeOperation = "lighter";
    for (let i = 0; i < 3; i++) {
      const rr = (0.16 + i * 0.14) * W * (0.5 + (Math.sin(t * 1.4 - i * 0.6) * 0.5 + 0.5) * 0.06);
      ctx.strokeStyle = rgba(tint, (0.22 - i * 0.06) * glow); ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.ellipse(W * 0.5, H * 0.93, rr, rr * 0.22, 0, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
  }
  raf = requestAnimationFrame(tick);

  const ro = new ResizeObserver(resize);
  try { ro.observe(container); } catch { }
  const onVis = () => {
    if (!document.hidden && !running) { running = true; t0 = performance.now(); raf = requestAnimationFrame(tick); }
    else if (document.hidden) { running = false; cancelAnimationFrame(raf); }
  };
  document.addEventListener("visibilitychange", onVis);

  return {
    ok: true,
    setState(s) { state = s || "idle"; },
    setEnergy(e) { energy = Math.max(0, Math.min(1, e || 0)); },
    dispose() {
      running = false; cancelAnimationFrame(raf);
      try { ro.disconnect(); } catch { }
      document.removeEventListener("visibilitychange", onVis);
      if (stage.parentNode) stage.parentNode.removeChild(stage);
    },
  };
}
