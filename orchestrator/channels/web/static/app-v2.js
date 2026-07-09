// LUNA-OS UI-V2 -- helles, dashboard-/sektionsbasiertes UI (opt-in, siehe UI.md Abschnitt 11).
// Nutzt DIESELBEN /api/*-Endpunkte wie V1, aber ohne Fenster (WinBox). Deutsch mit echten Umlauten.
// Ziel: VOLLE Paritaet zu V1 -- alle Bereiche, Felder und Aktionen sind auch hier erreichbar.
"use strict";

/* =========================== Helfer =========================== */
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const jget = async (u) => { try { const r = await fetch(u); return r.ok ? await r.json() : null; } catch { return null; } };
const jpost = async (u, body) => { try { const r = await fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }); return r.ok ? await r.json() : null; } catch { return null; } };
const num = (v, d = 1) => { const n = Number(v); return isFinite(n) ? n.toFixed(d) : "–"; };
const pct = (v) => isFinite(Number(v)) ? Math.round(Number(v) * 100) + " %" : "–";
const geld = (v, cur = "USD") => { const n = Number(v); if (!isFinite(n)) return "–"; try { return n.toLocaleString("de-DE", { style: "currency", currency: (cur || "USD").toUpperCase(), maximumFractionDigits: 2 }); } catch { return num(n, 2) + " " + (cur || "USD").toUpperCase(); } };
const firstOf = (o, keys, dflt = "") => { for (const k of keys) if (o && o[k] != null && o[k] !== "") return o[k]; return dflt; };
const zeit = (ts) => { try { return new Date(ts).toLocaleString("de-DE", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }); } catch { return ""; } };
function zeitKurz(t) {
  if (!t) return ""; const d = new Date(t); if (isNaN(d)) return String(t).slice(0, 16).replace("T", " ");
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "gerade eben"; if (s < 3600) return Math.floor(s / 60) + " Min";
  if (s < 86400) return Math.floor(s / 3600) + " Std"; return Math.floor(s / 86400) + " T";
}

/* Status-/Label-Karten (1:1 aus V1 uebernommen -> gleiche Begriffe) */
const trendLbl = { new: "Neu", reviewing: "In Prüfung", draft_created: "Entwurf erstellt", approved: "Freigegeben", published: "Veröffentlicht", ignored: "Ignoriert" };
const ideaLbl = { inbox: "Eingang", sorted: "Einsortiert", planned: "Geplant", in_progress: "In Arbeit", done: "Erledigt", archived: "Archiviert" };
const draftLbl = { idea: "Idee", in_progress: "In Arbeit", review: "Review", approved: "Freigegeben", scheduled: "Geplant", published: "Veröffentlicht", archived: "Archiviert" };
const recLbl = { use: "Nutzen", investigate: "Prüfen", later: "Später", ignore: "Ignorieren" };
const rolleLbl = { owner: "Owner (Voll)", admin: "Admin (Voll)", team: "Team (Content+CRM)", content: "Content", viewer: "Viewer" };
const cutLbl = { done: "Fertig", running: "Läuft", queued: "In Warteschlange", failed: "Fehler" };
const cutBadge = { done: "ok", running: "wartet", queued: "wartet", failed: "err" };
const evLbl = { eingereicht: "eingereicht", freigegeben: "freigegeben", abgelehnt: "abgelehnt", in_umsetzung: "in Umsetzung", erledigt: "erledigt", fehlgeschlagen: "fehlgeschlagen", geloescht: "gelöscht" };
const kanal = { instagram: "📸 Instagram", mail: "✉️ Mail", telegram: "💬 Telegram", manuell: "✎ Manuell" };
const badgeCls = (st) => ({ eingereicht: "wartet", freigegeben: "ok", abgelehnt: "err", in_umsetzung: "wartet", erledigt: "ok", aktiv: "aktiv", inaktiv: "neutral" }[st] || "neutral");

/* =========================== Zustand =========================== */
let ME = { apps: null, role: "owner", display_name: "CEO", username: "" };
let PREFS = {};
let STATE = {}, OVERVIEW = {}, LOOP = {}, INVEST = {};
let AKTIV = "dash", SUBTAB = {};

/* Dashboard-Bearbeiten (wie V1): Widget-Reihenfolge + ausgeblendete, pro Nutzer in PREFS.v2_dashboard. */
const DASH2_DEFAULT = ["freigaben", "loop", "budget", "trefferquote", "provider", "compliance", "live", "schritte", "meldungen", "research"];
const DASH2_TITEL = { budget: "Monatsbudget", trefferquote: "Prognose-Trefferquote", freigaben: "Offene Freigaben", provider: "Provider verbunden", loop: "Investment · Lern-Loop", compliance: "Compliance-Puls", live: "Live-Aktivität", schritte: "Erste Schritte", meldungen: "Meldungen", research: "Research-Tickets" };
let DASH2 = { order: [...DASH2_DEFAULT], hidden: [] };
let EDIT2 = false, DRAG2 = null;
let _VERLAUF = [], _trendRO = null;

function normDash2(l) {
  l = l || {}; const hidden = (Array.isArray(l.hidden) ? l.hidden : []).filter(id => DASH2_DEFAULT.includes(id));
  const order = (Array.isArray(l.order) ? l.order : []).filter(id => DASH2_DEFAULT.includes(id));
  DASH2_DEFAULT.forEach(id => { if (!order.includes(id)) order.push(id); });
  return { order, hidden };
}
function saveDash2() {
  PREFS = { ...PREFS, v2_dashboard: DASH2 };
  try { localStorage.setItem("luna-v2-dash", JSON.stringify(DASH2)); } catch { }
  jpost("/api/prefs", { prefs: PREFS });
}
function hideW2(id) { if (!DASH2.hidden.includes(id)) DASH2.hidden.push(id); saveDash2(); renderDash(); }
function showW2(id) { DASH2.hidden = DASH2.hidden.filter(x => x !== id); saveDash2(); renderDash(); }
function reorder2(from, to) { const o = DASH2.order.filter(x => x !== from); o.splice(Math.max(0, o.indexOf(to)), 0, from); DASH2.order = o; saveDash2(); renderDash(); }

/* Sektionen (Icon-Nav). app = Gate ueber /api/me.apps (null = immer sichtbar). Deckt ALLE V1-Bereiche ab. */
const SECTIONS = [
  { id: "dash", icon: "▦", label: "Dashboard", app: "home" },
  { id: "freigaben", icon: "✔", label: "Freigaben", app: "auftraege" },
  { id: "devroadmap", icon: "🗺", label: "Roadmap", app: null },
  { id: "investment", icon: "📈", label: "Investment", app: "investment" },
  { id: "crm", icon: "🤝", label: "CRM", app: "crm" },
  { id: "radar", icon: "🎯", label: "Radar", app: "crm" },
  { id: "content", icon: "✎", label: "Content", app: "trends" },
  { id: "cutter", icon: "🎬", label: "Cutter", app: "cutter" },
  { id: "reel", icon: "📤", label: "Reels", app: "cutter" },
  { id: "wissen", icon: "🧠", label: "Wissen", app: "wissen" },
  { id: "agenten", icon: "🛰", label: "Agenten", app: "home" },
  { id: "system", icon: "📡", label: "System", app: null },
  { id: "team", icon: "👥", label: "Team", app: "team" },
  { id: "einstellungen", icon: "⚙", label: "Einstellungen", app: null },
];
const darf = (app) => app == null || app === "home" || !ME.apps || ME.apps.includes(app);

/* =========================== Theme / Shell =========================== */
function applyTheme() {
  const m = localStorage.getItem("luna-v2-theme") || "light";
  const dark = m === "dark" || (m === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("v2-dark", dark);
  document.documentElement.classList.toggle("v2-light", !dark);
}
function toggleTheme() { const m = localStorage.getItem("luna-v2-theme") || "light"; localStorage.setItem("luna-v2-theme", m === "dark" ? "light" : "dark"); applyTheme(); }
async function setUiMode(mode) {
  if (mode !== "v2") mode = "v1";
  try { localStorage.setItem("luna-ui-mode", mode); } catch { }
  PREFS = { ...PREFS, ui_version: mode }; await jpost("/api/prefs", { prefs: PREFS });
  location.href = "/?ui=" + mode;
}
function buildShell() {
  $("#v2-nav").innerHTML = SECTIONS.filter(s => darf(s.app)).map(s =>
    `<button data-go="${s.id}" class="${s.id === "dash" ? "home " : ""}${s.id === AKTIV ? "active" : ""}" title="${esc(s.label)}">${s.icon}</button>`).join("");
  $("#v2-pills").innerHTML = [
    darf("auftraege") ? `<button class="v2-pill" data-go="freigaben">✔ Freigabe prüfen</button>` : "",
    darf("investment") ? `<button class="v2-pill" data-act="inv-screen">🔍 Screen starten</button>` : "",
    `<button class="v2-pill" data-toggle-chat>💬 LUNA fragen</button>`,
    `<button class="v2-pill cta" data-ui-mode="v1">↩ Zurück zu UI V1</button>`,
  ].filter(Boolean).join("");
  const nm = (ME.display_name || ME.username || "L").trim();
  $("#v2-avatar").textContent = nm.slice(0, 1).toUpperCase(); $("#v2-avatar").title = nm + (ME.role === "owner" ? " · Voll-Zugriff" : " · " + (ME.role || ""));
}

/* =========================== Router =========================== */
const RENDER = {};
function go(id, sub) {
  if (!SECTIONS.find(s => s.id === id)) id = "dash";
  AKTIV = id; if (sub) SUBTAB[id] = sub;
  document.querySelectorAll("#v2-nav button").forEach(b => b.classList.toggle("active", b.dataset.go === id));
  $("#v2-app").innerHTML = `<div class="v2-empty">Lade …</div>`;
  (RENDER[id] || renderDash)();
}

/* =========================== Bausteine =========================== */
function secHead(title, actions = "") { return `<div class="v2-sec-head"><h1>${esc(title)}</h1><div class="actions">${actions}</div></div>`; }
// Info-Symbol mit Mouseover-Erklaerung (erscheint neben den drei Punkten an jedem erklaerten Container).
function infoTip(text) { return `<span class="v2-info" tabindex="0">i<span class="v2-info-pop">${esc(text)}</span></span>`; }
// Titel -> Klartext-Erklaerung: welcher Container ist das und was passiert da? (laienverstaendlich)
const TILE_INFO = {
  "Modus": `In welchem Modus LUNA arbeitet: advisory = nur Vorschläge, paper = Übungshandel mit Spielgeld, live = echtes Geld (ist aus).`,
  "Track-Record": `Die Erfolgsbilanz: wie gut LUNAs bisherige Prognosen im Schnitt lagen.`,
  "Richtungsquote": `Wie oft LUNA die Richtung (rauf oder runter) richtig vorhergesagt hat. 50 % = Zufall, höher ist besser.`,
  "Watchlist": `Anzahl der Werte, die LUNA für dich beobachtet (nur ansehen, nicht kaufen).`,
  "💼 Paper-Depot (Alpaca-Sim)": `Übungsdepot mit Spielgeld und echten Kursen. Hier kannst du gefahrlos Kaufen/Verkaufen testen — kein echtes Geld im Spiel.`,
  "🏦 Echtes Depot (manuell)": `Deine echten Bestände, die du selbst einträgst. LUNA bewertet sie live und berät dich — kauft aber nie selbst.`,
  "Watchlist verwalten": `Werte zum Beobachten hinzufügen oder entfernen. Beobachten heißt nur ansehen, nicht kaufen.`,
  "Provider": `Die externen Datenquellen, aus denen LUNA Kurse und Infos zieht. Grün = verbunden.`,
  "Lern-Loop · Fehler-Verlauf": `Zwei FEHLER-Kurven (keine echten Kurse!). „Modell" = LUNAs Vorhersagen. „Baseline" = ein Dummy, der stur sagt „der Kurs bleibt gleich" — die Messlatte. Gezeigt wird, wie weit beide im Schnitt danebenlagen: je tiefer, desto besser. LUNA ist nur dann wirklich gut, wenn die Modell-Linie UNTER der Baseline liegt.`,
  "Je Anlageklasse": `Wie treffsicher LUNAs Prognosen je Anlage-Art sind (Aktie/ETF/Krypto). „Treffer" = Richtung stimmte.`,
  "Signal-Attribution": `Welche Signale (z. B. Momentum, Trend) wie oft richtig lagen — zeigt, worauf LUNAs Ideen beruhen.`,
  "Je Modell-Version": `Vergleich von LUNAs verschiedenen Prognose-Modellen: welche Version besser abschneidet.`,
  "Marktdrift-Kontrolle (Insider vs. Markt)": `Prüft, ob Aktienkäufe von Firmen-Insidern (z. B. Vorständen) tatsächlich besser laufen als der Gesamtmarkt.`,
  "Offene Prognosen": `Vorhersagen, deren Ergebnis noch aussteht — sie werden später automatisch überprüft.`,
  "Abweichungs-Register": `Ehrlicher Rückblick: LUNAs Prognose gegen das, was wirklich passierte. Macht Fehler transparent.`,
  "Shortlist (letzter Screen)": `Werte, die LUNAs letzter Marktdurchlauf („Screen") als interessant markiert hat.`,
  "Vorschläge (Risk-geprüft)": `Konkrete Kauf- oder Beobachten-Ideen, die zusätzlich einen Risiko-Check durchlaufen haben. Kein Gewinnversprechen.`,
  "Insider-Signale (SEC Form 4)": `Wenn Firmen-Chefs eigene Aktien kaufen (offizielle US-Meldung „Form 4") — oft ein Vertrauenssignal.`,
  "Autonomie-Leitplanken": `Die Sicherheits-Grenzen, in denen LUNA (nur im Paper-Modus) selbst handeln dürfte: max. Einsatz, Stop-Loss usw.`,
};
function tile(title, inner, cls = "", extraHead = "") {
  const info = TILE_INFO[title] ? infoTip(TILE_INFO[title]) : "";
  const tools = extraHead || `<span class="dots">···</span>`;
  return `<div class="v2-tile ${cls}"><div class="v2-tile-h"><span class="t">${esc(title)}</span><span class="v2-tile-tools">${info}${tools}</span></div>${inner}</div>`;
}
function kpiTile(title, big, delta, sub, spark) {
  const d = delta ? `<span class="delta ${delta.up ? "up" : "down"}">${delta.up ? "↗" : "↘"} ${esc(delta.text)}</span>` : "";
  return tile(title, `<div class="v2-kpi">${esc(big)} ${d}</div>${sub ? `<div class="v2-sub">${esc(sub)}</div>` : ""}${spark || ""}`);
}
const emptyRow = (t) => `<div class="v2-empty">${esc(t)}</div>`;

/* Antrags-Beschreibung sauber strukturieren: Sektionen (IDEE (..)/MACHBARKEIT (CTO)/KOSTEN (CFO)/QUELLEN,
   getrennt durch Leerzeilen) mit Label-Kopf + Absatz rendern, statt allem als Textwust. */
function fmtBeschreibung(text) {
  const t = String(text == null ? "" : text).trim();
  if (!t) return "<i>keine Beschreibung</i>";
  const H = 'style="font-weight:700;font-size:.72rem;letter-spacing:.05em;text-transform:uppercase;opacity:.55;margin-top:.75rem"';
  const B = 'style="white-space:pre-wrap;margin-top:.15rem;line-height:1.5"';
  return t.split(/\n\s*\n/).map(b => b.trim()).filter(Boolean).map(b => {
    const i = b.indexOf("\n");
    const head = (i === -1 ? b : b.slice(0, i)).trim();
    const body = (i === -1 ? "" : b.slice(i + 1)).trim();
    if (/^(IDEE|MACHBARKEIT|KOSTEN|QUELLEN|BEFUND)\b/i.test(head) && body)
      return `<div ${H}>${esc(head)}</div><div ${B}>${esc(body)}</div>`;
    return `<div style="white-space:pre-wrap;margin-top:.6rem;font-weight:600">${esc(b)}</div>`;  // Einzeiler (💶/↻)
  }).join("");
}
/* Kurzer, sauberer Karten-Teaser: die IDEE-Kernaussage (fallback: ganzer Text). */
function antragPreview(text) {
  const t = String(text == null ? "" : text);
  const m = t.match(/^IDEE\b[^\n]*\n([\s\S]*?)(?:\n\s*\n|$)/mi);
  return esc((m ? m[1] : t).trim()) || "<i>keine Beschreibung</i>";
}
function tabs(sec, list) {
  const cur = SUBTAB[sec] || list[0][0];
  return `<div class="v2-tabs">${list.map(([id, lbl]) => `<button class="${id === cur ? "active" : ""}" data-tab="${sec}:${id}">${esc(lbl)}</button>`).join("")}</div>`;
}
/* Detail-Overlay (ersetzt WinBox-Fenster) */
function openModal(title, html) {
  let m = $("#v2-modal"); if (!m) { m = document.createElement("div"); m.id = "v2-modal"; document.body.appendChild(m); }
  m.innerHTML = `<div class="v2-modal-back" data-modal-close></div><div class="v2-modal-card"><header><b>${esc(title)}</b><button class="v2-icon" data-modal-close>✕</button></header><div class="v2-modal-body">${html}</div></div>`;
  m.hidden = false;
}
function closeModal() { const m = $("#v2-modal"); if (m) m.hidden = true; }

/* Fehler-Verlauf-Chart (Modell vs. Baseline): breiten-bewusst gerendert -> KEINE Streckung.
   viewBox-Breite = Container-Pixelbreite -> 1:1-Abbildung (Achsen/Text unverzerrt). ResizeObserver wie V1. */
function chartMount() {
  return `<div class="v2-trend"></div><div class="v2-legend"><span><i style="background:var(--v2-accent)"></i>Modell</span><span><i style="background:var(--v2-faint)"></i>Baseline</span></div>`;
}
function mountTrends() {
  const els = document.querySelectorAll(".v2-trend"); if (!els.length) return;
  els.forEach(drawTrend);
  if (!_trendRO) _trendRO = new ResizeObserver(es => es.forEach(e => drawTrend(e.target)));
  try { _trendRO.disconnect(); els.forEach(el => _trendRO.observe(el)); } catch { }
}
function drawTrend(el) {
  const v = _VERLAUF || [];
  if (!v.length) { el.innerHTML = `<div class="v2-sub" style="padding:16px 0">Noch kein Fehler-Verlauf — braucht ausgewertete Prognosen.</div>`; return; }
  const W = Math.max(280, Math.round(el.clientWidth || 600)), H = 168, padL = 34, padR = 12, padT = 12, padB = 24;
  const max = Math.max(1, ...v.flatMap(p => [p.mae_pct || 0, p.baseline_mae_pct || 0])) * 1.1;
  const x = i => padL + (v.length <= 1 ? (W - padL - padR) / 2 : i * (W - padL - padR) / (v.length - 1));
  const y = val => H - padB - ((val || 0) / max) * (H - padT - padB);
  const line = k => v.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p[k]).toFixed(1)}`).join(" ");
  const grid = [0, .5, 1].map(f => { const t = max * f, yy = y(t).toFixed(1); return `<line x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}" class="v2-cgrid"/><text x="${padL - 6}" y="${+yy + 3}" class="v2-cax" text-anchor="end">${t.toFixed(1)}</text>`; }).join("");
  const xi = v.length > 2 ? [0, Math.floor((v.length - 1) / 2), v.length - 1] : v.map((_, i) => i);
  const xl = xi.map(i => `<text x="${x(i).toFixed(1)}" y="${H - 7}" class="v2-cax" text-anchor="middle">${esc((v[i].woche || "").replace("2026-", ""))}</text>`).join("");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" class="v2-chart" role="img">${grid}<path d="${line("baseline_mae_pct")}" class="v2-line base"/><path d="${line("mae_pct")}" class="v2-line strat"/>${xl}</svg><div class="v2-ctip" style="display:none"></div>`;
  const svg = el.querySelector("svg"), tip = el.querySelector(".v2-ctip");
  svg.addEventListener("mousemove", ev => { const r = svg.getBoundingClientRect(); let i = Math.round(((ev.clientX - r.left) / r.width * W - padL) / ((W - padL - padR) / Math.max(1, v.length - 1))); i = Math.max(0, Math.min(v.length - 1, i)); const p = v[i]; tip.innerHTML = `<b>${esc((p.woche || "").replace("2026-", ""))}</b> · Modell ${(p.mae_pct || 0).toFixed(1)}% · Baseline ${(p.baseline_mae_pct || 0).toFixed(1)}%`; tip.style.display = "block"; tip.style.left = Math.max(0, Math.min(r.width - 200, ev.clientX - r.left - 60)) + "px"; });
  svg.addEventListener("mouseleave", () => { tip.style.display = "none"; });
}
function balken(obj, suffix = "Treffer") {
  return Object.entries(obj || {}).map(([k, a]) =>
    `<div class="v2-bar-row"><span class="lbl">${esc(k)}</span><div class="v2-bar"><i style="width:${Math.round((a.richtungsquote || 0) * 100)}%"></i></div>
      <span class="val">${pct(a.richtungsquote)} ${suffix} · n=${a.n}</span></div>`).join("") || emptyRow("–");
}

/* =========================== Dashboard (bearbeitbar) =========================== */
RENDER.dash = renderDash;
function kpiInner(big, delta, sub, spark) {
  const d = delta ? `<span class="delta ${delta.up ? "up" : "down"}">${delta.up ? "↗" : "↘"} ${esc(delta.text)}</span>` : "";
  return `<div class="v2-kpi">${esc(big)} ${d}</div>${sub ? `<div class="v2-sub">${esc(sub)}</div>` : ""}${spark || ""}`;
}
function dashTile(id, w) {
  const clickable = !EDIT2 && w.link;
  const linkAttr = clickable ? (w.link.startsWith("go:") ? `data-go="${w.link.slice(3)}"` : `data-tab="${w.link.slice(4)}"`) : "";
  const a11y = clickable ? `role="button" tabindex="0" aria-label="${esc(w.aria || DASH2_TITEL[id])}"` : `role="region" aria-label="${esc(w.aria || DASH2_TITEL[id])}"`;
  const cls = "v2-tile " + (w.span || "") + (clickable ? " klick" : "") + (EDIT2 ? " editing" : "");
  const rightHead = EDIT2 ? `<button class="v2-wx" data-whide2="${id}" title="Ausblenden" aria-label="Widget ausblenden">✕</button>`
    : (w.link ? `<span class="dots go" aria-hidden="true">›</span>` : `<span class="dots" aria-hidden="true">···</span>`);
  const grip = EDIT2 ? `<span class="v2-grip" title="Ziehen zum Anordnen">⠿</span>` : "";
  return `<div class="${cls}" data-wid="${id}" ${EDIT2 ? 'draggable="true"' : linkAttr + " " + a11y}>
    <div class="v2-tile-h"><span class="t">${grip}${esc(DASH2_TITEL[id])}</span>${rightHead}</div>${w.html}</div>`;
}
function dash2Tray(W) {
  const hid = DASH2.order.filter(id => W[id] && DASH2.hidden.includes(id));
  return `<div class="v2-tray"><b>Ausgeblendet:</b> ${hid.length ? hid.map(id => `<button class="v2-btn" data-wadd2="${id}">＋ ${esc(DASH2_TITEL[id])}</button>`).join("") : `<span class="v2-sub">nichts ausgeblendet</span>`}</div>`;
}
async function renderDash() {
  [STATE, OVERVIEW, LOOP] = await Promise.all([jget("/api/state"), jget("/api/overview"), jget("/api/investment/loop")]);
  STATE = STATE || {}; OVERVIEW = OVERVIEW || {}; LOOP = LOOP || {}; _VERLAUF = LOOP.verlauf || [];
  const g = (LOOP.kennzahlen && LOOP.kennzahlen.gesamt) || {};
  const antraege = STATE.antraege || [], provs = OVERVIEW.providers || [];
  const connected = Number(OVERVIEW.providers_connected) || provs.filter(p => p.konfiguriert || p.connected).length;
  const provFrac = provs.length ? connected / provs.length : 0;
  const budget = OVERVIEW.monatsbudget || firstOf(STATE.finance || {}, ["monatsbudget", "budget"], "–");
  const aktiv = STATE.aktivitaet || [], meld = STATE.meldungen || [], research = STATE.research || [];
  const schritte = [
    { t: "Datenquellen verbunden", done: connected > 0 }, { t: "Investment-Loop aktiv", done: !!(LOOP.panel && LOOP.panel.symbole) },
    { t: "Team eingerichtet", done: (OVERVIEW.counts && OVERVIEW.counts.wissen != null) }, { t: "Budget gesetzt", done: budget && budget !== "–" }];
  const doneN = schritte.filter(s => s.done).length;
  const policy = [{ t: "Datenquellen verbunden", ok: provFrac >= .5 }, { t: "Freigabe-Tore aktiv", ok: true }, { t: "Security-Audit täglich", ok: true }];
  const live = aktiv.slice(0, 8).map(a => `<tr><td><b>${esc(String(firstOf(a, ["akteur", "titel", "name"], "Ereignis")))}</b> ${esc(String(firstOf(a, ["aktion", "text"], "")).slice(0, 70))}</td><td>${esc(zeitKurz(firstOf(a, ["ts", "zeit", "erstellt_am"], "")))}</td><td><span class="v2-badge live">Live</span></td></tr>`).join("") || `<tr><td colspan="3" class="v2-empty">Noch keine Aktivität.</td></tr>`;

  // Freigaben-HERO: Zahl + Top-3 offene Antraege mit Inline-Aktion (Progressive Disclosure statt nur Zaehler).
  const topFreig = antraege.slice(0, 3).map(x => `<div class="v2-list-row">
      <span class="v2-badge ${badgeCls(x.status || "eingereicht")}">${esc(x.status || "eingereicht")}</span>
      <div class="grow"><b>${esc(x.titel || "Antrag")}</b><small>${esc(x.von || "")}${x.kategorie ? " · " + esc(x.kategorie) : ""}</small></div>
      ${(x.status === "eingereicht") ? `<button class="v2-btn ok sm" data-act="antrag-freigeben" data-id="${esc(x.id)}" title="Freigeben">✓</button>` : ""}
      <button class="v2-btn sm" data-act="antrag-detail" data-id="${esc(x.id)}" title="Details">›</button></div>`).join("")
    || `<div class="v2-check done" style="border:none"><span class="mark">✓</span>alles freigegeben — nichts offen</div>`;
  const freigInner = `<div class="v2-kpi">${antraege.length} <span class="delta ${antraege.length ? "down" : "up"}">${antraege.length ? "wartet" : "frei"}</span></div>
    <div class="v2-hero-list">${topFreig}</div>
    ${antraege.length > 3 ? `<button class="v2-linkbtn" data-go="freigaben">Alle ${antraege.length} ansehen ›</button>` : ""}`;
  const miniList = (arr, keys, sub) => arr.slice(0, 2).map(x => `<div class="v2-mini"><b>${esc(String(firstOf(x, keys, "—")).slice(0, 54))}</b>${sub ? `<small>${esc(String(firstOf(x, sub, "")).slice(0, 40))}</small>` : ""}</div>`).join("") || `<div class="v2-sub">nichts offen</div>`;

  const W = {
    freigaben: { span: "w4 tall", link: null, aria: `Offene Freigaben: ${antraege.length}`, html: freigInner },
    loop: { span: "w8 tall", link: "go:investment", aria: `Investment Lern-Loop, Richtungsquote ${g.n ? pct(g.richtungsquote) : "keine Daten"}`, html: `<div class="v2-kpi">${g.n ? pct(g.richtungsquote) : "–"} <span class="delta ${(g.anteil_besser_baseline || 0) >= .5 ? "up" : "down"}">${g.n ? pct(g.anteil_besser_baseline) + " schlägt Baseline" : ""}</span></div><div class="v2-sub">Richtungsquote · MAE ${num(g.mae_pct)} vs Baseline ${num(g.baseline_mae_pct)} · n=${g.n || 0}</div>${chartMount()}` },
    budget: { span: "", link: null, aria: `Monatsbudget ${budget}`, html: kpiInner(String(budget), null, "aus finance/budget.md") },
    trefferquote: { span: "", link: "go:investment", aria: `Prognose-Trefferquote ${g.n ? pct(g.richtungsquote) : "keine Daten"}`, html: kpiInner(g.n ? pct(g.richtungsquote) : "–", g.n ? { up: (g.anteil_besser_baseline || 0) >= .5, text: pct(g.anteil_besser_baseline) + " > Baseline" } : null, g.n ? `n=${g.n} · MAE ${num(g.mae_pct)} vs ${num(g.baseline_mae_pct)}` : "noch keine Auswertung", sparkFromVerlauf(LOOP.verlauf)) },
    provider: { span: "", link: "go:investment", aria: `Provider verbunden ${connected} von ${provs.length}`, html: kpiInner(`${connected}/${provs.length || "–"}`, { up: provFrac >= .5, text: pct(provFrac) }, "externe Datenquellen") },
    compliance: { span: "", link: null, aria: `Compliance-Puls ${pct(provFrac)}`, html: `<div class="v2-gauge">${gaugeSvg(provFrac)}<div class="val">${pct(provFrac)}</div><div class="cap">Anbindungs-Abdeckung</div></div><div class="v2-policy">${policy.map(p => `<div class="row"><span>${esc(p.t)}</span><span class="v2-badge ${p.ok ? "aktiv" : "wartet"}">${p.ok ? "Aktiv" : "Offen"}</span></div>`).join("")}</div>` },
    live: { span: "w12", link: "tab:system:aktivitaet", aria: "Live-Aktivität", html: `<table class="v2-table"><thead><tr><th>Ereignis</th><th>Zeit</th><th>Status</th></tr></thead><tbody>${live}</tbody></table>` },
    schritte: { span: "w4", link: null, aria: `Erste Schritte, ${doneN} von ${schritte.length} erledigt`, html: `<div class="v2-sub">System-Bereitschaft</div><div class="v2-progress"><i style="width:${Math.round(doneN / schritte.length * 100)}%"></i></div>${schritte.map(s => `<div class="v2-check ${s.done ? "done" : ""}"><span class="mark">${s.done ? "✓" : ""}</span>${esc(s.t)}</div>`).join("")}` },
    meldungen: { span: "w4", link: "tab:system:meldungen", aria: `Meldungen: ${meld.length}`, html: `<div class="v2-kpi">${meld.length} <span class="v2-sub" style="font-size:12px">ungelesen</span></div><div class="v2-hero-list">${miniList(meld, ["text"], ["abteilung"])}</div>` },
    research: { span: "w4", link: "tab:system:research", aria: `Research-Tickets: ${research.length}`, html: `<div class="v2-kpi">${research.length} <span class="v2-sub" style="font-size:12px">offen</span></div><div class="v2-hero-list">${miniList(research, ["frage", "titel"], ["abteilung", "status"])}</div>` },
  };
  const order = DASH2.order.filter(id => W[id] && !DASH2.hidden.includes(id));
  const editBtn = `<button class="v2-btn ${EDIT2 ? "pri" : ""}" data-editdash>${EDIT2 ? "✓ Fertig" : "✎ Anpassen"}</button>`;
  $("#v2-app").innerHTML = `
    <div class="v2-welcome"><div class="v2-welcome-row"><div><h1>Willkommen zurück, ${esc(ME.display_name || "CEO")}</h1>
      <p>Dein KI-Kontrollraum — Agenten, Kosten und Compliance im Blick.</p></div>${editBtn}</div></div>
    <div class="v2-grid ${EDIT2 ? "editing" : ""}">${order.map(id => dashTile(id, W[id])).join("")}</div>
    ${EDIT2 ? dash2Tray(W) : ""}`;
  mountTrends();
}
function sparkFromVerlauf(verlauf) {
  const v = (verlauf || []).slice(-28); if (!v.length) return "";
  const mx = Math.max(...v.map(x => Number(x.mae_pct) || 0), 1);
  return `<div class="v2-spark">${v.map(x => { const h = Math.round((Number(x.mae_pct) || 0) / mx * 100); const gut = (Number(x.mae_pct) || 0) <= (Number(x.baseline_mae_pct) || 0); return `<i class="${gut ? "g" : "a"}" style="height:${Math.max(6, h)}%"></i>`; }).join("")}</div>`;
}
function gaugeSvg(frac) {
  const p = Math.max(0, Math.min(1, frac || 0)), ang = Math.PI * (1 - p), r = 62, cx = 80, cy = 78;
  const x = cx + r * Math.cos(ang), y = cy - r * Math.sin(ang), big = p > 0.5 ? 1 : 0;
  return `<svg viewBox="0 0 160 96" width="180" height="108" aria-hidden="true">
    <path d="M18 78 A62 62 0 0 1 142 78" fill="none" stroke="var(--v2-line-soft)" stroke-width="13" stroke-linecap="round"/>
    <path d="M18 78 A62 62 0 ${big} 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="url(#gg)" stroke-width="13" stroke-linecap="round"/>
    <defs><linearGradient id="gg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="var(--v2-orange)"/><stop offset=".6" stop-color="var(--v2-green)"/><stop offset="1" stop-color="var(--v2-blue)"/></linearGradient></defs></svg>`;
}

/* =========================== Freigaben =========================== */
RENDER.freigaben = renderFreigaben;
async function renderFreigaben() {
  STATE = await jget("/api/state") || STATE;
  const a = STATE.antraege || [];
  const cards = a.map(x => {
    const id = x.id, st = x.status || "eingereicht";
    const btns = [
      st === "eingereicht" ? `<button class="v2-btn ok" data-act="antrag-freigeben" data-id="${esc(id)}">✓ Freigeben</button>` : "",
      (st === "eingereicht" || st === "freigegeben") ? `<button class="v2-btn danger" data-act="antrag-ablehnen" data-id="${esc(id)}">✕ Ablehnen</button>` : "",
      (st === "eingereicht" || st === "freigegeben") ? `<button class="v2-btn" data-act="antrag-revidieren" data-id="${esc(id)}">✏️ Revidieren</button>` : "",
      `<button class="v2-btn" data-act="antrag-detail" data-id="${esc(id)}">📄 Details</button>`,
      `<button class="v2-btn" data-act="antrag-mehr" data-id="${esc(id)}">🔍 Mehr Info</button>`,
      `<button class="v2-btn" data-act="antrag-loeschen" data-id="${esc(id)}">🗑 Löschen</button>`,
    ].filter(Boolean).join("");
    return `<div class="v2-card"><div class="v2-card-h"><span class="v2-badge ${badgeCls(st)}">${esc(st)}</span><b>${esc(x.titel)}</b></div>
      <div class="v2-sub">von ${esc(x.von)}${x.kategorie ? " · " + esc(x.kategorie) : ""} · ${esc(id)}</div>
      <div class="v2-desc clamp">${antragPreview(x.beschreibung)}</div><div class="v2-card-actions">${btns}</div></div>`;
  }).join("") || emptyRow("Keine offenen Freigaben — alles erledigt. 🎉");
  const bar = a.length ? `<button class="v2-btn" data-act="antrag-reformat">🔄 Alle neu formatieren</button>` : "";
  $("#v2-app").innerHTML = secHead("Freigaben", bar) + `<div class="v2-cards">${cards}</div>`;
}

/* =========================== Investment (FULL) =========================== */
/* --- Depot-Ansichten: Paper (Alpaca-Sim) + echtes Depot (manuell). Beide read-only. --- */
const KLASSE_LABEL = { aktie: "Aktien", etf: "ETF", krypto: "Krypto" };
function gruppenChips(gruppen, cur) {
  const eintr = Object.entries(gruppen || {});
  if (!eintr.length) return "";
  return `<div class="v2-chips" style="margin:6px 0 10px">` + eintr.map(([k, g]) => {
    const up = (g.gv_abs || 0) >= 0;
    return `<span class="v2-chip"><b>${esc(KLASSE_LABEL[k] || k)}</b> ${geld(g.wert, cur)} <small style="color:${up ? "var(--v2-green)" : "var(--v2-red)"}">${up ? "+" : ""}${geld(g.gv_abs, cur)}</small></span>`;
  }).join("") + `</div>`;
}
function depotTable(positionen, cur, extraCell) {
  const rows = (positionen || []).map(p => {
    const gv = p.gv_abs, col = gv == null ? "var(--v2-muted)" : (gv >= 0 ? "var(--v2-green)" : "var(--v2-red)");
    const perStk = (v) => `<br><small style="color:var(--v2-muted)">à ${geld(v, cur)}</small>`;
    const einstand = geld(p.einstand_wert, cur) + perStk(p.einstand_preis);
    const wert = p.wert == null ? "<i title='Kurs nicht abrufbar'>Kurs fehlt</i>" : geld(p.wert, cur) + (p.kurs ? perStk(p.kurs) : "");
    const gvBetrag = gv == null ? "–" : `${gv >= 0 ? "+" : ""}${geld(gv, cur)}`;
    const gvProzent = gv == null ? "–" : `${p.gv_pct >= 0 ? "+" : ""}${num(p.gv_pct, 1)} %`;
    const x = extraCell ? `<td>${extraCell(p)}</td>` : "";
    return `<tr><td><span class="v2-chip">${esc(KLASSE_LABEL[p.klasse] || p.klasse)}</span></td><td><b>${esc(p.symbol)}</b></td><td>${num(p.stueck, 4)}</td><td>${einstand}</td><td>${wert}</td><td style="color:${col}">${gvBetrag}</td><td style="color:${col}">${gvProzent}</td>${x}</tr>`;
  }).join("") || `<tr><td colspan="${extraCell ? 8 : 7}" class="v2-empty">Keine Positionen.</td></tr>`;
  return `<table class="v2-table"><thead><tr><th>Klasse</th><th>Symbol</th><th>Stück</th><th title="Gesamter Einstandswert (Stück × Ø-Kaufpreis)">Einstand</th><th title="Aktueller Gesamtwert (Stück × aktueller Kurs)">Wert</th><th>G/V</th><th>G/V %</th>${extraCell ? "<th></th>" : ""}</tr></thead><tbody>${rows}</tbody></table>`;
}
function depotPaperTile(pf) {
  if (!pf || !pf.verfuegbar)
    return tile("💼 Paper-Depot (Alpaca-Sim)", emptyRow((pf && pf.grund) || "Paper-Konto nicht verbunden."), "w6");
  const k = pf.konto || {}, cur = k.waehrung || "USD", up = (k.tag_abs || 0) >= 0;
  const head = `<div class="v2-kpi">${geld(k.gesamtwert, cur)} <span class="delta ${up ? "up" : "down"}">${up ? "↗" : "↘"} ${geld(k.tag_abs, cur)} (${num(k.tag_pct, 2)}%)</span></div><div class="v2-sub">Cash ${geld(k.cash, cur)} · Kaufkraft ${geld(k.kaufkraft, cur)} · Positionen ${geld(k.positionswert, cur)}</div>`;
  const order = `<div class="v2-depot-form" style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0">
      <select id="po-side" class="v2-inp"><option value="buy">Kaufen</option><option value="sell">Verkaufen</option></select>
      <select id="po-klasse" class="v2-inp"><option value="aktie">Aktie/ETF</option><option value="krypto">Krypto</option></select>
      <input id="po-sym" class="v2-inp" placeholder="Symbol (AAPL / bitcoin)" style="width:150px">
      <input id="po-qty" class="v2-inp" type="number" step="any" placeholder="Stück" style="width:90px">
      <button class="v2-btn pri" data-act="paper-order">Order (Paper)</button>
    </div>`;
  const sell = (p) => `<button class="v2-btn sm" data-act="paper-sell" data-id="${esc(p.symbol)}" data-asset="${esc(p.klasse)}" data-val="${esc(p.stueck)}">Verkaufen</button>`;
  return tile("💼 Paper-Depot (Alpaca-Sim)", head + order + gruppenChips(pf.gruppen, cur) + depotTable(pf.positionen, cur, sell), "w6");
}
function txListe(tx, cur) {
  if (!tx || !tx.length) return "";
  const rows = tx.map(t => {
    const sell = t.side === "verkauf";
    return `<div class="v2-list-row"><span class="v2-badge ${sell ? "wartet" : "ok"}">${sell ? "Verkauf" : "Kauf"}</span><div class="grow"><b>${esc(t.symbol)}</b> <small>${num(t.stueck, 4)} × ${geld(t.preis, cur)}${t.gebuehr ? " · Geb. " + geld(t.gebuehr, cur) : ""}${t.datum ? " · " + esc(t.datum) : ""}</small></div><button class="chip-x" data-act="depot-storno" data-id="${esc(t.id)}" title="Buchung stornieren">✕</button></div>`;
  }).join("");
  return `<div class="v2-sub" style="margin:12px 0 4px">Buchungen (neueste zuerst)</div>${rows}`;
}
function depotEchtTile(dp) {
  const s = (dp && dp.summe) || {}, cur = s.waehrung || "USD", up = (s.gv_abs || 0) >= 0;
  const rz = s.realisiert || 0;
  const rzHtml = rz ? ` · realisiert <b style="color:${rz >= 0 ? "var(--v2-green)" : "var(--v2-red)"}">${rz >= 0 ? "+" : ""}${geld(rz, cur)}</b>` : "";
  const head = `<div class="v2-kpi">${geld(s.gesamtwert, cur)} <span class="delta ${up ? "up" : "down"}">${up ? "↗" : "↘"} ${geld(s.gv_abs, cur)} (${num(s.gv_pct, 2)}%)</span></div><div class="v2-sub">Einstand ${geld(s.einstand, cur)}${rzHtml}${s.unbewertet ? " · " + s.unbewertet + " ohne Kurs" : ""} · offene G/V (unrealisiert)</div>`;
  const hinweise = (dp && dp.hinweise) || [];
  const hinweiseHtml = hinweise.length ? `<div style="margin:10px 0">${hinweise.map(h => `<div class="v2-list-row"><span class="v2-badge ${h.signal === "stop" ? "wartet" : "ok"}">${h.signal === "stop" ? "🛑 Stop-Loss" : "🎯 Take-Profit"}</span><div class="grow"><small>${esc(h.text)}</small></div></div>`).join("")}<div class="v2-sub" style="margin-top:4px">LUNA berät — Ausführung machst du selbst in deinem Broker.</div></div>` : "";
  const form = `<div class="v2-depot-form" style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0">
      <select id="dep-side" class="v2-inp"><option value="kauf">Kauf</option><option value="verkauf">Verkauf</option></select>
      <select id="dep-klasse" class="v2-inp"><option value="aktie">Aktie</option><option value="etf">ETF</option><option value="krypto">Krypto</option></select>
      <input id="dep-sym" class="v2-inp" placeholder="Symbol (AAPL)" style="width:110px">
      <input id="dep-id" class="v2-inp" placeholder="Kurs-Id (Krypto: bitcoin)" style="width:150px">
      <input id="dep-stueck" class="v2-inp" type="number" step="any" placeholder="Stück" style="width:80px">
      <input id="dep-preis" class="v2-inp" type="number" step="any" placeholder="Preis/Stück" style="width:110px">
      <input id="dep-gebuehr" class="v2-inp" type="number" step="any" placeholder="Gebühr" style="width:80px">
      <button class="v2-btn" data-act="depot-trade">Buchen</button>
    </div>`;
  return tile("🏦 Echtes Depot (manuell)", head + hinweiseHtml + form + depotTable((dp && dp.positionen) || [], cur, null) + txListe(dp && dp.transaktionen, cur), "w6");
}
RENDER.investment = renderInvestment;
async function renderInvestment() {
  let PF = null, DP = null;
  [INVEST, LOOP, PF, DP] = await Promise.all([jget("/api/investment"), jget("/api/investment/loop"), jget("/api/investment/portfolio"), jget("/api/investment/depot")]);
  INVEST = INVEST || {}; LOOP = LOOP || {}; _VERLAUF = LOOP.verlauf || [];
  const i = INVEST, g = (LOOP.kennzahlen && LOOP.kennzahlen.gesamt) || {}, mk = LOOP.insider_kontrolle;
  const sc = i.scorecard || {}, h = i.historie || {}, jt = h.je_tabelle || {};
  const scText = sc.ausgewertet ? `${pct(sc.trefferquote)} (${sc.treffer}/${sc.ausgewertet})` : "noch keine Auswertung";
  const histText = h.eintraege_gesamt ? `${h.eintraege_gesamt} Einträge · ${jt.forecasts || 0} Prognosen · ${jt.actuals || 0} ausgewertet · ${jt.screening || 0} Screens` : "noch leer";
  const prov = (i.provider || []).map(p => `<span class="v2-chip ${p.konfiguriert ? "on" : "off"}">${esc(p.name)}</span>`).join(" ");
  const wl = (i.watchlist || []).map(w => `<span class="v2-chip"><b>${esc(w.symbol)}</b> <small>${esc(w.asset)}</small><button class="chip-x" data-act="inv-remove" data-id="${esc(w.symbol)}" title="Entfernen">✕</button></span>`).join("") || "<i>leer</i>";
  const sl = (i.shortlist || []).map(s => { const c = s.veraenderung_pct, v = (c > 0 ? "+" : "") + (c == null ? "?" : Number(c).toFixed(1)) + "%";
    return `<div class="v2-list-row klick" data-act="inv-detail" data-id="${esc(s.symbol)}" data-asset="${esc(s.asset || "aktie")}"><span style="color:${c >= 0 ? "var(--v2-green)" : "var(--v2-red)"};font-weight:700;width:64px">${v}</span><div class="grow"><b>${esc(s.symbol)}</b> <small>${esc(s.asset)} · ${esc(s.quelle)}</small></div><span>›</span></div>`; }).join("") || emptyRow("Noch kein Screen — klick auf Screen jetzt.");
  const sug = (i.vorschlaege || []).map(s => `<div class="v2-list-row klick" data-act="inv-detail" data-id="${esc(s.symbol)}" data-asset="${/^[a-z]/.test(s.symbol || "") && (s.symbol || "").length > 4 ? "krypto" : "aktie"}">
    <span class="v2-badge ${s.risiko_label === "spekulativ" ? "wartet" : "ok"}">${esc(s.risiko_label || "")}</span>
    <div class="grow"><b>${esc((s.aktion || "").toUpperCase())} ${esc(s.symbol)}</b><small>${esc(s.grund || "")} · Konfidenz ${pct(s.konfidenz)}</small></div><span>›</span></div>`).join("") || emptyRow("Noch keine Vorschläge.");
  const ins = (i.insider || []).map(s => `<div class="v2-list-row"><span class="v2-badge wartet">Insider</span><div class="grow"><b>${esc(s.symbol)}</b> <small>${s.cluster || 1} Insider · ~${s.betrag != null ? esc(s.betrag) : "?"} USD · ${esc(s.rolle || "k.A.")} · Konf. ${pct(s.konfidenz)}${s.datum ? " · " + esc(s.datum) : ""}</small></div>${s.filing_url ? `<a href="${esc(s.filing_url)}" target="_blank" rel="noopener">Form 4 ↗</a>` : ""}</div>`).join("") || emptyRow("Noch keine Insider-Signale — klick auf Insider-Scan.");
  const vers = Object.entries((LOOP.kennzahlen && LOOP.kennzahlen.je_version) || {}).map(([k, a]) =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(k)}</b><small>MAE ${num(a.mae_pct)} vs ${num(a.baseline_mae_pct)} · Richtung ${pct(a.richtungsquote)} · n=${a.n}</small></div><span class="v2-badge ${(a.anteil_besser_baseline || 0) >= .5 ? "ok" : "wartet"}">${pct(a.anteil_besser_baseline)} schlägt Baseline</span></div>`).join("") || emptyRow("Noch keine Versions-Daten.");
  const offen = (LOOP.offene_prognosen || []).slice(0, 12).map(f => { const up = f.richtung === "steigt", dn = f.richtung === "faellt";
    return `<tr><td style="color:${up ? "var(--v2-green)" : dn ? "var(--v2-red)" : "var(--v2-muted)"}">${up ? "▲" : dn ? "▼" : "▬"} ${(f.ziel_return_pct > 0 ? "+" : "") + num(f.ziel_return_pct)}%</td><td><b>${esc(f.symbol)}</b></td><td>${esc(f.asset || "")}</td><td>${pct(f.konfidenz)}</td><td>${esc(f.faellig_am || "")}</td></tr>`; }).join("") || `<tr><td colspan="5" class="v2-empty">Keine offenen Prognosen.</td></tr>`;
  const reg = (LOOP.register || []).slice(0, 10).map(d => `<tr><td style="color:${d.besser_als_baseline ? "var(--v2-green)" : "var(--v2-amber)"}">Δ ${num(d.fehler_abs_pct)}%</td><td><b>${esc(d.symbol)}</b> ${esc(d.asset || "")}</td><td>${num(d.prognose_return_pct)}% → ${num(d.real_return_pct)}%${d.richtungstreffer ? " ✓" : ""}${d.backtest ? " · BT" : ""}</td><td><span class="v2-badge ${d.besser_als_baseline ? "ok" : "wartet"}">${d.besser_als_baseline ? "schlägt Baseline" : "unter Baseline"}</span></td></tr>`).join("") || `<tr><td colspan="4" class="v2-empty">Register noch leer.</td></tr>`;
  const lp = LOOP.leitplanken, lpHtml = lp ? `<div class="v2-lp-status ${lp.autonom_aktiv ? "on" : "off"}"><span class="dot"></span>${lp.autonom_aktiv ? "Autonomes Handeln AKTIV (Modus " + esc(lp.modus) + ")" : "Autonomes Handeln inaktiv — Modus " + esc(lp.modus || "advisory")}</div>${(lp.konfiguration || []).map(c => `<div class="v2-list-row"><div class="grow"><b>${esc(c.label)}</b></div><span>${esc(c.wert)}</span></div>`).join("")}` : emptyRow("–");
  const mkHtml = mk && mk.insider && mk.insider.n ? `
    <div class="v2-list-row"><div class="grow"><b>Insider-Wochen</b><small>n=${mk.insider.n}</small></div><span>Richtung ${pct(mk.insider.richtung_pct)} · schlägt Markt ${pct(mk.insider.schlaegt_markt_pct)} · Ø Alpha ${num(mk.insider.alpha_schnitt_pct)}%</span></div>
    <div class="v2-list-row"><div class="grow"><b>Basisrate (alle Wochen)</b><small>n=${mk.basisrate.n}</small></div><span>Richtung ${pct(mk.basisrate.richtung_pct)} · schlägt Markt ${pct(mk.basisrate.schlaegt_markt_pct)}</span></div>
    <div class="v2-sub">Vorsprung: ${mk.edge_richtung_pp > 0 ? "+" : ""}${mk.edge_richtung_pp} pp Richtung · ${mk.edge_markt_pp > 0 ? "+" : ""}${mk.edge_markt_pp} pp schlägt-Markt</div>` : emptyRow("Noch keine Marktdrift-Kontrolle.");
  const actions = `<button class="v2-btn" data-act="inv-sammeln">📥 Jetzt sammeln</button><button class="v2-btn" data-act="inv-backfill">📚 Historie laden</button><button class="v2-btn" data-act="inv-screen">📡 Screen jetzt</button><button class="v2-btn" data-act="inv-insider">🔍 Insider-Scan</button>`;
  $("#v2-app").innerHTML = secHead("Investment", actions) + `
    <div class="v2-grid">
      ${kpiTile("Modus", esc(i.modus || "–"), null, "Handels-Modus")}
      ${kpiTile("Track-Record", scText.split(" ")[0] || "–", null, scText)}
      ${kpiTile("Richtungsquote", g.n ? pct(g.richtungsquote) : "–", g.n ? { up: (g.anteil_besser_baseline || 0) >= .5, text: pct(g.anteil_besser_baseline) } : null, `n=${g.n || 0} · MAE ${num(g.mae_pct)} vs ${num(g.baseline_mae_pct)}`, sparkFromVerlauf(LOOP.verlauf))}
      ${kpiTile("Watchlist", String((i.watchlist || []).length), null, "beobachtete Werte")}
      ${depotPaperTile(PF)}
      ${depotEchtTile(DP)}
      ${tile("Watchlist verwalten", `<div style="margin-bottom:10px" class="v2-inv-search"><input id="inv-sym" placeholder="Aktie/Krypto suchen & hinzufügen…" autocomplete="off"><div id="inv-suggest" class="v2-suggest"></div></div><div class="v2-chips">${wl}</div>`, "w6")}
      ${tile("Provider", `<div class="v2-chips">${prov || "–"}</div><div class="v2-sub" style="margin-top:10px">Historie: ${esc(histText)}</div>`, "w6")}
      ${tile("Lern-Loop · Fehler-Verlauf", `<div class="v2-sub">${(LOOP.panel || {}).symbole || 0} Werte · ${(LOOP.panel || {}).snapshots || 0} Snapshots · Modell ${esc(LOOP.modell_version || "")}</div>${chartMount()}`, "w8")}
      ${tile("Je Anlageklasse", balken((LOOP.kennzahlen || {}).je_asset), "w4")}
      ${tile("Signal-Attribution", balken((LOOP.kennzahlen || {}).je_signal), "w6")}
      ${tile("Je Modell-Version", vers, "w6")}
      ${tile("Marktdrift-Kontrolle (Insider vs. Markt)", mkHtml, "w12")}
      ${tile("Offene Prognosen", `<table class="v2-table"><thead><tr><th>Ziel</th><th>Symbol</th><th>Klasse</th><th>Konf.</th><th>fällig</th></tr></thead><tbody>${offen}</tbody></table>`, "w6")}
      ${tile("Abweichungs-Register", `<table class="v2-table"><thead><tr><th>Fehler</th><th>Symbol</th><th>Prognose→real</th><th>Bewertung</th></tr></thead><tbody>${reg}</tbody></table>`, "w6")}
      ${tile("Shortlist (letzter Screen)", sl, "w4")}
      ${tile("Vorschläge (Risk-geprüft)", sug, "w4")}
      ${tile("Insider-Signale (SEC Form 4)", ins, "w4")}
      ${tile("Autonomie-Leitplanken", lpHtml, "w12")}
    </div>`;
  const inp = $("#inv-sym"); if (inp) inp.addEventListener("input", () => invSuche(inp.value));
  mountTrends();
}
let _sucheTimer = null;
function invSuche(q) {
  clearTimeout(_sucheTimer); const box = $("#inv-suggest"); if (!box) return; q = (q || "").trim();
  if (q.length < 2) { box.innerHTML = ""; box.classList.remove("open"); return; }
  _sucheTimer = setTimeout(async () => {
    const d = await jget("/api/investment/suche?q=" + encodeURIComponent(q)) || {}; const t = d.treffer || [];
    box.innerHTML = t.length ? t.map(x => `<div data-act="inv-add" data-id="${esc(x.symbol)}" data-asset="${esc(x.asset)}"><b>${esc(x.ticker || x.symbol)}</b> <small>${esc(x.name || "")} · ${esc(x.asset)}</small></div>`).join("") : `<div class="v2-empty">keine Treffer</div>`;
    box.classList.add("open");
  }, 300);
}
async function invDetail(symbol, asset) {
  openModal(symbol, `<div class="v2-empty">Lade Infos zu ${esc(symbol)}…</div>`);
  const d = await jget(`/api/investment/detail?symbol=${encodeURIComponent(symbol)}&asset=${encodeURIComponent(asset || "aktie")}`);
  if (!d) { openModal(symbol, emptyRow("Konnte Infos nicht laden.")); return; }
  const kv = (k, v) => v != null && v !== "" ? `<div class="v2-kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>` : "";
  const kurs = kursChart(d.kurs_historie);
  let body;
  if (asset === "krypto") {
    const i = d.info || {};
    body = i.ok ? `<h3>${esc(i.name)} (${esc(i.symbol)})</h3>${kurs}${kv("Rang", i.rang ? "#" + i.rang : "")}${kv("Preis (EUR)", i.preis_eur)}${kv("Veränderung 24h", (i.veraenderung_pct > 0 ? "+" : "") + num(i.veraenderung_pct, 2) + "%")}${kv("Marktkap. (EUR)", i.marktkap_eur)}${kv("24h-Volumen", i.volumen_eur)}${kv("ATH", i.ath_eur)}${kv("ATL", i.atl_eur)}${i.beschreibung ? `<h3>Über</h3><p>${esc(i.beschreibung)}</p>` : ""}` : emptyRow("Keine Krypto-Infos verfügbar.");
  } else {
    const p = d.profil, q = d.quote, r = d.rsi;
    const news = (d.news || []).map(n => `<div class="v2-list-row"><div class="grow"><b>${esc(n.titel)}</b><small>${esc(n.quelle || "")}</small></div></div>`).join("");
    body = `<h3>${esc((p && p.name) || d.symbol)}</h3>${p ? `<div class="v2-sub">${esc(p.branche || "")}${p.boerse ? " · " + esc(p.boerse) : ""}${p.land ? " · " + esc(p.land) : ""}</div>` : ""}${kurs}
      ${q ? kv("Preis", q.preis) + kv("Veränderung", (q.veraenderung_pct > 0 ? "+" : "") + q.veraenderung_pct + "%") + kv("Tageshoch", q.hoch) + kv("Tagestief", q.tief) : ""}
      ${r ? kv("RSI (14)", r.wert + " · " + r.label) : ""}${p ? kv("Marktkap. (Mio)", p.marktkap_mio) + kv("IPO", p.ipo) : ""}
      ${news ? `<h3>News</h3>${news}` : ""}${(d.hinweise || []).length ? emptyRow(d.hinweise[0]) : ""}`;
  }
  openModal(symbol, body);
}
function kursChart(h) {
  if (!h || h.length < 2) return `<div class="v2-sub">Noch zu wenig Kurs-Historie.</div>`;
  const W = 460, H = 130, pad = 22, closes = h.map(p => p.close), smas = h.map(p => p.sma20).filter(v => v != null);
  const lo = Math.min(...closes, ...(smas.length ? smas : [Infinity])), hi = Math.max(...closes, ...(smas.length ? smas : [-Infinity])), span = (hi - lo) || 1;
  const x = i => pad + (h.length <= 1 ? 0 : i * (W - 2 * pad) / (h.length - 1));
  const y = v => H - pad - ((v - lo) / span) * (H - 2 * pad);
  const path = h.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p.close).toFixed(1)}`).join(" ");
  const smaPts = h.map((p, i) => p.sma20 != null ? `${x(i).toFixed(1)} ${y(p.sma20).toFixed(1)}` : null).filter(Boolean);
  const smaPath = smaPts.length > 1 ? "M" + smaPts.join(" L") : "";
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none" class="v2-chart">${smaPath ? `<path d="${smaPath}" class="v2-line base"/>` : ""}<path d="${path}" class="v2-line strat"/></svg>
    <div class="v2-legend"><span><i style="background:var(--v2-accent)"></i>Kurs ${closes[closes.length - 1]}</span>${smaPts.length ? `<span><i style="background:var(--v2-faint)"></i>SMA-20</span>` : ""}<span class="v2-sub">${esc(h[0].datum)} → ${esc(h[h.length - 1].datum)} · ${h.length} Tage</span></div>`;
}

/* =========================== CRM =========================== */
RENDER.crm = renderCrm;
async function renderCrm() {
  const sub = SUBTAB.crm || "pipeline";
  const [crm, tl] = await Promise.all([jget("/api/crm"), sub === "timeline" ? jget("/api/crm/timeline") : Promise.resolve(null)]);
  const c = crm || {}, u = c.uebersicht || {}, pipe = u.pipeline || {};
  let body;
  if (sub === "timeline") {
    body = tile("Timeline — alle Kanäle", (tl && tl.nachrichten || []).map(m => crmMsg(m, true)).join("") || emptyRow("Noch keine Nachrichten."), "w12");
  } else {
    const pipeHtml = ["neu", "in_gespraech", "angebot", "vereinbart", "abgelehnt"].map(s => `<div class="v2-kv"><span>${esc(s)}</span><b>${pipe[s] || 0}</b></div>`).join("");
    const todos = (c.todos || []).map(t => `<div class="v2-list-row"><span class="v2-badge wartet">To-do</span><div class="grow"><b>${esc(t.firma)}</b><small>${esc(t.vorschlag || "")}${t.begruendung ? " · " + esc(t.begruendung) : ""}</small></div><button class="v2-btn ok" data-act="crm-todo" data-id="${esc(t.id)}">✓ Erledigt</button></div>`).join("") || emptyRow("Keine offenen To-dos.");
    const firmen = (c.firmen || []).map(f => `<div class="v2-list-row klick" data-act="crm-firma" data-id="${esc(f.firma)}"><span class="v2-badge neutral">${esc(f.status)}</span><div class="grow"><b>${esc(f.firma)}</b><small>${esc(f.quelle || "")} · ${f.nachrichten || 0} Nachr.</small></div><span>›</span></div>`).join("") || emptyRow("Noch keine Anfragen — kommt automatisch per Instagram-Webhook.");
    body = `${kpiTile("Firmen gesamt", String(u.firmen_gesamt || 0), null, "im CRM")}${kpiTile("Offene To-dos", String(u.offene_todos || 0), null, "zu erledigen")}
      ${tile("Pipeline", pipeHtml, "w6")}${tile("Offene To-dos", todos, "w6")}${tile("Firmen (nach letztem Kontakt)", firmen, "w12")}`;
  }
  $("#v2-app").innerHTML = secHead("Collab-CRM", `<button class="v2-btn" data-act="crm-sync">🔄 DMs synchronisieren</button>`) + tabs("crm", [["pipeline", "Pipeline & Firmen"], ["timeline", "Timeline"]]) + `<div class="v2-grid">${body}</div>`;
}
function crmMsg(m, mitFirma) {
  return `<div class="v2-list-row"><span title="${esc(m.richtung === "ein" ? "eingehend" : "ausgehend")}">${esc(kanal[m.quelle] || "•").split(" ")[0]}${m.richtung === "ein" ? "⬅︎" : "➡︎"}</span><div class="grow">${mitFirma && m.firma ? `<b>${esc(m.firma)}</b> ` : ""}<b>${esc(m.text)}</b><small>${esc(kanal[m.quelle] || m.quelle || "")}${m.ts ? " · " + esc(m.ts) : ""}</small></div></div>`;
}
async function crmFirma(firma) {
  openModal(firma, `<div class="v2-empty">Lade Verlauf…</div>`);
  const d = await jget("/api/crm/konversation?firma=" + encodeURIComponent(firma));
  openModal(firma, (d && d.nachrichten || []).map(m => crmMsg(m, false)).join("") || emptyRow("Kein Verlauf."));
}

/* =========================== Collab-Radar =========================== */
RENDER.radar = renderCollabRadar;
async function renderCollabRadar() {
  const sub = SUBTAB.radar || "collab";
  const r = await jget("/api/collab-radar" + (sub === "collab" ? "?nur_collab=1" : "")) || {};
  const u = r.uebersicht || {}, ks = r.kontakte || [];
  const wartenBadge = (w) => w === "uns" ? `<span class="v2-badge wartet">Wir am Zug</span>`
    : w === "kontakt" ? `<span class="v2-badge neutral">Warten auf Kontakt</span>` : "";
  const rows = ks.map(k => {
    const todos = (k.offene_todos || []).length;
    const info = k.analysiert ? esc(k.zusammenfassung || k.stand || "—") : "Noch nicht analysiert";
    return `<div class="v2-list-row klick" data-act="radar-kontakt" data-id="${esc(k.contact_id)}">
      <span class="v2-badge ${k.collab ? "ok" : "neutral"}">${k.collab ? "Collab" : "—"}</span>
      <div class="grow"><b>@${esc(k.name)}</b> ${wartenBadge(k.warten_auf)}<small>${info}${todos ? " · " + todos + " To-do" : ""} · ${k.nachrichten || 0} Nachr. (ein ${k.ein}/aus ${k.aus})</small></div><span>›</span></div>`;
  }).join("") || emptyRow(sub === "collab"
    ? "Noch keine Collab-Gespräche erkannt — erst Postfach synchronisieren und analysieren lassen."
    : "Kein Kontakt im Archiv — sag LUNA „synchronisiere das Instagram-Postfach\".");
  const body = `${kpiTile("Collab-Gespräche", String(u.collab || 0), null, "erkannt")}${kpiTile("Wir am Zug", String(u.warten_auf_uns || 0), null, "warten auf uns")}
    ${kpiTile("Offene To-dos", String(u.offene_todos || 0), null, "aus Analysen")}${kpiTile("Unanalysiert", String(u.unanalysiert || 0), null, "Kontakte")}
    ${tile("Kontakte", rows, "w12")}`;
  $("#v2-app").innerHTML = secHead("Collab-Radar") + tabs("radar", [["collab", "Nur Collabs"], ["alle", "Alle Kontakte"]]) + `<div class="v2-grid">${body}</div>`;
}
async function radarKontakt(cid) {
  openModal("Gesprächs-Verlauf", `<div class="v2-empty">Lade Verlauf…</div>`);
  const d = await jget("/api/collab-radar/verlauf?contact_id=" + encodeURIComponent(cid)) || {};
  const rows = (d.nachrichten || []).map(m =>
    `<div class="v2-list-row"><span title="${m.richtung === "ein" ? "eingehend" : "ausgehend"}">${m.richtung === "ein" ? "⬅︎" : "➡︎"}</span><div class="grow"><b>${esc(m.text || "")}</b><small>${m.richtung === "ein" ? "Kontakt" : "Wir"}${m.ts ? " · " + esc(m.ts) : ""}</small></div></div>`
  ).join("") || emptyRow("Kein Verlauf.");
  openModal("Gesprächs-Verlauf", rows);
}

/* =========================== Content (Sub-Tabs) =========================== */
RENDER.content = renderContent;
async function renderContent() {
  const sub = SUBTAB.content || "trends";
  const map = { trends: "/api/trends", ideen: "/api/ideas", drafts: "/api/drafts", quellen: "/api/sources", aiinbox: "/api/ai-inbox" };
  const d = await jget(map[sub]) || {};
  let rows = "";
  if (sub === "trends") rows = (d.trends || []).map(t => card(trendLbl[t.status], t.title, `${esc(t.description || "")}<br><small>${esc(t.source_name || t.source_type || "")}${t.relevance ? " · " + esc(t.relevance) : ""}${t.score != null ? " · " + t.score : ""}</small>${t.source_url ? ` · <a href="${esc(t.source_url)}" target="_blank" rel="noopener">Quelle ↗</a>` : ""}`, ["reviewing", "approved", "ignored"].map(s => btn("trend", t.id, s, trendLbl[s])).join(""), t.status === "approved")).join("");
  if (sub === "ideen") rows = (d.ideas || []).map(x => card(ideaLbl[x.status], x.title, `${esc(x.description || "")}${x.ai_summary ? `<br><small>KI: ${esc(x.ai_summary)}</small>` : ""}${x.next_steps ? `<br><small>Nächste Schritte: ${esc(x.next_steps)}</small>` : ""}`, ["sorted", "planned", "done", "archived"].map(s => btn("idea", x.id, s, ideaLbl[s])).join(""), x.status === "done")).join("");
  if (sub === "drafts") rows = (d.drafts || []).map(x => card(draftLbl[x.status], x.title, `${x.hook ? `<b>Hook:</b> ${esc(x.hook)}<br>` : ""}${esc(x.caption || "")}${(x.hashtags && x.hashtags.length) ? `<br><small>${x.hashtags.map(h => "#" + esc(h)).join(" ")}</small>` : ""}<br><small>${esc(x.platform || "")}${x.content_format ? " · " + esc(x.content_format) : ""}</small>`, ["in_progress", "review", "approved", "scheduled", "published"].map(s => btn("draft", x.id, s, draftLbl[s])).join(""), ["approved", "published", "scheduled"].includes(x.status))).join("");
  if (sub === "quellen") rows = (d.sources || []).map(s => card(s.is_active ? "Aktiv" : "Inaktiv", s.name, `${esc(s.source_type || "")}${s.priority != null ? " · Prio " + s.priority : ""}${s.url ? ` · <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)} ↗</a>` : ""}`, `<button class="v2-btn" data-act="src-toggle" data-id="${esc(s.id)}" data-val="${s.is_active ? "0" : "1"}">${s.is_active ? "Deaktivieren" : "Aktivieren"}</button>`, s.is_active)).join("");
  if (sub === "aiinbox") rows = (d.items || []).map(it => card(recLbl[it.recommendation] || it.recommendation, it.title || "(ohne Titel)", `${esc(it.summary || "")}<br><small>${esc(it.source_type || "")}${it.author ? " · " + esc(it.author) : ""} · Relevanz ${it.hcc_relevance_score ?? "?"} · Machbarkeit ${it.feasibility_score ?? "?"} · Risiko ${it.risk_score ?? "?"}</small>${it.source_url ? ` · <a href="${esc(it.source_url)}" target="_blank" rel="noopener">Quelle ↗</a>` : ""}`, ["use", "investigate", "later", "ignore"].map(rc => btn("ai", it.id, rc, recLbl[rc])).join(""), it.recommendation === "use")).join("");
  $("#v2-app").innerHTML = secHead("Content-Ops") + tabs("content", [["trends", "Trends"], ["ideen", "Ideen-Labor"], ["drafts", "Drafts"], ["quellen", "Quellen"], ["aiinbox", "AI-Inbox"]]) + `<div class="v2-cards">${rows || emptyRow("Leer.")}</div>`;
}
function card(badge, titel, body, actions, good) {
  return `<div class="v2-card"><div class="v2-card-h"><span class="v2-badge ${good ? "ok" : "neutral"}">${esc(badge || "")}</span><b>${esc(titel)}</b></div><div class="v2-desc">${body}</div>${actions ? `<div class="v2-card-actions">${actions}</div>` : ""}</div>`;
}
const btn = (typ, id, val, lbl) => `<button class="v2-btn" data-act="status" data-typ="${typ}" data-id="${esc(id)}" data-val="${esc(val)}">${esc(lbl)}</button>`;

/* =========================== Cutter =========================== */
RENDER.cutter = renderCutter;
async function renderCutter() {
  const c = await jget("/api/cutter") || {};
  if (!c.verfuegbar) { $("#v2-app").innerHTML = secHead("Cutter") + `<div class="v2-tile w12">${emptyRow("Cutter-Jobs nicht verfügbar — SQL-Migration cutter_jobs in Supabase ausführen.")}</div>`; return; }
  const jobs = (c.jobs || []).map(j => { const st = j.status || "queued";
    const det = [j.clips_verwendet != null ? `${j.clips_verwendet} Clips` : "", j.dauer_sek != null ? `${j.dauer_sek}s` : "", j.groesse_mb != null ? `${j.groesse_mb} MB` : ""].filter(Boolean).join(" · ");
    return `<div class="v2-card"><div class="v2-card-h"><span class="v2-badge ${cutBadge[st] || "neutral"}">${cutLbl[st] || esc(st)}</span><b>${esc(j.projekt || "—")}</b></div>
      <div class="v2-sub">${esc(j.quelle || "")}${j.created_at ? " · " + zeit(j.created_at) : ""}${det ? " · " + esc(det) : ""}</div>
      ${j.reel_datei ? `<div class="v2-sub">🎬 ${esc(j.reel_datei)}</div>` : ""}${j.fehler ? `<div class="v2-desc" style="color:var(--v2-red)">${esc(j.fehler)}</div>` : ""}${j.note ? `<div class="v2-desc">${esc(j.note)}</div>` : ""}</div>`; }).join("") || emptyRow("Noch keine Reel-Jobs.");
  const form = `<div class="v2-form"><input id="cut-projekt" placeholder="Ordnername in der Cutter-Inbox (z. B. hsv_stadion)"><input id="cut-note" placeholder="Notiz (optional)"><button class="v2-btn pri" data-act="cutter-job">Job anstoßen</button><div id="cut-msg" class="v2-msg"></div><div class="v2-sub">Der Mac-Cutter holt den Job ab, schneidet den Ordner und meldet den Status zurück. Posten bleibt CEO-Tor.</div></div>`;
  $("#v2-app").innerHTML = secHead("Cutter") + `<div class="v2-grid">${tile("Reel-Job anstoßen", form, "w5")}${tile(`Jobs & Historie (${(c.jobs || []).length})`, jobs, "w7")}</div>`;
}

/* =========================== Entwicklungs-Roadmap (freigegebene Antraege) =========================== */
RENDER.devroadmap = renderDevRoadmap;
let ROADMAP_ITEMS = [];
const RM_BADGE = { offen: "wartet", in_arbeit: "neutral", umgesetzt: "ok", verworfen: "danger" };
const RM_LBL = { offen: "🔲 offen", in_arbeit: "🟡 in Arbeit", umgesetzt: "✅ umgesetzt", verworfen: "✖ verworfen" };
async function renderDevRoadmap() {
  const d = await jget("/api/entwicklungs-roadmap") || {};
  ROADMAP_ITEMS = d.items || [];
  const cards = ROADMAP_ITEMS.map(it => {
    const st = it.status || "offen";
    return `<div class="v2-card klick" data-act="roadmap-detail" data-id="${esc(it.roadmap_id)}" style="cursor:pointer"><div class="v2-card-h"><span class="v2-badge ${RM_BADGE[st] || "neutral"}">${RM_LBL[st] || esc(st)}</span><b>${esc(it.titel || "(ohne Titel)")}</b></div>
      <div class="v2-sub">von ${esc(it.von || "-")} · ${esc(it.quelle || "-")} · freigegeben ${esc((it.freigegeben_ts || "").slice(0, 10))}${it.notiz ? " · Notiz: " + esc(it.notiz) : ""}</div>
      <div class="v2-desc clamp">${antragPreview(it.beschreibung)}</div></div>`;
  }).join("") || emptyRow("Noch keine freigegebenen Anträge auf der Roadmap. Sobald du einen Vorschlag freigibst, erscheint er hier — Claude Code arbeitet die Punkte ab.");
  const offen = ROADMAP_ITEMS.filter(i => (i.status || "offen") === "offen").length;
  $("#v2-app").innerHTML = secHead("Entwicklungs-Roadmap", `<span class="v2-sub">${offen} offen · ${ROADMAP_ITEMS.length} gesamt</span>`) + `<div class="v2-cards">${cards}</div>`;
}
function roadmapDetail(rid) {
  const it = ROADMAP_ITEMS.find(x => x.roadmap_id === rid);
  if (!it) return;
  const st = it.status || "offen";
  openModal(it.titel || "Roadmap-Punkt", `<div class="v2-card-h"><span class="v2-badge ${RM_BADGE[st] || "neutral"}">${RM_LBL[st] || esc(st)}</span></div>
    <div class="v2-sub">von ${esc(it.von || "-")} · Quelle ${esc(it.quelle || "-")} · Antrag ${esc(it.antrag_id || "-")} · freigegeben ${esc((it.freigegeben_ts || "").slice(0, 10))}${it.notiz ? " · Notiz: " + esc(it.notiz) : ""}</div>
    <div class="v2-desc">${fmtBeschreibung(it.beschreibung)}</div>`);
}

/* =========================== Reels (Stufe C: 1-Tap-Freigabe) =========================== */
RENDER.reel = renderReels;
async function renderReels() {
  const d = await jget("/api/reel") || {};
  const badge = { wartet: "wartet", freigegeben: "ok", abgelehnt: "danger", gepostet: "ok", fehler: "danger" };
  const lbl = { wartet: "Wartet auf Freigabe", freigegeben: "Freigegeben – wird gepostet…", abgelehnt: "Abgelehnt", gepostet: "Gepostet", fehler: "Fehler" };
  const cards = (d.reels || []).map(r => {
    const wartet = r.status === "wartet", postbar = r.status === "freigegeben" || r.status === "fehler";
    return `<div class="v2-card"><div class="v2-card-h"><span class="v2-badge ${badge[r.status] || "neutral"}">${lbl[r.status] || esc(r.status)}</span><b>${esc(r.thema || "Reel")}</b> <small>${esc(r.datum || "")}${r.dauer_sek ? " · " + r.dauer_sek + "s" : ""}</small></div>
    <video src="/api/reel/${esc(r.id)}/video" controls playsinline preload="metadata" style="width:100%;max-height:60vh;border-radius:12px;background:#000;margin:8px 0"></video>
    <div class="v2-sub">Text fürs Video (wird so gepostet – kurz halten):</div>
    <textarea id="cap-${esc(r.id)}" rows="2" maxlength="180" ${wartet ? "" : "readonly"} style="width:100%;resize:vertical;font:inherit">${esc(r.caption || "")}</textarea>
    ${(r.spiele && r.spiele.length) ? `<div class="v2-sub">${r.spiele.map(esc).join(" · ")}</div>` : ""}
    ${r.status === "gepostet" && r.fb_video_id ? `<div class="v2-sub">✅ Facebook · video_id ${esc(r.fb_video_id)}</div>` : ""}
    ${r.status === "fehler" && r.fehler ? `<div class="v2-desc" style="color:var(--v2-red)">${esc(r.fehler)}</div>` : ""}
    ${wartet ? `<div style="display:flex;gap:8px;margin-top:8px"><button class="v2-btn ok" data-act="reel-freigeben" data-id="${esc(r.id)}">✅ Freigeben & posten</button><button class="v2-btn danger" data-act="reel-ablehnen" data-id="${esc(r.id)}">❌ Ablehnen</button></div>` : ""}
    ${postbar ? `<div style="display:flex;gap:8px;margin-top:8px"><button class="v2-btn" data-act="reel-posten" data-id="${esc(r.id)}">🔁 Erneut posten</button></div>` : ""}</div>`;
  }).join("") || emptyRow("Noch keine Reels — der Mac-Cutter reicht sie nach dem Schnitt hier ein (Auto-Posten bleibt CEO-Tor).");
  $("#v2-app").innerHTML = secHead("Reels") + `<div class="v2-cards">${cards}</div>`;
}

/* =========================== Wissen + Lagebild =========================== */
RENDER.wissen = renderWissen;
async function renderWissen() {
  const sub = SUBTAB.wissen || "brain";
  if (sub === "lagebild") {
    const l = await jget("/api/lagebild") || {}; const d = l.daten || {};
    const sek = (t, arr) => arr && arr.length ? tile(t, arr.map(z => `<div class="v2-list-row"><div class="grow">${z}</div></div>`).join(""), "w6") : "";
    const ent = (d.entscheidungen || []).map(x => `<b>${esc(x.titel)}</b> <small>[${esc(x.id)}] ${esc(x.status)}</small>`);
    const term = (d.termine_heute || []).map(x => `<b>${esc(x.zeit)}</b> ${esc(x.titel)}`);
    const mails = d.mails && d.mails.verfuegbar ? (d.mails.liste || []).map(x => `<b>${esc(x.von)}</b>: ${esc(x.betreff)}`) : [];
    const tick = (d.tickets || []).map(x => `${esc(x.frage)} <small>[${esc(x.id)}]</small>`);
    const ag = (d.agenda || []).map(esc);
    const body = [sek("Auf dich warten", ent), sek("Heute im Kalender", term), d.mails && d.mails.verfuegbar ? sek(`Ungelesene Mails (${d.mails.anzahl})`, mails) : "", sek("Offene Research-Tickets", tick), sek("Agenda", ag)].join("") || `<div class="v2-tile w12">${emptyRow("Alles ruhig. Nichts Dringendes. 👍")}</div>`;
    $("#v2-app").innerHTML = secHead("Wissen & Lagebild") + tabs("wissen", [["brain", "Second Brain"], ["lagebild", "Lagebild"]]) + `<div class="v2-grid">${body}</div>`;
    return;
  }
  const b = await jget("/api/brain") || {};
  const liste = (b.items || []).map(e => `<div class="v2-card"><div class="v2-card-h"><b>${esc(e.titel || (e.text || "").slice(0, 50))}</b></div>${e.tags && e.tags.length ? `<div class="v2-sub">${e.tags.map(esc).join(" · ")}</div>` : ""}<div class="v2-desc">${esc(e.text)}</div></div>`).join("") || emptyRow("Noch kein Wissen gespeichert. Merk dir was. 🧠");
  const search = `<div class="v2-form-row"><input id="brain-q" placeholder="Wissen durchsuchen (intern + Gmail + Drive)…"><button class="v2-btn" data-act="brain-suchen">🔍 Suchen</button></div>`;
  const add = `<div class="v2-form-row"><input id="brain-note" placeholder="Neues Wissen merken…"><button class="v2-btn ok" data-act="brain-merken">＋ Merken</button></div>`;
  $("#v2-app").innerHTML = secHead("Wissen & Lagebild") + tabs("wissen", [["brain", "Second Brain"], ["lagebild", "Lagebild"]]) + `<div class="v2-tile w12">${search}<div id="brain-results" class="v2-cards">${liste}</div>${add}</div>`;
}

/* =========================== Agenten (Organigramm-Mindmap, aus V1 portiert) =========================== */
RENDER.agenten = renderAgents;
async function renderAgents() {
  const a = await jget("/api/agenten") || {};
  const deps = a.departments || [], ceo = a.ceo || {}, luna = a.luna || {};
  const stL = (st) => st === "active" ? "Aktiv" : st === "offline" ? "Geplant" : "Standby";
  const legend = `<div class="v2-mm-legend"><span class="lg active"><i></i>Aktiv</span><span class="lg standby"><i></i>Standby</span><span class="lg offline"><i></i>Geplant</span><span class="lg human"><i></i>CEO</span></div>`;
  let svg = emptyRow("Keine Agenten geladen.");
  if (deps.length) {
    // Top-down-Baum: CEO -> LUNA -> Abteilungen auf ZWEI Reihen (A/B) -> Unter-Agenten (identische Geometrie wie V1).
    const bw = 96, bh = 34, colStep = 106, padX = 18, padTop = 20, vGap = 66, subStep = 40, rowGap = 34;
    const half = Math.ceil((deps.length || 1) / 2), rowA = deps.slice(0, half), rowB = deps.slice(half);
    const cols = Math.max(rowA.length, rowB.length, 1);
    const W = padX * 2 + (cols - 1) * colStep + bw, centerX = W / 2;
    const rowX = (row, j) => centerX - ((row.length - 1) * colStep) / 2 + j * colStep;
    const rowMaxSub = row => Math.max(0, ...row.map(d => (d.subs || []).length));
    const maxSubA = rowMaxSub(rowA), maxSubB = rowMaxSub(rowB);
    const yCEO = padTop + bh / 2, yLUNA = yCEO + vGap, yDEPA = yLUNA + vGap, ySUBA = yDEPA + vGap;
    const subABottom = maxSubA > 0 ? ySUBA + (maxSubA - 1) * subStep : yDEPA;
    const yDEPB = subABottom + rowGap + vGap, ySUBB = yDEPB + vGap;
    const subBBottom = maxSubB > 0 ? ySUBB + (maxSubB - 1) * subStep : yDEPB;
    const H = subBBottom + bh / 2 + 12;
    const box = (cxp, y, w, titel, cls, sub, tip) => {
      const t = sub ? `<text x="${cxp}" y="${y - 3}" text-anchor="middle" class="v2-mm-bt">${esc(titel)}</text><text x="${cxp}" y="${y + 10}" text-anchor="middle" class="v2-mm-bs">${esc(sub)}</text>`
        : `<text x="${cxp}" y="${y + 4}" text-anchor="middle" class="v2-mm-bt">${esc(titel)}</text>`;
      return `<g class="v2-mm-b ${cls}">${tip ? `<title>${esc(tip)}</title>` : ""}<rect x="${cxp - w / 2}" y="${y - bh / 2}" width="${w}" height="${bh}" rx="9"/>${t}</g>`;
    };
    const vlink = (x1, y1, x2, y2, cls) => { const my = (y1 + y2) / 2; return `<path d="M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}" class="v2-mm-link ${cls}"/>`; };
    let links = vlink(centerX, yCEO + bh / 2, centerX, yLUNA - bh / 2, "human"), nodes = "";
    const drawRow = (row, yDEP, ySUB) => row.forEach((d, i) => {
      const cx = rowX(row, i);
      links += vlink(centerX, yLUNA + bh / 2, cx, yDEP - bh / 2, d.status);
      const num = (d.name.split("·")[0] || "").trim(), kuerzel = (d.name.split("·")[1] || d.name).trim();
      nodes += box(cx, yDEP, bw, kuerzel, "dep " + d.status, num, d.rolle);
      (d.subs || []).forEach((s, j) => {
        const sy = ySUB + j * subStep, py = j === 0 ? yDEP + bh / 2 : sy - subStep + bh / 2;
        links += vlink(cx, py, cx, sy - bh / 2, s.status);
        nodes += box(cx, sy, bw, s.name, "sub " + s.status, "", s.name + " · " + stL(s.status));
      });
    });
    drawRow(rowA, yDEPA, ySUBA); drawRow(rowB, yDEPB, ySUBB);
    nodes += box(centerX, yCEO, 126, ceo.name || "CEO", "human", ceo.rolle);
    nodes += box(centerX, yLUNA, 142, luna.name || "LUNA", "luna", luna.rolle || "Head of Agents");
    svg = `<div class="v2-mm-scroll"><svg viewBox="0 0 ${W} ${H}" class="v2-mm-svg" preserveAspectRatio="xMidYMid meet" style="min-width:${Math.min(W, 900)}px">${links}${nodes}</svg></div>`;
  }
  $("#v2-app").innerHTML = secHead("Agenten-Organisation") + tile("Organigramm — Live-Status", legend + svg, "w12");
}

/* =========================== System (Sub-Tabs) =========================== */
RENDER.system = renderSystem;
async function renderSystem() {
  const sub = SUBTAB.system || "research";
  STATE = await jget("/api/state") || STATE;
  let body;
  if (sub === "research") body = (STATE.research || []).map(r => `<div class="v2-list-row"><span class="v2-badge neutral">${esc(firstOf(r, ["status", "abteilung"], ""))}</span><div class="grow"><b>${esc(firstOf(r, ["frage", "titel"], ""))}</b>${r.id ? `<small>${esc(r.id)}</small>` : ""}</div></div>`).join("") || emptyRow("Keine Research-Tickets.");
  if (sub === "meldungen") body = (STATE.meldungen || []).map(m => `<div class="v2-list-row"><span class="v2-badge neutral">${esc(m.abteilung || "")}</span><div class="grow"><b>${esc(m.text)}</b><small>${esc(zeitKurz(m.ts))}</small></div></div>`).join("") || emptyRow("Keine Meldungen.");
  if (sub === "aktivitaet") body = (STATE.aktivitaet || []).map(a => `<div class="v2-list-row"><span class="v2-badge live">Live</span><div class="grow"><b>${esc(a.akteur || "")}</b> ${esc(a.aktion || "")}<small>${esc(zeitKurz(a.ts))}</small></div></div>`).join("") || emptyRow("Keine Aktivität.");
  if (sub === "finanzen") { const f = STATE.finance || {}; body = `<div class="v2-kv"><span>Monatsbudget</span><b>${esc(f.monatsbudget || "unbekannt")}</b></div><div class="v2-kv"><span>Offene Aufträge</span><b>${(STATE.antraege || []).length}</b></div><div class="v2-kv"><span>Offene Research-Tickets</span><b>${(STATE.research || []).length}</b></div>`; }
  $("#v2-app").innerHTML = secHead("System") + tabs("system", [["research", "Research"], ["meldungen", "Meldungen"], ["aktivitaet", "Aktivität"], ["finanzen", "Finanzen"]]) + `<div class="v2-tile w12">${body}</div>`;
}

/* =========================== Team =========================== */
RENDER.team = renderTeam;
async function renderTeam() {
  const t = await jget("/api/team") || {};
  if (!t.verfuegbar) { $("#v2-app").innerHTML = secHead("Team") + `<div class="v2-tile w12">${emptyRow("Nutzer-Tabelle nicht verfügbar — SQL-Migration luna_os_users in Supabase ausführen.")}</div>`; return; }
  const users = (t.users || []).map(u => `<div class="v2-card"><div class="v2-card-h"><span class="v2-badge ${u.is_active === false ? "neutral" : "aktiv"}">${u.is_active === false ? "Inaktiv" : "Aktiv"}</span><b>${esc(u.display_name || u.username)}</b></div>
    <div class="v2-sub">@${esc(u.username)} · ${esc(rolleLbl[u.role] || u.role || "")} · Module: ${(u.allowed_modules || []).map(esc).join(", ") || "—"}${u.role === "owner" ? " (alle)" : ""}</div>
    <div class="v2-card-actions"><button class="v2-btn" data-act="team-aktiv" data-id="${esc(u.username)}" data-val="${u.is_active === false ? "1" : "0"}">${u.is_active === false ? "Aktivieren" : "Deaktivieren"}</button></div></div>`).join("") || emptyRow("Noch keine Nutzer.");
  const mods = (t.module || []).map(m => `<label class="v2-modlbl"><input type="checkbox" class="team-mod" value="${esc(m.id)}"> ${esc(m.label)}</label>`).join("");
  const rollen = (t.rollen || ["content"]).map(r => `<option value="${esc(r)}">${esc(rolleLbl[r] || r)}</option>`).join("");
  const form = `<div class="v2-form"><input id="team-username" placeholder="Benutzername (Login)"><input id="team-name" placeholder="Anzeigename (optional)"><input id="team-pw" type="password" placeholder="Passwort"><select id="team-role">${rollen}</select><div class="v2-mods"><small>Module (leer = Standard der Rolle):</small>${mods}</div><button class="v2-btn pri" data-act="team-save">Anlegen / aktualisieren</button><div id="team-msg" class="v2-msg"></div></div>`;
  $("#v2-app").innerHTML = secHead("Team") + `<div class="v2-grid">${tile("Neuen Nutzer anlegen", form, "w5")}${tile("Nutzer", users, "w7")}</div>`;
}

/* =========================== Einstellungen =========================== */
const SETTING_KEYS = ["depot_stop_pct", "depot_target_pct", "depot_alerts", "paper_stop_pct", "paper_target_pct",
  "paper_order_betrag_usd", "paper_dip_schwelle_pct", "briefing_morgen_stunde", "briefing_abend_stunde",
  "ruhezeit_von", "ruhezeit_bis", "alert_investment", "alert_crm", "alert_security", "alert_content"];
const SETTING_BOOLS = new Set(["depot_alerts", "alert_investment", "alert_crm", "alert_security", "alert_content"]);
const SETTING_OPT = new Set(["ruhezeit_von", "ruhezeit_bis"]);
RENDER.einstellungen = renderEinstellungen;
async function renderEinstellungen() {
  const cfg = await jget("/api/settings") || {};
  const nInp = (k, label, sub) => `<label class="v2-set-row"><span class="v2-set-lbl">${esc(label)}${sub ? `<small>${esc(sub)}</small>` : ""}</span><input id="set-${k}" class="v2-inp" type="number" step="any" value="${cfg[k] != null ? esc(String(cfg[k])) : ""}" style="width:120px"></label>`;
  const chk = (k, label, sub) => `<label class="v2-set-row"><span class="v2-set-lbl">${esc(label)}${sub ? `<small>${esc(sub)}</small>` : ""}</span><input id="set-${k}" type="checkbox" ${cfg[k] ? "checked" : ""}></label>`;
  const a = nInp("depot_stop_pct", "Stop-Loss-Hinweis", "ab −x %") + nInp("depot_target_pct", "Take-Profit-Hinweis", "ab +x %") + chk("depot_alerts", "Advisory-Alerts (Telegram)", "an/aus");
  const b = nInp("paper_stop_pct", "Auto-Stop-Loss", "verkauft ab −x %") + nInp("paper_target_pct", "Take-Profit-Vorschlag", "ab +x %") + nInp("paper_order_betrag_usd", "Standard-Order-Betrag", "USD je 1-Tap-Kauf") + nInp("paper_dip_schwelle_pct", "Live-Dip-Empfindlichkeit", "% Bewegung");
  const c = nInp("briefing_morgen_stunde", "Morgen-Briefing", "Stunde 0–23") + nInp("briefing_abend_stunde", "Abend-Briefing", "Stunde 0–23") + nInp("ruhezeit_von", "Nicht stören von", "Stunde (leer = aus)") + nInp("ruhezeit_bis", "Nicht stören bis", "Stunde (leer = aus)") + chk("alert_investment", "Alerts: Investment") + chk("alert_crm", "Alerts: CRM") + chk("alert_security", "Alerts: Security") + chk("alert_content", "Alerts: Content");
  const actions = `<span id="set-msg" class="v2-msg"></span><button class="v2-btn pri" data-act="settings-save">Speichern</button>`;
  $("#v2-app").innerHTML = secHead("Einstellungen", actions) + `<div class="v2-grid">
    ${tile("🏦 Echtes Depot (Beratung)", a, "w4")}
    ${tile("💼 Paper-Depot (Spielgeld)", b, "w4")}
    ${tile("🔔 Benachrichtigungen & Briefings", c, "w4")}
  </div><div class="v2-sub" style="margin-top:8px">Gilt für Anzeige, Telegram-Hinweise und Briefings. Moduswechsel (advisory→paper→live) und Budget bleiben separat abgesichert.</div>`;
}

/* =========================== Aktionen =========================== */
const reFreig = () => AKTIV === "dash" ? renderDash() : renderFreigaben();  // Antrags-Aktion aus Dashboard ODER Freigaben
async function handleAct(act, el) {
  const id = el.dataset.id, val = el.dataset.val, asset = el.dataset.asset, typ = el.dataset.typ;
  const flash = (m) => { const o = el.textContent; el.textContent = m; return o; };
  switch (act) {
    case "antrag-freigeben": await jpost(`/api/antraege/${id}/freigeben`); return reFreig();
    case "antrag-ablehnen": { const grund = prompt("Grund der Ablehnung?", ""); if (grund === null) return; await jpost(`/api/antraege/${id}/ablehnen`, { grund }); return reFreig(); }
    case "antrag-revidieren": { const feedback = prompt("Was soll anders/besser sein? LUNA überarbeitet den Antrag (du musst neu freigeben).", ""); if (feedback === null) return; flash("⏳ überarbeitet…"); await jpost(`/api/antraege/${id}/revidieren`, { feedback }); return reFreig(); }
    case "antrag-loeschen": if (!confirm("Antrag wirklich löschen?")) return; await jpost(`/api/antraege/${id}/loeschen`); return reFreig();
    case "antrag-mehr": { flash("⏳ Agenten…"); const r = await jpost(`/api/antraege/${id}/mehr-info`); if (r && r.bewertung) alert("LUNA-Bewertung:\n\n" + r.bewertung); return reFreig(); }
    case "antrag-reformat": if (!confirm("Alle offenen Anträge neu formatieren? Freigegebene werden zurückgesetzt.")) return; flash("⏳ formatiert…"); await jpost("/api/antraege/neu-formatieren"); return reFreig();
    case "antrag-detail": return antragDetail(id);
    case "roadmap-detail": return roadmapDetail(id);
    case "crm-todo": await jpost(`/api/crm/todo/${id}/erledigen`); return renderCrm();
    case "crm-sync": { flash("⏳ synchronisiert…"); const r = await jpost("/api/crm/sync"); if (r && r.api_fehler) alert("Instagram-Sync-Fehler:\n" + r.api_fehler); else if (r && r.ok === false) alert("Sync nicht möglich:\n" + (r.hinweis || "unbekannt")); return renderCrm(); }
    case "crm-firma": return crmFirma(id);
    case "reel-freigeben": { const t = (($(`#cap-${id}`) || {}).value || "").trim(); flash("⏳ …"); await jpost(`/api/reel/${id}/freigeben`, { caption: t }); return renderReels(); }
    case "reel-ablehnen": if (!confirm("Reel ablehnen? Es wird nicht gepostet.")) return; await jpost(`/api/reel/${id}/ablehnen`); return renderReels();
    case "reel-posten": flash("⏳ …"); await jpost(`/api/reel/${id}/posten`); return renderReels();
    case "radar-kontakt": return radarKontakt(id);
    case "status": {
      const map = { trend: ["/api/trends/", "status", renderContent], idea: ["/api/ideas/", "status", renderContent], draft: ["/api/drafts/", "status", renderContent], ai: ["/api/ai-inbox/", "recommendation", renderContent] };
      const [base, key, re] = map[typ]; await jpost(`${base}${encodeURIComponent(id)}/${key === "recommendation" ? "recommendation" : "status"}`, key === "recommendation" ? { recommendation: val } : { status: val }); return re();
    }
    case "src-toggle": await jpost(`/api/sources/${encodeURIComponent(id)}/aktiv`, { is_active: val === "1" }); return renderContent();
    case "inv-sammeln": flash("⏳ sammelt…"); await jpost("/api/investment/sammeln"); return renderInvestment();
    case "inv-backfill": flash("⏳ Historie…"); await jpost("/api/investment/backfill", { seit: "2026-01-01" }); return renderInvestment();
    case "inv-screen": flash("⏳ Screen…"); await jpost("/api/investment/screen"); return AKTIV === "investment" ? renderInvestment() : go("investment");
    case "inv-insider": flash("⏳ Insider…"); await jpost("/api/investment/insider-scan"); return renderInvestment();
    case "inv-add": await jpost("/api/investment/watchlist", { symbol: id, asset: asset || "aktie" }); return renderInvestment();
    case "inv-remove": await jpost("/api/investment/watchlist/remove", { symbol: id }); return renderInvestment();
    case "inv-detail": return invDetail(id, asset);
    case "depot-trade": {
      const sym = (($("#dep-sym") || {}).value || "").trim();
      if (!sym) { flash("Symbol fehlt."); return; }
      const side = ($("#dep-side") || {}).value || "kauf";
      const stueck = Number(($("#dep-stueck") || {}).value || 0);
      if (!(stueck > 0)) { flash("Stück fehlt."); return; }
      const r = await jpost("/api/investment/depot/trade", { symbol: sym, side, klasse: ($("#dep-klasse") || {}).value || "aktie",
        stueck, preis: ($("#dep-preis") || {}).value || 0, gebuehr: ($("#dep-gebuehr") || {}).value || 0,
        kurs_id: (($("#dep-id") || {}).value || "").trim() });
      flash(r && r.ok ? `${side === "verkauf" ? "Verkauf" : "Kauf"} „${sym.toUpperCase()}" gebucht.` : "Fehler beim Buchen.");
      return renderInvestment();
    }
    case "depot-storno": if (!confirm("Diese Buchung stornieren?")) return; await jpost("/api/investment/depot/storno", { id }); return renderInvestment();
    case "settings-save": {
      const settings = {};
      for (const k of SETTING_KEYS) {
        const e = $("#set-" + k); if (!e) continue;
        if (SETTING_BOOLS.has(k)) settings[k] = e.checked;
        else if (SETTING_OPT.has(k)) settings[k] = e.value.trim() === "" ? null : e.value;
        else settings[k] = e.value;
      }
      const r = await jpost("/api/settings", { settings }); const msg = $("#set-msg");
      if (msg) { msg.textContent = r && r.ok ? "Gespeichert ✓" : "Fehler beim Speichern"; msg.className = "v2-msg " + (r && r.ok ? "ok" : "err"); }
      return;
    }
    case "paper-sell": {
      const set = (k, v) => { const e = $("#" + k); if (e) e.value = v; };
      set("po-side", "sell"); set("po-sym", id); set("po-klasse", asset === "krypto" ? "krypto" : "aktie"); set("po-qty", val || "");
      const e = $("#po-sym"); if (e) e.scrollIntoView({ block: "center" });
      flash("Verkauf vorbereitet — Stück prüfen und auf Order klicken."); return;
    }
    case "paper-order": {
      const sym = (($("#po-sym") || {}).value || "").trim();
      if (!sym) { flash("Symbol fehlt."); return; }
      const side = ($("#po-side") || {}).value || "buy";
      const assetK = ($("#po-klasse") || {}).value || "aktie";
      const qty = Number(($("#po-qty") || {}).value || 0);
      if (!(qty > 0)) { flash("Stück fehlt."); return; }
      const est = await jpost("/api/investment/paper-order", { symbol: sym, side, asset: assetK, qty });
      if (!est) { flash("Order fehlgeschlagen."); return; }
      if (est.abgelehnt) { alert("Risk-Ablehnung:\n" + (est.grund || "")); return; }
      if (est.bestaetigung_noetig) {
        if (!confirm(`${side === "sell" ? "VERKAUF" : "KAUF"} ${qty} ${sym.toUpperCase()} (~${geld(est.geschaetzter_wert, "USD")}).\nRisk: ${est.risk || "ok"}\n\nPaper-Order (Spielgeld) ausführen?`)) return;
        const done = await jpost("/api/investment/paper-order", { symbol: sym, side, asset: assetK, qty, bestaetigt: true });
        flash(done && done.ok ? "✅ Paper-Order platziert." : "Fehler: " + ((done && done.hinweis) || "unbekannt"));
        return renderInvestment();
      }
      flash(est.ok ? "✅ platziert." : "Hinweis: " + (est.hinweis || "unbekannt"));
      return renderInvestment();
    }
    case "cutter-job": { const p = ($("#cut-projekt") || {}).value || "", n = ($("#cut-note") || {}).value || "", msg = $("#cut-msg"); if (!p.trim()) { if (msg) { msg.textContent = "Ordnername ist Pflicht."; msg.className = "v2-msg err"; } return; } const r = await jpost("/api/cutter/job", { projekt: p.trim(), note: n.trim() }); if (msg) { msg.textContent = r && r.ok ? `Job „${p}" in Warteschlange.` : "Fehler: " + ((r && (r.hinweis || r.fehler)) || "unbekannt"); msg.className = "v2-msg " + (r && r.ok ? "ok" : "err"); } if (r && r.ok) renderCutter(); return; }
    case "brain-suchen": { const q = ($("#brain-q") || {}).value || ""; const d = await jget("/api/brain?q=" + encodeURIComponent(q)) || {}; const box = $("#brain-results"); if (box) box.innerHTML = (d.items || []).map(e => `<div class="v2-card"><div class="v2-card-h"><b>${esc(e.titel || (e.text || "").slice(0, 50))}</b></div><div class="v2-desc">${esc(e.text)}</div></div>`).join("") || emptyRow("Keine Treffer."); return; }
    case "brain-merken": { const inp = $("#brain-note"); const v = (inp && inp.value || "").trim(); if (!v) return; await jpost("/api/brain", { text: v }); if (inp) inp.value = ""; return renderWissen(); }
    case "team-aktiv": await jpost(`/api/team/${encodeURIComponent(id)}/aktiv`, { is_active: val === "1" }); return renderTeam();
    case "team-save": { const g = (i) => ($("#" + i) || {}).value || ""; const mods = [...document.querySelectorAll(".team-mod:checked")].map(c => c.value); const msg = $("#team-msg"); const r = await jpost("/api/team", { username: g("team-username").trim(), display_name: g("team-name").trim(), passwort: g("team-pw"), role: g("team-role"), allowed_modules: mods }); if (msg) { msg.textContent = r && r.ok ? "Gespeichert." : "Fehler: " + ((r && r.hinweis) || "unbekannt"); msg.className = "v2-msg " + (r && r.ok ? "ok" : "err"); } if (r && r.ok) renderTeam(); return; }
  }
}
async function antragDetail(id) {
  openModal("Antrag " + id, `<div class="v2-empty">Lade Details…</div>`);
  const a = await jget(`/api/antraege/${encodeURIComponent(id)}`); if (!a) { openModal("Antrag " + id, emptyRow("Konnte Details nicht laden.")); return; }
  const verlauf = (a.verlauf || []).map(s => `<div class="v2-list-row"><span>${esc(zeit(s.ts))}</span><div class="grow"><b>${esc(evLbl[s.event] || s.event)}</b>${s.akteur ? " · " + esc(s.akteur) : ""}${s.grund ? `<br><small>${esc(s.grund)}</small>` : ""}</div></div>`).join("") || emptyRow("noch keine Schritte");
  openModal(a.titel || ("Antrag " + id), `<div class="v2-card-h"><span class="v2-badge ${badgeCls(a.status)}">${esc(a.status)}</span></div>
    <div class="v2-sub">von ${esc(a.von)}${a.kategorie ? " · " + esc(a.kategorie) : ""} · ${esc(a.id)}</div>
    <div class="v2-desc">${fmtBeschreibung(a.beschreibung)}</div>${a.betroffen ? `<div class="v2-kv"><span>Betroffen</span><b>${esc(a.betroffen)}</b></div>` : ""}
    <h3>Verlauf</h3>${verlauf}`);
}

/* =========================== LUNA-Chat + Voice =========================== */
let CHAT_OPEN = false, REC = null, LISTENING = false, AUDIO = null;
let AVATAR = null, AV_MOD = null;   // 3D-Hologramm (lazy geladen)

function updateHoloToggle() {
  const b = $("#v2-holo-toggle"); if (!b) return;
  b.hidden = ME.avatar_enabled === false;
  const on = PREFS.avatar === "hologramm";
  b.textContent = on ? "🌙" : "◐"; b.classList.toggle("on", on);
  b.title = on ? "Hologramm aktiv — zum Orb wechseln" : "Orb aktiv — zum 3D-Hologramm wechseln";
}
async function applyAvatar() {
  updateHoloToggle();
  const holo = $("#luna-holo"), orb = $("#v2-orb"); if (!holo || !orb) return;
  const on = ME.avatar_enabled !== false && PREFS.avatar === "hologramm";
  if (on) {
    holo.hidden = false; orb.style.display = "none";
    if (!AVATAR) {
      try { AV_MOD = AV_MOD || await import("/static/luna-avatar.js?v=11");
        AVATAR = AV_MOD.createAvatar(holo, { reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches }); }
      catch (e) { console.warn("[luna] Avatar-Ladefehler", e); AVATAR = null; }
      if (!AVATAR) { holo.hidden = true; orb.style.display = ""; }   // Fallback auf Orb
    }
  } else {
    if (AVATAR) { AVATAR.dispose(); AVATAR = null; }
    holo.hidden = true; orb.style.display = "";
  }
}
async function setAvatarPref(mode) {
  PREFS = { ...PREFS, avatar: mode };
  try { localStorage.setItem("luna-v2-avatar", mode); } catch { }
  jpost("/api/prefs", { prefs: PREFS });
  await applyAvatar();
}
function chatShell() {
  $("#v2-chat").innerHTML = `<header>LUNA <button class="v2-icon" id="v2-mic" title="Sprechen">🎙</button></header>
    <div class="log" id="v2-log"><div class="msg luna">Hallo! Wie kann ich helfen?</div></div>
    <form id="v2-chatform"><input id="v2-chatin" placeholder="Frag LUNA …" autocomplete="off"><button class="v2-btn pri" type="submit">↑</button></form>`;
  $("#v2-chatform").addEventListener("submit", (e) => { e.preventDefault(); const v = $("#v2-chatin").value.trim(); if (v) { $("#v2-chatin").value = ""; sendChat(v); } });
  $("#v2-mic").addEventListener("click", toggleVoice);
}
function toggleChat(open) { CHAT_OPEN = open == null ? !CHAT_OPEN : open; const c = $("#v2-chat"); c.hidden = !CHAT_OPEN; if (CHAT_OPEN && !c.dataset.init) { chatShell(); c.dataset.init = "1"; } }
function addMsg(who, text) { const log = $("#v2-log"); if (!log) return; const d = document.createElement("div"); d.className = "msg " + who; d.textContent = text; log.appendChild(d); log.scrollTop = log.scrollHeight; }
async function sendChat(text) { addMsg("me", text); setOrb("thinking"); const r = await jpost("/api/chat", { text }); const reply = (r && (r.reply || r.antwort)) || "…"; addMsg("luna", reply); lunaSpeak(reply); }
function setOrb(state) {
  const o = $("#v2-orb"); if (o) o.className = "v2-orb " + state;
  if (AVATAR) AVATAR.setState(state);
  const holo = $("#luna-holo"); if (holo) holo.classList.toggle("big", state === "speaking" || state === "listening");
}
async function lunaSpeak(text) {
  let raf = 0;
  try {
    const r = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: String(text).slice(0, 600) }) });
    if (!r.ok) { setOrb("idle"); return; }
    const buf = await r.arrayBuffer(); const ctx = AUDIO || (AUDIO = new (window.AudioContext || window.webkitAudioContext)());
    const audio = await ctx.decodeAudioData(buf); const src = ctx.createBufferSource(); src.buffer = audio;
    if (AVATAR) {   // Lip-Sync: Amplitude von Lolas Stimme -> Avatar-Energie (Mund/Glow)
      const an = ctx.createAnalyser(); an.fftSize = 64; an.smoothingTimeConstant = 0.7; src.connect(an); an.connect(ctx.destination);
      const data = new Uint8Array(an.frequencyBinCount);
      const loop = () => { an.getByteFrequencyData(data); let s = 0; for (const v of data) s += v; AVATAR.setEnergy(Math.min(1, (s / data.length) / 105)); raf = requestAnimationFrame(loop); }; loop();
    } else src.connect(ctx.destination);
    setOrb("speaking");
    src.onended = () => { setOrb("idle"); if (raf) cancelAnimationFrame(raf); if (AVATAR) AVATAR.setEnergy(0); };
    src.start();
  } catch { setOrb("idle"); if (raf) cancelAnimationFrame(raf); }
}
function toggleVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SR) { toggleChat(true); return; }
  if (LISTENING) { REC && REC.stop(); return; }
  REC = new SR(); REC.lang = "de-DE"; REC.interimResults = false;
  REC.onstart = () => { LISTENING = true; setOrb("listening"); }; REC.onend = () => { LISTENING = false; setOrb("idle"); };
  REC.onresult = (e) => { const t = e.results[0][0].transcript; toggleChat(true); sendChat(t); }; REC.start();
}

/* =========================== SSE Live =========================== */
function connectSSE() { try { const es = new EventSource("/api/events"); es.onmessage = () => { if (AKTIV === "dash" && !EDIT2) renderDash(); }; } catch { } }

/* =========================== Events + Boot =========================== */
document.addEventListener("click", (e) => {
  const ed = e.target.closest("[data-editdash]"); if (ed) { EDIT2 = !EDIT2; renderDash(); return; }
  const wh2 = e.target.closest("[data-whide2]"); if (wh2) { hideW2(wh2.dataset.whide2); return; }
  const wa2 = e.target.closest("[data-wadd2]"); if (wa2) { showW2(wa2.dataset.wadd2); return; }
  const ac0 = e.target.closest("[data-act]"); if (ac0) { handleAct(ac0.dataset.act, ac0); return; }  // Aktionen VOR Navigation (Inline-Buttons in klickbaren Kacheln)
  const g = e.target.closest("[data-go]"); if (g) { go(g.dataset.go); return; }
  const tb = e.target.closest("[data-tab]"); if (tb) { const [sec, id] = tb.dataset.tab.split(":"); go(sec, id); return; }
  const um = e.target.closest("[data-ui-mode]"); if (um) { setUiMode(um.dataset.uiMode); return; }
  const tc = e.target.closest("[data-toggle-chat]"); if (tc) { toggleChat(); return; }
  const orb = e.target.closest("#v2-orb"); if (orb) { toggleVoice(); return; }
  const holo = e.target.closest("#luna-holo"); if (holo) { toggleVoice(); return; }
  const ht = e.target.closest("#v2-holo-toggle"); if (ht) { setAvatarPref(PREFS.avatar === "hologramm" ? "orb" : "hologramm"); return; }
  const th = e.target.closest("#v2-theme"); if (th) { toggleTheme(); return; }
  const mc = e.target.closest("[data-modal-close]"); if (mc) { closeModal(); return; }
  const ac = e.target.closest("[data-act]"); if (ac) { handleAct(ac.dataset.act, ac); return; }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeModal(); return; }
  if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches('.v2-tile.klick[role="button"]')) {
    e.preventDefault(); const el = e.target;
    if (el.dataset.go) go(el.dataset.go); else if (el.dataset.tab) { const [s, i] = el.dataset.tab.split(":"); go(s, i); }
  }
});

/* Drag&Drop zum Anordnen der Dashboard-Widgets (nur im Edit-Modus) */
document.addEventListener("dragstart", (e) => { const t = e.target.closest("[data-wid]"); if (!t || !EDIT2) return; DRAG2 = t.dataset.wid; t.classList.add("dragging"); });
document.addEventListener("dragend", (e) => { const t = e.target.closest("[data-wid]"); if (t) t.classList.remove("dragging"); DRAG2 = null; });
document.addEventListener("dragover", (e) => { if (EDIT2 && DRAG2) e.preventDefault(); });
document.addEventListener("drop", (e) => { if (!EDIT2 || !DRAG2) return; const t = e.target.closest("[data-wid]"); if (!t || t.dataset.wid === DRAG2) return; e.preventDefault(); reorder2(DRAG2, t.dataset.wid); });

(async function boot() {
  applyTheme();
  [ME, PREFS] = await Promise.all([jget("/api/me").then(x => x || ME), jget("/api/prefs").then(x => (x && x.prefs) || {})]);
  let saved = PREFS.v2_dashboard; if (!saved) { try { saved = JSON.parse(localStorage.getItem("luna-v2-dash") || "null"); } catch { } }
  DASH2 = normDash2(saved);
  if (!PREFS.avatar) { try { const a = localStorage.getItem("luna-v2-avatar"); if (a) PREFS.avatar = a; } catch { } }
  buildShell(); go("dash"); connectSSE(); applyAvatar();
})();
