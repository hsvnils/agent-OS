// LUNA-OS -- Desktop-aehnliche Arbeitsoberflaeche (Phase 16).
// Holt den Zustand aus der API, zeigt Apps in WinBox-Fenstern, Aktionen per Button (live).
"use strict";

let STATE = { antraege: [], meldungen: [], aktivitaet: [], research: [], finance: {} };
let ME = { apps: null, role: "owner", display_name: "", username: "" };  // apps=null -> alles zeigen (bis geladen)
const WINS = {};  // app-id -> WinBox

// K4: erlaubte Apps des eingeloggten Nutzers (SSOT vom Backend /api/me). darf() = Sichtbarkeits-/Zugriffs-Gate.
async function ladeMe() {
  try { ME = await (await fetch("/api/me")).json(); } catch { ME = { apps: null, role: "owner" }; }
}
const darf = (id) => id === "home" || !ME.apps || ME.apps.includes(id);

// Theme: Dunkel / Hell / Automatisch (pro Gerät in localStorage; Auto folgt dem System-Erscheinungsbild).
function applyTheme() {
  const mode = localStorage.getItem("luna-theme") || "auto";
  const light = mode === "light" || (mode === "auto" && matchMedia("(prefers-color-scheme: light)").matches);
  document.documentElement.classList.toggle("theme-light", light);
  document.documentElement.classList.toggle("theme-dark", !light);
  document.querySelectorAll("#theme-switch button").forEach(b => b.classList.toggle("active", b.dataset.themeSet === mode));
}
function setTheme(mode) { localStorage.setItem("luna-theme", mode); applyTheme(); }

// UI-Version V1 <-> V2: Wahl pro Nutzer (Prefs + localStorage-Flash-Schutz), dann Seite in der Zielversion laden.
async function setUiMode(mode) {
  if (mode !== "v2") mode = "v1";
  try { localStorage.setItem("luna-ui-mode", mode); } catch { /* egal */ }
  PREFS = { ...PREFS, ui_version: mode };
  try { await fetch("/api/prefs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prefs: PREFS }) }); } catch { /* offline: Query-Override greift trotzdem */ }
  location.href = "/?ui=" + mode;   // Server liefert die passende Einstiegs-Datei
}
try { matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
  if ((localStorage.getItem("luna-theme") || "auto") === "auto") applyTheme();
}); } catch { /* aeltere Browser */ }

// LUNA 3D-Hologramm (opt-in, lazy geladen) -- ersetzt den Orb; teilt sich das Modul mit V2.
let AVATAR = null, AV_MOD = null;
function updateAvatarSwitch() {
  const sw = document.getElementById("avatar-switch"); if (!sw) return;
  sw.hidden = ME.avatar_enabled === false;
  const mode = PREFS.avatar === "hologramm" ? "hologramm" : "orb";
  sw.querySelectorAll("button").forEach(b => b.classList.toggle("active", b.dataset.avatarSet === mode));
}
async function applyAvatar() {
  updateAvatarSwitch();
  const holo = document.getElementById("luna-holo"); if (!holo) return;
  const on = ME.avatar_enabled !== false && PREFS.avatar === "hologramm";
  document.body.classList.toggle("holo-on", on);
  if (on) {
    holo.hidden = false;
    if (!AVATAR) {
      try { AV_MOD = AV_MOD || await import("/static/luna-avatar.js?v=11");
        AVATAR = AV_MOD.createAvatar(holo, { reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches }); }
      catch (e) { console.warn("[luna] Avatar-Ladefehler", e); AVATAR = null; }
      if (!AVATAR) { holo.hidden = true; document.body.classList.remove("holo-on"); }   // Fallback: Orb
    }
  } else { if (AVATAR) { AVATAR.dispose(); AVATAR = null; } holo.hidden = true; }
}
async function setAvatarPref(mode) {
  PREFS = { ...PREFS, avatar: mode };
  try { localStorage.setItem("luna-avatar-mode", mode); } catch { }
  try { await fetch("/api/prefs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prefs: PREFS }) }); } catch { }
  applyAvatar();
}

// #2: Konfigurierbares Dashboard -- Widget-Reihenfolge + ausgeblendete, pro User in Supabase gespeichert.
const DASH_DEFAULT = ["ov", "hero", "feed", "agents", "timeline", "quick", "sysmon", "investP", "mem", "llm"];
const DASH_TITEL = { ov: "AI Core Overview", hero: "LUNA Core", feed: "Live Intelligence Feed",
  agents: "Active Agents", timeline: "Mission Timeline", quick: "Quick Commands", sysmon: "System Monitor",
  investP: "Investment", mem: "Memory Insights", llm: "LLM / Provider" };
let LAYOUT = { order: [...DASH_DEFAULT], hidden: [] };
let PREFS = {};
let EDIT = false;
let DRAG = null;

function normLayout(l) {
  l = l || {};
  const hidden = (Array.isArray(l.hidden) ? l.hidden : []).filter(id => DASH_DEFAULT.includes(id));
  const order = (Array.isArray(l.order) ? l.order : []).filter(id => DASH_DEFAULT.includes(id));
  DASH_DEFAULT.forEach(id => { if (!order.includes(id)) order.push(id); });  // neue Widgets hinten anfuegen
  return { order, hidden };
}
async function ladePrefs() {
  try { const p = JSON.parse(localStorage.getItem("luna-prefs") || "{}"); if (p.dashboard) LAYOUT = normLayout(p.dashboard); } catch { /* egal */ }
  try { const r = await (await fetch("/api/prefs")).json(); PREFS = r.prefs || {}; if (PREFS.dashboard) LAYOUT = normLayout(PREFS.dashboard); } catch { /* offline -> localStorage/Default */ }
}
async function savePrefs() {
  PREFS = { ...PREFS, dashboard: LAYOUT };
  try { localStorage.setItem("luna-prefs", JSON.stringify(PREFS)); } catch { /* egal */ }
  try { await fetch("/api/prefs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prefs: PREFS }) }); } catch { /* offline: bleibt lokal */ }
}
function toggleEdit() {
  EDIT = !EDIT;
  AKTIV_NAV = "home";
  if (!EDIT) savePrefs();
  renderDashboard(); updateSidebarCounts();
  document.getElementById("edit-dash")?.classList.toggle("on", EDIT);
}
function hideWidget(id) { if (!LAYOUT.hidden.includes(id)) LAYOUT.hidden.push(id); savePrefs(); renderDashboard(); }
function showWidget(id) { LAYOUT.hidden = LAYOUT.hidden.filter(x => x !== id); savePrefs(); renderDashboard(); }
function tagWidget(id, html) {
  if (!html) return "";
  let h = html.replace('<div class="', `<div data-wid="${id}"${EDIT ? ' draggable="true"' : ""} class="`);
  if (EDIT) h = h.replace(">", `><div class="wedit"><span class="wdrag" title="Ziehen zum Anordnen">⠿</span>` +
    `<button class="whide" data-whide="${id}" title="Ausblenden">✕</button></div>`);
  return h;
}
function dashTray() {
  const hid = LAYOUT.order.filter(id => LAYOUT.hidden.includes(id));
  const chips = hid.length
    ? hid.map(id => `<button class="wadd" data-wadd="${id}">+ ${esc(DASH_TITEL[id] || id)}</button>`).join("")
    : `<span class="leer">Keine ausgeblendeten Widgets.</span>`;
  return `<div class="panel dash-tray"><div class="tray-chips">
    <b>Bearbeiten:</b> Widgets ziehen zum Anordnen · ✕ ausblenden · unten wieder hinzufügen.
    <button class="btn primary" data-editdone="1">Fertig</button></div>
    <div class="tray-chips" style="margin-top:8px">${chips}</div></div>`;
}
// Drag & Drop zum Anordnen (nur im Edit-Modus); Handler einmalig registriert.
document.addEventListener("dragstart", e => { if (!EDIT) return; const p = e.target.closest("[data-wid]"); if (!p) return; DRAG = p.dataset.wid; e.dataTransfer.effectAllowed = "move"; p.classList.add("dragging"); });
document.addEventListener("dragend", e => { const p = e.target.closest("[data-wid]"); if (p) p.classList.remove("dragging"); DRAG = null; });
document.addEventListener("dragover", e => { if (EDIT && DRAG) e.preventDefault(); });
document.addEventListener("drop", e => {
  if (!EDIT || !DRAG) return; e.preventDefault();
  const target = e.target.closest("[data-wid]"); if (!target || target.dataset.wid === DRAG) return;
  const from = LAYOUT.order.indexOf(DRAG), to = LAYOUT.order.indexOf(target.dataset.wid);
  if (from < 0 || to < 0) return;
  LAYOUT.order.splice(from, 1); LAYOUT.order.splice(to, 0, DRAG);
  savePrefs(); renderDashboard();
});

const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const zeit = (ts) => { try { return new Date(ts).toLocaleString("de-DE", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }); } catch { return ""; } };

// ---- Apps -----------------------------------------------------------------
const APPS = {
  auftraege: { icon: "📋", titel: "Aufträge", badge: () => STATE.antraege.length, render: renderAuftraege },
  meldungen: { icon: "🔔", titel: "Meldungen", badge: () => STATE.meldungen.length, render: renderListe("meldungen", m => [m.abteilung, m.text, m.ts]) },
  aktivitaet: { icon: "📊", titel: "Aktivität", badge: () => 0, render: renderListe("aktivitaet", a => [a.akteur, a.aktion, a.ts]) },
  research: { icon: "🔍", titel: "Research", badge: () => STATE.research.length, render: renderListe("research", r => [r.abteilung || r.status, r.frage, ""]) },
  lagebild: { icon: "📡", titel: "Lagebild", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Lagebild…</div></div>`, load: ladeLagebild },
  wissen: { icon: "🧠", titel: "Wissen", badge: () => 0, render: renderWissen, load: ladeWissen },
  investment: { icon: "📈", titel: "Investment", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Investment…</div></div>`, load: ladeInvestment },
  crm: { icon: "🤝", titel: "Collab-CRM", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade CRM…</div></div>`, load: ladeCRM },
  timeline: { icon: "🕒", titel: "Timeline", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Timeline…</div></div>`, load: ladeTimeline },
  trends: { icon: "🔥", titel: "Trends", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Trends…</div></div>`, load: ladeTrends },
  ideas: { icon: "💡", titel: "Ideen-Labor", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Ideen…</div></div>`, load: ladeIdeen },
  drafts: { icon: "✍️", titel: "Drafts", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Drafts…</div></div>`, load: ladeDrafts },
  quellen: { icon: "📡", titel: "Quellen", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Quellen…</div></div>`, load: ladeQuellen },
  aiinbox: { icon: "🧩", titel: "AI-Inbox", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade AI-Inbox…</div></div>`, load: ladeAiInbox },
  cutter: { icon: "🎬", titel: "Cutter", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Cutter…</div></div>`, load: ladeCutter },
  finance: { icon: "💶", titel: "Finanzen", badge: () => 0, render: renderFinance },
  agenten: { icon: "🕸️", titel: "Organigramm", badge: () => 0, render: renderAgenten, load: ladeAgenten },
  team: { icon: "👥", titel: "Team", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Team…</div></div>`, load: ladeTeam },
};

// ---- Investment (CIO, advisory) --------------------------------------------
let INVEST = null, INVLOOP = null;
async function ladeInvestment() {
  try { INVEST = await (await fetch("/api/investment")).json(); } catch { INVEST = null; }
  try { INVLOOP = await (await fetch("/api/investment/loop")).json(); } catch { INVLOOP = null; }
  const win = WINS.investment; if (!win) return;
  if (!INVEST) { win.body.innerHTML = `<div class="app"><div class="leer">Investment nicht verfügbar.</div></div>`; return; }
  const i = INVEST;
  const prov = (i.provider || []).map(p => `<span class="pill ${p.konfiguriert ? "active" : "off"}"><span class="dot"></span>${esc(p.name)}</span>`).join(" ");
  const wl = (i.watchlist || []).map(w => `<span class="chip"><b>${esc(w.symbol)}</b><span class="meta">${esc(w.asset)}</span><button class="chip-x" data-invremove="${esc(w.symbol)}" title="Aus Watchlist entfernen">✕</button></span>`).join("") || "<i>leer</i>";
  const sl = (i.shortlist || []).map(s => { const c = s.veraenderung_pct; const v = (c > 0 ? "+" : "") + (c == null ? "?" : Number(c).toFixed(1)) + "%";
    return `<div class="row klick" data-invsym="${esc(s.symbol)}" data-invasset="${esc(s.asset || "aktie")}" title="Details zu ${esc(s.symbol)}"><span class="t" style="color:${c >= 0 ? "var(--green)" : "var(--red)"}">${v}</span><div><b>${esc(s.symbol)}</b> <span class="meta">${esc(s.asset)} · ${esc(s.quelle)}</span></div><span class="chev">›</span></div>`; }).join("")
    || `<div class="leer">Noch kein Screen — klick „Screen jetzt".</div>`;
  const sug = (i.vorschlaege || []).map(s => `<div class="card klick" data-invsym="${esc(s.symbol)}" data-invasset="${esc(/^[a-z]/.test(s.symbol || "") && (s.symbol || "").length > 4 ? "krypto" : "aktie")}" title="Details zu ${esc(s.symbol)}">
    <div class="head"><span class="badge ${s.risiko_label === "spekulativ" ? "in_umsetzung" : "freigegeben"}">${esc(s.risiko_label || "")}</span><b>${esc((s.aktion || "").toUpperCase())} ${esc(s.symbol)}</b><span class="chev">›</span></div>
    <div class="desc">${esc(s.grund || "")}</div>
    <div class="meta">Konfidenz ${Math.round((s.konfidenz || 0) * 100)}% · ${(s.quellen || []).map(esc).join(", ")}</div></div>`).join("")
    || `<div class="leer">Noch keine Vorschläge.</div>`;
  const ins = (i.insider || []).map(s => `<div class="card">
    <div class="head"><span class="badge in_umsetzung">Insider</span><b>${esc(s.symbol)}</b><span class="meta">${s.cluster || 1} Insider · ~${s.betrag != null ? esc(s.betrag) : "?"} USD</span></div>
    <div class="desc">${esc(s.rolle || "k.A.")} · Konfidenz ${Math.round((s.konfidenz || 0) * 100)}%${s.datum ? " · " + esc(s.datum) : ""}</div>
    ${s.filing_url ? `<div class="meta"><a href="${esc(s.filing_url)}" target="_blank" rel="noopener">SEC Form 4 ↗</a></div>` : ""}</div>`).join("")
    || `<div class="leer">Noch keine Insider-Signale — klick „Insider-Scan".</div>`;
  const sc = i.scorecard || {};
  const scText = sc.ausgewertet ? `${Math.round((sc.trefferquote || 0) * 100)}% Trefferquote (${sc.treffer}/${sc.ausgewertet})` : "noch keine Auswertung";
  const h = i.historie || {}; const jt = h.je_tabelle || {};
  const histText = h.eintraege_gesamt ? `${h.eintraege_gesamt} Einträge (all-time) · ${jt.forecasts || 0} Prognosen · ${jt.actuals || 0} ausgewertet · ${jt.screening || 0} Screens` : "noch leer";
  win.body.innerHTML = `<div class="app">
    <div class="kv"><span class="k">Modus</span><b>${esc(i.modus)}</b></div>
    <div class="kv"><span class="k">Track-Record</span><b>${esc(scText)}</b></div>
    <div class="kv"><span class="k">Historie (append-only)</span><b>${esc(histText)}</b></div>
    <div style="margin:10px 0; display:flex; gap:6px; flex-wrap:wrap">${prov}</div>
    ${invLoopHtml(INVLOOP)}
    <div class="brain-bar">
      <div class="inv-ac"><input id="inv-sym" placeholder="Aktie/Krypto suchen & hinzufügen…" autocomplete="off" oninput="investSuche(this.value)">
        <div id="inv-suggest" class="inv-suggest"></div></div>
      <button class="btn info" onclick="investSammeln(this)">📥 Jetzt sammeln</button>
      <button class="btn info" onclick="investBackfill(this)">📚 Historie laden</button>
      <button class="btn info" onclick="investScreen(this)">📡 Screen jetzt</button>
      <button class="btn info" onclick="investInsiderScan(this)">🔍 Insider-Scan</button></div>
    <h3>Watchlist</h3><div>${wl}</div>
    <h3>Shortlist (letzter Screen)</h3>${sl}
    <h3>Vorschläge (vom Risk-Agent geprüft)</h3>${sug}
    <h3>Insider-Signale (SEC Form 4)</h3>${ins}</div>`;
  invMountCharts();
}

// ---- Investment-Lern-Loop (Walk-Forward): Command-Center-Block -------------
const invPct = v => (v == null ? "–" : Math.round(v) + "%");
const invNum = v => (v == null ? "–" : Number(v).toFixed(1));
function invKpi(label, wert, sub) {
  return `<div class="inv-kpi"><div class="k">${esc(label)}</div><b>${wert}</b><span>${esc(sub || "")}</span></div>`;
}
// Fehler-Verlauf: zwei Linien (Modell vs. Baseline), niedriger = besser.
// Fehler-Verlauf als ECHTER, responsiver Chart: zeichnet sich pixelgenau zur Containerbreite (mit Achsen/Gitter/
// Hover) und rendert bei jeder Groessenaenderung frisch (ResizeObserver) -- kein Strecken, keine Fremd-Lib.
let _invChartRO = null;
function invMountCharts() {
  const el = document.getElementById("inv-trend");
  if (!el) return;
  invRenderTrend(el);
  if (!_invChartRO) _invChartRO = new ResizeObserver(es => es.forEach(e => invRenderTrend(e.target)));
  try { _invChartRO.disconnect(); _invChartRO.observe(el); } catch {}
}
function invRenderTrend(el) {
  const v = (INVLOOP && INVLOOP.verlauf) || [];
  if (!v.length) { el.innerHTML = `<div class="leer">Noch kein Fehler-Verlauf — braucht ausgewertete Prognosen.</div>`; return; }
  const W = Math.max(260, Math.round(el.clientWidth || 320)), H = 150, padL = 30, padR = 10, padT = 10, padB = 20;
  const max = Math.max(1, ...v.flatMap(p => [p.mae_pct || 0, p.baseline_mae_pct || 0])) * 1.1;
  const x = i => padL + (v.length <= 1 ? (W - padL - padR) / 2 : i * (W - padL - padR) / (v.length - 1));
  const y = val => H - padB - ((val || 0) / max) * (H - padT - padB);
  const line = k => v.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p[k]).toFixed(1)}`).join(" ");
  const dots = (k, c) => v.map((p, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(p[k]).toFixed(1)}" r="2.4" class="c-dot ${c}"/>`).join("");
  const grid = [0, .5, 1].map(f => { const t = max * f, yy = y(t).toFixed(1); return `<line x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}" class="c-grid"/><text x="${padL - 5}" y="${(+yy + 3)}" class="c-axt" text-anchor="end">${t.toFixed(1)}</text>`; }).join("");
  const xi = v.length > 2 ? [0, Math.floor((v.length - 1) / 2), v.length - 1] : v.map((_, i) => i);
  const xl = xi.map(i => `<text x="${x(i).toFixed(1)}" y="${H - 5}" class="c-axt" text-anchor="middle">${esc((v[i].woche || "").replace("2026-", ""))}</text>`).join("");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none" class="inv-chart-svg" role="img">
    ${grid}<path d="${line("baseline_mae_pct")}" class="inv-line base"/><path d="${line("mae_pct")}" class="inv-line strat"/>
    ${dots("baseline_mae_pct", "base")}${dots("mae_pct", "strat")}${xl}</svg><div class="c-tip" style="display:none"></div>`;
  const svg = el.querySelector("svg"), tip = el.querySelector(".c-tip");
  svg.addEventListener("mousemove", ev => {
    const r = svg.getBoundingClientRect();
    let i = Math.round(((ev.clientX - r.left) / r.width * W - padL) / ((W - padL - padR) / Math.max(1, v.length - 1)));
    i = Math.max(0, Math.min(v.length - 1, i)); const p = v[i];
    tip.innerHTML = `<b>${esc((p.woche || "").replace("2026-", ""))}</b> · Modell ${(p.mae_pct || 0).toFixed(1)}% · Baseline ${(p.baseline_mae_pct || 0).toFixed(1)}%`;
    tip.style.display = "block";
    tip.style.left = Math.max(0, Math.min(r.width - 190, ev.clientX - r.left - 60)) + "px";
  });
  svg.addEventListener("mouseleave", () => { tip.style.display = "none"; });
}
function invLoopHtml(L) {
  if (!L) return "";
  const g = (L.kennzahlen && L.kennzahlen.gesamt) || {};
  const p = L.panel || {};
  const kpis = g.n
    ? `<div class="inv-kpis">
        ${invKpi("Richtungsquote", invPct((g.richtungsquote || 0) * 100), g.n + " ausgewertet")}
        ${invKpi("Fehler (MAE)", invNum(g.mae_pct) + "%", "je Prognose")}
        ${invKpi("Baseline", invNum(g.baseline_mae_pct) + "%", "Messlatte")}
        ${invKpi("Besser als Baseline", invPct((g.anteil_besser_baseline || 0) * 100), "Trefferanteil")}
      </div>`
    : `<div class="leer">Noch keine ausgewerteten Prognosen — der Loop sammelt (Prognose Mo, Abgleich nach 7 Tagen).</div>`;
  const klassen = Object.entries((L.kennzahlen && L.kennzahlen.je_asset) || {}).map(([k, a]) =>
    `<div class="inv-cls"><span class="lbl">${esc(k)}</span>
      <div class="bar"><i style="width:${Math.round((a.richtungsquote || 0) * 100)}%"></i></div>
      <span class="val">${invPct((a.richtungsquote || 0) * 100)} · MAE ${invNum(a.mae_pct)}% · n=${a.n}</span></div>`).join("")
    || `<div class="leer">–</div>`;
  const attr = Object.entries((L.kennzahlen && L.kennzahlen.je_signal) || {}).map(([k, a]) =>
    `<div class="inv-cls"><span class="lbl">${esc(k)}</span>
      <div class="bar"><i style="width:${Math.round((a.richtungsquote || 0) * 100)}%"></i></div>
      <span class="val">${invPct((a.richtungsquote || 0) * 100)} Treffer · n=${a.n}</span></div>`).join("");
  const vers = Object.entries((L.kennzahlen && L.kennzahlen.je_version) || {}).map(([k, a]) =>
    `<div class="inv-lp-row"><span class="k" style="text-transform:none">${esc(k)}</span>
      <b>${invPct((a.anteil_besser_baseline || 0) * 100)} schlägt Baseline · MAE ${invNum(a.mae_pct)} vs ${invNum(a.baseline_mae_pct)} · Richtung ${invPct((a.richtungsquote || 0) * 100)} · n=${a.n}</b></div>`).join("");
  const prog = (L.offene_prognosen || []).slice(0, 8).map(f => {
    const up = f.richtung === "steigt", dn = f.richtung === "faellt";
    const col = up ? "var(--green)" : dn ? "var(--red)" : "var(--muted)";
    const pfeil = up ? "▲" : dn ? "▼" : "▬";
    return `<div class="row"><span class="t" style="color:${col}">${pfeil} ${(f.ziel_return_pct > 0 ? "+" : "") + invNum(f.ziel_return_pct)}%</span>
      <div><b>${esc(f.symbol)}</b> <span class="meta">${esc(f.asset)} · Konf. ${invPct((f.konfidenz || 0) * 100)} · fällig ${esc(f.faellig_am || "")}</span></div></div>`;
  }).join("") || `<div class="leer">Noch keine offenen Prognosen.</div>`;
  const reg = (L.register || []).slice(0, 8).map(d => {
    const gut = d.besser_als_baseline;
    return `<div class="row"><span class="t" style="color:${gut ? "var(--green)" : "var(--amber)"}">Δ ${invNum(d.fehler_abs_pct)}%</span>
      <div><b>${esc(d.symbol)}</b> <span class="meta">${esc(d.asset)} · Prognose ${invNum(d.prognose_return_pct)}% → real ${invNum(d.real_return_pct)}%${d.richtungstreffer ? " · Richtung ✓" : ""}${d.backtest ? " · Backtest" : ""}</span></div>
      <span class="badge ${gut ? "freigegeben" : "in_umsetzung"}">${gut ? "schlägt Baseline" : "unter Baseline"}</span></div>`;
  }).join("") || `<div class="leer">Register noch leer — Abweichungen erscheinen nach dem ersten Abgleich.</div>`;
  return `<div class="inv-loop">
    <div class="inv-loop-head"><b>Lern-Loop (Walk-Forward)</b>
      <span class="meta">${p.symbole || 0} Werte · ${p.snapshots || 0} Snapshots · Stand ${esc(p.letzter || "–")} · Modell ${esc(L.modell_version || "")}</span></div>
    ${kpis}
    <div class="inv-two">
      <div><h4>Fehler-Verlauf <span class="meta">niedriger = besser</span></h4><div class="inv-chart" id="inv-trend"></div>
        <div class="inv-leg"><span><i class="strat"></i>Modell</span><span><i class="base"></i>Baseline</span></div></div>
      <div><h4>Je Anlageklasse</h4>${klassen}</div>
    </div>
    ${attr ? `<h4>Signal-Attribution <span class="meta">welche Signale treffen</span></h4>${attr}` : ""}
    ${vers ? `<h4>Je Modell-Version <span class="meta">schlägt es die Baseline?</span></h4><div class="inv-lp">${vers}</div>
      <div class="meta" style="margin-top:6px">v4-insider-30d = eigenes Modell: nur Werte mit frischem SEC-Form-4-Insider-Cluster-Kauf, 30-Tage-Horizont (kleinere Stichprobe). Nicht 1:1 gegen die 7-Tage-MAE von v2/v3 zu lesen — Maßstab ist „schlägt Baseline" + Richtungsquote auf dem Insider-Subset.</div>` : ""}
    ${invMarktKontrolleHtml(L.insider_kontrolle)}
    <h4>Offene Prognosen</h4>${prog}
    <h4>Abweichungs-Register <span class="meta">separat, dauerhaft</span></h4>${reg}
    ${invLeitplankenHtml(L.leitplanken)}
  </div>`;
}
function invMarktKontrolleHtml(mk) {
  if (!mk || !mk.insider || !mk.insider.n) return "";
  const ins = mk.insider, bas = mk.basisrate || {};
  const pct = (x) => x == null ? "–" : invPct(x * 100);
  const eR = mk.edge_richtung_pp, eM = mk.edge_markt_pp;   // Prozentpunkte Vorsprung Insider vs Basisrate
  const alpha = ins.alpha_schnitt_pct;
  // Echter Edge = Insider schlägt den Markt HÄUFIGER als der Durchschnitts-Wert (edge_markt_pp > 0) und Alpha > 0.
  const echterEdge = (eM != null && eM > 0) && (alpha != null && alpha > 0);
  const grenzwertig = (eM != null && eM > 0) || (alpha != null && alpha > 0);
  const badge = echterEdge ? ["freigegeben", "Edge über Marktdrift"]
    : grenzwertig ? ["in_umsetzung", "grenzwertig"] : ["in_umsetzung", "kein Edge über Markt"];
  const row = (lbl, o, n) => `<div class="inv-lp-row"><span class="k" style="text-transform:none">${lbl}</span>
      <b>Richtung ${pct(o.richtung_pct)} · schlägt Markt ${pct(o.schlaegt_markt_pct)} · n=${n}</b></div>`;
  return `<h4>Marktdrift-Kontrolle <span class="meta">Insider vs. „steigt eh mit dem Markt" (${esc(mk.benchmark || "SPY")}, ${mk.horizont_tage || 30}T)</span>
      <span class="badge ${badge[0]}" style="margin-left:8px">${badge[1]}</span></h4>
    <div class="inv-lp">
      ${row("Insider-Wochen", ins, ins.n)}
      ${row("Basisrate (alle Wochen)", bas, bas.n)}
      <div class="inv-lp-row"><span class="k" style="text-transform:none">Vorsprung Insider</span>
        <b style="color:${(eM != null && eM > 0) ? "var(--green)" : "var(--amber)"}">Richtung ${eR == null ? "–" : (eR > 0 ? "+" : "") + eR + " pp"} · schlägt Markt ${eM == null ? "–" : (eM > 0 ? "+" : "") + eM + " pp"} · Ø Alpha ${alpha == null ? "–" : (alpha > 0 ? "+" : "") + invNum(alpha) + "%"}</b></div>
    </div>
    <div class="meta" style="margin-top:6px">Trennt Insider-Alpha von der Marktdrift: über 30 Tage steigt in einem freundlichen Markt fast jede Aktie. Nur wenn Insider-Werte den Markt <b>häufiger schlagen</b> als der Durchschnitt (Vorsprung &gt; 0) und das Ø-Alpha positiv ist, ist der Edge echt — nicht bloß Mitschwimmen.</div>`;
}
function invLeitplankenHtml(lp) {
  if (!lp) return "";
  const aktiv = lp.autonom_aktiv;
  const cfg = (lp.konfiguration || []).map(c =>
    `<div class="inv-lp-row"><span class="k">${esc(c.label)}</span><b>${esc(c.wert)}</b></div>`).join("");
  return `<h4>Autonomie-Leitplanken <span class="meta">CEO-abgesegnet</span></h4>
    <div class="inv-lp-status ${aktiv ? "on" : "off"}">
      <span class="dot"></span>${aktiv ? "Autonomes Handeln AKTIV (Modus " + esc(lp.modus) + ")"
        : "Autonomes Handeln inaktiv — Modus " + esc(lp.modus || "advisory") + " (greift ab Paper/Live)"}</div>
    <div class="inv-lp">${cfg}</div>`;
}
async function investSammeln(btn) {
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Sammelt…"; }
  let txt = "";
  try {
    const r = await (await fetch("/api/investment/sammeln", { method: "POST" })).json();
    if (r && r.ok) txt = `✅ ${r.gesammelt} gesammelt · ${r.prognosen_neu} Prognosen · ${r.ausgewertet} ausgewertet`;
  } catch { txt = "Fehler beim Sammeln"; }
  await ladeInvestment();
  const b = document.querySelector('[onclick="investSammeln(this)"]');
  if (b && txt) { b.textContent = txt; setTimeout(() => { b.textContent = "📥 Jetzt sammeln"; }, 4000); }
}
async function investBackfill(btn) {
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Lädt Historie…"; }
  let txt = "";
  try {
    const r = await (await fetch("/api/investment/backfill", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ seit: "2026-01-01" }) })).json();
    if (r && r.ok) txt = `✅ ${r.zeilen_neu} Kurse · ${r.auswertungen_neu} Backtest` + ((r.hinweise && r.hinweise.length) ? ` · ⚠️ ${r.hinweise.length} übersprungen: ${r.hinweise[0]}` : "");
  } catch { txt = "Fehler beim Laden"; }
  await ladeInvestment();
  const b = document.querySelector('[onclick="investBackfill(this)"]');
  if (b && txt) { b.textContent = txt; setTimeout(() => { b.textContent = "📚 Historie laden"; }, 6000); }
}
async function investScreen(btn) {
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Screent…"; }
  try { await fetch("/api/investment/screen", { method: "POST" }); } catch {}
  ladeInvestment();
}
async function investInsiderScan(btn) {
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Scannt…"; }
  try { await fetch("/api/investment/insider-scan", { method: "POST" }); } catch {}
  ladeInvestment();
}
// ---- Collab-CRM (CRO) ------------------------------------------------------
let CRM = null;
async function ladeCRM() {
  try { CRM = await (await fetch("/api/crm")).json(); } catch { CRM = null; }
  const win = WINS.crm; if (!win) return;
  if (!CRM) { win.body.innerHTML = `<div class="app"><div class="leer">CRM nicht verfügbar.</div></div>`; return; }
  const c = CRM, u = c.uebersicht || {}, pipe = u.pipeline || {};
  const pipeHtml = ["neu", "in_gespraech", "angebot", "vereinbart", "abgelehnt"].map(s => `<div class="kv"><span class="k">${esc(s)}</span><b>${pipe[s] || 0}</b></div>`).join("");
  const todos = (c.todos || []).map(t => `<div class="card">
    <div class="head"><span class="badge in_umsetzung">To-do</span><b>${esc(t.firma)}</b></div>
    <div class="desc">${esc(t.vorschlag)}</div>${t.begruendung ? `<div class="meta">${esc(t.begruendung)}</div>` : ""}
    <button class="btn" data-crmtodo="${esc(t.id)}">✓ Erledigt</button></div>`).join("")
    || `<div class="leer">Keine offenen To-dos.</div>`;
  const firmen = (c.firmen || []).map(f => `<div class="row klick" data-crmfirma="${esc(f.firma)}" title="Verlauf von ${esc(f.firma)}"><span class="t">${esc(f.status)}</span><div><b>${esc(f.firma)}</b> <span class="meta">${esc(f.quelle || "")} · ${f.nachrichten || 0} Nachr.</span></div><span class="chev">›</span></div>`).join("")
    || `<div class="leer">Noch keine Anfragen erfasst — kommt automatisch per Instagram-Webhook.</div>`;
  win.body.innerHTML = `<div class="app">
    <div class="kv"><span class="k">Firmen gesamt</span><b>${u.firmen_gesamt || 0}</b></div>
    <div class="kv"><span class="k">Offene To-dos</span><b>${u.offene_todos || 0}</b></div>
    <h3>Pipeline</h3>${pipeHtml}
    <h3>Offene To-dos</h3>${todos}
    <h3>Firmen (nach letztem Kontakt)</h3>${firmen}</div>`;
}
async function crmTodoErledigt(id) {
  try { await fetch("/api/crm/todo/" + encodeURIComponent(id) + "/erledigen", { method: "POST" }); } catch {}
  ladeCRM();
}
async function openCrmKonversation(firma) {
  const wid = "crmk:" + firma;
  if (WINS[wid]) { WINS[wid].focus(); return; }
  const win = new WinBox("🤝  " + firma, { ...(istMobil() ? winGeom() : { width: "460px", height: "62%", x: "center", y: "center" }), class: ["modern"], onclose: () => { delete WINS[wid]; return false; } });
  WINS[wid] = win;
  win.body.innerHTML = `<div class="app"><div class="leer">Lade Verlauf…</div></div>`;
  try {
    const d = await (await fetch("/api/crm/konversation?firma=" + encodeURIComponent(firma))).json();
    const msgs = (d.nachrichten || []).map(m => crmMsgRow(m)).join("") || `<div class="leer">Kein Verlauf.</div>`;
    win.body.innerHTML = `<div class="app detail"><div class="head"><b>${esc(firma)}</b></div>${msgs}</div>`;
  } catch { win.body.innerHTML = `<div class="app"><div class="leer">Konnte Verlauf nicht laden.</div></div>`; }
}
// Kanaluebergreifend: Kanal-Badge je Nachricht (Instagram/Mail/Telegram/...).
const KANAL = { instagram: { i: "📸", l: "Instagram" }, mail: { i: "✉️", l: "Mail" }, telegram: { i: "💬", l: "Telegram" }, manuell: { i: "✎", l: "Manuell" } };
const kanalIcon = q => (KANAL[q] || { i: "•" }).i;
const kanalLabel = q => (KANAL[q] || { l: q || "—" }).l;
function crmMsgRow(m, mitFirma = false) {
  return `<div class="row"><span class="t" title="${esc(kanalLabel(m.quelle))} · ${m.richtung === "ein" ? "eingehend" : "ausgehend"}">${kanalIcon(m.quelle)}${m.richtung === "ein" ? "⬅︎" : "➡︎"}</span>
    <div>${mitFirma ? `<b>${esc(m.firma || "")}</b> ` : ""}<b>${esc(m.text)}</b><br>
    <span class="meta">${esc(kanalLabel(m.quelle))}${m.kategorie && m.kategorie !== "mail" ? " · " + esc(m.kategorie) : ""}${m.ts ? " · " + esc(m.ts) : ""}</span></div></div>`;
}
// Phase 20: kanaluebergreifende Timeline (alle Firmen, alle Kanaele, chronologisch).
async function ladeTimeline() {
  let d; try { d = await (await fetch("/api/crm/timeline")).json(); } catch { d = null; }
  const win = WINS.timeline; if (!win) return;
  if (!d) { win.body.innerHTML = `<div class="app"><div class="leer">Timeline nicht verfügbar.</div></div>`; return; }
  const rows = (d.nachrichten || []).map(m => crmMsgRow(m, true)).join("") || `<div class="leer">Noch keine Nachrichten.</div>`;
  win.body.innerHTML = `<div class="app"><h3>Timeline — alle Kanäle</h3>${rows}</div>`;
}
// ---- content_ops: Trends (K2) ----------------------------------------------
let TRENDS = null;
const trendStatusLabels = { new: "Neu", reviewing: "In Prüfung", draft_created: "Entwurf erstellt", approved: "Freigegeben", published: "Veröffentlicht", ignored: "Ignoriert" };
function trendStatusLabel(s) { return trendStatusLabels[s] || s || ""; }
async function ladeTrends() {
  try { TRENDS = await (await fetch("/api/trends")).json(); } catch { TRENDS = null; }
  const win = WINS.trends; if (!win) return;
  if (!TRENDS) { win.body.innerHTML = `<div class="app"><div class="leer">Trends nicht verfügbar.</div></div>`; return; }
  const relFarbe = { high: "var(--green)", medium: "var(--cyan)", low: "var(--fg)" };
  const rows = (TRENDS.trends || []).map(t => `<div class="card">
    <div class="head"><span class="badge ${t.status === "approved" ? "freigegeben" : "in_umsetzung"}">${esc(trendStatusLabel(t.status))}</span><b>${esc(t.title)}</b><span class="meta" style="color:${relFarbe[t.relevance] || "var(--fg)"}">${esc(t.relevance || "")}${t.score != null ? " · " + t.score : ""}</span></div>
    ${t.description ? `<div class="desc">${esc(t.description)}</div>` : ""}
    <div class="meta">${esc(t.source_name || t.source_type || "")}${t.source_url ? ` · <a href="${esc(t.source_url)}" target="_blank" rel="noopener">Quelle ↗</a>` : ""}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${["reviewing", "approved", "ignored"].map(s => `<button class="btn" data-trendid="${esc(t.id)}" data-trendstatus="${s}">${esc(trendStatusLabel(s))}</button>`).join("")}</div>
  </div>`).join("") || `<div class="leer">Noch keine Trends. LUNAs Social-Media-Researcher füllt sie später (K3).</div>`;
  win.body.innerHTML = `<div class="app"><h3>Trend-Inbox</h3>${rows}</div>`;
}
async function trendStatus(id, status) {
  try { await fetch("/api/trends/" + encodeURIComponent(id) + "/status", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); } catch {}
  ladeTrends();
}
// ---- content_ops: Ideen-Labor (K2) -----------------------------------------
let IDEAS = null;
const ideaStatusLabels = { inbox: "Eingang", sorted: "Einsortiert", planned: "Geplant", in_progress: "In Arbeit", done: "Erledigt", archived: "Archiviert" };
function ideaStatusLabel(s) { return ideaStatusLabels[s] || s || ""; }
async function ladeIdeen() {
  try { IDEAS = await (await fetch("/api/ideas")).json(); } catch { IDEAS = null; }
  const win = WINS.ideas; if (!win) return;
  if (!IDEAS) { win.body.innerHTML = `<div class="app"><div class="leer">Ideen nicht verfügbar.</div></div>`; return; }
  const rows = (IDEAS.ideas || []).map(i => `<div class="card">
    <div class="head"><span class="badge ${i.status === "done" ? "freigegeben" : "in_umsetzung"}">${esc(ideaStatusLabel(i.status))}</span><b>${esc(i.title)}</b>${i.category ? `<span class="meta">${esc(i.category)}</span>` : ""}</div>
    ${i.description ? `<div class="desc">${esc(i.description)}</div>` : ""}
    ${i.ai_summary ? `<div class="meta">KI: ${esc(i.ai_summary)}</div>` : ""}${i.next_steps ? `<div class="meta">Naechste Schritte: ${esc(i.next_steps)}</div>` : ""}
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${["sorted", "planned", "done", "archived"].map(s => `<button class="btn" data-ideaid="${esc(i.id)}" data-ideastatus="${s}">${esc(ideaStatusLabel(s))}</button>`).join("")}</div>
  </div>`).join("") || `<div class="leer">Noch keine Ideen. LUNAs Agenten füllen sie später (K3).</div>`;
  win.body.innerHTML = `<div class="app"><h3>Ideen-Labor</h3>${rows}</div>`;
}
async function ideaStatus(id, status) {
  try { await fetch("/api/ideas/" + encodeURIComponent(id) + "/status", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); } catch {}
  ladeIdeen();
}
// ---- content_ops: Drafts (K2) ----------------------------------------------
let DRAFTS = null;
const draftStatusLabels = { idea: "Idee", in_progress: "In Arbeit", review: "Review", approved: "Freigegeben", scheduled: "Geplant", published: "Veröffentlicht", archived: "Archiviert" };
function draftStatusLabel(s) { return draftStatusLabels[s] || s || ""; }
async function ladeDrafts() {
  try { DRAFTS = await (await fetch("/api/drafts")).json(); } catch { DRAFTS = null; }
  const win = WINS.drafts; if (!win) return;
  if (!DRAFTS) { win.body.innerHTML = `<div class="app"><div class="leer">Drafts nicht verfügbar.</div></div>`; return; }
  const rows = (DRAFTS.drafts || []).map(d => `<div class="card">
    <div class="head"><span class="badge ${["approved", "published", "scheduled"].includes(d.status) ? "freigegeben" : "in_umsetzung"}">${esc(draftStatusLabel(d.status))}</span><b>${esc(d.title)}</b><span class="meta">${esc(d.platform || "")}${d.content_format ? " · " + esc(d.content_format) : ""}</span></div>
    ${d.hook ? `<div class="desc"><b>Hook:</b> ${esc(d.hook)}</div>` : ""}${d.caption ? `<div class="meta">${esc(d.caption)}</div>` : ""}
    ${(d.hashtags && d.hashtags.length) ? `<div class="meta">${d.hashtags.map(h => "#" + esc(h)).join(" ")}</div>` : ""}
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${["in_progress", "review", "approved", "scheduled", "published"].map(s => `<button class="btn" data-draftid="${esc(d.id)}" data-draftstatus="${s}">${esc(draftStatusLabel(s))}</button>`).join("")}</div>
  </div>`).join("") || `<div class="leer">Noch keine Drafts. LUNAs Content-Agenten füllen sie später (K3).</div>`;
  win.body.innerHTML = `<div class="app"><h3>Drafts</h3>${rows}</div>`;
}
async function draftStatus(id, status) {
  try { await fetch("/api/drafts/" + encodeURIComponent(id) + "/status", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); } catch {}
  ladeDrafts();
}
// ---- content_ops: Quellen (K2) ---------------------------------------------
let SOURCES = null;
async function ladeQuellen() {
  try { SOURCES = await (await fetch("/api/sources")).json(); } catch { SOURCES = null; }
  const win = WINS.quellen; if (!win) return;
  if (!SOURCES) { win.body.innerHTML = `<div class="app"><div class="leer">Quellen nicht verfügbar.</div></div>`; return; }
  const rows = (SOURCES.sources || []).map(s => `<div class="card">
    <div class="head"><span class="badge ${s.is_active ? "freigegeben" : "abgelehnt"}">${s.is_active ? "Aktiv" : "Inaktiv"}</span><b>${esc(s.name)}</b><span class="meta">${esc(s.source_type || "")}${s.priority != null ? " · Prio " + s.priority : ""}</span></div>
    ${s.url ? `<div class="meta"><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)} ↗</a></div>` : ""}
    <div style="margin-top:6px"><button class="btn" data-srcid="${esc(s.id)}" data-srcaktiv="${s.is_active ? "0" : "1"}">${s.is_active ? "Deaktivieren" : "Aktivieren"}</button></div>
  </div>`).join("") || `<div class="leer">Noch keine Quellen.</div>`;
  win.body.innerHTML = `<div class="app"><h3>Quellen</h3>${rows}</div>`;
}
async function sourceAktiv(id, aktiv) {
  try { await fetch("/api/sources/" + encodeURIComponent(id) + "/aktiv", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: aktiv === "1" }) }); } catch {}
  ladeQuellen();
}
// ---- K4: Team-Verwaltung (Rollen + Module) ---------------------------------
let TEAM = null;
const teamRolleLabel = { owner: "Owner (Voll)", admin: "Admin (Voll)", team: "Team (Content+CRM)", content: "Content", viewer: "Viewer" };
async function ladeTeam() {
  try { TEAM = await (await fetch("/api/team")).json(); } catch { TEAM = null; }
  const win = WINS.team; if (!win) return;
  if (!TEAM) { win.body.innerHTML = `<div class="app"><div class="leer">Team-Verwaltung nicht verfügbar.</div></div>`; return; }
  if (!TEAM.verfuegbar) { win.body.innerHTML = `<div class="app"><div class="leer">Nutzer-Tabelle nicht verfügbar — SQL-Migration <code>luna_os_users</code> in Supabase ausführen.</div></div>`; return; }
  const module = TEAM.module || [];
  const rollen = TEAM.rollen || ["content"];
  const users = (TEAM.users || []).map(u => `<div class="card">
    <div class="head"><span class="badge ${u.is_active === false ? "abgelehnt" : "freigegeben"}">${u.is_active === false ? "Inaktiv" : "Aktiv"}</span>
      <b>${esc(u.display_name || u.username)}</b><span class="meta">@${esc(u.username)} · ${esc(teamRolleLabel[u.role] || u.role || "")}</span></div>
    <div class="meta">Module: ${(u.allowed_modules || []).map(esc).join(", ") || "—"}${u.role === "owner" ? " (alle)" : ""}</div>
    <div style="margin-top:6px"><button class="btn" data-teamuser="${esc(u.username)}" data-teamaktiv="${u.is_active === false ? "1" : "0"}">${u.is_active === false ? "Aktivieren" : "Deaktivieren"}</button></div>
  </div>`).join("") || `<div class="leer">Noch keine Nutzer.</div>`;
  const modChecks = module.map(m => `<label class="team-modlbl"><input type="checkbox" class="team-mod" value="${esc(m.id)}"> ${esc(m.label)}</label>`).join("");
  const rollenOpts = rollen.map(r => `<option value="${esc(r)}">${esc(teamRolleLabel[r] || r)}</option>`).join("");
  win.body.innerHTML = `<div class="app">
    <h3>Neuen Nutzer anlegen</h3>
    <div class="team-form">
      <input id="team-username" placeholder="Benutzername (Login)" autocomplete="off">
      <input id="team-name" placeholder="Anzeigename (optional)" autocomplete="off">
      <input id="team-pw" type="password" placeholder="Passwort" autocomplete="new-password">
      <select id="team-role">${rollenOpts}</select>
      <div class="team-mods"><div class="team-mods-h">Module (leer = Standard der Rolle):</div>${modChecks}</div>
      <button class="btn primary" data-teamsave="1">Anlegen / aktualisieren</button>
      <div id="team-msg" class="team-msg"></div>
    </div>
    <h3 style="margin-top:14px">Nutzer (${(TEAM.users || []).length})</h3>
    ${users}
  </div>`;
}
async function teamAnlegen() {
  const g = (id) => (document.getElementById(id) || {}).value || "";
  const username = g("team-username").trim(), passwort = g("team-pw"), role = g("team-role") || "content";
  const display_name = g("team-name").trim();
  const mods = [...document.querySelectorAll(".team-mod:checked")].map(c => c.value);
  const msg = document.getElementById("team-msg");
  if (!username || !passwort) { if (msg) { msg.textContent = "Benutzername und Passwort sind Pflicht."; msg.className = "team-msg err"; } return; }
  let r; try { r = await (await fetch("/api/team", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, passwort, role, display_name, allowed_modules: mods.length ? mods : null }) })).json(); }
  catch { r = { ok: false, hinweis: "Netzwerkfehler." }; }
  if (msg) { msg.textContent = r.ok ? `Nutzer „${username}" gespeichert.` : ("Fehler: " + (r.hinweis || r.fehler || "unbekannt")); msg.className = "team-msg " + (r.ok ? "ok" : "err"); }
  if (r.ok) ladeTeam();
}
async function teamAktiv(username, aktiv) {
  try { await fetch("/api/team/" + encodeURIComponent(username) + "/aktiv", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ aktiv: aktiv === "1" }) }); } catch {}
  ladeTeam();
}
// ---- K5: Cutter (Reel-Jobs, geteilt Mac<->LUNA-OS) --------------------------
let CUTTER = null;
const cutBadge = { done: "freigegeben", running: "in_umsetzung", queued: "eingereicht", failed: "abgelehnt" };
const cutLabel = { done: "Fertig", running: "Läuft", queued: "In Warteschlange", failed: "Fehler" };
async function ladeCutter() {
  try { CUTTER = await (await fetch("/api/cutter")).json(); } catch { CUTTER = null; }
  const win = WINS.cutter; if (!win) return;
  if (!CUTTER) { win.body.innerHTML = `<div class="app"><div class="leer">Cutter nicht verfügbar.</div></div>`; return; }
  if (!CUTTER.verfuegbar) { win.body.innerHTML = `<div class="app"><div class="leer">Cutter-Jobs nicht verfügbar — SQL-Migration <code>cutter_jobs</code> in Supabase ausführen.</div></div>`; return; }
  const jobs = (CUTTER.jobs || []).map(j => {
    const st = j.status || "queued";
    const det = [
      j.clips_verwendet != null ? `${j.clips_verwendet} Clips` : "",
      j.dauer_sek != null ? `${j.dauer_sek}s` : "",
      j.untertitel ? `UT: ${esc(String(j.untertitel))}` : "",
      j.groesse_mb != null ? `${j.groesse_mb} MB` : "",
    ].filter(Boolean).join(" · ");
    return `<div class="card">
      <div class="head"><span class="badge ${cutBadge[st] || ""}">${cutLabel[st] || esc(st)}</span>
        <b>${esc(j.projekt || "—")}</b><span class="meta">${esc(j.quelle || "")}${j.created_at ? " · " + zeit(j.created_at) : ""}</span></div>
      ${det ? `<div class="meta">${esc(det)}</div>` : ""}
      ${j.reel_datei ? `<div class="meta">🎬 ${esc(j.reel_datei)}</div>` : ""}
      ${j.fehler ? `<div class="desc" style="color:var(--red)">${esc(j.fehler)}</div>` : ""}
      ${j.note ? `<div class="desc">${esc(j.note)}</div>` : ""}
    </div>`; }).join("") || `<div class="leer">Noch keine Reel-Jobs.</div>`;
  win.body.innerHTML = `<div class="app">
    <h3>Reel-Job anstoßen</h3>
    <div class="team-form">
      <input id="cut-projekt" placeholder="Ordnername in der Cutter-Inbox (z. B. hsv_stadion)" autocomplete="off">
      <input id="cut-note" placeholder="Notiz (optional)" autocomplete="off">
      <button class="btn primary" data-cuttersave="1">Job anstoßen</button>
      <div id="cut-msg" class="team-msg"></div>
      <div class="meta">Der Mac-Cutter holt den Job ab, schneidet den Ordner und meldet den Status hierher zurück. Posten bleibt CEO-Tor.</div>
    </div>
    <h3 style="margin-top:14px">Jobs & Historie (${(CUTTER.jobs || []).length})</h3>
    ${jobs}
  </div>`;
}
async function cutterJob() {
  const g = (id) => (document.getElementById(id) || {}).value || "";
  const projekt = g("cut-projekt").trim(), note = g("cut-note").trim();
  const msg = document.getElementById("cut-msg");
  if (!projekt) { if (msg) { msg.textContent = "Ordnername ist Pflicht."; msg.className = "team-msg err"; } return; }
  let r; try { r = await (await fetch("/api/cutter/job", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ projekt, note }) })).json(); }
  catch { r = { ok: false, hinweis: "Netzwerkfehler." }; }
  if (msg) { msg.textContent = r.ok ? `Job „${projekt}" in Warteschlange.` : ("Fehler: " + (r.hinweis || r.fehler || "unbekannt")); msg.className = "team-msg " + (r.ok ? "ok" : "err"); }
  if (r.ok) ladeCutter();
}
// ---- content_ops: AI-Inbox (K2) --------------------------------------------
let AIINBOX = null;
const recLabels = { use: "Nutzen", investigate: "Prüfen", later: "Später", ignore: "Ignorieren" };
async function ladeAiInbox() {
  try { AIINBOX = await (await fetch("/api/ai-inbox")).json(); } catch { AIINBOX = null; }
  const win = WINS.aiinbox; if (!win) return;
  if (!AIINBOX) { win.body.innerHTML = `<div class="app"><div class="leer">AI-Inbox nicht verfügbar.</div></div>`; return; }
  const rows = (AIINBOX.items || []).map(it => `<div class="card">
    <div class="head"><span class="badge ${it.recommendation === "use" ? "freigegeben" : (it.recommendation === "ignore" ? "abgelehnt" : "in_umsetzung")}">${esc(recLabels[it.recommendation] || it.recommendation || "—")}</span><b>${esc(it.title || "(ohne Titel)")}</b><span class="meta">${esc(it.source_type || "")}${it.author ? " · " + esc(it.author) : ""}</span></div>
    ${it.summary ? `<div class="desc">${esc(it.summary)}</div>` : ""}
    <div class="meta">Relevanz ${it.hcc_relevance_score ?? "?"} · Machbarkeit ${it.feasibility_score ?? "?"} · Risiko ${it.risk_score ?? "?"}${it.source_url ? ` · <a href="${esc(it.source_url)}" target="_blank" rel="noopener">Quelle ↗</a>` : ""}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${["use", "investigate", "later", "ignore"].map(rc => `<button class="btn" data-aiid="${esc(it.id)}" data-airec="${rc}">${esc(recLabels[rc])}</button>`).join("")}</div>
  </div>`).join("") || `<div class="leer">AI-Inbox leer.</div>`;
  win.body.innerHTML = `<div class="app"><h3>AI-Inbox</h3>${rows}</div>`;
}
async function aiRec(id, rec) {
  try { await fetch("/api/ai-inbox/" + encodeURIComponent(id) + "/recommendation", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ recommendation: rec }) }); } catch {}
  ladeAiInbox();
}
// Detailansicht zu einem Wert (Aktie: Profil + Quote + News; Krypto: CoinGecko-Infos).
async function openInvestDetail(symbol, asset) {
  const wid = "invdet:" + symbol;
  if (WINS[wid]) { WINS[wid].focus(); return; }
  const win = new WinBox("📈  " + symbol, { ...(istMobil() ? winGeom() : { width: "480px", height: "64%", x: "center", y: "center" }),
    class: ["modern"], onclose: () => { delete WINS[wid]; return false; } });
  WINS[wid] = win;
  win.body.innerHTML = `<div class="app"><div class="leer">Lade Infos zu ${esc(symbol)}…</div></div>`;
  try {
    const d = await (await fetch(`/api/investment/detail?symbol=${encodeURIComponent(symbol)}&asset=${encodeURIComponent(asset || "aktie")}`)).json();
    win.body.innerHTML = `<div class="app detail">${asset === "krypto" ? invDetailKrypto(d) : invDetailAktie(d)}</div>`;
  } catch { win.body.innerHTML = `<div class="app"><div class="leer">Konnte Infos nicht laden.</div></div>`; }
}
const kvz = (k, v) => v != null && v !== "" ? `<div class="kv"><span class="k">${esc(k)}</span><b>${esc(v)}</b></div>` : "";
const linkRow = (l) => `<div class="kv"><span class="k">${esc(l.label)}</span><b><a href="${esc(l.url)}" target="_blank" rel="noopener">öffnen ↗</a></b></div>`;
const rsiFarbe = { ueberkauft: "var(--red)", ueberverkauft: "var(--green)", neutral: "var(--cyan)" };
// Kursverlauf aus unserer eigenen angesammelten Historie (Tages-Closes + SMA-20). Inline-SVG, kein CDN.
function invKursHtml(h) {
  if (!h || h.length < 2)
    return `<h3>Kursverlauf</h3><div class="leer">Noch zu wenig Historie — der Loop sammelt täglich einen Kurs.</div>`;
  const W = 440, H = 140, pad = 26;
  const closes = h.map(p => p.close);
  const smas = h.map(p => p.sma20).filter(v => v != null);
  const lo = Math.min(...closes, ...(smas.length ? smas : [Infinity]));
  const hi = Math.max(...closes, ...(smas.length ? smas : [-Infinity]));
  const span = (hi - lo) || 1;
  const x = i => pad + (h.length <= 1 ? 0 : i * (W - 2 * pad) / (h.length - 1));
  const y = v => H - pad - ((v - lo) / span) * (H - 2 * pad);
  const closePath = h.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p.close).toFixed(1)}`).join(" ");
  const smaPts = h.map((p, i) => p.sma20 != null ? `${x(i).toFixed(1)} ${y(p.sma20).toFixed(1)}` : null).filter(Boolean);
  const smaPath = smaPts.length > 1 ? "M" + smaPts.join(" L") : "";
  const last = closes[closes.length - 1];
  return `<h3>Kursverlauf <span class="meta">eigene Historie · ${h.length} Tage</span></h3>
    <svg viewBox="0 0 ${W} ${H}" class="inv-svg kurs" preserveAspectRatio="none" role="img">
      ${smaPath ? `<path d="${smaPath}" class="inv-line sma"/>` : ""}<path d="${closePath}" class="inv-line close"/></svg>
    <div class="inv-leg"><span><i class="close"></i>Kurs ${last}</span>${smaPts.length ? `<span><i class="sma"></i>SMA-20</span>` : ""}
      <span class="meta">${esc(h[0].datum)} → ${esc(h[h.length - 1].datum)}</span></div>`;
}
function invDetailAktie(d) {
  const p = d.profil, q = d.quote, r = d.rsi;
  const news = (d.news || []).map(n => `<div class="row"><div><b>${esc(n.titel)}</b><br><span class="meta">${esc(n.quelle || "")}</span></div></div>`).join("");
  const links = (d.links || []).map(linkRow).join("");
  const hinweis = (d.hinweise || []).length ? `<div class="leer">${esc(d.hinweise[0])}</div>` : "";
  return `<div class="head"><b>${esc((p && p.name) || d.symbol)}</b></div>
    ${p ? `<div class="meta">${esc(p.branche || "")}${p.boerse ? " · " + esc(p.boerse) : ""}${p.land ? " · " + esc(p.land) : ""}</div>` : ""}
    ${invKursHtml(d.kurs_historie)}
    ${q ? kvz("Preis", q.preis) + kvz("Veränderung", (q.veraenderung_pct > 0 ? "+" : "") + q.veraenderung_pct + "%") + kvz("Tageshoch", q.hoch) + kvz("Tagestief", q.tief) : ""}
    ${r ? `<div class="kv"><span class="k">RSI (14)</span><b style="color:${rsiFarbe[r.label] || "var(--fg)"}">${esc(r.wert)} · ${esc(r.label)}</b></div>` : ""}
    ${p ? kvz("Marktkap. (Mio)", p.marktkap_mio) + kvz("IPO", p.ipo) : ""}
    ${links ? `<h3>Weitere Infos</h3>${links}` : ""}
    ${news ? `<h3>News</h3>${news}` : ""}${hinweis}`;
}
function invDetailKrypto(d) {
  const i = d.info || {};
  if (!i.ok) return `<div class="leer">Keine Krypto-Infos verfügbar.</div>`;
  return `<div class="head"><b>${esc(i.name)} (${esc(i.symbol)})</b></div>
    ${invKursHtml(d.kurs_historie)}
    ${kvz("Rang", i.rang ? "#" + i.rang : "")}${kvz("Preis (EUR)", i.preis_eur)}
    ${kvz("Veränderung 24h", (i.veraenderung_pct > 0 ? "+" : "") + Number(i.veraenderung_pct || 0).toFixed(2) + "%")}
    ${kvz("Marktkap. (EUR)", i.marktkap_eur)}${kvz("24h-Volumen (EUR)", i.volumen_eur)}
    ${kvz("ATH (EUR)", i.ath_eur)}${kvz("ATL (EUR)", i.atl_eur)}
    ${i.homepage ? linkRow({ label: "Website", url: i.homepage }) : ""}
    ${i.beschreibung ? `<h3>Über</h3><div class="desc full">${esc(i.beschreibung)}</div>` : ""}`;
}
let _invSucheTimer = null;
function investSuche(q) {
  clearTimeout(_invSucheTimer);
  const box = document.getElementById("inv-suggest"); if (!box) return;
  q = (q || "").trim();
  if (q.length < 2) { box.innerHTML = ""; box.classList.remove("open"); return; }
  _invSucheTimer = setTimeout(async () => {
    try {
      const d = await (await fetch("/api/investment/suche?q=" + encodeURIComponent(q))).json();
      const t = d.treffer || [];
      box.innerHTML = t.length ? t.map(x => `<div class="ac-item" data-acsym="${esc(x.symbol)}" data-acasset="${esc(x.asset)}"><b>${esc(x.ticker || x.symbol)}</b> <span class="meta">${esc(x.name || "")} · ${esc(x.asset)}</span></div>`).join("")
        : `<div class="ac-item leer">keine Treffer</div>`;
      box.classList.add("open");
    } catch { box.innerHTML = ""; }
  }, 300);
}
async function investWatchAddDirect(symbol, asset) {
  try { await fetch("/api/investment/watchlist", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, asset: asset || "aktie" }) }); } catch {}
  const box = document.getElementById("inv-suggest"); if (box) { box.innerHTML = ""; box.classList.remove("open"); }
  const inp = document.getElementById("inv-sym"); if (inp) inp.value = "";
  ladeInvestment();
}
async function investWatchRemove(symbol) {
  try { await fetch("/api/investment/watchlist/remove", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }) }); } catch {}
  ladeInvestment();
}

// ---- Second Brain (Wissen) -------------------------------------------------
let BRAIN_ITEMS = [];
function renderWissen() {
  const liste = (BRAIN_ITEMS || []).map(e => `<div class="card">
      <div class="head"><b>${esc(e.titel || e.text.slice(0, 50))}</b></div>
      ${e.tags && e.tags.length ? `<div class="meta">${e.tags.map(esc).join(" · ")}</div>` : ""}
      <div class="desc">${esc(e.text)}</div></div>`).join("");
  return `<div class="app">
    <div class="brain-bar">
      <input id="brain-q" placeholder="Wissen durchsuchen (intern + Gmail + Drive)…" autocomplete="off">
      <button class="btn info" onclick="brainSuchen()">🔍 Suchen</button>
    </div>
    <div id="brain-results">${liste || `<div class="leer">Noch kein Wissen gespeichert. Merk dir was unten. 🧠</div>`}</div>
    <div class="brain-add">
      <input id="brain-note" placeholder="Neues Wissen merken…" autocomplete="off">
      <button class="btn ok" onclick="brainMerken()">＋ Merken</button>
    </div></div>`;
}
async function ladeWissen() {
  try { BRAIN_ITEMS = (await (await fetch("/api/brain")).json()).items || []; } catch { BRAIN_ITEMS = []; }
  renderApp("wissen");
}
async function brainSuchen() {
  const q = (document.getElementById("brain-q") || {}).value || "";
  const box = document.getElementById("brain-results");
  if (box) box.innerHTML = `<div class="leer">Suche…</div>`;
  try {
    const d = await (await fetch("/api/brain?q=" + encodeURIComponent(q.trim()))).json();
    const t = (d.treffer || []);
    if (box) box.innerHTML = t.length ? t.map(x => `<div class="card">
      <div class="head"><span class="badge eingereicht">${esc(x.quelle)}</span><b>${esc(x.titel)}</b></div>
      <div class="desc">${esc(x.text)}</div></div>`).join("") : `<div class="leer">Keine Treffer.</div>`;
  } catch { if (box) box.innerHTML = `<div class="leer">Suche fehlgeschlagen.</div>`; }
}
async function brainMerken() {
  const inp = document.getElementById("brain-note"); const text = (inp && inp.value || "").trim();
  if (!text) return;
  try { await fetch("/api/brain", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }) }); if (inp) inp.value = ""; ladeWissen(); } catch { alert("Konnte nicht merken."); }
}

// ---- Lagebild (proaktive Tages-Insights) -----------------------------------
async function ladeLagebild() {
  let d;
  try { d = (await (await fetch("/api/lagebild")).json()).daten; } catch { d = null; }
  const win = WINS.lagebild; if (!win) return;
  if (!d) { win.body.innerHTML = `<div class="app"><div class="leer">Lagebild nicht verfügbar.</div></div>`; return; }
  const sek = (titel, zeilen) => zeilen.length
    ? `<h3>${esc(titel)}</h3>` + zeilen.map(z => `<div class="row"><div>${z}</div></div>`).join("") : "";
  const ent = (d.entscheidungen || []).map(x => `<b>${esc(x.titel)}</b> <span class="meta">[${esc(x.id)}] ${esc(x.status)}</span>`);
  const term = (d.termine_heute || []).map(x => `<b>${esc(x.zeit)}</b> ${esc(x.titel)}`);
  const mails = d.mails && d.mails.verfuegbar ? (d.mails.liste || []).map(x => `<b>${esc(x.von)}</b>: ${esc(x.betreff)}`) : [];
  const tick = (d.tickets || []).map(x => `${esc(x.frage)} <span class="meta">[${esc(x.id)}]</span>`);
  const ag = (d.agenda || []).map(esc);
  const body = sek("Auf dich warten", ent) + sek("Heute im Kalender", term)
    + (d.mails && d.mails.verfuegbar ? sek(`Ungelesene Mails (${d.mails.anzahl})`, mails) : "")
    + sek("Offene Research-Tickets", tick) + sek("Agenda", ag);
  win.body.innerHTML = `<div class="app detail">${body || `<div class="leer">Alles ruhig. Nichts Dringendes. 👍</div>`}</div>`;
}

// Sprach-/Text-Befehle: "zeig mir die Aufträge", "öffne Finanzen" -> passende App einblenden.
// Funktioniert per Tippen UND per Mikrofon, auf jedem Geraet (Handy/Rechner/iPad).
const APP_SYNONYME = [
  ["auftraege", ["auftrag", "auftraege", "aufträge", "antrag", "anträge", "antraege", "aufgabe", "aufgaben", "freigabe", "freigaben", "inbox"]],
  ["meldungen", ["meldung", "meldungen", "benachrichtigung", "benachrichtigungen", "nachrichten"]],
  ["aktivitaet", ["aktivität", "aktivitaet", "aktivitäten", "protokoll", "verlauf", "log", "historie"]],
  ["research", ["research", "recherche", "ticket", "tickets", "suche"]],
  ["agenten", ["agenten", "agent", "mindmap", "map", "organigramm", "team", "abteilungen"]],
  ["finance", ["finanzen", "finance", "budget", "kosten", "geld"]],
];
const ZEIG_VERB = /\b(zeig|zeige|öffne|oeffne|öffnen|oeffnen|anzeigen|geh|gehe|wechsel|wechsle|zeig mir|ruf|rufe|starte|öffn)\b/;
function versucheKontextBefehl(text) {
  const t = " " + text.toLowerCase().trim() + " ";
  const istBefehl = ZEIG_VERB.test(t) || t.trim().split(/\s+/).length <= 2; // kurze Eingaben gelten als Befehl
  for (const [id, woerter] of APP_SYNONYME) {
    if (woerter.some(w => t.includes(" " + w) || t.includes(w + " "))) {
      if (!istBefehl) return null;
      openApp(id);
      return APPS[id].titel;
    }
  }
  return null;
}
// Erkennt, ob eine FRAGE eine Ansicht betrifft (auch ohne „zeig") -> dann blendet LUNA das Panel ein
// und erklaert die Daten dazu. Z. B. „welche Anträge sind offen?" -> Auftraege-Fenster + gesprochene Erklaerung.
function panelFuerFrage(text) {
  const t = " " + text.toLowerCase() + " ";
  for (const [id, woerter] of APP_SYNONYME) {
    if (woerter.some(w => t.includes(" " + w) || t.includes(w + " "))) return id;
  }
  return null;
}

function renderAuftraege() {
  if (!STATE.antraege.length) return `<div class="app"><div class="leer">Keine offenen Aufträge. 🎉<br>LUNA meldet sich, wenn etwas ansteht.</div></div>`;
  const cards = STATE.antraege.map(a => {
    const lang = a.beschreibung.length > 240;
    const freigeben = a.status === "eingereicht"
      ? `<button class="btn ok" data-act="freigeben" data-id="${esc(a.id)}">✓ Freigeben</button>` : "";
    const ablehnen = (a.status === "eingereicht" || a.status === "freigegeben")
      ? `<button class="btn warn" data-act="ablehnen" data-id="${esc(a.id)}">✕ Ablehnen</button>` : "";
    const revidieren = (a.status === "eingereicht" || a.status === "freigegeben")
      ? `<button class="btn info" data-act="revidieren" data-id="${esc(a.id)}" title="Feedback geben, LUNA überarbeitet (z. B. günstiger/kostenlos)">✏️ Revidieren</button>` : "";
    return `<div class="card">
      <div class="head"><span class="badge ${esc(a.status)}">${esc(a.status)}</span><b class="titel" data-detail="${esc(a.id)}" title="Details anzeigen">${esc(a.titel)}</b></div>
      <div class="meta">von ${esc(a.von)}${a.kategorie ? " · " + esc(a.kategorie) : ""} · ${esc(a.id)}</div>
      <div class="desc">${esc(a.beschreibung) || "<i>keine Beschreibung</i>"}</div>
      ${lang ? `<div class="mehr" data-mehr>mehr anzeigen ▾</div>` : ""}
      <div class="actions">
        ${freigeben}${ablehnen}${revidieren}
        <button class="btn ghost" data-detail="${esc(a.id)}">📄 Details</button>
        <button class="btn info" data-act="mehr-info" data-id="${esc(a.id)}">🔍 Mehr Info holen</button>
        <button class="btn danger" data-act="loeschen" data-id="${esc(a.id)}">🗑 Löschen</button>
      </div></div>`;
  }).join("");
  const bar = `<div class="actions" style="margin:0 0 8px 0"><button class="btn ghost" data-batch="reformat" title="Alle offenen Anträge ins neue Format bringen; freigegebene werden zurückgesetzt">🔄 Alle neu formatieren</button></div>`;
  return `<div class="app">${bar}${cards}</div>`;
}

// ---- Agenten-Mindmap (lebendiges Organigramm mit Live-Status) ---------------
let AGENTEN = null;
async function ladeAgenten() {
  try { AGENTEN = await (await fetch("/api/agenten")).json(); } catch { AGENTEN = null; }
  renderApp("agenten");
}
function renderAgenten() {
  if (!AGENTEN) return `<div class="app"><div class="leer">Lade Organigramm…</div></div>`;
  const deps = AGENTEN.departments || [], ceo = AGENTEN.ceo || {}, luna = AGENTEN.luna || {};
  // Top-down-Baum: CEO -> LUNA -> Abteilungen auf ZWEI Reihen (A/B) je ~8 -> Unter-Agenten darunter.
  // Zwei Reihen halten die Breite bei ~830px (statt ~1580px bei einer Reihe) -> kein Horizontal-Scroll.
  const bw = 92, bh = 34, colStep = 100, padX = 18, padTop = 20, vGap = 66, subStep = 40, rowGap = 34;
  const n = deps.length || 1;
  const half = Math.ceil(n / 2);
  const rowA = deps.slice(0, half), rowB = deps.slice(half);
  const cols = Math.max(rowA.length, rowB.length, 1);
  const W = padX * 2 + (cols - 1) * colStep + bw;
  const centerX = W / 2;
  // Spalten-Zentrum: jede Reihe wird mittig unter LUNA ausgerichtet.
  const rowX = (row, j) => centerX - ((row.length - 1) * colStep) / 2 + j * colStep;
  const rowMaxSub = row => Math.max(0, ...row.map(d => (d.subs || []).length));
  const maxSubA = rowMaxSub(rowA), maxSubB = rowMaxSub(rowB);
  const yCEO = padTop + bh / 2, yLUNA = yCEO + vGap;
  const yDEPA = yLUNA + vGap, ySUBA = yDEPA + vGap;
  // Unterkante der Reihe-A-Subs; darunter (mit rowGap) beginnt Reihe B -> keine Kollision.
  const subABottom = maxSubA > 0 ? ySUBA + (maxSubA - 1) * subStep : yDEPA;
  const yDEPB = subABottom + rowGap + vGap, ySUBB = yDEPB + vGap;
  const subBBottom = maxSubB > 0 ? ySUBB + (maxSubB - 1) * subStep : yDEPB;
  const H = subBBottom + bh / 2 + 12;
  const box = (cxp, y, w, titel, cls, sub, tip) => {
    const t = sub
      ? `<text x="${cxp}" y="${y - 3}" text-anchor="middle" class="mm-bt">${esc(titel)}</text><text x="${cxp}" y="${y + 10}" text-anchor="middle" class="mm-bs">${esc(sub)}</text>`
      : `<text x="${cxp}" y="${y + 4}" text-anchor="middle" class="mm-bt">${esc(titel)}</text>`;
    return `<g class="mm-b ${cls}">${tip ? `<title>${esc(tip)}</title>` : ""}<rect x="${cxp - w / 2}" y="${y - bh / 2}" width="${w}" height="${bh}" rx="8"/>${t}</g>`;
  };
  // vertikale Elbow-Verbindung (Eltern unten -> Kind oben)
  const vlink = (x1, y1, x2, y2, cls) => { const my = (y1 + y2) / 2; return `<path d="M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}" class="mm-link ${cls}"/>`; };
  let links = vlink(centerX, yCEO + bh / 2, centerX, yLUNA - bh / 2, "human"), nodes = "";
  const drawRow = (row, yDEP, ySUB) => {
    row.forEach((d, i) => {
      const cx = rowX(row, i);
      links += vlink(centerX, yLUNA + bh / 2, cx, yDEP - bh / 2, d.status);
      const num = (d.name.split("·")[0] || "").trim();
      const kuerzel = (d.name.split("·")[1] || d.name).trim();
      nodes += box(cx, yDEP, bw, kuerzel, "dep " + d.status, num, d.rolle);
      (d.subs || []).forEach((s, j) => {
        const sy = ySUB + j * subStep;
        const py = j === 0 ? yDEP + bh / 2 : sy - subStep + bh / 2;
        links += vlink(cx, py, cx, sy - bh / 2, s.status);
        nodes += box(cx, sy, bw, s.name, "sub " + s.status, "", s.name);
      });
    });
  };
  drawRow(rowA, yDEPA, ySUBA);
  drawRow(rowB, yDEPB, ySUBB);
  nodes += box(centerX, yCEO, 122, ceo.name || "CEO", "human", ceo.rolle);
  nodes += box(centerX, yLUNA, 138, luna.name || "LUNA", "luna", luna.rolle || "Head of Agents");
  const legend = `<div class="mm-legend"><span class="lg active"><i></i>Aktiv</span><span class="lg standby"><i></i>Standby</span><span class="lg offline"><i></i>Geplant</span><span class="lg human"><i></i>CEO</span></div>`;
  return `<div class="app mindmap">
    <div class="mm-head"><b>Organigramm — Live-Status</b>${legend}</div>
    <div class="mm-scroll"><svg viewBox="0 0 ${W} ${H}" class="mm-svg" preserveAspectRatio="xMidYMid meet" style="min-width:${W}px">
      ${links}${nodes}
    </svg></div></div>`;
}

function renderListe(key, cols) {
  return () => {
    const arr = STATE[key] || [];
    if (!arr.length) return `<div class="app"><div class="leer">Nichts vorhanden.</div></div>`;
    const rows = arr.map(x => { const [a, b, t] = cols(x);
      return `<div class="row"><span class="t">${esc(zeit(t) || a)}</span><div><b>${esc(a)}</b><br>${esc(b)}</div></div>`;
    }).join("");
    return `<div class="app">${rows}</div>`;
  };
}

function renderFinance() {
  return `<div class="app"><div class="kv"><span class="k">Monatsbudget</span><b>${esc(STATE.finance.monatsbudget || "unbekannt")}</b></div>
    <div class="kv"><span class="k">Offene Aufträge</span><b>${STATE.antraege.length}</b></div>
    <div class="kv"><span class="k">Offene Research-Tickets</span><b>${STATE.research.length}</b></div></div>`;
}

// ---- Fenster ---------------------------------------------------------------
const istMobil = () => window.matchMedia("(max-width: 640px)").matches;
// Auf schmalen Screens fuellen Fenster (fast) den Bildschirm; sonst gestaffelt/kompakt.
function winGeom(breite, hoehe, off) {
  // Mobil: Fenster fuellt die Breite und laesst oben die Top-Bar (38) und unten das Dock (~84) frei,
  // damit die Chat-Eingabe nicht hinter dem Dock verschwindet.
  if (istMobil()) return { width: "100%", height: Math.max(280, window.innerHeight - 38 - 84) + "px", x: 0, y: 38 };
  return { width: breite, height: hoehe, x: 90 + (off || 0), y: 60 + (off || 0) };
}
let zaehler = 0;
function openApp(id) {
  const app = APPS[id];
  if (!app) return;
  if (!darf(id)) return;   // K4: kein Zugriff auf dieses Modul
  if (WINS[id]) { WINS[id].focus(); return; }
  const off = (zaehler++ % 5) * 34;
  const win = new WinBox(`${app.icon}  ${app.titel}`, {
    ...winGeom("560px", "72%", off), class: ["modern"],
    onclose: () => { delete WINS[id]; return false; },
  });
  WINS[id] = win;
  renderApp(id);
  if (app.load) app.load();  // App laedt ihre Daten selbst (z. B. Wissen, Lagebild)
}
function renderApp(id) {
  if (WINS[id]) WINS[id].body.innerHTML = APPS[id].render();
}
function renderOffene() { Object.keys(WINS).forEach(renderApp); }

// ---- Sidebar-Navigation ----------------------------------------------------
const NAV = [
  { id: "home", icon: "▦", label: "Command Center" },
  { id: "auftraege", icon: "📋", label: "Aufträge", count: () => STATE.antraege.length },
  { id: "lagebild", icon: "📡", label: "Lagebild" },
  { id: "wissen", icon: "🧠", label: "Wissen" },
  { id: "investment", icon: "📈", label: "Investment" },
  { id: "crm", icon: "🤝", label: "Collab-CRM" },
  { id: "timeline", icon: "🕒", label: "Timeline" },
  { id: "trends", icon: "🔥", label: "Trends" },
  { id: "ideas", icon: "💡", label: "Ideen-Labor" },
  { id: "drafts", icon: "✍️", label: "Drafts" },
  { id: "quellen", icon: "📡", label: "Quellen" },
  { id: "aiinbox", icon: "🧩", label: "AI-Inbox" },
  { id: "cutter", icon: "🎬", label: "Cutter" },
  { id: "research", icon: "🔍", label: "Research", count: () => STATE.research.length },
  { id: "meldungen", icon: "🔔", label: "Meldungen", count: () => STATE.meldungen.length },
  { id: "aktivitaet", icon: "📊", label: "Aktivität" },
  { id: "agenten", icon: "🕸️", label: "Agenten-Map" },
  { id: "finance", icon: "💶", label: "Finanzen" },
  { id: "team", icon: "👥", label: "Team" },
  { id: "luna", icon: "💬", label: "LUNA-Chat" },
];
let AKTIV_NAV = "home";
function buildSidebar() {
  const nav = document.getElementById("nav");
  nav.innerHTML = NAV.filter(n => darf(n.id)).map(n => `<div class="nav-item${n.id === AKTIV_NAV ? " active" : ""}" data-app="${n.id}">
    <span class="nico">${n.icon}</span><span>${esc(n.label)}</span><span class="ncount" data-ncount="${n.id}" hidden></span></div>`).join("");
  updateSidebarCounts();
  zeigeNutzer();
}
// K4: Nutzer-Chip in der Brand-Leiste (Name + Rolle). Owner = CEO/Voll.
function zeigeNutzer() {
  const block = document.querySelector(".brand-block");
  if (!block || !ME.username) return;
  let chip = document.getElementById("user-chip");
  if (!chip) {
    chip = document.createElement("div");
    chip.id = "user-chip";
    block.appendChild(chip);
  }
  const rolle = ME.role === "owner" ? "Voll-Zugriff" : esc(ME.role || "");
  chip.innerHTML = `<span class="uc-ava">${esc((ME.display_name || ME.username || "?")[0].toUpperCase())}</span>
    <span class="uc-txt"><b>${esc(ME.display_name || ME.username)}</b><small>${rolle}</small></span>`;
}
function updateSidebarCounts() {
  NAV.forEach(n => {
    const el = document.querySelector(`[data-ncount="${n.id}"]`); if (!el) return;
    const c = n.count ? n.count() : 0; el.hidden = !c; el.textContent = c;
  });
  document.querySelectorAll(".nav-item").forEach(el =>
    el.classList.toggle("active", el.dataset.app === AKTIV_NAV));
}
function navTo(id) {
  if (!darf(id)) return;   // K4: nicht-erlaubte Bereiche ignorieren
  if (id === "home") { AKTIV_NAV = "home"; renderDashboard(); updateSidebarCounts(); }
  else if (id === "luna") { AKTIV_NAV = "luna"; openLuna(); updateSidebarCounts(); }
  else { AKTIV_NAV = id; openApp(id); updateSidebarCounts(); }
  document.getElementById("sidebar").classList.remove("open");  // mobil zuklappen
}

// ---- Command-Center-Dashboard ----------------------------------------------
let OVERVIEW = { counts: {}, providers: [], agenten: [], providers_connected: 0 };
let LAGE = { daten: {} };

function gauge(val, max, label) {
  const r = 30, c = 2 * Math.PI * r, frac = Math.max(0, Math.min(1, max ? val / max : 0));
  return `<div class="gauge"><svg viewBox="0 0 76 76">
    <circle cx="38" cy="38" r="${r}" fill="none" stroke="rgba(120,170,255,.15)" stroke-width="6"/>
    <circle cx="38" cy="38" r="${r}" fill="none" stroke="#2ee6ff" stroke-width="6" stroke-linecap="round"
      stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${(c * (1 - frac)).toFixed(1)}" transform="rotate(-90 38 38)"/>
    <text class="gv" x="38" y="43" text-anchor="middle">${val}</text></svg>
    <div class="glabel">${esc(label)}</div></div>`;
}
function panel(titel, inhalt, opts = {}) {
  const head = `<div class="panel-h"><span>${esc(titel)}</span>${opts.right || ""}</div>`;
  return `<div class="panel${opts.cls ? " " + opts.cls : ""}">${head}${inhalt}</div>`;
}

function renderDashboard() {
  const main = document.getElementById("cc-main"); if (!main) return;
  const c = OVERVIEW.counts || {};
  const d = LAGE.daten || {};

  // Hero / AI Core
  const hero = `<div class="panel hero col-2">
    <div class="hero-core"><span class="globe"></span><span class="orbit"></span>
      <div id="luna-orb" class="idle" title="LUNA — antippen und sprechen">
        <span class="orb-ring r1"></span><span class="orb-ring r2"></span><span class="orb-core"></span></div></div>
    <div class="htitle">LUNA</div><div class="hsub">AI CORE</div><div class="hver">v3 · Command Center</div></div>`;

  // AI Core Overview
  const ov = panel("AI Core Overview", `
    ${ovItem("🌙", "LUNA Core", "Head of Agents", "active")}
    ${ovItem("🧠", "Memory", (c.wissen || 0) + " Wissens-Einträge", (c.wissen ? "active" : "off"))}
    ${ovItem("🔊", "Voice", "ElevenLabs (Lola)", "active")}
    ${ovItem("🤖", "Agents", "14 Abteilungen", "active")}
    ${ovItem("🧩", "LLMs", OVERVIEW.providers_connected + " verbunden", (OVERVIEW.providers_connected ? "active" : "off"))}
    ${ovItem("🛡️", "System", "Optimal", "active")}`);

  // Live Intelligence Feed (Meldungen)
  const feedItems = (STATE.meldungen || []).slice(0, 6).map(m => `<div class="feed-item">
    <span class="fi">🔔</span><div><div class="ft">${esc((m.text || "").slice(0, 70))}</div>
    <div class="fs">${esc(m.abteilung || "")}</div></div><span class="tag info">INFO</span></div>`).join("");
  const feed = panel("Live Intelligence Feed", feedItems || `<div class="leer">Keine neuen Meldungen.</div>`,
    { right: `<span class="livep"><span class="dot"></span>LIVE</span>` });

  // Active Agents
  const agentCards = (OVERVIEW.agenten || []).map(a => `<div class="agent ${a.status}">
    <div class="an">${esc(a.name)}</div><span class="pill ${a.status}"><span class="dot"></span>${a.status === "active" ? "Active" : "Standby"}</span>
    <div class="aw"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div>`).join("");
  const agents = panel("Active Agents", `<div class="agents-grid">${agentCards}</div>`,
    { cls: "col-2", right: `<span class="right" data-app="agenten">Map ›</span>` });

  // Mission Timeline (heutige Termine)
  const tl = (d.termine_heute || []).map(t => `<div class="tl-item"><span class="tlz">${esc(t.zeit)}</span><span class="tlt">${esc(t.titel)}</span></div>`).join("");
  const timeline = panel("Mission Timeline — Heute", tl || `<div class="leer">Heute keine Termine.</div>`,
    { right: `<span class="right" data-app="lagebild">Lagebild ›</span>` });

  // Quick Commands
  const quick = panel("Quick Commands", `<div class="qc-grid">
    <button class="qc" data-cmd="talk"><span class="qci">🎙️</span>Sprach-Gespräch starten</button>
    <button class="qc" data-cmd="auftraege"><span class="qci">📋</span>Aufträge öffnen</button>
    <button class="qc" data-cmd="wissen"><span class="qci">🧠</span>Wissen durchsuchen</button>
    <button class="qc" data-cmd="lagebild"><span class="qci">📡</span>Lagebild anzeigen</button></div>`);

  // System Monitor (echte LUNA-Zahlen)
  const sysmon = panel("System Monitor", `<div class="gauges">
    ${gauge(c.antraege || 0, 10, "Aufträge")}${gauge(c.research || 0, 10, "Tickets")}
    ${gauge(c.wissen || 0, 20, "Wissen")}${gauge(c.meldungen || 0, 10, "Meldungen")}</div>`);

  // Memory Insights
  const mem = panel("Memory Insights", `
    <div class="kv"><span class="k">Wissens-Einträge</span><b>${c.wissen || 0}</b></div>
    <div class="kv"><span class="k">Offene Research-Tickets</span><b>${c.research || 0}</b></div>
    <div class="kv"><span class="k">Aktivitäts-Einträge</span><b>${c.aktivitaet || 0}</b></div>
    <div class="kv"><span class="k">Monatsbudget</span><b>${esc(OVERVIEW.monatsbudget || "—")}</b></div>`,
    { right: `<span class="right" data-app="wissen">Wissen ›</span>` });

  // LLM / Provider Status
  const provs = (OVERVIEW.providers || []).map(p => `<div class="prov ${p.connected ? "on" : "off"}">
    <div><div class="pn">${esc(p.name)}</div><div class="ps">${p.connected ? "Verbunden" : "Nicht verknüpft"}</div></div>
    <span class="pd"></span></div>`).join("");
  const llm = panel("LLM / Provider Status", `<div class="prov-grid">${provs}</div>`,
    { right: `<span class="livep"><span class="dot"></span>${OVERVIEW.providers_connected} aktiv</span>` });

  // Investment (advisory)
  const iv = INVEST || {};
  const ivtop = (iv.shortlist || []).slice(0, 4).map(s => { const c = s.veraenderung_pct;
    return `<div class="row"><span class="t" style="color:${c >= 0 ? "var(--green)" : "var(--red)"}">${(c > 0 ? "+" : "") + (c == null ? "?" : Number(c).toFixed(1))}%</span><div><b>${esc(s.symbol)}</b> <span class="meta">${esc(s.asset || "")}</span></div></div>`; }).join("");
  const ivsc = iv.scorecard || {};
  const investP = panel("Investment (CIO)", `
    <div class="kv"><span class="k">Modus</span><b>${esc(iv.modus || "advisory")}</b></div>
    <div class="kv"><span class="k">Trefferquote</span><b>${ivsc.ausgewertet ? Math.round((ivsc.trefferquote || 0) * 100) + "%" : "—"}</b></div>
    <div class="kv"><span class="k">Offene Vorschläge</span><b>${(iv.vorschlaege || []).length}</b></div>
    <div class="kv"><span class="k">Watchlist</span><b>${(iv.watchlist || []).length}</b></div>
    ${ivtop ? `<h3>Top-Mover</h3>${ivtop}` : `<div class="leer">Noch kein Screen.</div>`}`,
    { right: `<span class="right" data-app="investment">Öffnen ›</span>` });

  // #2: Widget-Register -> nach gespeicherter Reihenfolge, ohne ausgeblendete. Im Edit-Modus mit Tray/Controls.
  const W = { ov, hero, feed, agents, timeline, quick, sysmon, investP, mem, llm };
  const sichtbar = LAYOUT.order.filter(id => !LAYOUT.hidden.includes(id));
  main.innerHTML = sichtbar.map(id => tagWidget(id, W[id])).join("") + (EDIT ? dashTray() : "");
  main.classList.toggle("editing", EDIT);
  setOrb(VOICE.active ? "listening" : "idle");  // Orb-Zustand nach Neurender wiederherstellen
}
function ovItem(icon, titel, sub, status) {
  return `<div class="ov-item"><span class="ovi">${icon}</span>
    <div><div class="ovt">${esc(titel)}</div><div class="ovs">${esc(sub)}</div></div>
    <span class="pill ${status}"><span class="dot"></span>${status === "active" ? "Active" : "—"}</span></div>`;
}

// ---- Daten + Aktionen ------------------------------------------------------
async function refresh() {
  try {
    STATE = await (await fetch("/api/state")).json();
    setLive(true);
    // Dashboard-Daten (parallel, fehlertolerant)
    try { OVERVIEW = await (await fetch("/api/overview")).json(); } catch {}
    try { LAGE = await (await fetch("/api/lagebild")).json(); } catch {}
    try { INVEST = await (await fetch("/api/investment")).json(); } catch {}
    renderOffene(); updateSidebarCounts();
    if (AKTIV_NAV === "home") renderDashboard();
  } catch { setLive(false); }
}
async function batchReformat(btn) {
  if (!confirm("Alle offenen Anträge ins neue Format bringen? Freigegebene werden dabei zurückgesetzt (du musst sie neu freigeben). Das kann je nach Anzahl etwas dauern.")) return;
  const alt = btn.textContent; btn.disabled = true; btn.textContent = "⏳ LUNA formatiert alle...";
  try {
    const r = await fetch("/api/antraege/neu-formatieren", { method: "POST" });
    const d = await r.json();
    if (d.state) { STATE = d.state; renderOffene(); updateSidebarCounts(); if (AKTIV_NAV === "home") renderDashboard(); }
    alert("Fertig: " + ((d.res && d.res.anzahl) || 0) + " Anträge neu formatiert.");
  } catch { btn.disabled = false; btn.textContent = alt; alert("Aktion fehlgeschlagen."); }
}
async function aktion(id, akt, btn) {
  let body = {};
  if (akt === "ablehnen") { const g = prompt("Grund der Ablehnung?", ""); if (g === null) return; body = { grund: g }; }
  if (akt === "revidieren") {
    const fb = prompt("Was soll anders/besser sein? LUNA überarbeitet den Antrag (Status wird zurückgesetzt, du musst neu freigeben).\n\nz. B.: mach es günstiger · geht das kostenlos? · nur die 20-Euro-Stufe · kürzer fassen", "");
    if (fb === null) return; body = { feedback: fb };
  }
  if (akt === "loeschen" && !confirm("Antrag wirklich löschen?")) return;
  // Mehr-Info/Revidieren sind agentisch (CTO/CFO + ggf. Recherche) -> kann einige Sekunden dauern.
  let alt;
  if (btn) { alt = btn.textContent; btn.disabled = true;
    if (akt === "mehr-info") btn.textContent = "⏳ Agenten arbeiten...";
    if (akt === "revidieren") btn.textContent = "⏳ LUNA überarbeitet..."; }
  try {
    const r = await fetch(`/api/antraege/${encodeURIComponent(id)}/${akt}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const d = await r.json();
    if (akt === "mehr-info" && d.bewertung) alert("LUNA-Bewertung:\n\n" + d.bewertung);
    if (d.state) { STATE = d.state; renderOffene(); updateSidebarCounts(); if (AKTIV_NAV === "home") renderDashboard(); }
  } catch { if (btn) { btn.disabled = false; btn.textContent = alt; } alert("Aktion fehlgeschlagen."); }
}

// ---- Antrags-Detailansicht -------------------------------------------------
const EVENT_LABEL = { eingereicht: "📥 eingereicht", freigegeben: "✅ freigegeben", abgelehnt: "⛔ abgelehnt",
  in_umsetzung: "⚙️ in Umsetzung", erledigt: "🏁 erledigt", fehlgeschlagen: "💥 fehlgeschlagen", geloescht: "🗑 geloescht" };
async function openDetail(id) {
  const wid = "detail:" + id;
  if (WINS[wid]) { WINS[wid].focus(); return; }
  const win = new WinBox("📄  Antrag " + id, { ...(istMobil() ? winGeom() : { width: "520px", height: "66%", x: "center", y: "center" }),
    class: ["modern"], onclose: () => { delete WINS[wid]; return false; } });
  WINS[wid] = win;
  win.body.innerHTML = `<div class="app"><div class="leer">Lade Details...</div></div>`;
  try {
    const a = await (await fetch(`/api/antraege/${encodeURIComponent(id)}`)).json();
    const verlauf = (a.verlauf || []).map(s =>
      `<div class="row"><span class="t">${esc(zeit(s.ts))}</span><div><b>${esc(EVENT_LABEL[s.event] || s.event)}</b>${s.akteur ? " · " + esc(s.akteur) : ""}${s.grund ? `<br><span class="grund">${esc(s.grund)}</span>` : ""}</div></div>`).join("");
    win.body.innerHTML = `<div class="app detail">
      <div class="head"><span class="badge ${esc(a.status)}">${esc(a.status)}</span><b>${esc(a.titel)}</b></div>
      <div class="meta">von ${esc(a.von)}${a.kategorie ? " · " + esc(a.kategorie) : ""} · ${esc(a.id)}</div>
      <div class="desc full">${esc(a.beschreibung) || "<i>keine Beschreibung</i>"}</div>
      ${a.betroffen ? `<div class="kv"><span class="k">Betroffen</span><b>${esc(a.betroffen)}</b></div>` : ""}
      <h3>Verlauf</h3>${verlauf || `<div class="leer">noch keine Schritte</div>`}</div>`;
  } catch { win.body.innerHTML = `<div class="app"><div class="leer">Konnte Details nicht laden.</div></div>`; }
}

// ---- Events ----------------------------------------------------------------
document.addEventListener("click", (e) => {
  const orb = e.target.closest("#luna-orb"); if (orb) { toggleVoice(); return; }
  const holo = e.target.closest("#luna-holo"); if (holo) { toggleVoice(); return; }
  const talk = e.target.closest("#talk"); if (talk) { toggleVoice(); return; }
  const tog = e.target.closest("#side-toggle, #nav-open"); if (tog) { document.getElementById("sidebar").classList.toggle("open"); return; }
  const ac = e.target.closest("[data-acsym]");
  if (ac) { investWatchAddDirect(ac.dataset.acsym, ac.dataset.acasset); return; }
  const rm = e.target.closest("[data-invremove]");
  if (rm) { investWatchRemove(rm.dataset.invremove); return; }
  const inv = e.target.closest("[data-invsym]");
  if (inv) { openInvestDetail(inv.dataset.invsym, inv.dataset.invasset); return; }
  const crmt = e.target.closest("[data-crmtodo]");
  if (crmt) { crmTodoErledigt(crmt.dataset.crmtodo); return; }
  const crmf = e.target.closest("[data-crmfirma]");
  if (crmf) { openCrmKonversation(crmf.dataset.crmfirma); return; }
  const trs = e.target.closest("[data-trendid]");
  if (trs) { trendStatus(trs.dataset.trendid, trs.dataset.trendstatus); return; }
  const idc = e.target.closest("[data-ideaid]");
  if (idc) { ideaStatus(idc.dataset.ideaid, idc.dataset.ideastatus); return; }
  const drf = e.target.closest("[data-draftid]");
  if (drf) { draftStatus(drf.dataset.draftid, drf.dataset.draftstatus); return; }
  const src = e.target.closest("[data-srcid]");
  if (src) { sourceAktiv(src.dataset.srcid, src.dataset.srcaktiv); return; }
  const aii = e.target.closest("[data-aiid]");
  if (aii) { aiRec(aii.dataset.aiid, aii.dataset.airec); return; }
  const tsave = e.target.closest("[data-teamsave]");
  if (tsave) { teamAnlegen(); return; }
  const tu = e.target.closest("[data-teamuser]");
  if (tu) { teamAktiv(tu.dataset.teamuser, tu.dataset.teamaktiv); return; }
  const csave = e.target.closest("[data-cuttersave]");
  if (csave) { cutterJob(); return; }
  const th = e.target.closest("[data-theme-set]");
  if (th) { setTheme(th.dataset.themeSet); return; }
  const uim = e.target.closest("[data-ui-mode]");
  if (uim) { setUiMode(uim.dataset.uiMode); return; }
  const av = e.target.closest("[data-avatar-set]");
  if (av) { setAvatarPref(av.dataset.avatarSet); return; }
  const ed = e.target.closest("#edit-dash, [data-editdone]");
  if (ed) { toggleEdit(); return; }
  const wh = e.target.closest("[data-whide]");
  if (wh) { hideWidget(wh.dataset.whide); return; }
  const wa = e.target.closest("[data-wadd]");
  if (wa) { showWidget(wa.dataset.wadd); return; }
  const cmd = e.target.closest("[data-cmd]");
  if (cmd) { cmd.dataset.cmd === "talk" ? toggleVoice() : navTo(cmd.dataset.cmd); return; }
  const navi = e.target.closest("[data-app]");
  if (navi) { navTo(navi.dataset.app); return; }
  const det = e.target.closest("[data-detail]");
  if (det) { openDetail(det.dataset.detail); return; }
  const batch = e.target.closest("[data-batch]");
  if (batch) { batchReformat(batch); return; }
  const btn = e.target.closest("[data-act]");
  if (btn) { aktion(btn.dataset.id, btn.dataset.act, btn); return; }
  const mehr = e.target.closest("[data-mehr]");
  if (mehr) { const d = mehr.previousElementSibling; d.classList.toggle("open");
    mehr.textContent = d.classList.contains("open") ? "weniger anzeigen ▴" : "mehr anzeigen ▾"; }
});
function setLive(on) { const el = document.getElementById("live"); if (el) el.classList.toggle("stale", !on); }
function clock() {
  const now = new Date();
  const cl = document.getElementById("clock"); if (cl) cl.textContent = now.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const dt = document.getElementById("datum"); if (dt) dt.textContent = now.toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });
}

function connectSSE() {
  try {
    const es = new EventSource("/api/events");
    es.addEventListener("update", refresh);
    es.onerror = () => setLive(false);
  } catch { /* Polling-Fallback */ setInterval(refresh, 5000); }
}

// ---- Live-Gespraech mit LUNA (Browser-Ohren + ElevenLabs-Stimme) -----------
// Der Orb ist die SPRECHENDE Live-LUNA: antippen -> freihaendiges Gespraech (du sprichst,
// die echte LUNA mit Tools/Persona antwortet gesprochen). Der Tipp-Chat ist die Rueckfallebene.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const SPEECH = { canListen: !!SR, canSpeak: "speechSynthesis" in window };
const VOICE = { active: false, rec: null, sprechen: false };
const LUNA_HISTORY = [];

// Web-Audio: noetig, weil Safari/iOS (und Chrome) Audio nur nach einer Nutzer-Geste abspielen.
// Wir entsperren den AudioContext beim Orb-/Gespraech-Tap (unlockAudio) -> danach darf LUNA von selbst sprechen.
let AUDIO_CTX = null, CUR_SRC = null, ANALYSER = null;
function ensureAudio() {
  try { if (!AUDIO_CTX) AUDIO_CTX = new (window.AudioContext || window.webkitAudioContext)(); } catch {}
  if (AUDIO_CTX && !ANALYSER) {  // Analyser fuer die audio-reaktive Orb-Visualisierung (Jarvis-Stil)
    try { ANALYSER = AUDIO_CTX.createAnalyser(); ANALYSER.fftSize = 64; ANALYSER.smoothingTimeConstant = 0.7;
      ANALYSER.connect(AUDIO_CTX.destination); } catch {}
  }
  if (AUDIO_CTX && AUDIO_CTX.state === "suspended") { try { AUDIO_CTX.resume(); } catch {} }
  return AUDIO_CTX;
}
// Treibt die Orb-Animation aus Lolas echter Stimme (Amplitude -> CSS-Variable --energy).
function startOrbViz() {
  if (!ANALYSER) return;
  const data = new Uint8Array(ANALYSER.frequencyBinCount);
  const orb = document.getElementById("luna-orb");
  (function tick() {
    if (!VOICE.sprechen) { if (orb) orb.style.setProperty("--energy", "0"); return; }
    try { ANALYSER.getByteFrequencyData(data); } catch {}
    let sum = 0; for (const v of data) sum += v;
    const e = Math.min(1, (sum / data.length) / 105);
    if (orb) orb.style.setProperty("--energy", e.toFixed(2));
    if (AVATAR) AVATAR.setEnergy(e);
    requestAnimationFrame(tick);
  })();
}
function unlockAudio() {  // MUSS im Klick-/Tap-Handler laufen (Nutzer-Geste)
  const ac = ensureAudio(); if (!ac) return;
  try { const b = ac.createBuffer(1, 1, 22050); const s = ac.createBufferSource(); s.buffer = b; s.connect(ac.destination); s.start(0); } catch {}
}

function setOrb(s) {
  const o = document.getElementById("luna-orb"); if (o) o.className = s;
  const on = (s === "listening" || s === "speaking");
  const w = document.getElementById("side-wave"); if (w) w.classList.toggle("on", on);
  const t = document.getElementById("talk"); if (t) t.classList.toggle("on", on);
  if (AVATAR) AVATAR.setState(s);
  const holo = document.getElementById("luna-holo"); if (holo) holo.classList.toggle("big", on);
}
function voiceStatus(t) {
  const el = document.getElementById("voice-status"); if (el) el.textContent = t;  // im Chat-Fenster
  const sv = document.getElementById("side-voice-state"); if (sv) sv.textContent = t;
  const ts = document.getElementById("talk-sub"); if (ts) ts.textContent = t;
}
function voiceToggleUI() { const b = document.getElementById("voice-toggle");
  if (b) { b.classList.toggle("on", VOICE.active); b.textContent = VOICE.active ? "⏹ Gespräch beenden" : "🎙️ Gespräch starten"; } }

function stopAudio() {
  VOICE.sprechen = false;
  // stop() loest onended aus -> die wartende lunaSpeak-Schleife laeuft weiter und nimmt wieder auf (Barge-in).
  try { if (CUR_SRC) CUR_SRC.stop(); } catch {}
  try { window.speechSynthesis && window.speechSynthesis.cancel(); } catch {}
}

// Zerlegt die Antwort in Saetze -> LUNA faengt frueher an zu sprechen (Streaming-Muster, vgl. OpenJARVIS).
function inSaetze(text) {
  const teile = String(text).replace(/\s+/g, " ").match(/[^.!?…]+[.!?…]+|\S[^.!?…]*$/g) || [text];
  const out = []; let buf = "";
  for (const s of teile) { buf += (buf ? " " : "") + s.trim();
    if (buf.length >= 60) { out.push(buf); buf = ""; } }
  if (buf.trim()) out.push(buf.trim());
  return out.filter(Boolean);
}

// LUNA spricht die ganze Antwort (Satz fuer Satz, ElevenLabs -> Fallback Browser-Stimme).
async function lunaSpeak(text) {
  setOrb("speaking"); voiceStatus("LUNA spricht… — Orb antippen zum Unterbrechen"); VOICE.sprechen = true;
  startOrbViz();  // Orb pulsiert mit Lolas Stimme
  const saetze = inSaetze(text);
  let premiumOk = true;
  for (const satz of saetze) {
    if (!VOICE.sprechen) break;                 // abgebrochen (Barge-in/Stop)
    const ok = premiumOk && await spieleTts(satz);
    if (!ok) { premiumOk = false; await browserSpeak(satz); }  // sobald Premium scheitert: Browser-Stimme
  }
  VOICE.sprechen = false;
  if (VOICE.active) startListening(); else setOrb(WINS.luna ? "listening" : "idle");
}

// Holt einen Satz als MP3 von /api/tts und spielt ihn ueber den AudioContext. true = gespielt.
async function spieleTts(text) {
  const ac = ensureAudio(); if (!ac) return false;
  try {
    const r = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }) });
    if (!r.ok || !(r.headers.get("content-type") || "").includes("audio")) return false;
    const data = await r.arrayBuffer();
    const audioBuf = await ac.decodeAudioData(data.slice(0)).catch(() => null);
    if (!audioBuf) return false;
    if (!VOICE.sprechen) return true;
    await new Promise((res) => {
      const s = ac.createBufferSource(); s.buffer = audioBuf;
      s.connect(ANALYSER || ac.destination);  // ueber den Analyser -> audio-reaktiver Orb
      CUR_SRC = s; s.onended = () => { if (CUR_SRC === s) CUR_SRC = null; res(); };
      try { s.start(0); } catch { res(); }
    });
    return true;
  } catch { return false; }
}

// Fallback: Browser-Stimme (kein Premium). Wartet bis der Satz gesprochen ist.
function browserSpeak(text) {
  return new Promise((res) => {
    if (!SPEECH.canSpeak || !VOICE.sprechen) return res();
    try {
      const u = new SpeechSynthesisUtterance(text); u.lang = "de-DE"; u.rate = 1.04;
      const v = window.speechSynthesis.getVoices().find(x => x.lang && x.lang.startsWith("de"));
      if (v) u.voice = v; u.onend = u.onerror = res; window.speechSynthesis.speak(u);
    } catch { res(); }
  });
}

// Eine Hoer-Runde: nimmt einen gesprochenen Satz auf und schickt ihn an LUNA.
function startListening() {
  if (!VOICE.active || !SR) return;
  stopAudio();
  let rec; try { rec = new SR(); } catch { return; }
  rec.lang = "de-DE"; rec.interimResults = true; rec.continuous = false;
  VOICE.rec = rec; setOrb("listening"); voiceStatus("Ich höre…");
  let text = "";
  rec.onresult = (e) => { text = Array.from(e.results).map(r => r[0].transcript).join(""); voiceStatus(text || "Ich höre…"); };
  rec.onerror = () => {};
  rec.onend = () => {
    VOICE.rec = null;
    if (!VOICE.active) return;
    const t = text.trim();
    if (t) sendeAnLuna(t, true);   // -> LUNA antwortet + spricht -> danach wieder zuhoeren
    else startListening();          // Stille: weiter zuhoeren
  };
  try { rec.start(); } catch { /* evtl. schon aktiv */ }
}

function startVoice() {
  if (!SR) { addMsg("luna", "Sprach-Eingabe braucht HTTPS und einen unterstützten Browser (Chrome/Safari)."); return; }
  VOICE.active = true; voiceToggleUI(); startListening();
}
function stopVoice() {
  VOICE.active = false; stopAudio();
  try { VOICE.rec && VOICE.rec.stop(); } catch {}
  VOICE.rec = null; setOrb(WINS.luna ? "listening" : "idle");
  voiceStatus("Gespräch pausiert — Orb antippen zum Weitersprechen."); voiceToggleUI();
}
function toggleVoice() {
  unlockAudio();  // im Tap-Kontext -> erlaubt LUNA, danach von selbst zu sprechen (Safari/iOS!)
  // BARGE-IN: spricht LUNA gerade? -> sofort verstummen; lunaSpeak nimmt danach automatisch wieder auf.
  if (VOICE.sprechen) { stopAudio(); voiceStatus("…ja?"); return; }
  if (!WINS.luna) openLuna(); else WINS.luna.focus();
  if (!SR) {  // z. B. iOS Safari: keine Sprach-Eingabe -> aber LUNA spricht (auf getippte Eingabe)
    voiceStatus("Auf diesem Gerät bitte tippen — LUNA antwortet mit Stimme.");
    return;
  }
  if (VOICE.active) stopVoice(); else startVoice();
}

function openLuna() {
  if (WINS.luna) { WINS.luna.focus(); return; }
  const win = new WinBox("🌙  LUNA", { ...(istMobil() ? winGeom() : { width: "440px", height: "64%", x: "right", y: 60 }),
    class: ["modern"], onclose: () => { delete WINS.luna; stopVoice(); setOrb("idle"); return false; } });
  WINS.luna = win;
  const begruessung = LUNA_HISTORY.length ? "" : `<div class="msg luna">Hallo Nils 🌙 Tippe oben auf „Gespräch starten" und sprich mit mir — oder schreib unten.</div>`;
  const msgs = LUNA_HISTORY.map(m => `<div class="msg ${m.role}">${esc(m.text)}</div>`).join("");
  const voiceBtn = SPEECH.canListen
    ? `<button type="button" id="voice-toggle" class="${VOICE.active ? "on" : ""}">${VOICE.active ? "⏹ Gespräch beenden" : "🎙️ Gespräch starten"}</button>`
    : `<button type="button" id="voice-toggle" onclick="unlockAudio()">🔊 Stimme aktivieren</button>`;
  win.body.innerHTML = `<div class="chat">
    <div class="voice-bar">${voiceBtn}<span id="voice-status" class="voice-status">${VOICE.active ? "Ich höre…" : "Sprich mit LUNA oder tippe."}</span></div>
    <div class="chat-msgs" id="chat-msgs">${begruessung}${msgs}</div>
    <form class="chat-form" id="chat-form"><input id="chat-in" placeholder="Schreib LUNA..." autocomplete="off"><button type="submit">➤</button></form></div>`;
  const form = win.body.querySelector("#chat-form"), inp = win.body.querySelector("#chat-in");
  const vt = win.body.querySelector("#voice-toggle"); if (vt) vt.onclick = toggleVoice;
  form.onsubmit = (e) => {
    e.preventDefault();
    unlockAudio();  // Tippen+Senden ist eine Geste -> erlaubt LUNA, die Antwort vorzulesen (auch iOS)
    const t = inp.value.trim(); if (!t) return;
    inp.value = "";
    sendeAnLuna(t, true);  // der Orb ist die sprechende LUNA -> Antwort wird vorgelesen
    inp.focus();
  };
  if (!VOICE.active) setOrb("idle");
  setTimeout(() => inp.focus(), 50);
}

// Schickt eine Nutzer-Aeusserung an LUNA. sprich=true -> Antwort wird gesprochen (+ Gespraech laeuft weiter).
async function sendeAnLuna(text, sprich) {
  addMsg("user", text);
  // Reiner Anzeige-Befehl ("zeig mir die Aufträge") -> App einblenden, kurz bestaetigen, fertig.
  const app = versucheKontextBefehl(text);
  if (app) { const s = `Zeige dir „${app}".`; typeLunaText(s); if (sprich) lunaSpeak(s); else setOrb(WINS.luna ? "listening" : "idle"); return; }
  // Frage betrifft eine Ansicht (Anträge/Tickets/Finanzen…)? -> passendes Panel sofort zeigen, LUNA erklaert dazu.
  const ziel = panelFuerFrage(text);
  if (ziel) openApp(ziel);
  setOrb("speaking"); voiceStatus("LUNA denkt…");
  let reply = "(keine Antwort)";
  try {
    const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: LUNA_HISTORY }) });
    reply = (await r.json()).reply || reply;
  } catch { reply = "(Verbindungsfehler)"; }
  typeLunaText(reply);
  if (sprich) lunaSpeak(reply); else setOrb(WINS.luna ? "listening" : "idle");
}

function addMsg(role, text) {
  LUNA_HISTORY.push({ role, text });
  const box = document.getElementById("chat-msgs"); if (!box) return;
  const d = document.createElement("div"); d.className = "msg " + role; d.textContent = text;
  box.appendChild(d); box.scrollTop = box.scrollHeight;
}
// Rendert LUNAs Antwort im Chat (Schreibmaschinen-Effekt). Das SPRECHEN macht lunaSpeak separat.
function typeLunaText(text) {
  LUNA_HISTORY.push({ role: "luna", text });
  const box = document.getElementById("chat-msgs");
  const d = document.createElement("div"); d.className = "msg luna"; if (box) box.appendChild(d);
  let i = 0;
  (function step() {
    if (d) d.textContent = text.slice(0, i);
    if (box) box.scrollTop = box.scrollHeight;
    if (i++ < text.length) setTimeout(step, 14);
  })();
}

// ---- Start -----------------------------------------------------------------
clock(); setInterval(clock, 1000);
// Topbar-Suche: Enter -> an LUNA (oeffnet Chat); Kontext-Befehle blenden direkt das Panel ein.
const _ts = document.getElementById("topsearch");
if (_ts) _ts.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && _ts.value.trim()) { const t = _ts.value.trim(); _ts.value = "";
    openLuna(); sendeAnLuna(t, false); }
});
// K4: erst Rolle/erlaubte Apps laden (blendet nicht-erlaubte Apps aus), dann Sidebar + Daten.
(async function boot() {
  applyTheme();       // Theme-Klasse ist schon (flash-frei) vom Head-Script gesetzt -> hier nur Button-Status
  await ladeMe();
  await ladePrefs();  // #2: Dashboard-Layout pro User (Reihenfolge + ausgeblendete)
  if (!PREFS.avatar) { try { const a = localStorage.getItem("luna-avatar-mode"); if (a) PREFS.avatar = a; } catch { } }
  buildSidebar();
  applyAvatar();      // Orb oder 3D-Hologramm gemaess Pref
  refresh();          // laedt Daten + rendert das Command-Center-Dashboard (Home)
})();
connectSSE();
// Orb-/Talk-Klicks laufen ueber die zentrale Event-Delegation (siehe oben).
