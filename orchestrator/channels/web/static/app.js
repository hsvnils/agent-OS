// LUNA-OS -- Desktop-aehnliche Arbeitsoberflaeche (Phase 16).
// Holt den Zustand aus der API, zeigt Apps in WinBox-Fenstern, Aktionen per Button (live).
"use strict";

let STATE = { antraege: [], meldungen: [], aktivitaet: [], research: [], finance: {} };
const WINS = {};  // app-id -> WinBox

const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const zeit = (ts) => { try { return new Date(ts).toLocaleString("de-DE", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }); } catch { return ""; } };

// ---- Apps -----------------------------------------------------------------
const APPS = {
  auftraege: { icon: "📋", titel: "Auftraege", badge: () => STATE.antraege.length, render: renderAuftraege },
  meldungen: { icon: "🔔", titel: "Meldungen", badge: () => STATE.meldungen.length, render: renderListe("meldungen", m => [m.abteilung, m.text, m.ts]) },
  aktivitaet: { icon: "📊", titel: "Aktivitaet", badge: () => 0, render: renderListe("aktivitaet", a => [a.akteur, a.aktion, a.ts]) },
  research: { icon: "🔍", titel: "Research", badge: () => STATE.research.length, render: renderListe("research", r => [r.abteilung || r.status, r.frage, ""]) },
  finance: { icon: "💶", titel: "Finanzen", badge: () => 0, render: renderFinance },
};

function renderAuftraege() {
  if (!STATE.antraege.length) return `<div class="app"><div class="leer">Keine offenen Auftraege. 🎉<br>LUNA meldet sich, wenn etwas ansteht.</div></div>`;
  const cards = STATE.antraege.map(a => {
    const lang = a.beschreibung.length > 240;
    const freigeben = a.status === "eingereicht"
      ? `<button class="btn ok" data-act="freigeben" data-id="${esc(a.id)}">✓ Freigeben</button>` : "";
    const ablehnen = (a.status === "eingereicht" || a.status === "freigegeben")
      ? `<button class="btn warn" data-act="ablehnen" data-id="${esc(a.id)}">✕ Ablehnen</button>` : "";
    return `<div class="card">
      <div class="head"><span class="badge ${esc(a.status)}">${esc(a.status)}</span><b>${esc(a.titel)}</b></div>
      <div class="meta">von ${esc(a.von)}${a.kategorie ? " · " + esc(a.kategorie) : ""} · ${esc(a.id)}</div>
      <div class="desc">${esc(a.beschreibung) || "<i>keine Beschreibung</i>"}</div>
      ${lang ? `<div class="mehr" data-mehr>mehr anzeigen ▾</div>` : ""}
      <div class="actions">
        ${freigeben}${ablehnen}
        <button class="btn info" data-act="mehr-info" data-id="${esc(a.id)}">🔍 Mehr Info holen</button>
        <button class="btn danger" data-act="loeschen" data-id="${esc(a.id)}">🗑 Loeschen</button>
      </div></div>`;
  }).join("");
  return `<div class="app">${cards}</div>`;
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
    <div class="kv"><span class="k">Offene Auftraege</span><b>${STATE.antraege.length}</b></div>
    <div class="kv"><span class="k">Offene Research-Tickets</span><b>${STATE.research.length}</b></div></div>`;
}

// ---- Fenster ---------------------------------------------------------------
let zaehler = 0;
function openApp(id) {
  const app = APPS[id];
  if (!app) return;
  if (WINS[id]) { WINS[id].focus(); return; }
  const off = (zaehler++ % 5) * 34;
  const win = new WinBox(`${app.icon}  ${app.titel}`, {
    width: "560px", height: "72%", x: 90 + off, y: 60 + off, class: ["modern"],
    onclose: () => { delete WINS[id]; return false; },
  });
  WINS[id] = win;
  renderApp(id);
}
function renderApp(id) {
  if (WINS[id]) WINS[id].body.innerHTML = APPS[id].render();
}
function renderOffene() { Object.keys(WINS).forEach(renderApp); }

// ---- Dock ------------------------------------------------------------------
function buildDock() {
  const dock = document.getElementById("dock");
  dock.innerHTML = Object.entries(APPS).map(([id, a]) =>
    `<div class="dock-app" data-app="${id}"><div class="ico">${a.icon}</div><div class="lbl">${esc(a.titel)}</div><span class="badge-n" data-badge="${id}" hidden></span></div>`).join("");
  dock.querySelectorAll(".dock-app").forEach(el => el.onclick = () => openApp(el.dataset.app));
}
function updateBadges() {
  Object.entries(APPS).forEach(([id, a]) => {
    const el = document.querySelector(`[data-badge="${id}"]`);
    if (!el) return;
    const n = a.badge();
    el.hidden = !n; el.textContent = n;
  });
  document.getElementById("welcome").style.display = STATE.antraege.length ? "none" : "";
}

// ---- Daten + Aktionen ------------------------------------------------------
async function refresh() {
  try {
    STATE = await (await fetch("/api/state")).json();
    renderOffene(); updateBadges(); setLive(true);
  } catch { setLive(false); }
}
async function aktion(id, akt) {
  let body = {};
  if (akt === "ablehnen") { const g = prompt("Grund der Ablehnung?", ""); if (g === null) return; body = { grund: g }; }
  if (akt === "loeschen" && !confirm("Antrag wirklich loeschen?")) return;
  try {
    const r = await fetch(`/api/antraege/${encodeURIComponent(id)}/${akt}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const d = await r.json();
    if (d.state) { STATE = d.state; renderOffene(); updateBadges(); }
  } catch { alert("Aktion fehlgeschlagen."); }
}

// ---- Events ----------------------------------------------------------------
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-act]");
  if (btn) { aktion(btn.dataset.id, btn.dataset.act); return; }
  const mehr = e.target.closest("[data-mehr]");
  if (mehr) { const d = mehr.previousElementSibling; d.classList.toggle("open");
    mehr.textContent = d.classList.contains("open") ? "weniger anzeigen ▴" : "mehr anzeigen ▾"; }
});
function setLive(on) { const el = document.getElementById("live"); el.classList.toggle("stale", !on);
  el.textContent = on ? "● live" : "○ offline"; }
function clock() { document.getElementById("clock").textContent =
  new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }); }

function connectSSE() {
  try {
    const es = new EventSource("/api/events");
    es.addEventListener("update", refresh);
    es.onerror = () => setLive(false);
  } catch { /* Polling-Fallback */ setInterval(refresh, 5000); }
}

// ---- Start -----------------------------------------------------------------
buildDock(); clock(); setInterval(clock, 1000);
refresh().then(() => { openApp("auftraege"); });
connectSSE();
