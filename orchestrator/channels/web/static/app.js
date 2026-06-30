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
  auftraege: { icon: "📋", titel: "Aufträge", badge: () => STATE.antraege.length, render: renderAuftraege },
  meldungen: { icon: "🔔", titel: "Meldungen", badge: () => STATE.meldungen.length, render: renderListe("meldungen", m => [m.abteilung, m.text, m.ts]) },
  aktivitaet: { icon: "📊", titel: "Aktivität", badge: () => 0, render: renderListe("aktivitaet", a => [a.akteur, a.aktion, a.ts]) },
  research: { icon: "🔍", titel: "Research", badge: () => STATE.research.length, render: renderListe("research", r => [r.abteilung || r.status, r.frage, ""]) },
  lagebild: { icon: "📡", titel: "Lagebild", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Lagebild…</div></div>`, load: ladeLagebild },
  wissen: { icon: "🧠", titel: "Wissen", badge: () => 0, render: renderWissen, load: ladeWissen },
  investment: { icon: "📈", titel: "Investment", badge: () => 0, render: () => `<div class="app"><div class="leer">Lade Investment…</div></div>`, load: ladeInvestment },
  finance: { icon: "💶", titel: "Finanzen", badge: () => 0, render: renderFinance },
};

// ---- Investment (CIO, advisory) --------------------------------------------
let INVEST = null;
async function ladeInvestment() {
  try { INVEST = await (await fetch("/api/investment")).json(); } catch { INVEST = null; }
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
  const sc = i.scorecard || {};
  const scText = sc.ausgewertet ? `${Math.round((sc.trefferquote || 0) * 100)}% Trefferquote (${sc.treffer}/${sc.ausgewertet})` : "noch keine Auswertung";
  const h = i.historie || {}; const jt = h.je_tabelle || {};
  const histText = h.eintraege_gesamt ? `${h.eintraege_gesamt} Einträge (all-time) · ${jt.forecasts || 0} Prognosen · ${jt.actuals || 0} ausgewertet · ${jt.screening || 0} Screens` : "noch leer";
  win.body.innerHTML = `<div class="app">
    <div class="kv"><span class="k">Modus</span><b>${esc(i.modus)}</b></div>
    <div class="kv"><span class="k">Track-Record</span><b>${esc(scText)}</b></div>
    <div class="kv"><span class="k">Historie (append-only)</span><b>${esc(histText)}</b></div>
    <div style="margin:10px 0; display:flex; gap:6px; flex-wrap:wrap">${prov}</div>
    <div class="brain-bar">
      <div class="inv-ac"><input id="inv-sym" placeholder="Aktie/Krypto suchen & hinzufügen…" autocomplete="off" oninput="investSuche(this.value)">
        <div id="inv-suggest" class="inv-suggest"></div></div>
      <button class="btn info" onclick="investScreen(this)">📡 Screen jetzt</button></div>
    <h3>Watchlist</h3><div>${wl}</div>
    <h3>Shortlist (letzter Screen)</h3>${sl}
    <h3>Vorschläge (vom Risk-Agent geprüft)</h3>${sug}</div>`;
}
async function investScreen(btn) {
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Screent…"; }
  try { await fetch("/api/investment/screen", { method: "POST" }); } catch {}
  ladeInvestment();
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
function invDetailAktie(d) {
  const p = d.profil, q = d.quote, r = d.rsi;
  const news = (d.news || []).map(n => `<div class="row"><div><b>${esc(n.titel)}</b><br><span class="meta">${esc(n.quelle || "")}</span></div></div>`).join("");
  const links = (d.links || []).map(linkRow).join("");
  const hinweis = (d.hinweise || []).length ? `<div class="leer">${esc(d.hinweise[0])}</div>` : "";
  return `<div class="head"><b>${esc((p && p.name) || d.symbol)}</b></div>
    ${p ? `<div class="meta">${esc(p.branche || "")}${p.boerse ? " · " + esc(p.boerse) : ""}${p.land ? " · " + esc(p.land) : ""}</div>` : ""}
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
  { id: "research", icon: "🔍", label: "Research", count: () => STATE.research.length },
  { id: "meldungen", icon: "🔔", label: "Meldungen", count: () => STATE.meldungen.length },
  { id: "aktivitaet", icon: "📊", label: "Aktivität" },
  { id: "finance", icon: "💶", label: "Finanzen" },
  { id: "luna", icon: "💬", label: "LUNA-Chat" },
];
let AKTIV_NAV = "home";
function buildSidebar() {
  const nav = document.getElementById("nav");
  nav.innerHTML = NAV.map(n => `<div class="nav-item${n.id === AKTIV_NAV ? " active" : ""}" data-app="${n.id}">
    <span class="nico">${n.icon}</span><span>${esc(n.label)}</span><span class="ncount" data-ncount="${n.id}" hidden></span></div>`).join("");
  updateSidebarCounts();
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
    { cls: "col-2", right: `<span class="right" data-app="auftraege">Alle ›</span>` });

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

  main.innerHTML = ov + hero + feed + agents + timeline + quick + sysmon + investP + mem + llm;
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
  const talk = e.target.closest("#talk"); if (talk) { toggleVoice(); return; }
  const tog = e.target.closest("#side-toggle, #nav-open"); if (tog) { document.getElementById("sidebar").classList.toggle("open"); return; }
  const ac = e.target.closest("[data-acsym]");
  if (ac) { investWatchAddDirect(ac.dataset.acsym, ac.dataset.acasset); return; }
  const rm = e.target.closest("[data-invremove]");
  if (rm) { investWatchRemove(rm.dataset.invremove); return; }
  const inv = e.target.closest("[data-invsym]");
  if (inv) { openInvestDetail(inv.dataset.invsym, inv.dataset.invasset); return; }
  const cmd = e.target.closest("[data-cmd]");
  if (cmd) { cmd.dataset.cmd === "talk" ? toggleVoice() : navTo(cmd.dataset.cmd); return; }
  const navi = e.target.closest("[data-app]");
  if (navi) { navTo(navi.dataset.app); return; }
  const det = e.target.closest("[data-detail]");
  if (det) { openDetail(det.dataset.detail); return; }
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
buildSidebar(); clock(); setInterval(clock, 1000);
// Topbar-Suche: Enter -> an LUNA (oeffnet Chat); Kontext-Befehle blenden direkt das Panel ein.
const _ts = document.getElementById("topsearch");
if (_ts) _ts.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && _ts.value.trim()) { const t = _ts.value.trim(); _ts.value = "";
    openLuna(); sendeAnLuna(t, false); }
});
refresh();          // laedt Daten + rendert das Command-Center-Dashboard (Home)
connectSSE();
// Orb-/Talk-Klicks laufen ueber die zentrale Event-Delegation (siehe oben).
