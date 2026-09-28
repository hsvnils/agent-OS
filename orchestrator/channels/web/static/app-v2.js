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
const DASH2_DEFAULT = ["todos", "freigaben", "loop", "budget", "trefferquote", "provider", "compliance", "live", "schritte", "meldungen", "research"];
const DASH2_TITEL = { todos: "Zu erledigen", budget: "Monatsbudget", trefferquote: "Prognose-Trefferquote", freigaben: "Offene Freigaben", provider: "Provider verbunden", loop: "Investment · Lern-Loop", compliance: "Compliance-Puls", live: "Live-Aktivität", schritte: "Erste Schritte", meldungen: "Meldungen", research: "Research-Tickets" };
let DASH2 = { order: [...DASH2_DEFAULT], hidden: [] };
let EDIT2 = false, DRAG2 = null;
let _VERLAUF = [], _trendRO = null;

function normDash2(l) {
  l = l || {}; const hidden = (Array.isArray(l.hidden) ? l.hidden : []).filter(id => DASH2_DEFAULT.includes(id));
  const order = (Array.isArray(l.order) ? l.order : []).filter(id => DASH2_DEFAULT.includes(id));
  if (!order.includes("todos")) order.unshift("todos");             // neu (2026-09-28): ganz nach oben
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
  { id: "kunden", icon: "🏢", label: "Kunden", app: "kunden" },
  { id: "angebote", icon: "📄", label: "Angebote", app: "angebote" },
  { id: "finanzen", icon: "💶", label: "Finanzen", app: "finanzen" },
  { id: "rechnungen", icon: "🧾", label: "Rechnungen", app: "rechnungen" },
  { id: "belege", icon: "📥", label: "Belege", app: "belege" },
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
  jpost("/api/nutzung", { app: id });   // Feature-Friedhof: App-Oeffnung zaehlen (fire-and-forget)
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
  "Lern-Loop · Fehler-Verlauf": `Zwei FEHLER-Kurven (keine echten Kurse!). „LUNA" = die Vorhersagen von LUNA. „Baseline" = ein Dummy, der stur sagt „der Kurs bleibt gleich" — die Messlatte. Gezeigt wird, wie weit beide im Schnitt danebenlagen: je tiefer, desto besser. LUNA ist nur dann wirklich gut, wenn die LUNA-Linie UNTER der Baseline liegt.`,
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
function openModal(title, html, breit = false) {   // breit = ganze Seite (z. B. Angebots-Editor)
  let m = $("#v2-modal"); if (!m) { m = document.createElement("div"); m.id = "v2-modal"; document.body.appendChild(m); }
  m.innerHTML = `<div class="v2-modal-back" data-modal-close></div><div class="v2-modal-card${breit ? " breit" : ""}"><header><b>${esc(title)}</b><button class="v2-icon" data-modal-close>✕</button></header><div class="v2-modal-body">${html}</div></div>`;
  m.hidden = false;
}
function closeModal() { const m = $("#v2-modal"); if (m && !m.hidden) { m.hidden = true; if (AKTIV === "dash") renderDash(); } }   // To-dos neu laden

/* Fehler-Verlauf-Chart (LUNA vs. Baseline): breiten-bewusst gerendert -> KEINE Streckung.
   viewBox-Breite = Container-Pixelbreite -> 1:1-Abbildung (Achsen/Text unverzerrt). ResizeObserver wie V1. */
function chartMount() {
  return `<div class="v2-trend"></div><div class="v2-legend"><span><i style="background:var(--v2-accent)"></i>LUNA</span><span><i style="background:var(--v2-faint)"></i>Baseline</span></div>`;
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
  svg.addEventListener("mousemove", ev => { const r = svg.getBoundingClientRect(); let i = Math.round(((ev.clientX - r.left) / r.width * W - padL) / ((W - padL - padR) / Math.max(1, v.length - 1))); i = Math.max(0, Math.min(v.length - 1, i)); const p = v[i]; tip.innerHTML = `<b>${esc((p.woche || "").replace("2026-", ""))}</b> · LUNA ${(p.mae_pct || 0).toFixed(1)}% · Baseline ${(p.baseline_mae_pct || 0).toFixed(1)}%`; tip.style.display = "block"; tip.style.left = Math.max(0, Math.min(r.width - 200, ev.clientX - r.left - 60)) + "px"; });
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
  let TODOS;
  [STATE, OVERVIEW, LOOP, TODOS] = await Promise.all([jget("/api/state"), jget("/api/overview"), jget("/api/investment/loop"), jget("/api/todos")]);
  TODOS = TODOS || { todos: [], anzahl: 0, dringend: 0 };
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
    todos: { span: "w12", link: null, aria: `Zu erledigen: ${TODOS.anzahl}`, html: todosInner(TODOS) },
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
/* To-dos des Tagesbetriebs (Belege, Rechnungen, Angebote, Aufträge, CRM, Reels) -- zusammengefasst je Bereich.
   Erledigt wird durch die eigentliche Arbeit („Öffnen“) oder direkt („✓ …“); LUNA löscht dazugehörige Kalendertermine. */
function todosInner(d) {
  const liste = d.todos || [];
  if (!liste.length) return `<div class="v2-check done" style="border:none"><span class="mark">✓</span>Alles erledigt — nichts offen im Tagesbetrieb.</div>`;
  const gruppen = {}; liste.forEach(t => (gruppen[t.bereich] = gruppen[t.bereich] || []).push(t));
  const zeile = (t) => `<div class="v2-list-row"><span>${t.icon}</span><div class="grow"><b>${esc(t.titel)}</b><small>${esc(t.detail || "")}</small></div>
    ${t.faellig ? `<span class="v2-badge ${t.dringend ? "err" : "neutral"}">${t.dringend ? (t.faellig < heuteIso() ? "überfällig" : "heute") : esc(datumDe(t.faellig))}</span>` : ""}
    ${t.erledigen ? `<button class="v2-btn ok sm" data-act="todo-erledigen" data-val="${esc(t.erledigen.pfad)}">${esc(t.erledigen.label)}</button>` : ""}
    <button class="v2-btn sm" data-act="todo-oeffnen" data-val="${esc(t.act)}" data-id="${esc(t.act_id || "")}">Öffnen ›</button></div>`;
  const bloecke = Object.entries(gruppen).map(([b, ts]) => {
    const dr = ts.filter(t => t.dringend).length;
    return `<details class="v2-todo-gruppe" ${dr || Object.keys(gruppen).length === 1 ? "open" : ""}><summary><b>${esc(ts[0].icon)} ${esc(b)}</b> <span class="v2-badge ${dr ? "err" : "neutral"}">${ts.length}${dr ? ` · ${dr} fällig` : ""}</span></summary>${ts.map(zeile).join("")}</details>`;
  }).join("");
  return `<div class="v2-kpi">${d.anzahl} <span class="delta ${d.dringend ? "down" : "up"}">${d.dringend ? d.dringend + " heute fällig/überfällig" : "nichts dringend"}</span></div>
    <div class="v2-sub">Tagesbetrieb — Freigaben für die Weiterentwicklung stehen separat.</div><div class="v2-todo-liste">${bloecke}</div>`;
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

/* =========================== Kunden (Stammdaten, KUNDEN_FINANZEN Etappe 2) =========================== */
// Firmen mit Firmenkundennummer K-…, Ansprechpartner mit AP-…; jede Änderung landet als Eintrag im Verlauf.
const KUNDE_TYP = { kunde: "Kunde", lieferant: "Lieferant", partner: "Partner" };
const FIRMA_FORM = [["name", "Firmenname *"], ["typ", "Typ", "typ"], ["strasse", "Straße und Hausnummer"], ["plz", "PLZ"], ["ort", "Ort"], ["land", "Land"],
  ["rechnungsmail", "Rechnungs-Mail", "email"], ["telefon", "Telefon"], ["website", "Website"], ["ustid", "USt-IdNr."], ["steuernummer", "Steuernummer"],
  ["zahlungsziel_tage", "Zahlungsziel (Tage)", "number"], ["notiz", "Notiz", "textarea"]];
const AP_FORM = [["vorname", "Vorname"], ["nachname", "Nachname"], ["rolle", "Rolle / Position"], ["mail", "Mail", "email"], ["telefon", "Telefon"], ["notiz", "Notiz", "textarea"]];
const FELD_LBL = Object.fromEntries([...FIRMA_FORM, ...AP_FORM].map(([k, l]) => [k, l.replace(" *", "")]).concat([["aktiv", "Aktiv"], ["collab", "Collab zugeordnet"], ["collab_entfernt", "Collab gelöst"], ["firma", "Firma"]]));
let KUNDEN = { firmen: [], collab_ohne_nummer: [] }, KUNDEN_SUCHE = "", _kundenTimer = null;

function formFelder(prefix, spec, werte = {}) {
  return spec.map(([k, lbl, art]) => {
    const v = werte[k] == null ? "" : String(werte[k]);
    let inp;
    if (art === "typ") inp = `<select id="${prefix}-${k}">${Object.entries(KUNDE_TYP).map(([id, l]) => `<option value="${id}" ${(v || "kunde") === id ? "selected" : ""}>${l}</option>`).join("")}</select>`;
    else if (art === "textarea") inp = `<textarea id="${prefix}-${k}" rows="3" class="v2-inp">${esc(v)}</textarea>`;
    else inp = `<input id="${prefix}-${k}" type="${art || "text"}" value="${esc(v)}" ${art === "number" ? 'min="0" max="365"' : ""}>`;
    return `<label class="v2-feld"><small>${esc(lbl)}</small>${inp}</label>`;
  }).join("");
}
function formWerte(prefix, spec) { const o = {}; spec.forEach(([k]) => { const e = $(`#${prefix}-${k}`); if (e) o[k] = e.value.trim(); }); return o; }
function kundenMsg(id, text, ok) { const m = $("#" + id); if (m) { m.textContent = text; m.className = "v2-msg " + (ok ? "ok" : "err"); } }

RENDER.kunden = renderKunden;
async function renderKunden() {
  const sub = SUBTAB.kunden || "firmen";
  KUNDEN = await jget("/api/crm/kunden" + (KUNDEN_SUCHE ? "?suche=" + encodeURIComponent(KUNDEN_SUCHE) : "")) || { firmen: [], collab_ohne_nummer: [] };
  const f = KUNDEN.firmen || [], c = KUNDEN.collab_ohne_nummer || [];
  let body;
  if (sub === "collab") {
    body = tile("Collab-Firmen ohne Kundennummer", c.map(x => `<div class="v2-list-row"><span class="v2-badge neutral">${esc(x.status || "")}</span><div class="grow"><b>${esc(x.firma)}</b><small>${esc(kanal[x.quelle] || x.quelle || "")} · ${x.nachrichten || 0} Nachr.${x.letzter_kontakt ? " · " + esc(zeitKurz(x.letzter_kontakt)) : ""}</small></div>
      <button class="v2-btn" data-act="kunde-neu" data-id="${esc(x.firma)}">+ Als Firma anlegen</button><button class="v2-btn" data-act="kunde-collab-zu" data-id="${esc(x.firma)}">Zuordnen…</button></div>`).join("") || emptyRow("Alle Collab-Firmen haben eine Kundennummer."), "w12");
  } else {
    const rows = f.map(x => `<tr class="klick" data-act="kunde-detail" data-id="${esc(x.nummer)}"><td><b>${esc(x.nummer)}</b></td><td>${esc(x.name)}${x.aktiv ? "" : ` <span class="v2-badge neutral">inaktiv</span>`}</td><td>${esc(KUNDE_TYP[x.typ] || x.typ || "")}</td><td>${esc([x.plz, x.ort].filter(Boolean).join(" "))}</td><td>${x.ansprechpartner || 0}</td><td>${(x.collab || []).length ? "🤝" : ""}</td></tr>`).join("");
    body = `${kpiTile("Firmen", String(f.filter(x => x.aktiv).length), null, "aktiv")}${kpiTile("Collab ohne Nummer", String(c.length), null, "noch zuzuordnen")}
      ${tile(KUNDEN_SUCHE ? `Treffer für „${KUNDEN_SUCHE}"` : "Firmen", rows ? `<table class="v2-table"><thead><tr><th>Nr.</th><th>Firma</th><th>Typ</th><th>Ort</th><th>Ansprechp.</th><th></th></tr></thead><tbody>${rows}</tbody></table>` : emptyRow(KUNDEN_SUCHE ? "Keine Treffer." : "Noch keine Firma angelegt — oben rechts „+ Neue Firma“."), "w12")}`;
  }
  const actions = `<input id="kunden-suche" class="v2-inp" placeholder="Suchen (Name, Nr., Ort, Ansprechpartner)…" value="${esc(KUNDEN_SUCHE)}" style="width:260px"><button class="v2-btn pri" data-act="kunde-neu">+ Neue Firma</button>`;
  $("#v2-app").innerHTML = secHead("Kunden", actions) + tabs("kunden", [["firmen", "Firmen"], ["collab", `Collab ohne Nummer (${c.length})`]]) + `<div class="v2-grid">${body}</div>`;
  const s = $("#kunden-suche");
  if (s) {
    s.addEventListener("input", () => { clearTimeout(_kundenTimer); _kundenTimer = setTimeout(() => { KUNDEN_SUCHE = s.value.trim(); renderKunden().then(() => { const n = $("#kunden-suche"); if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }); }, 300); });
  }
}
function kundeNeu(collab) {
  openModal("Neue Firma", `<div class="v2-form">${collab ? `<div class="v2-sub">Wird mit der Collab-Firma <b>${esc(collab)}</b> verknüpft.</div>` : ""}${formFelder("kf", FIRMA_FORM, collab ? { name: collab, typ: "partner" } : {})}
    <button class="v2-btn pri" data-act="kunde-anlegen" data-id="${esc(collab || "")}">Anlegen (Nummer wird vergeben)</button><div id="kf-msg" class="v2-msg"></div></div>`);
}
async function kundeAnlegen(collab, trotz) {
  const firma = formWerte("kf", FIRMA_FORM);
  const r = await jpost("/api/crm/kunden", { firma, collab: collab || "", trotz_dublette: !!trotz });
  if (!r) return kundenMsg("kf-msg", "Keine Verbindung zum Server.", false);
  if (!r.ok && r.dublette && confirm(r.hinweis + "\n\nTrotzdem als eigene Firma anlegen?")) return kundeAnlegen(collab, true);
  if (!r.ok) return kundenMsg("kf-msg", r.hinweis || "Fehler.", false);
  await renderKunden(); return kundeDetail(r.nummer, `${r.nummer} angelegt.`);
}
async function kundeDetail(nr, meldung) {
  openModal(nr, `<div class="v2-empty">Lade…</div>`);
  const d = await jget("/api/crm/kunden/" + encodeURIComponent(nr));
  const f = d && d.firma; if (!f) return openModal(nr, emptyRow("Firma nicht gefunden."));
  const aps = (f.ansprechpartner_liste || []).map(a => `<div class="v2-list-row"><span class="v2-badge ${a.aktiv ? "aktiv" : "neutral"}">${esc(a.nummer)}</span><div class="grow"><b>${esc([a.vorname, a.nachname].filter(Boolean).join(" "))}</b><small>${esc([a.rolle, a.mail, a.telefon].filter(Boolean).join(" · "))}</small></div><button class="v2-btn" data-act="kunde-ap-edit" data-id="${esc(a.nummer)}" data-val="${esc(f.nummer)}">Bearbeiten</button></div>`).join("") || emptyRow("Noch kein Ansprechpartner.");
  const collab = (f.collab || []).map(c => `<div class="v2-list-row"><span>🤝</span><div class="grow"><b>${esc(c)}</b></div><button class="v2-btn" data-act="kunde-collab-los" data-id="${esc(f.nummer)}" data-val="${esc(c)}">Lösen</button></div>`).join("") || emptyRow("Keine Collab-Firma verknüpft.");
  const verlauf = (f.verlauf || []).slice().reverse().map(v => `<div class="v2-list-row"><div class="grow"><b>${esc({ firma_angelegt: "Angelegt", firma_geaendert: "Geändert", collab_zugeordnet: "Collab verknüpft", collab_geloest: "Collab gelöst" }[v.typ] || v.typ)}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")} · ${esc(Object.entries(v.felder || {}).filter(([k, w]) => w !== "" && w != null).map(([k, w]) => `${FELD_LBL[k] || k}: ${typeof w === "boolean" ? (w ? "ja" : "nein") : w}`).join(" · "))}</small></div></div>`).join("");
  openModal(`${f.nummer} · ${f.name}`, `${meldung ? `<div class="v2-msg ok">${esc(meldung)}</div>` : ""}
    <h3>Stammdaten</h3><div class="v2-form">${formFelder("ke", FIRMA_FORM, f)}
    <label class="v2-modlbl"><input type="checkbox" id="ke-aktiv" ${f.aktiv ? "checked" : ""}> Aktiv (inaktive Firmen bleiben erhalten, nur ausgeblendet)</label>
    <button class="v2-btn pri" data-act="kunde-speichern" data-id="${esc(f.nummer)}">Änderungen speichern</button><div id="ke-msg" class="v2-msg"></div></div>
    <h3>Ansprechpartner</h3>${aps}<button class="v2-btn" data-act="kunde-ap-neu" data-id="${esc(f.nummer)}" style="margin-top:8px">+ Ansprechpartner</button><div id="kap-box"></div>
    <h3>Angebote</h3><button class="v2-btn" data-act="an-neu" data-id="${esc(f.nummer)}">+ Angebot für ${esc(f.name)}</button>
    <h3>Collab-CRM</h3>${collab}
    <h3>Verlauf</h3>${verlauf}`);
}
async function kundeSpeichern(nr) {
  const firma = { ...formWerte("ke", FIRMA_FORM), aktiv: !!($("#ke-aktiv") || {}).checked };
  const r = await jpost("/api/crm/kunden/" + encodeURIComponent(nr), { firma });
  if (!r || !r.ok) return kundenMsg("ke-msg", (r && r.hinweis) || "Fehler.", false);
  const n = Object.keys(r.geaendert || {}).length;
  renderKunden(); return kundeDetail(nr, n ? `${n} Feld(er) geändert.` : "Keine Änderung.");
}
function kundeApForm(firmaNr, ap) {
  const box = $("#kap-box"); if (!box) return;
  box.innerHTML = `<div class="v2-form" style="margin-top:10px"><b>${ap ? esc(ap.nummer) + " bearbeiten" : "Neuer Ansprechpartner"}</b>${formFelder("kap", AP_FORM, ap || {})}
    ${ap ? `<label class="v2-modlbl"><input type="checkbox" id="kap-aktiv" ${ap.aktiv ? "checked" : ""}> Aktiv</label>` : ""}
    <button class="v2-btn pri" data-act="kunde-ap-speichern" data-id="${esc(ap ? ap.nummer : "")}" data-val="${esc(firmaNr)}">${ap ? "Speichern" : "Anlegen (Nummer wird vergeben)"}</button><div id="kap-msg" class="v2-msg"></div></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
async function kundeApSpeichern(apNr, firmaNr) {
  const ansprechpartner = formWerte("kap", AP_FORM);
  if (apNr) ansprechpartner.aktiv = !!($("#kap-aktiv") || {}).checked;
  const r = apNr ? await jpost("/api/crm/ansprechpartner/" + encodeURIComponent(apNr), { ansprechpartner })
    : await jpost(`/api/crm/kunden/${encodeURIComponent(firmaNr)}/ansprechpartner`, { ansprechpartner });
  if (!r || !r.ok) return kundenMsg("kap-msg", (r && r.hinweis) || "Fehler.", false);
  renderKunden(); return kundeDetail(firmaNr, apNr ? "Ansprechpartner gespeichert." : `${r.nummer} angelegt.`);
}
async function kundeCollabZu(collab) {
  const f = (KUNDEN.firmen || []).filter(x => x.aktiv);
  if (!f.length) return alert("Noch keine Firma angelegt — nutze „+ Als Firma anlegen“.");
  openModal("Collab zuordnen", `<div class="v2-form"><div class="v2-sub">Collab-Firma <b>${esc(collab)}</b> einer bestehenden Firmenkundennummer zuordnen:</div>
    <select id="kcz-nr">${f.map(x => `<option value="${esc(x.nummer)}">${esc(x.nummer)} · ${esc(x.name)}</option>`).join("")}</select>
    <button class="v2-btn pri" data-act="kunde-collab-ok" data-id="${esc(collab)}">Zuordnen</button><div id="kcz-msg" class="v2-msg"></div></div>`);
}

/* =========================== Angebote (KUNDEN_FINANZEN Etappe 3 + 3b) =========================== */
// Angebot AN-JJJJ-NNNN zu Firma + Ansprechpartner; Positionen aus dem Leistungskatalog, Zuschläge + Paketrabatt,
// PDF im Hanserautisch-Look, Gmail-Entwurf mit Anhang (Senden = CEO), Kalender-Erinnerungen; Katalog + Preisliste.
const AN_STATUS = { entwurf: ["Entwurf", "neutral"], versendet: ["Versendet", "wartet"], angenommen: ["Angenommen", "ok"], abgelehnt: ["Abgelehnt", "err"], abgelaufen: ["Abgelaufen", "err"] };
const anBadge = (st) => { const [l, c] = AN_STATUS[st] || [st, "neutral"]; return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
const cent2eur = (c) => (Number(c || 0) / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" });
const cent2feld = (c) => (Number(c || 0) / 100).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const heuteIso = (plus = 0) => { const d = new Date(); d.setDate(d.getDate() + plus); return d.toLocaleDateString("sv-SE"); };
const zahl = (t) => { t = String(t || "").replace(/[€\s]/g, ""); if (t.includes(",")) t = t.replace(/\./g, "").replace(",", "."); else if (/^-?\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, ""); const n = Number(t); return isFinite(n) ? n : NaN; };
const pz = (p) => String(p).replace(".", ",");
let AN_FIRMEN = [], KATALOG = null, KAT_DARF = false;
async function katalogLaden(neu) { if (!KATALOG || neu) { const d = await jget("/api/crm/katalog"); KATALOG = d && d.katalog; KAT_DARF = !!(d && d.darf_aendern); } return KATALOG; }
const katItem = (id) => { for (const g of (KATALOG && KATALOG.gruppen) || []) for (const it of g.items) if (it.id === id) return [it, g]; return [null, null]; };

RENDER.angebote = renderAngebote;
async function renderAngebote() {
  const sub = SUBTAB.angebote || "offen";
  if (sub === "katalog") return renderKatalog();
  if (sub === "auftraege") return renderAuftraege();
  if (sub === "preisliste") return renderPreisliste();
  const d = await jget("/api/crm/angebote") || {};
  const alle = d.angebote || [];
  const offen = alle.filter(a => ["entwurf", "versendet"].includes(a.anzeige_status));
  const liste = sub === "offen" ? offen : alle;
  const jahr = String(new Date().getFullYear());
  const summe = (l) => l.reduce((s, a) => s + (a.summe_cent || 0), 0);
  const angen = alle.filter(a => a.status === "angenommen" && a.datum.startsWith(jahr));
  const rows = liste.map(a => `<tr class="klick" data-act="an-detail" data-id="${esc(a.nummer)}"><td><b>${esc(a.nummer)}</b></td><td>${esc(a.firma_name || a.firma)}</td><td>${esc(a.titel || "")}</td><td>${esc(new Date(a.datum).toLocaleDateString("de-DE"))}</td><td style="text-align:right">${cent2eur(a.summe_cent)}</td><td>${anBadge(a.anzeige_status)}</td></tr>`).join("");
  const body = `${kpiTile("Offene Angebote", String(offen.length), null, cent2eur(summe(offen)))}${kpiTile("Versendet", String(alle.filter(a => a.anzeige_status === "versendet").length), null, "warten auf Antwort")}
    ${kpiTile("Angenommen " + jahr, String(angen.length), null, cent2eur(summe(angen)))}
    ${tile(sub === "offen" ? "Offene Angebote" : "Alle Angebote", rows ? `<table class="v2-table"><thead><tr><th>Nr.</th><th>Firma</th><th>Titel</th><th>Datum</th><th style="text-align:right">Summe</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>` : emptyRow(sub === "offen" ? "Keine offenen Angebote — oben rechts „+ Neues Angebot“." : "Noch kein Angebot."), "w12")}`;
  $("#v2-app").innerHTML = anKopf() + `<div class="v2-grid">${body}</div>`;
}
const anKopf = () => secHead("Angebote & Aufträge", `<button class="v2-btn pri" data-act="an-neu">+ Neues Angebot</button>`) + tabs("angebote", [["offen", "Offen"], ["alle", "Alle"], ["auftraege", "Aufträge"], ["katalog", "Katalog"], ["preisliste", "Preisliste"]]);

/* ---------- Editor ---------- */
function anPosZeile(p = {}) {
  return `<div class="v2-an-pos" data-katalog="${esc(p.katalog_id || "")}" data-gruppe="${esc(p.gruppe || "")}" data-farbe="${esc(p.gruppe_farbe || "")}">
    <div class="v2-an-text"><input class="v2-inp an-p-beschreibung" value="${esc(p.beschreibung || "")}" placeholder="Leistung">
      <input class="v2-inp an-p-detail" value="${esc(p.detail || "")}" placeholder="Detail (Reichweite, Hinweis) – optional"></div>
    <input class="v2-inp an-p-menge" value="${esc(p.menge != null ? String(p.menge).replace(".", ",") : "1")}" placeholder="Menge" inputmode="decimal" aria-label="Menge">
    <input class="v2-inp an-p-einheit" value="${esc(p.einheit || "")}" placeholder="Einheit" aria-label="Einheit">
    <input class="v2-inp an-p-preis" value="${p.einzelpreis_cent != null ? cent2feld(p.einzelpreis_cent) : ""}" placeholder="Einzelpreis €" inputmode="decimal" aria-label="Einzelpreis">
    <span class="an-p-gesamt">–</span>
    <button class="v2-btn v2-an-weg" data-act="an-pos-weg" title="Position löschen" aria-label="Position löschen">🗑</button></div>`;
}
/* Firmen-Suche mit Vorschlägen (statt Dropdown) */
function firmaSucheVerdrahten() {   // genutzt von Angebots- und Rechnungs-Editor
  const such = $("#an-firma-suche"); if (!such) return;
  such.addEventListener("input", () => { $("#an-firma").value = ""; $("#an-ap").innerHTML = `<option value="">— erst Firma wählen —</option>`; firmaListe(); });
  such.addEventListener("focus", () => { if (!$("#an-firma").value) firmaListe(); });
  such.addEventListener("keydown", (e) => {
    const box = $("#an-firma-treffer"); const z = [...box.querySelectorAll(".v2-auto-z")]; const i = z.findIndex(x => x.classList.contains("aktiv"));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); if (box.hidden) return firmaListe(); if (!z.length) return; z[i]?.classList.remove("aktiv"); z[(i + (e.key === "ArrowDown" ? 1 : -1) + z.length) % z.length].classList.add("aktiv"); }
    else if (e.key === "Enter") { e.preventDefault(); const t = z[Math.max(i, 0)]; if (t) firmaWaehlen(t.dataset.id); }
    else if (e.key === "Escape") { e.stopPropagation(); box.hidden = true; }
  });
}
function firmaTreffer(q) {
  q = (q || "").trim().toLowerCase();
  return AN_FIRMEN.filter(f => !q || [f.nummer, f.name, f.ort, f.plz].filter(Boolean).join(" ").toLowerCase().includes(q)).slice(0, 8);
}
function firmaListe() {
  const box = $("#an-firma-treffer"); if (!box) return;
  const t = firmaTreffer($("#an-firma-suche").value);
  box.innerHTML = t.length ? t.map((f, i) => `<button type="button" class="v2-auto-z${i === 0 ? " aktiv" : ""}" data-act="an-firma-wahl" data-id="${esc(f.nummer)}"><b>${esc(f.name)}</b><small>${esc(f.nummer)}${f.ort ? " · " + esc(f.ort) : ""}</small></button>`).join("")
    : `<div class="v2-auto-leer">Keine Firma gefunden — unter „🏢 Kunden“ anlegen.</div>`;
  box.hidden = false;
}
async function firmaWaehlen(nr) {
  const f = AN_FIRMEN.find(x => x.nummer === nr); if (!f) return;
  $("#an-firma").value = f.nummer; $("#an-firma-suche").value = `${f.name} (${f.nummer})`;
  const box = $("#an-firma-treffer"); if (box) box.hidden = true;
  await anApListe("");
}
async function anEditor(nummer, firmaVorwahl) {
  openModal(nummer ? `${nummer} bearbeiten` : "Neues Angebot", `<div class="v2-empty">Lade…</div>`, true);
  const [k, d] = await Promise.all([jget("/api/crm/kunden"), nummer ? jget("/api/crm/angebote/" + encodeURIComponent(nummer)) : Promise.resolve(null), katalogLaden()]);
  AN_FIRMEN = ((k && k.firmen) || []).filter(f => f.aktiv);
  if (!AN_FIRMEN.length) return openModal("Neues Angebot", emptyRow("Zuerst unter „🏢 Kunden“ eine Firma anlegen."), true);
  const a = (d && d.angebot) || { firma: firmaVorwahl || AN_FIRMEN[0].nummer, datum: heuteIso(), gueltig_bis: heuteIso(14), nachfassen_tage: 7, positionen: [], zuschlaege: [], rabatt_prozent: 0, layout: "hanserautisch" };
  const b = a.bloecke || {};
  const fa = AN_FIRMEN.find(f => f.nummer === a.firma);
  const katOpt = ((KATALOG && KATALOG.gruppen) || []).map(g => `<optgroup label="${esc(g.name)}">${g.items.filter(it => it.aktiv).map(it => `<option value="${esc(it.id)}">${esc(it.name)} — ${cent2eur(it.preis_cent)}${it.einheit ? " / " + esc(it.einheit) : ""}</option>`).join("")}</optgroup>`).join("");
  const gewaehlt = new Set((a.zuschlaege || []).map(z => z.id));
  const zuListe = [...((KATALOG && KATALOG.zuschlaege) || []), ...(a.zuschlaege || []).filter(z => !((KATALOG && KATALOG.zuschlaege) || []).some(k => k.id === z.id))];
  const zuHtml = zuListe.map(z => { const alt = (a.zuschlaege || []).find(x => x.id === z.id); const pr = alt ? alt.prozent : z.prozent;
    return `<label class="v2-modlbl"><input type="checkbox" class="an-zu" value="${esc(z.id)}" data-name="${esc(z.name)}" data-prozent="${esc(String(pr))}" ${gewaehlt.has(z.id) ? "checked" : ""}> +${esc(pz(pr))} % ${esc(z.name)}</label>`; }).join("");
  const rmax = esc(String((KATALOG && KATALOG.rabatt_max) || 30));
  openModal(nummer ? `${nummer} bearbeiten` : "Neues Angebot", `<div class="v2-form v2-an-editor">
    <div class="v2-an-kopf">
      <div class="v2-form">
        <div class="v2-feld v2-auto-feld"><small>Firma * (Name, Kundennummer oder Ort tippen)</small>
          <input id="an-firma-suche" class="v2-inp" autocomplete="off" placeholder="Firma suchen …" value="${fa ? esc(`${fa.name} (${fa.nummer})`) : ""}">
          <input type="hidden" id="an-firma" value="${esc(fa ? fa.nummer : "")}"><div id="an-firma-treffer" class="v2-auto" hidden></div></div>
        <label class="v2-feld"><small>Ansprechpartner</small><select id="an-ap"></select></label>
        <label class="v2-feld"><small>Titel / Untertitel (leer = „${esc(b.untertitel || (KATALOG && KATALOG.texte.untertitel) || "")}“)</small><input id="an-titel" value="${esc(a.titel || "")}" placeholder="z. B. Kampagne Herbst"></label>
      </div>
      <div class="v2-form">
        <div class="v2-an-zeile"><label class="v2-feld"><small>Datum</small><input id="an-datum" type="date" value="${esc(a.datum)}"></label>
          <label class="v2-feld"><small>Gültig bis</small><input id="an-gueltig" type="date" value="${esc(a.gueltig_bis)}"></label>
          <label class="v2-feld"><small>Nachfassen nach (Tagen)</small><input id="an-nachfassen" type="number" min="1" max="90" value="${esc(String(a.nachfassen_tage || 7))}"></label></div>
        <div class="v2-an-zeile"><label class="v2-feld"><small>Layout</small><select id="an-layout"><option value="hanserautisch" ${a.layout !== "standard" ? "selected" : ""}>Hanserautisch</option><option value="standard" ${a.layout === "standard" ? "selected" : ""}>Schlicht (DIN)</option></select></label>
          <label class="v2-modlbl"><input type="checkbox" id="an-zeige-kalk" ${b.zeige_kalkulation !== false ? "checked" : ""}> „So kalkulieren wir“</label>
          <label class="v2-modlbl"><input type="checkbox" id="an-zeige-kz" ${b.zeige_kennzahlen !== false ? "checked" : ""}> Kennzahlen</label></div>
      </div>
    </div>
    <h3>Positionen <small class="v2-sub">Preise ohne Umsatzsteuer (Kleinunternehmer § 19 UStG)</small></h3>
    <div class="v2-an-kat"><select id="an-kat" class="v2-inp"><option value="">Aus Katalog wählen …</option>${katOpt}</select><button class="v2-btn" data-act="an-kat-neu">+ Aus Katalog</button><button class="v2-btn" data-act="an-pos-neu">+ Freie Position</button></div>
    <div class="v2-an-pos v2-an-pos-kopf"><span>Leistung / Detail</span><span>Menge</span><span>Einheit</span><span>Einzelpreis</span><span>Gesamt</span><span></span></div>
    <div id="an-pos">${(a.positionen || []).map(anPosZeile).join("")}</div>
    <div id="an-pos-leer" class="v2-empty">Noch keine Position — „Aus Katalog“ oder „Freie Position“.</div>
    <div class="v2-an-fuss">
      <div class="v2-form">
        ${zuHtml ? `<small class="v2-sub">Zuschläge (Prozent auf die Summe aller Formate)</small><div class="v2-mods" id="an-zu-box">${zuHtml}</div>` : ""}
        <label class="v2-feld"><small>Paketrabatt in % (0–${rmax}, nur gegen Laufzeit oder Volumen)</small><input id="an-rabatt" type="number" min="0" max="${rmax}" step="0.5" value="${esc(String(a.rabatt_prozent || 0))}"></label>
      </div>
      <div id="an-summe-box" class="v2-an-summen"></div>
    </div>
    <div class="v2-an-kopf">
      <label class="v2-feld"><small>Einleitung (leer = Standardtext)</small><textarea id="an-einleitung" rows="3" class="v2-inp">${esc(a.einleitung || "")}</textarea></label>
      <label class="v2-feld"><small>Schluss (nur schlichtes Layout; leer = Standardtext mit Gruß)</small><textarea id="an-schluss" rows="3" class="v2-inp">${esc(a.schluss || "")}</textarea></label>
    </div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="an-speichern" data-id="${esc(nummer || "")}">${nummer ? "Änderungen speichern" : "Anlegen (Nummer wird vergeben)"}</button><div id="an-msg" class="v2-msg"></div></div></div>`, true);
  await anApListe(a.ansprechpartner || "");
  firmaSucheVerdrahten();
  const box = $("#v2-modal .v2-form"); box.addEventListener("input", anSumme); box.addEventListener("change", anSumme); anSumme();
}
async function anApListe(vorwahl) {
  const nr = ($("#an-firma") || {}).value; const sel = $("#an-ap"); if (!sel) return;
  if (!nr) { sel.innerHTML = `<option value="">— erst Firma wählen —</option>`; return; }
  const d = await jget("/api/crm/kunden/" + encodeURIComponent(nr));
  const aps = ((d && d.firma && d.firma.ansprechpartner_liste) || []).filter(x => x.aktiv || x.nummer === vorwahl);
  sel.innerHTML = `<option value="">— keiner —</option>` + aps.map(x => `<option value="${esc(x.nummer)}" ${x.nummer === vorwahl ? "selected" : ""}>${esc(x.nummer)} · ${esc([x.vorname, x.nachname].filter(Boolean).join(" "))}${x.mail ? " · " + esc(x.mail) : ""}</option>`).join("");
}
function anKatNeu() {
  const id = ($("#an-kat") || {}).value; if (!id) return;
  const [it, g] = katItem(id); if (!it) return;
  $("#an-pos").insertAdjacentHTML("beforeend", anPosZeile({ beschreibung: it.name, detail: [it.basis, it.hinweis].filter(Boolean).join(" · "), menge: 1, einheit: it.einheit, einzelpreis_cent: it.preis_cent, katalog_id: it.id, gruppe: g.name, gruppe_farbe: g.farbe }));
  $("#an-kat").value = ""; anSumme();
}
function anPositionen() {
  return [...document.querySelectorAll("#an-pos .v2-an-pos")].map(z => ({ beschreibung: $(".an-p-beschreibung", z).value.trim(), detail: $(".an-p-detail", z).value.trim(), menge: $(".an-p-menge", z).value.trim(), einheit: $(".an-p-einheit", z).value.trim(), einzelpreis: $(".an-p-preis", z).value.trim(),
    katalog_id: z.dataset.katalog || "", gruppe: z.dataset.gruppe || "", gruppe_farbe: z.dataset.farbe || "" })).filter(p => p.beschreibung || p.einzelpreis);
}
const anZuschlaege = () => [...document.querySelectorAll(".an-zu:checked")].map(e => ({ id: e.value, name: e.dataset.name, prozent: Number(e.dataset.prozent) }));
function anSumme() {
  const box = $("#an-summe-box"); if (!box) return;
  document.querySelectorAll("#an-pos .v2-an-pos").forEach(z => { const c = Math.round(zahl($(".an-p-menge", z).value) * zahl($(".an-p-preis", z).value) * 100); $(".an-p-gesamt", z).textContent = isFinite(c) ? cent2eur(c) : "–"; });
  const leer = $("#an-pos-leer"); if (leer) leer.hidden = !!document.querySelector("#an-pos .v2-an-pos");
  const formate = anPositionen().reduce((acc, p) => acc + Math.round(zahl(p.menge) * zahl(p.einzelpreis) * 100), 0);
  if (!isFinite(formate)) { box.innerHTML = `<div class="v2-kv"><span>Summe</span><b>Eingabe prüfen</b></div>`; return; }
  const zu = anZuschlaege().map(z => [z.name, z.prozent, Math.round(formate * z.prozent / 100)]);
  const zwischen = formate + zu.reduce((s, z) => s + z[2], 0);
  const r = Number(($("#an-rabatt") || {}).value || 0), rb = Math.round(zwischen * r / 100);
  box.innerHTML = `<div class="v2-kv"><span>Summe Formate</span><b>${cent2eur(formate)}</b></div>` + zu.map(z => `<div class="v2-kv"><span>${esc(z[0])} (+${esc(pz(z[1]))} %)</span><b>${cent2eur(z[2])}</b></div>`).join("")
    + (r ? `<div class="v2-kv"><span>Paketrabatt (${esc(pz(r))} %)</span><b>−${cent2eur(rb)}</b></div>` : "") + `<div class="v2-kv"><span><b>Gesamtbetrag</b></span><b>${cent2eur(zwischen - rb)}</b></div>`;
}
async function anSpeichern(nummer) {
  if (!$("#an-firma").value) { $("#an-firma-suche").focus(); return kundenMsg("an-msg", "Bitte eine Firma aus den Vorschlägen auswählen.", false); }
  const angebot = { firma: $("#an-firma").value, ansprechpartner: $("#an-ap").value, titel: $("#an-titel").value.trim(), datum: $("#an-datum").value, gueltig_bis: $("#an-gueltig").value,
    nachfassen_tage: $("#an-nachfassen").value, einleitung: $("#an-einleitung").value.trim(), schluss: $("#an-schluss").value.trim(), positionen: anPositionen(),
    zuschlaege: anZuschlaege(), rabatt_prozent: ($("#an-rabatt") || {}).value || 0, layout: $("#an-layout").value,
    zeige_kalkulation: $("#an-zeige-kalk").checked, zeige_kennzahlen: $("#an-zeige-kz").checked };
  const r = nummer ? await jpost("/api/crm/angebote/" + encodeURIComponent(nummer), { angebot }) : await jpost("/api/crm/angebote", { angebot });
  if (!r || !r.ok) return kundenMsg("an-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  const nr = nummer || r.nummer; if (AKTIV === "angebote") renderAngebote();
  return anDetail(nr, nummer ? (r.geaendert && r.geaendert.length ? "Gespeichert." : "Keine Änderung.") : `${nr} angelegt.`);
}

/* ---------- Detail ---------- */
async function anDetail(nr, meldung, fehler) {
  openModal(nr, `<div class="v2-empty">Lade…</div>`, true);
  const d = await jget("/api/crm/angebote/" + encodeURIComponent(nr));
  const a = d && d.angebot; if (!a) return openModal(nr, emptyRow("Angebot nicht gefunden."), true);
  const ap = d.ansprechpartner, sm = a.summen || { formate_cent: a.summe_cent, zuschlaege: [], rabatt: null, gesamt_cent: a.summe_cent };
  const pos = a.positionen.map((p, i) => `<tr><td>${i + 1}</td><td><b>${esc(p.beschreibung)}</b>${p.detail ? `<br><small>${esc(p.detail)}</small>` : ""}</td><td style="text-align:right">${esc(String(p.menge).replace(".", ","))} ${esc(p.einheit || "")}</td><td style="text-align:right">${cent2eur(p.gesamt_cent)}</td></tr>`).join("");
  const fuss = (sm.zuschlaege.length || sm.rabatt ? `<tr><td></td><td>Summe Formate</td><td></td><td style="text-align:right">${cent2eur(sm.formate_cent)}</td></tr>` : "")
    + sm.zuschlaege.map(([n, p, c]) => `<tr><td></td><td>${esc(n)} (+${esc(pz(p))} %)</td><td></td><td style="text-align:right">${cent2eur(c)}</td></tr>`).join("")
    + (sm.rabatt ? `<tr><td></td><td>Paketrabatt (${esc(pz(sm.rabatt[0]))} %)</td><td></td><td style="text-align:right">−${cent2eur(sm.rabatt[1])}</td></tr>` : "")
    + `<tr><td></td><td><b>Gesamtbetrag</b></td><td></td><td style="text-align:right"><b>${cent2eur(sm.gesamt_cent)}</b></td></tr>`;
  const termine = (a.versendet_termine || []).map(t => `<div class="v2-list-row"><span>📅</span><div class="grow"><b>${esc(t.titel)}</b><small>${esc(new Date(t.datum).toLocaleDateString("de-DE"))}, 09:00</small></div></div>`).join("");
  const pdfs = (a.pdfs || []).map(p => `<div class="v2-list-row"><span>📎</span><div class="grow"><b>${esc(p.pfad.split("/").pop())}</b><small>${esc(zeit(p.ts))}${p.an ? " · Mail-Entwurf an " + esc(p.an) : ""}${p.inhalt === a.inhalt ? "" : " · älterer Stand"}</small></div></div>`).join("");
  let aktionen = `<a class="v2-btn" href="/api/crm/angebote/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📄 PDF ansehen</a>`;
  if (a.status === "entwurf") aktionen += `<button class="v2-btn" data-act="an-bearbeiten" data-id="${esc(nr)}">✎ Bearbeiten</button>
    <button class="v2-btn pri" data-act="an-senden" data-id="${esc(nr)}" ${d.google ? "" : "disabled title=\"Google nicht verbunden\""}>✉️ Senden …</button>
    <button class="v2-btn" data-act="an-versendet" data-id="${esc(nr)}" title="Nur wenn du das Angebot auf anderem Weg verschickt hast">✔ Anderweitig versendet</button>`;
  if (a.auftrag) aktionen += `<button class="v2-btn ok" data-act="ab-detail" data-id="${esc(a.auftrag)}">📋 Auftrag ${esc(a.auftrag)}</button>`;
  else if (a.status === "angenommen") aktionen += `<button class="v2-btn pri" data-act="ab-neu" data-id="${esc(nr)}">📋 Auftrag anlegen</button>`;
  else if (a.status === "versendet") aktionen += `<button class="v2-btn pri" data-act="ab-neu" data-id="${esc(nr)}" data-val="annehmen">📋 Angenommen + Auftrag anlegen</button>`;
  if (a.status === "versendet") aktionen += `<button class="v2-btn ok" data-act="an-status" data-id="${esc(nr)}" data-val="angenommen">Angenommen</button><button class="v2-btn" data-act="an-status" data-id="${esc(nr)}" data-val="abgelehnt">Abgelehnt</button>`
    + ((a.versendet_termine || []).length < 2 ? `<button class="v2-btn" data-act="an-erinnerungen" data-id="${esc(nr)}" title="Fehlende Kalender-Erinnerungen anlegen">📅 Erinnerungen nachholen</button>` : "");
  if ((a.pdfs || []).length) aktionen += `<a class="v2-btn" href="/api/crm/angebote/${encodeURIComponent(nr)}/pdf?archiv=1" target="_blank" rel="noopener">📎 Abgelegtes PDF</a>`;
  const verlaufLbl = { auftrag_angelegt: "Auftrag angelegt", angebot_angelegt: "Angelegt", angebot_geaendert: "Geändert", angebot_pdf_abgelegt: "PDF abgelegt", angebot_status: "Status", angebot_erinnerungen: "Erinnerungen nachgeholt", angebot_antwort: "Antwort vom Kunden" };
  const anzAntworten = (a.antworten || []).length;
  const verlauf = (a.verlauf || []).slice().reverse().map(v => {
    const kopf = `<b>${esc(verlaufLbl[v.typ] || v.typ)}${v.status ? ": " + esc((AN_STATUS[v.status] || [v.status])[0]) : ""}${v.auftrag ? " " + esc(v.auftrag) : ""}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")}${v.felder ? " · " + esc(v.felder.join(", ")) : ""}${v.an ? " · an " + esc(v.an) : ""}${v.grund ? " · " + esc(v.grund) : ""}</small>`;
    if (!v.mail_id) return `<div class="v2-list-row"><div class="grow">${kopf}</div></div>`;
    const titel = v.richtung === "ein" ? `💬 Antwort von ${esc(v.mail_von || "")}` : `✉️ Gesendet an ${esc(v.mail_an || "")}${v.betreff ? " · „" + esc(v.betreff) + "“" : ""}`;
    return `<details class="v2-mail" data-nr="${esc(nr)}" data-mid="${esc(v.mail_id)}"><summary><div class="grow"><b>${titel}</b><small>${esc(zeit(v.ts))}${v.vorschau ? " · " + esc(v.vorschau.slice(0, 90)) : ""}${v.status ? " · Status: " + esc((AN_STATUS[v.status] || [v.status])[0]) : ""}</small></div></summary><div class="v2-mail-inhalt">Lade Mail…</div></details>`;
  }).join("");
  openModal(`${nr} · ${d.firma.name || a.firma}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    <div class="v2-card-actions" style="flex-wrap:wrap;margin:8px 0 14px">${aktionen}</div>
    <div class="v2-an-detail"><div>
    <div class="v2-kv"><span>Status</span>${anBadge(a.anzeige_status)}</div>
    <div class="v2-kv"><span>Firma</span><b>${esc(a.firma)} · ${esc(d.firma.name || "")}</b></div>
    <div class="v2-kv"><span>Ansprechpartner</span><b>${ap ? esc(ap.nummer + " · " + [ap.vorname, ap.nachname].filter(Boolean).join(" ")) : "—"}</b></div>
    <div class="v2-kv"><span>Mail an</span><b>${esc(d.mail_an || "— keine Adresse —")}</b></div>
    <div class="v2-kv"><span>Datum / gültig bis</span><b>${esc(new Date(a.datum).toLocaleDateString("de-DE"))} / ${esc(new Date(a.gueltig_bis).toLocaleDateString("de-DE"))}</b></div>
    <div class="v2-kv"><span>Layout</span><b>${a.layout === "standard" ? "Schlicht (DIN)" : "Hanserautisch"}</b></div>
    ${a.titel ? `<div class="v2-kv"><span>Titel</span><b>${esc(a.titel)}</b></div>` : ""}
    ${d.firmendaten ? "" : `<div class="v2-msg err">Firmendaten fehlen auf der NAS — PDF nicht möglich.</div>`}
    ${anzAntworten ? `<div class="v2-kv"><span>Antworten vom Kunden</span><b>💬 ${anzAntworten} (im Verlauf)</b></div>` : ""}
    ${termine ? `<h3>Erinnerungen</h3>${termine}` : ""}${pdfs ? `<h3>Abgelegte PDFs</h3>${pdfs}` : ""}
    <h3>Verlauf <small class="v2-sub">Mails zum Aufklappen</small></h3>${verlauf}
    </div><div>
    <div id="an-senden-box"></div>
    <h3>Positionen</h3><table class="v2-table"><thead><tr><th>#</th><th>Leistung</th><th style="text-align:right">Menge</th><th style="text-align:right">Gesamt</th></tr></thead><tbody>${pos}</tbody><tfoot>${fuss}</tfoot></table>
    </div></div>`, true);
}

/* ---------- Auftraege (Beauftragung, KUNDEN_FINANZEN Etappe 4) ---------- */
const AB_STATUS = { beauftragt: ["Beauftragt", "wartet"], erledigt: ["Erledigt", "ok"], storniert: ["Storniert", "err"] };
const abBadge = (st) => { const [l, c] = AB_STATUS[st] || [st, "neutral"]; return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
const datumDe = (d) => d ? new Date(d).toLocaleDateString("de-DE") : "";
async function renderAuftraege() {
  const d = await jget("/api/crm/auftraege") || {};
  const l = d.auftraege || [];
  const offen = l.filter(a => a.status === "beauftragt");
  const rows = l.map(a => `<tr class="klick" data-act="ab-detail" data-id="${esc(a.nummer)}"><td><b>${esc(a.nummer)}</b></td><td>${esc(a.firma_name || a.firma)}</td><td>${esc(a.titel || "")}</td><td>${esc(a.angebot)}</td><td>${esc([datumDe(a.leistung_von), datumDe(a.leistung_bis)].filter(Boolean).join(" – "))}</td><td style="text-align:right">${cent2eur(a.summe_cent)}</td><td>${abBadge(a.status)}</td></tr>`).join("");
  const body = `${kpiTile("Offene Aufträge", String(offen.length), null, cent2eur(offen.reduce((x, a) => x + (a.summe_cent || 0), 0)))}${kpiTile("Erledigt", String(l.filter(a => a.status === "erledigt").length), null, "bereit für die Rechnung")}
    ${tile("Aufträge", rows ? `<table class="v2-table"><thead><tr><th>Nr.</th><th>Firma</th><th>Titel</th><th>Angebot</th><th>Leistung</th><th style="text-align:right">Summe</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>` : emptyRow("Noch kein Auftrag — entsteht aus einem angenommenen Angebot („📋 Auftrag anlegen“)."), "w12")}`;
  $("#v2-app").innerHTML = anKopf() + `<div class="v2-grid">${body}</div>`;
}
function abNeu(angebotNr, annehmen) {
  openModal(`Auftrag aus ${angebotNr}`, `<div class="v2-form" style="max-width:640px">
    ${annehmen ? `<div class="v2-msg">Das Angebot wird dabei als <b>angenommen</b> markiert.</div>` : ""}
    <div class="v2-an-zeile"><label class="v2-feld"><small>Leistung von</small><input id="ab-von" type="date"></label>
      <label class="v2-feld"><small>Leistung bis</small><input id="ab-bis" type="date"></label></div>
    <label class="v2-feld"><small>Notiz (erscheint auf der Auftragsbestätigung)</small><textarea id="ab-notiz" rows="3" class="v2-inp"></textarea></label>
    <button class="v2-btn pri" data-act="ab-anlegen" data-id="${esc(angebotNr)}" data-val="${annehmen ? "annehmen" : ""}">📋 Auftrag anlegen (Nummer wird vergeben)</button><div id="ab-msg" class="v2-msg"></div></div>`, true);
}
async function abAnlegen(angebotNr, annehmen) {
  const r = await jpost(`/api/crm/angebote/${encodeURIComponent(angebotNr)}/auftrag`, { annehmen: !!annehmen, leistung_von: $("#ab-von").value, leistung_bis: $("#ab-bis").value, notiz: $("#ab-notiz").value.trim() });
  if (!r || !r.ok) return kundenMsg("ab-msg", (r && r.hinweis) || "Fehler.", false);
  if (AKTIV === "angebote") renderAngebote();
  return abDetail(r.nummer, [`${r.nummer} angelegt.`, ...(r.hinweise || [])].join("\n"));
}
async function abDetail(nr, meldung, fehler) {
  openModal(nr, `<div class="v2-empty">Lade…</div>`, true);
  const d = await jget("/api/crm/auftraege/" + encodeURIComponent(nr));
  const a = d && d.auftrag; if (!a) return openModal(nr, emptyRow("Auftrag nicht gefunden."), true);
  const ap = d.ansprechpartner, sm = a.summen;
  const pos = a.positionen.map((p, i) => `<tr><td>${i + 1}</td><td><b>${esc(p.beschreibung)}</b>${p.detail ? `<br><small>${esc(p.detail)}</small>` : ""}</td><td style="text-align:right">${esc(String(p.menge).replace(".", ","))} ${esc(p.einheit || "")}</td><td style="text-align:right">${cent2eur(p.gesamt_cent)}</td></tr>`).join("");
  const fuss = (sm.zuschlaege.length || sm.rabatt ? `<tr><td></td><td>Summe Formate</td><td></td><td style="text-align:right">${cent2eur(sm.formate_cent)}</td></tr>` : "")
    + sm.zuschlaege.map(([n, p, c]) => `<tr><td></td><td>${esc(n)} (+${esc(pz(p))} %)</td><td></td><td style="text-align:right">${cent2eur(c)}</td></tr>`).join("")
    + (sm.rabatt ? `<tr><td></td><td>Paketrabatt (${esc(pz(sm.rabatt[0]))} %)</td><td></td><td style="text-align:right">−${cent2eur(sm.rabatt[1])}</td></tr>` : "")
    + `<tr><td></td><td><b>Gesamtbetrag</b></td><td></td><td style="text-align:right"><b>${cent2eur(sm.gesamt_cent)}</b></td></tr>`;
  let aktionen = `<a class="v2-btn" href="/api/crm/auftraege/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📄 Auftragsbestätigung (PDF)</a>
    <button class="v2-btn" data-act="an-detail" data-id="${esc(a.angebot)}">↩ Angebot ${esc(a.angebot)}</button>`;
  if (a.status !== "storniert") aktionen += `<button class="v2-btn pri" data-act="ab-senden" data-id="${esc(nr)}" ${d.google ? "" : "disabled"}>✉️ Senden …</button>`;
  if (a.status !== "storniert" && darf("rechnungen")) aktionen += `<button class="v2-btn pri" data-act="ab-rechnung" data-id="${esc(nr)}">🧾 Rechnung erstellen</button>`;
  if (a.status === "beauftragt") aktionen += `<button class="v2-btn ok" data-act="ab-status" data-id="${esc(nr)}" data-val="erledigt">✔ Erledigt</button><button class="v2-btn" data-act="ab-status" data-id="${esc(nr)}" data-val="storniert">Stornieren</button>`;
  if ((a.pdfs || []).length) aktionen += `<a class="v2-btn" href="/api/crm/auftraege/${encodeURIComponent(nr)}/pdf?archiv=1" target="_blank" rel="noopener">📎 Abgelegtes PDF</a>`;
  const lbl = { auftrag_angelegt: "Angelegt", auftrag_geaendert: "Geändert", auftrag_pdf_abgelegt: "PDF abgelegt", auftrag_status: "Status" };
  const verlauf = (a.verlauf || []).slice().reverse().map(v => `<div class="v2-list-row"><div class="grow"><b>${esc(lbl[v.typ] || v.typ)}${v.status ? ": " + esc(v.status === "gesendet" ? "Gesendet an " + (v.mail_an || "") : (AB_STATUS[v.status] || [v.status])[0]) : ""}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")}${v.felder ? " · " + esc(v.felder.join(", ")) : ""}${v.grund ? " · " + esc(v.grund) : ""}</small></div></div>`).join("");
  const bearbeitbar = a.status === "beauftragt";
  openModal(`${nr} · ${d.firma.name || a.firma}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    <div class="v2-card-actions" style="flex-wrap:wrap;margin:8px 0 14px">${aktionen}</div>
    <div class="v2-an-detail"><div>
    <div class="v2-kv"><span>Status</span>${abBadge(a.status)}</div>
    <div class="v2-kv"><span>Angebot</span><b>${esc(a.angebot)}</b></div>
    <div class="v2-kv"><span>Firma</span><b>${esc(a.firma)} · ${esc(d.firma.name || "")}</b></div>
    <div class="v2-kv"><span>Ansprechpartner</span><b>${ap ? esc(ap.nummer + " · " + [ap.vorname, ap.nachname].filter(Boolean).join(" ")) : "—"}</b></div>
    <div class="v2-kv"><span>Beauftragt am</span><b>${esc(datumDe(a.datum))}</b></div>
    ${a.gesendet_mail ? `<div class="v2-kv"><span>Bestätigung gesendet</span><b>✉️ ${esc(a.gesendet_mail.an)} · ${esc(zeit(a.gesendet_am))}</b></div>` : ""}
    <h3>Leistung</h3><div class="v2-form">
      <div class="v2-an-zeile"><label class="v2-feld"><small>von</small><input id="abe-von" type="date" value="${esc(a.leistung_von || "")}" ${bearbeitbar ? "" : "disabled"}></label>
        <label class="v2-feld"><small>bis</small><input id="abe-bis" type="date" value="${esc(a.leistung_bis || "")}" ${bearbeitbar ? "" : "disabled"}></label></div>
      <label class="v2-feld"><small>Notiz</small><textarea id="abe-notiz" rows="2" class="v2-inp" ${bearbeitbar ? "" : "disabled"}>${esc(a.notiz || "")}</textarea></label>
      ${bearbeitbar ? `<button class="v2-btn" data-act="ab-speichern" data-id="${esc(nr)}">Speichern</button><div id="abe-msg" class="v2-msg"></div>` : ""}</div>
    <h3>Verlauf</h3>${verlauf}
    </div><div>
    <div id="ab-senden-box"></div>
    <h3>Positionen <small class="v2-sub">aus ${esc(a.angebot)} übernommen</small></h3><table class="v2-table"><thead><tr><th>#</th><th>Leistung</th><th style="text-align:right">Menge</th><th style="text-align:right">Gesamt</th></tr></thead><tbody>${pos}</tbody><tfoot>${fuss}</tfoot></table>
    </div></div>`, true);
}
async function abSendenVorschau(nr) {
  const box = $("#ab-senden-box"); if (!box) return;
  const v = await jget(`/api/crm/auftraege/${encodeURIComponent(nr)}/versandvorschau`);
  if (!v) { box.innerHTML = emptyRow("Vorschau nicht verfügbar."); return; }
  box.innerHTML = `<h3>Auftragsbestätigung senden</h3><div class="v2-form">
    <div class="v2-kv"><span>Absender</span><b>${esc(v.absender)}</b></div>
    <label class="v2-feld"><small>An *</small><input id="abs-an" type="email" value="${esc(v.an || "")}"></label>
    <label class="v2-feld"><small>Betreff *</small><input id="abs-betreff" value="${esc(v.betreff)}"></label>
    <label class="v2-feld"><small>Text *</small><textarea id="abs-text" class="v2-inp" rows="9">${esc(v.text)}</textarea></label>
    <div class="v2-kv"><span>Anhang</span><a href="/api/crm/auftraege/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="ab-senden-jetzt" data-id="${esc(nr)}">✉️ Jetzt senden</button><button class="v2-btn" data-act="ab-senden-abbruch">Abbrechen</button></div>
    <div id="abs-msg" class="v2-msg"></div></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function abSendenJetzt(nr) {
  const an = $("#abs-an").value.trim();
  if (!an || !an.includes("@")) return kundenMsg("abs-msg", "Bitte eine gültige Empfänger-Adresse eintragen.", false);
  if (!confirm(`Auftragsbestätigung ${nr} jetzt an ${an} senden?`)) return;
  const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(nr)}/senden`, { an, betreff: $("#abs-betreff").value.trim(), text: $("#abs-text").value.trim(), bestaetigt: true });
  if (!r || !r.ok) return kundenMsg("abs-msg", (r && r.hinweis) || "Senden fehlgeschlagen.", false);
  return abDetail(nr, `Auftragsbestätigung an ${r.an} gesendet.`);
}

/* ---------- Mails im Verlauf: erst beim Aufklappen laden ---------- */
document.addEventListener("toggle", async (e) => {
  const d = e.target; if (!(d instanceof HTMLElement) || !d.matches("details.v2-mail") || !d.open || d.dataset.geladen) return;
  d.dataset.geladen = "1";
  const box = d.querySelector(".v2-mail-inhalt");
  const m = await jget(`/api/crm/angebote/${encodeURIComponent(d.dataset.nr)}/mail/${encodeURIComponent(d.dataset.mid)}`);
  if (!m) { box.textContent = "Mail nicht abrufbar."; delete d.dataset.geladen; return; }
  box.innerHTML = `<div class="v2-kv"><span>Von</span><b>${esc(m.von)}</b></div><div class="v2-kv"><span>An</span><b>${esc(m.an)}</b></div>
    <div class="v2-kv"><span>Datum</span><b>${esc(m.datum)}</b></div><div class="v2-kv"><span>Betreff</span><b>${esc(m.betreff)}</b></div>
    ${(m.anhaenge || []).length ? `<div class="v2-kv"><span>Anhänge</span><b>📎 ${m.anhaenge.map(esc).join(", ")}</b></div>` : ""}
    <pre class="v2-mail-text">${esc(m.text || "(kein Text)")}</pre><small class="v2-sub">${m.archiviert ? "Original archiviert (Aufbewahrung 6 Jahre)" : "Noch nicht archiviert — wird beim nächsten Abgleich abgelegt"}</small>`;
}, true);

/* ---------- Senden aus LUNAs Konto (CEO-Klick, mit Vorschau) ---------- */
async function anSendenVorschau(nr) {
  const box = $("#an-senden-box"); if (!box) return;
  box.innerHTML = `<div class="v2-empty">Lade Vorschau…</div>`;
  const v = await jget(`/api/crm/angebote/${encodeURIComponent(nr)}/versandvorschau`);
  if (!v) { box.innerHTML = emptyRow("Vorschau nicht verfügbar."); return; }
  box.innerHTML = `<h3>Angebot senden</h3><div class="v2-form v2-an-senden">
    <div class="v2-kv"><span>Absender</span><b>${esc(v.absender)}</b></div>
    <label class="v2-feld"><small>An *</small><input id="as-an" type="email" value="${esc(v.an || "")}" placeholder="kunde@firma.de"></label>
    <label class="v2-feld"><small>Betreff *</small><input id="as-betreff" value="${esc(v.betreff)}"></label>
    <label class="v2-feld"><small>Text * (Signatur anpassbar)</small><textarea id="as-text" class="v2-inp" rows="10">${esc(v.text)}</textarea></label>
    <div class="v2-kv"><span>Anhang</span><a href="/api/crm/angebote/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="an-senden-jetzt" data-id="${esc(nr)}">✉️ Jetzt senden</button><button class="v2-btn" data-act="an-senden-abbruch">Abbrechen</button></div>
    <div id="as-msg" class="v2-msg"></div>
    <small class="v2-sub">Geht aus LUNAs Google-Konto raus. Danach ist das Angebot „versendet“ (nicht mehr änderbar), die Erinnerungen werden angelegt, Antworten des Kunden erscheinen hier und kommen per Telegram.</small></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function anSendenJetzt(nr) {
  const an = $("#as-an").value.trim(), betreff = $("#as-betreff").value.trim(), text = $("#as-text").value.trim();
  if (!an || !an.includes("@")) return kundenMsg("as-msg", "Bitte eine gültige Empfänger-Adresse eintragen.", false);
  if (!confirm(`Angebot ${nr} jetzt an ${an} senden?\n\nDas lässt sich nicht zurückholen.`)) return;
  const b = $('[data-act="an-senden-jetzt"]'); if (b) { b.disabled = true; b.textContent = "⏳ sendet…"; }
  const r = await jpost(`/api/crm/angebote/${encodeURIComponent(nr)}/senden`, { an, betreff, text, bestaetigt: true });
  if (!r || !r.ok) { if (b) { b.disabled = false; b.textContent = "✉️ Jetzt senden"; } return kundenMsg("as-msg", (r && r.hinweis) || "Senden fehlgeschlagen.", false); }
  if (AKTIV === "angebote") renderAngebote();
  return anDetail(nr, [`Gesendet an ${r.an}.`, ...(r.termine || []).map(t => `📅 ${t.titel} (${new Date(t.datum).toLocaleDateString("de-DE")})`), ...(r.hinweise || [])].join("\n"));
}

/* ---------- Katalog (Preise pflegen, nur mit Modul Finanzen) ---------- */
async function renderKatalog(ausCache) {
  const k = ausCache ? KATALOG : await katalogLaden(true);
  if (!k) { $("#v2-app").innerHTML = anKopf() + emptyRow("Katalog nicht erreichbar."); return; }
  const ro = KAT_DARF ? "" : "disabled";
  const grp = k.gruppen.map((g, gi) => tile(g.name, `<div class="v2-kat-liste">${g.items.map(it => `<div class="v2-kat-zeile" data-gi="${gi}" data-id="${esc(it.id)}">
      <input class="v2-inp kat-name" value="${esc(it.name)}" ${ro}><input class="v2-inp kat-basis" value="${esc(it.basis)}" placeholder="Basis (Reichweite)" ${ro}>
      <input class="v2-inp kat-hinweis" value="${esc(it.hinweis)}" placeholder="Hinweis" ${ro}><input class="v2-inp kat-preis" value="${cent2feld(it.preis_cent)}" inputmode="decimal" ${ro}>
      <input class="v2-inp kat-einheit" value="${esc(it.einheit)}" placeholder="Einheit" ${ro}><label class="v2-modlbl"><input type="checkbox" class="kat-aktiv" ${it.aktiv ? "checked" : ""} ${ro}> aktiv</label></div>`).join("")}</div>
      ${KAT_DARF ? `<button class="v2-btn" data-act="kat-neu" data-id="${gi}">+ Format</button>` : ""}`, "w12")).join("");
  const zu = tile("Zuschläge", `${k.zuschlaege.map(z => `<div class="v2-kat-zu" data-id="${esc(z.id)}"><input class="v2-inp zu-name" value="${esc(z.name)}" ${ro}><input class="v2-inp zu-prozent" value="${esc(pz(z.prozent))}" inputmode="decimal" ${ro}><input class="v2-inp zu-info" value="${esc(z.info)}" placeholder="Erklärung" ${ro}></div>`).join("")}`, "w12");
  const t = k.texte, ta = (id, v, rows = 3) => `<textarea id="kt-${id}" rows="${rows}" class="v2-inp" ${ro}>${esc(v || "")}</textarea>`;
  const texte = tile("Textbausteine (Angebot + Preisliste)", `<div class="v2-form">
    <label class="v2-feld"><small>Untertitel</small><input id="kt-untertitel" value="${esc(t.untertitel)}" ${ro}></label>
    <label class="v2-feld"><small>Einleitung</small>${ta("intro", t.intro)}</label>
    <label class="v2-feld"><small>Überschrift Kalkulation</small><input id="kt-kalkulation_titel" value="${esc(t.kalkulation_titel)}" ${ro}></label>
    ${[0, 1, 2].map(i => `<label class="v2-feld"><small>Kalkulation, Absatz ${i + 1} (Text vor dem ersten Doppelpunkt wird fett)</small>${ta("kalk" + i, (t.kalkulation || [])[i])}</label>`).join("")}
    <label class="v2-feld"><small>Rechenbeispiel</small>${ta("kalkulation_beispiel", t.kalkulation_beispiel, 2)}</label>
    <small class="v2-sub">Kennzahlen (bis Etappe 3c von Hand; danach aus deinen Meta-Exporten)</small>
    <div class="v2-an-zeile">${[0, 1, 2, 3].map(i => `<div class="v2-feld"><input id="kt-kzw${i}" value="${esc(((t.kennzahlen || [])[i] || [])[0] || "")}" placeholder="Wert" ${ro}><input id="kt-kzl${i}" value="${esc(((t.kennzahlen || [])[i] || [])[1] || "")}" placeholder="Beschriftung" ${ro}></div>`).join("")}</div>
    <label class="v2-feld"><small>Datenbasis-Hinweis</small>${ta("kennzahlen_quelle", t.kennzahlen_quelle)}</label>
    <label class="v2-feld"><small>Einleitung „Zusätzliche Leistungen“ (Preisliste)</small>${ta("zuschlaege_info", t.zuschlaege_info, 2)}</label>
    <label class="v2-feld"><small>Fußtext</small>${ta("fuss", t.fuss)}</label>
    <label class="v2-feld"><small>Kontakt (Fußzeile)</small><input id="kt-kontakt" value="${esc(t.kontakt)}" ${ro}></label></div>`, "w12");
  const aktion = KAT_DARF ? `<span id="kat-msg" class="v2-msg"></span><button class="v2-btn pri" data-act="kat-speichern">Katalog speichern</button>` : `<span class="v2-sub">Nur ansehen — Preise ändert der Owner (Modul Finanzen).</span>`;
  $("#v2-app").innerHTML = anKopf() + `<div class="v2-card-actions" style="justify-content:flex-end;margin-bottom:10px">${aktion}</div><div class="v2-grid">${grp}${zu}${texte}</div>`;
}
function katalogAusForm() {
  const k = JSON.parse(JSON.stringify(KATALOG));
  k.gruppen.forEach(g => g.items = []);
  document.querySelectorAll(".v2-kat-zeile").forEach(z => {
    const g = k.gruppen[Number(z.dataset.gi)];
    g.items.push({ id: z.dataset.id, name: $(".kat-name", z).value.trim(), basis: $(".kat-basis", z).value.trim(), hinweis: $(".kat-hinweis", z).value.trim(),
      preis_cent: Math.round(zahl($(".kat-preis", z).value) * 100), einheit: $(".kat-einheit", z).value.trim(), aktiv: $(".kat-aktiv", z).checked });
  });
  k.zuschlaege = [...document.querySelectorAll(".v2-kat-zu")].map(z => ({ id: z.dataset.id, name: $(".zu-name", z).value.trim(), prozent: zahl($(".zu-prozent", z).value), info: $(".zu-info", z).value.trim() }));
  const v = (id) => ($("#kt-" + id) || {}).value || "";
  k.texte = { untertitel: v("untertitel"), intro: v("intro"), kalkulation_titel: v("kalkulation_titel"), kalkulation: [0, 1, 2].map(i => v("kalk" + i)).filter(x => x.trim()),
    kalkulation_beispiel: v("kalkulation_beispiel"), kennzahlen: [0, 1, 2, 3].map(i => [v("kzw" + i), v("kzl" + i)]).filter(x => x[0].trim()),
    kennzahlen_quelle: v("kennzahlen_quelle"), zuschlaege_info: v("zuschlaege_info"), fuss: v("fuss"), kontakt: v("kontakt") };
  return k;
}
async function katalogSpeichern() {
  const k = katalogAusForm();
  const bad = k.gruppen.flatMap(g => g.items).find(it => !isFinite(it.preis_cent) || it.preis_cent < 0);
  if (bad) return kundenMsg("kat-msg", `Preis bei „${bad.name}“ prüfen.`, false);
  const r = await jpost("/api/crm/katalog", { katalog: k });
  if (!r || !r.ok) return kundenMsg("kat-msg", (r && r.hinweis) || "Fehler.", false);
  const n = Object.keys(r.preise || {}).length;
  await renderKatalog(); kundenMsg("kat-msg", r.geaendert === false ? "Keine Änderung." : `Gespeichert${n ? ` · ${n} Preis(e) geändert` : ""}. Bestehende Angebote bleiben unverändert.`, true);
}
function katalogFormatNeu(gi) {
  const name = prompt("Name des neuen Formats:", ""); if (!name) return;
  KATALOG = katalogAusForm();
  const basisId = name.toLowerCase().replace(/[äÄ]/g, "ae").replace(/[öÖ]/g, "oe").replace(/[üÜ]/g, "ue").replace(/ß/g, "ss").replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 24) || "format";
  const ids = new Set(KATALOG.gruppen.flatMap(g => g.items.map(i => i.id))); let id = basisId, n = 2; while (ids.has(id)) id = `${basisId}_${n++}`;
  KATALOG.gruppen[gi].items.push({ id, name, basis: "", hinweis: "", preis_cent: 0, einheit: "", aktiv: true });
  const scroll = window.scrollY;
  renderKatalog(true).then(() => { window.scrollTo(0, scroll); kundenMsg("kat-msg", "Neues Format ergänzt — Preis eintragen und speichern.", true); });
}

/* ---------- Preisliste ---------- */
async function renderPreisliste() {
  const [k, kd] = await Promise.all([katalogLaden(true), jget("/api/crm/kunden")]);
  if (!k) { $("#v2-app").innerHTML = anKopf() + emptyRow("Katalog nicht erreichbar."); return; }
  const firmen = ((kd && kd.firmen) || []).filter(f => f.aktiv);
  const wahl = k.gruppen.map(g => `<div class="v2-feld"><small style="color:${g.farbe === "rot" ? "var(--v2-red)" : "var(--v2-accent)"}"><b>${esc(g.name)}</b></small>${g.items.filter(it => it.aktiv).map(it => `<label class="v2-modlbl"><input type="checkbox" class="pl-id" value="${esc(it.id)}" checked> ${esc(it.name)} — ${cent2eur(it.preis_cent)}${it.einheit ? " / " + esc(it.einheit) : ""}</label>`).join("")}</div>`).join("");
  const form = `<div class="v2-form"><label class="v2-feld"><small>Empfänger (optional)</small><select id="pl-firma"><option value="">— ohne Empfänger —</option>${firmen.map(f => `<option value="${esc(f.nummer)}">${esc(f.nummer)} · ${esc(f.name)}</option>`).join("")}</select></label>
    <label class="v2-feld"><small>Ansprechpartner</small><select id="pl-ap"><option value="">— keiner —</option></select></label>
    <button class="v2-btn pri" data-act="pl-pdf">📄 Preisliste als PDF</button>
    <small class="v2-sub">Ohne Nummer und ohne Buchhaltungseintrag. Zuschläge erscheinen als „Zusätzliche Leistungen“.</small></div>`;
  $("#v2-app").innerHTML = anKopf() + `<div class="v2-grid">${tile("Preisliste erstellen", form, "w5")}${tile("Formate", `<div class="v2-form">${wahl}</div>`, "w7")}</div>`;
  $("#pl-firma").addEventListener("change", async () => { const nr = $("#pl-firma").value; const sel = $("#pl-ap"); sel.innerHTML = `<option value="">— keiner —</option>`; if (!nr) return;
    const d = await jget("/api/crm/kunden/" + encodeURIComponent(nr)); sel.innerHTML += ((d && d.firma && d.firma.ansprechpartner_liste) || []).filter(x => x.aktiv).map(x => `<option value="${esc(x.nummer)}">${esc(x.nummer)} · ${esc([x.vorname, x.nachname].filter(Boolean).join(" "))}</option>`).join(""); });
}
function preislistePdf() {
  const ids = [...document.querySelectorAll(".pl-id:checked")].map(e => e.value);
  if (!ids.length) return alert("Mindestens ein Format auswählen.");
  const q = new URLSearchParams({ ids: ids.join(","), firma: ($("#pl-firma") || {}).value || "", ap: ($("#pl-ap") || {}).value || "" });
  window.open("/api/crm/katalog/preisliste.pdf?" + q.toString(), "_blank", "noopener");
}

/* =========================== Rechnungen (KUNDEN_FINANZEN Etappe 5, Modul Finanzen) =========================== */
// Entwurf (ohne Nummer, frei aenderbar) -> Festschreiben (RE-Nummer + PDF, unveraenderlich) -> Senden -> Bezahlt.
// Korrektur nur per Storno (eigene Nummer). Kleinunternehmer-Waechter blockiert > 100.000 EUR Jahresumsatz.
const RE_STATUS = { entwurf: ["Entwurf", "neutral"], offen: ["Offen", "wartet"], bezahlt: ["Bezahlt", "ok"], storniert: ["Storniert", "neutral"], storno: ["Stornorechnung", "neutral"] };
const reBadge = (r) => { const st = r.ueberfaellig ? "ueberfaellig" : r.status; const [l, c] = st === "ueberfaellig" ? ["Überfällig", "err"] : (RE_STATUS[st] || [st, "neutral"]); return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
RENDER.rechnungen = renderRechnungen;
async function renderRechnungen() {
  const sub = SUBTAB.rechnungen || "offen";
  const d = await jget("/api/finanzen/rechnungen") || { rechnungen: [], entwuerfe: [], waechter: {} };
  const alle = d.rechnungen || [], w = d.waechter || {};
  const offen = alle.filter(r => r.status === "offen");
  const ueber = offen.filter(r => r.ueberfaellig);
  const jahr = String(w.jahr || new Date().getFullYear());
  const bezahlt = alle.filter(r => r.status === "bezahlt" && String(r.rechnungsdatum).startsWith(jahr));
  const anteil = Math.min(100, Math.round((w.anteil || 0) * 100));
  const balken = `<div class="v2-re-balken"><i style="width:${anteil}%;background:${w.ueberschritten ? "var(--v2-red)" : w.warnung ? "#e8a200" : "var(--v2-accent)"}"></i></div><small class="v2-sub">${anteil} % der Kleinunternehmer-Grenze (100.000 €)${w.vorjahr_ueberschritten ? " · ⚠️ Vorjahr über 25.000 €!" : ""}</small>`;
  let liste = sub === "entwuerfe" ? null : (sub === "offen" ? offen : alle);
  const rows = liste ? liste.map(r => `<tr class="klick" data-act="re-detail" data-id="${esc(r.nummer)}"><td><b>${esc(r.nummer)}</b>${r.art === "storno" ? " <small>Storno zu " + esc(r.bezug) + "</small>" : ""}</td><td>${esc(r.firma_name || r.firma)}</td><td>${esc(r.titel || "")}</td><td>${esc(datumDe(r.rechnungsdatum))}</td><td>${esc(datumDe(r.faellig_am))}</td><td style="text-align:right">${cent2eur(r.summe_cent)}</td><td>${reBadge(r)}${r.versendet ? " ✉️" : ""}</td></tr>`).join("")
    : (d.entwuerfe || []).map(e => `<tr class="klick" data-act="re-detail" data-id="${esc(e.entwurf_id)}"><td><b>Entwurf</b> <small>${esc(e.entwurf_id)}</small></td><td>${esc(e.firma_name || e.firma)}</td><td>${esc(e.titel || "")}</td><td>${esc(e.auftrag || "")}</td><td></td><td style="text-align:right">${cent2eur(e.summe_cent)}</td><td>${reBadge({ status: "entwurf" })}</td></tr>`).join("");
  const kopf = sub === "entwuerfe" ? "<th>Entwurf</th><th>Firma</th><th>Titel</th><th>Auftrag</th><th></th><th style=\"text-align:right\">Summe</th><th></th>" : "<th>Nr.</th><th>Firma</th><th>Titel</th><th>Datum</th><th>Fällig</th><th style=\"text-align:right\">Betrag</th><th>Status</th>";
  const body = `${tile("Umsatz " + jahr, `<div class="v2-kpi">${esc(cent2eur(w.umsatz_cent || 0))}</div>${balken}`, "w4")}
    ${kpiTile("Offen", String(offen.length), null, cent2eur(offen.reduce((x, r) => x + r.summe_cent - (r.bezahlt_cent || 0), 0)))}
    ${kpiTile("Überfällig", String(ueber.length), null, ueber.length ? cent2eur(ueber.reduce((x, r) => x + r.summe_cent - (r.bezahlt_cent || 0), 0)) : "alles im Zeitplan")}
    ${kpiTile("Bezahlt " + jahr, String(bezahlt.length), null, cent2eur(bezahlt.reduce((x, r) => x + r.summe_cent, 0)))}
    ${tile(sub === "entwuerfe" ? "Entwürfe (noch ohne Nummer)" : sub === "offen" ? "Offene Rechnungen" : "Alle Rechnungen", rows ? `<table class="v2-table"><thead><tr>${kopf}</tr></thead><tbody>${rows}</tbody></table>` : emptyRow(sub === "entwuerfe" ? "Keine Entwürfe." : "Keine Rechnungen — aus einem Auftrag („🧾 Rechnung erstellen“) oder oben rechts „+ Neue Rechnung“."), "w12")}`;
  $("#v2-app").innerHTML = secHead("Rechnungen", `<button class="v2-btn pri" data-act="re-neu">+ Neue Rechnung</button>`) + tabs("rechnungen", [["offen", "Offen"], ["alle", "Alle"], ["entwuerfe", `Entwürfe (${(d.entwuerfe || []).length})`]]) + `<div class="v2-grid">${body}</div>`;
}
async function reEditor(eid) {
  openModal(eid ? `Rechnung ${eid} bearbeiten` : "Neue Rechnung", `<div class="v2-empty">Lade…</div>`, true);
  const [k, d] = await Promise.all([jget("/api/crm/kunden"), eid ? jget("/api/finanzen/rechnungen/" + encodeURIComponent(eid)) : Promise.resolve(null), katalogLaden()]);
  AN_FIRMEN = ((k && k.firmen) || []).filter(f => f.aktiv);
  if (!AN_FIRMEN.length) return openModal("Neue Rechnung", emptyRow("Zuerst unter „🏢 Kunden“ eine Firma anlegen."), true);
  const r = (d && d.rechnung) || { firma: "", positionen: [], zuschlaege: [], rabatt_prozent: 0, layout: "hanserautisch", leistung_von: heuteIso(), zahlungsziel_tage: "" };
  const fa = AN_FIRMEN.find(f => f.nummer === r.firma);
  const katOpt = ((KATALOG && KATALOG.gruppen) || []).map(g => `<optgroup label="${esc(g.name)}">${g.items.filter(it => it.aktiv).map(it => `<option value="${esc(it.id)}">${esc(it.name)} — ${cent2eur(it.preis_cent)}${it.einheit ? " / " + esc(it.einheit) : ""}</option>`).join("")}</optgroup>`).join("");
  const gewaehlt = new Set((r.zuschlaege || []).map(z => z.id));
  const zuListe = [...((KATALOG && KATALOG.zuschlaege) || []), ...(r.zuschlaege || []).filter(z => !((KATALOG && KATALOG.zuschlaege) || []).some(x => x.id === z.id))];
  const zuHtml = zuListe.map(z => { const alt = (r.zuschlaege || []).find(x => x.id === z.id); const pr = alt ? alt.prozent : z.prozent;
    return `<label class="v2-modlbl"><input type="checkbox" class="an-zu" value="${esc(z.id)}" data-name="${esc(z.name)}" data-prozent="${esc(String(pr))}" ${gewaehlt.has(z.id) ? "checked" : ""}> +${esc(pz(pr))} % ${esc(z.name)}</label>`; }).join("");
  const rmax = esc(String((KATALOG && KATALOG.rabatt_max) || 30));
  openModal(eid ? `Rechnungs-Entwurf ${eid}` : "Neue Rechnung", `<div class="v2-form v2-an-editor">
    ${r.auftrag ? `<div class="v2-msg ok">Aus Auftrag ${esc(r.auftrag)} (Angebot ${esc(r.angebot || "")}) übernommen — Positionen bei Bedarf anpassen.</div>` : ""}
    <div class="v2-an-kopf"><div class="v2-form">
        <div class="v2-feld v2-auto-feld"><small>Firma * (Name, Kundennummer oder Ort tippen)</small>
          <input id="an-firma-suche" class="v2-inp" autocomplete="off" placeholder="Firma suchen …" value="${fa ? esc(`${fa.name} (${fa.nummer})`) : ""}">
          <input type="hidden" id="an-firma" value="${esc(fa ? fa.nummer : "")}"><div id="an-firma-treffer" class="v2-auto" hidden></div></div>
        <label class="v2-feld"><small>Ansprechpartner</small><select id="an-ap"></select></label>
        <label class="v2-feld"><small>Titel</small><input id="an-titel" value="${esc(r.titel || "")}" placeholder="z. B. Kampagne Herbst"></label></div>
      <div class="v2-form">
        <div class="v2-an-zeile"><label class="v2-feld"><small>Leistung von * (Leistungsdatum)</small><input id="re-von" type="date" value="${esc(r.leistung_von || "")}"></label>
          <label class="v2-feld"><small>Leistung bis (bei Zeitraum)</small><input id="re-bis" type="date" value="${esc(r.leistung_bis || "")}"></label>
          <label class="v2-feld"><small>Zahlungsziel (Tage)</small><input id="re-ziel" type="number" min="0" max="120" value="${esc(String(r.zahlungsziel_tage ?? ""))}" placeholder="Firma / 14"></label></div>
        <label class="v2-feld"><small>Layout</small><select id="an-layout"><option value="hanserautisch" ${r.layout !== "standard" ? "selected" : ""}>Hanserautisch</option><option value="standard" ${r.layout === "standard" ? "selected" : ""}>Schlicht (DIN)</option></select></label></div></div>
    <h3>Positionen <small class="v2-sub">ohne Umsatzsteuer (Kleinunternehmer § 19 UStG)</small></h3>
    <div class="v2-an-kat"><select id="an-kat" class="v2-inp"><option value="">Aus Katalog wählen …</option>${katOpt}</select><button class="v2-btn" data-act="an-kat-neu">+ Aus Katalog</button><button class="v2-btn" data-act="an-pos-neu">+ Freie Position</button></div>
    <div class="v2-an-pos v2-an-pos-kopf"><span>Leistung / Detail</span><span>Menge</span><span>Einheit</span><span>Einzelpreis</span><span>Gesamt</span><span></span></div>
    <div id="an-pos">${(r.positionen || []).map(anPosZeile).join("")}</div>
    <div id="an-pos-leer" class="v2-empty">Noch keine Position.</div>
    <div class="v2-an-fuss"><div class="v2-form">${zuHtml ? `<small class="v2-sub">Zuschläge</small><div class="v2-mods">${zuHtml}</div>` : ""}
        <label class="v2-feld"><small>Rabatt in % (0–${rmax})</small><input id="an-rabatt" type="number" min="0" max="${rmax}" step="0.5" value="${esc(String(r.rabatt_prozent || 0))}"></label></div>
      <div id="an-summe-box" class="v2-an-summen"></div></div>
    <label class="v2-feld"><small>Einleitung (leer = „vielen Dank für Ihren Auftrag. Wir berechnen Ihnen folgende Leistungen:“)</small><textarea id="an-einleitung" rows="2" class="v2-inp">${esc(r.einleitung || "")}</textarea></label>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="re-speichern" data-id="${esc(eid || "")}">${eid ? "Entwurf speichern" : "Entwurf anlegen (noch ohne Nummer)"}</button><div id="an-msg" class="v2-msg"></div></div></div>`, true);
  await anApListe(r.ansprechpartner || "");
  firmaSucheVerdrahten();
  const box = $("#v2-modal .v2-form"); box.addEventListener("input", anSumme); box.addEventListener("change", anSumme); anSumme();
}
async function reSpeichern(eid) {
  if (!$("#an-firma").value) { $("#an-firma-suche").focus(); return kundenMsg("an-msg", "Bitte eine Firma aus den Vorschlägen auswählen.", false); }
  const rechnung = { firma: $("#an-firma").value, ansprechpartner: $("#an-ap").value, titel: $("#an-titel").value.trim(), leistung_von: $("#re-von").value, leistung_bis: $("#re-bis").value,
    layout: $("#an-layout").value, einleitung: $("#an-einleitung").value.trim(), positionen: anPositionen(), zuschlaege: anZuschlaege(), rabatt_prozent: ($("#an-rabatt") || {}).value || 0 };
  if ($("#re-ziel").value !== "") rechnung.zahlungsziel_tage = $("#re-ziel").value;
  const r = eid ? await jpost("/api/finanzen/rechnungen/" + encodeURIComponent(eid), { rechnung }) : await jpost("/api/finanzen/rechnungen", { rechnung });
  if (!r || !r.ok) return kundenMsg("an-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  if (AKTIV === "rechnungen") renderRechnungen();
  return reDetail(eid || r.entwurf_id, eid ? "Entwurf gespeichert." : "Entwurf angelegt — prüfen, dann festschreiben.");
}
async function reDetail(id, meldung, fehler) {
  openModal(id, `<div class="v2-empty">Lade…</div>`, true);
  const d = await jget("/api/finanzen/rechnungen/" + encodeURIComponent(id));
  const r = d && d.rechnung; if (!r) return openModal(id, emptyRow("Rechnung nicht gefunden."), true);
  const entwurf = r.status === "entwurf", sm = r.summen, ap = d.ansprechpartner;
  const pos = r.positionen.map((p, i) => `<tr><td>${i + 1}</td><td><b>${esc(p.beschreibung)}</b>${p.detail ? `<br><small>${esc(p.detail)}</small>` : ""}</td><td style="text-align:right">${esc(String(p.menge).replace(".", ","))} ${esc(p.einheit || "")}</td><td style="text-align:right">${cent2eur(p.gesamt_cent)}</td></tr>`).join("");
  const fuss = (sm.zuschlaege.length || sm.rabatt ? `<tr><td></td><td>Summe Positionen</td><td></td><td style="text-align:right">${cent2eur(sm.formate_cent)}</td></tr>` : "")
    + sm.zuschlaege.map(([n, p, c]) => `<tr><td></td><td>${esc(n)} (+${esc(pz(p))} %)</td><td></td><td style="text-align:right">${cent2eur(c)}</td></tr>`).join("")
    + (sm.rabatt ? `<tr><td></td><td>Rabatt (${esc(pz(sm.rabatt[0]))} %)</td><td></td><td style="text-align:right">−${cent2eur(Math.abs(sm.rabatt[1]))}</td></tr>` : "")
    + `<tr><td></td><td><b>Rechnungsbetrag</b></td><td></td><td style="text-align:right"><b>${cent2eur(sm.gesamt_cent)}</b></td></tr>`;
  let aktionen = `<a class="v2-btn" href="/api/finanzen/rechnungen/${encodeURIComponent(id)}/pdf" target="_blank" rel="noopener">📄 ${entwurf ? "PDF-Vorschau" : "Rechnung (PDF)"}</a>`;
  if (entwurf) aktionen += `<button class="v2-btn" data-act="re-bearbeiten" data-id="${esc(id)}">✎ Bearbeiten</button>
    <button class="v2-btn pri" data-act="re-festschreiben" data-id="${esc(id)}" ${d.steuernummer ? "" : "disabled title=\"Steuernummer fehlt\""}>🔒 Festschreiben (Nummer vergeben)</button>
    <button class="v2-btn" data-act="re-verwerfen" data-id="${esc(id)}">Entwurf verwerfen</button>`;
  else {
    if (r.art !== "storno") aktionen += `<button class="v2-btn pri" data-act="re-senden" data-id="${esc(r.nummer)}" ${d.google ? "" : "disabled"}>✉️ Senden …</button>`;
    else aktionen += `<button class="v2-btn" data-act="re-senden" data-id="${esc(r.nummer)}" ${d.google ? "" : "disabled"}>✉️ Storno senden …</button>`;
    if (r.status === "offen") aktionen += `<button class="v2-btn ok" data-act="re-bezahlt-form" data-id="${esc(r.nummer)}">💶 Zahlung erfassen</button><button class="v2-btn" data-act="re-storno" data-id="${esc(r.nummer)}">Stornieren …</button>`;
  }
  if (r.auftrag) aktionen += `<button class="v2-btn" data-act="ab-detail" data-id="${esc(r.auftrag)}">↩ Auftrag ${esc(r.auftrag)}</button>`;
  if (r.bezug) aktionen += `<button class="v2-btn" data-act="re-detail" data-id="${esc(r.bezug)}">↩ Original ${esc(r.bezug)}</button>`;
  if (r.storniert_durch) aktionen += `<button class="v2-btn" data-act="re-detail" data-id="${esc(r.storniert_durch)}">Storno ${esc(r.storniert_durch)}</button>`;
  const zahlungen = (r.zahlungen || []).map((z, i) => `<div class="v2-list-row${z.storniert ? " v2-fin-storno" : ""}"><span>💶</span><div class="grow"><b>${cent2eur(z.betrag_cent)}</b><small>${esc(datumDe(z.datum))}${z.zuordnung_jahr ? " · zugeordnet " + esc(z.zuordnung_jahr) : ""}${z.notiz ? " · " + esc(z.notiz) : ""}${z.storniert ? " · storniert: " + esc(z.storno_grund || "") : ""}</small></div>${!z.storniert && r.status !== "storniert" ? `<button class="v2-btn" data-act="re-zahlung-storno" data-id="${esc(r.nummer)}" data-val="${i}" title="Falsch erfasste Zahlung zurücknehmen">↶</button>` : ""}</div>`).join("");
  const lbl = { rechnung_entwurf: "Entwurf angelegt", rechnung_entwurf_geaendert: "Entwurf geändert", rechnung_festgeschrieben: "Festgeschrieben", rechnung_versendet: "Gesendet", rechnung_bezahlt: "Zahlung", rechnung_zahlung_storniert: "Zahlung storniert" };
  const verlauf = (r.verlauf || []).slice().reverse().map(v => `<div class="v2-list-row"><div class="grow"><b>${esc(lbl[v.typ] || v.typ)}${v.mail_an ? " an " + esc(v.mail_an) : ""}${v.betrag_cent ? " " + cent2eur(v.betrag_cent) : ""}${v.storno ? " — storniert durch " + esc(v.storno) : ""}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")}${v.felder ? " · " + esc(v.felder.join(", ")) : ""}${v.grund ? " · " + esc(v.grund) : ""}</small></div></div>`).join("");
  const titel = entwurf ? `Rechnungs-Entwurf · ${d.firma.name || r.firma}` : `${r.nummer} · ${d.firma.name || r.firma}`;
  openModal(titel, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    ${entwurf && !d.steuernummer ? `<div class="v2-msg err">Steuernummer fehlt in den Firmendaten — Festschreiben nicht möglich.</div>` : ""}
    <div class="v2-card-actions" style="flex-wrap:wrap;margin:8px 0 14px">${aktionen}</div>
    <div class="v2-an-detail"><div>
    <div class="v2-kv"><span>Status</span>${reBadge(r)}</div>
    ${entwurf ? `<div class="v2-kv"><span>Nummer</span><b>wird beim Festschreiben vergeben</b></div>` : `<div class="v2-kv"><span>Rechnungsdatum</span><b>${esc(datumDe(r.rechnungsdatum))}</b></div><div class="v2-kv"><span>Fällig am</span><b>${esc(datumDe(r.faellig_am))}</b></div>`}
    <div class="v2-kv"><span>Firma</span><b>${esc(r.firma)} · ${esc(d.firma.name || "")}</b></div>
    <div class="v2-kv"><span>Ansprechpartner</span><b>${ap ? esc(ap.nummer + " · " + [ap.vorname, ap.nachname].filter(Boolean).join(" ")) : "—"}</b></div>
    <div class="v2-kv"><span>Leistung</span><b>${esc([datumDe(r.leistung_von), datumDe(r.leistung_bis)].filter(Boolean).join(" – ") || "— fehlt —")}</b></div>
    ${!entwurf && r.art !== "storno" ? `<div class="v2-kv"><span>Bezahlt / offen</span><b>${cent2eur(r.bezahlt_cent || 0)} / ${cent2eur(r.summe_cent - (r.bezahlt_cent || 0))}</b></div>` : ""}
    ${r.versendet_mail ? `<div class="v2-kv"><span>Gesendet</span><b>✉️ ${esc(r.versendet_mail.an)} · ${esc(zeit(r.versendet_am))}</b></div>` : ""}
    ${zahlungen ? `<h3>Zahlungen</h3>${zahlungen}` : ""}
    <h3>Verlauf</h3>${verlauf}
    </div><div>
    <div id="re-aktion-box"></div>
    <h3>Positionen</h3><table class="v2-table"><thead><tr><th>#</th><th>Leistung</th><th style="text-align:right">Menge</th><th style="text-align:right">Gesamt</th></tr></thead><tbody>${pos}</tbody><tfoot>${fuss}</tfoot></table>
    </div></div>`, true);
}
async function reSendenVorschau(nr) {
  const box = $("#re-aktion-box"); if (!box) return;
  const v = await jget(`/api/finanzen/rechnungen/${encodeURIComponent(nr)}/versandvorschau`);
  if (!v) { box.innerHTML = emptyRow("Vorschau nicht verfügbar."); return; }
  box.innerHTML = `<h3>Rechnung senden</h3><div class="v2-form">
    <div class="v2-kv"><span>Absender</span><b>${esc(v.absender)}</b></div>
    <label class="v2-feld"><small>An *</small><input id="res-an" type="email" value="${esc(v.an || "")}"></label>
    <label class="v2-feld"><small>Betreff *</small><input id="res-betreff" value="${esc(v.betreff)}"></label>
    <label class="v2-feld"><small>Text *</small><textarea id="res-text" class="v2-inp" rows="8">${esc(v.text)}</textarea></label>
    <div class="v2-kv"><span>Anhang</span><a href="/api/finanzen/rechnungen/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="re-senden-jetzt" data-id="${esc(nr)}">✉️ Jetzt senden</button><button class="v2-btn" data-act="re-box-zu">Abbrechen</button></div><div id="res-msg" class="v2-msg"></div></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
function reBezahltForm(nr) {
  const box = $("#re-aktion-box"); if (!box) return;
  box.innerHTML = `<h3>Zahlung erfassen</h3><div class="v2-form" style="max-width:420px">
    <div class="v2-an-zeile"><label class="v2-feld"><small>Zahlungsdatum</small><input id="rez-datum" type="date" value="${heuteIso()}"></label>
      <label class="v2-feld"><small>Betrag (leer = offener Rest)</small><input id="rez-betrag" inputmode="decimal" placeholder="z. B. 1.020,00"></label></div>
    <label class="v2-feld"><small>Notiz</small><input id="rez-notiz" placeholder="z. B. Überweisung comdirect"></label><div id="rez-zuord"></div>
    <div class="v2-card-actions"><button class="v2-btn ok" data-act="re-bezahlt" data-id="${esc(nr)}">💶 Zahlung buchen</button><button class="v2-btn" data-act="re-box-zu">Abbrechen</button></div><div id="rez-msg" class="v2-msg"></div></div>`;
  zehnTageVerdrahten("rez-datum", "rez-zuord");
}

/* =========================== Belege / Eingangsrechnungen (KUNDEN_FINANZEN Etappe 6) =========================== */
// Hochladen (Ziehen, Auswahl, Kamera) oder an LUNA weiterleiten -> lokal auslesen -> Vorschlag -> CEO bucht.
const BL_STATUS = { zu_pruefen: ["Zu prüfen", "wartet"], gebucht: ["Gebucht", "ok"], verworfen: ["Verworfen", "neutral"] };
const blBadge = (st) => { const [l, c] = BL_STATUS[st] || [st, "neutral"]; return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
const TQ = { "xml": "E-Rechnung (XML)", "pdf-text": "PDF-Text", "ocr": "Texterkennung (Scan/Foto)", "leer": "kein Text erkannt" };
let BL_KAT = {}, BL_KAT_EIN = {};
RENDER.belege = renderBelege;
async function renderBelege(meldung) {
  const sub = SUBTAB.belege || "pruefen";
  const d = await jget("/api/finanzen/belege") || { belege: [], kategorien: {} };
  BL_KAT = d.kategorien || {}; BL_KAT_EIN = d.kategorien_einnahme || {};
  const alle = d.belege || [];
  const liste = sub === "pruefen" ? alle.filter(b => b.status === "zu_pruefen") : sub === "gebucht" ? alle.filter(b => b.status === "gebucht") : alle;
  const jahr = String(new Date().getFullYear());
  const gebuchtJahr = alle.filter(b => b.status === "gebucht" && b.art !== "einnahme" && String(b.rechnungsdatum || "").startsWith(jahr));
  const rows = liste.map(b => `<tr class="klick" data-act="bl-detail" data-id="${esc(b.nummer)}"><td><b>${esc(b.nummer)}</b>${b.quelle === "mail" ? " ✉️" : ""}${b.e_rechnung ? " <small>E-Rechnung</small>" : ""}</td><td>${esc(b.lieferant || b.dateiname)}</td><td>${esc(datumDe(b.rechnungsdatum))}</td><td style="text-align:right${b.art === "einnahme" ? ";color:var(--v2-green)" : ""}">${b.betrag_cent != null ? (b.art === "einnahme" ? "+" : "") + cent2eur(b.betrag_cent) : "–"}</td><td>${b.art === "einnahme" ? "Gutschrift (Einnahme)" : esc(BL_KAT[b.kategorie] || "")}</td><td>${blBadge(b.status)}${b.bezahlt_am ? " 💶" : b.bezahlt_cent ? " <small>teilw. bezahlt</small>" : ""}</td></tr>`).join("");
  const upload = `<div class="v2-bl-drop" id="bl-drop"><b>Rechnungen hierher ziehen</b><small>PDF, E-Rechnung (XML), Foto · bis 15 MB · mehrere auf einmal</small>
    <div class="v2-card-actions" style="justify-content:center"><label class="v2-btn pri">📄 Dateien wählen<input id="bl-datei" type="file" multiple accept=".pdf,.xml,image/*" hidden></label>
    <label class="v2-btn">📷 Foto aufnehmen<input id="bl-kamera" type="file" accept="image/*" capture="environment" hidden></label></div>
    <small class="v2-sub">Oder Rechnungen per Mail an <b>luna.hanserautisch@gmail.com</b> weiterleiten — LUNA übernimmt sie automatisch (nur von deinen Adressen).</small>
    <div id="bl-msg" class="v2-msg" style="white-space:pre-wrap">${meldung ? esc(meldung) : ""}</div></div>`;
  const body = `${tile("Beleg hinzufügen", upload, "w12")}
    ${kpiTile("Zu prüfen", String(alle.filter(b => b.status === "zu_pruefen").length), null, "warten auf dich")}
    ${kpiTile("Ausgaben " + jahr, cent2eur(gebuchtJahr.reduce((x, b) => x + (b.betrag_cent || 0), 0)), null, `${gebuchtJahr.length} gebuchte Belege`)}
    ${kpiTile("Unbezahlt", String(alle.filter(b => b.status === "gebucht" && !b.bezahlt_am).length), null, "gebucht, noch offen")}
    ${tile(sub === "pruefen" ? "Zu prüfen" : sub === "gebucht" ? "Gebucht" : "Alle Belege", rows ? `<table class="v2-table"><thead><tr><th>Nr.</th><th>Lieferant / Datei</th><th>Datum</th><th style="text-align:right">Betrag</th><th>Kategorie</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>` : emptyRow(sub === "pruefen" ? "Nichts zu prüfen." : "Noch keine Belege."), "w12")}`;
  $("#v2-app").innerHTML = secHead("Belege & Eingangsrechnungen") + tabs("belege", [["pruefen", "Zu prüfen"], ["gebucht", "Gebucht"], ["alle", "Alle"]]) + `<div class="v2-grid">${body}</div>`;
  const drop = $("#bl-drop");
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("aktiv"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("aktiv"); }));
  drop.addEventListener("drop", e => blHochladen([...e.dataTransfer.files]));
  $("#bl-datei").addEventListener("change", e => blHochladen([...e.target.files]));
  $("#bl-kamera").addEventListener("change", e => blHochladen([...e.target.files]));
}
function blLesen(datei) {                        // -> {name, daten: base64}; grosse Fotos im Browser verkleinern
  return new Promise((ok, nein) => {
    const alsB64 = (blob, name) => { const r = new FileReader(); r.onload = () => ok({ name, daten: String(r.result).split(",")[1] }); r.onerror = nein; r.readAsDataURL(blob); };
    if (/^image\/(jpeg|png|webp)$/.test(datei.type) && datei.size > 2500000) {
      const img = new Image(), url = URL.createObjectURL(datei);
      img.onload = () => { const f = Math.min(1, 2400 / Math.max(img.width, img.height)); const c = document.createElement("canvas"); c.width = Math.round(img.width * f); c.height = Math.round(img.height * f);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url); c.toBlob(b => alsB64(b, datei.name.replace(/\.\w+$/, "") + ".jpg"), "image/jpeg", 0.88); };
      img.onerror = () => { URL.revokeObjectURL(url); alsB64(datei, datei.name); };
      img.src = url;
    } else alsB64(datei, datei.name);
  });
}
async function blHochladen(dateien) {
  if (!dateien.length) return;
  const msg = $("#bl-msg"); if (msg) { msg.className = "v2-msg"; msg.textContent = `⏳ ${dateien.length} Datei(en) werden ausgelesen …`; }
  const zeilen = [];
  for (let i = 0; i < dateien.length; i += 5) {                      // in kleinen Paketen senden
    const paket = await Promise.all(dateien.slice(i, i + 5).map(blLesen));
    const r = await jpost("/api/finanzen/belege/hochladen", { dateien: paket });
    if (!r) { zeilen.push("Upload fehlgeschlagen (Verbindung oder Datei zu groß)."); continue; }
    (r.ergebnisse || []).forEach(e => zeilen.push(e.ok ? (e.doppelt ? `${e.name}: schon vorhanden als ${e.nummer}` : `${e.name} → ${e.nummer} (${TQ[e.text_quelle] || e.text_quelle})`) : `${e.name}: ${e.hinweis}`));
  }
  SUBTAB.belege = "pruefen";
  return renderBelege(zeilen.join("\n"));
}
async function blDetail(nr, meldung, fehler) {
  openModal(nr, `<div class="v2-empty">Lade…</div>`, true);
  const d = await jget("/api/finanzen/belege/" + encodeURIComponent(nr));
  const b = d && d.beleg; if (!b) return openModal(nr, emptyRow("Beleg nicht gefunden."), true);
  BL_KAT = d.kategorien || BL_KAT; BL_KAT_EIN = d.kategorien_einnahme || BL_KAT_EIN;
  const f = Object.keys(b.felder || {}).length ? b.felder : null, v = b.vorschlag || {};
  const art = (f ? f.art : v.art) || "ausgabe", ein = art === "einnahme";
  const w = (k) => f ? (k === "betrag" ? cent2feld(f.betrag_cent) : f[k] || "") : (v[k] || "");
  const src = `/api/finanzen/belege/${encodeURIComponent(nr)}/datei`;
  const vorschau = (b.mime || "").startsWith("image/") ? `<img src="${src}" alt="Beleg" class="v2-bl-bild">`
    : b.mime === "application/pdf" ? `<iframe src="${src}" class="v2-bl-pdf" title="Beleg"></iframe>` : `<pre class="v2-mail-text">${esc(b.text || "")}</pre>`;
  const quelle = { "e-rechnung": "E-Rechnung (exakt)", regeln: "Schnell-Erkennung", backoffice: "LUNA-Backoffice (lokale KI)" }[v.quelle] || v.quelle || "";
  const kiLaeuft = !f && v.quelle !== "backoffice" && v.quelle !== "e-rechnung" && ["neu", "in_arbeit"].includes(d.ki_status);
  const katOpt = Object.entries(ein ? BL_KAT_EIN : BL_KAT).map(([k, l]) => `<option value="${esc(k)}" ${w("kategorie") === k ? "selected" : ""}>${esc(l)}</option>`).join("");
  const lief = (d.lieferanten || []).map(l => `<option value="${esc(l.name)}">`).join("");
  const gesperrt = b.status === "verworfen" ? "disabled" : "";
  const lbl = { eingang_angelegt: "Eingegangen", eingang_vorschlag: "Vorschlag", eingang_gebucht: "Gebucht", eingang_bezahlt: "Zahlung", eingang_zahlung_storniert: "Zahlung storniert", eingang_verworfen: "Verworfen" };
  const rest = f ? f.betrag_cent - (b.bezahlt_cent || 0) : 0;
  const zahlungen = (b.zahlungen || []).map((z, i) => `<div class="v2-list-row${z.storniert ? " v2-fin-storno" : ""}"><span>💶</span><div class="grow"><b>${cent2eur(z.betrag_cent)}</b><small>${esc(datumDe(z.datum))}${z.zuordnung_jahr ? " · zugeordnet " + esc(z.zuordnung_jahr) : ""}${z.notiz ? " · " + esc(z.notiz) : ""}${z.storniert ? " · storniert: " + esc(z.storno_grund || "") : ""}</small></div>${!z.storniert ? `<button class="v2-btn" data-act="bl-zahlung-storno" data-id="${esc(nr)}" data-val="${i}" title="Falsch erfasste Zahlung zurücknehmen">↶</button>` : ""}</div>`).join("");
  const verlauf = (b.verlauf || []).slice().reverse().map(x => `<div class="v2-list-row"><div class="grow"><b>${esc(lbl[x.typ] || x.typ)}${x.quelle ? " (" + esc(x.quelle) + ")" : ""}${x.datum ? " " + esc(datumDe(x.datum)) : ""}</b><small>${esc(zeit(x.ts))} · ${esc(x.von || "")}${x.grund ? " · " + esc(x.grund) : ""}</small></div></div>`).join("");
  openModal(`${nr} · ${b.dateiname}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    <div class="v2-an-detail"><div>
      ${vorschau}
      <div class="v2-kv"><span>Eingang</span><b>${esc(zeit(b.eingegangen))} · ${b.quelle === "mail" ? "per Mail" : "Upload"} · ${esc(TQ[b.text_quelle] || b.text_quelle)}</b></div>
      <h3>Verlauf</h3>${verlauf}
    </div><div>
      <div class="v2-kv"><span>Status</span>${blBadge(b.status)}${b.bezahlt_am ? ` <span class="v2-badge ok">bezahlt ${esc(datumDe(b.bezahlt_am))}</span>` : b.bezahlt_cent ? ` <span class="v2-badge wartet">teilweise bezahlt · offen ${esc(cent2eur(rest))}</span>` : ""}</div>
      ${!f ? `<div class="v2-kv"><span>Vorschlag von</span><b>${esc(quelle)}${kiLaeuft ? " · KI liest noch …" : ""}</b></div>` : ""}
      ${kiLaeuft ? `<button class="v2-btn" data-act="bl-detail" data-id="${esc(nr)}">🔄 KI-Vorschlag abholen</button>` : ""}
      ${!f && v.waehrung && v.waehrung !== "EUR" ? `<div class="v2-msg err" style="margin:8px 0">Betrag in ${esc(v.waehrung)}: ${esc(v.betrag_fremd || "?")}. Bitte den <b>Euro-Betrag</b> eintragen, der auf dem Konto angekommen bzw. abgebucht worden ist (Kontoauszug) — nur der zählt in der EÜR.</div>` : ""}
      <h3>${f ? "Gebucht (korrigierbar)" : "Prüfen & buchen"}</h3><div class="v2-form">
        <label class="v2-feld"><small>Art *</small><select id="bl-art" ${gesperrt}><option value="ausgabe" ${ein ? "" : "selected"}>Ausgabe — wir zahlen (Eingangsrechnung)</option><option value="einnahme" ${ein ? "selected" : ""}>Einnahme — wir bekommen Geld (Gutschrift, z. B. Facebook-Monetarisierung)</option></select></label>
        <label class="v2-feld"><small id="bl-lief-lbl">${ein ? "Von (Aussteller der Gutschrift) *" : "Lieferant *"}</small><input id="bl-lieferant" list="bl-lieferanten" value="${esc(w("lieferant"))}" ${gesperrt}><datalist id="bl-lieferanten">${lief}</datalist></label>
        <label class="v2-modlbl"><input type="checkbox" id="bl-lief-anlegen" ${f && f.lieferant_firma ? "" : "checked"} ${gesperrt}> im Kundenstamm als Lieferant führen</label>
        <div class="v2-an-zeile"><label class="v2-feld"><small>Rechnungsnummer</small><input id="bl-nr" value="${esc(w("rechnungsnummer"))}" ${gesperrt}></label>
          <label class="v2-feld"><small>Rechnungsdatum *</small><input id="bl-datum" type="date" value="${esc(w("rechnungsdatum"))}" ${gesperrt}></label>
          <label class="v2-feld"><small>Fällig am</small><input id="bl-faellig" type="date" value="${esc(w("faellig_am"))}" ${gesperrt}></label></div>
        <div class="v2-an-zeile"><label class="v2-feld"><small>Betrag brutto (€) *</small><input id="bl-betrag" inputmode="decimal" value="${esc(w("betrag"))}" ${gesperrt}></label>
          <label class="v2-feld" style="grid-column: span 2"><small>Kategorie (EÜR) *</small><select id="bl-kat" ${gesperrt}><option value="">— wählen —</option>${katOpt}</select></label></div>
        <label class="v2-feld" id="bl-nd-feld" ${w("kategorie") === "anlage" ? "" : "hidden"}><small>Nutzungsdauer in Jahren * (Computer/Software: 1 = sofort voll absetzbar · Foto/Video-Technik: 7)</small><input id="bl-nd" type="number" min="1" max="50" value="${esc(String((f && f.nutzungsdauer_jahre) || ""))}" ${gesperrt}></label>
        <label class="v2-feld"><small>Leistung / was wurde gekauft</small><input id="bl-leistung" value="${esc(w("leistung"))}" ${gesperrt}></label>
        <label class="v2-feld"><small>Notiz</small><input id="bl-notiz" value="${esc(f ? f.notiz || "" : v.betrag_fremd ? `${v.betrag_fremd} ${v.waehrung} laut Beleg` : "")}" ${gesperrt}></label>
        ${b.status !== "verworfen" ? `<div class="v2-card-actions"><button class="v2-btn pri" data-act="bl-buchen" data-id="${esc(nr)}">✔ ${f ? "Korrektur buchen" : "Buchen"}</button>
          ${f && rest !== 0 ? `<button class="v2-btn ok" data-act="bl-bezahlt-form" data-id="${esc(nr)}">💶 ${ein ? "Geldeingang erfassen" : "Zahlung erfassen"}</button>` : ""}
          ${!f ? `<button class="v2-btn" data-act="bl-verwerfen" data-id="${esc(nr)}">Kein Beleg / verwerfen</button>` : ""}</div>` : `<div class="v2-msg">Verworfen: ${esc(b.grund || "")}</div>`}
        <div id="bl-form-msg" class="v2-msg"></div></div>
      <div id="bl-aktion-box"></div>
      ${zahlungen ? `<h3>Zahlungen</h3>${zahlungen}` : ""}
      ${ein ? `<div class="v2-msg" style="margin:8px 0">Gutschrift = Einnahme: zählt zum Umsatz und zur Kleinunternehmer-Grenze. Achtung: Weist die Gutschrift <b>Umsatzsteuer</b> aus, kannst du sie dem Finanzamt schulden (§ 14c UStG), solange du nicht widersprichst — dann dem Aussteller widersprechen und im Konto „Kleinunternehmer“ hinterlegen.</div>` : ""}
      <small class="v2-sub">Kleinunternehmer: Der Bruttobetrag ist die Ausgabe (kein Vorsteuerabzug). Über 800 € ist es kein geringwertiges Wirtschaftsgut, sondern ein Anlagegut (Abschreibung). Das Original bleibt unverändert archiviert.</small>
    </div></div>`, true);
  const kt = $("#bl-kat"); if (kt) kt.addEventListener("change", () => { const nd = $("#bl-nd-feld"); if (nd) nd.hidden = kt.value !== "anlage"; });
  const at = $("#bl-art"); if (at && kt) at.addEventListener("change", () => {              // Kategorien je Art umschalten
    const e = at.value === "einnahme", liste = e ? BL_KAT_EIN : BL_KAT;
    kt.innerHTML = (e ? "" : `<option value="">— wählen —</option>`) + Object.entries(liste).map(([k, l]) => `<option value="${esc(k)}">${esc(l)}</option>`).join("");
    $("#bl-lief-lbl").textContent = e ? "Von (Aussteller der Gutschrift) *" : "Lieferant *"; kt.dispatchEvent(new Event("change")); });
}
function blBezahltForm(nr) {
  const box = $("#bl-aktion-box"); if (!box) return;
  box.innerHTML = `<h3>Zahlung erfassen</h3><div class="v2-form" style="max-width:420px">
    <div class="v2-an-zeile"><label class="v2-feld"><small>Bezahlt am</small><input id="blz-datum" type="date" value="${heuteIso()}"></label>
      <label class="v2-feld"><small>Betrag (leer = offener Rest)</small><input id="blz-betrag" inputmode="decimal" placeholder="Rest"></label></div>
    <label class="v2-feld"><small>Notiz</small><input id="blz-notiz" placeholder="z. B. PayPal, Kreditkarte"></label><div id="blz-zuord"></div>
    <div class="v2-card-actions"><button class="v2-btn ok" data-act="bl-bezahlt" data-id="${esc(nr)}">💶 Zahlung buchen</button><button class="v2-btn" data-act="bl-box-zu">Abbrechen</button></div><div id="blz-msg" class="v2-msg"></div></div>`;
  zehnTageVerdrahten("blz-datum", "blz-zuord");
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function blBuchen(nr, trotz) {
  const felder = { lieferant: $("#bl-lieferant").value.trim(), rechnungsnummer: $("#bl-nr").value.trim(), rechnungsdatum: $("#bl-datum").value, faellig_am: $("#bl-faellig").value,
    betrag: $("#bl-betrag").value.trim(), kategorie: $("#bl-kat").value, leistung: $("#bl-leistung").value.trim(), notiz: $("#bl-notiz").value.trim(), trotz_doppelt: !!trotz, art: $("#bl-art").value,
    nutzungsdauer_jahre: $("#bl-kat").value === "anlage" ? $("#bl-nd").value : "" };
  const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(nr)}/buchen`, { felder, lieferant_anlegen: $("#bl-lief-anlegen").checked });
  if (!r) return kundenMsg("bl-form-msg", "Keine Verbindung zum Server.", false);
  if (!r.ok && /schon als/.test(r.hinweis || "") && confirm(r.hinweis + "\n\nTrotzdem buchen?")) return blBuchen(nr, true);
  if (!r.ok) return kundenMsg("bl-form-msg", r.hinweis || "Fehler.", false);
  if (AKTIV === "belege") renderBelege();
  return blDetail(nr, `Gebucht: ${r.felder.lieferant} · ${cent2eur(r.felder.betrag_cent)} · ${r.felder.art === "einnahme" ? "Einnahme (Gutschrift)" : BL_KAT[r.felder.kategorie] || r.felder.kategorie}`);
}

/* =========================== Finanzen (KUNDEN_FINANZEN Etappe 7) =========================== */
// Übersicht über alles (Kennzahlen, Monatsverlauf, offene Posten, Pipeline, To-dos), Journal nach Zahlungsdatum,
// EÜR, Anlageverzeichnis und Buchungen ohne Beleg (Eigenbelege, z. B. Plattform-Auszahlungen).
let FIN_JAHR = 0, FIN_KAT = null;
const FIN_ACT = { rechnung: "re-detail", beleg: "bl-detail", eigenbeleg: "eb-detail" };
function finDelta(jetzt, vor, weniger_ist_gut) {
  if (!vor) return null; const p = Math.round((jetzt - vor) / Math.abs(vor) * 100);
  return { up: weniger_ist_gut ? p <= 0 : p >= 0, text: (p >= 0 ? "+" : "") + p + " % zum Vorjahr" };
}
RENDER.finanzen = renderFinanzen;
async function renderFinanzen(meldung) {
  const sub = SUBTAB.finanzen || "uebersicht";
  const u = await jget("/api/finanzen/uebersicht" + (FIN_JAHR ? "?jahr=" + FIN_JAHR : ""));
  if (!u) { $("#v2-app").innerHTML = secHead("Finanzen") + emptyRow("Finanzen nicht erreichbar (Modul „Finanzen“ nötig)."); return; }
  FIN_JAHR = u.jahr;
  const jahrWahl = `<select id="fin-jahr" class="v2-inp" style="width:auto">${u.jahre.map(j => `<option ${j === u.jahr ? "selected" : ""}>${j}</option>`).join("")}</select>`;
  const body = sub === "journal" ? await finJournal(u.jahr) : sub === "euer" ? await finEuer(u.jahr) : sub === "anlagen" ? await finAnlagen(u.jahr) : finUebersicht(u);
  $("#v2-app").innerHTML = secHead("Finanzen " + u.jahr, `${jahrWahl}<button class="v2-btn" data-act="eb-neu" data-val="ausgabe">− Ausgabe ohne Beleg</button><button class="v2-btn pri" data-act="eb-neu" data-val="einnahme">+ Einnahme ohne Rechnung</button>`)
    + tabs("finanzen", [["uebersicht", "Übersicht"], ["journal", "Journal"], ["euer", "EÜR"], ["anlagen", "Anlagen"]])
    + (meldung ? `<div class="v2-msg ok" style="margin-bottom:12px">${esc(meldung)}</div>` : "") + `<div class="v2-grid">${body}</div>`;
  $("#fin-jahr").addEventListener("change", e => { FIN_JAHR = Number(e.target.value); renderFinanzen(); });
}
function finUebersicht(u) {
  const k = u.kennzahlen, v = u.vorjahr, f = u.forderungen, vb = u.verbindlichkeiten, p = u.pipeline, w = u.waechter;
  const max = Math.max(1, ...u.monate.map(m => Math.max(Math.abs(m.einnahmen_cent), Math.abs(m.ausgaben_cent))));
  const h = (c) => Math.max(0, Math.round(c / max * 100));
  const monate = `<div class="v2-fin-monate">${u.monate.map(m => `<div class="v2-fin-monat" title="${esc(m.monat)}: Einnahmen ${esc(cent2eur(m.einnahmen_cent))} · Ausgaben ${esc(cent2eur(m.ausgaben_cent))}"><div class="v2-fin-saeulen"><i class="e" style="height:${h(m.einnahmen_cent)}%"></i><i class="a" style="height:${h(m.ausgaben_cent)}%"></i></div><small>${esc(m.monat)}</small></div>`).join("")}</div>
    <div class="v2-legend"><span><i style="background:var(--v2-green)"></i>Einnahmen</span><span><i style="background:var(--v2-red)"></i>Ausgaben (abziehbar)</span>${u.afa_cent ? `<span>+ Abschreibung ${esc(cent2eur(u.afa_cent))} im Jahr</span>` : ""}</div>`;
  const kmax = Math.max(1, ...u.kategorien.map(x => Math.abs(x.betrag_cent)));
  const kat = u.kategorien.length ? u.kategorien.map(x => `<div class="v2-fin-hbar"><span>${esc(x.name)}</span><div><i style="width:${Math.max(2, Math.round(Math.abs(x.betrag_cent) / kmax * 100))}%"></i></div><b>${esc(cent2eur(x.betrag_cent))}</b></div>`).join("") : emptyRow("Noch keine Ausgaben in diesem Jahr.");
  const kunden = u.kunden.length ? u.kunden.map((x, i) => `<div class="v2-list-row"><span>${i + 1}.</span><div class="grow"><b>${esc(x.name)}</b></div><b>${esc(cent2eur(x.betrag_cent))}</b></div>`).join("") : emptyRow("Noch keine Einnahmen in diesem Jahr.");
  const anteil = Math.min(100, Math.round((w.anteil || 0) * 100));
  const grenze = `<div class="v2-kpi">${esc(cent2eur(w.umsatz_cent || 0))}</div><div class="v2-re-balken"><i style="width:${anteil}%;background:${w.ueberschritten ? "var(--v2-red)" : w.warnung ? "#e8a200" : "var(--v2-accent)"}"></i></div>
    <small class="v2-sub">${anteil} % von 100.000 € · Rechnungen nach Rechnungsdatum + Einnahmen ohne Rechnung${w.vorjahr_ueberschritten ? " · ⚠️ Vorjahr über 25.000 €!" : ""}</small>`;
  const stufe = (icon, titel, anzahl, cent, ziel) => `<div class="v2-fin-stufe klick" data-tab="${ziel}"><span>${icon}</span><div><b>${esc(titel)}</b><small>${anzahl}${cent != null ? " · " + esc(cent2eur(cent)) : ""}</small></div></div>`;
  const pipeline = `<div class="v2-fin-pipeline">${stufe("📄", "Angebote offen", p.angebote_anzahl, p.angebote_cent, "angebote:offen")}${stufe("🤝", "Aufträge ohne Rechnung", p.auftraege_anzahl, p.auftraege_cent, "angebote:auftraege")}${stufe("✎", "Rechnungsentwürfe", p.rechnung_entwuerfe, null, "rechnungen:entwuerfe")}${stufe("⏳", "Offene Rechnungen", f.anzahl, f.summe_cent, "rechnungen:offen")}</div>`;
  const posten = (liste, act) => liste.slice(0, 6).map(x => `<div class="v2-list-row klick" data-act="${x.act || act}" data-id="${esc(x.nummer)}"><span class="v2-badge ${x.ueberfaellig ? "err" : "neutral"}">${x.ueberfaellig ? "überfällig" : x.faellig_am ? esc(datumDe(x.faellig_am)) : "offen"}</span><div class="grow"><b>${esc(x.gegenpartei || x.nummer)}</b><small>${esc(x.nummer)}</small></div><b>${esc(cent2eur(x.offen_cent))}</b></div>`).join("");
  const todos = [
    u.belege_zu_pruefen ? `<div class="v2-list-row klick" data-tab="belege:pruefen"><span>📥</span><div class="grow"><b>${u.belege_zu_pruefen} Beleg(e) prüfen und buchen</b></div><span>›</span></div>` : "",
    f.ueberfaellig ? `<div class="v2-list-row klick" data-tab="rechnungen:offen"><span>⚠️</span><div class="grow"><b>${f.ueberfaellig} Rechnung(en) überfällig</b><small>nachfassen oder Zahlung erfassen</small></div><span>›</span></div>` : "",
    vb.ueberfaellig ? `<div class="v2-list-row klick" data-tab="belege:gebucht"><span>💸</span><div class="grow"><b>${vb.ueberfaellig} Eingangsrechnung(en) fällig</b><small>bezahlen und als bezahlt markieren</small></div><span>›</span></div>` : "",
    p.auftraege_anzahl ? `<div class="v2-list-row klick" data-tab="angebote:auftraege"><span>🧾</span><div class="grow"><b>${p.auftraege_anzahl} Auftrag/Aufträge noch ohne Rechnung</b></div><span>›</span></div>` : "",
  ].join("") || emptyRow("Alles erledigt 🎉");
  const zeilen = u.letzte.length ? finTabelle(u.letzte, false) : emptyRow("Noch keine Zahlungen erfasst — in Rechnungen/Belegen „💶 Zahlung erfassen“ oder oben eine Einnahme/Ausgabe ohne Beleg.");
  return `${kpiTile("Einnahmen", cent2eur(k.einnahmen_cent), finDelta(k.einnahmen_cent, v.einnahmen_cent), "nach Zahlungseingang")}
    ${kpiTile("Ausgaben", cent2eur(k.ausgaben_cent), finDelta(k.ausgaben_cent, v.ausgaben_cent, true), "abziehbar, inkl. Abschreibung")}
    ${kpiTile("Gewinn", cent2eur(k.gewinn_cent), finDelta(k.gewinn_cent, v.gewinn_cent), "Einnahmen − Ausgaben (EÜR)")}
    ${kpiTile("Offen: bekommen wir", cent2eur(f.summe_cent), null, `${f.anzahl} Rechnung(en)${f.ueberfaellig ? ", " + f.ueberfaellig + " überfällig" : ""} · wir zahlen noch ${cent2eur(vb.summe_cent)}`)}
    ${tile("Monatsverlauf " + u.jahr, monate, "w8")}
    ${tile("Kleinunternehmer-Grenze " + u.jahr, grenze, "w4")}
    ${tile("Vom Angebot zum Geld", pipeline, "w12")}
    ${tile("Zu erledigen", todos, "w4")}
    ${tile("Wir bekommen (" + f.anzahl + ")", posten(f.liste, "re-detail") || emptyRow("Keine offenen Rechnungen."), "w4")}
    ${tile("Wir zahlen (" + vb.anzahl + ")", posten(vb.liste, "bl-detail") || emptyRow("Keine offenen Eingangsrechnungen."), "w4")}
    ${tile("Ausgaben nach Kategorie", kat, "w6")}
    ${tile("Top-Kunden " + u.jahr, kunden, "w6")}
    ${tile("Letzte Zahlungen", zeilen, "w12")}`;
}
function finTabelle(zeilen, summe) {
  const rows = zeilen.map(z => `<tr class="klick${z.storniert ? " v2-fin-storno" : ""}" data-act="${FIN_ACT[z.quelle]}" data-id="${esc(z.bezug)}"><td>${esc(datumDe(z.datum))}${z.zuordnung_jahr ? ` <small title="10-Tage-Regel">→ ${esc(z.zuordnung_jahr)}</small>` : ""}</td><td><b>${esc(z.bezug)}</b></td><td>${esc(z.gegenpartei || "")}</td><td>${esc(z.text || "")}${z.storniert ? ` <span class="v2-badge err">storniert</span>` : ""}</td><td><small>${esc(z.position)}</small></td>
    <td style="text-align:right;color:var(--v2-green)">${z.art === "einnahme" ? esc(cent2eur(z.betrag_cent)) : ""}</td><td style="text-align:right;color:var(--v2-red)">${z.art === "ausgabe" ? esc(cent2eur(z.betrag_cent)) : ""}</td>${summe ? `<td style="text-align:right">${z.art === "ausgabe" && z.abziehbar_cent !== z.betrag_cent && !z.storniert ? esc(cent2eur(z.abziehbar_cent)) : ""}</td>` : ""}</tr>`).join("");
  const gueltig = zeilen.filter(z => !z.storniert), s = (a) => gueltig.filter(z => z.art === a).reduce((x, z) => x + z.betrag_cent, 0);
  const fuss = summe ? `<tfoot><tr><td></td><td></td><td></td><td><b>Summe</b></td><td></td><td style="text-align:right"><b>${esc(cent2eur(s("einnahme")))}</b></td><td style="text-align:right"><b>${esc(cent2eur(s("ausgabe")))}</b></td><td></td></tr></tfoot>` : "";
  return `<div class="v2-tab-scroll"><table class="v2-table"><thead><tr><th>Bezahlt am</th><th>Beleg</th><th>Gegenpartei</th><th>Wofür</th><th>Position (EÜR)</th><th style="text-align:right">Einnahme</th><th style="text-align:right">Ausgabe</th>${summe ? `<th style="text-align:right" title="Abweichend absetzbar: Bewirtung 70 %, Anlagen über AfA">davon absetzbar</th>` : ""}</tr></thead><tbody>${rows}</tbody>${fuss}</table></div>`;
}
async function finJournal(jahr) {
  const d = await jget("/api/finanzen/journal?jahr=" + jahr) || { zeilen: [] };
  const inhalt = d.zeilen.length ? finTabelle(d.zeilen, true) : emptyRow("Keine Zahlungen in " + jahr + ".");
  return tile("Journal " + jahr + " — alle Zahlungen nach Zahlungsdatum", inhalt + `<div class="v2-card-actions" style="margin-top:10px"><a class="v2-btn" href="/api/finanzen/journal?jahr=${jahr}&format=csv">⬇ Als CSV (Excel/Numbers)</a><small class="v2-sub">Stornierte Zahlungen bleiben sichtbar, zählen aber nicht. „→ Jahr“ = 10-Tage-Regel.</small></div>`, "w12");
}
async function finEuer(jahr) {
  const e = await jget("/api/finanzen/euer?jahr=" + jahr);
  if (!e) return emptyRow("EÜR nicht verfügbar.");
  const zeile = (name, c, fett) => `<tr><td>${fett ? "<b>" + esc(name) + "</b>" : esc(name)}</td><td style="text-align:right">${fett ? "<b>" + esc(cent2eur(c)) + "</b>" : esc(cent2eur(c))}</td></tr>`;
  const tab = `<table class="v2-table v2-fin-euer"><tbody>
    <tr><th colspan="2">Betriebseinnahmen</th></tr>${e.einnahmen.map(x => zeile(x.position, x.betrag_cent)).join("")}${zeile("Summe Betriebseinnahmen", e.einnahmen_cent, true)}
    <tr><th colspan="2">Betriebsausgaben</th></tr>${e.ausgaben.length ? e.ausgaben.map(x => zeile(x.position, x.betrag_cent)).join("") : `<tr><td colspan="2"><small>keine</small></td></tr>`}${zeile("Summe Betriebsausgaben", e.ausgaben_cent, true)}
    <tr class="v2-fin-gewinn"><td><b>${e.gewinn_cent >= 0 ? "Gewinn" : "Verlust"}</b></td><td style="text-align:right"><b>${esc(cent2eur(e.gewinn_cent))}</b></td></tr></tbody></table>`;
  return tile("Einnahmen-Überschuss-Rechnung " + jahr, tab + `<small class="v2-sub">${esc(e.hinweis)}${e.bewirtung_nicht_abziehbar_cent ? ` Nicht abziehbarer Bewirtungsanteil (30 %): ${esc(cent2eur(e.bewirtung_nicht_abziehbar_cent))}.` : ""} Stand: vorläufig, bis das Jahr abgeschlossen ist.</small>`, "w8")
    + tile("So entsteht die Zahl", `<div class="v2-sub" style="line-height:1.6">Gezählt wird, wann Geld <b>geflossen</b> ist (Zahlungsdatum), nicht das Rechnungsdatum.<br>Als Kleinunternehmer ist der <b>Bruttobetrag</b> die Ausgabe.<br>Bewirtung zählt zu 70 %.<br>Geräte über 800 € werden über die Nutzungsdauer <b>abgeschrieben</b> (Reiter „Anlagen“); Computer und Software dürfen sofort voll abgesetzt werden.</div>`, "w4");
}
async function finAnlagen(jahr) {
  const d = await jget("/api/finanzen/anlagen?jahr=" + jahr) || { anlagen: [] };
  const rows = d.anlagen.map(a => `<tr class="klick" data-act="bl-detail" data-id="${esc(a.beleg)}"><td><b>${esc(a.bezeichnung)}</b><br><small>${esc(a.beleg)} · ${esc(a.lieferant)}</small></td><td>${esc(datumDe(a.anschaffung))}</td><td style="text-align:right">${esc(cent2eur(a.ak_cent))}</td><td style="text-align:right">${a.nutzungsdauer_jahre} J.</td><td style="text-align:right">${esc(cent2eur(a.afa_jahr_cent))}</td><td style="text-align:right">${esc(cent2eur(a.restwert_cent))}</td></tr>`).join("");
  return tile("Anlageverzeichnis " + jahr, rows ? `<table class="v2-table"><thead><tr><th>Gegenstand</th><th>Angeschafft</th><th style="text-align:right">Kosten</th><th style="text-align:right">Nutzung</th><th style="text-align:right">Abschreibung ${jahr}</th><th style="text-align:right">Restwert 31.12.</th></tr></thead><tbody>${rows}</tbody></table>`
    : emptyRow("Keine Anlagegüter. Geräte über 800 € beim Buchen eines Belegs als „Anlagegut > 800 €“ mit Nutzungsdauer erfassen."), "w12");
}
function zehnTageVerdrahten(datumId, boxId) {   // 10-Tage-Regel: Auswahl nur zwischen 22.12. und 10.01.
  const el = $("#" + datumId), box = $("#" + boxId); if (!el || !box) return;
  const upd = () => { const [y, m, d] = String(el.value).split("-").map(Number); const fenster = (m === 12 && d >= 22) || (m === 1 && d <= 10);
    const n = m === 12 ? y + 1 : y - 1;
    box.innerHTML = fenster ? `<label class="v2-feld"><small>Gehört wirtschaftlich zum Jahr (10-Tage-Regel: nur regelmäßige Zahlungen wie Abos, Miete)</small><select id="${boxId}-jahr"><option value="">${y} (Jahr der Zahlung)</option><option value="${n}">${n}</option></select></label>` : ""; };
  el.addEventListener("change", upd); upd();
}
const zehnTageWert = (boxId) => { const s = $("#" + boxId + "-jahr"); return s ? s.value : ""; };
async function ebNeu(art) {
  if (!FIN_KAT) FIN_KAT = ((await jget("/api/finanzen/eigenbelege")) || {}).kategorien || { einnahme: {}, ausgabe: {} };
  const kat = Object.entries(FIN_KAT[art] || {});
  openModal(art === "einnahme" ? "Einnahme ohne eigene Rechnung" : "Ausgabe ohne Beleg", `<div class="v2-form" style="max-width:620px">
    <div class="v2-msg">${art === "einnahme" ? "Zum Beispiel Auszahlungen von YouTube, Instagram oder anderen Plattformen – Geld, für das du keine eigene Rechnung schreibst. Zählt zum Umsatz (Kleinunternehmer-Grenze)." : "Nur wenn es wirklich keinen Beleg gibt (z. B. Kontoführungsgebühr, Parkautomat). Rechnungen bitte unter „📥 Belege“ hochladen."} LUNA vergibt eine Eigenbeleg-Nummer (EB-…); korrigieren geht nur per Storno.</div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>${art === "einnahme" ? "Eingegangen am *" : "Bezahlt am *"}</small><input id="eb-datum" type="date" value="${heuteIso()}"></label>
      <label class="v2-feld"><small>Betrag (€) *</small><input id="eb-betrag" inputmode="decimal" placeholder="z. B. 250,50"></label>
      <label class="v2-feld"><small>Kategorie *</small><select id="eb-kat">${kat.length > 1 ? `<option value="">— wählen —</option>` : ""}${kat.map(([k, l]) => `<option value="${esc(k)}">${esc(l)}</option>`).join("")}</select></label></div>
    <label class="v2-feld"><small>Wofür? *</small><input id="eb-text" placeholder="${art === "einnahme" ? "z. B. YouTube-Auszahlung September" : "z. B. Kontoführungsgebühr Oktober"}"></label>
    <div class="v2-an-zeile"><label class="v2-feld"><small>${art === "einnahme" ? "Von wem" : "An wen"}</small><input id="eb-gegen" placeholder="z. B. Google Ireland Ltd."></label>
      <label class="v2-feld"><small>Referenz (Kontoauszug, Transaktions-ID)</small><input id="eb-ref"></label></div>
    <div id="eb-zuord"></div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="eb-speichern" data-val="${esc(art)}">✔ Buchen</button><button class="v2-btn" data-modal-close>Abbrechen</button></div><div id="eb-msg" class="v2-msg"></div></div>`, false);
  zehnTageVerdrahten("eb-datum", "eb-zuord");
}
async function ebSpeichern(art) {
  const buchung = { art, datum: $("#eb-datum").value, betrag: $("#eb-betrag").value.trim(), kategorie: $("#eb-kat").value, text: $("#eb-text").value.trim(),
    gegenpartei: $("#eb-gegen").value.trim(), referenz: $("#eb-ref").value.trim(), zuordnung_jahr: zehnTageWert("eb-zuord") };
  const r = await jpost("/api/finanzen/eigenbelege", { buchung });
  if (!r || !r.ok) return kundenMsg("eb-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  closeModal(); FIN_JAHR = Number(buchung.zuordnung_jahr || buchung.datum.slice(0, 4)) || FIN_JAHR;
  if (AKTIV === "finanzen") return renderFinanzen(`${r.nummer} gebucht: ${buchung.text} · ${buchung.betrag} €`);
  return go("finanzen");
}
async function ebDetail(nr, meldung, fehler) {
  const d = await jget("/api/finanzen/eigenbelege") || { eigenbelege: [], kategorien: {} };
  const x = (d.eigenbelege || []).find(e => e.nummer === nr); if (!x) return openModal(nr, emptyRow("Eigenbeleg nicht gefunden."));
  const kat = ((d.kategorien || {})[x.art] || {})[x.kategorie] || x.kategorie;
  openModal(`${nr} · ${x.art === "einnahme" ? "Einnahme" : "Ausgabe"} ohne Beleg`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}">${esc(meldung)}</div>` : ""}
    <div class="v2-kv"><span>Status</span>${x.status === "storniert" ? `<span class="v2-badge err">storniert</span>` : `<span class="v2-badge ok">gebucht</span>`}</div>
    <div class="v2-kv"><span>${x.art === "einnahme" ? "Eingegangen am" : "Bezahlt am"}</span><b>${esc(datumDe(x.datum))}${x.zuordnung_jahr ? " · zugeordnet " + esc(x.zuordnung_jahr) + " (10-Tage-Regel)" : ""}</b></div>
    <div class="v2-kv"><span>Betrag</span><b>${esc(cent2eur(x.betrag_cent))}</b></div>
    <div class="v2-kv"><span>Kategorie</span><b>${esc(kat)}</b></div>
    <div class="v2-kv"><span>Wofür</span><b>${esc(x.text)}</b></div>
    ${x.gegenpartei ? `<div class="v2-kv"><span>${x.art === "einnahme" ? "Von" : "An"}</span><b>${esc(x.gegenpartei)}</b></div>` : ""}
    ${x.referenz ? `<div class="v2-kv"><span>Referenz</span><b>${esc(x.referenz)}</b></div>` : ""}
    <div class="v2-kv"><span>Erfasst</span><b>${esc(zeit(x.angelegt))} · ${esc(x.von || "")}</b></div>
    ${x.status === "storniert" ? `<div class="v2-kv"><span>Storniert</span><b>${esc(zeit(x.storniert_am))} · ${esc(x.storno_grund)}</b></div>` : `<div class="v2-card-actions"><button class="v2-btn" data-act="eb-storno" data-id="${esc(nr)}">↶ Stornieren …</button></div>`}`);
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
  const themaOpts = ["Torjubel", "Tore & Highlights", "Beste Momente", "Fan-Stimmung", "Emotionen pur"]
    .map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join("");
  const reelForm = `<div class="v2-form">
      <select id="rl-thema">${themaOpts}</select>
      <select id="rl-modus"><option value="einzel">Einzelnes Spiel</option><option value="alle">Über alle Spiele</option></select>
      <input id="rl-spiel" placeholder="Spielordner-Name (bei Einzelspiel)">
      <div class="v2-form-row"><input id="rl-min" type="number" step="1" placeholder="Min-Länge (s)" value="15"><input id="rl-max" type="number" step="1" placeholder="Max-Länge (s)" value="45"></div>
      <button class="v2-btn pri" data-act="reel-auftrag">🎬 Reel bauen lassen</button><div id="rl-msg" class="v2-msg"></div>
      <div class="v2-sub">Der Auftrag geht in die Warteschlange; der Cutter-Rechner sucht passende Clips (nur ausreichende Qualität), schneidet ein Reel (mind. 15 s) und legt es dir unter Reels zur Freigabe vor. Pyro &amp; Fangesang folgen später.</div></div>`;
  const form = `<div class="v2-form"><input id="cut-projekt" placeholder="Ordnername in der Cutter-Inbox (z. B. hsv_stadion)"><input id="cut-note" placeholder="Notiz (optional)"><button class="v2-btn pri" data-act="cutter-job">Job anstoßen</button><div id="cut-msg" class="v2-msg"></div><div class="v2-sub">Der Cutter-Rechner holt den Job ab, schneidet den Ordner und meldet den Status zurück. Posten bleibt CEO-Tor.</div></div>`;
  $("#v2-app").innerHTML = secHead("Cutter") + `<div class="v2-grid">${tile("🎬 Manueller Reel-Auftrag", reelForm, "w6")}${tile("Reel-Job aus Ordner", form, "w6")}${tile(`Jobs & Historie (${(c.jobs || []).length})`, jobs, "w12")}</div>`;
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
const AMPEL_FARBE = { gruen: "var(--v2-green)", gelb: "var(--v2-amber)", rot: "var(--v2-red)" };
const ampelDot = (a) => `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${AMPEL_FARBE[a] || "var(--v2-line)"};margin-right:8px"></span>`;
function leistungHtml(p) {
  if (!p) return emptyRow("Leistungsbericht nicht verfügbar.");
  const w = p.woche || {}, v = p.vorwoche || {};
  const pct = (q) => q == null ? "keine Entscheidungen" : Math.round(q * 100) + " %";
  const delta = (a, b, einheit = "") => (a == null || b == null) ? "" : ` · Vorwoche ${b}${einheit} ${a > b ? "↗" : a < b ? "↘" : "→"}`;
  const zeile = (ampel, titel, text) => `<div class="v2-list-row">${ampelDot(ampel)}<div class="grow"><b>${esc(titel)}</b><small>${text}</small></div></div>`;
  const ampelLbl = { gruen: "Grün", gelb: "Gelb", rot: "Rot" };
  let h = `<div class="v2-kpi" style="margin-bottom:6px">${ampelDot(p.gesamt)} Gesamt: ${esc(ampelLbl[p.gesamt] || "keine Daten")} <span class="v2-sub" style="font-size:13px">(letzte ${p.fenster_tage} Tage vs. Vorwoche)</span></div>`;
  if (w.reels) h += zeile(p.ampeln.reel_qualitaet, "Reels — Qualität (deine Freigaben)",
    `${w.reels.erstellt} erstellt${delta(w.reels.erstellt, (v.reels || {}).erstellt)} · Freigabequote ${pct(w.reels.freigabequote)} (${w.reels.freigegeben} frei / ${w.reels.abgelehnt} abgelehnt) · ${w.reels.gepostet} gepostet · ${w.reels.fehler} Fehler`);
  if (w.antraege) h += zeile(p.ampeln.antrag_qualitaet, "Anträge — Qualität",
    `${w.antraege.eingereicht} neu${delta(w.antraege.eingereicht, (v.antraege || {}).eingereicht)} · Freigabequote ${pct(w.antraege.freigabequote)} · ${w.antraege.erledigt} erledigt`);
  if (w.cutter) h += zeile(p.ampeln.pipeline, "Cutter-Pipeline — Zuverlässigkeit",
    `${w.cutter.jobs} Jobs · Erfolg ${w.cutter.erfolgsquote == null ? "keine Jobs" : Math.round(w.cutter.erfolgsquote * 100) + " %"} (${w.cutter.done} ok / ${w.cutter.failed} Fehler)`);
  if (w.aktivitaet) h += zeile(null, "Durchsatz",
    `${w.aktivitaet.aktionen} Aktionen${delta(w.aktivitaet.aktionen, (v.aktivitaet || {}).aktionen)} · aktiv: ${Object.entries(w.aktivitaet.top_akteure || {}).slice(0, 3).map(([k, n]) => `${esc(k)} (${n})`).join(", ") || "—"}`);
  if (w.kosten) {
    const treiber = Object.entries(w.kosten.top_quellen || {}).map(([q, e2]) => `${esc(q)} ${e2.toFixed(2)} €`).join(", ");
    h += zeile(null, "Kosten (Token/API)",
      `${(w.kosten.eur).toFixed(2)} € · ${w.kosten.aufrufe} Aufrufe${delta(w.kosten.eur, (v.kosten || {}).eur, " €")}${treiber ? " · Treiber: " + treiber : ""}`);
  }
  const rz = w.reaktionszeiten || {};
  const rzTeile = [rz.cutter_h != null ? `Cutter ${rz.cutter_h.toFixed(1)} h` : null,
    rz.antrag_h != null ? `Anträge ${rz.antrag_h.toFixed(1)} h` : null,
    rz.reel_entscheidung_h != null ? `Reel-Entscheidung ${rz.reel_entscheidung_h.toFixed(1)} h` : null].filter(Boolean);
  if (rzTeile.length) h += zeile(null, "Reaktionszeiten (Median, abgeschlossene Vorgänge)", rzTeile.join(" · "));
  if (w.nutzung) {
    const topApps = Object.entries(w.nutzung.je_app || {}).slice(0, 4).map(([a, n]) => `${esc(a)} (${n})`).join(", ");
    h += zeile(null, "Nutzung (App-Öffnungen)", `${w.nutzung.oeffnungen} diese Woche${topApps ? " · meist: " + topApps : ""}`);
  }
  if (p.friedhof && p.friedhof.length) h += zeile("gelb", `Feature-Friedhof (> ${p.friedhof_tage} Tage nicht geöffnet)`, p.friedhof.map(esc).join(", "));
  h += zeile(p.ampeln.fehler, "Fehler gesamt", String(p.fehler_gesamt));
  if (p.historie && p.historie.length) {
    const rows = p.historie.map(hh => `<tr><td><b>${esc(hh.label)}</b></td><td>${hh.reels_erstellt}</td><td>${hh.freigabequote == null ? "–" : Math.round(hh.freigabequote * 100) + " %"}</td><td style="color:${hh.fehler ? "var(--v2-red)" : "var(--v2-muted)"}">${hh.fehler}</td><td>${hh.aktionen}</td><td>${(hh.kosten_eur || 0).toFixed(2)} €</td></tr>`).join("");
    h += `<div class="v2-sub" style="margin:14px 0 4px"><b>Verlauf (${p.historie.length} Wochen)</b></div><table class="v2-table"><thead><tr><th>Woche</th><th>Reels</th><th>Freigabequote</th><th>Fehler</th><th>Aktionen</th><th>Kosten</th></tr></thead><tbody>${rows}</tbody></table>`;
  }
  h += `<div class="v2-sub" style="margin-top:10px">Ampeln: Freigabequote ≥70 % grün / ≥40 % gelb · Pipeline-Erfolg ≥90 % grün / ≥70 % gelb · Fehler 0 grün / ≤2 gelb. Regelbasiert aus den Ereignis-Protokollen — kein LLM, keine Kosten. Wochenbericht kommt montags 9:00 per Telegram. Nutzung zählt nur App-Öffnungen (ts + App).</div>`;
  return h;
}
async function renderSystem() {
  const sub = SUBTAB.system || "leistung";
  STATE = await jget("/api/state") || STATE;
  let body;
  if (sub === "leistung") body = leistungHtml(await jget("/api/performance"));
  if (sub === "research") body = (STATE.research || []).map(r => `<div class="v2-list-row"><span class="v2-badge neutral">${esc(firstOf(r, ["status", "abteilung"], ""))}</span><div class="grow"><b>${esc(firstOf(r, ["frage", "titel"], ""))}</b>${r.id ? `<small>${esc(r.id)}</small>` : ""}</div></div>`).join("") || emptyRow("Keine Research-Tickets.");
  if (sub === "meldungen") body = (STATE.meldungen || []).map(m => `<div class="v2-list-row"><span class="v2-badge neutral">${esc(m.abteilung || "")}</span><div class="grow"><b>${esc(m.text)}</b><small>${esc(zeitKurz(m.ts))}</small></div></div>`).join("") || emptyRow("Keine Meldungen.");
  if (sub === "aktivitaet") body = (STATE.aktivitaet || []).map(a => `<div class="v2-list-row"><span class="v2-badge live">Live</span><div class="grow"><b>${esc(a.akteur || "")}</b> ${esc(a.aktion || "")}<small>${esc(zeitKurz(a.ts))}</small></div></div>`).join("") || emptyRow("Keine Aktivität.");
  if (sub === "finanzen") { const f = STATE.finance || {}; body = `<div class="v2-kv"><span>Monatsbudget</span><b>${esc(f.monatsbudget || "unbekannt")}</b></div><div class="v2-kv"><span>Offene Aufträge</span><b>${(STATE.antraege || []).length}</b></div><div class="v2-kv"><span>Offene Research-Tickets</span><b>${(STATE.research || []).length}</b></div>`; }
  $("#v2-app").innerHTML = secHead("System") + tabs("system", [["leistung", "Leistung"], ["research", "Research"], ["meldungen", "Meldungen"], ["aktivitaet", "Aktivität"], ["finanzen", "Finanzen"]]) + `<div class="v2-tile w12">${body}</div>`;
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
    case "an-neu": return anEditor("", id || "");
    case "an-detail": return anDetail(id);
    case "an-bearbeiten": return anEditor(id);
    case "an-pos-neu": { $("#an-pos").insertAdjacentHTML("beforeend", anPosZeile()); return anSumme(); }
    case "an-kat-neu": return anKatNeu();
    case "an-firma-wahl": return firmaWaehlen(id);
    case "kat-speichern": return katalogSpeichern();
    case "kat-neu": return katalogFormatNeu(Number(id));
    case "pl-pdf": return preislistePdf();
    case "an-pos-weg": { const z = el.closest(".v2-an-pos"); if (z) z.remove(); return anSumme(); }
    case "an-speichern": return anSpeichern(id);
    case "an-mail": { flash("⏳ erstellt…"); const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/mailentwurf`, {}); return anDetail(id, r && r.ok ? `Gmail-Entwurf an ${r.an} mit PDF angelegt — in Gmail prüfen und selbst senden. Danach hier „Als versendet markieren“.` : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "an-versendet": {
      if (!confirm("Hast du das Angebot auf anderem Weg verschickt (nicht über „Senden“)? Danach ist es nicht mehr änderbar, und die Kalender-Erinnerungen werden angelegt.")) return;
      flash("⏳ …"); const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/versendet`, {});
      if (AKTIV === "angebote") renderAngebote();
      return anDetail(id, r && r.ok ? ["Als versendet markiert.", ...(r.termine || []).map(t => `📅 ${t.titel} (${new Date(t.datum).toLocaleDateString("de-DE")})`), ...(r.hinweise || [])].join("\n") : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "bl-detail": return blDetail(id);
    case "bl-buchen": return blBuchen(id);
    case "bl-bezahlt-form": return blBezahltForm(id);
    case "bl-box-zu": { const bx = $("#bl-aktion-box"); if (bx) bx.innerHTML = ""; return; }
    case "bl-bezahlt": {
      const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(id)}/bezahlt`, { datum: $("#blz-datum").value, betrag: $("#blz-betrag").value.trim() || null, notiz: $("#blz-notiz").value.trim(), zuordnung_jahr: zehnTageWert("blz-zuord") });
      if (!r || !r.ok) return kundenMsg("blz-msg", (r && r.hinweis) || "Fehler.", false);
      if (AKTIV === "belege") renderBelege(); if (AKTIV === "finanzen") renderFinanzen();
      return blDetail(id, r.rest_cent ? `Zahlung ${cent2eur(Math.abs(r.betrag_cent))} gebucht — offen: ${cent2eur(Math.abs(r.rest_cent))}.` : "Vollständig bezahlt.");
    }
    case "bl-zahlung-storno": case "re-zahlung-storno": {
      const grund = prompt("Zahlung zurücknehmen — Grund (z. B. „falsches Datum“, „Rücklastschrift“):", ""); if (!grund) return;
      const pfad = act === "re-zahlung-storno" ? "rechnungen" : "belege";
      const r = await jpost(`/api/finanzen/${pfad}/${encodeURIComponent(id)}/zahlung-stornieren`, { index: Number(val), grund });
      if (AKTIV === "finanzen") renderFinanzen(); if (AKTIV === "belege") renderBelege(); if (AKTIV === "rechnungen") renderRechnungen();
      const ok = !!(r && r.ok), m = ok ? "Zahlung storniert — sie bleibt sichtbar, zählt aber nicht mehr." : ((r && r.hinweis) || "Fehler.");
      return act === "re-zahlung-storno" ? reDetail(id, m, !ok) : blDetail(id, m, !ok);
    }
    case "todo-oeffnen": {
      if (val.startsWith("go:")) { const [, s, t] = val.split(":"); return go(s, t); }
      return handleAct(val, el);
    }
    case "todo-erledigen": {
      el.disabled = true; const r = await jpost(val, {});
      if (!r || r.ok === false) { el.disabled = false; return alert((r && r.hinweis) || "Fehler."); }
      return renderDash();
    }
    case "eb-neu": return ebNeu(val);
    case "eb-speichern": return ebSpeichern(val);
    case "eb-detail": return ebDetail(id);
    case "eb-storno": {
      const grund = prompt("Eigenbeleg stornieren — Grund:", ""); if (!grund) return;
      const r = await jpost(`/api/finanzen/eigenbelege/${encodeURIComponent(id)}/stornieren`, { grund });
      if (AKTIV === "finanzen") renderFinanzen();
      return ebDetail(id, r && r.ok ? "Storniert — bleibt im Journal sichtbar, zählt aber nicht." : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "bl-verwerfen": { const grund = prompt("Warum ist das kein Beleg? (z. B. versehentlich hochgeladen)", ""); if (!grund) return; const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(id)}/verwerfen`, { grund }); if (AKTIV === "belege") renderBelege(); return blDetail(id, r && r.ok ? "Verworfen — die Datei bleibt archiviert." : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "re-neu": return reEditor("");
    case "re-detail": return reDetail(id);
    case "re-bearbeiten": return reEditor(id);
    case "re-speichern": return reSpeichern(id);
    case "re-verwerfen": { if (!confirm("Entwurf verwerfen? (Er hatte noch keine Nummer.)")) return; const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/verwerfen`, {}); closeModal(); return AKTIV === "rechnungen" ? renderRechnungen() : null; }
    case "re-festschreiben": {
      if (!confirm("Rechnung festschreiben?\n\nSie bekommt jetzt ihre Rechnungsnummer und ist danach NICHT mehr änderbar (Korrektur nur per Storno).")) return;
      flash("⏳ …"); const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/festschreiben`, { bestaetigt: true });
      if (AKTIV === "rechnungen") renderRechnungen();
      if (!r || !r.ok) return reDetail(id, (r && r.hinweis) || "Fehler.", true);
      return reDetail(r.nummer, [`${r.nummer} festgeschrieben — fällig am ${datumDe(r.faellig_am)}.`, ...(r.hinweise || [])].join("\n"));
    }
    case "re-senden": return reSendenVorschau(id);
    case "re-senden-jetzt": {
      const an = $("#res-an").value.trim(); if (!an.includes("@")) return kundenMsg("res-msg", "Bitte eine gültige Empfänger-Adresse eintragen.", false);
      if (!confirm(`${id} jetzt an ${an} senden?`)) return;
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/senden`, { an, betreff: $("#res-betreff").value.trim(), text: $("#res-text").value.trim(), bestaetigt: true });
      if (!r || !r.ok) return kundenMsg("res-msg", (r && r.hinweis) || "Senden fehlgeschlagen.", false);
      if (AKTIV === "rechnungen") renderRechnungen(); return reDetail(id, `An ${r.an} gesendet.`);
    }
    case "re-bezahlt-form": return reBezahltForm(id);
    case "re-bezahlt": {
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/bezahlt`, { datum: $("#rez-datum").value, betrag: $("#rez-betrag").value.trim() || null, notiz: $("#rez-notiz").value.trim(), zuordnung_jahr: zehnTageWert("rez-zuord") });
      if (!r || !r.ok) return kundenMsg("rez-msg", (r && r.hinweis) || "Fehler.", false);
      if (AKTIV === "rechnungen") renderRechnungen(); return reDetail(id, [r.rest_cent > 0 ? `Zahlung ${cent2eur(r.betrag_cent)} gebucht — offen: ${cent2eur(r.rest_cent)}.` : "Vollständig bezahlt.", ...(r.hinweise || [])].join("\n"));
    }
    case "re-storno": {
      const grund = prompt("Stornieren — Grund (erscheint auf der Stornorechnung):", ""); if (!grund) return;
      const korrektur = confirm("Direkt einen Korrektur-Entwurf mit denselben Positionen anlegen?");
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/stornieren`, { grund, korrektur });
      if (AKTIV === "rechnungen") renderRechnungen();
      if (!r || !r.ok) return reDetail(id, (r && r.hinweis) || "Fehler.", true);
      return r.korrektur_entwurf ? reEditor(r.korrektur_entwurf) : reDetail(r.storno, [`Stornorechnung ${r.storno} erstellt.`, ...(r.hinweise || [])].join("\n"));
    }
    case "re-box-zu": { const bx = $("#re-aktion-box"); if (bx) bx.innerHTML = ""; return; }
    case "ab-rechnung": { const r = await jpost(`/api/finanzen/rechnungen/aus-auftrag/${encodeURIComponent(id)}`, {}); if (!r || !r.ok) return abDetail(id, (r && r.hinweis) || "Fehler.", true); return reEditor(r.entwurf_id); }
    case "ab-neu": return abNeu(id, val === "annehmen");
    case "ab-anlegen": return abAnlegen(id, val === "annehmen");
    case "ab-detail": return abDetail(id);
    case "ab-senden": return abSendenVorschau(id);
    case "ab-senden-jetzt": return abSendenJetzt(id);
    case "ab-senden-abbruch": { const bx = $("#ab-senden-box"); if (bx) bx.innerHTML = ""; return; }
    case "ab-speichern": { const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}`, { auftrag: { leistung_von: $("#abe-von").value, leistung_bis: $("#abe-bis").value, notiz: $("#abe-notiz").value.trim() } }); if (!r || !r.ok) return kundenMsg("abe-msg", (r && r.hinweis) || "Fehler.", false); return abDetail(id, r.geaendert && r.geaendert.length ? "Gespeichert." : "Keine Änderung."); }
    case "ab-status": {
      const grund = prompt(val === "erledigt" ? "Erledigt — Notiz (optional):" : "Stornieren — Grund:", ""); if (grund === null) return;
      const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}/status`, { status: val, grund });
      if (AKTIV === "angebote") renderAngebote();
      return abDetail(id, r && r.ok ? (val === "erledigt" ? "Als erledigt markiert — bereit für die Rechnung." : "Storniert.") : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "an-senden": return anSendenVorschau(id);
    case "an-senden-jetzt": return anSendenJetzt(id);
    case "an-senden-abbruch": { const bx = $("#an-senden-box"); if (bx) bx.innerHTML = ""; return; }
    case "an-erinnerungen": {
      flash("⏳ …"); const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/erinnerungen`, {});
      return anDetail(id, r && r.ok ? [...(r.termine || []).map(t => `📅 ${t.titel} (${new Date(t.datum).toLocaleDateString("de-DE")})`), ...(r.hinweise || [])].join("\n") || "Erledigt." : ((r && r.hinweis) || "Fehler."), !(r && r.ok) || !(r.termine || []).length && (r.hinweise || []).some(h => h.startsWith("Kalender") || h.startsWith("Google")));
    }
    case "an-status": {
      const grund = prompt(val === "angenommen" ? "Angenommen — Notiz (optional, z. B. „per Mail vom …“):" : "Abgelehnt — Grund (optional):", ""); if (grund === null) return;
      const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/status`, { status: val, grund });
      if (AKTIV === "angebote") renderAngebote();
      return anDetail(id, r && r.ok ? [val === "angenommen" ? "Angenommen." : "Abgelehnt.", ...(r.hinweise || [])].join("\n") : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "kunde-neu": return kundeNeu(id || "");
    case "kunde-anlegen": return kundeAnlegen(id || "");
    case "kunde-detail": return kundeDetail(id);
    case "kunde-speichern": return kundeSpeichern(id);
    case "kunde-ap-neu": return kundeApForm(id, null);
    case "kunde-ap-edit": { const d = await jget("/api/crm/kunden/" + encodeURIComponent(val)); const ap = d && d.firma && (d.firma.ansprechpartner_liste || []).find(a => a.nummer === id); return kundeApForm(val, ap); }
    case "kunde-ap-speichern": return kundeApSpeichern(id, val);
    case "kunde-collab-zu": return kundeCollabZu(id);
    case "kunde-collab-ok": { const nr = ($("#kcz-nr") || {}).value; const r = await jpost(`/api/crm/kunden/${encodeURIComponent(nr)}/collab`, { collab: id }); if (!r || !r.ok) return kundenMsg("kcz-msg", (r && r.hinweis) || "Fehler.", false); await renderKunden(); return kundeDetail(nr, `${id} verknüpft.`); }
    case "kunde-collab-los": { if (!confirm(`Verknüpfung mit „${val}“ lösen? (Der Verlauf bleibt erhalten.)`)) return; await jpost(`/api/crm/kunden/${encodeURIComponent(id)}/collab`, { collab: val, loesen: true }); await renderKunden(); return kundeDetail(id, "Verknüpfung gelöst."); }
    case "reel-freigeben": { const t = (($(`#cap-${id}`) || {}).value || "").trim(); flash("⏳ …"); await jpost(`/api/reel/${id}/freigeben`, { caption: t }); return renderReels(); }
    case "reel-ablehnen": {
      if (!confirm("Reel ablehnen? Es wird nicht gepostet.")) return;
      const neu = confirm("Soll direkt ein NEUES Reel gebaut werden (gleiches Thema/Spiel)?");
      const r = await jpost(`/api/reel/${id}/ablehnen`, { neu });
      if (neu) flash(r && r.neu_job ? "Abgelehnt — Ersatz angefordert." : "Abgelehnt (Ersatz nicht möglich).");
      return renderReels();
    }
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
    case "reel-auftrag": {
      const thema = ($("#rl-thema") || {}).value || "", alle = (($("#rl-modus") || {}).value === "alle");
      const spiel = (($("#rl-spiel") || {}).value || "").trim(), msg = $("#rl-msg");
      if (!alle && !spiel) { if (msg) { msg.textContent = "Spielordner-Namen angeben oder Über alle Spiele wählen."; msg.className = "v2-msg err"; } return; }
      const r = await jpost("/api/cutter/reel", { thema, alle_spiele: alle, spiel, min_dauer: ($("#rl-min") || {}).value || 15, max_dauer: ($("#rl-max") || {}).value || 45 });
      if (msg) { const ok = r && r.ok; msg.textContent = ok ? "Auftrag in der Warteschlange — der Cutter-Rechner baut das Reel." : "Fehler: " + ((r && (r.hinweis || r.fehler)) || "unbekannt"); msg.className = "v2-msg " + (ok ? "ok" : "err"); }
      if (r && r.ok) renderCutter(); return;
    }
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
  const at = $("#an-firma-treffer"); if (at && !at.hidden && !e.target.closest(".v2-auto-feld")) at.hidden = true;
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
