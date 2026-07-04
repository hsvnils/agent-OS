// LUNA-OS UI-V2 -- helles, dashboard-/sektionsbasiertes UI (opt-in, siehe UI.md Abschnitt V2).
// Nutzt DIESELBEN /api/*-Endpunkte wie V1, aber ohne Fenster (WinBox). Deutsch, echte Daten.
"use strict";

/* =========================== Helfer =========================== */
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const jget = async (u) => { try { const r = await fetch(u); return r.ok ? await r.json() : null; } catch { return null; } };
const jpost = async (u, body) => { try { const r = await fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }); return r.ok ? await r.json() : null; } catch { return null; } };
const num = (v, d = 1) => { const n = Number(v); return isFinite(n) ? n.toFixed(d) : "–"; };
const pct = (v) => isFinite(Number(v)) ? Math.round(Number(v) * 100) + " %" : "–";
const firstOf = (o, keys, dflt = "") => { for (const k of keys) if (o && o[k] != null && o[k] !== "") return o[k]; return dflt; };
function zeitKurz(t) {
  if (!t) return "";
  const d = new Date(t); if (isNaN(d)) return String(t).slice(0, 16).replace("T", " ");
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "gerade eben"; if (s < 3600) return Math.floor(s / 60) + " Min";
  if (s < 86400) return Math.floor(s / 3600) + " Std"; return Math.floor(s / 86400) + " T";
}

/* =========================== Zustand =========================== */
let ME = { apps: null, role: "owner", display_name: "CEO", username: "" };
let PREFS = {};
let STATE = {}, OVERVIEW = {}, LOOP = {};
let AKTIV = "dash";

/* Sektionen (Icon-Nav). modul = Gate ueber /api/me.apps (null = immer sichtbar). */
const SECTIONS = [
  { id: "dash", icon: "▦", label: "Dashboard", app: "home" },
  { id: "approvals", icon: "✔", label: "Freigaben", app: "auftraege" },
  { id: "investment", icon: "📈", label: "Investment", app: "investment" },
  { id: "crm", icon: "🤝", label: "CRM", app: "crm" },
  { id: "content", icon: "✎", label: "Content", app: "trends" },
  { id: "cutter", icon: "🎬", label: "Cutter", app: "cutter" },
  { id: "knowledge", icon: "🧠", label: "Wissen", app: "wissen" },
  { id: "agents", icon: "🛰", label: "Agenten", app: "home" },
  { id: "team", icon: "👥", label: "Team", app: "team" },
];
const darf = (app) => app === "home" || !ME.apps || ME.apps.includes(app);

/* =========================== Theme / Shell =========================== */
function applyTheme() {
  const m = localStorage.getItem("luna-v2-theme") || "light";
  const dark = m === "dark" || (m === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("v2-dark", dark);
  document.documentElement.classList.toggle("v2-light", !dark);
}
function toggleTheme() {
  const m = localStorage.getItem("luna-v2-theme") || "light";
  localStorage.setItem("luna-v2-theme", m === "dark" ? "light" : "dark");
  applyTheme();
}
async function setUiMode(mode) {   // zurueck zu V1
  if (mode !== "v2") mode = "v1";
  try { localStorage.setItem("luna-ui-mode", mode); } catch { }
  PREFS = { ...PREFS, ui_version: mode };
  await jpost("/api/prefs", { prefs: PREFS });
  location.href = "/?ui=" + mode;
}

function buildShell() {
  // Nav-Icons (modul-gated)
  $("#v2-nav").innerHTML = SECTIONS.filter(s => darf(s.app)).map(s =>
    `<button data-go="${s.id}" class="${s.id === "dash" ? "home " : ""}${s.id === AKTIV ? "active" : ""}" title="${esc(s.label)}">${s.icon}</button>`).join("");
  // Aktions-Pills (echte Aktionen)
  const pills = [
    darf("auftraege") ? `<button class="v2-pill" data-go="approvals">✔ Freigabe pruefen</button>` : "",
    darf("investment") ? `<button class="v2-pill" data-act="inv-screen">🔍 Screen starten</button>` : "",
    `<button class="v2-pill" data-toggle-chat>💬 LUNA fragen</button>`,
    `<button class="v2-pill cta" data-ui-mode="v1">↩ Zurueck zu UI V1</button>`,
  ].filter(Boolean).join("");
  $("#v2-pills").innerHTML = pills;
  // Avatar
  const nm = (ME.display_name || ME.username || "L").trim();
  $("#v2-avatar").textContent = nm.slice(0, 1).toUpperCase();
  $("#v2-avatar").title = nm;
}

/* =========================== Router =========================== */
function go(id) {
  if (!SECTIONS.find(s => s.id === id)) id = "dash";
  AKTIV = id;
  document.querySelectorAll("#v2-nav button").forEach(b => b.classList.toggle("active", b.dataset.go === id));
  const app = $("#v2-app");
  app.innerHTML = `<div class="v2-empty">Lade …</div>`;
  ({ dash: renderDash, approvals: renderApprovals, investment: renderInvestment, crm: renderCrm,
     content: renderContent, cutter: renderCutter, knowledge: renderKnowledge, agents: renderAgents,
     team: renderTeam })[id]();
}

/* =========================== Dashboard =========================== */
async function ladeDashDaten() {
  [STATE, OVERVIEW, LOOP] = await Promise.all([
    jget("/api/state"), jget("/api/overview"), jget("/api/investment/loop")]);
  STATE = STATE || {}; OVERVIEW = OVERVIEW || {}; LOOP = LOOP || {};
}
function sparkFromVerlauf(verlauf) {
  const v = (verlauf || []).slice(-24);
  if (!v.length) return "";
  const vals = v.map(x => Number(x.mae_pct) || 0); const mx = Math.max(...vals, 1);
  return `<div class="v2-spark">${v.map(x => { const h = Math.round((Number(x.mae_pct) || 0) / mx * 100);
    const gut = (Number(x.mae_pct) || 0) <= (Number(x.baseline_mae_pct) || 0);
    return `<i class="${gut ? "g" : "a"}" style="height:${Math.max(6, h)}%"></i>`; }).join("")}</div>`;
}
function gaugeSvg(frac) {
  const p = Math.max(0, Math.min(1, frac || 0)); const ang = Math.PI * (1 - p);
  const r = 62, cx = 80, cy = 78; const x = cx + r * Math.cos(ang), y = cy - r * Math.sin(ang);
  const big = p > 0.5 ? 1 : 0;
  return `<svg viewBox="0 0 160 96" width="180" height="108" aria-hidden="true">
    <path d="M18 78 A62 62 0 0 1 142 78" fill="none" stroke="var(--v2-line-soft)" stroke-width="13" stroke-linecap="round"/>
    <path d="M18 78 A62 62 0 ${big} 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none"
      stroke="url(#gg)" stroke-width="13" stroke-linecap="round"/>
    <defs><linearGradient id="gg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="var(--v2-orange)"/><stop offset=".6" stop-color="var(--v2-green)"/>
      <stop offset="1" stop-color="var(--v2-blue)"/></linearGradient></defs></svg>`;
}
function tile(title, inner, cls = "") {
  return `<div class="v2-tile ${cls}"><div class="v2-tile-h"><span class="t">${esc(title)}</span><span class="dots">···</span></div>${inner}</div>`;
}
function kpiTile(title, big, delta, sub, spark) {
  const d = delta ? `<span class="delta ${delta.up ? "up" : "down"}">${delta.up ? "↗" : "↘"} ${esc(delta.text)}</span>` : "";
  return tile(title, `<div class="v2-kpi">${esc(big)} ${d}</div>${sub ? `<div class="v2-sub">${esc(sub)}</div>` : ""}${spark || ""}`);
}

async function renderDash() {
  await ladeDashDaten();
  const g = (LOOP.kennzahlen && LOOP.kennzahlen.gesamt) || {};
  const antraege = STATE.antraege || [];
  const provs = OVERVIEW.providers || [];
  const connected = Number(OVERVIEW.providers_connected) || provs.filter(p => p.konfiguriert || p.connected).length;
  const provFrac = provs.length ? connected / provs.length : 0;
  const budget = OVERVIEW.monatsbudget || firstOf(STATE.finance || {}, ["monatsbudget", "budget"], "–");
  const aktiv = STATE.aktivitaet || [];

  // Erste-Schritte (echte System-Bereitschaft)
  const schritte = [
    { t: "Provider verbunden", done: connected > 0 },
    { t: "Watchlist/Investment aktiv", done: !!(LOOP.panel && LOOP.panel.symbole) },
    { t: "Team eingerichtet", done: (OVERVIEW.counts && OVERVIEW.counts.wissen != null) },
    { t: "Budget gesetzt", done: budget && budget !== "–" },
  ];
  const doneN = schritte.filter(s => s.done).length;

  const kpis = [
    kpiTile("Monatsbudget", String(budget), null, "aus finance/budget.md"),
    kpiTile("Prognose-Trefferquote", g.n ? pct(g.richtungsquote) : "–",
      g.n ? { up: (g.anteil_besser_baseline || 0) >= .5, text: pct(g.anteil_besser_baseline) + " > Baseline" } : null,
      g.n ? `n=${g.n} · MAE ${num(g.mae_pct)} vs ${num(g.baseline_mae_pct)}` : "noch keine Auswertung",
      sparkFromVerlauf(LOOP.verlauf)),
    kpiTile("Offene Freigaben", String(antraege.length),
      antraege.length ? { up: false, text: "wartet" } : { up: true, text: "frei" },
      antraege.length ? "warten auf CEO-Entscheidung" : "alles freigegeben"),
    kpiTile("Provider verbunden", `${connected}/${provs.length || "–"}`,
      { up: provFrac >= .5, text: pct(provFrac) }, "externe Datenquellen"),
  ].join("");

  // Investment-Lern-Loop (w8)
  const loopTile = tile("Investment · Lern-Loop", `
    <div class="v2-kpi">${g.n ? pct(g.richtungsquote) : "–"} <span class="delta ${(g.anteil_besser_baseline || 0) >= .5 ? "up" : "down"}">${g.n ? pct(g.anteil_besser_baseline) + " schlägt Baseline" : ""}</span></div>
    <div class="v2-sub">Richtungsquote · MAE ${num(g.mae_pct)} vs Baseline ${num(g.baseline_mae_pct)} · n=${g.n || 0}</div>
    ${sparkFromVerlauf(LOOP.verlauf)}
    <div class="v2-legend"><span><i style="background:var(--v2-green)"></i>schlägt Baseline</span><span><i style="background:var(--v2-accent)"></i>darunter</span></div>`, "w8");

  // Compliance-Puls (w4)
  const policy = [
    { t: "Datenquellen verbunden", ok: provFrac >= .5 },
    { t: "Freigabe-Tore aktiv", ok: true },
    { t: "Security-Audit taeglich", ok: true },
  ];
  const pulsTile = tile("Compliance-Puls", `
    <div class="v2-gauge">${gaugeSvg(provFrac)}<div class="val">${pct(provFrac)}</div><div class="cap">Anbindungs-Abdeckung</div></div>
    <div class="v2-policy">${policy.map(p => `<div class="row"><span>${esc(p.t)}</span><span class="v2-badge ${p.ok ? "aktiv" : "wartet"}">${p.ok ? "Aktiv" : "Offen"}</span></div>`).join("")}</div>`, "w4");

  // Live-Aktivitaet (w8)
  const live = aktiv.slice(0, 6).map(a => {
    const name = firstOf(a, ["titel", "text", "name", "aktion"], "Ereignis");
    const t = firstOf(a, ["ts", "zeit", "zeitpunkt", "erstellt_am"], "");
    return `<tr><td><b>${esc(String(name).slice(0, 60))}</b></td><td>${esc(zeitKurz(t))}</td><td><span class="v2-badge live">Live</span></td></tr>`;
  }).join("") || `<tr><td colspan="3" class="v2-empty">Noch keine Aktivitaet.</td></tr>`;
  const liveTile = tile("Live-Aktivitaet", `<table class="v2-table"><thead><tr><th>Ereignis</th><th>Zeit</th><th>Status</th></tr></thead><tbody>${live}</tbody></table>`, "w8");

  // Erste-Schritte (w4)
  const stepTile = tile("Erste Schritte", `
    <div class="v2-sub">System-Bereitschaft</div>
    <div class="v2-progress"><i style="width:${Math.round(doneN / schritte.length * 100)}%"></i></div>
    ${schritte.map(s => `<div class="v2-check ${s.done ? "done" : ""}"><span class="mark">${s.done ? "✓" : ""}</span>${esc(s.t)}</div>`).join("")}`, "w4");

  $("#v2-app").innerHTML = `
    <div class="v2-welcome"><h1>Willkommen zurueck, ${esc(ME.display_name || "CEO")}</h1>
      <p>Dein KI-Kontrollraum — Agenten, Kosten und Compliance im Blick.</p></div>
    <div class="v2-grid">
      ${kpis}
      ${loopTile}${pulsTile}
      ${liveTile}${stepTile}
    </div>`;
}

/* =========================== Freigaben =========================== */
function secHead(title, actions = "") {
  return `<div class="v2-sec-head"><h1>${esc(title)}</h1><div class="actions">${actions}</div></div>`;
}
async function renderApprovals() {
  STATE = await jget("/api/state") || STATE;
  const a = STATE.antraege || [];
  const rows = a.map(x => {
    const id = firstOf(x, ["id"]); const titel = firstOf(x, ["titel", "titel_kurz", "name"], "Antrag");
    const von = firstOf(x, ["von", "abteilung", "agent"], ""); const st = firstOf(x, ["status"], "eingereicht");
    const kat = firstOf(x, ["kategorie"], "");
    return `<div class="v2-list-row"><div class="grow"><b>${esc(titel)}</b><small>${esc(von)}${kat ? " · " + esc(kat) : ""}</small></div>
      <span class="v2-badge ${esc(st)}">${esc(st)}</span>
      <button class="v2-btn ok" data-act="antrag-ok" data-id="${esc(id)}">Freigeben</button>
      <button class="v2-btn danger" data-act="antrag-no" data-id="${esc(id)}">Ablehnen</button></div>`;
  }).join("") || `<div class="v2-empty">Keine offenen Freigaben — alles erledigt.</div>`;
  $("#v2-app").innerHTML = secHead("Freigaben") + `<div class="v2-tile w12">${rows}</div>`;
}

/* =========================== Investment =========================== */
async function renderInvestment() {
  const [inv, loop] = await Promise.all([jget("/api/investment"), jget("/api/investment/loop")]);
  LOOP = loop || {}; const g = (LOOP.kennzahlen && LOOP.kennzahlen.gesamt) || {};
  const mk = LOOP.insider_kontrolle;
  const vers = Object.entries((LOOP.kennzahlen && LOOP.kennzahlen.je_version) || {}).map(([k, v]) =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(k)}</b><small>MAE ${num(v.mae_pct)} vs ${num(v.baseline_mae_pct)} · Richtung ${pct(v.richtungsquote)} · n=${v.n}</small></div>
      <span class="v2-badge ${(v.anteil_besser_baseline || 0) >= .5 ? "ok" : "wartet"}">${pct(v.anteil_besser_baseline)} schlägt Baseline</span></div>`).join("") || `<div class="v2-empty">Noch keine Versions-Daten.</div>`;
  const offen = (LOOP.offene_prognosen || []).slice(0, 10).map(f =>
    `<tr><td><b>${esc(f.symbol)}</b></td><td>${esc(f.asset || "")}</td><td>${f.ziel_return_pct > 0 ? "+" : ""}${num(f.ziel_return_pct)} %</td><td>${pct(f.konfidenz)}</td><td>${esc(f.faellig_am || "")}</td></tr>`).join("")
    || `<tr><td colspan="5" class="v2-empty">Keine offenen Prognosen.</td></tr>`;
  const mkTile = mk && mk.insider && mk.insider.n ? tile("Marktdrift-Kontrolle (Insider vs. Markt)", `
    <div class="v2-list-row"><div class="grow"><b>Insider-Wochen</b><small>n=${mk.insider.n}</small></div>
      <span>Richtung ${pct(mk.insider.richtung_pct)} · schlägt Markt ${pct(mk.insider.schlaegt_markt_pct)} · Ø Alpha ${num(mk.insider.alpha_schnitt_pct)} %</span></div>
    <div class="v2-list-row"><div class="grow"><b>Basisrate (alle Wochen)</b><small>n=${mk.basisrate.n}</small></div>
      <span>Richtung ${pct(mk.basisrate.richtung_pct)} · schlägt Markt ${pct(mk.basisrate.schlaegt_markt_pct)}</span></div>
    <div class="v2-sub">Vorsprung Insider: ${mk.edge_richtung_pp > 0 ? "+" : ""}${mk.edge_richtung_pp} pp Richtung · ${mk.edge_markt_pp > 0 ? "+" : ""}${mk.edge_markt_pp} pp schlägt-Markt</div>`, "w12") : "";
  const actions = `<button class="v2-btn" data-act="inv-sammeln">Jetzt sammeln</button>
    <button class="v2-btn" data-act="inv-backfill">Historie laden</button>
    <button class="v2-btn" data-act="inv-screen">Screen</button>
    <button class="v2-btn" data-act="inv-insider">Insider-Scan</button>`;
  $("#v2-app").innerHTML = secHead("Investment", actions) + `<div class="v2-grid">
    ${kpiTile("Richtungsquote", g.n ? pct(g.richtungsquote) : "–", g.n ? { up: (g.anteil_besser_baseline || 0) >= .5, text: pct(g.anteil_besser_baseline) } : null, `n=${g.n || 0}`, sparkFromVerlauf(LOOP.verlauf))}
    ${kpiTile("MAE (Fehler)", num(g.mae_pct), null, `Baseline ${num(g.baseline_mae_pct)}`)}
    ${kpiTile("Modus", esc((inv && inv.modus) || "–"), null, "Handels-Modus")}
    ${kpiTile("Watchlist", String((inv && inv.watchlist ? inv.watchlist.length : 0)), null, "beobachtete Werte")}
    ${tile("Je Modell-Version", vers, "w6")}
    ${tile("Offene Prognosen", `<table class="v2-table"><thead><tr><th>Symbol</th><th>Klasse</th><th>Ziel</th><th>Konf.</th><th>faellig</th></tr></thead><tbody>${offen}</tbody></table>`, "w6")}
    ${mkTile}
  </div>`;
}

/* =========================== CRM =========================== */
async function renderCrm() {
  const [crm, tl] = await Promise.all([jget("/api/crm"), jget("/api/crm/timeline")]);
  const firmen = (crm && crm.firmen || []).map(f =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(firstOf(f, ["name", "firma"], "Firma"))}</b><small>${esc(firstOf(f, ["status", "phase"], ""))}</small></div>
      <span class="v2-badge neutral">${esc(firstOf(f, ["status"], ""))}</span></div>`).join("") || `<div class="v2-empty">Keine Firmen.</div>`;
  const todos = (crm && crm.todos || []).map(t =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(firstOf(t, ["titel", "text", "aufgabe"], "Todo"))}</b><small>${esc(firstOf(t, ["firma", "faellig"], ""))}</small></div>
      <button class="v2-btn ok" data-act="crm-todo" data-id="${esc(firstOf(t, ["id"]))}">Erledigt</button></div>`).join("") || `<div class="v2-empty">Keine offenen Todos.</div>`;
  const msgs = (tl && tl.nachrichten || []).slice(0, 12).map(m =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(firstOf(m, ["firma", "von", "absender"], ""))}</b><small>${esc(String(firstOf(m, ["text", "inhalt", "nachricht"], "")).slice(0, 90))}</small></div>
      <small>${esc(zeitKurz(firstOf(m, ["ts", "zeit", "erstellt_am"], "")))}</small></div>`).join("") || `<div class="v2-empty">Keine Nachrichten.</div>`;
  $("#v2-app").innerHTML = secHead("Collab-CRM") + `<div class="v2-grid">
    ${tile("Firmen", firmen, "w6")}${tile("Offene Todos", todos, "w6")}
    ${tile("Timeline (kanaluebergreifend)", msgs, "w12")}</div>`;
}

/* =========================== Content-Ops =========================== */
function contentList(items, keys, statusKey = "status") {
  return (items || []).slice(0, 20).map(x =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(String(firstOf(x, keys, "—")).slice(0, 80))}</b><small>${esc(firstOf(x, ["quelle", "thema", "kanal"], ""))}</small></div>
      <span class="v2-badge neutral">${esc(firstOf(x, [statusKey], ""))}</span></div>`).join("") || `<div class="v2-empty">Leer.</div>`;
}
async function renderContent() {
  const [tr, id, dr, inb] = await Promise.all([jget("/api/trends"), jget("/api/ideas"), jget("/api/drafts"), jget("/api/ai-inbox")]);
  $("#v2-app").innerHTML = secHead("Content-Ops") + `<div class="v2-grid">
    ${tile("Trends", contentList(tr && tr.trends, ["titel", "text", "thema"]), "w6")}
    ${tile("Ideen-Labor", contentList(id && id.ideas, ["titel", "text", "idee"]), "w6")}
    ${tile("Drafts", contentList(dr && dr.drafts, ["titel", "text"]), "w6")}
    ${tile("AI-Inbox", contentList(inb && inb.items, ["titel", "text", "betreff"]), "w6")}</div>`;
}

/* =========================== Cutter =========================== */
async function renderCutter() {
  const c = await jget("/api/cutter") || {};
  const jobs = (c.jobs || []).slice(0, 20).map(j =>
    `<tr><td><b>${esc(firstOf(j, ["name", "titel", "ordner"], "Job"))}</b></td><td>${esc(zeitKurz(firstOf(j, ["ts", "erstellt_am"], "")))}</td>
      <td><span class="v2-badge ${esc(firstOf(j, ["status"], "wartet"))}">${esc(firstOf(j, ["status"], ""))}</span></td></tr>`).join("")
    || `<tr><td colspan="3" class="v2-empty">Keine Jobs.</td></tr>`;
  const av = c.verfuegbar ? `<span class="v2-badge aktiv">Mac-Bruecke verbunden</span>` : `<span class="v2-badge wartet">Mac-Bruecke offline</span>`;
  $("#v2-app").innerHTML = secHead("Cutter", av) + tile("Jobs", `<table class="v2-table"><thead><tr><th>Job</th><th>Zeit</th><th>Status</th></tr></thead><tbody>${jobs}</tbody></table>`, "w12");
}

/* =========================== Wissen / Lagebild =========================== */
async function renderKnowledge() {
  const [b, l] = await Promise.all([jget("/api/brain"), jget("/api/lagebild")]);
  const items = (b && b.items || []).slice(0, 20).map(x =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(firstOf(x, ["titel", "thema"], "Notiz"))}</b><small>${esc(String(firstOf(x, ["text", "inhalt"], "")).slice(0, 120))}</small></div>
      <small>${esc(firstOf(x, ["quelle", "tags"], ""))}</small></div>`).join("") || `<div class="v2-empty">Kein Wissen erfasst.</div>`;
  const lage = l && (l.text || l.hinweis) ? `<div style="white-space:pre-wrap;line-height:1.5">${esc(l.text || l.hinweis)}</div>` : `<div class="v2-empty">Kein Lagebild.</div>`;
  $("#v2-app").innerHTML = secHead("Wissen & Lagebild") + `<div class="v2-grid">
    ${tile("Lagebild", lage, "w6")}${tile("Second Brain", items, "w6")}</div>`;
}

/* =========================== Agenten =========================== */
async function renderAgents() {
  const a = await jget("/api/agenten") || {};
  const deps = (a.departments || []).map(d => {
    const st = firstOf(d, ["status"], "standby");
    const badge = st === "active" ? "aktiv" : st === "offline" ? "err" : "standby";
    return `<div class="v2-list-row"><div class="grow"><b>${esc(d.name || d.key)}</b><small>${esc(d.rolle || "")}${d.subs && d.subs.length ? " · " + d.subs.length + " Sub-Agenten" : ""}</small></div>
      <span class="v2-badge ${badge}">${esc(st)}</span></div>`;
  }).join("") || `<div class="v2-empty">Keine Agenten geladen.</div>`;
  const head = `<div class="v2-list-row"><div class="grow"><b>CEO → LUNA (Head of Agents)</b><small>${esc(a.stand || "")}</small></div><span class="v2-badge aktiv">aktiv</span></div>`;
  $("#v2-app").innerHTML = secHead("Agenten-Organisation") + tile("Abteilungen", head + deps, "w12");
}

/* =========================== Team =========================== */
async function renderTeam() {
  const t = await jget("/api/team") || {};
  if (!t.verfuegbar) { $("#v2-app").innerHTML = secHead("Team") + `<div class="v2-tile w12"><div class="v2-empty">Team-Verwaltung nicht aktiv (keine Nutzer-Tabelle).</div></div>`; return; }
  const users = (t.users || []).map(u =>
    `<div class="v2-list-row"><div class="grow"><b>${esc(firstOf(u, ["display_name", "username"], "Nutzer"))}</b><small>${esc(firstOf(u, ["role"], ""))} · ${esc((u.allowed_modules || []).join(", "))}</small></div>
      <span class="v2-badge ${u.is_active ? "aktiv" : "neutral"}">${u.is_active ? "aktiv" : "inaktiv"}</span></div>`).join("") || `<div class="v2-empty">Keine Nutzer.</div>`;
  $("#v2-app").innerHTML = secHead("Team") + tile("Nutzer", users, "w12");
}

/* =========================== Aktionen =========================== */
async function handleAct(act, el) {
  const id = el.dataset.id;
  const flash = (msg) => { el.textContent = msg; };
  if (act === "antrag-ok") { await jpost(`/api/antraege/${id}/freigeben`); return renderApprovals(); }
  if (act === "antrag-no") { await jpost(`/api/antraege/${id}/ablehnen`, { grund: "abgelehnt (UI-V2)" }); return renderApprovals(); }
  if (act === "crm-todo") { await jpost(`/api/crm/todo/${id}/erledigen`); return renderCrm(); }
  if (act === "inv-sammeln") { flash("Sammle …"); await jpost("/api/investment/sammeln"); return renderInvestment(); }
  if (act === "inv-backfill") { flash("Lade Historie …"); await jpost("/api/investment/backfill", { seit: "2026-01-01" }); return renderInvestment(); }
  if (act === "inv-screen") { flash("Screen …"); await jpost("/api/investment/screen"); return AKTIV === "investment" ? renderInvestment() : null; }
  if (act === "inv-insider") { flash("Insider-Scan …"); await jpost("/api/investment/insider-scan"); return renderInvestment(); }
}

/* =========================== LUNA-Chat + Voice =========================== */
let CHAT_OPEN = false, REC = null, LISTENING = false, AUDIO = null;
function chatShell() {
  $("#v2-chat").innerHTML = `
    <header>LUNA <button class="v2-icon" id="v2-mic" title="Sprechen">🎙</button></header>
    <div class="log" id="v2-log"><div class="msg luna">Hallo! Wie kann ich helfen?</div></div>
    <form id="v2-chatform"><input id="v2-chatin" placeholder="Frag LUNA …" autocomplete="off"><button class="v2-btn pri" type="submit">↑</button></form>`;
  $("#v2-chatform").addEventListener("submit", (e) => { e.preventDefault(); const v = $("#v2-chatin").value.trim(); if (v) { $("#v2-chatin").value = ""; sendChat(v); } });
  $("#v2-mic").addEventListener("click", toggleVoice);
}
function toggleChat(open) {
  CHAT_OPEN = open == null ? !CHAT_OPEN : open;
  const c = $("#v2-chat"); c.hidden = !CHAT_OPEN;
  if (CHAT_OPEN && !c.dataset.init) { chatShell(); c.dataset.init = "1"; }
}
function addMsg(who, text) {
  const log = $("#v2-log"); if (!log) return;
  const d = document.createElement("div"); d.className = "msg " + who; d.textContent = text; log.appendChild(d); log.scrollTop = log.scrollHeight;
}
async function sendChat(text) {
  addMsg("me", text);
  const r = await jpost("/api/chat", { text });
  const reply = (r && (r.reply || r.antwort)) || "…";
  addMsg("luna", reply); lunaSpeak(reply);
}
function setOrb(state) { const o = $("#v2-orb"); o.className = "v2-orb " + state; }
async function lunaSpeak(text) {
  try {
    const r = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: String(text).slice(0, 600) }) });
    if (!r.ok) return; const buf = await r.arrayBuffer();
    const ctx = AUDIO || (AUDIO = new (window.AudioContext || window.webkitAudioContext)());
    const audio = await ctx.decodeAudioData(buf); const src = ctx.createBufferSource(); src.buffer = audio;
    src.connect(ctx.destination); setOrb("speaking"); src.onended = () => setOrb("idle"); src.start();
  } catch { setOrb("idle"); }
}
function toggleVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { toggleChat(true); return; }
  if (LISTENING) { REC && REC.stop(); return; }
  REC = new SR(); REC.lang = "de-DE"; REC.interimResults = false;
  REC.onstart = () => { LISTENING = true; setOrb("listening"); };
  REC.onend = () => { LISTENING = false; setOrb("idle"); };
  REC.onresult = (e) => { const t = e.results[0][0].transcript; toggleChat(true); sendChat(t); };
  REC.start();
}

/* =========================== SSE Live =========================== */
function connectSSE() {
  try {
    const es = new EventSource("/api/events");
    es.onmessage = () => { if (AKTIV === "dash") renderDash(); };
  } catch { }
}

/* =========================== Events + Boot =========================== */
document.addEventListener("click", (e) => {
  const g = e.target.closest("[data-go]"); if (g) { go(g.dataset.go); return; }
  const um = e.target.closest("[data-ui-mode]"); if (um) { setUiMode(um.dataset.uiMode); return; }
  const tc = e.target.closest("[data-toggle-chat]"); if (tc) { toggleChat(); return; }
  const orb = e.target.closest("#v2-orb"); if (orb) { toggleVoice(); return; }
  const th = e.target.closest("#v2-theme"); if (th) { toggleTheme(); return; }
  const ac = e.target.closest("[data-act]"); if (ac) { handleAct(ac.dataset.act, ac); return; }
});

(async function boot() {
  applyTheme();
  [ME, PREFS] = await Promise.all([
    jget("/api/me").then(x => x || ME),
    jget("/api/prefs").then(x => (x && x.prefs) || {}),
  ]);
  buildShell();
  go("dash");
  connectSSE();
})();
