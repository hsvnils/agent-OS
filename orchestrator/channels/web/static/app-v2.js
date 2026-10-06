// LUNA-OS UI-V2 -- helles, dashboard-/sektionsbasiertes UI (opt-in, siehe UI.md Abschnitt 11).
// Einziges Design von LUNA-OS (V1 am 2026-09-29 entfernt, CEO). Deutsch mit echten Umlauten.
"use strict";

/* =========================== Helfer =========================== */
// Abgelaufene/fehlende Anmeldung (401) -> zur Login-Seite, danach zurueck hierher (LUNA_OS_UI_ROADMAP Etappe 2)
let LOGIN_UMLEITUNG = false;
{ const _fetch = window.fetch.bind(window);
  window.fetch = async (...a) => { const r = await _fetch(...a);
    if (r && r.status === 401 && !LOGIN_UMLEITUNG) { LOGIN_UMLEITUNG = true; location.href = "/login?weiter=" + encodeURIComponent(location.pathname || "/"); }
    return r; }; }
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const jget = async (u) => { try { const r = await fetch(u); return r.ok ? await r.json() : null; } catch { return null; } };
// Sofort sichtbar (CEO 2026-10-06): jede erfolgreiche Aenderung an /api laedt Glocke und aktuelle Seite neu --
// sofort, wenn kein Fenster offen ist, sonst beim Schliessen. Reine Lese-/Vorschau-Aufrufe zaehlen nicht.
const NUR_LESEN = /\/api\/(nutzung|prefs|chat|tts|sehen|login|logout|passkey)|\/(vorschlag|versandvorschau|vorschau)(\?|$)|konzept-videograf|mailentwurf|impressum-suche|\/pruefen$|\/eml$/;
let AENDERUNG_NR = 0, SEITE_NR = 0, AENDERUNG_TIMER = null;   // Zaehler statt Zeit: gleiche Millisekunde waere mehrdeutig
const _fetchOriginal = window.fetch.bind(window);
window.fetch = async (u, opt) => {
  const r = await _fetchOriginal(u, opt);
  try {
    const pfad = typeof u === "string" ? u : (u && u.url) || "", meth = ((opt && opt.method) || "GET").toUpperCase();
    if (meth !== "GET" && pfad.includes("/api/") && !NUR_LESEN.test(pfad) && r.ok) aenderungGemerkt();
  } catch { }
  return r;
};
function aenderungGemerkt() {
  AENDERUNG_NR++;
  clearTimeout(AENDERUNG_TIMER);
  AENDERUNG_TIMER = setTimeout(() => {
    if (typeof glockeAktualisieren === "function") glockeAktualisieren();
    const m = document.getElementById("v2-modal");
    if (!m || m.hidden) seiteAktualisieren();
  }, 450);
}
(function () {                                                    // wann wurde die Seite zuletzt neu gezeichnet?
  const a = document.getElementById("v2-app");
  if (a) new MutationObserver(() => { SEITE_NR = AENDERUNG_NR; }).observe(a, { childList: true });
})();
async function seiteAktualisieren() {
  if (SEITE_NR >= AENDERUNG_NR || !RENDER[AKTIV]) return;        // Seite wurde seit der letzten Aenderung schon neu gezeichnet
  const y = window.scrollY;
  await RENDER[AKTIV]();
  window.scrollTo(0, y);
}
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
const DASH2_TITEL = { todos: "⚡ Handlungsbedarf", budget: "Monatsbudget", trefferquote: "Prognose-Trefferquote", freigaben: "Offene Freigaben", provider: "Provider verbunden", loop: "Investment · Lern-Loop", compliance: "Compliance-Puls", live: "Live-Aktivität", schritte: "Erste Schritte", meldungen: "Meldungen", research: "Research-Tickets" };
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
  { id: "auftraege", icon: "📋", label: "Aufträge", app: "angebote" },
  { id: "finanzen", icon: "💶", label: "Finanzen", app: "finanzen" },
  { id: "rechnungen", icon: "🧾", label: "Rechnungen", app: "rechnungen" },
  { id: "belege", icon: "📥", label: "Belege", app: "belege" },
  { id: "vertraege", icon: "📜", label: "Vertragswerk", app: "angebote" },
  { id: "radar", icon: "🎯", label: "Radar", app: "crm" },
  { id: "content", icon: "✎", label: "Content", app: "trends" },
  { id: "contentplan", icon: "🗓", label: "Content-Plan", app: "trends" },
  { id: "cutter", icon: "🎬", label: "Cutter", app: "cutter" },
  { id: "reel", icon: "📤", label: "Reels", app: "cutter" },
  { id: "wissen", icon: "🧠", label: "Wissen", app: "wissen" },
  { id: "agenten", icon: "🛰", label: "Agenten", app: "home" },
  { id: "system", icon: "📡", label: "System", app: null },
  { id: "team", icon: "👥", label: "Team", app: "team" },
  { id: "einstellungen", icon: "⚙", label: "Einstellungen", app: null },
];
const darf = (app) => app == null || app === "home" || !ME.apps || ME.apps.includes(app);
// LUNA_OS_UI_ROADMAP Etappe 1: 4 Bereiche statt 19 Symbolen (CEO 2026-09-30, Skizze abgenommen). Reihenfolge nach Nutzung.
const BEREICHE = [
  { id: "geschaeft", icon: "💼", label: "Geschäft", teile: ["kunden", "angebote", "auftraege", "rechnungen", "belege", "finanzen", "vertraege"] },
  { id: "content", icon: "🎬", label: "Content & Collabs", teile: ["contentplan", "crm", "radar", "content", "cutter", "reel"] },
  { id: "investment", icon: "📈", label: "Investment", teile: ["investment"] },
  { id: "luna", icon: "🌙", label: "LUNA & System", teile: ["freigaben", "agenten", "wissen", "devroadmap", "system", "team", "einstellungen"] },
];
const TEIL_INFO = {
  kunden: "Firmen, Ansprechpartner, Akte", vertraege: "AGB und Vertragsvorlagen", angebote: "Angebote, Katalog, Preisliste", auftraege: "Laufende und gelieferte Aufträge", rechnungen: "Rechnungen, Zahlungen, Mahnungen",
  belege: "Eingangsbelege prüfen und buchen", finanzen: "Übersicht, Journal, EÜR, Abschluss", crm: "Collab-Anfragen und Verlauf",
  radar: "Neue Collab-Chancen", contentplan: "Kalender: eigene Posts, Kunden, Drehs", content: "Trends, Ideen, Entwürfe", cutter: "Schnitt-Aufträge", reel: "Reels freigeben",
  investment: "Depot, Paper-Handel, Prognosen", freigaben: "Anträge von LUNA", agenten: "Agenten und ihr Status",
  wissen: "LUNAs Gedächtnis", devroadmap: "Geplante Entwicklung", system: "Betrieb und Sicherheit", team: "Team-Zugänge",
  einstellungen: "Depot, Briefings, Anmeldung",
};
const teilErlaubt = (b) => b.teile.filter(t => { const x = SECTIONS.find(s => s.id === t); return x && darf(x.app); });
const bereichVon = (id) => BEREICHE.find(b => "b-" + b.id === id || b.teile.includes(id));
const bereichZiel = (b) => teilErlaubt(b).length > 1 ? "b-" + b.id : teilErlaubt(b)[0];
const seitenName = (id) => id === "dash" ? "Start" : id === "handlung" ? "Handlungsbedarf" : id.startsWith("b-") ? (bereichVon(id) || {}).label || "" : (SECTIONS.find(s => s.id === id) || {}).label || "";

/* =========================== Theme / Shell =========================== */
function applyTheme() {
  const m = localStorage.getItem("luna-v2-theme") || "light";
  const dark = m === "dark" || (m === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("v2-dark", dark);
  document.documentElement.classList.toggle("v2-light", !dark);
}
function toggleTheme() { const m = localStorage.getItem("luna-v2-theme") || "light"; localStorage.setItem("luna-v2-theme", m === "dark" ? "light" : "dark"); applyTheme(); }
function buildShell() {
  $("#v2-nav").innerHTML = BEREICHE.filter(b => teilErlaubt(b).length).map(b =>
    `<button data-go="${bereichZiel(b)}" data-bereich="${b.id}" title="${esc(b.label)}"><span class="i">${b.icon}</span><span class="t">${esc(b.label)}</span></button>`).join("");
  $("#v2-pills").innerHTML = `<button class="v2-pill" data-toggle-chat>💬 LUNA fragen</button>`;
  const nm = (ME.display_name || ME.username || "L").trim();
  $("#v2-avatar").textContent = nm.slice(0, 1).toUpperCase(); $("#v2-avatar").title = nm + (ME.role === "owner" ? " · Voll-Zugriff" : " · " + (ME.role || ""));
}

/* =========================== Router =========================== */
const RENDER = {};
function go(id, sub) {
  if (!SECTIONS.find(s => s.id === id) && !(id.startsWith("b-") && bereichVon(id)) && id !== "handlung") id = "dash";
  if (id === "angebote" && sub === "auftraege") id = "auftraege";        // Reiter „Aufträge“ = eigener Punkt in Geschäft
  if (id === "angebote" && !sub && SUBTAB.angebote === "auftraege") SUBTAB.angebote = "offen";
  AKTIV = id; if (sub) SUBTAB[id] = sub;
  navAktualisieren(); ladeZu();
  $("#v2-app").innerHTML = `<div class="v2-empty">Lade …</div>`;
  jpost("/api/nutzung", { app: id });   // Feature-Friedhof: App-Oeffnung zaehlen (fire-and-forget)
  (RENDER[id] || renderDash)();
}

// Kopfzeile, Unterreihe und Seitenmenue passend zur aktuellen Seite
function navAktualisieren() {
  const b = AKTIV === "dash" || AKTIV === "handlung" ? null : bereichVon(AKTIV);
  document.querySelectorAll("#v2-nav button").forEach(x => { const an = !!b && x.dataset.bereich === b.id; x.classList.toggle("active", an); x.setAttribute("aria-current", an ? "page" : "false"); });
  const u = $("#v2-unter"), teile = b ? teilErlaubt(b) : [];
  if (b && teile.length > 1) {
    u.innerHTML = `<span class="v2-unter-b">${b.icon} ${esc(b.label)}</span>`
      + [["b-" + b.id, "Übersicht"], ...teile.map(t => [t, seitenName(t)])].map(([id, n]) => `<button data-go="${id}" class="${id === AKTIV ? "active" : ""}" ${id === AKTIV ? 'aria-current="page"' : ""}>${esc(n)}</button>`).join("");
    u.hidden = false;
  } else { u.hidden = true; u.innerHTML = ""; }
  $("#v2-titel-mobil").textContent = seitenName(AKTIV);
  document.title = "LUNA · " + seitenName(AKTIV);
}
function ladeAuf() {
  const zeile = (id, n, extra = "") => `<button class="v2-lade-e ${id === AKTIV ? "active" : ""}" data-go="${id}">${n}${extra}</button>`;
  const n = GLOCKE_N ? ` <span class="v2-zaehler an">${GLOCKE_N}</span>` : "";
  $("#v2-lade").innerHTML = `<div class="v2-lade-kopf"><button class="v2-brand" data-go="dash"><span class="v2-logo"><span></span></span><b>LUNA</b></button><button class="v2-icon" id="v2-lade-zu" aria-label="Menü schließen">✕</button></div>`
    + zeile("dash", "🏠 Start") + zeile("handlung", "⚡ Handlungsbedarf", n)
    + (darf("finanzen") ? `<button class="v2-lade-e" data-act="zt-fenster">⏱ Zeit${ZEIT.laufend ? ` <span class="v2-zeit-mini" data-zeit-uhr>${zeitDauer(ZEIT.laufend)}</span>` : ""}</button>` : "")
    + BEREICHE.filter(b => teilErlaubt(b).length).map(b => `<div class="v2-lade-g">${esc(b.label)}</div>`
      + (teilErlaubt(b).length > 1 ? zeile("b-" + b.id, b.icon + " Übersicht") : "")
      + teilErlaubt(b).map(t => zeile(t, esc(seitenName(t)))).join("")).join("")
    + `<button class="v2-lade-luna" data-toggle-chat>💬 LUNA fragen</button>`;
  $("#v2-lade").hidden = false; $("#v2-schleier").hidden = false; document.body.classList.add("v2-lade-offen");
}
function ladeZu() { const l = $("#v2-lade"); if (!l || l.hidden) return; l.hidden = true; $("#v2-schleier").hidden = true; document.body.classList.remove("v2-lade-offen"); }
// Glocke: Anzahl dringender Punkte aus dem Handlungsbedarf (Etappe 3)
let GLOCKE_N = 0, GLOCKE_T = null;
async function glockeAktualisieren() {
  const d = await jget("/api/handlungsbedarf");
  if (!d || !d.zaehler) return;
  GLOCKE_N = d.zaehler.dringend || 0; glockeZeigen();
}
function glockeZeigen() {
  const el = $("#v2-glocke-n"); if (!el) return;
  el.textContent = GLOCKE_N > 99 ? "99+" : String(GLOCKE_N); el.hidden = !GLOCKE_N;
  $("#v2-glocke").setAttribute("aria-label", GLOCKE_N ? `${GLOCKE_N} dringende Punkte` : "Handlungsbedarf");
}
// KUNDEN_FINANZEN Etappe 29: Zeit-Tracker -- Kachel auf der Startseite, Fenster, Timer in der Kopfzeile
let ZEIT = { laufend: null, auftraege: [], alle: [], ergebnis: null };
const zeitStartMs = (l) => l.start_ms || new Date(l.start).getTime();          // start_ms: eindeutig, jede Zeitzone
const zeitDauer = (l) => { const s = Math.max(0, Math.floor((Date.now() - zeitStartMs(l)) / 1000));
  return `${Math.floor(s / 3600)}:${String(Math.floor(s % 3600 / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };
async function zeitLaden() {
  if (!darf("finanzen")) return;
  const d = await jget("/api/finanzen/zeit"); if (d) ZEIT.laufend = d.laufend || null;
  zeitZeigen();
}
function zeitZeigen() {
  const chip = $("#v2-zeit-chip"); if (chip) chip.hidden = !ZEIT.laufend;
  document.querySelectorAll("[data-zeit-uhr]").forEach(e => { e.textContent = ZEIT.laufend ? zeitDauer(ZEIT.laufend) : "0:00:00"; });
  const k = $("#v2-zeit-kachel"); if (k) k.innerHTML = zeitKachelInhalt();
}
setInterval(() => { if (ZEIT.laufend) document.querySelectorAll("[data-zeit-uhr]").forEach(e => { e.textContent = zeitDauer(ZEIT.laufend); }); }, 1000);
const zeitAuftragName = (nr) => { const a = ZEIT.alle.find(x => x.nummer === nr); return a ? `${a.nummer} · ${a.firma_name || a.firma}${a.titel ? " · " + a.titel : ""}` : (nr || "ohne Auftrag"); };
function zeitKachelInhalt() {
  if (ZEIT.laufend) return `<div class="v2-zeit-gross" data-zeit-uhr>${zeitDauer(ZEIT.laufend)}</div><div class="v2-sub">läuft · ${esc(zeitAuftragName(ZEIT.laufend.auftrag))}</div>
    <button class="v2-btn danger v2-zeit-knopf" data-act="zt-stopp">■ Zeit stoppen</button>`;
  return `<div class="v2-sub">Keine Zeit läuft.</div><button class="v2-btn pri v2-zeit-knopf" data-act="zt-fenster">▶ Zeit starten …</button>`;
}
function zeitInhalt(meldung, fehler) {
  const msg = meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="margin-bottom:10px">${esc(meldung)}</div>` : "";
  if (ZEIT.laufend) return msg + `<div class="v2-zeit-fenster"><div class="v2-zeit-gross" data-zeit-uhr>${zeitDauer(ZEIT.laufend)}</div>
    <div class="v2-sub">läuft seit ${esc(String(ZEIT.laufend.start).slice(11, 16))} Uhr · ${esc(zeitAuftragName(ZEIT.laufend.auftrag))}</div>
    <button class="v2-btn danger v2-zeit-knopf" data-act="zt-stopp">■ Zeit stoppen</button></div>`;
  if (ZEIT.ergebnis) { const e = ZEIT.ergebnis;
    return msg + `<div class="v2-zeit-fenster"><b>${esc(dauerTxt(e.minuten || 0))} erfasst</b><div class="v2-sub">${esc(zeitAuftragName(e.auftrag))} · intern ${esc(cent2eur(e.kosten_cent || 0))}</div>
      <label class="v2-feld"><small>Was hast du gemacht?</small><input id="zt-e-taet" class="v2-inp" list="zt-taet-liste" placeholder="z. B. Dreh, Schnitt, Abstimmung"></label>
      ${(ZEIT.taetigkeiten || []).length ? `<div class="v2-zt-chips">${ZEIT.taetigkeiten.map(t => `<button class="v2-btn sm" data-act="zt-taet-chip" data-val="${esc(t)}">${esc(t)}</button>`).join("")}</div>` : ""}
      <datalist id="zt-taet-liste">${(ZEIT.taetigkeiten || []).map(t => `<option value="${esc(t)}">`).join("")}</datalist>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Pause (Min.)</small><input id="zt-e-pause" class="v2-inp" inputmode="numeric"></label><label class="v2-feld"><small>km Hin + Rück</small><input id="zt-km" class="v2-inp" inputmode="numeric" placeholder="z. B. 42"></label></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="v2-btn pri" data-act="zt-km" data-id="${esc(e.id)}">Speichern</button><button class="v2-btn" data-act="zt-neu">Fertig</button></div></div>`; }
  let letzter = ""; try { letzter = localStorage.getItem("luna-zeit-auftrag") || ""; } catch { }
  if (!ZEIT.auftraege.length) return msg + emptyRow("Kein laufender Auftrag (Status „beauftragt“) – Zeit gibt es nur für laufende Aufträge.");
  return msg + `<div class="v2-zeit-fenster"><label class="v2-feld"><small>Laufender Auftrag</small><select id="zt-auftrag" class="v2-inp">${ZEIT.auftraege.map(a =>
      `<option value="${esc(a.nummer)}" ${a.nummer === letzter ? "selected" : ""}>${esc(a.nummer)} · ${esc(a.firma_name || a.firma)}${a.titel ? " · " + esc(a.titel) : ""}</option>`).join("")}</select></label>
    <button class="v2-btn pri v2-zeit-knopf" data-act="zt-start">▶ Zeit starten</button>
    <button class="v2-btn" data-act="zt-auswertung" data-val="monat">📊 Auswertung</button></div>`;
}
// PROJEKTZEITEN Z3: Zeiten auswerten (Woche/Monat/Jahr) je Kunde, Taetigkeit, Woche/Monat; CSV-Export
async function ztAuswertung(art, vonX, bisX) {
  const h = new Date(), iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const mo = new Date(h); mo.setDate(h.getDate() - ((h.getDay() + 6) % 7));
  const B = { woche: [mo, h], vorwoche: [new Date(mo.getFullYear(), mo.getMonth(), mo.getDate() - 7), new Date(mo.getFullYear(), mo.getMonth(), mo.getDate() - 1)],
    monat: [new Date(h.getFullYear(), h.getMonth(), 1), h], vormonat: [new Date(h.getFullYear(), h.getMonth() - 1, 1), new Date(h.getFullYear(), h.getMonth(), 0)],
    jahr: [new Date(h.getFullYear(), 0, 1), h] };
  const [v, b] = vonX ? [vonX, bisX] : (B[art] || B.monat).map(iso);
  const d = await jget(`/api/finanzen/zeit/auswertung?von=${v}&bis=${b}`);
  const chip = (k, t) => `<button class="v2-btn sm ${k === art ? "pri" : ""}" data-act="zt-auswertung" data-val="${k}">${t}</button>`;
  const tab = (titel, rows) => rows.length ? `<h3>${titel}</h3><div class="v2-tab-scroll"><table class="v2-table v2-zt-aw"><thead><tr><th></th><th class="num">Stunden</th><th class="num">km</th><th class="num">intern</th></tr></thead><tbody>${rows.map(r => `<tr><td>${esc(r.name)}</td><td class="num"><b>${esc(dauerTxt(r.minuten))}</b></td><td class="num">${r.km ? esc(String(r.km)) : ""}</td><td class="num">${cent2eur(r.kosten_cent)}</td></tr>`).join("")}</tbody></table></div>` : "";
  const s = (d && d.summe) || {};
  const lang = d && Object.keys(d).length && (d.je_woche || []).length > 1;
  openModal("📊 Zeiten auswerten", `<div class="v2-zt-chips">${chip("woche", "Diese Woche")}${chip("vorwoche", "Letzte Woche")}${chip("monat", "Dieser Monat")}${chip("vormonat", "Letzter Monat")}${chip("jahr", "Dieses Jahr")}</div>
    <div class="v2-an-zeile" style="margin-top:8px"><label class="v2-feld"><small>von</small><input id="aw-von" class="v2-inp" type="date" value="${esc(v)}"></label><label class="v2-feld"><small>bis</small><input id="aw-bis" class="v2-inp" type="date" value="${esc(b)}"></label><button class="v2-btn" data-act="zt-auswertung" data-val="frei">Anzeigen</button></div>
    ${!d ? emptyRow("Auswertung nicht verfügbar.") : `<div class="v2-aw-kpis"><div class="v2-aw-kpi"><small>Stunden</small><b>${esc(dauerTxt(s.minuten || 0))}</b></div><div class="v2-aw-kpi"><small>Einträge</small><b>${s.eintraege || 0}</b></div><div class="v2-aw-kpi"><small>km</small><b>${s.km || 0}</b></div><div class="v2-aw-kpi"><small>intern (kalkulatorisch)</small><b>${cent2eur(s.kosten_cent || 0)}</b></div></div>
    ${s.eintraege ? "" : emptyRow("Keine Zeiten in diesem Zeitraum.")}
    ${tab("Je Kunde", d.je_kunde || [])}${tab("Je Tätigkeit", d.je_taetigkeit || [])}${tab("Je Auftrag", (d.je_auftrag || []))}${lang ? tab((d.je_monat || []).length > 1 ? "Je Monat" : "Je Woche", ((d.je_monat || []).length > 1 ? d.je_monat : d.je_woche)) : ""}
    <div class="v2-card-actions" style="margin-top:10px"><a class="v2-btn" href="/api/finanzen/zeit/auswertung?von=${esc(v)}&bis=${esc(b)}&format=csv">⬇️ CSV herunterladen</a></div>
    <small class="v2-sub">🔒 Nur intern – Stunden und Kosten sind kalkulatorisch, keine Buchung.</small>`}`, true);
}
async function zeitFenster(meldung, fehler) {
  const [z, a] = await Promise.all([jget("/api/finanzen/zeit"), jget("/api/crm/auftraege")]);
  if (z) { ZEIT.laufend = z.laufend || null; ZEIT.taetigkeiten = z.taetigkeiten || []; }
  ZEIT.alle = (a && a.auftraege) || []; ZEIT.auftraege = ZEIT.alle.filter(x => x.status === "beauftragt");
  openModal("⏱ Zeiterfassung", `<div id="zt-box">${zeitInhalt(meldung, fehler)}</div>`);
  zeitZeigen();
}
const zeitNeuZeichnen = (m, f) => { const b = $("#zt-box"); if (b) b.innerHTML = zeitInhalt(m, f); zeitZeigen(); };
async function zeitStart() {
  const nr = ($("#zt-auftrag") || {}).value; if (!nr) return;
  try { localStorage.setItem("luna-zeit-auftrag", nr); } catch { }
  ZEIT.ergebnis = null; ZEIT.laufend = { start: new Date().toISOString(), start_ms: Date.now(), auftrag: nr, vorlaeufig: true };   // sofort umschalten
  zeitNeuZeichnen();
  const r = await jpost("/api/finanzen/zeit/start", { auftrag: nr });
  if (!r || r.ok === false) { ZEIT.laufend = null; return zeitNeuZeichnen((r && r.hinweis) || "Start hat nicht geklappt.", true); }
  ZEIT.laufend = { id: r.id, start: r.start, start_ms: r.start_ms, auftrag: r.auftrag, firma: r.firma };
  zeitNeuZeichnen();
}
async function zeitStopp() {
  const vorher = ZEIT.laufend; ZEIT.laufend = null; zeitNeuZeichnen();           // sofort umschalten
  const r = await jpost("/api/finanzen/zeit/stopp", {});
  if (!r || r.ok === false) { ZEIT.laufend = vorher; return zeitNeuZeichnen((r && r.hinweis) || "Stoppen hat nicht geklappt.", true); }
  ZEIT.ergebnis = r;
  if (!$("#zt-box")) return zeitFenster();
  zeitNeuZeichnen();
}

// Kennzahlen je Bereich (Etappe 4) -- nur aus bestehenden Endpunkten; ein Kontext teilt die Abrufe einer Seite
function bereichKontext(vorhanden = {}) {
  const c = { ...vorhanden }, einmal = (k, f) => (c[k] = c[k] || f());
  return {
    hb: () => einmal("hb", () => Promise.resolve(vorhanden.hbDaten || jget("/api/handlungsbedarf"))),
    fin: () => einmal("fin", () => darf("finanzen") ? jget("/api/finanzen/uebersicht") : Promise.resolve(null)),
    reels: () => einmal("reels", () => darf("cutter") ? jget("/api/reel") : Promise.resolve(null)),
    loop: () => einmal("loop", () => Promise.resolve(vorhanden.loopDaten || (darf("investment") ? jget("/api/investment/loop") : null))),
    betrieb: () => einmal("betrieb", () => jget("/api/betrieb/status")),
  };
}
async function bereichDaten(b, k) {
  const hb = await k.hb() || { punkte: [], bereiche: {} };
  const offen = (hb.bereiche || {})[b.id] || 0, dringend = (hb.punkte || []).filter(p => p.bereich_id === b.id && p.stufe === "dringend").length;
  const punkte = ["Offene Punkte", String(offen), dringend ? `${dringend} dringend` : "nichts dringend"];
  if (b.id === "geschaeft") {
    const u = await k.fin(); if (!u) return { kpis: [punkte], zeilen: [["Offene Punkte", String(offen)]] };
    const pl = u.pipeline || {}, fo = u.forderungen || {};
    return { kpis: [punkte, ["Gewinn " + u.jahr, cent2eur(u.kennzahlen.gewinn_cent), "echte Zahlen, ohne kalkulatorische Kosten"],
        ["Offen: bekommen wir", cent2eur(fo.summe_cent || 0), `${fo.anzahl || 0} Rechnung(en)${fo.ueberfaellig ? ` · ${fo.ueberfaellig} überfällig` : ""}`],
        ["Angebote offen", String(pl.angebote_anzahl || 0), cent2eur(pl.angebote_cent || 0)]],
      zeilen: [["Angebote offen", `${pl.angebote_anzahl || 0} · ${cent2eur(pl.angebote_cent || 0)}`], ["Offen: bekommen wir", cent2eur(fo.summe_cent || 0)], ["Gewinn " + u.jahr, cent2eur(u.kennzahlen.gewinn_cent)]] };
  }
  if (b.id === "content") {
    const r = await k.reels(), wartet = r ? (r.reels || []).filter(x => x.status === "wartet").length : null;
    const crm = (hb.punkte || []).filter(p => p.bereich === "CRM").length;
    return { kpis: [punkte, ["Reels zur Freigabe", wartet == null ? "–" : String(wartet), "warten auf dich"], ["CRM-Aufgaben", String(crm), "fällige Collab-To-dos"]],
      zeilen: [["Offene Punkte", String(offen)], ["Reels zur Freigabe", wartet == null ? "–" : String(wartet)], ["CRM-Aufgaben", String(crm)]] };
  }
  if (b.id === "investment") {
    const l = await k.loop() || {}, g = (l.kennzahlen && l.kennzahlen.gesamt) || {};
    return { kpis: [punkte, ["Trefferquote", g.n ? pct(g.richtungsquote) : "–", g.n ? `Richtung, n=${g.n}` : "noch keine Auswertung"]],
      zeilen: [["Offene Entscheidungen", String(offen)], ["Trefferquote", g.n ? pct(g.richtungsquote) : "–"]] };
  }
  const be = await k.betrieb();
  const antr = ((hb.punkte || []).find(p => p.id === "freigaben") || {}).anzahl || 0;     // dieselbe Quelle wie die Glocke
  const bot = be && be.bot_alter_min != null ? (be.bot_alter_min <= 45 ? "läuft" : `seit ${Math.round(be.bot_alter_min)} min stumm`) : "–";
  return { kpis: [punkte, ["Freigaben offen", String(antr), "Anträge von LUNA"], ["Telegram-Bot", bot, be && be.bot_alter_min != null ? `Herzschlag vor ${Math.round(be.bot_alter_min)} min` : "kein Herzschlag gemeldet"]],
    zeilen: [["Freigaben offen", String(antr)], ["Telegram-Bot", bot]] };
}
async function bereichKopf(b) {
  const k = bereichKontext(), d = await bereichDaten(b, k), hb = await k.hb() || { punkte: [] };
  const naechstes = (hb.punkte || []).filter(p => p.bereich_id === b.id).slice(0, 6);
  return `<div class="v2-grid">${d.kpis.map(([t, z, sub]) => tile(t, `<div class="v2-kpi">${esc(z)}</div><div class="v2-sub">${esc(sub)}</div>`, { 1: "w12", 2: "w6", 3: "w4" }[d.kpis.length] || "")).join("")}
    ${tile("Als Nächstes in diesem Bereich", naechstes.length ? naechstes.map(t => hbZeile(t, false)).join("") : `<div class="v2-check done" style="border:none"><span class="mark">✓</span>Hier wartet nichts auf dich.</div>`, "w12")}</div>`;
}
async function startBereiche(k) {
  const karten = await Promise.all(BEREICHE.filter(b => teilErlaubt(b).length).map(async b => {
    const d = await bereichDaten(b, k);
    return `<button class="v2-bereich-k" data-go="${bereichZiel(b)}"><span class="kopf"><span class="sym">${b.icon}</span>${esc(b.label)}</span>
      <span class="v2-sub">${esc(teilErlaubt(b).map(seitenName).join(", "))}</span>
      <span>${d.zeilen.map(([n, v]) => `<span class="v2-kv"><span>${esc(n)}</span><b>${esc(v)}</b></span>`).join("")}</span></button>`;
  }));
  return `<div class="v2-bereiche-start">${karten.join("")}</div>`;
}
// Bereichs-Startseite (Etappe 1: Spruenge; Etappe 4 ergaenzt Kennzahlen)
async function renderBereich() {
  const b = bereichVon(AKTIV); if (!b) return renderDash();
  const spruenge = `<div class="v2-sprung">${teilErlaubt(b).map(t => { const x = SECTIONS.find(s => s.id === t);
    return `<button class="v2-sprung-k" data-go="${t}"><span class="i">${x.icon}</span><b>${esc(x.label)}</b><small>${esc(TEIL_INFO[t] || "")}</small></button>`; }).join("")}</div>`;
  const oben = typeof bereichKopf === "function" ? await bereichKopf(b) : "";
  if (bereichVon(AKTIV) !== b) return;
  $("#v2-app").innerHTML = secHead(b.icon + " " + b.label) + oben + `<h3 class="v2-h3">Direkt zu</h3>` + spruenge;
}
BEREICHE.forEach(b => { RENDER["b-" + b.id] = renderBereich; });

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
  FORM_GEAENDERT = false;
  let m = $("#v2-modal"); if (!m) { m = document.createElement("div"); m.id = "v2-modal"; document.body.appendChild(m); }
  m.innerHTML = `<div class="v2-modal-back" data-modal-close></div><div class="v2-modal-card${breit ? " breit" : ""}"><header><b>${esc(title)}</b><button class="v2-icon" data-modal-close>✕</button></header><div class="v2-modal-body">${html}</div></div>`;
  m.hidden = false;
}
const formUngespeichert = () => FORM_GEAENDERT && !!document.querySelector("#v2-modal .v2-an-editor:not(.gesperrt)");
function closeModal() { const m = $("#v2-modal"); if (m && !m.hidden) {
  if (formUngespeichert() && !confirm("Im Formular gibt es ungespeicherte Änderungen. Wirklich schließen?")) return;
  FORM_GEAENDERT = false; m.hidden = true; seiteAktualisieren(); } }   // Aenderungen im Fenster -> Seite sofort aktuell

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
  [STATE, OVERVIEW, LOOP, TODOS] = await Promise.all([jget("/api/state"), jget("/api/overview"), jget("/api/investment/loop"), jget("/api/handlungsbedarf")]);
  TODOS = TODOS || { punkte: [], zaehler: { gesamt: 0, dringend: 0, woche: 0, spaeter: 0 }, bereiche: {} };
  GLOCKE_N = TODOS.zaehler.dringend || 0; glockeZeigen();
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
    todos: { span: "w12", link: null, aria: `Handlungsbedarf: ${TODOS.zaehler.gesamt}`, html: handlungKompakt(TODOS) },
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
  const hbKachel = darf("finanzen") ? tile("⚡ Handlungsbedarf", handlungKompakt(TODOS), "w8")
      + tile("⏱ Zeit", `<div id="v2-zeit-kachel" class="v2-zeit-kachel">${zeitKachelInhalt()}</div>`, "w4")
    : tile("⚡ Handlungsbedarf", handlungKompakt(TODOS), "w12");
  delete W.todos;                                            // Handlungsbedarf steht fest oben (Etappe 4)
  const order = DASH2.order.filter(id => W[id] && !DASH2.hidden.includes(id));
  const bereiche = await startBereiche(bereichKontext({ hbDaten: TODOS, loopDaten: LOOP }));
  if (AKTIV !== "dash") return;
  const stunde = new Date().getHours(), gruss = stunde < 11 ? "Guten Morgen" : stunde < 18 ? "Hallo" : "Guten Abend";
  const editBtn = `<button class="v2-btn ${EDIT2 ? "pri" : ""}" data-editdash>${EDIT2 ? "✓ Fertig" : "✎ Anpassen"}</button>`;
  $("#v2-app").innerHTML = `
    <div class="v2-welcome"><div class="v2-welcome-row"><div><h1>${gruss}, ${esc(ME.display_name || "CEO")}</h1>
      <p>Was ansteht und wo du hinwillst.</p></div></div></div>
    <div class="v2-grid">${hbKachel}</div>
    ${bereiche}
    <div class="v2-sec-head v2-dash-kopf"><h2>Dein Dashboard</h2><div class="actions">${editBtn}</div></div>
    <div class="v2-grid ${EDIT2 ? "editing" : ""}">${order.map(id => dashTile(id, W[id])).join("")}</div>
    ${EDIT2 ? dash2Tray(W) : ""}`;
  mountTrends();
}
/* To-dos des Tagesbetriebs (Belege, Rechnungen, Angebote, Aufträge, CRM, Reels) -- zusammengefasst je Bereich.
   Erledigt wird durch die eigentliche Arbeit („Öffnen“) oder direkt („✓ …“); LUNA löscht dazugehörige Kalendertermine. */
// Handlungsbedarf (LUNA_OS_UI_ROADMAP Etappe 3): alle Punkte aus allen Bereichen, nach Stufe
const STUFEN = [["dringend", "Dringend", "überfällig, heute oder Störung"], ["woche", "Diese Woche", "fällig in 7 Tagen oder wartet auf dich"], ["spaeter", "Wenn Zeit ist", "ohne Termin"]];
let HB_FILTER = "";
function hbZeile(t, mitBereich) {
  const b = BEREICHE.find(x => x.id === t.bereich_id);
  const termin = t.faellig ? `<span class="v2-badge ${t.stufe === "dringend" ? "err" : "neutral"}">${t.stufe === "dringend" ? (t.faellig < heuteIso() ? "überfällig" : "heute") : esc(datumDe(t.faellig))}</span>` : "";
  return `<div class="v2-list-row v2-hb-zeile"><span>${t.icon}</span><div class="grow"><b class="v2-todo-titel" role="button" tabindex="0" title="Öffnen" data-act="todo-oeffnen" data-val="${esc(t.act)}" data-id="${esc(t.act_id || "")}">${esc(t.titel)}</b><small>${esc(t.detail || "")}${mitBereich && b ? ` · ${b.icon} ${esc(b.label)}` : ""}</small></div>
    ${termin}${t.erledigen ? `<button class="v2-btn ok sm" data-act="todo-erledigen" data-val="${esc(t.erledigen.pfad)}" data-schluessel="${esc(t.erledigen.schluessel || "")}">${esc(t.erledigen.label)}</button>` : ""}
    <button class="v2-btn sm" data-act="todo-oeffnen" data-val="${esc(t.act)}" data-id="${esc(t.act_id || "")}">Öffnen ›</button></div>`;
}
function hbChips(z) {
  return `<span class="v2-hb-chips">${STUFEN.map(([k, n]) => `<span class="v2-badge ${k === "dringend" && z[k] ? "err" : k === "woche" && z[k] ? "warn" : "neutral"}">${z[k] || 0} ${n}</span>`).join("")}</span>`;
}
function handlungKompakt(d) {
  const z = d.zaehler || {}, dr = (d.punkte || []).filter(p => p.stufe === "dringend");
  if (!z.gesamt) return `<div class="v2-check done" style="border:none"><span class="mark">✓</span>Alles erledigt — nichts wartet auf dich.</div>`;
  const naechste = dr.length ? dr : (d.punkte || []).slice(0, 3);
  return `<div class="v2-hb-kopf"><div class="v2-kpi">${z.gesamt}</div>${hbChips(z)}</div>
    <div class="v2-sub">${dr.length ? "Dringend:" : "Nichts dringend. Als Nächstes:"}</div>
    <div class="v2-todo-liste">${naechste.slice(0, 6).map(t => hbZeile(t, true)).join("")}</div>
    <button class="v2-btn" data-go="handlung">Alle ${z.gesamt} Punkte anzeigen ›</button>`;
}
async function renderHandlung() {
  const d = await jget("/api/handlungsbedarf");
  if (AKTIV !== "handlung") return;
  if (!d) { $("#v2-app").innerHTML = secHead("⚡ Handlungsbedarf") + emptyRow("Nicht erreichbar."); return; }
  const liste = (d.punkte || []).filter(p => !HB_FILTER || p.bereich_id === HB_FILTER);
  const filter = `<div class="v2-tabs" role="group" aria-label="Nach Bereich filtern"><button class="${!HB_FILTER ? "active" : ""}" data-act="hb-filter" data-val="">Alle · ${d.zaehler.gesamt}</button>`
    + BEREICHE.filter(b => d.bereiche[b.id]).map(b => `<button class="${HB_FILTER === b.id ? "active" : ""}" data-act="hb-filter" data-val="${b.id}">${b.icon} ${esc(b.label)} · ${d.bereiche[b.id]}</button>`).join("") + `</div>`;
  const teile = STUFEN.map(([k, n, info]) => { const l = liste.filter(p => p.stufe === k); if (!l.length) return "";
    return tile(`${n} · ${l.length}`, `<div class="v2-sub" style="margin-bottom:6px">${esc(info)}</div>${l.map(t => hbZeile(t, !HB_FILTER)).join("")}`, "w12"); }).join("");
  $("#v2-app").innerHTML = secHead("⚡ Handlungsbedarf") + `<div class="v2-sub" style="margin:-8px 0 14px">Alles, was du tun musst, aus allen Bereichen von LUNA. Erledigtes verschwindet von selbst, sobald LUNA es in der Fachseite sieht.</div>`
    + filter + (teile ? `<div class="v2-grid">${teile}</div>` : emptyRow(HB_FILTER ? "In diesem Bereich ist nichts offen." : "Alles erledigt — nichts wartet auf dich."));
  GLOCKE_N = d.zaehler.dringend || 0; glockeZeigen();
}
RENDER.handlung = renderHandlung;
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
const KUNDE_TYP = { kunde: "Kunde", interessent: "Interessent", lieferant: "Lieferant", partner: "Partner" };
const FIRMA_FORM = [["name", "Firmenname *"], ["typ", "Typ", "typ"], ["strasse", "Straße und Hausnummer"], ["plz", "PLZ"], ["ort", "Ort"], ["land", "Land"],
  ["rechnungsmail", "Rechnungs-Mail", "email"], ["telefon", "Telefon"], ["website", "Website"], ["ustid", "USt-IdNr."], ["handelsregister", "Handelsregister (z. B. Amtsgericht Hamburg HRB 12345)"], ["steuernummer", "Steuernummer"],
  ["zahlungsziel_tage", "Zahlungsziel (Tage)", "number"], ["verbraucher", "Privatperson (Verbraucher)?", "janein"],
  ["kundennummer_bei", "Unsere Kundennummer dort"], ["zahlungsweg", "Zahlungsweg (z. B. PayPal, Mastercard •••• 1364, Lastschrift)"],
  ["rechnungs_absender", "Rechnungs-Absender (Mail oder Domain, mit Komma getrennt)"], ["vertraege", "Verträge / Abos / Policen", "vertraege"], ["notiz", "Notiz", "textarea"]];
// Etappe 14: Lieferanten L-, Partner P-, Kunden K- — die Rollennummer steht vorne, frühere Nummern bleiben gültig
const firmaNr = (x) => x.anzeige || x.nummer;
const firmaOption = (x) => `${firmaNr(x)} · ${x.name}`;
const firmaAusText = (t) => { const m = /^\s*([KLP]-\d{5})\s*·\s*(.*)$/.exec(t || ""); return m ? { firma: m[1], name: m[2].trim() } : { firma: "", name: (t || "").trim() }; };
function vertragZeile(v = {}) {
  return `<div class="v2-an-zeile v2-vertrag"><input class="v2-inp vt-bez" placeholder="Bezeichnung (z. B. AppleCare iPhone)" value="${esc(v.bezeichnung || "")}"><input class="v2-inp vt-nr" placeholder="Vertrags-/Policen-Nr." value="${esc(v.nummer || "")}"><input class="v2-inp vt-notiz" placeholder="Notiz (Laufzeit, Kündigung …)" value="${esc(v.notiz || "")}"></div>`;
}
const AP_FORM = [["vorname", "Vorname"], ["nachname", "Nachname"], ["rolle", "Rolle / Position"], ["mail", "Mail", "email"], ["telefon", "Telefon"], ["notiz", "Notiz", "textarea"]];
const FELD_LBL = Object.fromEntries([...FIRMA_FORM, ...AP_FORM].map(([k, l]) => [k, l.replace(" *", "")]).concat([["aktiv", "Aktiv"], ["collab", "Collab zugeordnet"], ["collab_entfernt", "Collab gelöst"], ["firma", "Firma"]]));
let KUNDEN = { firmen: [], collab_ohne_nummer: [] }, KUNDEN_SUCHE = "", _kundenTimer = null;

function formFelder(prefix, spec, werte = {}) {
  return spec.map(([k, lbl, art]) => {
    const v = werte[k] == null ? "" : String(werte[k]);
    let inp;
    if (art === "typ") inp = `<select id="${prefix}-${k}">${Object.entries(KUNDE_TYP).map(([id, l]) => `<option value="${id}" ${(v || "kunde") === id ? "selected" : ""}>${l}</option>`).join("")}</select>`;
    else if (art === "textarea") inp = `<textarea id="${prefix}-${k}" rows="3" class="v2-inp">${esc(v)}</textarea>`;
    else if (art === "vertraege") inp = `<div id="${prefix}-${k}">${(Array.isArray(werte[k]) && werte[k].length ? werte[k] : [{}]).map(vertragZeile).join("")}</div><button class="v2-btn sm" type="button" data-act="vertrag-neu" data-id="${prefix}-${k}">+ Vertrag</button>`;
    else if (art === "janein") inp = `<select id="${prefix}-${k}"><option value="nein">nein — Firma / Unternehmer</option><option value="ja" ${v === "true" || v === "ja" ? "selected" : ""}>ja — Privatperson</option></select>`;
    else inp = `<input id="${prefix}-${k}" type="${art || "text"}" value="${esc(v)}" ${art === "number" ? 'min="0" max="365"' : ""}>`;
    return `<label class="v2-feld"><small>${esc(lbl)}</small>${inp}</label>`;
  }).join("");
}
function formWerte(prefix, spec) {
  const o = {};
  spec.forEach(([k, , art]) => {
    const e = $(`#${prefix}-${k}`); if (!e) return;
    if (art === "vertraege") o[k] = [...e.querySelectorAll(".v2-vertrag")].map(z => ({ bezeichnung: z.querySelector(".vt-bez").value.trim(), nummer: z.querySelector(".vt-nr").value.trim(), notiz: z.querySelector(".vt-notiz").value.trim() })).filter(v => v.bezeichnung || v.nummer);
    else o[k] = e.value.trim();
  });
  return o;
}
function kundenMsg(id, text, ok) { const m = $("#" + id); if (m) { m.textContent = text; m.className = "v2-msg " + (ok ? "ok" : "err"); } }

RENDER.kunden = renderKunden;
async function renderKunden() {
  const sub = SUBTAB.kunden || "firmen";
  const ROLLE = { kunden: "kunde", interessenten: "interessent", lieferanten: "lieferant", partner: "partner" };
  KUNDEN = await jget("/api/crm/kunden" + (KUNDEN_SUCHE ? "?suche=" + encodeURIComponent(KUNDEN_SUCHE) : "")) || { firmen: [], collab_ohne_nummer: [] };
  const alle = KUNDEN.firmen || [], c = KUNDEN.collab_ohne_nummer || [];
  const f = ROLLE[sub] ? alle.filter(x => (x.typ || "kunde") === ROLLE[sub]) : alle;
  let body;
  if (sub === "vorstellungen") body = await vsListe();
  else if (sub === "collab") {
    body = tile("Collab-Firmen ohne Kundennummer", c.map(x => `<div class="v2-list-row"><span class="v2-badge neutral">${esc(x.status || "")}</span><div class="grow"><b>${esc(x.firma)}</b><small>${esc(kanal[x.quelle] || x.quelle || "")} · ${x.nachrichten || 0} Nachr.${x.letzter_kontakt ? " · " + esc(zeitKurz(x.letzter_kontakt)) : ""}</small></div>
      <button class="v2-btn" data-act="kunde-neu" data-id="${esc(x.firma)}">+ Als Firma anlegen</button><button class="v2-btn" data-act="kunde-collab-zu" data-id="${esc(x.firma)}">Zuordnen…</button></div>`).join("") || emptyRow("Alle Collab-Firmen haben eine Kundennummer."), "w12");
  } else {
    const rows = f.map(x => `<tr class="klick" data-act="kunde-detail" data-id="${esc(x.nummer)}"><td><b>${esc(firmaNr(x))}</b>${firmaNr(x) !== x.nummer ? `<br><small class="v2-sub">früher ${esc(x.nummer)}</small>` : ""}</td><td>${esc(x.name)}${x.aktiv ? "" : ` <span class="v2-badge neutral">inaktiv</span>`}${(x.luecken || []).length && x.typ !== "kunde" ? ` <span class="v2-badge wartet" title="fehlt: ${esc(x.luecken.join(", "))}">⚠️ ${esc(x.luecken.join(", "))} fehlt</span>` : ""}</td><td>${esc(KUNDE_TYP[x.typ] || x.typ || "")}</td><td>${esc([x.plz, x.ort].filter(Boolean).join(" "))}</td><td>${x.ansprechpartner || 0}</td><td>${(x.collab || []).length ? "🤝" : ""}</td></tr>`).join("");
    body = `${kpiTile("Firmen", String(f.filter(x => x.aktiv).length), null, "aktiv")}${kpiTile("Collab ohne Nummer", String(c.length), null, "noch zuzuordnen")}
      ${tile(KUNDEN_SUCHE ? `Treffer für „${KUNDEN_SUCHE}"` : "Firmen", rows ? `<table class="v2-table"><thead><tr><th>Nr.</th><th>Firma</th><th>Typ</th><th>Ort</th><th>Ansprechp.</th><th></th></tr></thead><tbody>${rows}</tbody></table>` : emptyRow(KUNDEN_SUCHE ? "Keine Treffer." : "Noch keine Firma angelegt — oben rechts „+ Neue Firma“."), "w12")}`;
  }
  const actions = `<input id="kunden-suche" class="v2-inp" placeholder="Suchen (Name, Nr., Ort, Ansprechpartner)…" value="${esc(KUNDEN_SUCHE)}" style="width:260px"><button class="v2-btn" data-act="vs-neu">✉️ Neue Mail</button><button class="v2-btn pri" data-act="kunde-neu">+ Neue Firma</button>`;
  const n = (t) => alle.filter(x => (x.typ || "kunde") === t).length;
  $("#v2-app").innerHTML = secHead("Kunden & Lieferanten", actions) + tabs("kunden", [["firmen", `Alle (${alle.length})`], ["kunden", `Kunden (${n("kunde")})`], ["interessenten", `Interessenten (${n("interessent")})`], ["vorstellungen", "✉️ Vorstellungen"], ["lieferanten", `Lieferanten (${n("lieferant")})`], ["partner", `Partner (${n("partner")})`], ["collab", `Collab ohne Nummer (${c.length})`]]) + `<div class="v2-grid">${body}</div>`;
  const s = $("#kunden-suche");
  if (s) {
    s.addEventListener("input", () => { clearTimeout(_kundenTimer); _kundenTimer = setTimeout(() => { KUNDEN_SUCHE = s.value.trim(); renderKunden().then(() => { const n = $("#kunden-suche"); if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }); }, 300); });
  }
}
/* SERIEN_UND_VORSTELLUNG V1/V2: Vorstellungs-Mail an Firmen (Firma beim Senden als Interessent), Ueberblick + Nachfassen */
let VS = { firma: "", nachfassen: false, v: null, textGeaendert: false };
async function vsDialog(firma, nachfassen) {
  if (!AN_FIRMEN.length) await belegFormDaten().catch(() => { });
  VS = { firma: firma || "", nachfassen: !!nachfassen, v: null, textGeaendert: false };
  const firmen = (AN_FIRMEN || []).filter(f => f.typ !== "lieferant");
  openModal(nachfassen ? "✉️ Nachfassen" : "✉️ Neue Mail an eine Firma", `<div class="v2-form" id="vs-form">
    <label class="v2-feld"><small>Empfänger</small><select class="v2-inp" id="vs-firma"><option value="">Neue Firma (wird beim Senden als Interessent angelegt)</option>${firmen.map(f => `<option value="${esc(f.nummer)}" ${f.nummer === VS.firma ? "selected" : ""}>${esc(f.name)} (${esc(f.nummer)})</option>`).join("")}</select></label>
    <div id="vs-neu" class="v2-form" ${VS.firma ? "hidden" : ""}>
      <label class="v2-feld"><small>Firmenname *</small><input class="v2-inp" id="vs-name" maxlength="200" placeholder="z. B. Kiez Alm Gastro GmbH"></label>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Vorname</small><input class="v2-inp" id="vs-vorname"></label><label class="v2-feld"><small>Nachname</small><input class="v2-inp" id="vs-nachname"></label></div>
      <label class="v2-feld"><small>Website (optional)</small><input class="v2-inp" id="vs-web" inputmode="url" placeholder="https://…"></label></div>
    <label class="v2-feld"><small>An (Mailadresse) *</small><input class="v2-inp" id="vs-an" type="email" inputmode="email" placeholder="name@firma.de"></label>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Vorlage</small><select class="v2-inp" id="vs-vorlage"></select></label>
      <label class="v2-modlbl" id="vs-nf-l" hidden><input type="checkbox" id="vs-nf" ${nachfassen ? "checked" : ""}> Nachfassen</label></div>
    <label class="v2-feld"><small>Betreff *</small><input class="v2-inp" id="vs-betreff"></label>
    <label class="v2-feld"><small>Text * (mit deiner Signatur)</small><textarea class="v2-inp" id="vs-text" rows="12"></textarea></label>
    <div class="v2-msg v2-vs-uwg" id="vs-uwg"></div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Anlass (optional, als Nachweis)</small><select class="v2-inp" id="vs-anlass"><option value="">— keiner —</option></select></label>
      <label class="v2-feld"><small>Notiz zum Anlass</small><input class="v2-inp" id="vs-anlass-notiz" maxlength="300" placeholder="z. B. Gespräch beim Derby, 03.10."></label></div>
    <div class="v2-kv"><span>Absender</span><b id="vs-absender">…</b></div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="vs-senden" id="vs-senden-knopf">✉️ Jetzt senden</button></div><div class="v2-msg" id="vs-msg"></div></div>`);
  const f = $("#vs-form");
  f.addEventListener("input", (e) => { if (e.target.id === "vs-text" || e.target.id === "vs-betreff") VS.textGeaendert = true; });
  let timer;
  const neuLaden = () => { clearTimeout(timer); timer = setTimeout(() => vsVorschau(), 350); };
  ["vs-name", "vs-vorname", "vs-nachname"].forEach(id => $("#" + id).addEventListener("input", neuLaden));
  $("#vs-firma").addEventListener("change", () => { VS.firma = $("#vs-firma").value; $("#vs-neu").hidden = !!VS.firma; VS.textGeaendert = false; vsVorschau(true); });
  $("#vs-vorlage").addEventListener("change", () => { VS.textGeaendert = false; vsVorschau(); });
  $("#vs-nf").addEventListener("change", () => { VS.nachfassen = $("#vs-nf").checked; VS.textGeaendert = false; vsVorschau(); });
  await vsVorschau(true);
  ($(VS.firma ? "#vs-text" : "#vs-name") || {}).focus?.();
}
async function vsVorschau(empfaenger) {
  const q = new URLSearchParams({ firma: VS.firma, name: ($("#vs-name") || {}).value || "", vorname: ($("#vs-vorname") || {}).value || "",
    nachname: ($("#vs-nachname") || {}).value || "", vorlage: ($("#vs-vorlage") || {}).value || "", nachfassen: VS.nachfassen ? "1" : "0" });
  const v = await jget("/api/crm/vorstellung/vorschau?" + q); if (!v || !$("#vs-form")) return;
  VS.v = v;
  if (v.bisher && !VS.nachfassen && empfaenger && VS.firma) { VS.nachfassen = true; $("#vs-nf").checked = true; return vsVorschau(empfaenger); }
  $("#vs-nf-l").hidden = !v.bisher;
  $("#vs-vorlage").innerHTML = (v.vorlagen || []).map(x => `<option value="${esc(x.id)}" ${x.id === v.vorlage ? "selected" : ""}>${esc(x.name)}${x.standard && x.name !== "Standard" ? " (Standard)" : ""}</option>`).join("");
  if (!VS.textGeaendert) { $("#vs-betreff").value = v.betreff; $("#vs-text").value = v.text; }
  if (empfaenger && v.an) $("#vs-an").value = v.an;
  if ($("#vs-anlass").options.length <= 1) $("#vs-anlass").insertAdjacentHTML("beforeend", Object.entries(v.anlaesse || {}).map(([k, l]) => `<option value="${esc(k)}">${esc(l)}</option>`).join(""));
  $("#vs-uwg").textContent = "⚖️ " + v.hinweis_uwg + (v.bisher ? ` · Diese Firma hast du am ${datumDe(v.bisher)} schon angeschrieben.` : "");
  $("#vs-absender").textContent = v.absender;
  const k = $("#vs-senden-knopf"); k.disabled = !v.bereit; k.title = v.bereit ? "" : "Versand nicht eingerichtet";
}
async function vsSenden(el, trotz) {
  const body = { an: $("#vs-an").value.trim(), betreff: $("#vs-betreff").value.trim(), text: $("#vs-text").value.trim(), anlass: $("#vs-anlass").value,
    anlass_notiz: $("#vs-anlass-notiz").value.trim(), nachfassen: VS.nachfassen, bestaetigt: true, trotz_dublette: !!trotz };
  if (VS.firma) body.firma = VS.firma;
  else body.neu = { name: $("#vs-name").value.trim(), vorname: $("#vs-vorname").value.trim(), nachname: $("#vs-nachname").value.trim(), website: $("#vs-web").value.trim() };
  const m = $("#vs-msg");
  if (!confirm(`Mail jetzt an ${body.an} senden?`)) return;
  el.disabled = true; m.className = "v2-msg"; m.textContent = "Sende …";
  const r = await jpost("/api/crm/vorstellung/senden", body); el.disabled = false;
  if (r && r.ok === false && r.dublette) {
    m.className = "v2-msg err";
    m.innerHTML = `${esc(r.hinweis)}<div class="v2-card-actions" style="margin-top:8px">${r.dublette.map(n => `<button class="v2-btn sm" data-act="vs-dublette-nehmen" data-id="${esc(n)}">${esc(((AN_FIRMEN || []).find(f => f.nummer === n) || {}).name || n)} nehmen</button>`).join("")}<button class="v2-btn sm" data-act="vs-trotzdem">Trotzdem neu anlegen</button></div>`;
    return;
  }
  if (!r || r.ok === false) { m.className = "v2-msg err"; m.textContent = (r && r.hinweis) || "Keine Verbindung."; return; }
  AN_FIRMEN = []; if (AKTIV === "kunden") renderKunden();
  return kundeDetail(r.firma, `✉️ Mail an ${r.an} gesendet${r.neu_angelegt ? " – Firma als Interessent angelegt" : ""}. Antworten meldet LUNA per Telegram.`);
}
async function vsListe() {
  const d = await jget("/api/crm/vorstellungen") || {}, l = d.vorstellungen || [];
  const st = (x) => x.antwort ? `<span class="v2-badge ok">💬 Antwort ${esc(datumDe(x.antwort))}</span>` : x.erledigt ? `<span class="v2-badge neutral">✓ ${esc(x.erledigt)}</span>`
    : x.typ !== "interessent" ? `<span class="v2-badge ok">${esc(KUNDE_TYP[x.typ] || x.typ)}</span>`
    : x.nachfassen_faellig ? `<span class="v2-badge warn">Nachfassen fällig</span>` : `<span class="v2-badge wartet">wartet bis ${esc(datumDe(x.faellig_am))}</span>`;
  const rows = l.map(x => `<div class="v2-list-row v2-vs-zeile"><span>✉️</span><div class="grow"><b class="klick" data-act="kunde-detail" data-id="${esc(x.firma)}">${esc(x.name)}</b>
      <small>${esc(datumDe(x.erste))}${x.anzahl > 1 ? ` · ${x.anzahl} Mails (${x.nachgefasst} × nachgefasst)` : ""} · an ${esc(x.an)}</small></div>${st(x)}
      ${x.faellig_am ? `<button class="v2-btn sm" data-act="vs-neu" data-id="${esc(x.firma)}" data-val="nachfassen">Nachfassen …</button><button class="v2-btn sm" data-act="vs-erledigt" data-id="${esc(x.firma)}">Kein Interesse</button>` : ""}</div>`).join("");
  return tile(`Vorstellungen (${l.length})`, rows || emptyRow("Noch keine Vorstellungs-Mail – „✉️ Neue Mail“ oben rechts."), "w12",
    `<small class="v2-sub">ohne Antwort nach ${d.nachfassen_tage || 7} Tagen: Erinnerung zum Nachfassen</small>`);
}
// IMPRESSUM_SUCHE I1: Website/Impressum-Link eintragen -> leere Felder aus dem Impressum vorausfuellen (nur Vorschlag)
function impressumSuche(prefix) {
  return `<div class="v2-impressum"><label class="v2-feld"><small>Website oder Link zum Impressum</small><input class="v2-inp" id="${prefix}-impressum-url" inputmode="url" autocomplete="off" placeholder="Website oder Impressum-Seite der Firma"></label>
    <button class="v2-btn" data-act="impressum-suchen" data-val="${prefix}">🔎 Kundendaten suchen</button></div><div class="v2-msg" id="${prefix}-impressum-msg"></div>`;
}
async function impressumSuchen(prefix, el) {
  const m = $(`#${prefix}-impressum-msg`), url = ($(`#${prefix}-impressum-url`).value || ($(`#${prefix}-website`) || {}).value || "").trim();
  if (!url) { m.className = "v2-msg err"; m.textContent = "Bitte die Website oder den Link zum Impressum eintragen."; return; }
  el.disabled = true; m.className = "v2-msg"; m.textContent = "🔎 Lese das Impressum …";
  const r = await jpost("/api/crm/impressum-suche", { url }); el.disabled = false;
  if (!r || r.ok === false) { m.className = "v2-msg err"; m.textContent = (r && r.hinweis) || "Keine Verbindung."; return; }
  const v = r.vorschlaege || {}, gefuellt = [], anders = [];
  for (const [k, wert] of Object.entries(v)) {
    const e = $(`#${prefix}-${k}`); if (!e) continue;
    if (!e.value.trim()) { e.value = wert; e.classList.add("v2-erkannt"); gefuellt.push(k); }
    else if (e.value.trim() !== String(wert)) anders.push(`${(FIRMA_FORM.find(f => f[0] === k) || [k, k])[1].replace(" *", "")}: ${wert}`);
  }
  if (!Object.keys(v).length) { m.className = "v2-msg err"; m.textContent = r.hinweis || "Nichts gefunden."; return; }
  m.className = "v2-msg ok";
  m.innerHTML = `✅ ${gefuellt.length} Feld${gefuellt.length === 1 ? "" : "er"} aus dem Impressum vorausgefüllt – bitte prüfen, gespeichert wird erst mit dem Knopf unten.`
    + (r.quelle ? ` <a href="${esc(r.quelle)}" target="_blank" rel="noopener">Quelle ↗</a>` : "")
    + (anders.length ? `<br><small>Nicht überschrieben (schon ausgefüllt): ${esc(anders.join(" · "))}</small>` : "");
}
/* GLOBALE_SUCHE G1: eine Suche ueber alles Geschaeftliche, Ergebnisse nach Kategorien */
let SUCHE = { q: "", timer: null, nr: 0, erster: null };
function sucheOeffnen() {
  openModal("🔎 Suchen", `<div class="v2-suche"><input id="suche-q" class="v2-inp" type="search" autocomplete="off" enterkeyhint="search"
      placeholder="Firma, Nummer, Titel, Betrag (1.600), Datum (03.10.) …" value="${esc(SUCHE.q)}">
    <small class="v2-sub">Durchsucht Kunden, Angebote, Aufträge, Rechnungen, Mahnungen, Ausgaben, Eigenbelege, Content-Plan, Konzepte und die Akte.</small>
    <div id="suche-erg"></div></div>`);
  const i = $("#suche-q");
  i.addEventListener("input", () => { clearTimeout(SUCHE.timer); SUCHE.timer = setTimeout(sucheLaden, 200); });
  i.addEventListener("keydown", (e) => { if (e.key === "Enter" && SUCHE.erster) { e.preventDefault(); SUCHE.erster.click(); } });
  i.focus(); i.select();
  if (SUCHE.q) sucheLaden();
}
async function sucheLaden() {
  const i = $("#suche-q"), box = $("#suche-erg"); if (!i || !box) return;
  const q = i.value.trim(); SUCHE.q = q; const nr = ++SUCHE.nr;
  if (q.length < 2) { box.innerHTML = ""; SUCHE.erster = null; return; }
  box.innerHTML = `<div class="v2-empty">Suche …</div>`;
  const d = await jget("/api/suche?q=" + encodeURIComponent(q));
  if (nr !== SUCHE.nr || !$("#suche-erg")) return;                 // inzwischen weitergetippt
  if (!d || !d.gruppen || !d.gruppen.length) { box.innerHTML = emptyRow(`Nichts gefunden für „${q}“.`); SUCHE.erster = null; return; }
  box.innerHTML = `<div class="v2-sub v2-suche-anzahl">${d.gesamt} Treffer</div>` + d.gruppen.map(g => `<section class="v2-suche-gruppe"><h4>${esc(g.titel)} <span class="v2-badge neutral">${g.anzahl}</span></h4>
    ${g.treffer.map(t => `<button class="v2-list-row v2-suche-treffer" data-act="suche-treffer" data-val="${esc(t.act)}" data-id="${esc(t.act_id)}">
      <div class="grow"><b>${esc(t.titel)}</b><small>${esc(t.info || "")}${t.datum ? (t.info ? " · " : "") + esc(datumDe(t.datum)) : ""}</small></div><span>›</span></button>`).join("")}
    ${g.anzahl > g.treffer.length ? `<small class="v2-sub">… und ${g.anzahl - g.treffer.length} weitere – Suche genauer eingrenzen</small>` : ""}</section>`).join("");
  SUCHE.erster = box.querySelector(".v2-suche-treffer");
}
async function sucheTreffer(act, id) {
  if (act === "cp-suche") { CP.tag = id || heuteIso(); closeModal(); return go("contentplan"); }
  if (act === "konzept") return konzeptFenster(id);
  if (act === "akte-datei") { window.open(`/api/crm/akte/${encodeURIComponent(id)}/datei`, "_blank", "noopener"); return; }   // Mail ohne Firma
  const el = document.createElement("button"); el.dataset.id = id || "";
  return handleAct(act, el);
}
function kundeNeu(collab) {
  openModal("Neue Firma", `<div class="v2-form">${collab ? `<div class="v2-sub">Wird mit der Collab-Firma <b>${esc(collab)}</b> verknüpft.</div>` : ""}${impressumSuche("kf")}${formFelder("kf", FIRMA_FORM, collab ? { name: collab, typ: "partner" } : {})}
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
  const verlauf = (f.verlauf || []).slice().reverse().map(v => `<div class="v2-list-row"><div class="grow"><b>${esc({ firma_angelegt: "Angelegt", firma_geaendert: "Geändert", firma_nummer_ergaenzt: "Nummer ergänzt", collab_zugeordnet: "Collab verknüpft", collab_geloest: "Collab gelöst" }[v.typ] || v.typ)}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")} · ${esc(Object.entries(v.felder || {}).filter(([k, w]) => w !== "" && w != null).map(([k, w]) => `${FELD_LBL[k] || (k === "nummer_ergaenzt" ? "Nummer" : k)}: ${typeof w === "boolean" ? (w ? "ja" : "nein") : Array.isArray(w) ? w.map(v => [v.bezeichnung, v.nummer].filter(Boolean).join(" ")).join(", ") : w}`).join(" · "))}</small></div></div>`).join("");
  const bu = (d && d.buchungen) || { belege: [], je_jahr: {}, abo: {} };
  const buHtml = `${bu.abo && bu.abo.monatlich_cent ? `<div class="v2-msg">🔁 Abo erkannt: ca. <b>${esc(cent2eur(bu.abo.monatlich_cent))}</b> im Monat (${esc(bu.abo.monate.map(m => m.slice(5) + "/" + m.slice(0, 4)).join(", "))}) <button class="v2-btn sm" data-act="abo-aus-firma" data-id="${esc(f.nummer)}">Als Abo anlegen</button></div>` : ""}
    ${Object.entries(bu.je_jahr || {}).map(([j, x]) => `<div class="v2-kv"><span>${esc(j)}</span><b>${x.ausgaben_cent ? `bezahlt ${esc(cent2eur(x.ausgaben_cent))}` : ""}${x.ausgaben_cent && x.einnahmen_cent ? " · " : ""}${x.einnahmen_cent ? `erhalten ${esc(cent2eur(x.einnahmen_cent))}` : ""}</b></div>`).join("")}
    ${(bu.belege || []).map(b => `<div class="v2-list-row klick" data-act="${b.quelle === "eigenbeleg" ? "eb-detail" : "bl-detail"}" data-id="${esc(b.nummer)}"><span class="v2-badge ${b.status === "bezahlt" || b.status === "gebucht" ? "ok" : "neutral"}">${esc(b.status)}</span><div class="grow"><b>${esc(b.nummer)} · ${esc(cent2eur(b.betrag_cent))}</b><small>${esc(datumDe(b.datum))} · ${esc(b.text || "")}</small></div></div>`).join("") || emptyRow("Noch keine Belege unter dieser Nummer.")}`;
  const nummern = (f.nummern || [f.nummer]).filter(x => x !== firmaNr(f));
  openModal(`${firmaNr(f)} · ${f.name}`, `${meldung ? `<div class="v2-msg ok">${esc(meldung)}</div>` : ""}
    ${nummern.length ? `<div class="v2-sub">Auch gültig: ${esc(nummern.join(", "))}</div>` : ""}
    ${f.typ !== "lieferant" ? `<div class="v2-card-actions"><button class="v2-btn" data-act="vs-neu" data-id="${esc(f.nummer)}">✉️ Mail schreiben</button></div>` : ""}
    ${(f.luecken || []).length && f.typ !== "kunde" ? `<div class="v2-msg err">Es fehlt noch: ${esc(f.luecken.join(", "))} – steht meist auf der Rechnung.</div>` : ""}
    ${f.typ !== "kunde" || (bu.belege || []).length ? `<h3>Belege & Zahlungen</h3>${buHtml}` : ""}
    <h3>Stammdaten</h3>${kundeRecherche(f, d)}<div class="v2-form">${f.verbraucher ? "" : impressumSuche("ke")}${formFelder("ke", FIRMA_FORM, f)}
    <label class="v2-modlbl"><input type="checkbox" id="ke-aktiv" ${f.aktiv ? "checked" : ""}> Aktiv (inaktive Firmen bleiben erhalten, nur ausgeblendet)</label>
    <button class="v2-btn pri" data-act="kunde-speichern" data-id="${esc(f.nummer)}">Änderungen speichern</button><div id="ke-msg" class="v2-msg"></div></div>
    <h3>📁 Akte <small class="v2-sub">Dokumente &amp; Mails</small></h3><div id="akte-box"><div class="v2-empty">Lade…</div></div>
    <h3>Ansprechpartner</h3>${aps}<button class="v2-btn" data-act="kunde-ap-neu" data-id="${esc(f.nummer)}" style="margin-top:8px">+ Ansprechpartner</button><div id="kap-box"></div>
    <h3>Angebote</h3><button class="v2-btn" data-act="an-neu" data-id="${esc(f.nummer)}">+ Angebot für ${esc(f.name)}</button>
    <h3>Collab-CRM</h3>${collab}
    <h3>Verlauf</h3>${verlauf}`);
  akteLaden(f.nummer);
}
// Etappe 22: oeffentliche Firmendaten (Impressum) vorschlagen -- uebernommen wird nur per Klick
function kundeRecherche(f, d) {
  const v = d.vorschlaege || {}, namen = d.feldnamen || {}, offen = Object.keys(v);
  if (f.verbraucher) return "";
  const knopf = (d.luecken || []).length ? `<button class="v2-btn" data-act="kunde-recherche" data-id="${esc(f.nummer)}">🔎 Fehlende Daten im Netz suchen</button>` : "";
  if (!offen.length) return knopf ? `<div class="v2-card-actions" style="margin:4px 0 10px">${knopf}<small class="v2-sub">Fehlt: ${esc(d.luecken.map(k => namen[k] || k).join(", "))}</small></div>` : "";
  return `<div class="v2-msg" style="margin:6px 0 12px"><b>🔎 Vorschläge aus dem Netz</b>${d.vorschlag_quelle ? ` · Quelle: <a href="${esc(d.vorschlag_quelle)}" target="_blank" rel="noopener">${esc(d.vorschlag_quelle.replace(/^https?:\/\//, ""))}</a>` : ""}
    ${offen.map(k => `<div class="v2-kv"><span>${esc(namen[k] || k)}</span><b>${esc(v[k])} <button class="v2-btn sm" data-act="kunde-vorschlag" data-id="${esc(f.nummer)}" data-val="${esc(k)}">Übernehmen</button></b></div>`).join("")}
    <div class="v2-card-actions" style="margin-top:6px"><button class="v2-btn ok sm" data-act="kunde-vorschlag" data-id="${esc(f.nummer)}" data-val="">Alle übernehmen</button><button class="v2-btn sm" data-act="kunde-vorschlag-weg" data-id="${esc(f.nummer)}">Verwerfen</button>${knopf}</div></div>`;
}
// Etappe 24: Firmenakte -- Dokumente hochladen, Mails (weitergeleitet / LUNA in CC) chronologisch
async function akteLaden(nr) {
  const box = $("#akte-box"); if (!box) return;
  const d = await jget(`/api/crm/kunden/${encodeURIComponent(nr)}/akte`);
  const docs = (d && d.dokumente) || [], arten = (d && d.arten) || {}, lief = (d && d.lieferungen) || [];
  const ICON = { mail: "✉️", anwalt: "⚖️", vertrag: "📜", schreiben: "📄", notiz: "📝", bericht: "📊", sonstiges: "📎" };
  box.innerHTML = (docs.length ? docs.map(x => `<div class="v2-list-row"><span>${ICON[x.art] || "📎"}</span><div class="grow"><b><a href="/api/crm/akte/${encodeURIComponent(x.id)}/datei" target="_blank" rel="noopener">${esc(x.titel)}</a></b>
      <small>${esc(datumDe(x.datum))} · ${esc(arten[x.art] || x.art)}${x.mail_von ? " · von " + esc(x.mail_von) : ""}${x.bezug ? " · zu " + esc(x.bezug) : ""}${x.notiz ? " · " + esc(x.notiz) : ""}${(x.dateien || []).length > 1 ? ` · <a href="/api/crm/akte/${encodeURIComponent(x.id)}/datei?i=1">Original (.eml)</a>` : ""}</small></div></div>`).join("")
    : `<div class="v2-sub">Noch nichts abgelegt. Mails landen hier automatisch, wenn du sie an LUNA weiterleitest oder LUNA in CC/BCC nimmst.</div>`)
    + (lief.length ? `<h3 class="v2-h3">📦 Geliefert</h3>${lief.map(x => lfAnzeige(x, false)).join("")}` : "")
    + ((d && d.kampagnen || []).length ? `<h3 class="v2-h3">📣 Kampagnen</h3>${d.kampagnen.map(k => `<div class="v2-list-row klick" data-act="ab-detail" data-id="${esc(k.nummer)}"><span>${k.abgeschlossen ? "✅" : "📣"}</span><div class="grow"><b>${esc(k.nummer)}${k.titel ? " · " + esc(k.titel) : ""}</b>
      <small class="v2-kampagne"><span>${esc(datumDe(k.datum))}</span>${k.postings ? `<span>${k.gemessen}/${k.postings} Postings gemessen</span>` : "<span>ohne Postings</span>"}${k.kontakte_ist ? `<span>${esc(Number(k.kontakte_ist).toLocaleString("de-DE"))} Kontakte</span>` : ""}${k.mehrleistung_cent != null ? `<span>${k.mehrleistung_cent >= 0 ? "+" : "−"}${cent2eur(Math.abs(k.mehrleistung_cent))} Mehrleistung</span>` : ""}${k.bericht ? "<span>📝 Bericht gesendet</span>" : ""}</small></div></div>`).join("")}` : "")
    + `<details style="margin-top:8px"><summary><small>+ Dokument hochladen</small></summary><div class="v2-form">
      <div class="v2-an-zeile"><label class="v2-feld"><small>Datei *</small><input id="ak-datei" type="file"></label><label class="v2-feld"><small>Art</small><select id="ak-art">${Object.entries(arten).filter(([k]) => k !== "mail").map(([k, n]) => `<option value="${esc(k)}">${esc(n)}</option>`).join("")}</select></label></div>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Titel</small><input id="ak-titel" placeholder="z. B. Schreiben der Anwältin"></label><label class="v2-feld"><small>Datum</small><input id="ak-datum" type="date"></label><label class="v2-feld"><small>Bezug (optional)</small><input id="ak-bezug" placeholder="z. B. RG-11052026"></label></div>
      <label class="v2-feld"><small>Notiz</small><input id="ak-notiz"></label>
      <button class="v2-btn" data-act="akte-hochladen" data-id="${esc(nr)}">Ablegen</button><div id="ak-msg" class="v2-msg"></div></div></details>`;
}
async function akteHochladen(nr) {
  const f = ($("#ak-datei") || {}).files; if (!f || !f.length) return kundenMsg("ak-msg", "Bitte eine Datei wählen.", false);
  const datei = await blLesen(f[0]);
  const r = await jpost(`/api/crm/kunden/${encodeURIComponent(nr)}/akte`, { datei, art: $("#ak-art").value, titel: $("#ak-titel").value.trim(), datum: $("#ak-datum").value, bezug: $("#ak-bezug").value.trim(), notiz: $("#ak-notiz").value.trim() });
  if (!r || !r.ok) return kundenMsg("ak-msg", (r && r.hinweis) || "Keine Verbindung.", false);
  return akteLaden(nr);
}
async function akteZuordnenForm(did) {
  const [o, k] = await Promise.all([jget("/api/crm/akte/offen"), jget("/api/crm/kunden")]);
  const m = ((o && o.mails) || []).find(x => x.id === did); if (!m) return openModal("Mail zuordnen", emptyRow("Diese Mail ist schon zugeordnet."));
  const firmen = ((k && k.firmen) || []).filter(f => f.aktiv !== false);
  openModal("Mail zuordnen", `<div class="v2-form"><div class="v2-kv"><span>Betreff</span><b><a href="/api/crm/akte/${encodeURIComponent(did)}/datei" target="_blank" rel="noopener">${esc(m.titel)}</a></b></div>
    <div class="v2-kv"><span>Von</span><b>${esc(m.mail_von || "?")}</b></div>${m.notiz ? `<div class="v2-kv"><span>Deine Notiz</span><b>${esc(m.notiz)}</b></div>` : ""}
    <label class="v2-feld"><small>Firma</small><select id="az-firma">${firmen.map(f => `<option value="${esc(f.nummer)}" ${(m.kandidaten || [])[0] === f.nummer ? "selected" : ""}>${esc(f.name)} (${esc(firmaNr(f))})</option>`).join("")}</select></label>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="akte-zuordnen-ok" data-id="${esc(did)}">Zuordnen</button><button class="v2-btn" data-act="akte-zuordnen-keine" data-id="${esc(did)}">Gehört zu keiner Firma</button></div></div>`);
}
async function kundeSpeichern(nr) {
  const firma = { ...formWerte("ke", FIRMA_FORM), aktiv: !!($("#ke-aktiv") || {}).checked };
  const r = await jpost("/api/crm/kunden/" + encodeURIComponent(nr), { firma });
  if (!r || !r.ok) return kundenMsg("ke-msg", (r && r.hinweis) || "Fehler.", false);
  const n = Object.keys(r.geaendert || {}).length;
  renderKunden(); return kundeDetail(nr, (n ? `${n} Feld(er) geändert.` : "Keine Änderung.") + (r.rollennummer ? ` Nummer für die neue Rolle: ${r.rollennummer}.` : ""));
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
let IST_KONTAKTE = {};
async function katalogLaden(neu) { if (!KATALOG || neu) { const d = await jget("/api/crm/katalog"); KATALOG = d && d.katalog; KAT_DARF = !!(d && d.darf_aendern); OMR = (d && d.omr) || OMR; IST_KONTAKTE = (d && d.ist_kontakte) || {}; } return KATALOG; }
// Etappe 16: Reichweiten-Formate = Kontakte × TKP / 1.000 + Produktion (auf 10 € gerundet); OMR-Werte als Vergleich
let OMR = { werte: {} };
const tkpPreis = (kontakte, tkpCent, prodCent) => Math.round((kontakte * tkpCent / 1000 + prodCent) / 1000) * 1000;
const omrText = (key) => { const w = (OMR.werte || {})[key]; return w ? `OMR ${w.min}–${w.max} € (${w.name})` : ""; };
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
function provText(pr) {      // wie core/angebote.provision_text
  if (!pr) return "";
  if (pr.art === "stueck") return `${cent2eur(pr.satz_cent)} je verkauftem Artikel` + (pr.stueck != null ? ` · abgerechnet: ${pr.stueck} × ${cent2eur(pr.satz_cent)}` : "");
  return `${pz(pr.prozent)} % vom vermittelten Umsatz` + (pr.basis_cent != null ? ` · abgerechnet: ${pz(pr.prozent)} % von ${cent2eur(pr.basis_cent)}` : "");
}
const posBetrag = (p) => p.provision && p.provision.stueck == null && p.provision.basis_cent == null ? "nach Abrechnung" : cent2eur(p.gesamt_cent);
function anProvBetrag(z) {   // Cent der Provision oder null (noch nicht abgerechnet)
  const art = $(".an-p-prov-art", z).value, w = zahl($(".an-p-prov-wert", z).value), abF = $(".an-p-prov-ab", z);
  if (!abF || abF.value.trim() === "") return null;
  const ab = zahl(abF.value);
  return art === "stueck" ? Math.round(ab * w * 100) : Math.round(ab * 100 * w / 100);
}
let AN_KONTEXT = "angebot";   // "rechnung": Provision abrechnen (Etappe 23)
function anProvFelder(pr) {
  const st = pr.art === "stueck";
  const wert = st ? cent2feld(pr.satz_cent ?? pr.wert_cent ?? 0) : pz(pr.prozent ?? 0);
  const ab = st ? (pr.stueck ?? "") : (pr.basis_cent != null ? cent2feld(pr.basis_cent) : "");
  return `<div class="an-p-prov"><small>Provision</small><select class="v2-inp an-p-prov-art"><option value="stueck" ${st ? "selected" : ""}>€ je verkauftem Artikel</option><option value="prozent" ${st ? "" : "selected"}>% vom Umsatz</option></select>
    <input class="v2-inp an-p-prov-wert" value="${esc(wert)}" inputmode="decimal" aria-label="Provisionssatz">
    ${AN_KONTEXT === "rechnung" ? `<small>Abrechnung:</small><input class="v2-inp an-p-prov-ab" value="${esc(String(ab))}" inputmode="decimal" placeholder="${st ? "verkaufte Stück" : "vermittelter Umsatz €"}" aria-label="Abrechnung">` : `<small class="v2-sub">wird nach der Kooperation abgerechnet</small>`}</div>`;
}
let RE_AUS_AUFTRAG = false;
function anPosOrig(p) {                                         // Rechnung: Bezugspreis, dessen Aenderung einen Grund braucht
  if (AN_KONTEXT !== "rechnung" || p.provision || p.einzelpreis_cent == null) return "";
  if (p.preis_vorher_cent != null) return String(p.preis_vorher_cent);
  return p.katalog_id || p.kontakte || RE_AUS_AUFTRAG ? String(p.einzelpreis_cent) : "";
}
const anGrundText = (orig, grund) => grund ? `<small class="an-p-grund">✎ Preis geändert${orig !== "" ? " (vorher " + cent2eur(Number(orig)) + ")" : ""} · Grund: ${esc(grund)}</small>` : "";
function anPosZeile(p = {}) {
  const orig = anPosOrig(p), tkpFest = p.kontakte && AN_KONTEXT !== "rechnung";   // Rechnung: Preis immer direkt aenderbar
  const tkp = p.kontakte ? `<div class="an-p-tkp"><small>TKP</small><input class="v2-inp an-p-tkpwert" type="number" min="${(p.tkp_min_cent || 100) / 100}" max="${(p.tkp_max_cent || 50000) / 100}" step="1" value="${esc(String((p.tkp_cent || p.tkp_min_cent) / 100))}" aria-label="TKP in Euro"><small>€ · Spanne ${esc(String((p.tkp_min_cent || p.tkp_cent) / 100))}–${esc(String((p.tkp_max_cent || p.tkp_cent) / 100))} €${p.omr ? " · " + esc(omrText(p.omr)) : ""} · ${esc(Number(p.kontakte).toLocaleString("de-DE"))} Kontakte + ${esc(cent2eur(p.produktion_cent || 0))} Produktion</small></div>` : "";
  const prov = p.provision ? anProvFelder(p.provision) : "";
  return `<div class="v2-an-pos${p.provision ? " v2-an-prov" : ""}" data-prov="${p.provision ? "1" : ""}" data-orig="${esc(orig)}" data-grund="${esc(p.preis_grund || "")}" data-katalog="${esc(p.katalog_id || "")}" data-gruppe="${esc(p.gruppe || "")}" data-farbe="${esc(p.gruppe_farbe || "")}" data-kontakte="${esc(String(p.kontakte || ""))}" data-prod="${esc(String(p.produktion_cent || 0))}" data-tmin="${esc(String(p.tkp_min_cent || ""))}" data-tmax="${esc(String(p.tkp_max_cent || ""))}" data-omr="${esc(p.omr || "")}">
    <div class="v2-an-text"><input class="v2-inp an-p-beschreibung" value="${esc(p.beschreibung || "")}" placeholder="Leistung">
      <input class="v2-inp an-p-detail" value="${esc(p.detail || "")}" placeholder="Detail (Reichweite, Hinweis) – optional">${tkp}${prov}<span class="an-p-grund-box">${anGrundText(orig, p.preis_grund)}</span></div>
    <input class="v2-inp an-p-menge" value="${esc(p.menge != null ? String(p.menge).replace(".", ",") : "1")}" placeholder="Menge" inputmode="decimal" aria-label="Menge">
    <input class="v2-inp an-p-einheit" value="${esc(p.einheit || "")}" placeholder="Einheit" aria-label="Einheit">
    <input class="v2-inp an-p-preis" value="${p.einzelpreis_cent != null ? cent2feld(p.einzelpreis_cent) : ""}" placeholder="Einzelpreis €" inputmode="decimal" aria-label="Einzelpreis" ${tkpFest ? 'readonly title="folgt aus dem TKP"' : ""}>
    <span class="an-p-gesamt">–</span>
    <button class="v2-btn v2-an-weg" data-act="an-pos-weg" title="Position löschen" aria-label="Position löschen">🗑</button></div>`;
}
document.addEventListener("change", (e) => {                // Rechnung: Preisaenderung gegen den Bezugspreis -> Grund abfragen
  const pr = e.target; if (!(pr instanceof HTMLInputElement) || !pr.classList.contains("an-p-preis") || AN_KONTEXT !== "rechnung") return;
  const z = pr.closest(".v2-an-pos"); if (!z || !z.dataset.orig) return;
  const neu = Math.round(zahl(pr.value) * 100), orig = Number(z.dataset.orig);
  if (neu === orig) { z.dataset.grund = ""; $(".an-p-grund-box", z).innerHTML = ""; return; }
  if (z.dataset.grund) { $(".an-p-grund-box", z).innerHTML = anGrundText(z.dataset.orig, z.dataset.grund); return; }
  const grund = (prompt(`Preis von ${cent2eur(orig)} auf ${cent2eur(neu)} ändern – Grund? (wird an der Position vermerkt, nicht auf der Rechnung gedruckt)`, "") || "").trim();
  if (!grund) { pr.value = cent2feld(orig); anSumme(); return; }
  z.dataset.grund = grund; $(".an-p-grund-box", z).innerHTML = anGrundText(z.dataset.orig, grund);
  if (z.dataset.kontakte) { delete z.dataset.kontakte; const t = $(".an-p-tkp", z); if (t) t.remove(); }   // eigener Preis statt TKP
  anSumme();
});
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
// BELEG_EINE_EBENE: Formular als Baustein -- im Fenster (Neu anlegen) und in der Detailansicht (Entwurf / nur lesen)
async function belegFormDaten() {
  const [k] = await Promise.all([jget("/api/crm/kunden"), katalogLaden()]);
  AN_FIRMEN = ((k && k.firmen) || []).filter(f => f.aktiv);
}
let FORM_GEAENDERT = false;                                       // ungespeicherte Eingaben im Beleg-Formular
const belegAnsichtWahl = () => { try { return localStorage.getItem("luna-beleg-ansicht") === "vorschau" ? "vorschau" : "formular"; } catch { return "formular"; } };
function belegZweiAnsichten(formular, vorschau) {                 // Umschalter Formular | Vorschau (Belegblatt)
  const v = belegAnsichtWahl();
  return `<div class="v2-ansicht" data-ansicht="${v}"><div class="v2-ansicht-wahl" role="group" aria-label="Ansicht">
    <button class="${v === "formular" ? "on" : ""}" data-act="bl-ansicht" data-val="formular">✎ Formular</button><button class="${v === "vorschau" ? "on" : ""}" data-act="bl-ansicht" data-val="vorschau">📄 Vorschau</button></div>
    <div class="v2-ansicht-formular">${formular}</div><div class="v2-ansicht-vorschau">${vorschau}</div></div>`;
}
// Formular verdrahten. `sperre` = Grund -> nur lesen (keine Eingabe, keine Knoepfe); `summen` = Summen-Zeilen vom Server
async function belegFormularFertig(sperre, ap, summen) {
  const root = document.querySelector("#v2-modal .v2-an-editor"); if (!root) return;
  await anApListe(ap || "");
  if (sperre) {
    root.classList.add("gesperrt");
    root.querySelectorAll("input, select, textarea").forEach(e => { e.disabled = true; });
    root.querySelectorAll("button, .v2-an-kat, .v2-an-neu, #an-pos-leer").forEach(e => { e.hidden = true; });
    root.querySelectorAll("input:not([type=checkbox]):not([type=hidden]), textarea").forEach(e => {   // leere Felder ruhig darstellen
      if (e.value) return;
      if (e.classList.contains("an-p-detail")) e.hidden = true;
      else if (e.type === "date") { e.type = "text"; e.value = "–"; }
      else e.placeholder = "–"; });
    root.querySelectorAll(".v2-mods").forEach(m => {               // nur gewaehlte Zuschlaege zeigen
      m.querySelectorAll(".v2-modlbl").forEach(l => { const c = l.querySelector("input"); if (c && !c.checked) l.hidden = true; });
      if (![...m.querySelectorAll(".v2-modlbl")].some(l => !l.hidden)) { m.hidden = true; const t = m.previousElementSibling; if (t && t.tagName === "SMALL") t.hidden = true; } });
    root.insertAdjacentHTML("afterbegin", `<div class="v2-msg v2-gesperrt-hinweis">🔒 ${esc(sperre)}</div>`);
  } else {
    firmaSucheVerdrahten();
    root.addEventListener("input", () => { FORM_GEAENDERT = true; });
    root.addEventListener("input", anSumme); root.addEventListener("change", anSumme);
  }
  anSumme();
  const box = $("#an-summe-box");
  if (summen && box) box.innerHTML = `<table class="v2-table v2-summen-fest"><tbody>${summen}</tbody></table>`;
  if (sperre) { const l = $("#an-pos-leer"); if (l) l.hidden = true; }
  FORM_GEAENDERT = false;
}
function anFormHtml(a, { nummer = "" } = {}) {
  const b = a.bloecke || {};
  const fa = AN_FIRMEN.find(f => f.nummer === a.firma);
  const gewaehlt = new Set((a.zuschlaege || []).map(z => z.id));
  const zuListe = [...((KATALOG && KATALOG.zuschlaege) || []), ...(a.zuschlaege || []).filter(z => !((KATALOG && KATALOG.zuschlaege) || []).some(k => k.id === z.id))];
  const zuHtml = zuListe.map(z => { const alt = (a.zuschlaege || []).find(x => x.id === z.id); const pr = alt ? alt.prozent : z.prozent;
    return `<label class="v2-modlbl"><input type="checkbox" class="an-zu" value="${esc(z.id)}" data-name="${esc(z.name)}" data-prozent="${esc(String(pr))}" ${gewaehlt.has(z.id) ? "checked" : ""}> +${esc(pz(pr))} % ${esc(z.name)}</label>`; }).join("");
  const rmax = esc(String((KATALOG && KATALOG.rabatt_max) || 30));
  return `<div class="v2-form v2-an-editor">
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
        <div class="v2-an-zeile"><label class="v2-feld"><small>Präsentation (Canva-Link)</small><select id="an-praes">${[["de", "Deutsch"], ["en", "Englisch"], ["", "keine"]].map(([v, l]) => `<option value="${v}" ${(a.nummer ? ((a.praesentation || {}).sprache || "") : "de") === v ? "selected" : ""}>${l}</option>`).join("")}</select></label></div>
        <div class="v2-an-zeile"><label class="v2-feld"><small>Layout</small><select id="an-layout"><option value="hanserautisch" ${a.layout !== "standard" ? "selected" : ""}>Hanserautisch</option><option value="standard" ${a.layout === "standard" ? "selected" : ""}>Schlicht (DIN)</option></select></label>
          <label class="v2-modlbl"><input type="checkbox" id="an-zeige-kalk" ${b.zeige_kalkulation !== false ? "checked" : ""}> „So kalkulieren wir“</label>
          <label class="v2-modlbl"><input type="checkbox" id="an-zeige-kz" ${b.zeige_kennzahlen !== false ? "checked" : ""}> Kennzahlen</label>
          <label class="v2-modlbl"><input type="checkbox" id="an-tkp-zeigen" ${b.tkp_zeigen !== false ? "checked" : ""}> Rechnung Kontakte × TKP zeigen</label>
          <label class="v2-modlbl"><input type="checkbox" id="an-omr-zeigen" ${b.omr_zeigen ? "checked" : ""}> OMR-Vergleich mit Link zeigen</label></div>
      </div>
    </div>
    <h3>Positionen <small class="v2-sub">Preise ohne Umsatzsteuer (Kleinunternehmer § 19 UStG)</small></h3>
    <div class="v2-an-kat"><button class="v2-btn pri" data-act="an-pos-neu">+ Neue Position</button>
      <label class="v2-feld" style="margin-left:auto"><small>Community-Fit (TKP innerhalb der Spanne)</small><select id="an-fit" class="v2-inp"><option value="0">Standard – unterer TKP</option><option value="0.5">Gute Passung – Mitte</option><option value="1">Sehr gute Passung – oberer TKP</option></select></label></div>
    <div class="v2-an-pos v2-an-pos-kopf"><span>Leistung / Detail</span><span>Menge</span><span>Einheit</span><span>Einzelpreis</span><span>Gesamt</span><span></span></div>
    <div id="an-pos">${(a.positionen || []).map(anPosZeile).join("")}</div>
    <div id="an-pos-leer" class="v2-empty">Noch keine Position — „+ Neue Position“ antippen und das Produkt wählen.</div>
    <div class="v2-an-fuss">
      <div class="v2-form">
        ${zuHtml ? `<small class="v2-sub">Zuschläge (Prozent auf die Summe aller Formate)</small><div class="v2-mods" id="an-zu-box">${zuHtml}</div>` : ""}
        <label class="v2-feld"><small>Paketrabatt in % (0–${rmax}, nur gegen Laufzeit oder Volumen)</small><input id="an-rabatt" type="number" min="0" max="${rmax}" step="0.5" value="${esc(String(a.rabatt_prozent || 0))}"></label>
        ${anWareFelder(a.ware)}
        ${anZahlungFelder(a.zahlung)}
      </div>
      <div id="an-summe-box" class="v2-an-summen"></div>
    </div>
    <div class="v2-an-kopf">
      <label class="v2-feld"><small>Einleitung (leer = Standardtext)</small><textarea id="an-einleitung" rows="3" class="v2-inp">${esc(a.einleitung || "")}</textarea></label>
      <label class="v2-feld"><small>Schluss (nur schlichtes Layout; leer = Standardtext mit Gruß)</small><textarea id="an-schluss" rows="3" class="v2-inp">${esc(a.schluss || "")}</textarea></label>
    </div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="an-speichern" data-id="${esc(nummer || "")}">${nummer ? "Änderungen speichern" : "Anlegen (Nummer wird vergeben)"}</button><div id="an-msg" class="v2-msg"></div></div></div>`;
}
async function anEditor(nummer, firmaVorwahl, modus) {
  if (nummer) return anDetail(nummer);                            // Bearbeiten passiert im Beleg selbst
  AN_KONTEXT = "angebot";
  const alsAuftrag = modus === "auftrag";                         // Etappe 31: Auftrag ohne Angebot, gleicher Editor
  openModal(alsAuftrag ? "Neuer Auftrag" : "Neues Angebot", `<div class="v2-empty">Lade…</div>`, true);
  await belegFormDaten();
  if (!AN_FIRMEN.length) return openModal("Neues Angebot", emptyRow("Zuerst unter „🏢 Kunden“ eine Firma anlegen."), true);
  const a = { firma: firmaVorwahl || AN_FIRMEN[0].nummer, datum: heuteIso(), gueltig_bis: heuteIso(14), nachfassen_tage: 7, positionen: [], zuschlaege: [], rabatt_prozent: 0, layout: "hanserautisch" };
  openModal(alsAuftrag ? "Neuer Auftrag (ohne Angebot)" : "Neues Angebot", anFormHtml(a), true);
  await belegFormularFertig("", "");
  if (alsAuftrag) abEditorUmbauen();
}
async function anApListe(vorwahl) {
  const nr = ($("#an-firma") || {}).value; const sel = $("#an-ap"); if (!sel) return;
  if (!nr) { sel.innerHTML = `<option value="">— erst Firma wählen —</option>`; return; }
  const d = await jget("/api/crm/kunden/" + encodeURIComponent(nr));
  const aps = ((d && d.firma && d.firma.ansprechpartner_liste) || []).filter(x => x.aktiv || x.nummer === vorwahl);
  sel.innerHTML = `<option value="">— keiner —</option>` + aps.map(x => `<option value="${esc(x.nummer)}" ${x.nummer === vorwahl ? "selected" : ""}>${esc(x.nummer)} · ${esc([x.vorname, x.nachname].filter(Boolean).join(" "))}${x.mail ? " · " + esc(x.mail) : ""}</option>`).join("");
}
function katPosDaten(id) {                                    // Katalog-Artikel -> Positionsdaten (TKP nach Community-Fit)
  const [it, g] = katItem(id); if (!it) return null;
  const fit = ($("#an-fit") || {}).value || "0", tk = it.kontakte ? Math.round((it.tkp_min_cent + Number(fit) * (it.tkp_max_cent - it.tkp_min_cent)) / 100) * 100 : null;
  return ({ beschreibung: it.name, detail: [it.basis, it.hinweis].filter(Boolean).join(" · "), menge: 1, einheit: it.einheit, einzelpreis_cent: it.kontakte ? tkpPreis(it.kontakte, tk, it.produktion_cent || 0) : it.preis_cent, katalog_id: it.id, gruppe: g.name, gruppe_farbe: g.farbe,
    kontakte: it.kontakte, tkp_cent: tk, tkp_min_cent: it.tkp_min_cent, tkp_max_cent: it.tkp_max_cent, produktion_cent: it.produktion_cent, omr: it.omr,
    ...(it.provision_art ? { provision: it.provision_art === "stueck" ? { art: "stueck", satz_cent: it.provision_wert } : { art: "prozent", prozent: it.provision_wert }, einzelpreis_cent: 0 } : {}) });
}
function anProduktZeile() {                                   // neue Position: erst Produkt waehlen (Katalog oder frei)
  const opt = ((KATALOG && KATALOG.gruppen) || []).map(g => `<optgroup label="${esc(g.name)}">${g.items.filter(it => it.aktiv).map(it => `<option value="${esc(it.id)}">${esc(it.name)} — ${cent2eur(it.preis_cent)}${it.einheit ? " / " + esc(it.einheit) : ""}</option>`).join("")}</optgroup>`).join("");
  return `<div class="v2-an-pos v2-an-neu"><div class="v2-an-text"><select class="v2-inp an-p-produkt" aria-label="Produkt wählen"><option value="">Produkt wählen …</option>${opt}<option value="__frei">Freie Position (ohne Katalog)</option></select></div>
    <button class="v2-btn v2-an-weg" data-act="an-pos-weg" title="Position löschen" aria-label="Position löschen">🗑</button></div>`;
}
document.addEventListener("change", (e) => {
  const sel = e.target; if (!(sel instanceof HTMLSelectElement) || !sel.classList.contains("an-p-produkt") || !sel.value) return;
  const z = sel.closest(".v2-an-pos"), daten = sel.value === "__frei" ? {} : katPosDaten(sel.value); if (!z || !daten) return;
  z.insertAdjacentHTML("afterend", anPosZeile(daten)); const neu = z.nextElementSibling; z.remove();
  anSumme(); const f = neu && $(sel.value === "__frei" ? ".an-p-beschreibung" : ".an-p-menge", neu); if (f) f.focus();
});
function anPositionen() {
  return [...document.querySelectorAll("#an-pos .v2-an-pos:not(.v2-an-neu)")].map(z => ({ beschreibung: $(".an-p-beschreibung", z).value.trim(), detail: $(".an-p-detail", z).value.trim(), menge: $(".an-p-menge", z).value.trim(), einheit: $(".an-p-einheit", z).value.trim(), einzelpreis: $(".an-p-preis", z).value.trim(),
    katalog_id: z.dataset.katalog || "", gruppe: z.dataset.gruppe || "", gruppe_farbe: z.dataset.farbe || "",
    ...(z.dataset.kontakte ? { kontakte: Number(z.dataset.kontakte), tkp_cent: Math.round(zahl($(".an-p-tkpwert", z).value) * 100), produktion_cent: Number(z.dataset.prod || 0),
      tkp_min_cent: z.dataset.tmin, tkp_max_cent: z.dataset.tmax, omr: z.dataset.omr } : {}),
    ...(z.dataset.orig && !z.dataset.kontakte ? { preis_vorher_cent: Number(z.dataset.orig), ...(z.dataset.grund ? { preis_grund: z.dataset.grund } : {}) } : {}),
    ...(z.dataset.prov ? { menge: "1", einzelpreis: "0", provision: { art: $(".an-p-prov-art", z).value, wert: $(".an-p-prov-wert", z).value.trim(), ...($(".an-p-prov-ab", z) && $(".an-p-prov-ab", z).value.trim() !== "" ? { abrechnung: $(".an-p-prov-ab", z).value.trim() } : {}) } } : {}) })).filter(p => p.beschreibung || p.einzelpreis);
}
function anFitSetzen() {   // „Community-Fit“: TKP aller Reichweiten-Positionen innerhalb ihrer Spanne setzen
  const fit = Number(($("#an-fit") || {}).value || 0);
  document.querySelectorAll("#an-pos .v2-an-pos").forEach(z => { const i = $(".an-p-tkpwert", z); if (!i || !z.dataset.tmin) return; const lo = Number(z.dataset.tmin), hi = Number(z.dataset.tmax || z.dataset.tmin); i.value = String(Math.round((lo + fit * (hi - lo)) / 100)); });
  anSumme();
}
const anZuschlaege = () => [...document.querySelectorAll(".an-zu:checked")].map(e => ({ id: e.value, name: e.dataset.name, prozent: Number(e.dataset.prozent) }));
// Etappe 12: Barter -- Gegenleistung ganz oder teilweise in Ware (Angebot, Auftrag, Rechnung)
function anWareFelder(w) {
  const an = !!(w && w.wert_cent);
  return `<label class="v2-modlbl"><input type="checkbox" id="an-ware-an" ${an ? "checked" : ""}> 🎁 Gegenleistung (ganz oder teilweise) in Ware – Barter</label>
    <div id="an-ware-box" ${an ? "" : "hidden"}><label class="v2-feld"><small>Welche Ware? *</small><input id="an-ware-text" value="${esc((w && w.text) || "")}" placeholder="z. B. 2x Kamera-Rig XY"></label>
    <label class="v2-feld"><small>Warenwert in € (Preis laut Marke)</small><input id="an-ware-wert" inputmode="decimal" value="${an ? esc(cent2feld(w.wert_cent)) : ""}"></label>
    <button class="v2-btn sm" data-act="an-ware-alles">Ganzer Betrag in Ware</button></div>`;
}
// Etappe 18: Zahlungsbedingungen je Angebot -- Zahlungsziel, optional Vorkasse (Prozent oder Euro) mit Frist
function anZahlungFelder(z) {
  z = z || {}; const v = z.vorkasse || {};
  const wert = v.art === "prozent" ? pz(v.prozent) : v.art === "euro" ? cent2feld(v.cent) : "";
  return `<h4 style="margin:10px 0 2px">💶 Zahlungsbedingungen</h4>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Zahlungsziel der Rechnung (Tage; leer = aus Kundendaten, sonst 14)</small><input id="an-ziel" type="number" min="0" max="120" value="${esc(z.ziel_tage ?? "")}"></label>
      <label class="v2-feld"><small>Vorkasse</small><select id="an-vk-art"><option value="">keine</option><option value="prozent" ${v.art === "prozent" ? "selected" : ""}>in % des Auftrags</option><option value="euro" ${v.art === "euro" ? "selected" : ""}>fester Betrag in €</option></select></label></div>
    <div id="an-vk-box" ${v.art ? "" : "hidden"}><div class="v2-an-zeile"><label class="v2-feld"><small id="an-vk-lbl">${v.art === "euro" ? "Betrag in €" : "Prozent"}</small><input id="an-vk-wert" inputmode="decimal" value="${esc(wert)}" placeholder="${v.art === "euro" ? "z. B. 500" : "z. B. 50"}"></label>
      <label class="v2-feld"><small>fällig … Tage nach Auftragsbestätigung</small><input id="an-vk-tage" type="number" min="0" max="90" value="${esc(v.frist_datum ? "" : (v.frist_tage ?? 7))}"></label>
      <label class="v2-feld"><small>oder festes Datum</small><input id="an-vk-datum" type="date" value="${esc(v.frist_datum || "")}"></label></div>
      <small class="v2-sub">LUNA erinnert an die Vorkasse-Rechnung und legt einen Payment-Check in ihren Kalender.</small></div>
    <label class="v2-feld"><small>Zusatz zu den Zahlungsbedingungen (optional)</small><input id="an-zb-text" value="${esc(z.text || "")}" placeholder="z. B. Bitte Rechnungsnummer als Verwendungszweck angeben."></label>`;
}
function anZahlung() {
  const art = ($("#an-vk-art") || {}).value || "", datum = ($("#an-vk-datum") || {}).value || "";
  const vk = art ? { art, wert: ($("#an-vk-wert") || {}).value.trim(), ...(datum ? { frist_datum: datum } : { frist_tage: ($("#an-vk-tage") || {}).value }) } : null;
  return { ziel_tage: ($("#an-ziel") || {}).value, vorkasse: vk, text: ($("#an-zb-text") || {}).value.trim() };
}
function anVorkasseZeile(geldCent) {   // Vorschau „Vorkasse … · Rest …“ im Summenkasten
  const art = ($("#an-vk-art") || {}).value; const box = $("#an-vk-box"); if (box) box.hidden = !art;
  const lbl = $("#an-vk-lbl"); if (lbl) lbl.textContent = art === "euro" ? "Betrag in €" : "Prozent";
  if (!art || !(geldCent > 0)) return "";
  const w = zahl(($("#an-vk-wert") || {}).value);
  if (!isFinite(w) || w <= 0) return `<div class="v2-kv"><span>Vorkasse</span><b>Wert eingeben</b></div>`;
  const vk = Math.min(geldCent, art === "prozent" ? Math.round(geldCent * w / 100) : Math.round(w * 100));
  return `<div class="v2-kv"><span>Vorkasse${art === "prozent" ? " (" + esc(pz(w)) + " %)" : ""}</span><b>${cent2eur(vk)}</b></div><div class="v2-kv"><span>Rest mit der Rechnung</span><b>${cent2eur(geldCent - vk)}</b></div>`;
}
function zbKurz(z) {
  if (!z) return "—"; const v = z.vorkasse;
  return (v ? (v.art === "prozent" ? pz(v.prozent) + " %" : cent2eur(v.cent)) + " Vorkasse · " : "") + `Zahlungsziel ${z.ziel_tage ?? 14} Tage` + (z.text ? " · " + z.text : "");
}
const anWare = () => ($("#an-ware-an") || {}).checked ? { text: ($("#an-ware-text") || {}).value.trim(), wert: ($("#an-ware-wert") || {}).value.trim() } : {};
function anSumme(ev) {
  if (ev && ev.target && ev.target.id === "an-fit") return anFitSetzen();
  const box = $("#an-summe-box"); if (!box) return;
  document.querySelectorAll("#an-pos .v2-an-pos").forEach(z => { const i = $(".an-p-tkpwert", z); if (!i || !z.dataset.kontakte) return;
    if (ev && ev.target === $(".an-p-preis", z)) return;      // Rechnung: Preis wird gerade von Hand geaendert
    $(".an-p-preis", z).value = cent2feld(tkpPreis(Number(z.dataset.kontakte), Math.round(zahl(i.value) * 100), Number(z.dataset.prod || 0))); });
  document.querySelectorAll("#an-pos .v2-an-pos:not(.v2-an-neu)").forEach(z => { const pv = z.dataset.prov ? anProvBetrag(z) : undefined; const c = pv !== undefined ? pv : Math.round(zahl($(".an-p-menge", z).value) * zahl($(".an-p-preis", z).value) * 100); $(".an-p-gesamt", z).textContent = pv === null ? "nach Abrechnung" : isFinite(c) ? cent2eur(c) : "–"; });
  const leer = $("#an-pos-leer"); if (leer) leer.hidden = !!document.querySelector("#an-pos .v2-an-pos");
  const formate = anPositionen().filter(p => !p.provision).reduce((acc, p) => acc + Math.round(zahl(p.menge) * zahl(p.einzelpreis) * 100), 0);
  const provZ = [...document.querySelectorAll("#an-pos .v2-an-pos[data-prov='1']")].map(anProvBetrag);
  const prov = provZ.reduce((s, c) => s + (c || 0), 0), provOffen = provZ.some(c => c === null);
  if (!isFinite(formate)) { box.innerHTML = `<div class="v2-kv"><span>Summe</span><b>Eingabe prüfen</b></div>`; return; }
  const zu = anZuschlaege().map(z => [z.name, z.prozent, Math.round(formate * z.prozent / 100)]);
  const zwischen = formate + zu.reduce((s, z) => s + z[2], 0);
  const r = Number(($("#an-rabatt") || {}).value || 0), rb = Math.round(zwischen * r / 100);
  box.innerHTML = `<div class="v2-kv"><span>Summe Formate</span><b>${cent2eur(formate)}</b></div>` + zu.map(z => `<div class="v2-kv"><span>${esc(z[0])} (+${esc(pz(z[1]))} %)</span><b>${cent2eur(z[2])}</b></div>`).join("")
    + (r ? `<div class="v2-kv"><span>Paketrabatt (${esc(pz(r))} %)</span><b>−${cent2eur(rb)}</b></div>` : "")
    + (provZ.length ? `<div class="v2-kv"><span>Provision</span><b>${provOffen && !prov ? "nach Abrechnung" : cent2eur(prov)}</b></div>` : "")
    + `<div class="v2-kv"><span><b>Gesamtbetrag</b></span><b>${cent2eur(zwischen - rb + prov)}${provOffen ? " + Provision" : ""}</b></div>`;
  const wb = $("#an-ware-box"); if (wb) wb.hidden = !($("#an-ware-an") || {}).checked;
  const wc = ($("#an-ware-an") || {}).checked ? feld2cent(($("#an-ware-wert") || {}).value) : 0;
  if (wc) box.innerHTML += `<div class="v2-kv"><span>davon in Ware 🎁</span><b>${cent2eur(wc)}</b></div><div class="v2-kv"><span>in Geld zu zahlen</span><b style="${wc > zwischen - rb ? "color:var(--v2-red)" : ""}">${cent2eur(zwischen - rb - wc)}</b></div>`;
  if ($("#an-vk-art")) box.innerHTML += anVorkasseZeile(zwischen - rb - wc);
  box.innerHTML += anInternKalk(zwischen - rb);
}
function anInternKalk(netto) {   // Etappe 21: nur intern (nie im PDF) -- Kosten laut Katalog x Menge
  if (!KATALOG) return "";
  const items = Object.fromEntries(KATALOG.gruppen.flatMap(g => g.items).map(i => [i.id, i]));
  let kosten = 0, ohne = 0;
  anPositionen().filter(p => !p.provision).forEach(p => { const it = items[p.katalog_id]; const k = it ? Object.values(it.kosten || {}).reduce((s, c) => s + c, 0) : 0; if (k) kosten += Math.round(k * zahl(p.menge)); else ohne++; });
  if (!kosten) return "";
  const db = netto - kosten, marge = netto ? Math.round(db * 1000 / netto) / 10 : 0, unter = marge < (KATALOG.mindestmarge_prozent ?? 30);
  return `<div class="v2-an-intern"><small>🔒 Intern (nicht im PDF)</small><div class="v2-kv"><span>Kosten laut Katalog${ohne ? ` (${ohne} Pos. ohne Kosten)` : ""}</span><b>${cent2eur(kosten)}</b></div><div class="v2-kv"><span>Deckungsbeitrag</span><b>${cent2eur(db)}</b></div><div class="v2-kv"><span>Marge</span><b style="${unter ? "color:var(--v2-red)" : ""}">${esc(pz(marge))} %${unter ? " ⚠️ unter Mindestmarge" : ""}</b></div></div>`;
}
// Etappe 31: im Auftragsmodus Gueltigkeit/Nachfassen weg, Leistungszeitraum + Notiz dazu, Speichern legt den Auftrag an
function abEditorUmbauen() {
  ["#an-gueltig", "#an-nachfassen", "#an-datum"].forEach(sel => { const f = $(sel); const l = f && f.closest("label"); if (l) l.hidden = true; });
  const knopf = document.querySelector('[data-act="an-speichern"]'); if (!knopf) return;
  knopf.dataset.act = "ab-manuell-speichern"; knopf.textContent = "Auftrag anlegen (Nummer wird vergeben)";
  knopf.closest(".v2-card-actions").insertAdjacentHTML("beforebegin", `<h3>Auftrag</h3><div class="v2-form">
    <div class="v2-an-zeile"><label class="v2-feld"><small>Leistung von</small><input id="abm-von" type="date"></label><label class="v2-feld"><small>Leistung bis</small><input id="abm-bis" type="date"></label></div>
    <label class="v2-feld"><small>Notiz (intern)</small><textarea id="abm-notiz" rows="2" class="v2-inp"></textarea></label></div>`);
}
function anDaten() {
  return { firma: $("#an-firma").value, ansprechpartner: $("#an-ap").value, titel: $("#an-titel").value.trim(), datum: $("#an-datum").value, gueltig_bis: $("#an-gueltig").value,
    nachfassen_tage: $("#an-nachfassen").value, einleitung: $("#an-einleitung").value.trim(), schluss: $("#an-schluss").value.trim(), positionen: anPositionen(),
    zuschlaege: anZuschlaege(), rabatt_prozent: ($("#an-rabatt") || {}).value || 0, layout: $("#an-layout").value,
    zeige_kalkulation: $("#an-zeige-kalk").checked, zeige_kennzahlen: $("#an-zeige-kz").checked, ware: anWare(), zahlung: anZahlung(), praesentation: ($("#an-praes") || {}).value || "",
    tkp_zeigen: ($("#an-tkp-zeigen") || {}).checked !== false, omr_zeigen: !!($("#an-omr-zeigen") || {}).checked };
}
async function abManuellSpeichern() {
  if (!$("#an-firma").value) { $("#an-firma-suche").focus(); return kundenMsg("an-msg", "Bitte eine Firma aus den Vorschlägen auswählen.", false); }
  const r = await jpost("/api/crm/auftraege", { auftrag: anDaten(), leistung_von: $("#abm-von").value, leistung_bis: $("#abm-bis").value, notiz: $("#abm-notiz").value.trim() });
  if (!r || !r.ok) return kundenMsg("an-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  if (AKTIV === "angebote" || AKTIV === "auftraege") renderAngebote();
  return abDetail(r.nummer, `${r.nummer} angelegt — ohne Angebot. Auftragsbestätigung, Rechnung und Zeiterfassung wie gewohnt.`);
}
async function anSpeichern(nummer) {
  if (!$("#an-firma").value) { $("#an-firma-suche").focus(); return kundenMsg("an-msg", "Bitte eine Firma aus den Vorschlägen auswählen.", false); }
  const angebot = anDaten();
  const r = nummer ? await jpost("/api/crm/angebote/" + encodeURIComponent(nummer), { angebot }) : await jpost("/api/crm/angebote", { angebot });
  if (!r || !r.ok) return kundenMsg("an-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  const nr = nummer || r.nummer; if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote();
  return anDetail(nr, nummer ? (r.geaendert && r.geaendert.length ? "Gespeichert." : "Keine Änderung.") : `${nr} angelegt.`);
}

/* ---------- Detail ---------- */
async function anDetail(nr, meldung, fehler) {
  openModal(nr, `<div class="v2-empty">Lade…</div>`, true);
  const [d] = await Promise.all([jget("/api/crm/angebote/" + encodeURIComponent(nr)), belegFormDaten()]);
  const a = d && d.angebot; if (!a) return openModal(nr, emptyRow("Angebot nicht gefunden."), true);
  AN_KONTEXT = "angebot";
  if (!AN_FIRMEN.some(f => f.nummer === a.firma)) AN_FIRMEN.push({ nummer: a.firma, name: (d.firma || {}).name || a.firma });
  const ap = d.ansprechpartner, sm = a.summen || { formate_cent: a.summe_cent, zuschlaege: [], rabatt: null, gesamt_cent: a.summe_cent };
  const pos = a.positionen.map((p, i) => `<tr><td>${i + 1}</td><td><b>${esc(p.beschreibung)}</b>${p.detail ? `<br><small>${esc(p.detail)}</small>` : ""}${p.provision ? `<br><small>💶 ${esc(provText(p.provision))}</small>` : ""}</td><td style="text-align:right">${esc(String(p.menge).replace(".", ","))} ${esc(p.einheit || "")}</td><td style="text-align:right">${posBetrag(p)}</td></tr>`).join("");
  const fuss = (sm.zuschlaege.length || sm.rabatt ? `<tr><td></td><td>Summe Formate</td><td></td><td style="text-align:right">${cent2eur(sm.formate_cent)}</td></tr>` : "")
    + sm.zuschlaege.map(([n, p, c]) => `<tr><td></td><td>${esc(n)} (+${esc(pz(p))} %)</td><td></td><td style="text-align:right">${cent2eur(c)}</td></tr>`).join("")
    + (sm.rabatt ? `<tr><td></td><td>Paketrabatt (${esc(pz(sm.rabatt[0]))} %)</td><td></td><td style="text-align:right">−${cent2eur(sm.rabatt[1])}</td></tr>` : "")
    + `<tr><td></td><td><b>Gesamtbetrag</b></td><td></td><td style="text-align:right"><b>${cent2eur(sm.gesamt_cent)}</b></td></tr>`;
  const termine = (a.versendet_termine || []).map(t => `<div class="v2-list-row"><span>📅</span><div class="grow"><b>${esc(t.titel)}</b><small>${esc(new Date(t.datum).toLocaleDateString("de-DE"))}, 09:00</small></div></div>`).join("");
  const pdfs = (a.pdfs || []).map(p => `<div class="v2-list-row"><span>📎</span><div class="grow"><b>${esc(p.pfad.split("/").pop())}</b><small>${esc(zeit(p.ts))}${p.an ? " · Mail-Entwurf an " + esc(p.an) : ""}${p.inhalt === a.inhalt ? "" : " · älterer Stand"}</small></div></div>`).join("");
  let aktionen = `<a class="v2-btn" href="/api/crm/angebote/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📄 PDF ansehen</a><button class="v2-btn" data-act="bv-oeffnen" data-id="${esc(nr)}">🔗 Belegverfolgung</button>`;
  if (a.status === "entwurf") aktionen += `<button class="v2-btn pri" data-act="an-senden" data-id="${esc(nr)}">✉️ Senden …</button>
    <button class="v2-btn" data-act="an-versendet" data-id="${esc(nr)}" title="Nur wenn du das Angebot auf anderem Weg verschickt hast">✔ Anderweitig versendet</button>`;
  else aktionen += `<button class="v2-btn" data-act="an-senden" data-id="${esc(nr)}" data-val="erneut" title="Gleiches PDF erneut schicken, z. B. mit der Vorlage zum Nachfassen">✉️ Erneut senden / nachfassen …</button>`;
  if (a.auftrag) aktionen += `<button class="v2-btn ok" data-act="ab-detail" data-id="${esc(a.auftrag)}">📋 Auftrag ${esc(a.auftrag)}</button>`;
  else if (a.status === "angenommen") aktionen += `<button class="v2-btn pri" data-act="ab-neu" data-id="${esc(nr)}">📋 Auftrag anlegen</button>`;
  else if (a.status === "versendet") aktionen += `<button class="v2-btn pri" data-act="ab-neu" data-id="${esc(nr)}" data-val="annehmen">📋 Angenommen + Auftrag anlegen</button>`;
  if (a.status === "versendet") aktionen += `<button class="v2-btn ok" data-act="an-status" data-id="${esc(nr)}" data-val="angenommen">Angenommen</button><button class="v2-btn" data-act="an-status" data-id="${esc(nr)}" data-val="abgelehnt">Abgelehnt</button>`
    + ((a.versendet_termine || []).length < 2 ? `<button class="v2-btn" data-act="an-erinnerungen" data-id="${esc(nr)}" title="Fehlende Kalender-Erinnerungen anlegen">📅 Erinnerungen nachholen</button>` : "");
  if ((a.pdfs || []).length) aktionen += `<a class="v2-btn" href="/api/crm/angebote/${encodeURIComponent(nr)}/pdf?archiv=1" target="_blank" rel="noopener">📎 Abgelegtes PDF</a>`;
  const verlaufLbl = { auftrag_angelegt: "Auftrag angelegt", angebot_angelegt: "Angelegt", angebot_geaendert: "Geändert", angebot_pdf_abgelegt: "PDF abgelegt", angebot_status: "Status", angebot_erinnerungen: "Erinnerungen nachgeholt", angebot_antwort: "Antwort vom Kunden", angebot_erneut_gesendet: "Erneut gesendet" };
  const anzAntworten = (a.antworten || []).length;
  const verlauf = (a.verlauf || []).slice().reverse().map(v => {
    const kopf = `<b>${esc(verlaufLbl[v.typ] || v.typ)}${v.status ? ": " + esc((AN_STATUS[v.status] || [v.status])[0]) : ""}${v.auftrag ? " " + esc(v.auftrag) : ""}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")}${v.felder ? " · " + esc(v.felder.join(", ")) : ""}${v.an ? " · an " + esc(v.an) : ""}${v.grund ? " · " + esc(v.grund) : ""}</small>`;
    if (!v.mail_id) return `<div class="v2-list-row"><div class="grow">${kopf}</div></div>`;
    const titel = v.richtung === "ein" ? `💬 Antwort von ${esc(v.mail_von || "")}` : `✉️ Gesendet an ${esc(v.mail_an || "")}${v.betreff ? " · „" + esc(v.betreff) + "“" : ""}`;
    return `<details class="v2-mail" data-nr="${esc(nr)}" data-mid="${esc(v.mail_id)}"><summary><div class="grow"><b>${titel}</b><small>${esc(zeit(v.ts))}${v.vorschau ? " · " + esc(v.vorschau.slice(0, 90)) : ""}${v.status ? " · Status: " + esc((AN_STATUS[v.status] || [v.status])[0]) : ""}</small></div></summary><div class="v2-mail-inhalt">Lade Mail…</div></details>`;
  }).join("");
  const altTab = `<h3>Positionen</h3><table class="v2-table"><thead><tr><th>#</th><th>Leistung</th><th style="text-align:right">Menge</th><th style="text-align:right">Gesamt</th></tr></thead><tbody>${pos}</tbody><tfoot>${fuss}</tfoot></table>`;
  const status = `<div class="v2-kv"><span>Status</span>${anBadge(a.anzeige_status)}</div>
    <div class="v2-kv"><span>Mail an</span><b>${esc(d.mail_an || "— keine Adresse —")}</b></div>
    <div class="v2-kv"><span>Layout</span><b>${a.layout === "standard" ? "Schlicht (DIN)" : "Hanserautisch"}</b></div>
    ${a.ware_cent ? `<div class="v2-kv"><span>Gegenleistung 🎁</span><b>${cent2eur(a.ware_cent)} in Ware${a.geld_cent ? " + " + cent2eur(a.geld_cent) + " Geld" : " – Barter"}</b></div>` : ""}
    ${anzAntworten ? `<div class="v2-kv"><span>Antworten vom Kunden</span><b>💬 ${anzAntworten} (im Verlauf)</b></div>` : ""}
    ${d.firmendaten ? "" : `<div class="v2-msg err">Firmendaten fehlen auf der NAS — PDF nicht möglich.</div>`}`;
  const seite = blBox("Status", status) + `<section class="v2-bl-box" id="bv-mini"></section>` + blBox("Erinnerungen", termine)
    + blBox("Abgelegte PDFs", pdfs) + blBox(`Verlauf <small class="v2-sub">Mails zum Aufklappen</small>`, verlauf);
  openModal(`${nr} · ${d.firma.name || a.firma}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    ${belegAnsicht({ aktionen, haupt: `<div id="an-senden-box"></div>${belegZweiAnsichten(anFormHtml(a, { nummer: nr }), d.blatt ? belegBlatt(d.blatt) : altTab)}`, seite, unten: `<section class="v2-kz" data-tabteil="konzept"><h3 class="v2-kz-titel">🎬 Konzept</h3><div id="kz-box"><div class="v2-empty">Lade…</div></div></section>`,
      reiter: [["beleg", "📄 Beleg"], ["konzept", "🎬 Konzept"]] })}`, true);
  const stand = a.status === "versendet" ? `Versendet${a.versendet_am ? " am " + datumDe(a.versendet_am) : ""}`
    : `${(AN_STATUS[a.status] || [a.status])[0]}${a.versendet_am ? " (versendet am " + datumDe(a.versendet_am) + ")" : ""}`;
  await belegFormularFertig(a.status === "entwurf" ? "" : `${stand} – nur lesen. Nachfassen über „Erneut senden“.`,
    a.ansprechpartner, a.status === "entwurf" ? null : fuss);
  bvMini(nr); KZ.tab = "briefing"; konzeptLaden(nr);
}

/* ---------- Auftraege (Beauftragung, KUNDEN_FINANZEN Etappe 4) ---------- */
const AB_STATUS = { beauftragt: ["Beauftragt", "wartet"], erledigt: ["Geliefert", "ok"], storniert: ["Storniert", "err"], abgeschlossen: ["✓ Abgeschlossen", "ok"] };   // Etappe 30: erledigt = „Geliefert“
const abBadge = (st) => { const [l, c] = AB_STATUS[st] || [st, "neutral"]; return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
const datumDe = (d) => d ? new Date(d).toLocaleDateString("de-DE") : "";
async function renderAuftraege() {
  const d = await jget("/api/crm/auftraege") || {};
  const l = d.auftraege || [];
  const offen = l.filter(a => a.status === "beauftragt");
  const rows = l.map(a => `<tr class="klick" data-act="ab-detail" data-id="${esc(a.nummer)}"><td><b>${esc(a.nummer)}</b></td><td>${esc(a.firma_name || a.firma)}</td><td>${esc(a.titel || "")}</td><td>${a.angebot ? esc(a.angebot) : `<span class="v2-sub">direkt</span>`}</td><td>${esc([datumDe(a.leistung_von), datumDe(a.leistung_bis)].filter(Boolean).join(" – "))}</td><td style="text-align:right">${cent2eur(a.summe_cent)}</td><td>${abBadge(a.abgeschlossen ? "abgeschlossen" : a.status)}</td></tr>`).join("");
  const body = `${kpiTile("Offene Aufträge", String(offen.length), null, cent2eur(offen.reduce((x, a) => x + (a.summe_cent || 0), 0)))}${kpiTile("Geliefert", String(l.filter(a => a.status === "erledigt").length), null, "bereit für die Rechnung")}
    ${tile("Aufträge", rows ? `<table class="v2-table"><thead><tr><th>Nr.</th><th>Firma</th><th>Titel</th><th>Angebot</th><th>Leistung</th><th style="text-align:right">Summe</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>` : emptyRow("Noch kein Auftrag — entsteht aus einem angenommenen Angebot („📋 Auftrag anlegen“)."), "w12")}`;
  $("#v2-app").innerHTML = anKopf() + `<div class="v2-card-actions" style="margin:-6px 0 12px"><button class="v2-btn pri" data-act="ab-manuell">+ Neuer Auftrag (ohne Angebot)</button></div><div class="v2-grid">${body}</div>`;
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
  if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote();
  return abDetail(r.nummer, [`${r.nummer} angelegt.`, ...(r.hinweise || [])].join("\n"));
}
async function abDetail(nr, meldung, fehler) {
  openModal(nr, `<div class="v2-empty">Lade…</div>`, true);
  const [d] = await Promise.all([jget("/api/crm/auftraege/" + encodeURIComponent(nr)), belegFormDaten()]);
  const a = d && d.auftrag; if (!a) return openModal(nr, emptyRow("Auftrag nicht gefunden."), true);
  AN_KONTEXT = "angebot";
  if (!AN_FIRMEN.some(f => f.nummer === a.firma)) AN_FIRMEN.push({ nummer: a.firma, name: (d.firma || {}).name || a.firma });
  const ap = d.ansprechpartner, sm = a.summen;
  const pos = a.positionen.map((p, i) => `<tr><td>${i + 1}</td><td><b>${esc(p.beschreibung)}</b>${p.detail ? `<br><small>${esc(p.detail)}</small>` : ""}${p.provision ? `<br><small>💶 ${esc(provText(p.provision))}</small>` : ""}</td><td style="text-align:right">${esc(String(p.menge).replace(".", ","))} ${esc(p.einheit || "")}</td><td style="text-align:right">${posBetrag(p)}</td></tr>`).join("");
  const fuss = (sm.zuschlaege.length || sm.rabatt ? `<tr><td></td><td>Summe Formate</td><td></td><td style="text-align:right">${cent2eur(sm.formate_cent)}</td></tr>` : "")
    + sm.zuschlaege.map(([n, p, c]) => `<tr><td></td><td>${esc(n)} (+${esc(pz(p))} %)</td><td></td><td style="text-align:right">${cent2eur(c)}</td></tr>`).join("")
    + (sm.rabatt ? `<tr><td></td><td>Paketrabatt (${esc(pz(sm.rabatt[0]))} %)</td><td></td><td style="text-align:right">−${cent2eur(sm.rabatt[1])}</td></tr>` : "")
    + `<tr><td></td><td><b>Gesamtbetrag</b></td><td></td><td style="text-align:right"><b>${cent2eur(sm.gesamt_cent)}</b></td></tr>`;
  let aktionen = `<a class="v2-btn" href="/api/crm/auftraege/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📄 Auftragsbestätigung (PDF)</a><button class="v2-btn" data-act="bv-oeffnen" data-id="${esc(nr)}">🔗 Belegverfolgung</button>
    ${a.angebot ? `<button class="v2-btn" data-act="an-detail" data-id="${esc(a.angebot)}">↩ Angebot ${esc(a.angebot)}</button>` : ""}`;
  if (a.status !== "storniert") aktionen += `<button class="v2-btn pri" data-act="ab-senden" data-id="${esc(nr)}">✉️ Senden …</button>`;
  const reListe = d.rechnungen || [], vkDa = reListe.some(r => r.art === "anzahlung" && r.status !== "storniert");
  const schlussDa = reListe.some(r => (r.art || "rechnung") === "rechnung" && r.status !== "storniert");
  if (a.status !== "storniert" && darf("rechnungen") && a.vorkasse_cent && !vkDa && !schlussDa) aktionen += `<button class="v2-btn pri" data-act="ab-vorkasse" data-id="${esc(nr)}">💶 Vorkasse-Rechnung erstellen</button>`;
  if (a.status !== "storniert" && darf("rechnungen")) aktionen += `<button class="v2-btn ${a.vorkasse_cent && !vkDa ? "" : "pri"}" data-act="ab-rechnung" data-id="${esc(nr)}">🧾 ${vkDa ? "Schlussrechnung" : "Rechnung"} erstellen</button>`;
  if (a.status === "beauftragt") aktionen += `<button class="v2-btn ok" data-act="ab-geliefert-form" data-id="${esc(nr)}">📦 Als geliefert markieren …</button><button class="v2-btn" data-act="ab-status" data-id="${esc(nr)}" data-val="storniert">Stornieren</button>`;
  if (a.status === "erledigt") aktionen += `<button class="v2-btn" data-act="ab-wieder-offen" data-id="${esc(nr)}" title="Für eine Nachlieferung – danach ist wieder Zeit buchbar">↺ Wieder öffnen …</button>`;
  if ((a.pdfs || []).length) aktionen += `<a class="v2-btn" href="/api/crm/auftraege/${encodeURIComponent(nr)}/pdf?archiv=1" target="_blank" rel="noopener">📎 Abgelegtes PDF</a>`;
  const lbl = { auftrag_angelegt: "Angelegt", auftrag_geaendert: "Geändert", auftrag_pdf_abgelegt: "PDF abgelegt", auftrag_status: "Status" };
  const verlauf = (a.verlauf || []).slice().reverse().map(v => `<div class="v2-list-row"><div class="grow"><b>${esc(lbl[v.typ] || v.typ)}${v.status ? ": " + esc(v.status === "gesendet" ? "Gesendet an " + (v.mail_an || "") : (AB_STATUS[v.status] || [v.status])[0]) : ""}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")}${v.felder ? " · " + esc(v.felder.join(", ")) : ""}${v.grund ? " · " + esc(v.grund) : ""}</small></div></div>`).join("");
  const bearbeitbar = a.status === "beauftragt";
  const altTab = `<h3>Positionen</h3><table class="v2-table"><thead><tr><th>#</th><th>Leistung</th><th style="text-align:right">Menge</th><th style="text-align:right">Gesamt</th></tr></thead><tbody>${pos}</tbody><tfoot>${fuss}</tfoot></table>`;
  const status = `<div class="v2-kv"><span>Status</span>${abBadge(a.abgeschlossen ? "abgeschlossen" : a.status)}</div>
    ${a.status === "erledigt" && a.geliefert_am ? `<div class="v2-kv"><span>Geliefert am</span><b>📦 ${esc(datumDe(a.geliefert_am))}</b></div>` : ""}
    ${a.ware_cent ? `<div class="v2-kv"><span>Gegenleistung 🎁</span><b>${cent2eur(a.ware_cent)} in Ware${a.geld_cent ? " + " + cent2eur(a.geld_cent) + " Geld" : " – Barter"}</b></div>` : ""}
    ${a.vorkasse_cent ? `<div class="v2-kv"><span>Vorkasse</span><b>${cent2eur(a.vorkasse_cent)} bis ${esc(datumDe(a.vorkasse_faellig))}</b></div>` : ""}
    ${reListe.length ? `<div class="v2-kv"><span>Rechnungen</span><b>${reListe.map(r => `<a href="#" data-act="re-detail" data-id="${esc(r.nummer)}">${esc(r.status === "entwurf" ? "Entwurf" : r.nummer)}</a> ${esc(RE_ART[r.art] || "")} · ${esc((RE_STATUS[r.status] || [r.status])[0])}`).join("<br>")}</b></div>` : ""}
    ${a.gesendet_mail ? `<div class="v2-kv"><span>Bestätigung gesendet</span><b>✉️ ${esc(a.gesendet_mail.an)} · ${esc(zeit(a.gesendet_am))}</b></div>` : ""}`;
  const leistung = `<div class="v2-form">
      <div class="v2-an-zeile"><label class="v2-feld"><small>von</small><input id="abe-von" type="date" value="${esc(a.leistung_von || "")}" ${bearbeitbar ? "" : "disabled"}></label>
        <label class="v2-feld"><small>bis</small><input id="abe-bis" type="date" value="${esc(a.leistung_bis || "")}" ${bearbeitbar ? "" : "disabled"}></label></div>
      <label class="v2-feld"><small>Notiz (steht als Anmerkung auf der Bestätigung)</small><textarea id="abe-notiz" rows="2" class="v2-inp" ${bearbeitbar ? "" : "disabled"}>${esc(a.notiz || "")}</textarea></label>
      ${bearbeitbar ? `<button class="v2-btn" data-act="ab-speichern" data-id="${esc(nr)}">Speichern</button><div id="abe-msg" class="v2-msg"></div>` : ""}</div>`;
  const seite = blBox("Status", status) + `<section class="v2-bl-box" id="bv-mini"></section>` + blBox("Leistung &amp; Anmerkung", leistung)
    + (a.status !== "storniert" ? blBox("Lieferungen", `<div id="ab-lief-box"><div class="v2-empty">Lade…</div></div>`) : "") + blBox("Verlauf", verlauf);
  const intern = `<div class="v2-beleg-intern"><div class="v2-intern-kopf">🔒 Intern – nie auf dem Beleg</div>
    <div class="v2-intern-raster"><div data-tabteil="postings"><div id="ab-post-box"></div><div id="ab-kond-box"></div></div>
    ${darf("rechnungen") ? `<div data-tabteil="zeiten"><div id="ab-zeit-box"></div></div>` : ""}
    ${a.status !== "storniert" ? `<div data-tabteil="bericht"><div id="ab-bericht-box"></div></div>` : ""}</div></div>`;
  openModal(`${nr} · ${d.firma.name || a.firma}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    ${belegAnsicht({ aktionen, haupt: `<div id="ab-senden-box"></div>${belegZweiAnsichten(anFormHtml(a, { nummer: nr }), d.blatt ? belegBlatt(d.blatt) : altTab)}`, seite, unten: `<section class="v2-kz" data-tabteil="konzept"><h3 class="v2-kz-titel">🎬 Konzept</h3><div id="kz-box"><div class="v2-empty">Lade…</div></div></section>` + intern,
      reiter: [["beleg", "📄 Beleg"], ["konzept", "🎬 Konzept"], ["postings", "📣 Postings"], ...(darf("rechnungen") ? [["zeiten", "⏱ Zeiten"]] : []), ["bericht", "📝 Bericht"]] })}`, true);
  await belegFormularFertig("Auftragsbestätigung – die Positionen sind aus dem Angebot festgeschrieben. Leistungszeitraum und Anmerkung änderst du rechts.",
    a.ansprechpartner, fuss);
  ["#an-gueltig", "#an-nachfassen", "#an-praes", "#an-zeige-kalk", "#an-zeige-kz", "#an-tkp-zeigen", "#an-omr-zeigen", "#an-schluss"].forEach(sel => {   // nur Angebot
    const f = document.querySelector("#v2-modal .v2-an-editor " + sel); const l = f && f.closest("label"); if (l) l.hidden = true; });
  bvMini(nr); KZ.tab = "briefing"; konzeptLaden(nr);
  abZeitLaden(nr); abLieferungen(nr); abPostings(nr, a.status); abBericht(nr);
}
// PROJEKTBERICHT P1: Postings je Position (Menge) mit Veroeffentlichung, Kennzahlen als Zahlen und TKP-Vergleich;
// dazu die beim Anlegen festgeschriebenen Konditionen (Katalog-Aenderungen wirken nie zurueck)
const tsd = (n) => n == null ? "–" : Number(n).toLocaleString("de-DE");
const pzt = (v) => v == null ? "" : `${String(v).replace(".", ",")} %`;
let POST = null;
async function abPostings(nr, status) {
  const box = $("#ab-post-box"), kbox = $("#ab-kond-box"); if (!box) return;
  const d = await jget(`/api/crm/auftraege/${encodeURIComponent(nr)}/postings`); POST = d;
  if (!d) { box.innerHTML = ""; return; }
  const k = d.konditionen || { positionen: [] }, mitTkp = k.positionen.some(p => p.tkp_cent);
  if (kbox) kbox.innerHTML = `<div class="v2-kond"><h3>Vereinbarte Konditionen <small class="v2-sub">festgeschrieben am ${esc(datumDe(k.festgeschrieben_am))}${k.angebot ? " · aus " + esc(k.angebot) : ""}</small></h3>
    <div class="v2-tab-scroll"><table class="v2-table v2-kond-t"><thead><tr><th>#</th><th>Leistung</th>${mitTkp ? `<th class="num">Kontakte</th><th class="num">TKP</th><th class="num">Produktion</th>` : ""}<th class="num">Preis je Stück</th></tr></thead><tbody>
    ${k.positionen.map(p => `<tr><td data-l="#">${p.position}</td><td data-l="Leistung">${esc(p.beschreibung)}</td>${mitTkp ? (p.tkp_cent ? `<td class="num" data-l="Kontakte">${tsd(p.kontakte)}</td><td class="num" data-l="TKP">${cent2eur(p.tkp_cent)}</td><td class="num" data-l="Produktion">${cent2eur(p.produktion_cent)}</td>` : `<td class="num leer">–</td><td class="num leer">–</td><td class="num leer">–</td>`) : ""}<td class="num" data-l="Preis je Stück">${cent2eur(p.einzelpreis_cent)}</td></tr>`).join("")}
    </tbody></table></div><small class="v2-sub">Diese Werte gelten für diesen Auftrag, seine Rechnungen und den Bericht – spätere Änderungen im Katalog ändern hier nichts.</small></div>`;
  const ps = d.postings || [];
  if (!ps.length) { box.innerHTML = ""; return; }
  const vz = Object.fromEntries(((d.vergleich || {}).zeilen || []).map(z => [z.id, z])), s = (d.vergleich || {}).summe || {};
  const offen = status !== "storniert";
  const karten = ps.map(p => { const z = vz[p.id] || {}, kz = p.kennzahlen || {}, kf = p.kontakt_feld, lbl = Object.fromEntries((d.felder[p.format] || []));
    const stand = p.kennzahlen ? `<span class="v2-badge ok">📊 Kennzahlen da</span>` : p.kennzahl_faellig ? `<span class="v2-badge warn">📊 Kennzahlen fällig</span>` : p.datum ? `<span class="v2-badge neutral">📣 veröffentlicht</span>` : `<span class="v2-badge neutral">${p.geplant ? "🗓 geplant " + esc(datumDe(p.geplant)) : "noch nicht geplant"}</span>`;
    const zahlen = p.kennzahlen ? `<div class="v2-po-zahlen">${(d.felder[p.format] || []).filter(([f]) => kz[f] != null).map(([f, l]) => `<span${f === kf ? ' class="kf"' : ""}><small>${esc(l)}</small><b>${tsd(kz[f])}</b></span>`).join("")}</div>
      <div class="v2-po-vgl"><span><small>${esc(lbl[kf] || kf)} Plan → Ist</small><b>${tsd(p.plan.kontakte || null)} → ${tsd(kz[kf])}${z.erfuellung_pct != null ? ` (${pzt(z.erfuellung_pct)})` : ""}</b></span>
      ${z.gegenwert_cent != null ? `<span><small>Gegenwert Ist</small><b>${cent2eur(z.gegenwert_cent)}</b></span><span><small>Mehrleistung</small><b class="${z.mehrleistung_cent >= 0 ? "pos" : "neg"}">${z.mehrleistung_cent >= 0 ? "+" : "−"}${cent2eur(Math.abs(z.mehrleistung_cent))}</b></span>${z.tkp_eff_cent != null ? `<span><small>TKP effektiv</small><b>${cent2eur(z.tkp_eff_cent)} <small>statt ${cent2eur(p.plan.tkp_cent)}</small></b></span>` : ""}` : ""}</div>` : "";
    return `<div class="v2-po" id="po-${esc(p.id)}"><div class="v2-po-kopf"><b>${esc(p.titel)}</b><small>${esc(p.plattform)} · Pos. ${p.position}${p.plan.kontakte ? " · Plan " + tsd(p.plan.kontakte) + " " + esc(lbl[kf] || kf) : ""}</small>${stand}</div>
      ${p.datum ? `<div class="v2-sub">Veröffentlicht am ${esc(datumDe(p.datum))}${p.link ? ` · <a href="${esc(p.link)}" target="_blank" rel="noopener noreferrer">🔗 ansehen</a>` : ""}</div>` : ""}
      ${!p.datum && offen ? `<label class="v2-feld v2-po-plan"><small>🗓 Geplant für (Content-Plan)</small><input class="v2-inp" type="date" data-po-geplant="${esc(p.id)}" data-nr="${esc(nr)}" value="${esc(p.geplant || "")}"></label>` : ""}
      ${zahlen}
      ${p.kennzahlen_30 ? `<div class="v2-sub">📈 Nach 30 Tagen: ${esc(lbl[kf] || kf)} <b>${tsd(p.kennzahlen_30[kf])}</b>${kz[kf] ? ` (+${tsd(Math.max(0, p.kennzahlen_30[kf] - kz[kf]))} seit Tag 7)` : ""}</div>` : ""}
      ${(p.bilder || []).length ? `<div class="v2-po-bilder">${p.bilder.map((b, i) => `<a href="/api/crm/postings/${encodeURIComponent(p.id)}/bild/${i}" target="_blank" rel="noopener"><img src="/api/crm/postings/${encodeURIComponent(p.id)}/bild/${i}" alt="Screenshot ${i + 1}" loading="lazy"></a>`).join("")}</div>` : ""}
      ${offen ? `<div class="v2-po-akt"><button class="v2-btn sm" data-act="po-form-v" data-id="${esc(p.id)}" data-val="${esc(nr)}">📣 ${p.datum ? "Veröffentlichung ändern" : "Veröffentlicht …"}</button>${p.datum ? `<button class="v2-btn sm ${p.kennzahl_faellig ? "pri" : ""}" data-act="po-form-k" data-id="${esc(p.id)}" data-val="${esc(nr)}">📊 Kennzahlen ${p.kennzahlen ? "korrigieren" : "eintragen"} …</button>` : ""}${p.kennzahlen && p.format === "reel" ? `<button class="v2-btn sm" data-act="po-form-l" data-id="${esc(p.id)}" data-val="${esc(nr)}" title="Optional: zweiter Messpunkt nach 30 Tagen">📈 30 Tage …</button>` : ""}</div>` : ""}
      <div class="po-form"></div></div>`; }).join("");
  const summe = s.gemessen && s.preis_cent ? `<div class="v2-po-summe"><b>Summe (${s.gemessen} von ${s.anzahl} gemessen)</b>
    <span><small>Kontakte Plan → Ist</small><b>${tsd(s.kontakte_plan)} → ${tsd(s.kontakte_ist)}${s.erfuellung_pct != null ? ` (${pzt(s.erfuellung_pct)})` : ""}</b></span>
    <span><small>Preis</small><b>${cent2eur(s.preis_cent)}</b></span><span><small>Gegenwert Ist</small><b>${cent2eur(s.gegenwert_cent)}</b></span>
    <span><small>Mehrleistung</small><b class="${s.mehrleistung_cent >= 0 ? "pos" : "neg"}">${s.mehrleistung_cent >= 0 ? "+" : "−"}${cent2eur(Math.abs(s.mehrleistung_cent))}${s.mehrleistung_pct != null ? ` (${pzt(Math.abs(s.mehrleistung_pct))})` : ""}</b></span></div>` : "";
  box.innerHTML = `<h3>📣 Postings &amp; Kennzahlen</h3>${karten}${summe}`;
}
function poForm(pid, nr, art) {
  const p = ((POST && POST.postings) || []).find(x => x.id === pid), karte = $("#po-" + CSS.escape(pid)); if (!p || !karte) return;
  const f = karte.querySelector(".po-form");
  if (art === "v") f.innerHTML = `<div class="v2-form"><div class="v2-an-zeile"><label class="v2-feld"><small>Veröffentlicht am *</small><input class="po-datum" type="date" max="${heuteIso()}" value="${esc(p.datum || heuteIso())}"></label>
    <label class="v2-feld"><small>Plattform</small><select class="po-pl v2-inp">${POST.plattformen.map(x => `<option${x === p.plattform ? " selected" : ""}>${esc(x)}</option>`).join("")}</select></label></div>
    <label class="v2-feld"><small>Link zum Posting</small><input class="po-link v2-inp" inputmode="url" placeholder="https://…" value="${esc(p.link || "")}"></label>
    <button class="v2-btn pri" data-act="po-speichern-v" data-id="${esc(pid)}" data-val="${esc(nr)}">Speichern</button><div class="v2-msg po-msg"></div></div>`;
  else { const lang = art === "l", kz = (lang ? p.kennzahlen_30 : p.kennzahlen) || {};
    f.innerHTML = `<div class="v2-form">${lang ? `<div class="v2-sub">📈 Zweiter Messpunkt 30 Tage nach der Veröffentlichung (optional) – der Bericht rechnet mit den 7-Tage-Zahlen.</div>` : `<label class="v2-feld"><small>📷 Screenshot(s) der Statistik – LUNA liest die Zahlen aus (Gemini), du prüfst und speicherst</small><input class="po-bild" type="file" accept="image/*" multiple></label><div class="v2-sub po-bild-msg"></div>`}<div class="v2-po-felder">${(POST.felder[p.format] || []).map(([k, l]) => `<label class="v2-feld"><small>${esc(l)}${k === p.kontakt_feld ? " *" : ""}</small><input class="v2-inp" data-feld="${esc(k)}" inputmode="numeric" value="${kz[k] != null ? esc(String(kz[k])) : ""}"></label>`).join("")}</div>
    <small class="v2-sub">${esc((POST.felder[p.format].find(([k]) => k === p.kontakt_feld) || [])[1] || "")} zählt als Kontakt (Grundlage für den TKP-Vergleich).${p.kennzahlen ? " Eine Korrektur bleibt im Verlauf sichtbar." : ""}</small>
    <button class="v2-btn pri" data-act="${lang ? "po-speichern-l" : "po-speichern-k"}" data-id="${esc(pid)}" data-val="${esc(nr)}">${lang ? "30-Tage-Zahlen speichern" : "Kennzahlen speichern"}</button><div class="v2-msg po-msg"></div></div>`; }
  const pb = f.querySelector(".po-bild"); if (pb) pb.addEventListener("change", () => poBilder(pb, pid));
  f.querySelector("[data-feld], .po-datum")?.focus();
}
async function poBilder(el, pid) {
  const karte = $("#po-" + CSS.escape(pid)), msg = karte && karte.querySelector(".po-bild-msg"); if (!karte) return;
  const files = [...(el.files || [])]; if (!files.length) return;
  let vorschlag = {}, hinweis = "";
  for (const [i, f] of files.entries()) {
    if (msg) msg.textContent = `Lade ${i + 1}/${files.length} hoch und lese aus …`;
    try { const r = await fetch(`/api/crm/postings/${encodeURIComponent(pid)}/bild`, { method: "POST", body: f, headers: { "X-Dateiname": encodeURIComponent(f.name || "screenshot.jpg") } });
      const j = await r.json(); if (!r.ok || j.ok === false) { hinweis = j.hinweis || "Upload fehlgeschlagen."; break; }
      vorschlag = j.vorschlag || {}; hinweis = j.hinweis || ""; } catch (e) { hinweis = "Keine Verbindung."; break; }
  }
  for (const [k, v] of Object.entries(vorschlag)) { const inp = karte.querySelector(`[data-feld="${k}"]`); if (inp) { inp.value = String(v); inp.classList.add("v2-erkannt"); } }
  if (msg) msg.textContent = Object.keys(vorschlag).length ? `✅ ${Object.keys(vorschlag).length} Werte erkannt – bitte prüfen und speichern.` : hinweis;
}
async function poSpeichern(pid, nr, art) {
  const karte = $("#po-" + CSS.escape(pid)); if (!karte) return;
  const r = art === "v" ? await jpost(`/api/crm/postings/${encodeURIComponent(pid)}/veroeffentlicht`, { datum: karte.querySelector(".po-datum").value, link: karte.querySelector(".po-link").value.trim(), plattform: karte.querySelector(".po-pl").value })
    : await jpost(`/api/crm/postings/${encodeURIComponent(pid)}/kennzahlen`, { werte: Object.fromEntries([...karte.querySelectorAll("[data-feld]")].map(i => [i.dataset.feld, i.value.trim()])), messpunkt: art === "l" ? 30 : 7 });
  if (!r || r.ok === false) { const m = karte.querySelector(".po-msg"); m.className = "v2-msg err po-msg"; m.textContent = (r && r.hinweis) || "Keine Verbindung."; return; }
  const a = (await jget("/api/crm/auftraege/" + encodeURIComponent(nr)) || {}).auftrag || {};
  return abPostings(nr, a.status);
}
document.addEventListener("change", async (e) => {             // CONTENT_PLAN C2: geplantes Datum eines Kunden-Postings
  const inp = e.target.closest && e.target.closest("[data-po-geplant]"); if (!inp) return;
  inp.disabled = true; const r = await jpost(`/api/crm/postings/${encodeURIComponent(inp.dataset.poGeplant)}/geplant`, { datum: inp.value }); inp.disabled = false;
  if (!r || r.ok === false) { alert((r && r.hinweis) || "Keine Verbindung."); return; }
  const a = (await jget("/api/crm/auftraege/" + encodeURIComponent(inp.dataset.nr)) || {}).auftrag || {};
  abPostings(inp.dataset.nr, a.status);
});
// KONZEPT_MAPPE K1-K3: eine Mappe je Vorgang (Briefing, Ideen, Skripte, Shotlist & Dreh, Freigabe)
let KZ = { tab: "briefing", d: null, beleg: "" };
const KZ_TABS = [["briefing", "📋 Briefing"], ["ideen", "💡 Ideen"], ["skripte", "✍️ Skripte"], ["dreh", "🎬 Dreh"], ["freigabe", "✅ Freigabe"]];
const KZ_ST = { idee: ["Idee", "neutral"], ausgewaehlt: ["ausgewählt", "ok"], verworfen: ["verworfen", "err"], entwurf: ["Entwurf", "wartet"], fertig: ["fertig", "neutral"], freigegeben: ["freigegeben", "ok"], beim_kunden: ["beim Kunden", "wartet"], aenderung: ["Änderungswunsch", "err"] };
const kzBadge = (st) => { const [l, c] = KZ_ST[st] || [st, "neutral"]; return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
async function konzeptLaden(beleg, tab) {
  const box = $("#kz-box"); if (!box) return;
  if (beleg !== KZ.beleg) KZ.vid = null;                    // Videograf-Vorschlag gehoert zum Vorgang
  if (tab) KZ.tab = tab;
  const d = await jget(`/api/crm/konzept/${encodeURIComponent(beleg)}`);
  if (!d) { box.innerHTML = emptyRow("Konzept nicht verfügbar."); return; }
  KZ.d = d; KZ.beleg = beleg; konzeptZeichnen();
}
function konzeptZeichnen() {
  const box = $("#kz-box"); if (!box || !KZ.d) return;
  const { mappe: m, kontext: k, felder: F } = KZ.d, v = k.vorgang, ta = (id, wert, rows = 2, ph = "") => `<textarea id="${id}" class="v2-inp" rows="${rows}" placeholder="${esc(ph)}">${esc(wert || "")}</textarea>`;
  const kopf = `<div class="v2-kz-kopf"><span class="v2-sub">Vorgang <b>${esc(v)}</b>${k.auftrag && k.auftrag !== v ? " · Auftrag " + esc(k.auftrag) : ""} · Freigabe ${kzBadge(m.freigabe.status)}</span>
    <div class="v2-card-actions"><a class="v2-btn sm" href="/api/crm/konzept-pdf/${encodeURIComponent(v)}?art=kunde" target="_blank" rel="noopener">📄 Konzept-PDF</a><a class="v2-btn sm" href="/api/crm/konzept-pdf/${encodeURIComponent(v)}?art=dreh" target="_blank" rel="noopener">📄 Drehliste</a></div></div>
    <div class="v2-kz-tabs">${KZ_TABS.map(([t, n]) => `<button class="${t === KZ.tab ? "on" : ""}" data-act="kz-tab" data-val="${t}">${n}</button>`).join("")}</div>`;
  let inhalt = "";
  if (KZ.tab === "briefing") {
    const b = m.briefing || {};
    inhalt = `<div class="v2-form"><div class="v2-kz-raster">${F.briefing.map(([key, label]) => `<label class="v2-feld"><small>${esc(label)}</small>${ta("kzb-" + key, b[key], key === "notizen" ? 3 : 2, key === "pflicht" ? "z. B. „Werbung“, @marke, Rabattcode, Link in Bio" : "")}</label>`).join("")}</div>
      <button class="v2-btn pri" data-act="kz-briefing" data-id="${esc(v)}">Briefing speichern</button><div id="kz-msg" class="v2-msg"></div></div>`;
  } else if (KZ.tab === "ideen") {
    const bilder = (m.bilder || []).map((x, i) => ({ ...x, i }));
    const karte = (i) => `<div class="v2-kz-idee${i.status === "verworfen" ? " weg" : ""}"><div class="v2-kz-zeile"><b>${esc(i.titel || "")}</b>${kzBadge(i.status)}</div>
      ${i.beschreibung ? `<div class="v2-sub">${esc(i.beschreibung)}</div>` : ""}${i.format || i.ziel ? `<small class="v2-sub">${esc([i.format, i.ziel].filter(Boolean).join(" · "))}</small>` : ""}
      ${bilder.filter(x => x.idee === i.id).length ? `<div class="v2-kz-mood">${bilder.filter(x => x.idee === i.id).map(x => `<a href="/api/crm/konzept-bild/${encodeURIComponent(v)}/${x.i}" target="_blank" rel="noopener"><img src="/api/crm/konzept-bild/${encodeURIComponent(v)}/${x.i}" alt="" loading="lazy"></a>`).join("")}</div>` : ""}
      <div class="v2-card-actions">${["ausgewaehlt", "idee", "verworfen"].filter(st => st !== i.status).map(st => `<button class="v2-btn sm" data-act="kz-idee-status" data-id="${esc(i.id)}" data-val="${st}">${st === "ausgewaehlt" ? "✓ auswählen" : st === "verworfen" ? "✕ verwerfen" : "↺ zurück"}</button>`).join("")}
        <label class="v2-btn sm v2-kz-upload">🖼 Bild<input type="file" accept="image/*" multiple hidden data-kz-bild="${esc(i.id)}"></label>
        ${i.status !== "verworfen" ? `<button class="v2-btn sm" data-act="kz-vid" data-id="${esc(i.id)}" data-val="idee">🎥 Videograf</button>` : ""}</div></div>`;
    const ideen = Object.values(m.ideen || {}).sort((a, b) => (a.status === "verworfen") - (b.status === "verworfen") || String(a.angelegt).localeCompare(String(b.angelegt)));
    inhalt = `${ideen.length ? `<div class="v2-kz-liste">${ideen.map(karte).join("")}</div>` : `<div class="v2-sub">Noch keine Ideen.</div>`}
      ${bilder.filter(x => !x.idee).length ? `<h4>Moodboard</h4><div class="v2-kz-mood">${bilder.filter(x => !x.idee).map(x => `<a href="/api/crm/konzept-bild/${encodeURIComponent(v)}/${x.i}" target="_blank" rel="noopener"><img src="/api/crm/konzept-bild/${encodeURIComponent(v)}/${x.i}" alt="" loading="lazy"></a>`).join("")}</div>` : ""}
      <details class="v2-pz" ${ideen.length ? "" : "open"}><summary><b>+ Idee hinzufügen</b></summary><div class="v2-form">
        <label class="v2-feld"><small>Titel *</small><input id="kzi-titel" class="v2-inp" maxlength="160"></label>
        <label class="v2-feld"><small>Beschreibung</small>${ta("kzi-beschr", "", 3)}</label>
        <div class="v2-an-zeile"><label class="v2-feld"><small>Format</small><input id="kzi-format" class="v2-inp" placeholder="z. B. Reel"></label><label class="v2-feld"><small>Für</small><input id="kzi-ziel" class="v2-inp" placeholder="z. B. Reel 1"></label></div>
        <button class="v2-btn pri" data-act="kz-idee" data-id="${esc(v)}">Idee speichern</button>
        <label class="v2-btn v2-kz-upload">🖼 Moodboard-Bilder hochladen<input type="file" accept="image/*" multiple hidden data-kz-bild=""></label><div id="kz-msg" class="v2-msg"></div></div></details>`;
  } else if (KZ.tab === "skripte") {
    const sk = m.skripte || {};
    inhalt = (k.slots || []).length ? k.slots.map(sl => { const x = sk[`S-${sl.position}-${sl.nr}`] || {}, id = `${sl.position}-${sl.nr}`;
      return `<details class="v2-kz-skript" ${x.hook || x.text ? "" : ""}><summary><b>${esc(sl.titel)}</b> ${x.status ? kzBadge(x.status) : `<span class="v2-sub">noch leer</span>`}${x.hook ? `<small class="v2-sub"> · ${esc(x.hook.slice(0, 60))}</small>` : ""}</summary>
        <div class="v2-form">${F.skript.map(([key, label]) => `<label class="v2-feld"><small>${esc(label)}</small>${key === "laenge" || key === "musik" ? `<input class="v2-inp" data-sk="${key}" value="${esc(x[key] || "")}">` : `<textarea class="v2-inp" rows="${key === "text" ? 5 : 2}" data-sk="${key}">${esc(x[key] || "")}</textarea>`}</label>`).join("")}
          <div class="v2-an-zeile"><label class="v2-feld"><small>Status</small><select class="v2-inp" data-sk="status">${["entwurf", "fertig", "freigegeben"].map(st => `<option value="${st}" ${(x.status || "entwurf") === st ? "selected" : ""}>${KZ_ST[st][0]}</option>`).join("")}</select></label></div>
          <div class="v2-card-actions"><button class="v2-btn pri" data-act="kz-skript" data-id="${esc(v)}" data-val="${id}">Skript speichern</button>
          ${x.hook || x.text ? `<button class="v2-btn" data-act="kz-vid" data-id="S-${id}" data-val="skript">🎥 Videograf-Vorschläge</button>` : ""}</div><div class="v2-msg" data-sk-msg="${id}"></div></div></details>`; }).join("")
      : `<div class="v2-sub">Keine Leistungen im Vorgang.</div>`;
  } else if (KZ.tab === "dreh") {
    const d = m.dreh || {}, sz = m.szenen_liste || [], fertig = sz.filter(x => x.erledigt).length;
    inhalt = kzVidPanel() + `<div class="v2-kz-zeile"><b>Shotlist</b><span class="v2-sub">${fertig}/${sz.length} erledigt</span>${sz.length ? `<button class="v2-btn pri sm" data-act="kz-drehmodus" data-id="${esc(v)}">🎬 Drehmodus</button>` : ""}</div>
      ${sz.map((x, i) => `<div class="v2-kz-szene${x.erledigt ? " ok" : ""}"><button class="v2-kz-haken" data-act="kz-erledigt" data-id="${esc(x.id)}" data-val="${x.erledigt ? "" : "1"}" aria-label="erledigt">${x.erledigt ? "✓" : ""}</button>
        <div class="grow"><b>${i + 1} · ${esc(x.titel || "")}${x.quelle ? ` <span title="${esc(x.quelle)}">🎥</span>` : ""}</b><small class="v2-sub">${esc([x.einstellung, x.ort, x.requisite, x.dauer].filter(Boolean).join(" · "))}${x.notiz ? " · " + esc(x.notiz) : ""}</small></div>
        <button class="v2-btn sm" data-act="kz-szene-weg" data-id="${esc(x.id)}" title="Szene entfernen">✕</button></div>`).join("") || `<div class="v2-sub">Noch keine Szenen.</div>`}
      <details class="v2-pz"><summary><b>+ Szene hinzufügen</b></summary><div class="v2-form"><div class="v2-kz-raster">${F.szene.map(([key, label]) => `<label class="v2-feld"><small>${esc(label)}${key === "titel" ? " *" : ""}</small><input class="v2-inp" data-sz="${key}"></label>`).join("")}</div>
        <button class="v2-btn pri" data-act="kz-szene" data-id="${esc(v)}">Szene speichern</button><div id="kz-msg" class="v2-msg"></div></div></details>
      <h4>Drehplan</h4><div class="v2-form"><div class="v2-kz-raster">${F.dreh.map(([key, label]) => `<label class="v2-feld"><small>${esc(label)}</small>${key === "mitbringen" ? ta("kzd-" + key, d[key], 2) : `<input id="kzd-${key}" class="v2-inp" type="${key === "datum" ? "date" : key === "zeit" ? "time" : "text"}" value="${esc(d[key] || "")}">`}</label>`).join("")}</div>
        <button class="v2-btn" data-act="kz-dreh" data-id="${esc(v)}">Drehplan speichern</button><div id="kz-msg2" class="v2-msg"></div></div>`;
  } else {
    const f = m.freigabe || { status: "entwurf", versionen: [] };
    inhalt = `<div class="v2-kv"><span>Status</span>${kzBadge(f.status)}${f[f.status + "_am"] ? ` <small class="v2-sub">seit ${esc(datumDe(f[f.status + "_am"]))}</small>` : ""}</div>
      ${f.notiz ? `<div class="v2-kv"><span>Notiz</span><b>${esc(f.notiz)}</b></div>` : ""}
      ${(f.versionen || []).map((x, i) => `<div class="v2-list-row"><span>📎</span><div class="grow"><b><a href="/api/crm/konzept-pdf/${encodeURIComponent(v)}?archiv=${i + 1}" target="_blank" rel="noopener">Konzept Version ${x.version}</a></b><small>gesendet an ${esc(x.an || "")} · ${esc(zeit(x.ts))} · in der Firmenakte</small></div></div>`).join("")}
      <div class="v2-card-actions" style="margin-top:8px"><button class="v2-btn pri" data-act="kz-senden-form" data-id="${esc(v)}">✉️ Zur Freigabe senden …</button>
        ${f.status !== "freigegeben" ? `<button class="v2-btn ok" data-act="kz-freigabe" data-id="${esc(v)}" data-val="freigegeben">✓ Kunde hat freigegeben</button>` : ""}
        <button class="v2-btn" data-act="kz-freigabe" data-id="${esc(v)}" data-val="aenderung">✎ Änderungswunsch …</button>
        ${f.status !== "entwurf" ? `<button class="v2-btn" data-act="kz-freigabe" data-id="${esc(v)}" data-val="entwurf">↺ wieder Entwurf</button>` : ""}</div>
      <div id="kz-msg" class="v2-msg"></div><div id="kz-senden-box"></div>`;
  }
  box.innerHTML = kopf + `<div class="v2-kz-inhalt">${inhalt}</div>`;
  box.querySelectorAll("[data-kz-bild]").forEach(inp => inp.addEventListener("change", () => kzBilder(inp)));
}
// VIDEOGRAF V3: Vorschlag des Videograf-Agenten (17) -- nur Anzeige, Szenen per Klick uebernehmen
function kzVidPanel() {
  const x = KZ.vid; if (!x) return "";
  if (x.laden) return `<div class="v2-kz-vid"><b>🎥 Videograf denkt nach …</b><small class="v2-sub">Vorschlag zu „${esc(x.titel || x.id)}“ – dauert meist 10–30 Sekunden.</small></div>`;
  if (x.fehler) return `<div class="v2-kz-vid err"><b>🎥 Kein Vorschlag</b><small class="v2-sub">${esc(x.fehler)}</small><div class="v2-card-actions"><button class="v2-btn sm" data-act="kz-vid-weg">Schließen</button></div></div>`;
  const rest = x.szenen.filter(z => !z.ok).length;
  return `<div class="v2-kz-vid"><div class="v2-kz-zeile"><b>🎥 Vorschlag des Videografen</b><span class="v2-sub">zu „${esc(x.titel || x.bezug)}“ · Vorschlag – nichts ist gespeichert</span></div>
    ${x.szenen.map((z, i) => `<div class="v2-kz-szene${z.ok ? " ok" : ""}"><div class="grow"><b>${i + 1} · ${esc(z.titel)}</b><small class="v2-sub">${esc([z.einstellung, z.ort, z.requisite, z.dauer].filter(Boolean).join(" · "))}${z.notiz ? " · " + esc(z.notiz) : ""}</small></div>
      ${z.ok ? `<span class="v2-badge ok">übernommen</span>` : `<button class="v2-btn sm" data-act="kz-vid-ueb" data-val="${i}">＋ übernehmen</button>`}</div>`).join("")}
    ${x.licht_ton ? `<div class="v2-kz-vid-txt"><b>Licht & Ton</b><p>${esc(x.licht_ton)}</p></div>` : ""}
    ${(x.equipment || []).length ? `<div class="v2-kz-vid-txt"><b>Equipment</b><p>${x.equipment.map(esc).join(" · ")}</p></div>` : ""}
    ${x.ablauf ? `<div class="v2-kz-vid-txt"><b>Ablauf</b><p>${esc(x.ablauf)}</p></div>` : ""}
    ${x.hinweise ? `<div class="v2-kz-vid-txt"><b>Hinweise</b><p>${esc(x.hinweise)}</p></div>` : ""}
    <div class="v2-card-actions">${rest ? `<button class="v2-btn pri sm" data-act="kz-vid-ueb" data-val="alle">＋ Alle ${rest} übernehmen</button>` : ""}<button class="v2-btn sm" data-act="kz-vid-weg">Vorschlag schließen</button></div>
    <div id="kz-vid-msg" class="v2-msg"></div></div>`;
}
async function kzVid(act, id, val) {
  const v = KZ.d && KZ.d.kontext.vorgang; if (!v) return;
  if (act === "kz-vid-weg") { KZ.vid = null; return konzeptZeichnen(); }
  if (act === "kz-vid") {
    const m = KZ.d.mappe, titel = val === "idee" ? ((m.ideen || {})[id] || {}).titel : ((KZ.d.kontext.slots || []).find(s => `S-${s.position}-${s.nr}` === id) || {}).titel;
    KZ.vid = { laden: true, id, titel }; KZ.tab = "dreh"; konzeptZeichnen();
    const r = await jpost(`/api/crm/konzept-videograf/${encodeURIComponent(v)}`, { art: val, id });
    if (!KZ.vid || KZ.vid.id !== id) return;
    KZ.vid = r && r.ok !== false ? { ...r, titel } : { fehler: (r && r.hinweis) || "Keine Verbindung." };
    return konzeptZeichnen();
  }
  if (act === "kz-vid-ueb" && KZ.vid && KZ.vid.szenen) {
    const idx = val === "alle" ? KZ.vid.szenen.map((z, i) => z.ok ? -1 : i).filter(i => i >= 0) : [Number(val)];
    for (const i of idx) { const z = KZ.vid.szenen[i]; if (!z || z.ok) continue;
      const { ok, ...felder } = z; const r = await jpost(`/api/crm/konzept/${encodeURIComponent(v)}/szene`, { ...felder, quelle: KZ.vid.quelle || "Videograf-Agent (Vorschlag)" });
      if (!r || r.ok === false) { kundenMsg("kz-vid-msg", (r && r.hinweis) || "Keine Verbindung.", false); break; }
      z.ok = true; }
    return konzeptLaden(KZ.beleg);
  }
}
async function kzBilder(inp) {
  const v = KZ.d.kontext.vorgang, files = [...(inp.files || [])];
  for (const f of files) {
    const r = await fetch(`/api/crm/konzept-bild/${encodeURIComponent(v)}?idee=${encodeURIComponent(inp.dataset.kzBild || "")}`, { method: "POST", body: f, headers: { "X-Dateiname": encodeURIComponent(f.name || "bild.jpg") } });
    const j = await r.json().catch(() => ({})); if (!r.ok || j.ok === false) { alert(j.hinweis || "Upload fehlgeschlagen."); break; }
  }
  return konzeptLaden(KZ.beleg);
}
async function kzAktion(act, id, val, el) {
  const v = KZ.d && KZ.d.kontext.vorgang, post = (teil, body) => jpost(`/api/crm/konzept/${encodeURIComponent(v)}/${teil}`, body);
  let r;
  if (act === "kz-tab") { KZ.tab = val; return konzeptZeichnen(); }
  if (act === "kz-briefing") r = await post("briefing", { felder: Object.fromEntries(KZ.d.felder.briefing.map(([k]) => [k, ($("#kzb-" + k) || {}).value || ""])) });
  else if (act === "kz-idee") r = await post("idee", { titel: $("#kzi-titel").value.trim(), beschreibung: $("#kzi-beschr").value.trim(), format: $("#kzi-format").value.trim(), ziel: $("#kzi-ziel").value.trim() });
  else if (act === "kz-idee-status") r = await post("idee", { id, status: val });
  else if (act === "kz-skript") { const [pos, nr] = val.split("-"); const box = el.closest(".v2-form");
    r = await post("skript", { position: Number(pos), nr: Number(nr), ...Object.fromEntries([...box.querySelectorAll("[data-sk]")].map(i => [i.dataset.sk, i.value])) });
    if (!r || r.ok === false) { const m = box.querySelector("[data-sk-msg]"); if (m) { m.className = "v2-msg err"; m.textContent = (r && r.hinweis) || "Fehler."; } return; } }
  else if (act === "kz-szene") r = await post("szene", Object.fromEntries([...document.querySelectorAll("#kz-box [data-sz]")].map(i => [i.dataset.sz, i.value.trim()])));
  else if (act === "kz-erledigt") r = await post("erledigt", { id, erledigt: !!val });
  else if (act === "kz-szene-weg") { if (!confirm("Szene entfernen?")) return; r = await post("entfernen", { id }); }
  else if (act === "kz-dreh") r = await post("dreh", { felder: Object.fromEntries(KZ.d.felder.dreh.map(([k]) => [k, ($("#kzd-" + k) || {}).value || ""])) });
  else if (act === "kz-freigabe") { let notiz = "";
    if (val === "aenderung") { notiz = prompt("Was möchte der Kunde geändert haben?", "") || ""; if (!notiz) return; }
    r = await post("freigabe", { status: val, notiz }); }
  else if (act === "kz-senden-form") return kzSendenForm(v);
  else if (act === "kz-senden") return kzSenden(v);
  else if (act === "kz-drehmodus") return drehModus(KZ.beleg);
  if (!r || r.ok === false) return kundenMsg(act === "kz-dreh" ? "kz-msg2" : "kz-msg", (r && r.hinweis) || "Keine Verbindung.", false);
  const offen = act === "kz-skript" ? [...document.querySelectorAll("#kz-box details[open]")].map(x => x.querySelector("summary b").innerText) : [];
  await konzeptLaden(KZ.beleg);
  if (offen.length) document.querySelectorAll("#kz-box details").forEach(x => { if (offen.includes(x.querySelector("summary b").innerText)) x.open = true; });
}
async function kzSendenForm(v) {
  const box = $("#kz-senden-box"), d = await jget(`/api/crm/konzept-versand/${encodeURIComponent(v)}`); if (!box || !d) return;
  box.innerHTML = `<h4>Konzept zur Freigabe senden</h4><div class="v2-form"><div class="v2-kv"><span>Absender</span><b>${esc(d.absender)}</b></div>
    <label class="v2-feld"><small>An *</small><input id="kzs-an" class="v2-inp" type="email" value="${esc(d.an || "")}"></label>
    <label class="v2-feld"><small>Betreff *</small><input id="kzs-betreff" class="v2-inp" value="${esc(d.betreff)}"></label>
    <label class="v2-feld"><small>Text *</small><textarea id="kzs-text" class="v2-inp" rows="7">${esc(d.text)}</textarea></label>
    <div class="v2-kv"><span>Anhang</span><a href="/api/crm/konzept-pdf/${encodeURIComponent(v)}?art=kunde" target="_blank" rel="noopener">📎 ${esc(d.pdf)}</a></div>${mailBlock("konzept", v, d)}
    <button class="v2-btn pri" data-act="kz-senden" data-id="${esc(v)}" ${d.google ? "" : "disabled"}>✉️ Jetzt senden</button><div id="kzs-msg" class="v2-msg"></div></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function kzSenden(v) {
  const an = $("#kzs-an").value.trim(); if (!an.includes("@")) return kundenMsg("kzs-msg", "Bitte eine gültige Adresse.", false);
  if (!confirm(`Konzept jetzt an ${an} senden?`)) return;
  const r = await jpost(`/api/crm/konzept-versand/${encodeURIComponent(v)}`, { an, betreff: $("#kzs-betreff").value.trim(), text: $("#kzs-text").value.trim(), bestaetigt: true });
  if (!r || !r.ok) return kundenMsg("kzs-msg", (r && r.hinweis) || "Senden fehlgeschlagen.", false);
  await konzeptLaden(KZ.beleg); kundenMsg("kz-msg", `Konzept Version ${r.version} an ${r.an} gesendet und in der Firmenakte abgelegt.`, true);
}
async function konzeptFenster(beleg, tab) {
  openModal("🎬 Konzept · " + beleg, `<div id="kz-box"><div class="v2-empty">Lade…</div></div>`, true);
  KZ.tab = tab || "briefing"; return konzeptLaden(beleg);
}
// Drehmodus: grosse Haken, Skript-Hook darunter -- fuer den Dreh auf dem iPhone
async function drehModus(beleg) {
  const d = await jget(`/api/crm/konzept/${encodeURIComponent(beleg)}`); if (!d) return;
  const m = d.mappe, v = d.kontext.vorgang, sz = m.szenen_liste || [], dr = m.dreh || {};
  openModal(`🎬 Dreh${dr.datum ? " " + datumDe(dr.datum) : ""} · ${v}`, `<div class="v2-dreh">
    <div class="v2-sub">${sz.filter(x => x.erledigt).length}/${sz.length} erledigt</div>
    ${sz.map((x, i) => `<button class="v2-dreh-zeile${x.erledigt ? " ok" : ""}" data-act="dreh-haken" data-id="${esc(x.id)}" data-val="${esc(beleg)}" data-ok="${x.erledigt ? "1" : ""}">
      <span class="v2-dreh-haken">${x.erledigt ? "✓" : ""}</span><span class="grow"><b>${i + 1} · ${esc(x.titel || "")}</b><small>${esc([x.einstellung, x.dauer, x.ort].filter(Boolean).join(" · "))}</small></span>${x.erledigt ? `<small>${esc(String(x.erledigt).slice(11, 16))}</small>` : ""}</button>`).join("")}
    ${dr.ort || dr.ansprechpartner || dr.mitbringen ? `<div class="v2-sub" style="margin-top:12px">${dr.ort ? "📍 " + esc(dr.ort) : ""}${dr.ansprechpartner ? " · " + esc(dr.ansprechpartner) : ""}${dr.telefon ? ` · <a href="tel:${esc(dr.telefon)}">${esc(dr.telefon)}</a>` : ""}${dr.mitbringen ? "<br>🎒 " + esc(dr.mitbringen) : ""}</div>` : ""}
    <div class="v2-card-actions" style="margin-top:12px"><button class="v2-btn" data-act="konzept" data-id="${esc(beleg)}" data-val="dreh">↩ zur Konzept-Mappe</button></div></div>`, true);
}
// VERTRAGSWERK V1/V2: Vorlagen-Bibliothek
const VT_ST = { entwurf: ["Entwurf – anwaltliche Prüfung erforderlich", "wartet"], geprueft: ["geprüft", "ok"], ausser_kraft: ["außer Kraft", "neutral"] };
const vtBadge = (st) => { const [l, c] = VT_ST[st] || [st || "—", "neutral"]; return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
const vtText = (t) => esc(t).replace(/\{([A-Za-zÄÖÜäöüß_]+)\}/g, '<span class="v2-ph">{$1}</span>');
RENDER.vertraege = async function () {
  const d = await jget("/api/crm/vertraege"); const l = (d && d.vorlagen) || [];
  const leer = l.every(x => !x.versionen);
  const pr = await jget("/api/crm/vertraege-pruefung") || {};
  $("#v2-app").innerHTML = secHead("📜 Vertragswerk", leer && darf("finanzen") ? `<button class="v2-btn pri" data-act="vt-entwuerfe">Erste Entwürfe laden</button>` : "")
    + `<div class="v2-msg warn" style="margin-bottom:12px">Die ersten Texte hat Claude Code entworfen – ungeprüft, keine Rechtsberatung; der CLO-Agent wird erst noch ausgebaut. An Kunden geht nur eine Version mit Status „geprüft“ – nach anwaltlicher Prüfung.</div>`
    + (pr.vorhanden ? `<div class="v2-bl-box" style="max-width:900px;margin-bottom:12px"><h4>⚖️ CLO-Prüfung vom ${esc(datumDe(pr.datum))}</h4><div class="v2-sub">Der CLO-Agent hat alle Vorlagen mit seinen Skills und Rechtsquellen geprüft (${esc(pr.modell || "")}). Je Paragraph Ampel, Fundstelle, Risiko und Fragen an die Anwältin – Details in der jeweiligen Vorlage.</div>
      <div class="v2-card-actions" style="margin-top:8px"><a class="v2-btn" href="/api/crm/vertraege-pruefung.pdf" target="_blank" rel="noopener">📄 Prüfbericht für die Anwältin (PDF)</a></div></div>` : "")
    + `<div class="v2-vt-liste">${l.map(x => `<button class="v2-vt-zeile" data-act="vt-detail" data-id="${esc(x.art)}"><span class="grow"><b>${esc(x.name)}</b><small class="v2-sub">${x.versionen ? `Version ${x.aktuell}${x.in_kraft ? ` · in Kraft: v${x.in_kraft}` : " · noch keine geprüfte Version"}` : "noch keine Version"}</small></span>${x.versionen ? vtBadge(x.status) : ""}</button>`).join("")}</div>`;
};
async function vtDetail(art, version, meldung) {
  const d = await jget(`/api/crm/vertraege/${encodeURIComponent(art)}`); const x = d && d.vorlage; if (!x) return;
  if (!x.versionen.length) return openModal(x.name, emptyRow("Noch keine Version – „Erste Entwürfe laden“ auf der Vertragswerk-Seite."), true);
  const pr = await jget("/api/crm/vertraege-pruefung") || {}, prv = (pr.vorlagen || []).find(v => v.art === art);
  const cloSchon = x.versionen.some(v => /CLO-Agent/.test(v.quelle || ""));
  const ver = x.versionen.find(v => v.version === Number(version)) || x.versionen[x.versionen.length - 1];
  const ceo = darf("finanzen");
  const kopf = `<div class="v2-card-actions" style="flex-wrap:wrap">${x.versionen.length > 1 ? `<select class="v2-inp" data-act-change="vt-version" data-id="${esc(art)}" style="width:auto">${x.versionen.map(v => `<option value="${v.version}" ${v.version === ver.version ? "selected" : ""}>Version ${v.version} · ${esc(VT_ST[v.status] ? VT_ST[v.status][0].split(" –")[0] : v.status)}</option>`).join("")}</select>` : ""}
    ${ceo ? `<button class="v2-btn" data-act="vt-neu" data-id="${esc(art)}" data-val="${ver.version}">✎ Neue Version</button>` : ""}
    ${ceo && ver.status !== "geprueft" ? `<button class="v2-btn ok" data-act="vt-pruef-form" data-id="${esc(art)}" data-val="${ver.version}">✓ Als geprüft markieren …</button>` : ""}
    ${ceo && ver.status === "geprueft" ? `<button class="v2-btn" data-act="vt-status" data-id="${esc(art)}" data-val="${ver.version}:ausser_kraft">Außer Kraft setzen</button>` : ""}
    ${x.versionen.length > 1 && ver.version > 1 ? `<button class="v2-btn" data-act="vt-vergleich" data-id="${esc(art)}" data-val="${ver.version - 1}:${ver.version}">⇄ Mit v${ver.version - 1} vergleichen</button>` : ""}</div>`;
  const seite = `<section class="v2-bl-box"><h4>Status</h4><div class="v2-kv"><span>Version ${ver.version}</span>${vtBadge(ver.status)}</div>
      ${ver.pruefer ? `<div class="v2-kv"><span>Geprüft</span><b>${esc(ver.pruefer)} · ${esc(datumDe(ver.datum))}</b></div>` : ""}
      <div class="v2-kv"><span>Quelle</span><b>${esc(ver.quelle || "")}</b></div><div class="v2-kv"><span>In Kraft</span><b>${x.in_kraft ? "Version " + x.in_kraft : "keine"}</b></div></section>
    ${prv ? `<section class="v2-bl-box"><h4>⚖️ CLO-Prüfung</h4><div class="v2-sub">${esc(prv.gesamt)}</div>
      <div class="v2-vt-ampeln">${["rot", "gelb", "gruen"].map(a => `<span class="v2-badge ${a === "rot" ? "err" : a === "gelb" ? "wartet" : "ok"}">${prv.paragraphen.filter(p => p.ampel === a).length} ${a === "gruen" ? "grün" : a}</span>`).join("")}${prv.fehlend.length ? `<span class="v2-badge neutral">${prv.fehlend.length} neu vorgeschlagen</span>` : ""}</div>
      ${prv.paragraphen.filter(p => p.ampel !== "gruen").map(p => `<details class="v2-vt-befund ${p.ampel}"><summary><b>${esc(p.titel)}</b></summary><small><b>Fundstelle:</b> ${esc(p.fundstelle)}<br><b>Risiko:</b> ${esc(p.risiko)}<br><b>Vorschlag:</b> ${esc(p.vorschlag)}${p.frage_anwaeltin ? `<br><b>Frage an die Anwältin:</b> ${esc(p.frage_anwaeltin)}` : ""}</small></details>`).join("")}
      ${prv.fehlend.map(f => `<details class="v2-vt-befund neu"><summary><b>Neu: ${esc(f.titel)}</b></summary><small>${esc(f.begruendung)}</small></details>`).join("")}
      <div class="v2-card-actions" style="margin-top:8px"><a class="v2-btn sm" href="/api/crm/vertraege-pruefung.pdf" target="_blank" rel="noopener">📄 Prüfbericht (PDF)</a>
        ${ceo && !cloSchon ? `<button class="v2-btn sm pri" data-act="vt-clo-version" data-id="${esc(art)}">Überarbeitung als neue Version übernehmen</button>` : cloSchon ? `<small class="v2-sub">Überarbeitung ist als Version angelegt.</small>` : ""}</div></section>` : ""}
    <section class="v2-bl-box"><h4>Platzhalter</h4><div class="v2-sub">${(ver.platzhalter || []).map(p => `<span class="v2-ph">{${esc(p)}}</span>`).join(" ") || "keine"}</div><div class="v2-sub" style="margin-top:6px">Werden beim Vertrag je Auftrag aus den Auftragsdaten gefüllt.</div></section>
    <section class="v2-bl-box"><h4>Verlauf</h4>${(ver.verlauf || []).slice().reverse().map(h => `<div class="v2-kv"><span>${esc(zeit(h.ts))}</span><b>${esc((VT_ST[h.status] || [h.status])[0].split(" –")[0])}${h.notiz ? " · " + esc(h.notiz) : ""}</b></div>`).join("")}</section>`;
  const blatt = `<article class="v2-blatt"><div class="bl-balken"><i></i><i></i></div>${ver.status === "entwurf" ? `<div class="bl-stempel ent">ENTWURF<small>anwaltl. Prüfung erforderlich</small></div>` : ""}
    <div class="bl-art" style="margin-bottom:10px">${esc(ver.titel)}</div>${ver.paragraphen.map(p => `<div class="v2-vt-par"><b>${vtText(p.titel)}</b><p>${vtText(p.text)}</p></div>`).join("")}</article>`;
  openModal(`📜 ${x.name}`, `${meldung ? `<div class="v2-msg ok">${esc(meldung)}</div>` : ""}${kopf}<div id="vt-box"></div>
    <div class="v2-beleg-layout" style="margin-top:10px"><div class="v2-beleg-haupt">${blatt}</div><aside class="v2-beleg-seite">${seite}</aside></div>`, true);
  const sel = document.querySelector("[data-act-change=vt-version]"); if (sel) sel.addEventListener("change", () => vtDetail(art, sel.value));
}
async function vtAktion(act, id, val) {
  if (act === "vt-entwuerfe") { const r = await jpost("/api/crm/vertraege/alle/entwuerfe", {}); if (!r || r.ok === false) return alert((r && r.hinweis) || "Fehler."); return RENDER.vertraege(); }
  if (act === "vt-detail") return vtDetail(id);
  if (act === "vt-clo-version") { if (!confirm("Die Überarbeitung des CLO als neue Version (Entwurf) anlegen? Version 1 bleibt erhalten.")) return;
    const r = await jpost(`/api/crm/vertraege/${encodeURIComponent(id)}/clo-version`, {});
    if (!r || r.ok === false) return alert((r && r.hinweis) || "Fehler."); return vtDetail(id, r.version, `Version ${r.version} (CLO-Überarbeitung) als Entwurf angelegt.`); }
  if (act === "vt-status") { const [v, st] = val.split(":"); if (!confirm("Version " + v + " außer Kraft setzen?")) return;
    const r = await jpost(`/api/crm/vertraege/${encodeURIComponent(id)}/status`, { version: Number(v), status: st }); return vtDetail(id, v, r && r.ok ? "Gespeichert." : (r && r.hinweis) || "Fehler."); }
  if (act === "vt-pruef-form") { $("#vt-box").innerHTML = `<section class="v2-bl-box" style="margin-top:10px"><h4>Anwaltliche Prüfung eintragen (Version ${esc(val)})</h4><div class="v2-form">
      <div class="v2-an-zeile"><label class="v2-feld"><small>Geprüft von *</small><input id="vtp-pruefer" class="v2-inp" placeholder="Kanzlei / Anwältin"></label><label class="v2-feld"><small>Datum *</small><input id="vtp-datum" class="v2-inp" type="date" value="${heuteIso()}"></label></div>
      <label class="v2-feld"><small>Notiz</small><input id="vtp-notiz" class="v2-inp" placeholder="z. B. Prüfschreiben liegt in der Firmenakte"></label>
      <button class="v2-btn ok" data-act="vt-pruefen" data-id="${esc(id)}" data-val="${esc(val)}">✓ Als geprüft speichern</button><div id="vtp-msg" class="v2-msg"></div></div></section>`; return; }
  if (act === "vt-pruefen") { const r = await jpost(`/api/crm/vertraege/${encodeURIComponent(id)}/status`, { version: Number(val), status: "geprueft", pruefer: $("#vtp-pruefer").value.trim(), datum: $("#vtp-datum").value, notiz: $("#vtp-notiz").value.trim() });
    if (!r || r.ok === false) return kundenMsg("vtp-msg", (r && r.hinweis) || "Fehler.", false); return vtDetail(id, val, "Als geprüft gespeichert – diese Version darf jetzt an Kunden."); }
  if (act === "vt-vergleich") { const [a, b] = val.split(":"); const d = await jget(`/api/crm/vertraege/${encodeURIComponent(id)}?a=${a}&b=${b}`);
    $("#vt-box").innerHTML = `<section class="v2-bl-box" style="margin-top:10px"><h4>Vergleich v${esc(a)} → v${esc(b)}</h4>${((d && d.vergleich) || []).filter(x => x.art !== "gleich").map(x => `<div class="v2-vt-diff ${x.art}"><b>${esc(x.titel)}</b> <span class="v2-badge ${x.art === "neu" ? "ok" : x.art === "entfernt" ? "err" : "wartet"}">${esc(x.art)}</span>${x.alt ? `<p class="alt">${esc(x.alt)}</p>` : ""}${x.neu ? `<p class="neu">${esc(x.neu)}</p>` : ""}</div>`).join("") || `<div class="v2-sub">Keine Unterschiede.</div>`}</section>`; return; }
  if (act === "vt-neu") { const d = await jget(`/api/crm/vertraege/${encodeURIComponent(id)}`); const ver = d.vorlage.versionen.find(v => v.version === Number(val));
    $("#vt-box").innerHTML = `<section class="v2-bl-box" style="margin-top:10px"><h4>Neue Version (auf Basis von v${esc(val)})</h4><div class="v2-form" id="vt-edit">
      <label class="v2-feld"><small>Titel</small><input id="vte-titel" class="v2-inp" value="${esc(ver.titel)}"></label>
      ${ver.paragraphen.map(p => vtParFeld(p)).join("")}
      <div class="v2-card-actions"><button class="v2-btn" data-act="vt-par-neu">+ Paragraph</button><button class="v2-btn pri" data-act="vt-speichern" data-id="${esc(id)}">Als neue Version speichern (Entwurf)</button></div><div id="vte-msg" class="v2-msg"></div></div></section>`;
    $("#vt-box").scrollIntoView({ behavior: "smooth" }); return; }
  if (act === "vt-par-neu") { $("#vt-edit .v2-card-actions").insertAdjacentHTML("beforebegin", vtParFeld({ titel: "", text: "" })); return; }
  if (act === "vt-par-weg") { const z = document.activeElement && document.activeElement.closest(".v2-vt-feld"); if (z) z.remove(); return; }
  if (act === "vt-speichern") { const par = [...document.querySelectorAll("#vt-edit .v2-vt-feld")].map(z => ({ titel: z.querySelector("input").value.trim(), text: z.querySelector("textarea").value.trim() }));
    const r = await jpost(`/api/crm/vertraege/${encodeURIComponent(id)}/version`, { titel: $("#vte-titel").value.trim(), paragraphen: par });
    if (!r || r.ok === false) return kundenMsg("vte-msg", (r && r.hinweis) || "Fehler.", false); return vtDetail(id, r.version, `Version ${r.version} als Entwurf gespeichert.`); }
}
const vtParFeld = (p) => `<div class="v2-vt-feld"><div class="v2-an-zeile"><input class="v2-inp" value="${esc(p.titel)}" placeholder="§ … Titel"><button class="v2-btn sm" data-act="vt-par-weg" title="Paragraph entfernen">✕</button></div><textarea class="v2-inp" rows="4">${esc(p.text)}</textarea></div>`;
// DIGITALER_BELEG D3: Mahnung als eigenes Belegblatt (Forderungsaufstellung wie im PDF)
async function maDetail(nr, meldung, fehler) {
  openModal(nr, `<div class="v2-empty">Lade…</div>`, true);
  const d = await jget(`/api/finanzen/mahnungen/${encodeURIComponent(nr)}`);
  const m = d && d.mahnung; if (!m) return openModal(nr, emptyRow("Mahnung nicht gefunden."), true);
  const r = d.rechnung || {};
  let aktionen = (m.pdf ? `<a class="v2-btn" href="/api/finanzen/mahnungen/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📄 ${m.alt ? "Original-PDF" : "PDF"}</a>` : "")
    + `<button class="v2-btn" data-act="bv-oeffnen" data-id="${esc(nr)}">🔗 Belegverfolgung</button><button class="v2-btn" data-act="re-detail" data-id="${esc(m.rechnung)}">↩ Rechnung ${esc(m.rechnung)}</button>`;
  if (!m.versendet_am) aktionen += `<button class="v2-btn pri" data-act="ma-senden" data-id="${esc(nr)}">✉️ Senden …</button>`;
  else if (!m.alt) aktionen += `<button class="v2-btn" data-act="ma-senden" data-id="${esc(nr)}" data-val="erneut" title="Gleiche Mahnung noch einmal schicken">✉️ Erneut senden …</button>`;
  const status = `<div class="v2-kv"><span>Mahnung</span><b>${m.versendet_am ? (m.alt ? "vor LUNA verschickt" : "✉️ gesendet " + esc(zeit(m.versendet_am)) + ((m.mail || {}).an ? " an " + esc(m.mail.an) : "")) : "noch nicht gesendet"}</b></div>
    ${(m.erneut || []).map(x => `<div class="v2-kv"><span>Erneut gesendet</span><b>${esc(zeit(x.ts))}${x.an ? " an " + esc(x.an) : ""}${x.kanal === "mail-programm" ? " (Mail-Programm)" : ""}</b></div>`).join("")}
    <div class="v2-kv"><span>Frist</span><b>${esc(datumDe(m.frist))}</b></div>
    <div class="v2-kv"><span>Rechnung</span><b><a href="#" data-act="re-detail" data-id="${esc(m.rechnung)}">${esc(m.rechnung)}</a> · ${esc((RE_STATUS[r.status] || [r.status || ""])[0])}</b></div>
    ${r.summe_cent != null ? `<div class="v2-kv"><span>Bezahlt / Rechnung</span><b>${cent2eur(r.bezahlt_cent || 0)} / ${cent2eur(r.summe_cent)}</b></div>` : ""}`;
  openModal(`${nr} · ${d.firma.name || ""}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    ${belegAnsicht({ aktionen, haupt: `<div id="re-aktion-box"></div>${d.blatt ? belegBlatt(d.blatt, { original: m.alt && m.pdf ? `/api/finanzen/mahnungen/${encodeURIComponent(nr)}/pdf` : "" }) : emptyRow("Ansicht nicht verfügbar.")}`,
      seite: blBox("Status", status) + `<section class="v2-bl-box" id="bv-mini"></section>` })}`, true);
  bvMini(nr);
}
// DIGITALER_BELEG D1-D3 (Variante A): jeder Beleg als Belegblatt -- Inhalte kommen vom Server (`blatt`, wie im PDF)
const BL_STEMPEL = { gelb: "offen", gruen: "bez", rot: "sto", grau: "ent", blau: "ges" };
function belegBlatt(b, extra = {}) {
  if (!b) return "";
  const eur = (c) => c == null ? "" : cent2eur(c);
  const posten = (b.gruppen || []).map(g => (g.name ? `<tr class="bl-gruppe"><td colspan="5">${esc(g.name)}</td></tr>` : "")
    + g.posten.map(p => `<tr><td class="bl-nr">${p.nr}</td><td class="bl-leistung"><b>${esc(p.beschreibung)}</b>${p.detail ? `<small>${esc(p.detail)}</small>` : ""}</td>
      <td class="bl-r bl-menge">${esc([p.menge ? String(p.menge).replace(".", ",") : "", p.einheit].filter(Boolean).join(" "))}<span class="bl-mal">${p.menge ? " × " : ""}${esc(p.einzel_text) || eur(p.einzel_cent)}</span></td>
      <td class="bl-r bl-einzel">${esc(p.einzel_text) || eur(p.einzel_cent)}</td><td class="bl-r bl-gesamt">${esc(p.gesamt_text) || eur(p.gesamt_cent)}</td></tr>`).join("")).join("");
  const st = b.stempel ? `<div class="bl-stempel ${BL_STEMPEL[b.stempel.art] || "ent"}">${esc(b.stempel.text)}${b.stempel.unter ? `<small>${esc(b.stempel.unter)}</small>` : ""}</div>` : "";
  const k = b.kalkulation;
  return `<article class="v2-blatt">
    <div class="bl-balken"><i></i><i></i></div>${st}
    <div class="bl-kopf"><div class="bl-anschrift"><div class="bl-absender">${esc(b.absender)}</div>${(b.empfaenger || []).map((z, i) => i ? `<div>${esc(z)}</div>` : `<div><b>${esc(z)}</b></div>`).join("")}</div>
      <div class="bl-meta"><div class="bl-art">${esc(b.art)}</div>${b.titel ? `<div class="bl-titel">${esc(b.titel)}</div>` : ""}
        <dl>${(b.infos || []).map(([l, w]) => `<dt>${esc(l)}</dt><dd>${esc(w)}</dd>`).join("")}</dl></div></div>
    ${b.anrede || b.einleitung ? `<div class="bl-text">${b.anrede ? `<b>${esc(b.anrede)}</b><br>` : ""}${esc(b.einleitung).replace(/\n/g, "<br>")}</div>` : ""}
    ${k ? `<div class="bl-kalk"><b>${esc(k.titel)}</b>${(k.absaetze || []).map(x => `<p>${esc(x)}</p>`).join("")}${k.beispiel ? `<p><i>${esc(k.beispiel)}</i></p>` : ""}</div>` : ""}
    <table class="bl-pos"><thead><tr><th class="bl-nr">#</th><th>Leistung</th><th class="bl-r">Menge</th><th class="bl-r">Einzelpreis</th><th class="bl-r">Gesamt</th></tr></thead><tbody>${posten}</tbody></table>
    <div class="bl-summen">${(b.summen || []).map(([n, c]) => `<div><span>${esc(n)}</span><span>${c < 0 ? "−" + eur(-c) : eur(c)}</span></div>`).join("")}
      <div class="bl-ges"><span>${esc(b.gesamt.text)}</span><span>${eur(b.gesamt.cent)}</span></div></div>
    ${(b.hinweise || []).length ? `<div class="bl-hinweis">${b.hinweise.map(h => `<div>${esc(h)}</div>`).join("")}</div>` : ""}
    ${(b.praesentation || {}).url ? `<a class="bl-praes" href="${esc(b.praesentation.url)}" target="_blank" rel="noopener">▶ ${esc(b.praesentation.text || "Präsentation")}<small>${esc(b.praesentation.url)}</small></a>` : ""}
    ${b.schluss ? `<div class="bl-text">${esc(b.schluss).replace(/\n/g, "<br>")}</div>` : ""}
    <div class="bl-fuss">${esc((b.fuss || []).join(" · "))}${b.anlage ? ` · 📎 Anlage: ${esc(b.anlage)}` : ""}${extra.original ? ` · <a href="${esc(extra.original)}" target="_blank" rel="noopener">📄 Original-PDF</a>` : ""}</div>
  </article>`;
}
// Variante A: Rechner Blatt links + Seitenleiste rechts; iPhone/iPad Blatt volle Breite, Aktionsleiste unten, Reiter beim Auftrag
function belegAnsicht({ aktionen, haupt, seite, unten = "", reiter = null }) {
  return `<div class="v2-beleg" data-tab="beleg">
    ${reiter ? `<div class="v2-beleg-reiter">${reiter.map(([k, t]) => `<button class="${k === "beleg" ? "on" : ""}" data-act="bl-reiter" data-val="${k}">${t}</button>`).join("")}</div>` : ""}
    <div class="v2-card-actions v2-beleg-aktionen">${aktionen}</div>
    <div class="v2-beleg-layout"><div class="v2-beleg-haupt" data-tabteil="beleg">${haupt}</div><aside class="v2-beleg-seite" data-tabteil="beleg">${seite}</aside></div>
    ${unten}</div>`;
}
const blBox = (titel, inhalt, id = "") => inhalt || id ? `<section class="v2-bl-box"${id ? ` id="${id}"` : ""}>${titel ? `<h4>${titel}</h4>` : ""}${inhalt || ""}</section>` : "";
async function bvMini(nr) {
  const box = $("#bv-mini"); if (!box) return;
  const d = await jget(`/api/crm/belege/${encodeURIComponent(nr)}/verfolgung`);
  const k = ((d && d.knoten) || []).filter(x => x.gross);
  if (k.length < 2) { box.remove(); return; }
  box.innerHTML = `<h4>🔗 Belegverfolgung</h4><div class="bl-mini">${k.map(x => x.id === d.start
      ? `<span class="akt">${esc(x.nummer || x.art_text)} · dieser Beleg</span>`
      : `<a href="#" data-act="${esc((x.oeffnen || {}).act || "bv-oeffnen")}" data-id="${esc((x.oeffnen || {}).id || x.id)}">${esc(x.nummer === "Entwurf" ? "Entwurf" : x.nummer)} · ${esc(x.art_text)}${x.status && ["storniert", "bezahlt", "storno"].includes(x.status) ? " · " + esc(x.status) : ""}</a>`).join("")}</div>
    <button class="v2-btn sm" data-act="bv-oeffnen" data-id="${esc(nr)}">Zeitstrahl öffnen</button>`;
}
// BELEGVERFOLGUNG B2: verbundene Belege als Zeitstrahl (Rechner waagerecht, iPad/iPhone senkrecht), Klick oeffnet
const BV_ICON = { angebot: "📝", auftrag: "📋", entwurf: "✎", vorkasse: "💶", rechnung: "🧾", schlussrechnung: "🧾", storno: "↩️", zahlung: "💰", mahnung: "⚠️", mahnverfahren: "⚖️", lieferung: "📦", bericht: "📊", dokument: "📎" };
const BV_EIN = { "beauftragt": "aus", "Vorkasse": "zu", "berechnet": "zu", "storniert durch": "storniert", "ersetzt durch": "ersetzt", "abgezogen in": "zieht ab:", "bezahlt": "für", "gemahnt": "zu", "Mahnverfahren": "zu", "geliefert": "zu", "Bericht gesendet": "zu", "Dokument": "zu" };
const BV_AUS = { "storniert durch": "storniert durch", "ersetzt durch": "ersetzt durch", "abgezogen in": "abgezogen in" };
async function belegVerfolgung(kennung) {
  openModal("🔗 Belegverfolgung · " + kennung, `<div class="v2-empty">Lade…</div>`, true);
  const d = await jget(`/api/crm/belege/${encodeURIComponent(kennung)}/verfolgung`);
  if (!d || !d.knoten) return openModal("🔗 Belegverfolgung · " + kennung, emptyRow("Belegverfolgung nicht verfügbar."), true);
  const nr = Object.fromEntries(d.knoten.map(k => [k.id, k.nummer]));
  const karte = (k, i) => {
    const ein = d.kanten.filter(e => e.nach === k.id).map(e => `${BV_EIN[e.text] || e.text} ${esc(nr[e.von] || e.von)}`);
    const aus = d.kanten.filter(e => e.von === k.id && BV_AUS[e.text]).map(e => `${BV_AUS[e.text]} ${esc(nr[e.nach] || e.nach)}`);
    const o = k.oeffnen || {}, akt = i === d.position;
    const inhalt = `<span class="bv-art">${BV_ICON[k.art] || "•"} ${esc(k.art_text)}</span><b>${esc(k.nummer)}</b>
      <small>${esc(datumDe(k.datum))}${k.betrag_cent != null ? " · " + cent2eur(k.betrag_cent) : ""}</small>
      ${k.titel ? `<small class="bv-titel">${esc(k.titel)}</small>` : ""}${k.status ? `<small class="bv-status">${esc({ storniert: "storniert", bezahlt: "bezahlt", offen: "offen", storno: "Storno", entwurf: "Entwurf", erledigt: "geliefert", beauftragt: "beauftragt", abgeschlossen: "✓ abgeschlossen", angenommen: "angenommen", versendet: "versendet", abgelehnt: "abgelehnt", gesendet: "gesendet" }[k.status] || k.status)}</small>` : ""}
      ${[...ein, ...aus].map(t => `<small class="bv-bez">${t}</small>`).join("")}`;
    const kl = `bv-knoten${k.gross ? "" : " klein"}${akt ? " aktuell" : ""}`;
    return akt ? `<div class="${kl}" id="bv-aktuell">${inhalt}<small class="bv-hier">● dieser Beleg</small></div>`
      : o.act ? `<button class="${kl}" data-act="${esc(o.act)}" data-id="${esc(o.id)}">${inhalt}</button>`
      : `<a class="${kl}" href="${esc(o.url || "#")}" target="_blank" rel="noopener">${inhalt}</a>`;
  };
  openModal("🔗 Belegverfolgung · " + kennung, `<div class="v2-sub" style="margin-bottom:8px">${d.vorher} früher · ${d.nachher} später – Klick öffnet den Beleg.</div>
    <div class="v2-bv"><div class="bv-spur">${d.knoten.map(karte).join("")}</div></div>`, true);
  const spur = $(".v2-bv .bv-spur"); if (spur) { bvLinie(spur); try { new ResizeObserver(() => bvLinie(spur)).observe(spur); } catch { } }
  requestAnimationFrame(() => { const a = $("#bv-aktuell"); if (a) a.scrollIntoView({ block: "center", inline: "center" }); });
}
// Spur am Rechner: Linie je Zeile, am Zeilenende ein Bogen nach rechts unten und zurueck zum Anfang der naechsten Zeile
function bvLinie(spur) {
  let svg = spur.querySelector(":scope > svg.bv-linie");
  if (innerWidth < 900) { if (svg) svg.remove(); return; }
  const karten = [...spur.querySelectorAll(":scope > .bv-knoten")]; if (!karten.length) return;
  const zeilen = [];
  karten.forEach(k => { const t = k.offsetTop, z = zeilen.find(r => Math.abs(r.top - t) < 4);
    z ? z.k.push(k) : zeilen.push({ top: t, k: [k] }); });
  const W = spur.clientWidth, R = 14, xl = 8, xr = W - 8, mitte = k => k.offsetLeft + k.offsetWidth / 2;
  let d = "";
  zeilen.forEach((z, i) => {
    const y = z.top - 13, x1 = mitte(z.k[0]), x2 = mitte(z.k[z.k.length - 1]);
    d += i ? ` L ${x1} ${y}` : `M ${x1} ${y}`;
    d += ` L ${x2} ${y}`;
    const n = zeilen[i + 1]; if (!n) return;
    const unten = Math.max(...z.k.map(k => k.offsetTop + k.offsetHeight)), yn = n.top - 13, ym = (unten + yn) / 2;
    d += ` L ${xr - R} ${y} Q ${xr} ${y} ${xr} ${y + R} L ${xr} ${ym - R} Q ${xr} ${ym} ${xr - R} ${ym}`
      + ` L ${xl + R} ${ym} Q ${xl} ${ym} ${xl} ${ym + R} L ${xl} ${yn - R} Q ${xl} ${yn} ${xl + R} ${yn}`;
  });
  if (!svg) { svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("class", "bv-linie"); svg.setAttribute("aria-hidden", "true"); spur.prepend(svg); }
  svg.setAttribute("width", W); svg.setAttribute("height", spur.scrollHeight); svg.innerHTML = `<path d="${d}"/>`;
}
// PROJEKTBERICHT P3: Bericht je Auftrag (Fazit-Vorschlag, Stunden/km per Haken, Versand nach Klick, Akte)
async function abBericht(nr) {
  const box = $("#ab-bericht-box"); if (!box) return;
  const d = await jget(`/api/crm/auftraege/${encodeURIComponent(nr)}/bericht`); if (!d) { box.innerHTML = ""; return; }
  const ab = d.abschluss || {}, e = d.entwurf || {}, b = d.berichte || [];
  const schritt = (ok, t) => `<span class="v2-ab-schritt${ok ? " ok" : ""}">${ok ? "✓" : "○"} ${esc(t)}</span>`;
  const gesendet = b.map((x, i) => `<div class="v2-list-row"><span>📎</span><div class="grow"><b><a href="/api/crm/auftraege/${encodeURIComponent(nr)}/bericht/pdf?archiv=${i + 1}" target="_blank" rel="noopener">Projektbericht${x.version > 1 ? " (Version " + x.version + ")" : ""}</a></b><small>gesendet an ${esc(x.an || "")} · ${esc(zeit(x.ts))} · liegt in der Firmenakte</small></div></div>`).join("");
  const offen = !d.abgeschlossen;
  box.innerHTML = `<h3>📝 Projektbericht &amp; Abschluss</h3>
    <div class="v2-ab-schritte">${schritt(ab.geliefert, "Geliefert")}${schritt(ab.bericht, ab.bericht === "entfaellt" ? "Kein Bericht nötig" : "Bericht versendet")}${schritt(ab.bezahlt, "Rechnung bezahlt")}${d.abgeschlossen ? `<span class="v2-badge ok">✓ Abgeschlossen</span>` : ""}</div>
    ${d.entfaellt ? `<div class="v2-sub">Kein Bericht nötig: ${esc(d.entfaellt)}</div>` : ""}${gesendet}
    ${(d.daten.fehlen || []).length ? `<div class="v2-msg warn">Noch ohne Zahlen: ${esc(d.daten.fehlen.join(", "))}</div>` : ""}
    <details class="v2-pz" ${b.length || !offen ? "" : "open"}><summary><b>${b.length ? "Neue Version erstellen" : "Bericht erstellen"}</b> <small class="v2-sub">Vorschau prüfen, dann senden</small></summary>
    <div class="v2-form">
      <label class="v2-feld"><small>Fazit (LUNA schlägt es aus den Zahlen vor – anpassen)</small><textarea id="ber-fazit" class="v2-inp" rows="6" maxlength="3000">${esc(e.fazit != null && e.fazit !== "" ? e.fazit : d.fazit_vorschlag)}</textarea></label>
      ${d.zeiten ? `<div class="v2-ab-haken"><label><input type="checkbox" id="ber-std" ${e.stunden ? "checked" : ""}> Stunden im Bericht zeigen</label><label><input type="checkbox" id="ber-km" ${e.km ? "checked" : ""}> km zeigen</label></div>` : ""}
      <div class="v2-card-actions"><button class="v2-btn" data-act="ber-vorschau" data-id="${esc(nr)}">💾 Speichern &amp; 📄 Vorschau</button><button class="v2-btn pri" data-act="ber-senden-form" data-id="${esc(nr)}">✉️ Senden …</button>${!b.length && !d.entfaellt ? `<button class="v2-btn" data-act="ber-entfaellt" data-id="${esc(nr)}" title="z. B. reiner Dreh ohne Postings">Kein Bericht nötig …</button>` : ""}</div>
      <div id="ber-msg" class="v2-msg"></div><div id="ber-senden-box"></div></div></details>
    ${b.length ? `<div class="v2-card-actions" style="margin-top:8px"><button class="v2-btn" data-act="ber-stimme" data-id="${esc(nr)}" title="Nur ein Entwurf in Gmail – du sendest selbst">💬 Kundenstimme erbitten (Entwurf) …</button></div><div id="ber-msg2" class="v2-msg"></div>` : ""}`;
}
async function berSpeichern(nr) {
  const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(nr)}/bericht`, { fazit: $("#ber-fazit").value, stunden: !!($("#ber-std") || {}).checked, km: !!($("#ber-km") || {}).checked });
  if (!r || r.ok === false) { kundenMsg("ber-msg", (r && r.hinweis) || "Keine Verbindung.", false); return false; }
  return true;
}
async function berSendenForm(nr) {
  if (!(await berSpeichern(nr))) return;
  const box = $("#ber-senden-box"), v = await jget(`/api/crm/auftraege/${encodeURIComponent(nr)}/bericht/versandvorschau`);
  if (!box || !v) return;
  box.innerHTML = `<h3>Bericht senden</h3>${(v.fehlen || []).length ? `<div class="v2-msg warn">Ohne Zahlen: ${esc(v.fehlen.join(", "))} – trotzdem senden?</div>` : ""}
    <div class="v2-kv"><span>Absender</span><b>${esc(v.absender)}</b></div>
    <label class="v2-feld"><small>An *</small><input id="ber-an" type="email" value="${esc(v.an || "")}"></label>
    <label class="v2-feld"><small>Betreff *</small><input id="ber-betreff" value="${esc(v.betreff)}"></label>
    <label class="v2-feld"><small>Text *</small><textarea id="ber-text" class="v2-inp" rows="8">${esc(v.text)}</textarea></label>
    <div class="v2-kv"><span>Anhang</span><a href="/api/crm/auftraege/${encodeURIComponent(nr)}/bericht/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>${mailBlock("bericht", nr, v)}
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="ber-senden" data-id="${esc(nr)}" ${sendSperre(v)}>✉️ Jetzt senden</button></div><div id="bers-msg" class="v2-msg"></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function berSenden(nr) {
  const an = $("#ber-an").value.trim();
  if (!an || !an.includes("@")) return kundenMsg("bers-msg", "Bitte eine gültige Empfänger-Adresse eintragen.", false);
  if (!confirm(`Projektbericht ${nr} jetzt an ${an} senden?`)) return;
  const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(nr)}/bericht/senden`, { an, betreff: $("#ber-betreff").value.trim(), text: $("#ber-text").value.trim(), bestaetigt: true });
  if (!r || !r.ok) return kundenMsg("bers-msg", (r && r.hinweis) || "Senden fehlgeschlagen.", false);
  glockeAktualisieren();
  return abDetail(nr, `Projektbericht an ${r.an} gesendet und in der Firmenakte abgelegt.`);
}
// Etappe 30: Lieferungen -- Dateien (in 8-MB-Stuecken, auch grosse Videos vom iPhone) und Links je Auftrag
function lfAnzeige(x, mitEntfernen) {
  const dateien = (x.dateien || []).map((f, i) => { const src = `/api/crm/lieferungen/${encodeURIComponent(x.id)}/datei/${i}`;
    const gr = f.groesse > 1048576 ? (f.groesse / 1048576).toFixed(1).replace(".", ",") + " MB" : Math.max(1, Math.round((f.groesse || 0) / 1024)) + " KB";
    return String(f.mime || "").startsWith("video/") ? `<div class="v2-lf-datei"><video src="${src}" controls playsinline preload="metadata"></video><small><a href="${src}" target="_blank" rel="noopener">${esc(f.name)}</a> · ${gr}</small></div>`
      : String(f.mime || "").startsWith("image/") ? `<div class="v2-lf-datei"><a href="${src}" target="_blank" rel="noopener"><img src="${src}" alt="${esc(f.name)}" loading="lazy"></a><small>${esc(f.name)} · ${gr}</small></div>`
      : `<div class="v2-lf-datei"><a href="${src}" target="_blank" rel="noopener">📄 ${esc(f.name)}</a><small>${gr}</small></div>`; }).join("");
  const links = (x.links || []).map(u => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">🔗 ${esc(u.replace(/^https?:\/\//, "").slice(0, 60))}</a>`).join("<br>");
  return `<div class="v2-lf"><div class="v2-lf-kopf"><b>📦 ${esc(x.titel)}</b><small>${esc(datumDe(x.datum))}${x.auftrag ? " · " + esc(x.auftrag) : ""}${x.notiz ? " · " + esc(x.notiz) : ""}</small>
    ${mitEntfernen ? `<button class="v2-btn sm" data-act="lf-entfernen" data-id="${esc(x.id)}" data-val="${esc(x.auftrag)}" title="Falsch angelegt? Entfernt die Lieferung samt Dateien">✕</button>` : ""}</div>
    ${links ? `<div class="v2-lf-links">${links}</div>` : ""}${dateien ? `<div class="v2-lf-dateien">${dateien}</div>` : ""}</div>`;
}
function lfFormular(nr, geliefert) {
  return `<div class="v2-form v2-lf-form">
    ${geliefert ? `<label class="v2-feld"><small>Geliefert am *</small><input id="lf-datum-st" type="date" value="${heuteIso()}"></label><small class="v2-sub">Optional gleich die Lieferung dazu – oder später unter „Lieferungen“.</small>` : ""}
    <label class="v2-feld"><small>Titel der Lieferung${geliefert ? "" : " *"}</small><input id="lf-titel" class="v2-inp" placeholder="z. B. Reel Herbstkampagne, finale Version"></label>
    <label class="v2-feld"><small>Links (je Zeile einer, z. B. Instagram-Post, Drive, WeTransfer)</small><textarea id="lf-links" rows="2" class="v2-inp" placeholder="https://… (Post, Drive, WeTransfer)"></textarea></label>
    <label class="v2-feld"><small>Dateien (Videos, Bilder, PDF, ZIP – auch mehrere, bis 4 GB je Datei)</small><input id="lf-dateien" type="file" multiple accept="video/*,image/*,.pdf,.zip"></label>
    <label class="v2-feld"><small>Notiz</small><input id="lf-notiz" class="v2-inp" maxlength="500"></label>
    <div id="lf-fortschritt" class="v2-sub"></div>
    <button class="v2-btn ${geliefert ? "ok" : "pri"}" data-act="${geliefert ? "ab-geliefert" : "lf-speichern"}" data-id="${esc(nr)}">${geliefert ? "📦 Als geliefert markieren" : "Lieferung speichern"}</button><div id="lf-msg" class="v2-msg"></div></div>`;
}
async function abLieferungen(nr) {
  const box = $("#ab-lief-box"); if (!box) return;
  const d = await jget(`/api/crm/auftraege/${encodeURIComponent(nr)}/lieferungen`);
  const l = (d && d.lieferungen) || [];
  box.innerHTML = (l.length ? l.map(x => lfAnzeige(x, true)).join("") : `<div class="v2-sub">Noch nichts geliefert. Hier legst du ab, was an den Kunden ging – Dateien und/oder Links.</div>`)
    + `<details style="margin-top:8px"><summary><small>+ Lieferung hinzufügen</small></summary>${lfFormular(nr, false)}</details>`;
}
async function lfHochladen(lid, file, melde) {
  const uid = (Date.now().toString(36) + Math.random().toString(36).slice(2, 12)).replace(/[^a-z0-9]/g, "");
  const ST = 8 * 1024 * 1024, teile = Math.max(1, Math.ceil(file.size / ST));
  for (let i = 0; i < teile; i++) {
    let ok = false, hinweis = "";
    for (let versuch = 0; versuch < 3 && !ok; versuch++) {
      try { const r = await fetch(`/api/crm/lieferungen/upload/${uid}/${i}`, { method: "PUT", body: file.slice(i * ST, (i + 1) * ST) });
        const j = await r.json(); ok = r.ok && j.ok !== false; hinweis = j.hinweis || ""; } catch (e) { hinweis = "Netzwerk"; }
    }
    if (!ok) throw new Error(`${file.name}: Upload abgebrochen bei ${Math.round(i / teile * 100)} % (${hinweis})`);
    melde(`${file.name}: ${Math.round((i + 1) / teile * 100)} %`);
  }
  const r = await jpost(`/api/crm/lieferungen/${encodeURIComponent(lid)}/fertig`, { upload_id: uid, name: file.name, groesse: file.size });
  if (!r || r.ok === false) throw new Error((r && r.hinweis) || `${file.name}: Abschluss fehlgeschlagen`);
}
// Lieferung anlegen + Dateien hochladen; `pflicht` = Titel zwingend (beim reinen „Lieferung hinzufuegen“)
async function lfSpeichern(nr, pflicht) {
  const titel = ($("#lf-titel") || {}).value.trim(), links = ($("#lf-links") || {}).value.trim(), files = [...((($("#lf-dateien") || {}).files) || [])];
  const fort = $("#lf-fortschritt"), melde = (t) => { if (fort) fort.textContent = t; };
  if (!titel && !links && !files.length) { if (pflicht) throw new Error("Bitte Titel und Dateien oder Links angeben."); return null; }
  if (!titel) throw new Error("Bitte einen Titel für die Lieferung angeben.");
  const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(nr)}/lieferungen`, { titel, links, notiz: ($("#lf-notiz") || {}).value || "", datum: ($("#lf-datum-st") || {}).value || "" });
  if (!r || r.ok === false) throw new Error((r && r.hinweis) || "Lieferung konnte nicht angelegt werden.");
  for (const f of files) await lfHochladen(r.id, f, melde);
  melde(files.length ? `${files.length} Datei(en) hochgeladen.` : "");
  return r;
}
// Etappe 25: Zeiten & Nachkalkulation -- NUR INTERN (nie im PDF, nie beim Kunden); Arbeitszeit ist kalkulatorisch, keine Buchung
async function abZeitLaden(nr) {
  const box = $("#ab-zeit-box"); if (!box) return;
  const d = await jget(`/api/finanzen/zeit?auftrag=${encodeURIComponent(nr)}`);
  if (!d) { box.innerHTML = ""; return; }
  const nk = d.nachkalkulation || {}, e = d.einstellungen || {}, lauf = d.laufend;
  const sz = d.stundenzettel || { eintraege: [], tage: [], summe: {} };   // PROJEKTZEITEN Z1: Stundenzettel wie Positionen
  const tagSumme = Object.fromEntries((sz.tage || []).map(t => [t.datum, t]));
  let zeilen = "", letzterTag = "";
  (sz.eintraege || []).forEach((x, i, alle) => {
    zeilen += `<tr><td class="zt-datum" data-tag="${esc(datumDe(x.datum))}">${x.datum !== letzterTag ? `<b>${esc(datumDe(x.datum))}</b>` : ""}</td><td class="zt-ein">${esc(x.von)}</td><td class="zt-aus">${esc(x.bis)}</td><td class="num zt-pause">${x.pause_min ? esc(String(x.pause_min)) + " min" : ""}</td>
      <td class="num zt-dauer"><b>${esc(dauerTxt(x.minuten))}</b></td><td>${esc(x.taetigkeit || "")}${x.notiz ? `<br><small class="v2-sub">${esc(x.notiz)}</small>` : ""}${x.korrigiert ? ` <small class="v2-sub" title="korrigiert">✎</small>` : ""}${x.abgerechnet ? ` <span class="v2-badge ok">${esc(x.abgerechnet)}</span>` : ""}</td>
      <td class="num">${x.km ? esc(String(x.km)) + " km" : ""}</td>
      <td class="v2-zt-akt">${x.abgerechnet ? "" : `<button class="v2-btn sm" data-act="zt-korr-form" data-id="${esc(x.id)}" data-val="${esc(nr)}" title="Ein/Aus/Pause/Tätigkeit korrigieren">✎</button>`}<button class="v2-btn sm" data-act="zeit-km" data-id="${esc(x.id)}" data-val="${esc(nr)}" title="Kilometer Hin + Rück">🚗</button>${x.abgerechnet ? "" : `<button class="v2-btn sm" data-act="zeit-storno" data-id="${esc(x.id)}" data-val="${esc(nr)}" title="Eintrag stornieren">↶</button>`}</td></tr>`;
    letzterTag = x.datum;
    const naechster = alle[i + 1];
    if (!naechster || naechster.datum !== x.datum) { const t = tagSumme[x.datum] || {};
      if (alle.filter(y => y.datum === x.datum).length > 1) zeilen += `<tr class="v2-zt-tag"><td colspan="4"><small>Summe ${esc(datumDe(x.datum))}</small></td><td class="num"><b>${esc(dauerTxt(t.minuten || 0))}</b></td><td></td><td class="num">${t.km ? esc(String(t.km)) + " km" : ""}</td><td></td></tr>`; }
  });
  if (zeilen) zeilen = `<div class="v2-tab-scroll"><table class="v2-table v2-zt"><thead><tr><th>Datum</th><th>Ein</th><th>Aus</th><th class="num">Pause</th><th class="num">Dauer</th><th>Tätigkeit</th><th class="num">km</th><th></th></tr></thead><tbody>${zeilen}</tbody>
    <tfoot><tr><td colspan="4"><b>Gesamt</b></td><td class="num"><b>${esc(dauerTxt((sz.summe || {}).minuten || 0))}</b></td><td></td><td class="num"><b>${(sz.summe || {}).km ? esc(String(sz.summe.km)) + " km" : ""}</b></td><td></td></tr></tfoot></table></div><div id="zt-korr-box"></div>`;
  const taetListe = `<datalist id="zt-taet-liste">${(d.taetigkeiten || []).map(t => `<option value="${esc(t)}">`).join("")}</datalist>`;
  box.innerHTML = `<h3>⏱ Zeiten &amp; Nachkalkulation <small class="v2-sub">🔒 nur intern, kalkulatorisch – nie im PDF, keine Buchung, nicht in der EÜR</small></h3>
    <div class="v2-an-intern" style="border-top:none">
      <div class="v2-kv"><span>Auftragssumme (Geld)</span><b>${cent2eur(nk.umsatz_cent || 0)}</b></div>
      <div class="v2-kv"><span>Arbeitszeit ${esc(dauerTxt(nk.minuten || 0))} × ${e.stundensatz_cent ? cent2eur(e.stundensatz_cent) + "/h" : "<i>Stundensatz fehlt</i>"} (kalkulatorisch)</span><b>−${cent2eur(nk.zeit_cent || 0)}</b></div>
      <div class="v2-kv"><span>Fahrtkosten ${nk.km || 0} km × 0,30 € (kalkulatorisch)</span><b>−${cent2eur(nk.fahrt_cent || 0)}</b></div>
      <div class="v2-kv"><span><b>Deckungsbeitrag</b></span><b style="${(nk.db_cent || 0) < 0 ? "color:var(--v2-red)" : ""}">${cent2eur(nk.db_cent || 0)}</b></div>
      ${nk.stundenlohn_cent != null ? `<div class="v2-kv"><span>Effektiver Stundenlohn</span><b>${cent2eur(nk.stundenlohn_cent)}/h</b></div>` : ""}
      ${(nk.je_position || []).length ? `<div class="v2-sub" style="margin-top:6px"><b>Je Leistung</b> (Zeit einer Position zugeordnet)</div>${nk.je_position.map(p => `<div class="v2-kv"><span>${p.position}. ${esc(p.beschreibung)} · ${esc(dauerTxt(p.minuten))}</span><b>${p.stundenlohn_cent != null ? cent2eur(p.stundenlohn_cent) + "/h" : "–"} <small class="v2-sub">DB ${cent2eur(p.db_cent)}</small></b></div>`).join("")}${nk.ohne_position_min ? `<div class="v2-kv"><span class="v2-sub">ohne Position</span><b class="v2-sub">${esc(dauerTxt(nk.ohne_position_min))}</b></div>` : ""}` : ""}</div>
    <div class="v2-card-actions" style="margin:8px 0">${lauf ? (lauf.auftrag === nr ? `<button class="v2-btn danger" data-act="zeit-stopp" data-id="${esc(nr)}">⏹ Zeit stoppen (läuft seit ${esc(lauf.start.slice(11, 16))})</button>` : `<small class="v2-sub">Es läuft gerade eine Zeit für ${esc(lauf.auftrag || lauf.firma)}.</small>`) : `<button class="v2-btn" data-act="zeit-start" data-id="${esc(nr)}">▶️ Zeit starten</button>`}</div>
    ${zeilen || `<div class="v2-sub">Noch keine Zeiten. Unterwegs per Telegram: „Bin auf dem Weg zu …“ / „Bin wieder zuhause“.</div>`}
    <details style="margin-top:8px"><summary><small>+ Zeit von Hand eintragen</small></summary><div class="v2-form">
      <div class="v2-an-zeile"><label class="v2-feld"><small>Datum</small><input id="zt-datum" type="date"></label><label class="v2-feld"><small>von</small><input id="zt-von" type="time"></label><label class="v2-feld"><small>bis</small><input id="zt-bis" type="time"></label><label class="v2-feld"><small>oder Dauer (Min.)</small><input id="zt-min" inputmode="numeric"></label></div>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Adresse des Drehs (leer = Firmenadresse)</small><input id="zt-adresse"></label><label class="v2-feld"><small>km Hin + Rück (leer = keine Fahrt)</small><input id="zt-km" inputmode="numeric"></label>
        <label class="v2-modlbl"><input type="checkbox" id="zt-km-auto"> km berechnen (OpenStreetMap)</label></div>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Tätigkeit</small><input id="zt-taet" list="zt-taet-liste" placeholder="z. B. Dreh, Schnitt"></label><label class="v2-feld"><small>Pause (Min.)</small><input id="zt-pause" inputmode="numeric"></label></div>${taetListe}
      <label class="v2-feld"><small>Notiz</small><input id="zt-notiz"></label>
      <button class="v2-btn" data-act="zeit-eintragen" data-id="${esc(nr)}">Eintragen</button><div id="zt-msg" class="v2-msg"></div></div></details>
    <details style="margin-top:6px"><summary><small>Stundensatz ${e.stundensatz_cent ? cent2eur(e.stundensatz_cent) + "/h" : "festlegen"}</small></summary><div class="v2-form"><small class="v2-sub">Brutto-Monatslohn × 12 ÷ (Wochenstunden × 52) – kalkulatorisch, bleibt nur auf der NAS.</small>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Brutto im Monat (€)</small><input id="zs-brutto" inputmode="decimal"></label><label class="v2-feld"><small>Wochenstunden</small><input id="zs-std" inputmode="decimal" value="${esc(String(e.wochenstunden || ""))}"></label></div>
      <button class="v2-btn" data-act="zeit-satz" data-id="${esc(nr)}">Speichern</button><div id="zs-msg" class="v2-msg"></div></div></details>`;
}
const dauerTxt = (m) => `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")} h`;
// Z1: Eintrag korrigieren (Ein/Aus/Pause/Taetigkeit, Grund Pflicht -- Verlauf bleibt in der Kette)
async function ztKorrForm(zid, nr) {
  const [d, ad] = await Promise.all([jget(`/api/finanzen/zeit?auftrag=${encodeURIComponent(nr)}`), jget("/api/crm/auftraege/" + encodeURIComponent(nr))]);
  const posListe = ((ad && ad.auftrag && ad.auftrag.positionen) || []);
  const x = ((d && d.stundenzettel && d.stundenzettel.eintraege) || []).find(e => e.id === zid); const box = $("#zt-korr-box"); if (!x || !box) return;
  box.innerHTML = `<h3>Zeit korrigieren</h3><div class="v2-form">
    <div class="v2-an-zeile"><label class="v2-feld"><small>Datum</small><input id="zk-datum" type="date" value="${esc(x.datum)}"></label><label class="v2-feld"><small>Ein</small><input id="zk-von" type="time" value="${esc(x.von)}"></label><label class="v2-feld"><small>Aus</small><input id="zk-bis" type="time" value="${esc(x.bis)}"></label><label class="v2-feld"><small>Pause (Min.)</small><input id="zk-pause" inputmode="numeric" value="${esc(String(x.pause_min || ""))}"></label></div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Tätigkeit</small><input id="zk-taet" list="zt-taet-liste" value="${esc(x.taetigkeit || "")}"></label><label class="v2-feld"><small>Grund der Korrektur *</small><input id="zk-grund" placeholder="z. B. Stoppen vergessen"></label></div>
    <button class="v2-btn pri" data-act="zt-korr-speichern" data-id="${esc(zid)}" data-val="${esc(nr)}">Korrektur speichern</button><div id="zk-msg" class="v2-msg"></div>
    ${posListe.length ? `<div class="v2-an-zeile" style="margin-top:10px"><label class="v2-feld"><small>Leistung (für die Nachkalkulation je Position)</small><select id="zk-pos" class="v2-inp"><option value="0">— keine —</option>${posListe.map((p, i) => `<option value="${i + 1}" ${Number(x.position || 0) === i + 1 ? "selected" : ""}>${i + 1}. ${esc(p.beschreibung)}</option>`).join("")}</select></label>
      <button class="v2-btn" data-act="zt-pos-speichern" data-id="${esc(zid)}" data-val="${esc(nr)}">Leistung zuordnen</button></div>` : ""}</div>`;
  box.scrollIntoView({ block: "nearest" });
}
async function zeitAktion(act, id, val) {
  let r;
  if (act === "zeit-start") r = await jpost("/api/finanzen/zeit/start", { auftrag: id });
  else if (act === "zeit-stopp") r = await jpost("/api/finanzen/zeit/stopp", {});
  else if (act === "zeit-storno") { const g = prompt("Grund für das Stornieren dieses Zeiteintrags:", ""); if (!g) return; r = await jpost(`/api/finanzen/zeit/${encodeURIComponent(id)}/stornieren`, { grund: g }); id = val; }
  else if (act === "zeit-km") {
    const v = await jget(`/api/finanzen/zeit/${encodeURIComponent(id)}/km`);
    const km = prompt(`Kilometer Hin + Rück${v && v.adresse ? " zu " + v.adresse : ""} (0,30 €/km, nur kalkulatorisch – keine Buchung):`, v && v.km ? String(v.km) : "");
    if (!km) return; r = await jpost(`/api/finanzen/zeit/${encodeURIComponent(id)}/fahrt`, { km }); id = val;
  } else if (act === "zeit-eintragen") {
    r = await jpost("/api/finanzen/zeit/eintrag", { auftrag: id, datum: $("#zt-datum").value, von: $("#zt-von").value, bis: $("#zt-bis").value, minuten: $("#zt-min").value.trim(),
      notiz: $("#zt-notiz").value.trim(), adresse: $("#zt-adresse").value.trim(), km: $("#zt-km").value.trim(), km_berechnen: $("#zt-km-auto").checked,
      taetigkeit: ($("#zt-taet") || {}).value || "", pause_min: ($("#zt-pause") || {}).value || "" });
    if (!r || !r.ok) return kundenMsg("zt-msg", (r && r.hinweis) || "Keine Verbindung.", false);
  } else if (act === "zeit-satz") {
    r = await jpost("/api/finanzen/zeit/einstellungen", { monatsbrutto: $("#zs-brutto").value.trim(), wochenstunden: $("#zs-std").value.trim() });
    if (!r || !r.ok) return kundenMsg("zs-msg", (r && r.hinweis) || "Keine Verbindung.", false);
  }
  if (r && r.ok === false) return alert(r.hinweis || "Fehler.");
  return abZeitLaden(id);
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
    <div class="v2-kv"><span>Anhang</span><a href="/api/crm/auftraege/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>${mailBlock("auftrag", nr, v)}
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="ab-senden-jetzt" data-id="${esc(nr)}" ${sendSperre(v)}>✉️ Jetzt senden</button><button class="v2-btn" data-act="ab-senden-abbruch">Abbrechen</button></div>
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
async function anSendenVorschau(nr, erneut) {
  const box = $("#an-senden-box"); if (!box) return;
  box.innerHTML = `<div class="v2-empty">Lade Vorschau…</div>`;
  const v = await jget(`/api/crm/angebote/${encodeURIComponent(nr)}/versandvorschau`);
  if (!v) { box.innerHTML = emptyRow("Vorschau nicht verfügbar."); return; }
  box.innerHTML = `<h3>${erneut ? "Angebot erneut senden / nachfassen" : "Angebot senden"}</h3>${erneut ? `<div class="v2-msg">Es geht das bereits versendete PDF noch einmal raus. Der Status bleibt, es entstehen keine neuen Erinnerungen – die Mail steht im Verlauf.</div>` : ""}<div class="v2-form v2-an-senden">
    <div class="v2-kv"><span>Absender</span><b>${esc(v.absender)}</b></div>
    <label class="v2-feld"><small>An *</small><input id="as-an" type="email" value="${esc(v.an || "")}" placeholder="kunde@firma.de"></label>
    <label class="v2-feld"><small>Betreff *</small><input id="as-betreff" value="${esc(v.betreff)}"></label>
    <label class="v2-feld"><small>Text * (Signatur anpassbar)</small><textarea id="as-text" class="v2-inp" rows="10">${esc(v.text)}</textarea></label>
    <div class="v2-kv"><span>Anhang</span><a href="/api/crm/angebote/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>${mailBlock("angebot", nr, v, erneut)}
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="an-senden-jetzt" data-id="${esc(nr)}" ${erneut ? 'data-val="erneut"' : ""} ${sendSperre(v)}>✉️ Jetzt senden</button><button class="v2-btn" data-act="an-senden-abbruch">Abbrechen</button></div>
    <div id="as-msg" class="v2-msg"></div>
    <small class="v2-sub">${erneut ? "„Jetzt senden“ geht aus LUNAs Google-Konto raus; Status und Erinnerungen bleiben unverändert, die Mail steht im Verlauf." : "Geht aus LUNAs Google-Konto raus. Danach ist das Angebot „versendet“ (nicht mehr änderbar), die Erinnerungen werden angelegt, Antworten des Kunden erscheinen hier und kommen per Telegram."}</small></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function anSendenJetzt(nr, erneut) {
  const an = $("#as-an").value.trim(), betreff = $("#as-betreff").value.trim(), text = $("#as-text").value.trim();
  if (!an || !an.includes("@")) return kundenMsg("as-msg", "Bitte eine gültige Empfänger-Adresse eintragen.", false);
  if (!confirm(`Angebot ${nr} jetzt ${erneut ? "erneut " : ""}an ${an} senden?\n\nDas lässt sich nicht zurückholen.`)) return;
  const b = $('[data-act="an-senden-jetzt"]'); if (b) { b.disabled = true; b.textContent = "⏳ sendet…"; }
  const r = await jpost(`/api/crm/angebote/${encodeURIComponent(nr)}/senden`, { an, betreff, text, bestaetigt: true, erneut: !!erneut });
  if (!r || !r.ok) { if (b) { b.disabled = false; b.textContent = "✉️ Jetzt senden"; } return kundenMsg("as-msg", (r && r.hinweis) || "Senden fehlgeschlagen.", false); }
  if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote();
  return anDetail(nr, [`${r.erneut ? "Erneut gesendet" : "Gesendet"} an ${r.an}.`, ...(r.termine || []).map(t => `📅 ${t.titel} (${new Date(t.datum).toLocaleDateString("de-DE")})`), ...(r.hinweise || [])].join("\n"));
}

/* ---------- TEXTBAUSTEINE T2/T3: Vorlage waehlen + Versand ueber das eigene Mail-Programm ---------- */
const E_ = encodeURIComponent;
const MP = {
  angebot: { px: "as", msg: "as-msg", vorschau: n => `/api/crm/angebote/${E_(n)}/versandvorschau`, senden: n => `/api/crm/angebote/${E_(n)}/senden`, fertig: (n, m) => { if (AKTIV === "angebote" || AKTIV === "auftraege") renderAngebote(); return anDetail(n, m); } },
  auftrag: { px: "abs", msg: "abs-msg", vorschau: n => `/api/crm/auftraege/${E_(n)}/versandvorschau`, senden: n => `/api/crm/auftraege/${E_(n)}/senden`, fertig: (n, m) => abDetail(n, m) },
  rechnung: { px: "res", msg: "res-msg", vorschau: n => `/api/finanzen/rechnungen/${E_(n)}/versandvorschau`, senden: n => `/api/finanzen/rechnungen/${E_(n)}/senden`, fertig: (n, m) => { if (AKTIV === "rechnungen") renderRechnungen(); return reDetail(n, m); } },
  mahnung: { px: "mas", msg: "mas-msg", vorschau: n => `/api/finanzen/mahnungen/${E_(n)}/versandvorschau`, senden: n => `/api/finanzen/mahnungen/${E_(n)}/senden`, fertig: (n, m) => reDetail(RE_DETAIL && RE_DETAIL.rechnung ? RE_DETAIL.rechnung.nummer : n, m) },
  bericht: { px: "ber", msg: "bers-msg", vorschau: n => `/api/crm/auftraege/${E_(n)}/bericht/versandvorschau`, senden: n => `/api/crm/auftraege/${E_(n)}/bericht/senden`, fertig: (n, m) => abDetail(n, m) },
  konzept: { px: "kzs", msg: "kzs-msg", vorschau: n => `/api/crm/konzept-versand/${E_(n)}`, senden: n => `/api/crm/konzept-versand/${E_(n)}`, fertig: async (n, m) => { await konzeptLaden(KZ.beleg); kundenMsg("kz-msg", m, true); } },
};
const MP_DATEI = {};
const MP_APPLE = /iPhone|iPad|Macintosh/.test(navigator.userAgent);
const MP_ERNEUT = {};
function mailBlock(art, nr, v, erneut) {
  const vl = v.vorlagen || [];
  MP_ERNEUT[art + "|" + nr] = !!erneut;
  const wahl = vl.length > 1 ? `<label class="v2-feld"><small>Textvorlage</small><select class="v2-inp v2-mp-vorlage" data-art="${esc(art)}" data-nr="${esc(nr)}">${vl.map(x => `<option value="${esc(x.id)}" ${x.id === v.vorlage ? "selected" : ""}>${esc(x.name)}${x.standard && x.name !== "Standard" ? " (Standard)" : ""}</option>`).join("")}</select></label>`
    : `<small class="v2-sub">Textvorlage „${esc((vl[0] || {}).name || "Standard")}“ – weitere Vorlagen und Signatur unter ⚙ Einstellungen.</small>`;
  setTimeout(() => mpVorbereiten(art, nr), 0);
  return `<div class="v2-mp">${wahl}
    <div class="v2-card-actions"><button class="v2-btn" data-act="mp-oeffnen" data-id="${esc(nr)}" data-val="${esc(art)}">✉️ Im Mail-Programm öffnen</button>
      <button class="v2-btn" data-act="mp-adresse" data-val="${esc(art)}">📋 Adresse kopieren</button></div>
    <div class="v2-mp-nach" data-mp-nach="${esc(art)}" hidden><small class="v2-sub">Mail aus deinem Mail-Programm verschickt? Dann hier abschließen – PDF kommt in die Firmenakte, Status und Erinnerungen wie beim Senden über LUNA.</small>
      <div class="v2-card-actions"><button class="v2-btn ok" data-act="mp-versendet" data-id="${esc(nr)}" data-val="${esc(art)}">${erneut ? "✓ Als erneut gesendet vermerken" : "✓ Als versendet markieren"}</button>
        ${MP_APPLE ? `<button class="v2-btn" data-act="mp-eml" data-id="${esc(nr)}" data-val="${esc(art)}">Als .eml-Datei</button>` : ""}</div></div></div>`;
}
async function mpVorbereiten(art, nr) {                   // PDF vorab laden: Teilen muss direkt im Tipp starten (Safari)
  if (!MP_APPLE || !navigator.canShare) return;
  try { const r = await fetch(`/api/crm/mailentwurf/${art}/${E_(nr)}/pdf`); if (!r.ok) return;
    const name = decodeURIComponent(r.headers.get("X-Dateiname") || `${nr}.pdf`);
    MP_DATEI[art + "|" + nr] = new File([await r.blob()], name, { type: "application/pdf" }); } catch { }
}
const mpFeld = (art, f) => ($(`#${MP[art].px}-${f}`) || {}).value || "";
function mpNach(art, text) { const n = document.querySelector(`[data-mp-nach="${art}"]`); if (n) n.hidden = false; if (text) kundenMsg(MP[art].msg, text, true); }
async function mpEml(art, nr) {
  const r = await fetch(`/api/crm/mailentwurf/${art}/${E_(nr)}/eml`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ an: mpFeld(art, "an").trim(), betreff: mpFeld(art, "betreff").trim(), text: mpFeld(art, "text").trim() }) });
  if (!r.ok) return kundenMsg(MP[art].msg, (await r.text()).slice(0, 200) || "Mail-Entwurf nicht möglich.", false);
  const url = URL.createObjectURL(await r.blob()), a = document.createElement("a");
  a.href = url; a.download = `${nr}.eml`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 5000);
  mpNach(art, "Mail-Entwurf heruntergeladen – Datei öffnen, Outlook zeigt die Mail mit Anhang, Text und Signatur.");
}
async function mpAktion(act, nr, art) {
  if (!MP[art]) return;
  if (act === "mp-oeffnen") {
    const f = MP_DATEI[art + "|" + nr];
    if (MP_APPLE && f && navigator.canShare && navigator.canShare({ files: [f] })) {
      try { await navigator.share({ files: [f], title: mpFeld(art, "betreff").trim(), text: mpFeld(art, "text").trim() }); }
      catch (e) { if (e && e.name === "AbortError") return; return mpEml(art, nr); }
      return mpNach(art, `Im Teilen-Menü „Mail“ wählen. Empfänger: ${mpFeld(art, "an").trim() || "bitte eintragen"} (mit „📋 Adresse kopieren“ übernehmen).`);
    }
    return mpEml(art, nr);
  }
  if (act === "mp-eml") return mpEml(art, nr);
  if (act === "mp-adresse") { const an = mpFeld(art, "an").trim(); if (!an) return kundenMsg(MP[art].msg, "Keine Adresse eingetragen.", false);
    try { await navigator.clipboard.writeText(an); kundenMsg(MP[art].msg, `Adresse kopiert: ${an}`, true); } catch { kundenMsg(MP[art].msg, `Adresse: ${an}`, true); } return; }
  if (act === "mp-versendet") {
    const an = mpFeld(art, "an").trim(); if (!an.includes("@")) return kundenMsg(MP[art].msg, "Bitte die Empfänger-Adresse eintragen (für die Ablage).", false);
    const erneut = !!MP_ERNEUT[art + "|" + nr];
    if (!confirm(erneut ? `Hast du die Mail an ${an} erneut verschickt?\n\nLUNA vermerkt sie im Verlauf.` : `Hast du die Mail an ${an} verschickt?\n\nLUNA markiert den Beleg dann als versendet und legt das PDF ab.`)) return;
    const r = await jpost(MP[art].senden(nr), { an, betreff: mpFeld(art, "betreff").trim(), text: mpFeld(art, "text").trim(), bestaetigt: true, kanal: "mail-programm", erneut });
    if (!r || !r.ok) return kundenMsg(MP[art].msg, (r && r.hinweis) || "Fehler.", false);
    return MP[art].fertig(nr, erneut ? `Erneut gesendet vermerkt (über dein Mail-Programm an ${an}).` : `Als versendet markiert (über dein Mail-Programm an ${an}).`);
  }
}
document.addEventListener("change", async (e) => {         // Vorlage gewechselt -> Betreff/Text neu aus der Vorschau
  const sel = e.target; if (!(sel instanceof HTMLSelectElement) || !sel.classList.contains("v2-mp-vorlage")) return;
  const art = sel.dataset.art, nr = sel.dataset.nr, v = await jget(MP[art].vorschau(nr) + "?vorlage=" + E_(sel.value));
  if (!v) return;
  const b = $(`#${MP[art].px}-betreff`), t = $(`#${MP[art].px}-text`); if (b) b.value = v.betreff; if (t) t.value = v.text;
});

/* ---------- Katalog (Preise pflegen, nur mit Modul Finanzen) ---------- */
async function renderKatalog(ausCache) {
  const k = ausCache ? KATALOG : await katalogLaden(true);
  if (!k) { $("#v2-app").innerHTML = anKopf() + emptyRow("Katalog nicht erreichbar."); return; }
  const ro = KAT_DARF ? "" : "disabled";
  const grp = k.gruppen.map((g, gi) => tile(g.name, `<div class="v2-kat-liste">${g.items.map(it => `<div class="v2-kat-zeile" data-gi="${gi}" data-id="${esc(it.id)}">
      <input class="v2-inp kat-name" value="${esc(it.name)}" ${ro}><input class="v2-inp kat-basis" value="${esc(it.basis)}" placeholder="Basis (Reichweite)" ${ro}>
      <input class="v2-inp kat-hinweis" value="${esc(it.hinweis)}" placeholder="Hinweis" ${ro}><input class="v2-inp kat-preis" value="${cent2feld(it.preis_cent)}" inputmode="decimal" ${ro}>
      <input class="v2-inp kat-einheit" value="${esc(it.einheit)}" placeholder="Einheit" ${ro}><label class="v2-modlbl"><input type="checkbox" class="kat-aktiv" ${it.aktiv ? "checked" : ""} ${ro}> aktiv</label>
      <div class="v2-kat-tkp"><small>Preismodell:</small><select class="v2-inp kat-prov-art" ${ro}><option value="">Festpreis</option><option value="stueck" ${it.provision_art === "stueck" ? "selected" : ""}>Provision je verkauftem Artikel (€)</option><option value="prozent" ${it.provision_art === "prozent" ? "selected" : ""}>Provision vom Umsatz (%)</option></select>
        <input class="v2-inp kat-prov-wert" value="${it.provision_art === "stueck" ? esc(cent2feld(it.provision_wert)) : it.provision_art ? esc(pz(it.provision_wert)) : ""}" placeholder="Satz (z. B. 5 oder 10)" inputmode="decimal" ${ro}></div>
      <details class="v2-kat-kalk" data-lager-start="${esc(it.lager_start || "")}"><summary><small>Kalkulation &amp; Lager (intern)${katKalkKurz(it, k)}</small></summary>
        <div class="v2-kat-tkp"><small>Kosten je Einheit:</small>${Object.entries(KOSTEN_ARTEN).map(([a, n]) => `<input class="v2-inp kat-kosten" data-art="${a}" value="${(it.kosten || {})[a] ? esc(cent2feld(it.kosten[a])) : ""}" placeholder="${esc(n)} €" inputmode="decimal" title="${esc(n)}" ${ro}>`).join("")}</div>
        <div class="v2-kat-tkp"><label class="v2-modlbl"><input type="checkbox" class="kat-physisch" ${it.physisch ? "checked" : ""} ${ro}> physische Ware (Lagerbestand führen)</label>
          <input class="v2-inp kat-mindest" value="${it.physisch ? esc(String(it.mindestbestand || 0)) : ""}" placeholder="Mindestbestand" inputmode="numeric" ${ro}></div></details>
      <div class="v2-kat-tkp"><small>TKP-Rechnung (leer = Festpreis):</small>
        <input class="v2-inp kat-kontakte" value="${it.kontakte ? esc(String(it.kontakte)) : ""}" placeholder="Kontakte (Median)" inputmode="numeric" ${ro}>
        <input class="v2-inp kat-tmin" value="${it.tkp_min_cent ? esc(String(it.tkp_min_cent / 100)) : ""}" placeholder="TKP min €" inputmode="decimal" ${ro}>
        <input class="v2-inp kat-tmax" value="${it.tkp_max_cent ? esc(String(it.tkp_max_cent / 100)) : ""}" placeholder="TKP max €" inputmode="decimal" ${ro}>
        <input class="v2-inp kat-prod" value="${it.kontakte ? esc(cent2feld(it.produktion_cent || 0)) : ""}" placeholder="Produktion €" inputmode="decimal" ${ro}>
        <select class="v2-inp kat-omr" ${ro}><option value="">OMR-Vergleich: keiner</option>${Object.entries(OMR.werte || {}).map(([k, w]) => `<option value="${esc(k)}" ${it.omr === k ? "selected" : ""}>${esc(w.name)} (${w.min}–${w.max} €)</option>`).join("")}</select>
        <small class="v2-sub">${it.kontakte ? `= ${esc(cent2eur(tkpPreis(it.kontakte, it.tkp_min_cent, it.produktion_cent || 0)))} bis ${esc(cent2eur(tkpPreis(it.kontakte, it.tkp_max_cent, it.produktion_cent || 0)))}${it.omr ? " · " + esc(omrText(it.omr)) : ""}` : ""}</small>
        ${IST_KONTAKTE[it.id] ? `<small class="v2-kat-ist">📊 Gemessen: Median ${esc(Number(IST_KONTAKTE[it.id].median).toLocaleString("de-DE"))} aus ${IST_KONTAKTE[it.id].anzahl} Posting(s) (${esc(Number(IST_KONTAKTE[it.id].min).toLocaleString("de-DE"))}–${esc(Number(IST_KONTAKTE[it.id].max).toLocaleString("de-DE"))})${KAT_DARF ? ` <button class="v2-btn sm" data-act="kat-ist" data-val="${IST_KONTAKTE[it.id].median}">übernehmen</button>` : ""}</small>` : ""}</div></div>`).join("")}</div>
      ${KAT_DARF ? `<button class="v2-btn" data-act="kat-neu" data-id="${gi}">+ Format</button>` : ""}`, "w12")).join("");
  const zu = tile("Zuschläge", `${k.zuschlaege.map(z => `<div class="v2-kat-zu" data-id="${esc(z.id)}"><input class="v2-inp zu-name" value="${esc(z.name)}" ${ro}><input class="v2-inp zu-prozent" value="${esc(pz(z.prozent))}" inputmode="decimal" ${ro}><input class="v2-inp zu-info" value="${esc(z.info)}" placeholder="Erklärung" ${ro}></div>`).join("")}`, "w12");
  const t = k.texte, ta = (id, v, rows = 3) => `<textarea id="kt-${id}" rows="${rows}" class="v2-inp" ${ro}>${esc(v || "")}</textarea>`;
  const texte = tile("Textbausteine (Angebot + Preisliste)", `<div class="v2-form">
    <label class="v2-feld"><small>Untertitel</small><input id="kt-untertitel" value="${esc(t.untertitel)}" ${ro}></label>
    <label class="v2-feld"><small>Einleitung</small>${ta("intro", t.intro)}</label>
    <label class="v2-feld"><small>Überschrift Kalkulation</small><input id="kt-kalkulation_titel" value="${esc(t.kalkulation_titel)}" ${ro}></label>
    ${[0, 1, 2].map(i => `<label class="v2-feld"><small>Kalkulation, Absatz ${i + 1} (Text vor dem ersten Doppelpunkt wird fett)${i === 1 ? " – beginnt er mit „2. TKP“, schreibt LUNA ihn aus den TKP-Werten neu" : ""}</small>${ta("kalk" + i, (t.kalkulation || [])[i])}</label>`).join("")}
    <label class="v2-feld"><small>Rechenbeispiel (bei TKP-Formaten erzeugt LUNA die Rechnung je Format selbst)</small>${ta("kalkulation_beispiel", t.kalkulation_beispiel, 2)}</label>
    <small class="v2-sub">Kennzahlen (bis Etappe 3c von Hand; danach aus deinen Meta-Exporten)</small>
    <div class="v2-an-zeile">${[0, 1, 2, 3].map(i => `<div class="v2-feld"><input id="kt-kzw${i}" value="${esc(((t.kennzahlen || [])[i] || [])[0] || "")}" placeholder="Wert" ${ro}><input id="kt-kzl${i}" value="${esc(((t.kennzahlen || [])[i] || [])[1] || "")}" placeholder="Beschriftung" ${ro}></div>`).join("")}</div>
    <label class="v2-feld"><small>Datenbasis-Hinweis</small>${ta("kennzahlen_quelle", t.kennzahlen_quelle)}</label>
    <label class="v2-feld"><small>Einleitung „Zusätzliche Leistungen“ (Preisliste)</small>${ta("zuschlaege_info", t.zuschlaege_info, 2)}</label>
    <label class="v2-feld"><small>Fußtext</small>${ta("fuss", t.fuss)}</label>
    <label class="v2-feld"><small>Kontakt (Fußzeile)</small><input id="kt-kontakt" value="${esc(t.kontakt)}" ${ro}></label>
    <small class="v2-sub">Präsentation im Angebot (Canva, je Angebot Deutsch/Englisch wählbar; leer = aus)</small>
    ${[["de", "Deutsch"], ["en", "Englisch"]].map(([s2, l]) => `<div class="v2-an-zeile"><label class="v2-feld"><small>Link ${l}</small><input id="kt-praesentation_${s2}" type="url" inputmode="url" value="${esc(t["praesentation_" + s2] || "")}" placeholder="https://…" ${ro}></label><label class="v2-feld"><small>Linktext ${l}</small><input id="kt-praesentation_text_${s2}" value="${esc(t["praesentation_text_" + s2] || "")}" ${ro}></label></div>`).join("")}</div>`, "w12");
  const aktion = KAT_DARF ? `<span id="kat-msg" class="v2-msg"></span><button class="v2-btn pri" data-act="kat-speichern">Katalog speichern</button>` : `<span class="v2-sub">Nur ansehen — Preise ändert der Owner (Modul Finanzen).</span>`;
  const lager = await jget("/api/finanzen/lager");
  const la = (lager && lager.artikel) || [];
  const lagerTile = tile("📦 Lager (physische Ware)", la.length ? `<table class="v2-table"><thead><tr><th>Artikel</th><th style="text-align:right">Bestand</th><th style="text-align:right">Mindest</th><th>seit</th></tr></thead><tbody>${la.map(x => `<tr><td>${esc(x.name)}</td><td style="text-align:right"><b style="${x.niedrig ? "color:var(--v2-red)" : ""}">${esc(String(x.bestand))}</b></td><td style="text-align:right">${esc(String(x.mindestbestand))}</td><td>${esc(datumDe(x.lager_start))}</td></tr>`).join("")}</tbody></table>
    ${KAT_DARF ? `<div class="v2-form" style="margin-top:10px"><div class="v2-an-zeile"><label class="v2-feld"><small>Artikel</small><select id="lg-artikel">${la.map(x => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join("")}</select></label>
      <label class="v2-feld"><small>Menge (+ Zugang / − Abgang)</small><input id="lg-menge" inputmode="numeric" placeholder="z. B. 50"></label><label class="v2-feld"><small>Datum</small><input id="lg-datum" type="date"></label></div>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Grund</small><input id="lg-grund" placeholder="Wareneingang, Inventur, Bruch …"></label><label class="v2-feld"><small>Beleg (optional)</small><input id="lg-beleg" placeholder="ER-2026-…"></label></div>
      <button class="v2-btn" data-act="lg-buchen">Bewegung erfassen</button><div id="lg-msg" class="v2-msg"></div></div>` : ""}`
    : emptyRow("Noch keine physische Ware. Im Katalog bei einem Artikel unter „Kalkulation & Lager“ „physische Ware“ anhaken — Verkäufe laut Rechnungen zählen dann automatisch ab."), "w12");
  const marge = KAT_DARF ? `<label class="v2-feld" style="max-width:220px"><small>Mindestmarge in % (Warnung darunter)</small><input id="kat-mindestmarge" value="${esc(pz(k.mindestmarge_prozent ?? 30))}" inputmode="decimal"></label>` : "";
  $("#v2-app").innerHTML = anKopf() + `<div class="v2-card-actions" style="justify-content:space-between;margin-bottom:10px">${marge}<span>${aktion}</span></div><div class="v2-grid">${grp}${lagerTile}${zu}${texte}</div>`;
}
const KOSTEN_ARTEN = { einkauf: "Einkauf", fremdleistung: "Fremdleistung/Freelancer", material: "Material", reise: "Reise/Fahrt", sonstiges: "Sonstiges" };
function katKalk(it, mm) {   // wie core/katalog.kalkulation -- nur intern
  const kosten = Object.values(it.kosten || {}).reduce((s, c) => s + c, 0);
  if (!kosten || it.provision_art || !it.preis_cent) return null;
  const db = it.preis_cent - kosten, marge = Math.round(db * 1000 / it.preis_cent) / 10;
  return { kosten, db, marge, unter: marge < (mm ?? 30) };
}
function katKalkKurz(it, k) {
  const x = katKalk(it, k.mindestmarge_prozent);
  return (x ? ` · Kosten ${cent2eur(x.kosten)} · DB ${cent2eur(x.db)} · <b style="${x.unter ? "color:var(--v2-red)" : ""}">Marge ${pz(x.marge)} %${x.unter ? " ⚠️" : ""}</b>` : "") + (it.physisch ? " · 📦 Lager" : "");
}
async function lagerBuchen() {
  const r = await jpost(`/api/finanzen/lager/${encodeURIComponent($("#lg-artikel").value)}/bewegung`, { menge: $("#lg-menge").value.trim(), grund: $("#lg-grund").value.trim(), datum: $("#lg-datum").value, beleg: $("#lg-beleg").value.trim() });
  if (!r || !r.ok) return kundenMsg("lg-msg", (r && r.hinweis) || "Keine Verbindung.", false);
  return renderKatalog(true);
}
function katalogAusForm() {
  const k = JSON.parse(JSON.stringify(KATALOG));
  k.gruppen.forEach(g => g.items = []);
  document.querySelectorAll(".v2-kat-zeile").forEach(z => {
    const g = k.gruppen[Number(z.dataset.gi)];
    g.items.push({ id: z.dataset.id, name: $(".kat-name", z).value.trim(), basis: $(".kat-basis", z).value.trim(), hinweis: $(".kat-hinweis", z).value.trim(),
      preis_cent: Math.round(zahl($(".kat-preis", z).value) * 100), einheit: $(".kat-einheit", z).value.trim(), aktiv: $(".kat-aktiv", z).checked,
      kontakte: ($(".kat-kontakte", z) || {}).value ? Math.round(zahl($(".kat-kontakte", z).value.replace(/\./g, ""))) : null,
      tkp_min_cent: Math.round(zahl(($(".kat-tmin", z) || {}).value || "0") * 100), tkp_max_cent: Math.round(zahl(($(".kat-tmax", z) || {}).value || "0") * 100),
      produktion_cent: Math.round(zahl(($(".kat-prod", z) || {}).value || "0") * 100), omr: ($(".kat-omr", z) || {}).value || "",
      ...(($(".kat-prov-art", z) || {}).value ? { provision_art: $(".kat-prov-art", z).value, provision_wert: $(".kat-prov-art", z).value === "stueck" ? Math.round(zahl($(".kat-prov-wert", z).value) * 100) : zahl($(".kat-prov-wert", z).value) } : {}),
      kosten: Object.fromEntries([...z.querySelectorAll(".kat-kosten")].filter(i => i.value.trim()).map(i => [i.dataset.art, Math.round(zahl(i.value) * 100)])),
      ...(($(".kat-physisch", z) || {}).checked ? { physisch: true, mindestbestand: Math.round(zahl($(".kat-mindest", z).value || "0")), lager_start: ($(".v2-kat-kalk", z) || {}).dataset?.lagerStart || "" } : {}) });
  });
  if ($("#kat-mindestmarge")) k.mindestmarge_prozent = zahl($("#kat-mindestmarge").value || "30");
  k.zuschlaege = [...document.querySelectorAll(".v2-kat-zu")].map(z => ({ id: z.dataset.id, name: $(".zu-name", z).value.trim(), prozent: zahl($(".zu-prozent", z).value), info: $(".zu-info", z).value.trim() }));
  const v = (id) => ($("#kt-" + id) || {}).value || "";
  k.texte = { untertitel: v("untertitel"), intro: v("intro"), kalkulation_titel: v("kalkulation_titel"), kalkulation: [0, 1, 2].map(i => v("kalk" + i)).filter(x => x.trim()),
    kalkulation_beispiel: v("kalkulation_beispiel"), kennzahlen: [0, 1, 2, 3].map(i => [v("kzw" + i), v("kzl" + i)]).filter(x => x[0].trim()),
    kennzahlen_quelle: v("kennzahlen_quelle"), zuschlaege_info: v("zuschlaege_info"), fuss: v("fuss"), kontakt: v("kontakt"),
    praesentation_de: v("praesentation_de").trim(), praesentation_en: v("praesentation_en").trim(),
    praesentation_text_de: v("praesentation_text_de"), praesentation_text_en: v("praesentation_text_en") };
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
const RE_ART = { anzahlung: "Vorkasse", rechnung: "", storno: "Storno" };
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
  const rows = liste ? liste.map(r => `<tr class="klick" data-act="re-detail" data-id="${esc(r.nummer)}"><td><b>${esc(r.nummer)}</b>${r.art === "storno" ? " <small>Storno zu " + esc(r.bezug) + "</small>" : r.art === "anzahlung" ? " <small>Vorkasse</small>" : ""}</td><td>${esc(r.firma_name || r.firma)}</td><td>${esc(r.titel || "")}</td><td>${esc(datumDe(r.rechnungsdatum))}</td><td>${esc(datumDe(r.faellig_am))}</td><td style="text-align:right">${cent2eur(r.summe_cent)}</td><td>${reBadge(r)}${r.versendet ? " ✉️" : ""}</td></tr>`).join("")
    : (d.entwuerfe || []).map(e => `<tr class="klick" data-act="re-detail" data-id="${esc(e.entwurf_id)}"><td><b>${e.art === "anzahlung" ? "Vorkasse-Entwurf" : "Entwurf"}</b> <small>${esc(e.entwurf_id)}</small></td><td>${esc(e.firma_name || e.firma)}</td><td>${esc(e.titel || "")}</td><td>${esc(e.auftrag || "")}</td><td></td><td style="text-align:right">${cent2eur(e.summe_cent)}</td><td>${reBadge({ status: "entwurf" })}</td></tr>`).join("");
  const kopf = sub === "entwuerfe" ? "<th>Entwurf</th><th>Firma</th><th>Titel</th><th>Auftrag</th><th></th><th style=\"text-align:right\">Summe</th><th></th>" : "<th>Nr.</th><th>Firma</th><th>Titel</th><th>Datum</th><th>Fällig</th><th style=\"text-align:right\">Betrag</th><th>Status</th>";
  const body = `${tile("Umsatz " + jahr, `<div class="v2-kpi">${esc(cent2eur(w.umsatz_cent || 0))}</div>${balken}`, "w4")}
    ${kpiTile("Offen", String(offen.length), null, cent2eur(offen.reduce((x, r) => x + r.summe_cent - (r.bezahlt_cent || 0), 0)))}
    ${kpiTile("Überfällig", String(ueber.length), null, ueber.length ? cent2eur(ueber.reduce((x, r) => x + r.summe_cent - (r.bezahlt_cent || 0), 0)) : "alles im Zeitplan")}
    ${kpiTile("Bezahlt " + jahr, String(bezahlt.length), null, cent2eur(bezahlt.reduce((x, r) => x + r.summe_cent, 0)))}
    ${tile(sub === "entwuerfe" ? "Entwürfe (noch ohne Nummer)" : sub === "offen" ? "Offene Rechnungen" : "Alle Rechnungen", rows ? `<table class="v2-table"><thead><tr>${kopf}</tr></thead><tbody>${rows}</tbody></table>` : emptyRow(sub === "entwuerfe" ? "Keine Entwürfe." : "Keine Rechnungen — aus einem Auftrag („🧾 Rechnung erstellen“) oder oben rechts „+ Neue Rechnung“."), "w12")}`;
  $("#v2-app").innerHTML = secHead("Rechnungen", `<button class="v2-btn" data-act="re-alt-form" title="Rechnung, die du vor LUNA mit eigener Nummer geschrieben hast">+ Altrechnung erfassen</button><button class="v2-btn pri" data-act="re-neu">+ Neue Rechnung</button>`) + tabs("rechnungen", [["offen", "Offen"], ["alle", "Alle"], ["entwuerfe", `Entwürfe (${(d.entwuerfe || []).length})`]]) + `<div class="v2-grid">${body}</div>`;
}
// Etappe 19: Rechnungen von vor LUNA (eigene Nummer, eigenes PDF) und dort schon verschickte Mahnungen
async function reAltForm() {
  const k = await jget("/api/crm/kunden"); const firmen = ((k && k.firmen) || []).filter(f => f.aktiv !== false);
  openModal("Altrechnung erfassen", `<div class="v2-form">
    <div class="v2-msg">Für Rechnungen, die du <b>vor LUNA</b> mit eigener Nummer geschrieben und verschickt hast. LUNA übernimmt Nummer und Original-PDF unverändert – es entsteht <b>keine</b> neue Rechnung. Danach: Zahlung erfassen oder mahnen wie gewohnt.</div>
    <label class="v2-feld"><small>Kunde *</small><select id="ra-firma"><option value="">— wählen —</option>${firmen.map(f => `<option value="${esc(f.nummer)}">${esc(f.name)} (${esc(f.nummer)})</option>`).join("")}</select></label>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Rechnungsnummer (Original) *</small><input id="ra-nr" placeholder="z. B. RG-11052026"></label>
      <label class="v2-feld"><small>Rechnungsdatum *</small><input id="ra-datum" type="date"></label>
      <label class="v2-feld"><small>Fällig am (leer = sofort)</small><input id="ra-faellig" type="date"></label></div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Betrag in € *</small><input id="ra-betrag" inputmode="decimal"></label>
      <label class="v2-feld"><small>Leistung von</small><input id="ra-von" type="date"></label><label class="v2-feld"><small>bis</small><input id="ra-bis" type="date"></label></div>
    <label class="v2-feld"><small>Leistung (wie auf der Rechnung)</small><input id="ra-leistung" placeholder="z. B. Provisionen aus Affiliate-Partnerschaft"></label>
    <label class="v2-feld"><small>Original-PDF *</small><input id="ra-pdf" type="file" accept=".pdf,application/pdf"></label>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="re-alt-speichern">Übernehmen</button><div id="ra-msg" class="v2-msg"></div></div></div>`, true);
}
async function reAltSpeichern() {
  const f = ($("#ra-pdf") || {}).files; if (!f || !f.length) return kundenMsg("ra-msg", "Bitte das Original-PDF wählen.", false);
  const datei = await blLesen(f[0]);
  const r = await jpost("/api/finanzen/rechnungen/alt", { datei, rechnung: { firma: $("#ra-firma").value, nummer: $("#ra-nr").value.trim(), rechnungsdatum: $("#ra-datum").value,
    faellig_am: $("#ra-faellig").value, betrag: $("#ra-betrag").value.trim(), leistung_von: $("#ra-von").value, leistung_bis: $("#ra-bis").value, leistung: $("#ra-leistung").value.trim() } });
  if (!r || !r.ok) return kundenMsg("ra-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  return reDetail(r.nummer, `${r.nummer} übernommen.`);
}
// Etappe 28: gerichtliches Mahnverfahren eintragen (CEO 2026-10-01)
function reMvForm(nr) {
  const box = $("#re-aktion-box"); if (!box) return;
  box.innerHTML = `<h3>Mahnverfahren eintragen</h3><div class="v2-form"><small class="v2-sub">Das gerichtliche Mahnverfahren läuft (z. B. von der Anwältin digital beantragt). Die Rechnung bleibt offen; LUNA meldet sie dann nicht mehr als dringend.</small>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Eingeleitet am *</small><input id="mv-datum" type="date" value="${heuteIso()}"></label><label class="v2-feld"><small>Durch</small><input id="mv-durch" class="v2-inp" placeholder="z. B. Rechtsanwältin Marquardt"></label></div>
    <label class="v2-feld"><small>Notiz</small><input id="mv-notiz" class="v2-inp" maxlength="500" placeholder="z. B. Aktenzeichen, Stand"></label>
    <button class="v2-btn pri" data-act="re-mv-speichern" data-id="${esc(nr)}">Mahnverfahren eintragen</button><div id="mv-msg" class="v2-msg"></div></div>`;
}
async function reMvSpeichern(nr) {
  const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(nr)}/mahnverfahren`, { datum: $("#mv-datum").value, durch: $("#mv-durch").value.trim(), notiz: $("#mv-notiz").value.trim() });
  if (!r || !r.ok) return kundenMsg("mv-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  glockeAktualisieren();
  return reDetail(nr, "Mahnverfahren eingetragen.");
}
function reAltMahnForm(nr) {
  const box = $("#re-aktion-box"); if (!box) return;
  box.innerHTML = `<h3>Mahnung vor LUNA erfassen</h3><div class="v2-form"><small class="v2-sub">Für Mahnungen, die du schon selbst verschickt hast – LUNA zählt die Stufe mit und macht danach mit der nächsten weiter.</small>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Mahnungsdatum *</small><input id="rm-datum" type="date"></label><label class="v2-feld"><small>Frist bis (leer = +7 Tage)</small><input id="rm-frist" type="date"></label>
    <label class="v2-feld"><small>Geforderter Betrag (leer = offener Rest)</small><input id="rm-summe" inputmode="decimal"></label></div>
    <label class="v2-feld"><small>PDF der Mahnung (optional)</small><input id="rm-pdf" type="file" accept=".pdf,application/pdf"></label>
    <button class="v2-btn pri" data-act="re-altmahn-speichern" data-id="${esc(nr)}">Mahnung erfassen</button><div id="rm-msg" class="v2-msg"></div></div>`;
}
async function reAltMahnSpeichern(nr) {
  const f = ($("#rm-pdf") || {}).files; const datei = f && f.length ? await blLesen(f[0]) : null;
  const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(nr)}/altmahnung`, { datum: $("#rm-datum").value, frist: $("#rm-frist").value, summe: $("#rm-summe").value.trim(), ...(datei ? { datei } : {}) });
  if (!r || !r.ok) return kundenMsg("rm-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  return reDetail(nr, `${r.nummer} erfasst (Stufe ${r.stufe}).`);
}
function reFormHtml(r, eid) {
  RE_AUS_AUFTRAG = !!r.auftrag;
  const fa = AN_FIRMEN.find(f => f.nummer === r.firma);
  const gewaehlt = new Set((r.zuschlaege || []).map(z => z.id));
  const zuListe = [...((KATALOG && KATALOG.zuschlaege) || []), ...(r.zuschlaege || []).filter(z => !((KATALOG && KATALOG.zuschlaege) || []).some(x => x.id === z.id))];
  const zuHtml = zuListe.map(z => { const alt = (r.zuschlaege || []).find(x => x.id === z.id); const pr = alt ? alt.prozent : z.prozent;
    return `<label class="v2-modlbl"><input type="checkbox" class="an-zu" value="${esc(z.id)}" data-name="${esc(z.name)}" data-prozent="${esc(String(pr))}" ${gewaehlt.has(z.id) ? "checked" : ""}> +${esc(pz(pr))} % ${esc(z.name)}</label>`; }).join("");
  const rmax = esc(String((KATALOG && KATALOG.rabatt_max) || 30));
  return `<div class="v2-form v2-an-editor">
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
    <div class="v2-an-kat"><button class="v2-btn pri" data-act="an-pos-neu">+ Neue Position</button></div>
    <div class="v2-an-pos v2-an-pos-kopf"><span>Leistung / Detail</span><span>Menge</span><span>Einheit</span><span>Einzelpreis</span><span>Gesamt</span><span></span></div>
    <div id="an-pos">${(r.positionen || []).map(anPosZeile).join("")}</div>
    <div id="an-pos-leer" class="v2-empty">Noch keine Position.</div>
    <div class="v2-an-fuss"><div class="v2-form">${zuHtml ? `<small class="v2-sub">Zuschläge</small><div class="v2-mods">${zuHtml}</div>` : ""}
        <label class="v2-feld"><small>Rabatt in % (0–${rmax})</small><input id="an-rabatt" type="number" min="0" max="${rmax}" step="0.5" value="${esc(String(r.rabatt_prozent || 0))}"></label>
        ${anWareFelder(r.ware)}</div>
      <div id="an-summe-box" class="v2-an-summen"></div></div>
    <label class="v2-feld"><small>Einleitung (leer = „vielen Dank für Ihren Auftrag. Wir berechnen Ihnen folgende Leistungen:“)</small><textarea id="an-einleitung" rows="2" class="v2-inp">${esc(r.einleitung || "")}</textarea></label>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="re-speichern" data-id="${esc(eid || "")}">${eid ? "Entwurf speichern" : "Entwurf anlegen (noch ohne Nummer)"}</button><div id="an-msg" class="v2-msg"></div></div></div>`;
}
async function reEditor(eid) {
  if (eid) return reDetail(eid);                                  // Bearbeiten passiert im Beleg selbst
  AN_KONTEXT = "rechnung";
  openModal("Neue Rechnung", `<div class="v2-empty">Lade…</div>`, true);
  await belegFormDaten();
  if (!AN_FIRMEN.length) return openModal("Neue Rechnung", emptyRow("Zuerst unter „🏢 Kunden“ eine Firma anlegen."), true);
  const r = { firma: "", positionen: [], zuschlaege: [], rabatt_prozent: 0, layout: "hanserautisch", leistung_von: heuteIso(), zahlungsziel_tage: "" };
  openModal("Neue Rechnung", reFormHtml(r, ""), true);
  await belegFormularFertig("", "");
}
async function reSpeichern(eid) {
  if (!$("#an-firma").value) { $("#an-firma-suche").focus(); return kundenMsg("an-msg", "Bitte eine Firma aus den Vorschlägen auswählen.", false); }
  const rechnung = { firma: $("#an-firma").value, ansprechpartner: $("#an-ap").value, titel: $("#an-titel").value.trim(), leistung_von: $("#re-von").value, leistung_bis: $("#re-bis").value,
    layout: $("#an-layout").value, einleitung: $("#an-einleitung").value.trim(), positionen: anPositionen(), zuschlaege: anZuschlaege(), rabatt_prozent: ($("#an-rabatt") || {}).value || 0, ware: anWare() };
  if ($("#re-ziel").value !== "") rechnung.zahlungsziel_tage = $("#re-ziel").value;
  const r = eid ? await jpost("/api/finanzen/rechnungen/" + encodeURIComponent(eid), { rechnung }) : await jpost("/api/finanzen/rechnungen", { rechnung });
  if (!r || !r.ok) return kundenMsg("an-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  FORM_GEAENDERT = false;
  if (AKTIV === "rechnungen") renderRechnungen();
  return reDetail(eid || r.entwurf_id, eid ? "Entwurf gespeichert." : "Entwurf angelegt — prüfen, dann festschreiben.");
}
async function reDetail(id, meldung, fehler) {
  openModal(id, `<div class="v2-empty">Lade…</div>`, true);
  const [d] = await Promise.all([jget("/api/finanzen/rechnungen/" + encodeURIComponent(id)), belegFormDaten()]);
  const r = d && d.rechnung; if (!r) return openModal(id, emptyRow("Rechnung nicht gefunden."), true);
  AN_KONTEXT = "rechnung";
  if (!AN_FIRMEN.some(f => f.nummer === r.firma)) AN_FIRMEN.push({ nummer: r.firma, name: (d.firma || {}).name || r.firma });
  const entwurf = r.status === "entwurf", sm = r.summen, ap = d.ansprechpartner;
  const pos = r.positionen.map((p, i) => `<tr><td>${i + 1}</td><td><b>${esc(p.beschreibung)}</b>${p.detail ? `<br><small>${esc(p.detail)}</small>` : ""}${p.provision ? `<br><small>💶 ${esc(provText(p.provision))}</small>` : ""}${p.preis_grund ? `<br><small>✎ Preis geändert (vorher ${cent2eur(p.preis_vorher_cent)}) · Grund: ${esc(p.preis_grund)}</small>` : ""}</td><td style="text-align:right">${esc(String(p.menge).replace(".", ","))} ${esc(p.einheit || "")}</td><td style="text-align:right">${posBetrag(p)}</td></tr>`).join("");
  const fuss = (sm.zuschlaege.length || sm.rabatt ? `<tr><td></td><td>Summe Positionen</td><td></td><td style="text-align:right">${cent2eur(sm.formate_cent)}</td></tr>` : "")
    + sm.zuschlaege.map(([n, p, c]) => `<tr><td></td><td>${esc(n)} (+${esc(pz(p))} %)</td><td></td><td style="text-align:right">${cent2eur(c)}</td></tr>`).join("")
    + (sm.rabatt ? `<tr><td></td><td>Rabatt (${esc(pz(sm.rabatt[0]))} %)</td><td></td><td style="text-align:right">−${cent2eur(Math.abs(sm.rabatt[1]))}</td></tr>` : "")
    + (sm.abzuege ? `<tr><td></td><td>Auftragssumme</td><td></td><td style="text-align:right">${cent2eur(sm.vor_abzug_cent)}</td></tr>` + sm.abzuege.map(([n, c]) => `<tr><td></td><td>${esc(n)}</td><td></td><td style="text-align:right">−${cent2eur(c)}</td></tr>`).join("") : "")
    + `<tr><td></td><td><b>Rechnungsbetrag</b></td><td></td><td style="text-align:right"><b>${cent2eur(sm.gesamt_cent)}</b></td></tr>`;
  let aktionen = `<a class="v2-btn" href="/api/finanzen/rechnungen/${encodeURIComponent(id)}/pdf" target="_blank" rel="noopener">📄 ${entwurf ? "PDF-Vorschau" : "Rechnung (PDF)"}</a><button class="v2-btn" data-act="bv-oeffnen" data-id="${esc(id)}">🔗 Belegverfolgung</button>`;
  if (entwurf) aktionen += `<button class="v2-btn pri" data-act="re-festschreiben" data-id="${esc(id)}" ${d.steuernummer ? "" : "disabled title=\"Steuernummer fehlt\""}>🔒 Festschreiben (Nummer vergeben)</button>
    <button class="v2-btn" data-act="re-verwerfen" data-id="${esc(id)}">Entwurf verwerfen</button>`;
  else {
    if (r.art !== "storno") aktionen += `<button class="v2-btn pri" data-act="re-senden" data-id="${esc(r.nummer)}">✉️ Senden …</button>`;
    else aktionen += `<button class="v2-btn" data-act="re-senden" data-id="${esc(r.nummer)}">✉️ Storno senden …</button>`;
    if (r.status === "offen" && (r.geld_cent ?? r.summe_cent) - (r.bezahlt_cent || 0) > 0) aktionen += `<button class="v2-btn ok" data-act="re-bezahlt-form" data-id="${esc(r.nummer)}">💶 Zahlung erfassen</button>`;
    if (r.art !== "storno" && r.ware_cent && !r.ware_erhalten && r.status !== "storniert") aktionen += `<button class="v2-btn ok" data-act="re-ware-form" data-id="${esc(r.nummer)}">📦 Ware erhalten …</button>`;
    if (r.ware_erhalten) aktionen += `<button class="v2-btn" data-act="re-ware-storno" data-id="${esc(r.nummer)}" title="Falsch erfassten Ware-Eingang zurücknehmen">↶ Ware-Eingang stornieren</button>`;
    if (r.status === "offen") aktionen += `<button class="v2-btn" data-act="re-storno" data-id="${esc(r.nummer)}">Stornieren …</button>`;
    if (d.naechste_mahnung) aktionen += `<button class="v2-btn danger" data-act="ma-form" data-id="${esc(r.nummer)}">⚠️ ${esc(d.naechste_mahnung.titel)} erstellen …</button>`;
    if (r.status === "offen" && r.art !== "storno" && !d.mahnverfahren && (d.mahnungen || []).length) aktionen += `<button class="v2-btn" data-act="re-mv-form" data-id="${esc(r.nummer)}" title="Gerichtliches Mahnverfahren ist eingeleitet (z. B. durch die Anwältin)">⚖️ Mahnverfahren eintragen …</button>`;
    if (r.status === "offen" && r.art !== "storno" && (d.mahnungen || []).length < 3) aktionen += `<button class="v2-btn" data-act="re-altmahn-form" data-id="${esc(r.nummer)}" title="Mahnung, die du schon selbst verschickt hast">📨 Mahnung vor LUNA erfassen …</button>`;
  }
  if (r.auftrag) aktionen += `<button class="v2-btn" data-act="ab-detail" data-id="${esc(r.auftrag)}">↩ Auftrag ${esc(r.auftrag)}</button>`;
  if (r.bezug) aktionen += `<button class="v2-btn" data-act="re-detail" data-id="${esc(r.bezug)}">↩ Original ${esc(r.bezug)}</button>`;
  if (r.storniert_durch) aktionen += `<button class="v2-btn" data-act="re-detail" data-id="${esc(r.storniert_durch)}">Storno ${esc(r.storniert_durch)}</button>`;
  const MSTUFE = { 1: "Mahnstufe 1", 2: "Mahnstufe 2", 3: "Mahnstufe 3" };   // Brief an den Kunden: „1./2./3. Mahnung“
  const mv = d.mahnverfahren;
  const dokumente = (d.dokumente || []).map(x => `<div class="v2-list-row"><span>📎</span><div class="grow"><b><a href="/api/crm/akte/${encodeURIComponent(x.id)}/datei" target="_blank" rel="noopener">${esc(x.titel)}</a></b><small>${esc(datumDe(x.datum))}${x.notiz ? " · " + esc(x.notiz) : ""}</small></div></div>`).join("");
  const mahnungen = (d.mahnungen || []).map(m => `<div class="v2-list-row"><span>⚠️</span><div class="grow"><b><a href="#" data-act="ma-detail" data-id="${esc(m.nummer)}">${esc(MSTUFE[m.stufe])} ${esc(m.nummer)}</a> · ${cent2eur(m.summe_cent)}</b><small>${esc(datumDe(m.datum))} · Frist ${esc(datumDe(m.frist))} · ${m.versendet_am ? "✉️ gesendet an " + esc((m.mail || {}).an || "") : "noch nicht gesendet"}</small></div>
    <a class="v2-btn sm" href="/api/finanzen/mahnungen/${encodeURIComponent(m.nummer)}/pdf" target="_blank" rel="noopener">📄</a><button class="v2-btn sm" data-act="bv-oeffnen" data-id="${esc(m.nummer)}" title="Belegverfolgung">🔗</button>${m.versendet_am ? "" : `<button class="v2-btn pri sm" data-act="ma-senden" data-id="${esc(m.nummer)}">✉️ Senden …</button>`}</div>`).join("");
  const zahlungen = (r.zahlungen || []).map((z, i) => `<div class="v2-list-row${z.storniert ? " v2-fin-storno" : ""}"><span>💶</span><div class="grow"><b>${cent2eur(z.betrag_cent)}${z.nebenforderung_cent ? " + " + cent2eur(z.nebenforderung_cent) + " Zinsen/Kosten" : ""}</b><small>${esc(datumDe(z.datum))}${z.zuordnung_jahr ? " · zugeordnet " + esc(z.zuordnung_jahr) : ""}${z.notiz ? " · " + esc(z.notiz) : ""}${z.storniert ? " · storniert: " + esc(z.storno_grund || "") : ""}</small></div>${!z.storniert && r.status !== "storniert" ? `<button class="v2-btn" data-act="re-zahlung-storno" data-id="${esc(r.nummer)}" data-val="${i}" title="Falsch erfasste Zahlung zurücknehmen">↶</button>` : ""}</div>`).join("");
  const lbl = { rechnung_entwurf: "Entwurf angelegt", rechnung_entwurf_geaendert: "Entwurf geändert", rechnung_festgeschrieben: "Festgeschrieben", rechnung_versendet: "Gesendet", rechnung_bezahlt: "Zahlung", rechnung_zahlung_storniert: "Zahlung storniert" };
  RE_DETAIL = d;
  const verlauf = (r.verlauf || []).slice().reverse().map(v => `<div class="v2-list-row"><div class="grow"><b>${esc(lbl[v.typ] || v.typ)}${v.mail_an ? " an " + esc(v.mail_an) : ""}${v.betrag_cent ? " " + cent2eur(v.betrag_cent) : ""}${v.storno ? " — storniert durch " + esc(v.storno) : ""}</b><small>${esc(zeit(v.ts))} · ${esc(v.von || "")}${v.felder ? " · " + esc(v.felder.join(", ")) : ""}${v.grund ? " · " + esc(v.grund) : ""}</small></div></div>`).join("");
  const artTxt = r.art === "anzahlung" ? "Vorkasse-Rechnung" : sm.abzuege ? "Schlussrechnung" : "Rechnung";
  const titel = entwurf ? `${r.art === "anzahlung" ? "Vorkasse-Entwurf" : sm.abzuege ? "Schlussrechnungs-Entwurf" : "Rechnungs-Entwurf"} · ${d.firma.name || r.firma}` : `${r.nummer} · ${artTxt} · ${d.firma.name || r.firma}`;
  const pzBox = entwurf && r.auftrag && r.art !== "anzahlung" ? `<div id="re-pz-box"></div>` : "";
  const altTab = `<h3>Positionen</h3><table class="v2-table"><thead><tr><th>#</th><th>Leistung</th><th style="text-align:right">Menge</th><th style="text-align:right">Gesamt</th></tr></thead><tbody>${pos}</tbody><tfoot>${fuss}</tfoot></table>`;
  const status = `<div class="v2-kv"><span>Status</span>${reBadge(r)}</div>
    ${!entwurf && r.art !== "storno" ? `<div class="v2-kv"><span>${r.ware_cent ? "Geld bezahlt / offen" : "Bezahlt / offen"}</span><b>${cent2eur(r.bezahlt_cent || 0)} / ${cent2eur((r.geld_cent ?? r.summe_cent) - (r.bezahlt_cent || 0))}</b></div>` : ""}
    ${(r.ware && r.ware.wert_cent) ? `<div class="v2-kv"><span>Ware 🎁</span><b>${cent2eur(r.ware.wert_cent)}${entwurf ? "" : r.ware_erhalten ? ` · ✓ erhalten ${esc(datumDe(r.ware_erhalten.datum))}` : " · noch nicht erhalten"}</b></div>` : ""}
    ${r.versendet_mail ? `<div class="v2-kv"><span>Gesendet</span><b>✉️ ${esc(r.versendet_mail.an)} · ${esc(zeit(r.versendet_am))}</b></div>` : ""}
    ${!entwurf || r.leistung_von || r.leistung_bis ? "" : `<div class="v2-kv"><span>Leistung</span><b class="v2-neg">— fehlt —</b></div>`}`;
  const seite = blBox("Status", status) + (entwurf ? "" : `<section class="v2-bl-box" id="bv-mini"></section>`)
    + (r.auftrag || r.angebot ? blBox("🎬 Konzept", `<button class="v2-btn sm" data-act="konzept" data-id="${esc(r.auftrag || r.angebot)}">Konzept-Mappe öffnen</button>`) : "")
    + blBox("Zahlungen", zahlungen) + blBox("Mahnungen", mahnungen)
    + (mv ? blBox("Mahnverfahren", `<div class="v2-list-row"><span>⚖️</span><div class="grow"><b>seit ${esc(datumDe(mv.datum))}${mv.durch ? " · " + esc(mv.durch) : ""}</b><small>${esc(mv.notiz || "")}${mv.notiz ? " · " : ""}Die Rechnung bleibt offen, bis gezahlt ist.</small></div></div>`) : "")
    + blBox("Dokumente", dokumente) + blBox("Verlauf", verlauf);
  openModal(titel, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    ${entwurf && !d.steuernummer ? `<div class="v2-msg err">Steuernummer fehlt in den Firmendaten — Festschreiben nicht möglich.</div>` : ""}
    ${belegAnsicht({ aktionen, haupt: `<div id="re-aktion-box"></div>${belegZweiAnsichten(reFormHtml(r, entwurf ? id : ""), d.blatt ? belegBlatt(d.blatt, { original: d.blatt.original_pdf ? `/api/finanzen/rechnungen/${encodeURIComponent(id)}/pdf` : "" }) : altTab)}${pzBox}`, seite })}`, true);
  const sperre = entwurf ? "" : r.art === "storno" ? "Stornorechnung – nur lesen." : r.status === "storniert" ? `Storniert${r.storniert_durch ? " durch " + r.storniert_durch : ""} – nur lesen.`
    : "Festgeschrieben – nur lesen. Korrekturen über „Stornieren …“ (danach entsteht ein neuer Entwurf).";
  await belegFormularFertig(sperre, r.ansprechpartner, entwurf && !sm.abzuege ? null : fuss);
  if (!entwurf) bvMini(r.nummer);
  if (entwurf && r.auftrag && r.art !== "anzahlung") rePzLaden(id);
}
// PROJEKTZEITEN Z2: Projektzeiten optional in der Rechnung (Standard aus; zusammengefasst + Stundenzettel-Anlage)
async function rePzLaden(eid) {
  const box = $("#re-pz-box"); if (!box) return;
  const d = await jget(`/api/finanzen/rechnungen/${encodeURIComponent(eid)}/projektzeiten`); if (!d) { box.innerHTML = ""; return; }
  const ez = (d.stundenzettel || {}).eintraege || [], akt = d.aktuell || {}, an = !!(akt.zeiten || []).length || !!(akt.km || []).length;
  if (!ez.length) { box.innerHTML = ""; return; }
  const gew = new Set(an ? akt.zeiten : ez.filter(x => !x.abgerechnet).map(x => x.id)), gewKm = new Set(an ? akt.km : []);
  const satz = (c) => c ? (c / 100).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "";
  const zeilen = ez.map(x => `<div class="v2-pz-zeile${x.abgerechnet ? " ab" : ""}"><label><input type="checkbox" class="pz-z" value="${esc(x.id)}" ${gew.has(x.id) && !x.abgerechnet ? "checked" : ""} ${x.abgerechnet ? "disabled" : ""}>
      <b>${esc(datumDe(x.datum))}</b> ${esc(x.von)}–${esc(x.bis)} · ${esc(dauerTxt(x.minuten))}${x.taetigkeit ? " · " + esc(x.taetigkeit) : ""}</label>
      ${x.km ? `<label class="pz-km-l"><input type="checkbox" class="pz-km" value="${esc(x.id)}" ${gewKm.has(x.id) && !x.km_abgerechnet ? "checked" : ""} ${x.km_abgerechnet ? "disabled" : ""}> 🚗 ${esc(String(x.km))} km</label>` : ""}
      ${x.abgerechnet ? `<span class="v2-badge ok">${esc(x.abgerechnet)}</span>` : ""}</div>`).join("");
  box.innerHTML = `<details class="v2-pz" ${an ? "open" : ""}><summary><b>⏱ Projektzeiten abrechnen</b> <small class="v2-sub">${an ? "auf dieser Rechnung" : "aus – Stunden sind sonst intern"}</small></summary>
    <div class="v2-form">${zeilen}
    <div class="v2-an-zeile"><label class="v2-feld"><small>Darstellung</small><select id="pz-darst" class="v2-inp"><option value="zusammen" ${akt.darstellung !== "einzeln" ? "selected" : ""}>Zusammengefasst + Stundenzettel als Anlage</option><option value="einzeln" ${akt.darstellung === "einzeln" ? "selected" : ""}>Einzeln (je Zeit eine Position)</option></select></label></div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Verkaufs-Stundensatz (€)</small><input id="pz-satz" class="v2-inp" inputmode="decimal" value="${esc(satz(akt.satz_cent || d.saetze.satz_cent))}" placeholder="z. B. 65,00"></label>
      <label class="v2-feld"><small>Verkaufs-km-Satz (€)</small><input id="pz-kmsatz" class="v2-inp" inputmode="decimal" value="${esc(satz(akt.km_satz_cent || d.saetze.km_satz_cent))}" placeholder="z. B. 0,50"></label></div>
    <small class="v2-sub">${d.saetze.quelle === "auftrag" ? "Satz aus diesem Auftrag." : d.saetze.quelle === "katalog" ? "Satz aus dem Katalog (Projektstunde)." : "Noch kein Satz: im Katalog „Projektstunde“ anlegen oder hier eintragen – er wird am Auftrag gemerkt."} Berechnete Stunden und km sind echte Einnahmen; die kalkulatorischen Kosten bleiben getrennt.</small>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="pz-speichern" data-id="${esc(eid)}">Übernehmen</button>${an ? `<button class="v2-btn" data-act="pz-aus" data-id="${esc(eid)}">Projektzeiten entfernen</button>` : ""}</div><div id="pz-msg" class="v2-msg"></div></div></details>`;
}
async function rePzSpeichern(eid, aus) {
  const werte = (k) => [...document.querySelectorAll(`#re-pz-box .${k}:checked`)].map(i => i.value);
  const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(eid)}/projektzeiten`, aus ? { zeiten: [], km: [] } :
    { zeiten: werte("pz-z"), km: werte("pz-km"), darstellung: $("#pz-darst").value, satz: $("#pz-satz").value.trim(), km_satz: $("#pz-kmsatz").value.trim() });
  if (!r || r.ok === false) return kundenMsg("pz-msg", (r && r.hinweis) || "Keine Verbindung.", false);
  return reDetail(eid, aus ? "Projektzeiten entfernt." : "Projektzeiten übernommen – bitte die PDF-Vorschau prüfen.");
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
    <div class="v2-kv"><span>Anhang</span><a href="/api/finanzen/rechnungen/${encodeURIComponent(nr)}/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>${mailBlock("rechnung", nr, v)}
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="re-senden-jetzt" data-id="${esc(nr)}" ${sendSperre(v)}>✉️ Jetzt senden</button><button class="v2-btn" data-act="re-box-zu">Abbrechen</button></div><div id="res-msg" class="v2-msg"></div></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
let RE_DETAIL = null;
async function reWareForm(nr) {
  const box = $("#re-aktion-box"); if (!box || !RE_DETAIL) return;
  const r = RE_DETAIL.rechnung, w = r.ware || {};
  if (!FIN_KAT) FIN_KAT = ((await jget("/api/finanzen/eigenbelege")) || {}).kategorien || { einnahme: {}, ausgabe: {} };
  const kat = Object.entries(FIN_KAT.ausgabe || {}).concat([["anlage", "Anlagegut > 800 € (Abschreibung)"]]);
  const std = w.wert_cent > 80000 ? "anlage" : "gwg";
  box.innerHTML = `<h3>📦 Ware erhalten (Barter)</h3><div class="v2-form" style="max-width:620px">
    <div class="v2-msg">Der Wert der Ware ist eine <b>Einnahme</b> (üblicher Ladenpreis, § 8 Abs. 2 EStG) und zählt zur Kleinunternehmer-Grenze. Nutzt du sie für Content, ist sie zugleich eine Anschaffung (bis 800 € sofort absetzbar). Leihgaben, die zurückgehen, sind keine Einnahme.</div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Erhalten am *</small><input id="rw-datum" type="date" value="${heuteIso()}"></label>
      <label class="v2-feld" style="grid-column: span 2"><small>Ware</small><input id="rw-text" value="${esc(w.text || "")}"></label></div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Wert laut Marke (€)</small><input id="rw-marke" inputmode="decimal" value="${esc(cent2feld(w.wert_cent || 0))}"></label>
      <label class="v2-feld"><small>Wert laut eigenem Nachweis (Shop-Preis, €)</small><input id="rw-nachweis" inputmode="decimal" placeholder="zählt, wenn angegeben"></label>
      <label class="v2-feld"><small>Verwendung</small><select id="rw-verw"><option value="content">für Content (betrieblich)</option><option value="privat">privat behalten</option><option value="leihgabe">Leihgabe – geht zurück</option></select></label></div>
    <div class="v2-an-zeile" id="rw-kat-zeile"><label class="v2-feld" style="grid-column: span 2"><small>Kategorie der Ware</small><select id="rw-kat">${kat.map(([k, l]) => `<option value="${esc(k)}" ${k === std ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>
      <label class="v2-feld" id="rw-nd-feld" ${std === "anlage" ? "" : "hidden"}><small>Nutzungsdauer (Jahre)</small><input id="rw-nd" type="number" min="1" max="50" placeholder="z. B. 7"></label></div>
    <label class="v2-feld"><small>Nachweise (Shop-Screenshot, Lieferschein, Mail der Marke) – optional, mehrere möglich</small><input id="rw-dateien" type="file" multiple accept=".pdf,image/*"></label>
    <div class="v2-card-actions"><button class="v2-btn ok" data-act="re-ware-speichern" data-id="${esc(nr)}">📦 Ware-Eingang buchen</button><button class="v2-btn" data-act="re-box-zu">Abbrechen</button></div><div id="rw-msg" class="v2-msg"></div></div>`;
  const sync = () => { const v = $("#rw-verw").value; $("#rw-kat-zeile").hidden = v !== "content"; $("#rw-nd-feld").hidden = $("#rw-kat").value !== "anlage"; };
  $("#rw-verw").addEventListener("change", sync); $("#rw-kat").addEventListener("change", sync); sync();
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
// Mahnung (Etappe 10): Vorschau mit Frist -> festschreiben (MA-Nummer, PDF) -> Versand mit Vorschau
async function maForm(nr, frist) {
  const box = $("#re-aktion-box"); if (!box) return;
  frist = frist || 7;
  const v = await jget(`/api/finanzen/rechnungen/${encodeURIComponent(nr)}/mahnung-vorschau?frist_tage=${frist}`);
  if (!v || !v.ok) { box.innerHTML = `<div class="v2-msg err">${esc((v && v.hinweis) || "Keine Vorschau möglich.")}</div>`; return; }
  const zins = (v.zins_abschnitte || []).map(a => `<tr><td><small>Verzugszinsen ${String(a.satz).replace(".", ",")} % p. a. auf ${cent2eur(a.offen_cent)}, ${datumDe(a.von)}–${datumDe(a.bis)} (${a.tage} Tage)</small></td><td style="text-align:right">${cent2eur(a.cent)}</td></tr>`).join("");
  box.innerHTML = `<h3>${esc(v.titel)} zu ${esc(nr)}</h3><div class="v2-form" style="max-width:560px">
    <label class="v2-feld"><small>Zahlungsfrist (Tage ab heute)</small><input id="ma-frist" type="number" min="1" max="60" value="${frist}"></label>
    <table class="v2-table"><tbody><tr><td>Offener Rechnungsbetrag (fällig ${esc(datumDe(v.faellig_am))})</td><td style="text-align:right">${cent2eur(v.offen_cent)}</td></tr>${zins}
      <tr><td>${esc(v.gebuehr_text)}</td><td style="text-align:right">${cent2eur(v.gebuehr_cent)}</td></tr>
      <tr><td><b>Gesamt, zahlbar bis ${esc(datumDe(v.frist))}</b></td><td style="text-align:right"><b>${cent2eur(v.summe_cent)}</b></td></tr></tbody></table>
    <small class="v2-sub">${v.verbraucher ? "Privatkunde: 5 Prozentpunkte über dem Basiszinssatz, 2,50 € Mahnkosten je Mahnung." : "Firmenkunde: 9 Prozentpunkte über dem Basiszinssatz, einmalig 40 € Verzugspauschale."} Danach weitere ${cent2eur(v.tageszins_cent)} Zinsen pro Tag.${v.stufe < 3 ? " Läuft die Frist ohne Zahlung ab, fragt LUNA dich per Telegram nach der nächsten Stufe." : ""}</small>
    <div class="v2-card-actions"><button class="v2-btn danger" data-act="ma-erstellen" data-id="${esc(nr)}">⚠️ ${esc(v.titel)} festschreiben</button><button class="v2-btn" data-act="re-box-zu">Abbrechen</button></div><div id="ma-msg" class="v2-msg"></div></div>`;
  $("#ma-frist").addEventListener("change", e => maForm(nr, Number(e.target.value) || 7));
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function maSendenVorschau(ma, erneut) {
  const box = $("#re-aktion-box"); if (!box) return;
  const v = await jget(`/api/finanzen/mahnungen/${encodeURIComponent(ma)}/versandvorschau`);
  if (!v) { box.innerHTML = emptyRow("Vorschau nicht verfügbar."); return; }
  box.innerHTML = `<h3>Mahnung ${esc(ma)} ${erneut ? "erneut " : ""}senden</h3>${erneut ? `<div class="v2-msg">Gleiche Mahnung noch einmal – Stufe und Frist bleiben, die Mail wird an der Mahnung vermerkt.</div>` : ""}<div class="v2-form">
    <div class="v2-kv"><span>Absender</span><b>${esc(v.absender)}</b></div>
    <label class="v2-feld"><small>An *</small><input id="mas-an" type="email" value="${esc(v.an || "")}"></label>
    <label class="v2-feld"><small>Betreff *</small><input id="mas-betreff" value="${esc(v.betreff)}"></label>
    <label class="v2-feld"><small>Text *</small><textarea id="mas-text" class="v2-inp" rows="8">${esc(v.text)}</textarea></label>
    <div class="v2-kv"><span>Anhang</span><a href="/api/finanzen/mahnungen/${encodeURIComponent(ma)}/pdf" target="_blank" rel="noopener">📎 ${esc(v.pdf)}</a></div>${mailBlock("mahnung", ma, v, erneut)}
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="ma-senden-jetzt" data-id="${esc(ma)}" ${erneut ? 'data-val="erneut"' : ""} ${sendSperre(v)}>✉️ Jetzt senden</button><button class="v2-btn" data-act="re-box-zu">Abbrechen</button></div><div id="mas-msg" class="v2-msg"></div></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
function reBezahltForm(nr) {
  const box = $("#re-aktion-box"); if (!box) return;
  box.innerHTML = `<h3>Zahlung erfassen</h3><div class="v2-form" style="max-width:420px">
    <div class="v2-an-zeile"><label class="v2-feld"><small>Zahlungsdatum</small><input id="rez-datum" type="date" value="${heuteIso()}"></label>
      <label class="v2-feld"><small>Betrag (leer = offener Rest)</small><input id="rez-betrag" inputmode="decimal" placeholder="z. B. 1.020,00"></label></div>
    <label class="v2-feld"><small>Notiz</small><input id="rez-notiz" placeholder="z. B. Überweisung comdirect"></label><div id="rez-zuord"></div>
    ${RE_DETAIL && (RE_DETAIL.mahnungen || []).length ? `<label class="v2-feld"><small>Zusätzlich gezahlte Verzugszinsen/Mahnkosten (€)</small><input id="rez-neben" inputmode="decimal" placeholder="z. B. 45,80"></label>` : ""}
    <div class="v2-card-actions"><button class="v2-btn ok" data-act="re-bezahlt" data-id="${esc(nr)}">💶 Zahlung buchen</button><button class="v2-btn" data-act="re-box-zu">Abbrechen</button></div><div id="rez-msg" class="v2-msg"></div></div>`;
  zehnTageVerdrahten("rez-datum", "rez-zuord");
}

/* =========================== Belege / Eingangsrechnungen (KUNDEN_FINANZEN Etappe 6) =========================== */
// Hochladen (Ziehen, Auswahl, Kamera) oder an LUNA weiterleiten -> lokal auslesen -> Vorschlag -> CEO bucht.
const BL_STATUS = { zu_pruefen: ["Zu prüfen", "wartet"], gebucht: ["Gebucht", "ok"], verworfen: ["Verworfen", "neutral"] };
const blBadge = (st) => { const [l, c] = BL_STATUS[st] || [st, "neutral"]; return `<span class="v2-badge ${c}">${esc(l)}</span>`; };
const TQ = { "xml": "E-Rechnung (XML)", "pdf-text": "PDF-Text", "ocr": "Texterkennung (Scan/Foto)", "mail": "Rechnung im Mailtext", "leer": "kein Text erkannt" };
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
  const rows = liste.map(b => `<tr class="klick" data-act="bl-detail" data-id="${esc(b.nummer)}"><td><b>${esc(b.nummer)}</b>${b.quelle === "mail" ? " ✉️" : ""}${b.e_rechnung ? " <small>E-Rechnung</small>" : ""}</td><td>${esc(b.lieferant || b.dateiname)}</td><td>${esc(datumDe(b.rechnungsdatum))}</td><td style="text-align:right${b.art === "einnahme" ? ";color:var(--v2-green)" : ""}">${b.betrag_cent != null ? (b.art === "einnahme" ? "+" : "") + cent2eur(b.betrag_cent) : "–"}</td><td>${b.art === "einnahme" ? "Gutschrift (Einnahme)" : b.aufgeteilt > 1 ? `aufgeteilt (${b.aufgeteilt})${b.teils_privat ? " · teils privat" : ""}` : esc(BL_KAT[b.kategorie] || "")}</td><td>${blBadge(b.status)}${b.bezahlt_am ? " 💶" : b.bezahlt_cent ? " <small>teilw. bezahlt</small>" : ""}</td></tr>`).join("");
  const upload = `<div class="v2-bl-drop" id="bl-drop"><b>Rechnungen hierher ziehen</b><small>PDF, E-Rechnung (XML), Foto, gespeicherte Mails (.eml/.mbox) · bis 15 MB · mehrere auf einmal</small>
    <div class="v2-card-actions" style="justify-content:center"><label class="v2-btn pri">📄 Dateien wählen<input id="bl-datei" type="file" multiple accept=".pdf,.xml,.eml,.mbox,message/rfc822,image/*" hidden></label>
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
// Etappe 27: Erzielt-Zeitraeume einer Plattform-Auszahlung (Information; die EUeR zaehlt den Bankeingang)
const datumKurz = (iso) => iso ? `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}` : "";
const fremdTxt = (c, w) => `${(Number(c || 0) / 100).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${w === "USD" ? "$" : esc(w || "")}`;
function blPlattform(nr, b, f) {
  const a = b.plattform, eur = f && f.betrag_cent;
  const summe = a ? a.posten.reduce((s, p) => s + p.betrag_cent, 0) : 0;
  const zeilen = a ? a.posten.map(p => `<tr><td>${esc(datumKurz(p.von))} – ${esc(datumKurz(p.bis))}</td><td class="num">${fremdTxt(p.betrag_cent, a.waehrung)}</td><td class="num">${eur ? cent2eur(Math.round(eur * p.betrag_cent / (summe || 1))) : "–"}</td><td><small class="v2-sub">${esc(p.referenz || p.text || "")}</small></td></tr>`).join("") : "";
  const quelle = a ? (a.quelle === "hand" ? "von Hand erfasst" : "aus dem Meta-PDF gelesen") : "";
  const form = `<details class="v2-bl-posten-form" ${a ? "" : "open"}><summary>${a ? "Zeiträume von Hand korrigieren" : "Zeiträume eintragen"}</summary><div class="v2-form">
      <small class="v2-sub">Je Zeile ein Posten: <b>von–bis Betrag</b>, z. B. <code>01.11.2025-30.11.2025 98,87</code>. Maßgeblich ist der Zahlungsbeleg von Meta.</small>
      <textarea id="bl-posten" rows="4" class="v2-inp" placeholder="01.11.2025-30.11.2025 98,87&#10;01.12.2025-31.12.2025 47,29">${a && a.quelle === "hand" ? esc(a.posten.map(p => `${datumKurz(p.von)}-${datumKurz(p.bis)} ${(p.betrag_cent / 100).toFixed(2).replace(".", ",")}`).join("\n")) : ""}</textarea>
      <div class="v2-an-zeile"><label class="v2-feld"><small>Zahlungs-ID</small><input id="bl-posten-id" class="v2-inp" value="${esc((a && a.zahlungs_id) || (f && f.rechnungsnummer) || "")}"></label>
      <label class="v2-feld"><small>Währung</small><input id="bl-posten-wg" class="v2-inp" value="${esc((a && a.waehrung) || "USD")}" maxlength="3"></label></div>
      <button class="v2-btn sm" data-act="bl-posten" data-id="${esc(nr)}">Zeiträume speichern</button></div></details>`;
  return `<h3>Erzielt-Zeiträume</h3>${a ? `<div class="v2-tab-scroll"><table class="v2-table"><thead><tr><th>Erzielt</th><th class="num">Betrag</th><th class="num">anteilig €</th><th>Referenz</th></tr></thead><tbody>${zeilen}</tbody></table></div>
    <small class="v2-sub">${quelle} · Summe ${fremdTxt(summe, a.waehrung)}${a.betrag_cent && a.betrag_cent !== summe ? ` · <b style="color:var(--v2-red)">passt nicht zur Auszahlung ${fremdTxt(a.betrag_cent, a.waehrung)}</b>` : ""}. Nur Information — die EÜR zählt den Bankeingang am Zahlungstag.</small>` : `<small class="v2-sub">Für diese Einnahme sind keine Zeiträume bekannt.</small>`}${form}`;
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
  const lief = (d.lieferanten || []).map(l => `<option value="${esc(firmaOption(l))}">`).join("");
  const fv = d.firma_vorschlag || {};
  const liefWert = fv.nummer ? firmaOption(fv) : w("lieferant");
  const gesperrt = b.status === "verworfen" ? "disabled" : "";
  const lbl = { eingang_angelegt: "Eingegangen", eingang_vorschlag: "Vorschlag", eingang_gebucht: "Gebucht", eingang_bezahlt: "Zahlung", eingang_zahlung_storniert: "Zahlung storniert", eingang_verworfen: "Verworfen" };
  const rest = f ? f.betrag_cent - (b.bezahlt_cent || 0) : 0;
  const zahlungen = (b.zahlungen || []).map((z, i) => `<div class="v2-list-row${z.storniert ? " v2-fin-storno" : ""}"><span>💶</span><div class="grow"><b>${cent2eur(z.betrag_cent)}</b><small>${esc(datumDe(z.datum))}${z.zuordnung_jahr ? " · zugeordnet " + esc(z.zuordnung_jahr) : ""}${z.notiz ? " · " + esc(z.notiz) : ""}${z.storniert ? " · storniert: " + esc(z.storno_grund || "") : ""}</small></div>${!z.storniert ? `<button class="v2-btn" data-act="bl-zahlung-storno" data-id="${esc(nr)}" data-val="${i}" title="Falsch erfasste Zahlung zurücknehmen">↶</button>` : ""}</div>`).join("");
  const verlauf = (b.verlauf || []).slice().reverse().map(x => `<div class="v2-list-row"><div class="grow"><b>${esc(lbl[x.typ] || x.typ)}${x.quelle ? " (" + esc(x.quelle) + ")" : ""}${x.datum ? " " + esc(datumDe(x.datum)) : ""}</b><small>${esc(zeit(x.ts))} · ${esc(x.von || "")}${x.grund ? " · " + esc(x.grund) : ""}</small></div></div>`).join("");
  openModal(`${nr} · ${b.dateiname}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}" style="white-space:pre-wrap">${esc(meldung)}</div>` : ""}
    <div class="v2-an-detail"><div>
      ${vorschau}
      ${(b.belege || []).length > 1 ? `<h3>Weitere Dateien</h3>${b.belege.slice(1).map((x, i) => `<div class="v2-list-row"><span>${x.rolle === "zahlungsnachweis" ? "🧾" : "✉️"}</span><div class="grow"><a href="${src}?i=${i + 1}" target="_blank" rel="noopener">${esc(x.name || (x.pfad || "").split("/").pop().slice(17))}</a><small>${x.rolle === "zahlungsnachweis" ? "Zahlungsnachweis" : "Original-Mail (unverändert)"}</small></div></div>`).join("")}` : ""}
      <div class="v2-kv"><span>Eingang</span><b>${esc(zeit(b.eingegangen))} · ${b.quelle === "mail" ? "per Mail" : "Upload"} · ${esc(TQ[b.text_quelle] || b.text_quelle)}</b></div>
      ${ein ? blPlattform(nr, b, f) : ""}
      <h3>Zweck / Begründung</h3><div class="v2-form"><textarea id="bl-zweck" rows="2" class="v2-inp" maxlength="500" placeholder="Wofür wurde das gekauft? (betriebliche Veranlassung – z. B. „Schuhe für den Medizincheck-Dreh im Athleticum“)">${esc(b.zweck || "")}</textarea>
        <button class="v2-btn sm" data-act="bl-zweck" data-id="${esc(nr)}">Zweck speichern</button><small class="v2-sub">Steht mit im Export für den Steuerberater. Schreibst du beim Weiterleiten etwas über die Mail, übernimmt LUNA es automatisch.</small></div>
      <h3>Verlauf</h3>${verlauf}
    </div><div>
      <div class="v2-kv"><span>Status</span>${blBadge(b.status)}${b.bezahlt_am ? ` <span class="v2-badge ok">bezahlt ${esc(datumDe(b.bezahlt_am))}</span>` : b.bezahlt_cent ? ` <span class="v2-badge wartet">teilweise bezahlt · offen ${esc(cent2eur(rest))}</span>` : ""}</div>
      ${!f ? `<div class="v2-kv"><span>Vorschlag von</span><b>${esc(quelle)}${kiLaeuft ? " · KI liest noch …" : ""}</b></div>` : ""}
      ${kiLaeuft ? `<button class="v2-btn" data-act="bl-detail" data-id="${esc(nr)}">🔄 KI-Vorschlag abholen</button>` : ""}
      ${!f && (v.hinweise || []).length ? `<div class="v2-msg" style="margin:8px 0">${v.hinweise.map(h => "⚠️ " + esc(h)).join("<br>")}</div>` : ""}
      ${!f && v.kurs ? `<div class="v2-msg" style="margin:8px 0">💱 Euro-Betrag nach <b>EZB-Referenzkurs</b> vom ${esc(datumDe(v.kurs.tag))} vorgeschlagen: ${esc(v.betrag_fremd || "")} ${esc(v.kurs.waehrung)} ÷ ${esc(String(v.kurs.kurs).replace(".", ","))} = <b>${esc(v.betrag)} €</b>. Weicht die Abbuchung laut Kontoauszug ab, einfach den Betrag ändern.</div>` : ""}
      ${!f && v.waehrung && v.waehrung !== "EUR" && !v.kurs ? `<div class="v2-msg err" style="margin:8px 0">Betrag in ${esc(v.waehrung)}: ${esc(v.betrag_fremd || "?")}. Bitte den <b>Euro-Betrag</b> eintragen, der auf dem Konto angekommen bzw. abgebucht worden ist (Kontoauszug) — nur der zählt in der EÜR.</div>` : ""}
      <h3>${f ? "Gebucht (korrigierbar)" : "Prüfen & buchen"}</h3><div class="v2-form">
        <label class="v2-feld"><small>Art *</small><select id="bl-art" ${gesperrt}><option value="ausgabe" ${ein ? "" : "selected"}>Ausgabe — wir zahlen (Eingangsrechnung)</option><option value="einnahme" ${ein ? "selected" : ""}>Einnahme — wir bekommen Geld (Gutschrift, z. B. Facebook-Monetarisierung)</option></select></label>
        <label class="v2-feld"><small id="bl-lief-lbl">${ein ? "Von (Aussteller der Gutschrift) *" : "Lieferant *"}</small><input id="bl-lieferant" list="bl-lieferanten" value="${esc(liefWert)}" ${gesperrt}><datalist id="bl-lieferanten">${lief}</datalist>
          <small class="v2-sub">${fv.nummer ? `Stammdaten: <b>${esc(fv.anzeige)}</b>${f ? "" : " (vorgeschlagen)"} – anderen aus der Liste wählen oder Namen tippen` : "Kein Treffer in den Stammdaten – beim Buchen wird der Lieferant mit eigener Nummer angelegt"}</small></label>
        <div class="v2-an-zeile"><label class="v2-feld"><small>Rechnungsnummer</small><input id="bl-nr" value="${esc(w("rechnungsnummer"))}" ${gesperrt}></label>
          <label class="v2-feld"><small>Rechnungsdatum *</small><input id="bl-datum" type="date" value="${esc(w("rechnungsdatum"))}" ${gesperrt}></label>
          <label class="v2-feld"><small>Fällig am</small><input id="bl-faellig" type="date" value="${esc(w("faellig_am"))}" ${gesperrt}></label></div>
        <div class="v2-an-zeile"><label class="v2-feld"><small>Betrag brutto (€) *</small><input id="bl-betrag" inputmode="decimal" value="${esc(w("betrag"))}" ${gesperrt}></label>
          <label class="v2-feld" style="grid-column: span 2"><small>Kategorie (EÜR) *</small><select id="bl-kat" ${gesperrt}><option value="">— wählen —</option>${katOpt}</select></label></div>
        <label class="v2-feld" id="bl-nd-feld" ${w("kategorie") === "anlage" ? "" : "hidden"}><small>Nutzungsdauer in Jahren * (Computer/Software: 1 = sofort voll absetzbar · Foto/Video-Technik: 7)</small><input id="bl-nd" type="number" min="1" max="50" value="${esc(String((f && f.nutzungsdauer_jahre) || ""))}" ${gesperrt}></label>
        <label class="v2-feld"><small>Leistung / was wurde gekauft</small><input id="bl-leistung" value="${esc(w("leistung"))}" ${gesperrt}></label>
        <div id="bl-pos-wrap" ${ein ? "hidden" : ""}><label class="v2-modlbl"><input type="checkbox" id="bl-pos-an" ${blPosStart(f, v).length > 1 ? "checked" : ""} ${gesperrt}> In Positionen aufteilen (z. B. private Artikel herausnehmen)</label>
          <div id="bl-pos-block"><div class="v2-bl-pos v2-bl-pos-kopf"><span>Position</span><span>Betrag brutto</span><span>Kategorie</span><span>ND</span><span></span></div>
          <div id="bl-pos">${blPosStart(f, v).map(blPosZeile).join("")}</div>
          <div class="v2-card-actions"><button class="v2-btn sm" data-act="bl-pos-neu">+ Position</button><button class="v2-btn sm" data-act="bl-pos-diff">Differenz als Position</button></div>
          <div id="bl-pos-summe" class="v2-sub"></div></div></div>
        <label class="v2-feld"><small>Notiz</small><input id="bl-notiz" value="${esc(f ? f.notiz || "" : v.kurs_notiz || (v.betrag_fremd ? `${v.betrag_fremd} ${v.waehrung} laut Beleg` : ""))}" ${gesperrt}></label>
        ${b.status !== "verworfen" ? `<div class="v2-card-actions"><button class="v2-btn pri" data-act="bl-buchen" data-id="${esc(nr)}">✔ ${f ? "Korrektur buchen" : "Buchen"}</button>
          ${f && rest !== 0 ? `<button class="v2-btn ok" data-act="bl-bezahlt-form" data-id="${esc(nr)}">💶 ${ein ? "Geldeingang erfassen" : "Zahlung erfassen"}</button>` : ""}
          ${!f ? `<button class="v2-btn" data-act="bl-verwerfen" data-id="${esc(nr)}">Kein Beleg / verwerfen</button><button class="v2-btn" data-act="bl-nachweis" data-id="${esc(nr)}">🧾 Ist Zahlungsnachweis zu …</button>` : ""}</div>` : `<div class="v2-msg">Verworfen: ${esc(b.grund || "")}</div>`}
        <div id="bl-form-msg" class="v2-msg"></div></div>
      <div id="bl-aktion-box"></div>
      ${zahlungen ? `<h3>Zahlungen</h3>${zahlungen}` : ""}
      ${ein ? `<div class="v2-msg" style="margin:8px 0">Gutschrift = Einnahme: zählt zum Umsatz und zur Kleinunternehmer-Grenze. Achtung: Weist die Gutschrift <b>Umsatzsteuer</b> aus, kannst du sie dem Finanzamt schulden (§ 14c UStG), solange du nicht widersprichst — dann dem Aussteller widersprechen und im Konto „Kleinunternehmer“ hinterlegen.</div>` : ""}
      <small class="v2-sub">Kleinunternehmer: Der Bruttobetrag ist die Ausgabe (kein Vorsteuerabzug). Über 800 € ist es kein geringwertiges Wirtschaftsgut, sondern ein Anlagegut (Abschreibung). Das Original bleibt unverändert archiviert.</small>
    </div></div>`, true);
  const kt = $("#bl-kat"); if (kt) kt.addEventListener("change", () => { const nd = $("#bl-nd-feld"); if (nd) nd.hidden = kt.value !== "anlage" || blPosAktiv(); });
  const pw = $("#bl-pos-wrap"); if (pw) { pw.addEventListener("input", blPosSync); pw.addEventListener("change", blPosSync); }
  const bb = $("#bl-betrag"); if (bb) bb.addEventListener("input", blPosSync);
  blPosSync();
  const at = $("#bl-art"); if (at && kt) at.addEventListener("change", () => {              // Kategorien je Art umschalten
    const e = at.value === "einnahme", liste = e ? BL_KAT_EIN : BL_KAT;
    const pw2 = $("#bl-pos-wrap"); if (pw2) { pw2.hidden = e; if (e) $("#bl-pos-an").checked = false; blPosSync(); }
    kt.innerHTML = (e ? "" : `<option value="">— wählen —</option>`) + Object.entries(liste).map(([k, l]) => `<option value="${esc(k)}">${esc(l)}</option>`).join("");
    $("#bl-lief-lbl").textContent = e ? "Von (Aussteller der Gutschrift) *" : "Lieferant *"; kt.dispatchEvent(new Event("change")); });
}
// Etappe 11: Positionen einer Rechnung -- einzeln kategorisieren, private Artikel herausnehmen
const blPosStart = (f, v) => f && f.aufteilung && f.aufteilung.length ? f.aufteilung.map(t => ({ text: t.text, betrag: cent2feld(t.betrag_cent), kategorie: t.kategorie, nutzungsdauer_jahre: t.nutzungsdauer_jahre }))
  : !f && (v.positionen || []).length ? v.positionen.map(p => ({ text: p.text, betrag: p.betrag, kategorie: p.kategorie || v.kategorie || "" })) : [];
function blPosZeile(p) {
  p = p || {};
  const opt = Object.entries(BL_KAT).map(([k, l]) => `<option value="${esc(k)}" ${p.kategorie === k ? "selected" : ""}>${esc(l)}</option>`).join("");
  return `<div class="v2-bl-pos"><input class="bp-text" value="${esc(p.text || "")}" placeholder="Artikel / Leistung"><input class="bp-betrag" inputmode="decimal" value="${esc(p.betrag || "")}" placeholder="0,00">
    <select class="bp-kat"><option value="">— Kategorie —</option><option value="privat" ${p.kategorie === "privat" ? "selected" : ""}>🏠 privat – nicht absetzbar</option>${opt}</select>
    <input class="bp-nd" type="number" min="1" max="50" value="${esc(String(p.nutzungsdauer_jahre || ""))}" placeholder="Jahre" title="Nutzungsdauer (nur Anlagegut)"><button class="v2-icon" data-act="bl-pos-weg" title="Position entfernen">✕</button></div>`;
}
const blPosAktiv = () => !!($("#bl-pos-an") || {}).checked && !($("#bl-pos-wrap") || {}).hidden;
const blPosWerte = () => [...document.querySelectorAll("#bl-pos .v2-bl-pos")].map(z => ({ text: $(".bp-text", z).value.trim(), betrag: $(".bp-betrag", z).value.trim(), kategorie: $(".bp-kat", z).value, nutzungsdauer_jahre: $(".bp-nd", z).value }));
const feld2cent = (s) => {                         // „1.234,56“, „241,80“ und „241.80“ (Punkt als Dezimalzeichen)
  let t = String(s || "").trim().replace(/[€\s]/g, "");
  t = /^-?\d+\.\d{1,2}$/.test(t) ? t : t.replace(/\./g, "").replace(",", ".");
  const n = Number(t); return t && isFinite(n) ? Math.round(n * 100) : 0;
};
function blPosSync() {
  const an = blPosAktiv(), blk = $("#bl-pos-block"); if (!blk) return;
  blk.hidden = !an;
  const katFeld = $("#bl-kat") && $("#bl-kat").closest("label"); if (katFeld) katFeld.hidden = an;
  const nd = $("#bl-nd-feld"); if (nd) nd.hidden = an || ($("#bl-kat") || {}).value !== "anlage";
  document.querySelectorAll("#bl-pos .v2-bl-pos").forEach(z => { $(".bp-nd", z).style.visibility = $(".bp-kat", z).value === "anlage" ? "visible" : "hidden"; });
  if (!an) return;
  const w = blPosWerte(), summe = w.reduce((x, p) => x + feld2cent(p.betrag), 0), gesamt = feld2cent(($("#bl-betrag") || {}).value);
  const privat = w.filter(p => p.kategorie === "privat").reduce((x, p) => x + feld2cent(p.betrag), 0), diff = gesamt - summe;
  $("#bl-pos-summe").innerHTML = `Summe Positionen <b>${cent2eur(summe)}</b> · Rechnungsbetrag <b>${cent2eur(gesamt)}</b>${diff ? ` · <span style="color:var(--v2-red)">Differenz ${cent2eur(diff)}</span> (z. B. Versand, Rabatt)` : " · ✓ passt"}${privat ? ` · davon privat ${cent2eur(privat)} → absetzbar ${cent2eur(summe - privat)}` : ""}`;
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
  const lf = firmaAusText($("#bl-lieferant").value);
  const felder = { lieferant: lf.name, lieferant_firma: lf.firma, rechnungsnummer: $("#bl-nr").value.trim(), rechnungsdatum: $("#bl-datum").value, faellig_am: $("#bl-faellig").value,
    betrag: $("#bl-betrag").value.trim(), kategorie: $("#bl-kat").value, leistung: $("#bl-leistung").value.trim(), notiz: $("#bl-notiz").value.trim(), trotz_doppelt: !!trotz, art: $("#bl-art").value,
    nutzungsdauer_jahre: $("#bl-kat").value === "anlage" ? $("#bl-nd").value : "" };
  if (blPosAktiv()) felder.aufteilung = blPosWerte().filter(p => p.text || p.betrag);
  const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(nr)}/buchen`, { felder });
  if (!r) return kundenMsg("bl-form-msg", "Keine Verbindung zum Server.", false);
  if (!r.ok && /schon als/.test(r.hinweis || "") && confirm(r.hinweis + "\n\nTrotzdem buchen?")) return blBuchen(nr, true);
  if (!r.ok) return kundenMsg("bl-form-msg", r.hinweis || "Fehler.", false);
  if (AKTIV === "belege") renderBelege();
  return blDetail(nr, `Gebucht: ${r.felder.lieferant} · ${cent2eur(r.felder.betrag_cent)} · ${r.felder.art === "einnahme" ? "Einnahme (Gutschrift)" : BL_KAT[r.felder.kategorie] || r.felder.kategorie}`);
}

/* =========================== Finanzen (KUNDEN_FINANZEN Etappe 7) =========================== */
// Übersicht über alles (Kennzahlen, Monatsverlauf, offene Posten, Pipeline, To-dos), Journal nach Zahlungsdatum,
// EÜR, Anlageverzeichnis und Buchungen ohne Beleg (Eigenbelege, z. B. Plattform-Auszahlungen).
let FIN_JAHR = 0, FIN_KAT = null, FIN_ZEIT = "jahr";
const FIN_ACT = { rechnung: "re-detail", beleg: "bl-detail", eigenbeleg: "eb-detail", afa: "bl-detail", ware: "re-detail" };
const FIN_MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];
const finZeitName = (z, j) => z === "jahr" ? String(j) : z[0] === "q" ? `Q${z[1]} ${j}` : `${FIN_MONATE[Number(z.slice(1)) - 1]} ${j}`;
function finDelta(jetzt, vor, weniger_ist_gut) {
  if (!vor) return null; const p = Math.round((jetzt - vor) / Math.abs(vor) * 100);
  return { up: weniger_ist_gut ? p <= 0 : p >= 0, text: (p >= 0 ? "+" : "") + p + " % zum Vorjahr" };
}
// Kennzahl-Kachel, die per Klick die Buchungen dahinter zeigt (Drill-down, Etappe 8)
function finKpi(title, big, delta, sub, drill) {
  const d = delta ? `<span class="delta ${delta.up ? "up" : "down"}">${delta.up ? "↗" : "↘"} ${esc(delta.text)}</span>` : "";
  return `<div class="v2-tile klick" data-act="fin-drill" data-val="${esc(drill)}" title="Klicken: Buchungen dahinter anzeigen"><div class="v2-tile-h"><span class="t">${esc(title)}</span><span class="v2-tile-tools"><span class="dots">›</span></span></div><div class="v2-kpi">${esc(big)} ${d}</div>${sub ? `<div class="v2-sub">${esc(sub)}</div>` : ""}</div>`;
}
RENDER.finanzen = renderFinanzen;
async function renderFinanzen(meldung) {
  const sub = SUBTAB.finanzen || "uebersicht";
  const u = await jget(`/api/finanzen/uebersicht?zeitraum=${FIN_ZEIT}` + (FIN_JAHR ? "&jahr=" + FIN_JAHR : ""));
  if (!u) { $("#v2-app").innerHTML = secHead("Finanzen") + emptyRow("Finanzen nicht erreichbar (Modul „Finanzen“ nötig)."); return; }
  FIN_JAHR = u.jahr;
  const jahrWahl = `<select id="fin-jahr" class="v2-inp" style="width:auto">${u.jahre.map(j => `<option ${j === u.jahr ? "selected" : ""}>${j}</option>`).join("")}</select>`;
  const zeitWahl = sub === "uebersicht" ? `<select id="fin-zeit" class="v2-inp" style="width:auto"><option value="jahr">Ganzes Jahr</option>${[1, 2, 3, 4].map(q => `<option value="q${q}">Q${q}</option>`).join("")}${FIN_MONATE.map((m, i) => `<option value="m${String(i + 1).padStart(2, "0")}">${m}</option>`).join("")}</select>` : "";
  const body = sub === "journal" ? await finJournal(u.jahr) : sub === "euer" ? await finEuer(u.jahr) : sub === "anlagen" ? await finAnlagen(u.jahr) : sub === "abschluss" ? await finAbschluss(u.jahr) : sub === "abos" ? await finAbos() : await finUebersicht(u);
  $("#v2-app").innerHTML = secHead("Finanzen " + (sub === "uebersicht" ? finZeitName(u.zeitraum, u.jahr) : u.jahr), `${jahrWahl}${zeitWahl}<button class="v2-btn" data-act="eb-neu" data-val="ausgabe">− Ausgabe ohne Beleg</button><button class="v2-btn pri" data-act="eb-neu" data-val="einnahme">+ Einnahme ohne Rechnung</button>`)
    + tabs("finanzen", [["uebersicht", "Übersicht"], ["journal", "Journal"], ["euer", "EÜR"], ["anlagen", "Anlagen"], ["abos", "Abos"], ["abschluss", "Jahresabschluss"]])
    + (meldung ? `<div class="v2-msg ok" style="margin-bottom:12px">${esc(meldung)}</div>` : "") + `<div class="v2-grid">${body}</div>`;
  $("#fin-jahr").addEventListener("change", e => { FIN_JAHR = Number(e.target.value); renderFinanzen(); });
  const zw = $("#fin-zeit"); if (zw) { zw.value = u.zeitraum; zw.addEventListener("change", e => { FIN_ZEIT = e.target.value; renderFinanzen(); }); }
}
/* ---- Abos / wiederkehrende Zahlungen (KUNDEN_FINANZEN Etappe 15) ---- */
let ABOS = { abos: [], turnus: {}, kategorien: { ausgabe: {}, einnahme: {} }, firmen: [], summe: {} };
async function finAbos() {
  ABOS = await jget("/api/finanzen/abos") || ABOS;
  const a = ABOS.abos || [], aktiv = a.filter(x => x.status === "aktiv");
  const rows = a.map(x => `<tr class="klick${x.status === "aktiv" ? "" : " blass"}" data-act="abo-detail" data-id="${esc(x.nummer)}"><td><b>${esc(x.nummer)}</b></td><td>${esc(x.bezeichnung)}<br><small class="v2-sub">${esc(x.firma_nr)} · ${esc(x.firma_name)}</small></td>
    <td>${esc(x.turnus_text)}${x.auto_buchen && !x.beleg_per_mail ? ` <span class="v2-badge ok" title="wird automatisch gebucht">auto</span>` : ""}${x.beleg_per_mail ? ` <span class="v2-badge neutral" title="Beleg kommt per Mail">✉️</span>` : ""}</td>
    <td style="text-align:right">${esc(cent2eur(x.betrag_cent))}</td><td style="text-align:right">${esc(cent2eur(x.monatlich_cent))}</td>
    <td>${x.status === "aktiv" ? esc(datumDe(x.naechste)) : `<span class="v2-badge neutral">beendet</span>`}${(x.offen || []).length ? ` <span class="v2-badge wartet">${x.offen.length} offen</span>` : ""}</td></tr>`).join("");
  return `${kpiTile("Aktive Abos", String(aktiv.length), null, "wiederkehrende Zahlungen")}${kpiTile("Kosten je Monat", cent2eur((ABOS.summe || {}).ausgaben_monat_cent || 0), null, "Jahresabos anteilig")}${kpiTile("Kosten je Jahr", cent2eur((ABOS.summe || {}).ausgaben_jahr_cent || 0), null, "hochgerechnet")}
    ${tile("Abos", `<div class="v2-card-actions" style="margin-bottom:8px"><button class="v2-btn pri" data-act="abo-neu">+ Abo anlegen</button></div>` + (rows ? `<div class="v2-tab-scroll"><table class="v2-table"><thead><tr><th>Nr.</th><th>Abo</th><th>Turnus</th><th style="text-align:right">Betrag</th><th style="text-align:right">je Monat</th><th>Nächste Fälligkeit</th></tr></thead><tbody>${rows}</tbody></table></div>` : emptyRow("Noch kein Abo angelegt.")), "w12")}`;
}
async function aboForm(nr, vorlage) {
  if (!(ABOS.firmen || []).length) ABOS = await jget("/api/finanzen/abos") || ABOS;
  const x = nr ? (ABOS.abos || []).find(a => a.nummer === nr) : (vorlage || {});
  const art = x.art || "ausgabe", kat = Object.entries((ABOS.kategorien || {})[art] || {});
  const firma = x.firma ? (ABOS.firmen || []).find(f => f.nummer === x.firma || f.anzeige === x.firma) : null;
  openModal(nr ? `${nr} bearbeiten` : "Neues Abo", `<div class="v2-form" style="max-width:680px">
    <label class="v2-feld"><small>Bezeichnung *</small><input id="abo-bez" value="${esc(x.bezeichnung || "")}" placeholder="z. B. iCloud+ 2 TB"></label>
    <label class="v2-feld"><small>Firma (Stammdaten) *</small><input id="abo-firma" list="abo-firmen" value="${esc(firma ? firmaOption(firma) : "")}" placeholder="L-… wählen"><datalist id="abo-firmen">${(ABOS.firmen || []).map(f => `<option value="${esc(firmaOption(f))}">`).join("")}</datalist></label>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Art</small><select id="abo-art"><option value="ausgabe">Ausgabe</option><option value="einnahme" ${art === "einnahme" ? "selected" : ""}>Einnahme</option></select></label>
      <label class="v2-feld"><small>Betrag (€) *</small><input id="abo-betrag" inputmode="decimal" value="${x.betrag_cent ? esc(cent2feld(x.betrag_cent)) : ""}"></label>
      <label class="v2-feld"><small>Kategorie *</small><select id="abo-kat"><option value="">— wählen —</option>${kat.map(([k, l]) => `<option value="${esc(k)}" ${x.kategorie === k ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label></div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Turnus *</small><select id="abo-turnus">${Object.entries(ABOS.turnus || {}).map(([k, l]) => `<option value="${esc(k)}" ${(x.turnus || "monatlich") === k ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>
      <label class="v2-feld"><small>Erste Fälligkeit *</small><input id="abo-start" type="date" value="${esc(x.start || heuteIso())}" ${nr ? "disabled" : ""}></label>
      <label class="v2-feld"><small>Ende / Vertragsende</small><input id="abo-ende" type="date" value="${esc(x.ende || "")}"></label></div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Kündigungsfrist (Tage)</small><input id="abo-frist" type="number" min="0" max="730" value="${x.kuendigungsfrist_tage == null ? "" : esc(String(x.kuendigungsfrist_tage))}"></label>
      <label class="v2-feld"><small>Zahlungsweg</small><input id="abo-weg" value="${esc(x.zahlungsweg || (firma && firma.zahlungsweg) || "")}"></label>
      <label class="v2-feld"><small>Vertrags-/Kundennummer</small><input id="abo-vnr" value="${esc(x.vertragsnummer || "")}"></label></div>
    <label class="v2-modlbl"><input type="checkbox" id="abo-mail" ${x.beleg_per_mail ? "checked" : ""}> Beleg kommt per Mail (LUNA wartet auf den Beleg und bucht nicht selbst)</label>
    <label class="v2-modlbl"><input type="checkbox" id="abo-auto" ${x.auto_buchen ? "checked" : ""}> Automatisch buchen, wenn fällig (ohne Rückfrage; nur ohne Mail-Beleg)</label>
    <label class="v2-feld"><small>Notiz</small><input id="abo-notiz" value="${esc(x.notiz || "")}"></label>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="abo-speichern" data-id="${esc(nr || "")}">✔ ${nr ? "Speichern" : "Abo anlegen"}</button><button class="v2-btn" data-modal-close>Abbrechen</button></div><div id="abo-msg" class="v2-msg"></div></div>`, false);
  $("#abo-art").addEventListener("change", e => { const k = Object.entries((ABOS.kategorien || {})[e.target.value] || {}); $("#abo-kat").innerHTML = `<option value="">— wählen —</option>` + k.map(([id, l]) => `<option value="${esc(id)}">${esc(l)}</option>`).join(""); });
}
async function aboSpeichern(nr) {
  const abo = { bezeichnung: $("#abo-bez").value.trim(), firma: firmaAusText($("#abo-firma").value).firma, art: $("#abo-art").value, betrag: $("#abo-betrag").value.trim(),
    kategorie: $("#abo-kat").value, turnus: $("#abo-turnus").value, ende: $("#abo-ende").value, kuendigungsfrist_tage: $("#abo-frist").value, zahlungsweg: $("#abo-weg").value.trim(),
    vertragsnummer: $("#abo-vnr").value.trim(), beleg_per_mail: $("#abo-mail").checked, auto_buchen: $("#abo-auto").checked, notiz: $("#abo-notiz").value.trim() };
  if (!nr) abo.start = $("#abo-start").value;
  const r = await jpost(nr ? `/api/finanzen/abos/${encodeURIComponent(nr)}` : "/api/finanzen/abos", { abo });
  if (!r || !r.ok) return kundenMsg("abo-msg", (r && r.hinweis) || "Keine Verbindung zum Server.", false);
  if (AKTIV === "finanzen") renderFinanzen();
  return aboDetail(nr || r.nummer, nr ? "Gespeichert." : `${r.nummer} angelegt.`);
}
async function aboDetail(nr, meldung, fehler) {
  ABOS = await jget("/api/finanzen/abos") || ABOS;
  const x = (ABOS.abos || []).find(a => a.nummer === nr); if (!x) return openModal(nr, emptyRow("Abo nicht gefunden."));
  const WIE = { gebucht: "gebucht", beleg: "Beleg kam", uebersprungen: "übersprungen" };
  const erl = Object.entries(x.erledigt || {}).sort((a, b) => b[0].localeCompare(a[0])).map(([d, v]) => `<div class="v2-list-row${v.beleg ? " klick" : ""}" ${v.beleg ? `data-act="${String(v.beleg).startsWith("EB-") ? "eb-detail" : "bl-detail"}" data-id="${esc(v.beleg)}"` : ""}><span class="v2-badge ${v.wie === "uebersprungen" ? "neutral" : "ok"}">${esc(WIE[v.wie] || v.wie)}</span><div class="grow"><b>${esc(datumDe(d))}</b><small>${esc(v.beleg || v.grund || "")}</small></div></div>`).join("");
  const offen = (x.offen || []).map(d => `<div class="v2-list-row"><span class="v2-badge wartet">offen</span><div class="grow"><b>${esc(datumDe(d))}</b><small>${esc(cent2eur(x.betrag_cent))}</small></div>
    <button class="v2-btn ok sm" data-act="abo-buchen" data-id="${esc(nr)}" data-val="${esc(d)}">✓ Buchen</button><button class="v2-btn sm" data-act="abo-skip" data-id="${esc(nr)}" data-val="${esc(d)}">Überspringen</button></div>`).join("");
  openModal(`${nr} · ${x.bezeichnung}`, `${meldung ? `<div class="v2-msg ${fehler ? "err" : "ok"}">${esc(meldung)}</div>` : ""}
    <div class="v2-kv"><span>Firma</span><b class="klick" data-act="kunde-detail" data-id="${esc(x.firma)}">${esc(x.firma_nr)} · ${esc(x.firma_name)}</b></div>
    <div class="v2-kv"><span>Betrag</span><b>${esc(cent2eur(x.betrag_cent))} ${esc(x.turnus_text)} · ${esc(cent2eur(x.monatlich_cent))} je Monat</b></div>
    <div class="v2-kv"><span>Buchung</span><b>${x.beleg_per_mail ? "Beleg kommt per Mail" : x.auto_buchen ? "automatisch bei Fälligkeit" : "auf Rückfrage (Hauptseite)"}</b></div>
    <div class="v2-kv"><span>Status</span><b>${x.status === "aktiv" ? `aktiv · nächste Fälligkeit ${esc(datumDe(x.naechste))}` : `beendet${x.ende ? " zum " + esc(datumDe(x.ende)) : ""}`}</b></div>
    ${x.ende && x.status === "aktiv" ? `<div class="v2-kv"><span>Vertragsende</span><b>${esc(datumDe(x.ende))}${x.kuendigungsfrist_tage != null ? ` · Kündigungsfrist ${esc(String(x.kuendigungsfrist_tage))} Tage` : ""}</b></div>` : ""}
    ${offen ? `<h3>Offene Fälligkeiten</h3>${offen}` : ""}
    <h3>Erledigt</h3>${erl || emptyRow("Noch keine Fälligkeit erledigt.")}
    ${x.status === "aktiv" ? `<div class="v2-card-actions" style="margin-top:12px"><button class="v2-btn" data-act="abo-bearbeiten" data-id="${esc(nr)}">Bearbeiten</button><button class="v2-btn" data-act="abo-beenden" data-id="${esc(nr)}">Abo beenden</button></div>` : ""}`, false);
}

async function finUebersicht(u) {
  const k = u.kennzahlen, v = u.vorjahr, f = u.forderungen, vb = u.verbindlichkeiten, p = u.pipeline, w = u.waechter;
  const zn = finZeitName(u.zeitraum, u.jahr), dz = `zeitraum=${u.zeitraum}`;
  const [ki0, pfTile] = await Promise.all([jget("/api/finanzen/ki-kosten?jahr=" + u.jahr), finPlattformTile(u.jahr)]);
  const ki = ki0 || { monate_eur: [], gesamt_eur: 0, je_provider: {} };
  const max = Math.max(1, ...u.monate.map(m => Math.max(Math.abs(m.einnahmen_cent), Math.abs(m.ausgaben_cent), Math.abs(m.vj_einnahmen_cent), Math.abs(m.vj_ausgaben_cent))));
  const h = (c) => Math.max(0, Math.round(c / max * 100));
  const aktivM = (m) => u.zeitraum === "jahr" || (u.zeitraum[0] === "q" ? Math.ceil(m.nr / 3) === Number(u.zeitraum[1]) : Number(u.zeitraum.slice(1)) === m.nr);
  const monate = `<div class="v2-fin-monate">${u.monate.map(m => `<div class="v2-fin-monat klick${aktivM(m) ? "" : " blass"}" data-act="fin-drill" data-val="zeitraum=m${String(m.nr).padStart(2, "0")}" title="${esc(m.monat)}: Einnahmen ${esc(cent2eur(m.einnahmen_cent))} · Ausgaben ${esc(cent2eur(m.ausgaben_cent))} · Vorjahr ${esc(cent2eur(m.vj_einnahmen_cent))} / ${esc(cent2eur(m.vj_ausgaben_cent))}"><div class="v2-fin-saeulen"><i class="ve" style="height:${h(m.vj_einnahmen_cent)}%"></i><i class="e" style="height:${h(m.einnahmen_cent)}%"></i><i class="va" style="height:${h(m.vj_ausgaben_cent)}%"></i><i class="a" style="height:${h(m.ausgaben_cent)}%"></i></div><small>${esc(m.monat)}</small></div>`).join("")}</div>
    <div class="v2-legend"><span><i style="background:var(--v2-green)"></i>Einnahmen</span><span><i style="background:var(--v2-red)"></i>Ausgaben (absetzbar, inkl. Abschreibung)</span><span><i style="background:var(--v2-line)"></i>blass = Vorjahr</span></div><small class="v2-sub">Monat anklicken: Buchungen dahinter.</small>`;
  const qrow = (q) => `<tr class="klick" data-act="fin-drill" data-val="zeitraum=${q.quartal}"><td><b>${q.quartal.toUpperCase()}</b></td><td style="text-align:right">${esc(cent2eur(q.einnahmen_cent))}</td><td style="text-align:right">${esc(cent2eur(q.ausgaben_cent))}</td><td style="text-align:right"><b>${esc(cent2eur(q.gewinn_cent))}</b></td><td style="text-align:right"><small>${esc(cent2eur(q.vj_gewinn_cent))}</small></td><td style="text-align:right">${q.vj_gewinn_cent ? (d => `<span class="v2-badge ${d >= 0 ? "ok" : "err"}">${d >= 0 ? "+" : ""}${esc(cent2eur(d))}</span>`)(q.gewinn_cent - q.vj_gewinn_cent) : ""}</td></tr>`;
  const quartale = `<table class="v2-table"><thead><tr><th></th><th style="text-align:right">Einnahmen</th><th style="text-align:right">Ausgaben</th><th style="text-align:right">Gewinn</th><th style="text-align:right">Gewinn Vorjahr</th><th style="text-align:right">Veränderung</th></tr></thead><tbody>${u.quartale.map(qrow).join("")}</tbody></table>`;
  const kmax = Math.max(1, ...u.kategorien.map(x => Math.abs(x.betrag_cent)));
  const kat = u.kategorien.length ? u.kategorien.map(x => `<div class="v2-fin-hbar klick" data-act="fin-drill" data-val="${dz}&art=ausgabe&kategorie=${esc(x.kategorie)}"><span>${esc(x.name)}</span><div><i style="width:${Math.max(2, Math.round(Math.abs(x.betrag_cent) / kmax * 100))}%"></i></div><b>${esc(cent2eur(x.betrag_cent))}</b></div>`).join("") : emptyRow("Keine Ausgaben in diesem Zeitraum.");
  const kunden = u.kunden.length ? u.kunden.map((x, i) => `<div class="v2-list-row klick" data-act="fin-drill" data-val="${dz}&art=einnahme&gegenpartei=${encodeURIComponent(x.name)}"><span>${i + 1}.</span><div class="grow"><b>${esc(x.name)}</b></div><b>${esc(cent2eur(x.betrag_cent))}</b></div>`).join("") : emptyRow("Keine Einnahmen in diesem Zeitraum.");
  const anteil = Math.min(100, Math.round((w.anteil || 0) * 100));
  const hr = u.hochrechnung_cent, hrA = hr ? Math.round(hr / 10000000 * 100) : 0;
  const grenze = `<div class="v2-kpi">${esc(cent2eur(w.umsatz_cent || 0))}</div><div class="v2-re-balken"><i style="width:${anteil}%;background:${w.ueberschritten ? "var(--v2-red)" : w.warnung ? "#e8a200" : "var(--v2-accent)"}"></i></div>
    <small class="v2-sub">${anteil} % von 100.000 € · Rechnungen nach Rechnungsdatum + Einnahmen ohne Rechnung${w.vorjahr_ueberschritten ? " · ⚠️ Vorjahr über 25.000 €!" : ""}</small>
    ${hr ? `<div class="v2-kv" style="margin-top:10px"><span>Hochrechnung Jahresende</span><b class="${hrA >= 80 ? "v2-rot" : ""}">${esc(cent2eur(hr))} (${hrA} %)</b></div><small class="v2-sub">wenn es im bisherigen Tempo weitergeht</small>` : ""}`;
  const stufe = (icon, titel, anzahl, cent, ziel) => `<div class="v2-fin-stufe klick" data-tab="${ziel}"><span>${icon}</span><div><b>${esc(titel)}</b><small>${anzahl}${cent != null ? " · " + esc(cent2eur(cent)) : ""}</small></div></div>`;
  const pipeline = `<div class="v2-fin-pipeline">${stufe("📄", "Angebote offen", p.angebote_anzahl, p.angebote_cent, "angebote:offen")}${stufe("🤝", "Aufträge ohne Rechnung", p.auftraege_anzahl, p.auftraege_cent, "angebote:auftraege")}${stufe("✎", "Rechnungsentwürfe", p.rechnung_entwuerfe, null, "rechnungen:entwuerfe")}${stufe("⏳", "Offene Rechnungen", f.anzahl, f.summe_cent, "rechnungen:offen")}</div>`;
  const posten = (liste, act) => liste.slice(0, 6).map(x => `<div class="v2-list-row klick" data-act="${x.act || act}" data-id="${esc(x.nummer)}"><span class="v2-badge ${x.ueberfaellig ? "err" : "neutral"}">${x.ueberfaellig ? "überfällig" : x.faellig_am ? esc(datumDe(x.faellig_am)) : "offen"}</span><div class="grow"><b>${esc(x.gegenpartei || x.nummer)}</b><small>${esc(x.nummer)}</small></div><b>${esc(cent2eur(x.offen_cent))}</b></div>`).join("");
  const mNow = new Date().getMonth(), kiMax = Math.max(0.01, ...ki.monate_eur);
  const kiHtml = `<div class="v2-kpi">${esc(geld(ki.monate_eur[mNow] || 0, "EUR"))} <span class="v2-sub" style="font-size:12px">diesen Monat · Budget ${esc(ki.budget || "–")}</span></div>
    <div class="v2-spark">${ki.monate_eur.map((x, i) => `<i class="${i === mNow ? "a" : ""}" style="height:${Math.max(4, Math.round(x / kiMax * 100))}%" title="${esc(FIN_MONATE[i])}: ${esc(geld(x, "EUR"))}"></i>`).join("")}</div>
    <div class="v2-sub">${u.jahr}: ${esc(geld(ki.gesamt_eur, "EUR"))} · ${Object.entries(ki.je_provider).map(([k2, x]) => `${esc(k2)} ${esc(geld(x, "EUR"))}`).join(" · ") || "keine Aufrufe"}</div>
    <small class="v2-sub">Verbrauch geschätzt aus den Token-Zählern — die Rechnung des Anbieters kommt als Beleg in die EÜR.</small>`;
  const zeilen = u.letzte.length ? finTabelle(u.letzte, false) : emptyRow("Noch keine Zahlungen erfasst — in Rechnungen/Belegen „💶 Zahlung erfassen“ oder oben eine Einnahme/Ausgabe ohne Beleg.");
  const vjText = u.zeitraum === "jahr" ? "Vorjahr" : "Vorjahreszeitraum";
  return `${finKpi("Einnahmen " + zn, cent2eur(k.einnahmen_cent), finDelta(k.einnahmen_cent, v.einnahmen_cent), `${vjText}: ${cent2eur(v.einnahmen_cent)}`, `${dz}&art=einnahme`)}
    ${finKpi("Ausgaben " + zn, cent2eur(k.ausgaben_cent), finDelta(k.ausgaben_cent, v.ausgaben_cent, true), `absetzbar, inkl. Abschreibung · ${vjText}: ${cent2eur(v.ausgaben_cent)}`, `${dz}&art=ausgabe`)}
    ${finKpi("Gewinn " + zn, cent2eur(k.gewinn_cent), finDelta(k.gewinn_cent, v.gewinn_cent), `${vjText}: ${cent2eur(v.gewinn_cent)}`, dz)}
    ${kpiTile("Offen: bekommen wir", cent2eur(f.summe_cent), null, `${f.anzahl} Rechnung(en)${f.ueberfaellig ? ", " + f.ueberfaellig + " überfällig" : ""} · wir zahlen noch ${cent2eur(vb.summe_cent)}`)}
    ${finKalkTile(u, zn)}
    ${pfTile}
    ${tile("Monatsverlauf " + u.jahr, monate, "w8")}
    ${tile("Kleinunternehmer-Grenze " + u.jahr, grenze, "w4")}
    ${u.verlustvortrag ? tile("Verlustvortrag aus " + u.verlustvortrag.aus_jahr, vvHtml(u.verlustvortrag), "w4") : ""}
    ${tile("Quartale " + u.jahr, quartale, "w8")}
    ${tile("KI-Kosten " + u.jahr, kiHtml, "w4")}
    ${tile("Vom Angebot zum Geld", pipeline, "w12")}
    ${tile("Wir bekommen (" + f.anzahl + ")", posten(f.liste, "re-detail") || emptyRow("Keine offenen Rechnungen."), "w6")}
    ${tile("Wir zahlen (" + vb.anzahl + ")", posten(vb.liste, "bl-detail") || emptyRow("Keine offenen Eingangsrechnungen."), "w6")}
    ${tile("Ausgaben nach Kategorie · " + zn, kat, "w6")}
    ${tile("Top-Kunden · " + zn, kunden, "w6")}
    ${tile("Letzte Zahlungen", zeilen, "w12")}`;
}
// Etappe 26: kalkulatorische Kosten (eigene Arbeitszeit, Fahrten) -- zuschaltbar, nie Teil der echten Zahlen/EÜR
function finKalkAn() { try { return localStorage.getItem("luna-fin-kalk") !== "aus"; } catch (e) { return true; } }
// Etappe 27: Plattform-Einnahmen -- erzielt je Monat neben ausgezahlt (Zufluss)
async function finPlattformTile(jahr) {
  const d = await jget(`/api/finanzen/plattform?jahr=${jahr}`);
  if (!d || !(d.auszahlungen || []).length) return "";
  const wg = d.auszahlungen[0].waehrung || "USD", mx = Math.max(...d.erzielt.map(m => m.fremd_cent), 1);
  const MN = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
  const balken = d.erzielt.map(m => `<div class="v2-pf-m" title="${esc(MN[Number(m.monat.slice(5)) - 1])} ${esc(m.monat.slice(0, 4))}: ${fremdTxt(m.fremd_cent, wg)} ≈ ${esc(cent2eur(m.eur_cent))}">
      <span class="v2-pf-b"><i style="height:${Math.max(3, Math.round(m.fremd_cent / mx * 100))}%"></i></span><small>${esc(MN[Number(m.monat.slice(5)) - 1])}${m.monat.slice(0, 4) !== String(jahr) ? " " + m.monat.slice(2, 4) : ""}</small><b>${fremdTxt(m.fremd_cent, wg).replace(",00", "")}</b></div>`).join("");
  const liste = d.auszahlungen.map(a => `<div class="v2-list-row klick" data-act="bl-detail" data-id="${esc(a.nummer)}" role="button" tabindex="0"><span>💸</span><div class="grow"><b>${esc(datumKurz(a.zufluss))} · ${fremdTxt(a.fremd_cent, a.waehrung)} → ${esc(cent2eur(a.eur_cent))}</b><small>erzielt ${esc(datumKurz(a.von))} – ${esc(datumKurz(a.bis))} · ${esc(a.nummer)}${a.quelle === "hand" ? " · von Hand" : ""}</small></div></div>`).join("");
  return tile(`Plattform-Einnahmen ${jahr} · Facebook`, `<div class="v2-kpi">${esc(cent2eur(d.ausgezahlt_eur_cent))} <span class="v2-sub" style="font-size:13px">ausgezahlt (${fremdTxt(d.ausgezahlt_fremd_cent, wg)})</span></div>
    <h3 class="v2-h3" style="margin-top:10px">Erzielt je Monat</h3><div class="v2-pf">${balken}</div>
    <h3 class="v2-h3">Auszahlungen</h3>${liste}<small class="v2-sub">${esc(d.hinweis)}</small>`, "w12");
}
function finKalkTile(u, zn) {
  const kk = u.kalkulatorisch; if (!kk) return "";
  const an = finKalkAn();
  const schalter = `<label class="v2-modlbl"><input type="checkbox" data-act="fin-kalk" ${an ? "checked" : ""}> Kalkulatorische Kosten zeigen</label>`;
  if (!an) return tile("Kalkulatorisch · " + zn, `${schalter}<small class="v2-sub">Ausgeblendet. Echte Zahlen und EÜR sind davon nie betroffen.</small>`, "w12");
  return tile("Kalkulatorisch (nicht steuerlich) · " + zn, `${schalter}
    <div class="v2-an-intern" style="border-top:none"><div class="v2-kv"><span>Eigene Arbeitszeit ${esc(dauerTxt(kk.minuten || 0))}</span><b>−${cent2eur(kk.zeit_cent)}</b></div>
    <div class="v2-kv"><span>Fahrten ${esc(String(kk.km || 0))} km</span><b>−${cent2eur(kk.fahrt_cent)}</b></div>
    <div class="v2-kv"><span>Gewinn (echt)</span><b>${cent2eur(u.kennzahlen.gewinn_cent)}</b></div>
    <div class="v2-kv"><span><b>Ergebnis inkl. kalkulatorischer Kosten</b></span><b style="${kk.gewinn_inkl_cent < 0 ? "color:var(--v2-red)" : ""}">${cent2eur(kk.gewinn_inkl_cent)}</b></div></div>
    <small class="v2-sub">${esc(kk.hinweis)}</small>`, "w12");
}
function vvHtml(v) {
  return `<div class="v2-kpi">${esc(cent2eur(v.verbleibend_cent))} <span class="v2-sub" style="font-size:12px">noch verrechenbar</span></div>
    <div class="v2-re-balken"><i style="width:${v.betrag_cent ? Math.round(v.verrechnet_cent / v.betrag_cent * 100) : 0}%;background:var(--v2-green)"></i></div>
    <small class="v2-sub">Verlust ${v.aus_jahr}: ${esc(cent2eur(v.betrag_cent))} · Gewinn ${v.aus_jahr + 1} bisher ${esc(cent2eur(v.gewinn_cent))} · davon verrechnet ${esc(cent2eur(v.verrechnet_cent))}. Das Finanzamt verrechnet den Verlust automatisch mit dem Gewinn (§ 10d EStG) — er gehört nicht in die Anlage EÜR.</small>`;
}
// Drill-down: die Buchungen hinter einer Zahl; die Summe muss der Kachel entsprechen (Abnahme gegen Rohdaten)
async function finDrill(query) {
  openModal("Buchungen", `<div class="v2-empty">Lade…</div>`, true);
  const d = await jget(`/api/finanzen/posten?jahr=${FIN_JAHR}&${query}`);
  if (!d || !d.kennzahlen) return openModal("Buchungen", emptyRow("Nicht verfügbar."), true);
  const q = new URLSearchParams(query), k = d.kennzahlen;
  const teile = [finZeitName(q.get("zeitraum") || "jahr", d.jahr), q.get("art") === "einnahme" ? "Einnahmen" : q.get("art") === "ausgabe" ? "Ausgaben" : "Einnahmen und Ausgaben",
    q.get("kategorie") ? (d.zeilen[0] || {}).position || q.get("kategorie") : "", q.get("gegenpartei") || ""].filter(Boolean);
  const summe = `<div class="v2-an-zeile" style="margin:6px 0 12px">${q.get("art") !== "ausgabe" ? `<div class="v2-kv"><span>Einnahmen (zählen)</span><b style="color:var(--v2-green)">${esc(cent2eur(k.einnahmen_cent))}</b></div>` : ""}
    ${q.get("art") !== "einnahme" ? `<div class="v2-kv"><span>Ausgaben (absetzbar)</span><b style="color:var(--v2-red)">${esc(cent2eur(k.ausgaben_cent))}</b></div>` : ""}
    ${!q.get("art") ? `<div class="v2-kv"><span>Gewinn</span><b>${esc(cent2eur(k.gewinn_cent))}</b></div>` : ""}</div>`;
  openModal(teile.join(" · "), summe + (d.zeilen.length ? finTabelle(d.zeilen, true) : emptyRow("Keine Buchungen in diesem Zeitraum."))
    + `<small class="v2-sub">Zeile anklicken: Rechnung/Beleg öffnen. Stornierte Zahlungen sind durchgestrichen und zählen nicht; Abschreibung erscheint monatlich.</small>`, true);
}
function finTabelle(zeilen, summe) {
  zeilen = [...zeilen].reverse();                                   // neueste oben (CEO 2026-10-06); Server/CSV bleiben chronologisch
  const rows = zeilen.map(z => `<tr class="klick${z.storniert ? " v2-fin-storno" : ""}" data-act="${String(z.bezug).startsWith("RE-") ? "re-detail" : FIN_ACT[z.quelle]}" data-id="${esc(z.bezug)}"><td>${z.quelle === "afa" ? esc(z.datum.slice(5, 7) + "/" + z.datum.slice(0, 4)) : esc(datumDe(z.datum))}${z.zuordnung_jahr ? ` <small title="10-Tage-Regel">→ ${esc(z.zuordnung_jahr)}</small>` : ""}</td><td><b>${esc(z.bezug)}</b></td><td>${z.firma_nr ? `<small class="v2-sub">${esc(z.firma_nr)}</small> ` : ""}${esc(z.gegenpartei || "")}</td><td>${esc(z.text || "")}${z.storniert ? ` <span class="v2-badge err">storniert</span>` : ""}</td><td><small>${esc(z.position)}</small></td>
    <td style="text-align:right;color:var(--v2-green)">${z.art === "einnahme" ? esc(cent2eur(z.betrag_cent)) : ""}</td><td style="text-align:right;color:var(--v2-red)">${z.art === "ausgabe" && z.quelle !== "afa" ? esc(cent2eur(z.betrag_cent)) : ""}</td>${summe ? `<td style="text-align:right">${z.art === "ausgabe" && !z.storniert ? esc(cent2eur(z.abziehbar_cent)) : ""}</td>` : ""}</tr>`).join("");
  const gueltig = zeilen.filter(z => !z.storniert), s = (a, feld) => gueltig.filter(z => z.art === a).reduce((x, z) => x + z[feld], 0);
  const fuss = summe ? `<tfoot><tr><td></td><td></td><td></td><td><b>Summe</b></td><td></td><td style="text-align:right"><b>${esc(cent2eur(s("einnahme", "betrag_cent")))}</b></td><td style="text-align:right"><b>${esc(cent2eur(s("ausgabe", "betrag_cent")))}</b></td><td style="text-align:right"><b>${esc(cent2eur(s("ausgabe", "abziehbar_cent")))}</b></td></tr></tfoot>` : "";
  return `<div class="v2-tab-scroll"><table class="v2-table"><thead><tr><th>Bezahlt am</th><th>Beleg</th><th>Gegenpartei</th><th>Wofür</th><th>Position (EÜR)</th><th style="text-align:right">Einnahme</th><th style="text-align:right">Zahlung</th>${summe ? `<th style="text-align:right" title="Was in der EÜR zählt: Bewirtung 70 %, Anlagen über die monatliche Abschreibung">absetzbar</th>` : ""}</tr></thead><tbody>${rows}</tbody>${fuss}</table></div>`;
}
async function finJournal(jahr) {
  const d = await jget("/api/finanzen/journal?jahr=" + jahr) || { zeilen: [] };
  const inhalt = d.zeilen.length ? finTabelle(d.zeilen, true) : emptyRow("Keine Zahlungen in " + jahr + ".");
  return tile("Journal " + jahr + " — alle Zahlungen, neueste oben", inhalt + `<div class="v2-card-actions" style="margin-top:10px"><a class="v2-btn" data-kalk-link href="/api/finanzen/journal?jahr=${jahr}&format=csv">⬇ Als CSV (Excel/Numbers)</a><label class="v2-modlbl"><input type="checkbox" data-act="fin-kalk-export"> kalkulatorische Kosten beilegen</label><small class="v2-sub">Stornierte Zahlungen bleiben sichtbar, zählen aber nicht. „→ Jahr“ = 10-Tage-Regel.</small></div>`, "w12");
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
// Jahresabschluss (Etappe 9): Prüfung vor der Steuererklärung, EÜR je Zeile für ELSTER, Export und PDF
async function finAbschluss(jahr) {
  const d = await jget("/api/finanzen/abschluss?jahr=" + jahr);
  if (!d) return emptyRow("Jahresabschluss nicht verfügbar.");
  const pr = d.pruefung, eu = d.euer, offenPflicht = pr.filter(p => !p.ok && p.pflicht).length;
  const pruef = pr.map(p => `<div class="v2-list-row${p.ziel ? " klick" : ""}" ${p.ziel ? `data-tab="${esc(p.ziel)}"` : ""}><span class="v2-badge ${p.ok ? "ok" : p.pflicht ? "err" : "wartet"}">${p.ok ? "✓" : p.pflicht ? "offen" : "Hinweis"}</span><div class="grow"><b>${esc(p.text)}</b>${p.detail ? `<small>${esc(p.detail)}</small>` : ""}</div>${p.ziel ? "<span>›</span>" : ""}</div>`).join("");
  const zeile = (z, t, c, fett, kz) => `<tr><td style="width:70px">${z ? `<span class="v2-badge neutral">${esc(z)}</span>` : "<small>–</small>"}</td><td style="width:70px">${kz ? `<small>Kz ${esc(kz)}</small>` : ""}</td><td>${fett ? "<b>" + esc(t) + "</b>" : esc(t)}</td><td style="text-align:right">${fett ? "<b>" + esc(cent2eur(c)) + "</b>" : esc(cent2eur(c))}</td></tr>`;
  const ein = eu.zeilen.filter(z => z.art === "einnahme"), aus = eu.zeilen.filter(z => z.art !== "einnahme");   // in Formular-Reihenfolge
  const tab = `<table class="v2-table v2-fin-euer"><thead><tr><th>Zeile</th><th>Kennzahl</th><th>Position (Anlage EÜR)</th><th style="text-align:right">Eintragen</th></tr></thead><tbody>
    ${ein.map(z => zeile(z.zeile, z.amtlich || z.position, z.betrag_cent, false, z.kz)).join("")}
    ${aus.map(z => zeile(z.zeile, z.amtlich || z.position, z.betrag_cent, false, z.kz)).join("")}
    <tr class="v2-fin-gewinn"><td></td><td></td><td><b>${eu.gewinn_cent >= 0 ? "Gewinn" : "Verlust"}</b> <small>(ELSTER rechnet die Summen selbst)</small></td><td style="text-align:right"><b>${esc(cent2eur(eu.gewinn_cent))}</b></td></tr></tbody></table>`;
  return tile(`Vor der Steuererklärung ${jahr}`, (offenPflicht ? `<div class="v2-msg err" style="margin-bottom:8px">${offenPflicht} Punkt(e) noch offen — erst klären, dann Export und ELSTER.</div>` : `<div class="v2-msg ok" style="margin-bottom:8px">Alles Nötige erledigt.</div>`) + pruef, "w6")
    + tile(`Export ${jahr}`, `<div class="v2-sub" style="line-height:1.6">Ein ZIP für Finanzamt oder Steuerberater: alle Tabellen (CSV + index.xml nach dem Beschreibungsstandard), das unveränderbare Kassenbuch mit Prüfergebnis, alle Belege im Original und die EÜR als PDF.</div>
      <div class="v2-card-actions" style="margin-top:12px"><a class="v2-btn pri" data-kalk-link href="/api/finanzen/abschluss/export?jahr=${jahr}">⬇ Export ${jahr} (ZIP)</a><label class="v2-modlbl" title="Als Zusatzdatei – EÜR, Journal und index.xml bleiben unverändert"><input type="checkbox" data-act="fin-kalk-export"> kalkulatorische Kosten als Zusatz beilegen</label><a class="v2-btn" href="/api/finanzen/abschluss/euer.pdf?jahr=${jahr}" target="_blank" rel="noopener">📄 EÜR ${jahr} als PDF</a></div>
      <small class="v2-sub">Geht nur an dich (Download), nichts wird verschickt.</small>`, "w6")
    + tile(`Verlustvortrag aus ${jahr - 1}`, (d.verlustvortrag ? vvHtml(d.verlustvortrag) : `<div class="v2-sub">Kein Verlustvortrag aus ${jahr - 1} erfasst. Hattest du ${jahr - 1} einen Verlust, trag ihn hier ein (Betrag aus deiner EÜR bzw. dem Steuerbescheid).</div>`)
      + `<div class="v2-card-actions" style="margin-top:8px"><button class="v2-btn sm" data-act="fin-vv" data-val="${jahr - 1}">${d.verlustvortrag ? "Ändern" : "Verlustvortrag eintragen"}</button></div>`, "w12")
    + tile(`EÜR ${jahr} für ELSTER — Anlage EÜR`, `<div class="v2-msg" style="margin-bottom:8px">${esc(eu.zeilen_hinweis)}</div>` + tab
      + `<small class="v2-sub">Nur die Zeilen mit Betrag eintragen. Kleinunternehmer: alle Beträge brutto. Das ist eine Eingabehilfe — die Verantwortung für die Erklärung bleibt bei dir.</small>`, "w12");
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
let EB_FIRMEN = [];
async function ebNeu(art) {
  EB_FIRMEN = (((await jget("/api/crm/kunden")) || {}).firmen || []).filter(x => x.aktiv);
  if (!FIN_KAT) FIN_KAT = ((await jget("/api/finanzen/eigenbelege")) || {}).kategorien || { einnahme: {}, ausgabe: {} };
  const kat = Object.entries(FIN_KAT[art] || {});
  openModal(art === "einnahme" ? "Einnahme ohne eigene Rechnung" : "Ausgabe ohne Beleg", `<div class="v2-form" style="max-width:620px">
    <div class="v2-msg">${art === "einnahme" ? "Zum Beispiel Auszahlungen von YouTube, Instagram oder anderen Plattformen – Geld, für das du keine eigene Rechnung schreibst. Zählt zum Umsatz (Kleinunternehmer-Grenze)." : "Nur wenn es wirklich keinen Beleg gibt (z. B. Kontoführungsgebühr, Parkautomat). Rechnungen bitte unter „📥 Belege“ hochladen."} LUNA vergibt eine Eigenbeleg-Nummer (EB-…); korrigieren geht nur per Storno.</div>
    <div class="v2-an-zeile"><label class="v2-feld"><small>${art === "einnahme" ? "Eingegangen am *" : "Bezahlt am *"}</small><input id="eb-datum" type="date" value="${heuteIso()}"></label>
      <label class="v2-feld"><small>Betrag (€) *</small><input id="eb-betrag" inputmode="decimal" placeholder="z. B. 250,50"></label>
      <label class="v2-feld"><small>Kategorie *</small><select id="eb-kat">${kat.length > 1 ? `<option value="">— wählen —</option>` : ""}${kat.map(([k, l]) => `<option value="${esc(k)}">${esc(l)}</option>`).join("")}</select></label></div>
    <label class="v2-feld"><small>Wofür? *</small><input id="eb-text" placeholder="${art === "einnahme" ? "z. B. YouTube-Auszahlung September" : "z. B. Kontoführungsgebühr Oktober"}"></label>
    <div class="v2-an-zeile"><label class="v2-feld"><small>${art === "einnahme" ? "Von wem" : "An wen"}</small><input id="eb-gegen" list="eb-firmen" placeholder="Firma wählen oder Namen tippen (wird mit eigener Nummer angelegt)"><datalist id="eb-firmen">${EB_FIRMEN.map(x => `<option value="${esc(firmaOption(x))}">`).join("")}</datalist></label>
      <label class="v2-feld"><small>Referenz (Kontoauszug, Transaktions-ID)</small><input id="eb-ref"></label></div>
    <div id="eb-zuord"></div>
    <div class="v2-card-actions"><button class="v2-btn pri" data-act="eb-speichern" data-val="${esc(art)}">✔ Buchen</button><button class="v2-btn" data-modal-close>Abbrechen</button></div><div id="eb-msg" class="v2-msg"></div></div>`, false);
  zehnTageVerdrahten("eb-datum", "eb-zuord");
}
async function ebSpeichern(art) {
  const buchung = { art, datum: $("#eb-datum").value, betrag: $("#eb-betrag").value.trim(), kategorie: $("#eb-kat").value, text: $("#eb-text").value.trim(),
    gegenpartei: firmaAusText($("#eb-gegen").value).name, firma: firmaAusText($("#eb-gegen").value).firma, referenz: $("#eb-ref").value.trim(), zuordnung_jahr: zehnTageWert("eb-zuord") };
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
/* =========================== Content-Plan (CONTENT_PLAN C1-C3) =========================== */
// Eigene Eintraege + Kunden-Postings (geplant/online) + Drehtermine + Feiertage/Anlaesse in Monat, Woche oder Liste.
RENDER.contentplan = renderContentplan;
let CP = { ansicht: "", tag: "", d: null, filter: "", kanal: "", status: "" };
let CP_KANAL = {}, CP_FORMAT = {}, CP_STATUS = {};
const CP_KUERZEL = { instagram: "IG", tiktok: "TT", youtube: "YT", facebook: "FB", threads: "TH", twitch: "TW", x: "X" };                       // Beschriftungen kommen vom Server (contentplan.py)
const CP_TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const cpIso = (d) => d.toLocaleDateString("sv-SE");
const cpDatum = (iso) => new Date(iso + "T12:00:00");
const cpPlus = (iso, n) => { const d = cpDatum(iso); d.setDate(d.getDate() + n); return cpIso(d); };
const cpMontag = (iso) => { const d = cpDatum(iso); return cpPlus(iso, -((d.getDay() + 6) % 7)); };
function cpBereich() {
  const t = CP.tag || heuteIso();
  if (CP.ansicht === "woche") { const v = cpMontag(t); return [v, cpPlus(v, 6)]; }
  const erster = t.slice(0, 8) + "01", d = cpDatum(erster); d.setMonth(d.getMonth() + 1); d.setDate(0);
  return CP.ansicht === "monat" ? [cpMontag(erster), cpPlus(cpMontag(cpIso(d)), 6)] : [erster, cpIso(d)];
}
function cpTitel() {
  const t = cpDatum(CP.tag || heuteIso());
  if (CP.ansicht !== "woche") return t.toLocaleDateString("de-DE", { month: "long", year: "numeric" });
  const [v, b] = cpBereich(), kw = (() => { const d = cpDatum(v); d.setDate(d.getDate() + 3); const j = new Date(d.getFullYear(), 0, 4); return 1 + Math.round(((d - j) / 864e5 - 3 + (j.getDay() + 6) % 7) / 7); })();
  const kurz = (iso) => cpDatum(iso).toLocaleDateString("de-DE", { day: "numeric", month: "numeric" });
  return `KW ${kw} · ${kurz(v)} – ${datumDe(b)}`;
}
async function renderContentplan(meldung) {
  if (!CP.ansicht) { let a = ""; try { a = localStorage.getItem("luna-cp-ansicht") || ""; } catch { } CP.ansicht = a || (innerWidth < 700 ? "liste" : "monat"); }
  const [von, bis] = cpBereich();
  const d = await jget(`/api/contentplan?von=${von}&bis=${bis}`);
  if (AKTIV !== "contentplan") return;
  if (!d || !d.eintraege) { $("#v2-app").innerHTML = secHead("🗓 Content-Plan") + emptyRow("Content-Plan nicht erreichbar."); return; }
  CP.d = d; CP_KANAL = d.kanaele || {}; CP_FORMAT = d.formate || {}; CP_STATUS = d.status || {};
  const sicht = (id, l) => `<button class="${CP.ansicht === id ? "active" : ""}" data-act="cp-ansicht" data-val="${id}">${l}</button>`;
  const kopf = `<div class="v2-cp-leiste"><div class="v2-cp-nav"><button class="v2-btn sm" data-act="cp-blaettern" data-val="-1" aria-label="zurück">‹</button><button class="v2-btn sm" data-act="cp-blaettern" data-val="0">Heute</button><button class="v2-btn sm" data-act="cp-blaettern" data-val="1" aria-label="weiter">›</button><b>${esc(cpTitel())}</b></div>
    <div class="v2-tabs v2-cp-sicht">${sicht("monat", "Monat")}${sicht("woche", "Woche")}${sicht("liste", "Liste")}</div>
    <div class="v2-cp-filter"><select class="v2-inp" data-act-change="cp-filter"><option value="">Alles</option>${[["plan", "Eigene"], ["posting", "Kunden-Postings"], ["dreh", "Drehtermine"]].map(([k, l]) => `<option value="${k}"${CP.filter === k ? " selected" : ""}>${l}</option>`).join("")}</select>
    <select class="v2-inp" data-act-change="cp-kanal"><option value="">Alle Kanäle</option>${Object.keys(CP_KANAL).map(k => `<option value="${k}"${CP.kanal === k ? " selected" : ""}>${esc(CP_KANAL[k] || k)}</option>`).join("")}</select>
    <select class="v2-inp" data-act-change="cp-status"><option value="">Jeder Status</option>${Object.keys(CP_STATUS).map(k => `<option value="${k}"${CP.status === k ? " selected" : ""}>${esc(CP_STATUS[k])}</option>`).join("")}</select></div></div>`;
  const aktionen = `<button class="v2-btn pri" data-act="cp-neu">＋ Eintrag</button><button class="v2-btn" data-act="cp-anlaesse">📌 Anlässe</button><button class="v2-btn" data-act="cp-vorschlag" title="Der Content-Agent (CCO) schlägt eigene Inhalte für die angezeigte Woche vor – nur Entwurf">🪄 Wochenplan vorschlagen</button>`;
  const es = d.eintraege.filter(e => (!CP.filter || e.quelle === CP.filter || (CP.filter === "plan" && e.quelle === "serie")) && (!CP.kanal || e.kanal === CP.kanal) && (!CP.status || e.status === CP.status));
  const proTag = {}; es.forEach(e => (proTag[e.datum] = proTag[e.datum] || []).push(e));
  const body = CP.ansicht === "liste" ? cpListe(proTag, von, bis) : cpRaster(proTag, von, bis);
  const legende = `<div class="v2-cp-legende"><span class="q-plan">Eigene</span><span class="q-posting">Kunden-Posting</span><span class="q-dreh">Dreh</span><span class="ueber">überfällig</span><span class="fei">Feiertag/Anlass</span></div>`;
  $("#v2-app").innerHTML = secHead("🗓 Content-Plan", aktionen) + (meldung ? `<div class="v2-msg ok">${esc(meldung)}</div>` : "") + kopf + body + legende + `<div id="cp-vorschlag-box"></div>`;
  document.querySelectorAll("#v2-app [data-act-change^=cp-]").forEach(sel => sel.addEventListener("change", () => { CP[{ "cp-filter": "filter", "cp-kanal": "kanal", "cp-status": "status" }[sel.dataset.actChange]] = sel.value; renderContentplan(); }));
}
function cpChip(e) {
  const zeit = e.zeit ? `<small>${esc(e.zeit)}</small>` : "";
  const was = e.quelle === "dreh" ? "🎬" : e.quelle === "posting" ? (e.status === "online" ? "✅" : "📣") : e.quelle === "serie" ? "🔁" : "";
  return `<button class="v2-cp-e q-${esc(e.quelle)} s-${esc(e.status || "")}${e.ueberfaellig ? " ueber" : ""}" data-act="cp-eintrag" data-id="${esc(e.id)}" title="${esc(e.titel)}${e.kunde_name ? " · " + esc(e.kunde_name) : ""}${e.status ? " · " + esc(CP_STATUS[e.status] || e.status) : ""}${e.ueberfaellig ? " · überfällig" : ""}">${zeit}<span>${was}${e.kanal && e.quelle !== "dreh" ? `<i title="${esc(CP_KANAL[e.kanal] || e.kanal)}">${esc(CP_KUERZEL[e.kanal] || "")}</i>` : ""} ${esc(e.titel)}</span></button>`;
}
function cpMarken(tag) {
  const f = CP.d.feiertage[tag], a = CP.d.anlaesse.filter(x => x.von <= tag && tag <= x.bis);
  return (f ? `<span class="v2-cp-fei">🎌 ${esc(f)}</span>` : "") + a.map(x => `<span class="v2-cp-anl" title="${esc(x.notiz || "")}">📌 ${esc(x.titel)}</span>`).join("");
}
function cpRaster(proTag, von, bis) {
  const heute = heuteIso(), monat = (CP.tag || heute).slice(0, 7), tage = [];
  for (let t = von; t <= bis; t = cpPlus(t, 1)) tage.push(t);
  const zellen = tage.map(t => `<div class="v2-cp-tag${t === heute ? " heute" : ""}${CP.ansicht === "monat" && t.slice(0, 7) !== monat ? " fremd" : ""}${CP.d.feiertage[t] ? " feiertag" : ""}">
    <button class="v2-cp-tagkopf" data-act="cp-neu" data-val="${t}" title="Eintrag am ${esc(datumDe(t))} anlegen"><b>${cpDatum(t).getDate()}</b>${CP.ansicht === "woche" ? `<small>${CP_TAGE[(cpDatum(t).getDay() + 6) % 7]}</small>` : ""}<span class="plus">＋</span></button>
    ${cpMarken(t)}${(proTag[t] || []).map(cpChip).join("")}</div>`).join("");
  return `<div class="v2-cp-raster ${CP.ansicht}">${CP.ansicht === "monat" ? CP_TAGE.map(x => `<div class="v2-cp-wt">${x}</div>`).join("") : ""}${zellen}</div>`;
}
function cpListe(proTag, von, bis) {
  const heute = heuteIso(), zeilen = [];
  for (let t = von; t <= bis; t = cpPlus(t, 1)) {
    const marken = cpMarken(t);
    if (!(proTag[t] || []).length && !marken) continue;
    zeilen.push(`<div class="v2-cp-ltag${t === heute ? " heute" : ""}"><div class="v2-cp-ldatum"><b>${CP_TAGE[(cpDatum(t).getDay() + 6) % 7]}, ${esc(datumDe(t))}</b><button class="v2-btn sm" data-act="cp-neu" data-val="${t}" aria-label="Eintrag anlegen">＋</button></div>${marken}${(proTag[t] || []).map(cpChip).join("")}</div>`);
  }
  return `<div class="v2-cp-liste">${zeilen.join("") || emptyRow("In diesem Monat ist noch nichts geplant.")}</div>`;
}
async function cpForm(id, datum, vorlage) {
  const e = id ? (CP.d.eintraege.find(x => x.id === id) || {}) : (vorlage || { datum: datum || CP.tag || heuteIso(), kanal: "instagram", format: "reel", status: "idee" });
  const serie = e.quelle === "serie", rh = CP.d.rhythmen || {};
  if (!CP.firmen) CP.firmen = ((await jget("/api/crm/kunden")) || {}).firmen?.filter(f => f.aktiv !== false && f.typ !== "lieferant").map(f => ({ nummer: f.nummer, name: f.name })) || [];
  const opt = (liste, namen, wert) => liste.map(k => `<option value="${k}"${k === wert ? " selected" : ""}>${esc(namen[k] || k)}</option>`).join("");
  const wiederholung = id && !serie ? "" : `<div class="v2-an-zeile"><label class="v2-feld"><small>Wiederholung${serie ? " (gilt für „Diesen und folgende“)" : ""}</small><select class="v2-inp" name="rhythmus" data-cp-rh>${serie ? "" : `<option value="">Keine</option>`}${opt(Object.keys(rh), rh, e.rhythmus || "")}</select></label>
    <label class="v2-feld" data-cp-ende ${serie || e.rhythmus ? "" : "hidden"}><small>Endet am (optional)</small><input class="v2-inp" type="date" name="ende" value="${esc(e.ende || "")}"></label></div>`;
  const aktionen = serie
    ? `<button class="v2-btn pri" data-act="cp-speichern" data-id="${esc(id)}" data-val="termin">Nur diesen Termin speichern</button><button class="v2-btn" data-act="cp-speichern" data-id="${esc(id)}" data-val="ab">Diesen und folgende ändern</button>
       <button class="v2-btn" data-act="cp-serie-auslassen" data-id="${esc(id)}">Termin auslassen</button><button class="v2-btn" data-act="cp-serie-ende" data-id="${esc(id)}">Serie ab hier beenden</button>`
    : `<button class="v2-btn pri" data-act="cp-speichern" data-id="${esc(id || "")}">Speichern</button>${id ? `<button class="v2-btn" data-act="cp-entfernen" data-id="${esc(id)}">🗑 Entfernen</button>` : ""}`;
  openModal(serie ? "Termin einer Serie" : id ? "Eintrag bearbeiten" : "Neuer Eintrag", `<div class="v2-form" id="cp-form">
    ${serie ? `<div class="v2-msg v2-cp-serie-hinweis">🔁 Teil einer Serie (${esc(rh[e.rhythmus] || e.rhythmus)}, seit ${esc(datumDe(e.start))}${e.ende ? ", bis " + esc(datumDe(e.ende)) : ""})${e.geaendert_einzeln ? " · dieser Termin ist einzeln angepasst" : ""}</div>` : ""}
    <label class="v2-feld"><small>Titel *</small><input class="v2-inp" name="titel" maxlength="160" value="${esc(e.titel || "")}" placeholder="z. B. Derby-Reel: Fanmarsch"></label>
    <div class="v2-an-zeile"><label class="v2-feld"><small>${serie ? "Termin" : "Datum *"}</small><input class="v2-inp" type="date" name="datum" value="${esc(e.datum || "")}" ${serie ? "disabled" : ""}></label><label class="v2-feld"><small>Uhrzeit</small><input class="v2-inp" type="time" name="zeit" value="${esc(e.zeit || "")}"></label></div>
    ${wiederholung}
    <div class="v2-an-zeile"><label class="v2-feld"><small>Kanal</small><select class="v2-inp" name="kanal">${opt(Object.keys(CP_KANAL), CP_KANAL, e.kanal)}</select></label><label class="v2-feld"><small>Format</small><select class="v2-inp" name="format">${opt(Object.keys(CP_FORMAT), CP_FORMAT, e.format)}</select></label><label class="v2-feld"><small>Status</small><select class="v2-inp" name="status">${opt(Object.keys(CP_STATUS), CP_STATUS, e.status)}</select></label></div>
    <label class="v2-feld"><small>Für Kunde (optional)</small><select class="v2-inp" name="kunde"><option value="">— eigener Inhalt —</option>${(CP.firmen || []).map(f => `<option value="${esc(f.nummer)}"${f.nummer === e.kunde ? " selected" : ""}>${esc(f.name)}</option>`).join("")}</select></label>
    <label class="v2-feld"><small>Notiz</small><textarea class="v2-inp" name="notiz" rows="3" maxlength="2000">${esc(e.notiz || "")}</textarea></label>
    <div class="v2-card-actions">${aktionen}</div><div class="v2-msg" id="cp-msg"></div></div>`);
  $("#cp-form [name=titel]").focus();
}
document.addEventListener("change", (e) => {                     // S1: „Endet am“ nur mit Wiederholung
  if (!e.target.matches || !e.target.matches("[data-cp-rh]")) return;
  const l = document.querySelector("[data-cp-ende]"); if (l) l.hidden = !e.target.value;
});
async function cpSpeichern(id, modus) {
  const f = $("#cp-form"), daten = Object.fromEntries([...f.querySelectorAll("[name]")].map(i => [i.name, i.value.trim()]));
  const nurPlan = (d) => { const x = { ...d }; delete x.rhythmus; delete x.ende; return x; };
  let pfad, body, text;
  if (id && id.includes("@")) {                                   // Termin einer Serie
    const [sid, tag] = id.split("@");
    if (modus === "ab") { pfad = `/api/contentplan/serie/${encodeURIComponent(sid)}/ab/${tag}`; body = { ...daten, datum: tag }; text = "Serie ab diesem Termin geändert."; }
    else { pfad = `/api/contentplan/serie/${encodeURIComponent(sid)}/termin/${tag}`; body = nurPlan(daten); delete body.datum; text = "Termin gespeichert."; }
  } else if (!id && daten.rhythmus) { pfad = "/api/contentplan/serie"; body = daten; text = "Serie angelegt."; }
  else { pfad = id ? `/api/contentplan/${encodeURIComponent(id)}` : "/api/contentplan"; body = nurPlan(daten); text = id ? "Eintrag gespeichert." : "Eintrag angelegt."; }
  if (!body.ende) delete body.ende;
  const r = await jpost(pfad, body);
  if (!r || r.ok === false) { const m = $("#cp-msg"); m.className = "v2-msg err"; m.textContent = (r && r.hinweis) || "Keine Verbindung."; return false; }
  CP.tag = daten.datum || CP.tag; closeModal(); renderContentplan(text); return true;
}
function cpAnlaesse() {
  const [von] = cpBereich(), liste = (CP.d.anlaesse || []).map(a => `<div class="v2-list-row"><span>📌</span><div class="grow"><b>${esc(a.titel)}</b><small>${esc(datumDe(a.von))}${a.bis !== a.von ? " – " + esc(datumDe(a.bis)) : ""}${a.notiz ? " · " + esc(a.notiz) : ""}</small></div><button class="v2-btn sm" data-act="cp-anlass-weg" data-id="${esc(a.id)}">Entfernen</button></div>`).join("");
  openModal("📌 Anlässe & Kampagnen", `<div class="v2-sub">Feiertage in Hamburg stehen automatisch im Kalender. Hier trägst du eigene Anlässe ein – z. B. Derby-Woche, Kampagne, Kiez-Event.</div>
    ${liste ? `<h3 class="v2-h3">Im angezeigten Zeitraum</h3>${liste}` : ""}
    <div class="v2-form" id="cp-anl"><h3 class="v2-h3">Neuer Anlass</h3><label class="v2-feld"><small>Titel *</small><input class="v2-inp" name="titel" maxlength="120" placeholder="z. B. Derby-Woche"></label>
    <div class="v2-an-zeile"><label class="v2-feld"><small>Von *</small><input class="v2-inp" type="date" name="von" value="${esc(CP.tag || von)}"></label><label class="v2-feld"><small>Bis</small><input class="v2-inp" type="date" name="bis"></label></div>
    <label class="v2-feld"><small>Notiz</small><input class="v2-inp" name="notiz" maxlength="500"></label>
    <button class="v2-btn pri" data-act="cp-anlass-neu">Anlass anlegen</button><div class="v2-msg" id="cp-anl-msg"></div></div>`);
}
async function cpVorschlag(el) {
  const box = $("#cp-vorschlag-box"); if (!box) return;
  const v = cpMontag(CP.ansicht === "woche" ? cpBereich()[0] : (CP.tag || heuteIso())), b = cpPlus(v, 6);
  box.innerHTML = `<div class="v2-tile w12 v2-cp-vor"><div class="v2-empty">🪄 Der Content-Agent plant die Woche ${esc(datumDe(v))} – ${esc(datumDe(b))} … (bis zu 30 Sekunden)</div></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  el.disabled = true; const r = await jpost("/api/contentplan/vorschlag", { von: v, bis: b }); el.disabled = false;
  if (!r || r.ok === false) { box.innerHTML = `<div class="v2-msg err">${esc((r && r.hinweis) || "Keine Verbindung.")}</div>`; return; }
  CP.vorschlaege = r.vorschlaege || [];
  box.innerHTML = `<div class="v2-tile w12 v2-cp-vor"><div class="v2-tile-h"><span class="t">🪄 Vorschlag des Content-Agenten (CCO) · ${esc(datumDe(v))} – ${esc(datumDe(b))}</span><span class="v2-tile-tools"><button class="v2-icon" data-act="cp-vorschlag-zu" aria-label="schließen">✕</button></span></div>
    <div class="v2-sub">Nur ein Entwurf – nichts ist gespeichert. Übernimm einzelne Ideen per Klick (als Status „Idee“).</div>
    ${CP.vorschlaege.map((x, i) => `<div class="v2-list-row" id="cp-v-${i}"><span>💡</span><div class="grow"><b>${esc(x.titel)}</b><small>${CP_TAGE[(cpDatum(x.datum).getDay() + 6) % 7]}, ${esc(datumDe(x.datum))} · ${esc(CP_KANAL[x.kanal] || x.kanal)} · ${esc(CP_FORMAT[x.format] || x.format)}${x.notiz ? " · " + esc(x.notiz) : ""}</small></div><button class="v2-btn sm" data-act="cp-v-uebernehmen" data-val="${i}">Übernehmen</button></div>`).join("") || emptyRow("Kein Vorschlag erhalten.")}</div>`;
}
async function cpEintragOeffnen(id) {
  const e = (CP.d.eintraege || []).find(x => x.id === id); if (!e) return;
  if (e.quelle === "plan" || e.quelle === "serie") return cpForm(id);
  if (e.quelle === "posting") return abDetail(e.auftrag);
  if (e.quelle === "dreh") return konzeptFenster(e.vorgang, "dreh");
}
// MAILVERSAND_ALLINKL M1: „Jetzt senden" gesperrt, wenn der gewaehlte Versandweg nicht bereit ist (Mail-Programm geht immer)
const sendSperre = (v) => v.google ? "" : `disabled title="${v.versand_kanal === "allinkl" ? "All-Inkl-Postfach nicht eingerichtet" : "Google nicht verbunden"} – nutze dein Mail-Programm"`;
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
  const badge = { wartet: "wartet", freigegeben: "ok", abgelehnt: "danger", gepostet: "ok", fehler: "danger", verfallen: "neutral" };
  const lbl = { wartet: "Wartet auf Freigabe", freigegeben: "Freigegeben – wird gepostet…", abgelehnt: "Abgelehnt", gepostet: "Gepostet", fehler: "Fehler", verfallen: "Verfallen – 30 Tage ohne Freigabe" };
  // REELS_ROADMAP: wartende zuerst (die bald verfallenden oben), danach der Rest neueste zuerst
  const verfaelltAm = (r) => { const t = new Date((r.eingereicht || r.ts || "").slice(0, 10)); if (isNaN(t)) return ""; t.setDate(t.getDate() + 31); return t.toISOString().slice(0, 10); };
  const reels = (d.reels || []).slice().sort((a, b) => (a.status === "wartet") !== (b.status === "wartet") ? (a.status === "wartet" ? -1 : 1)
    : a.status === "wartet" ? String(a.eingereicht || "").localeCompare(String(b.eingereicht || "")) : String(b.ts || "").localeCompare(String(a.ts || "")));
  const cards = reels.map(r => {
    const wartet = r.status === "wartet", postbar = r.status === "freigegeben" || r.status === "fehler";
    return `<div class="v2-card"><div class="v2-card-h"><span class="v2-badge ${badge[r.status] || "neutral"}">${lbl[r.status] || esc(r.status)}</span><b>${esc(r.thema || "Reel")}</b> <small>${esc(r.datum || "")}${r.dauer_sek ? " · " + r.dauer_sek + "s" : ""}</small></div>
    ${r.video_geloescht ? `<div class="v2-sub" style="margin:8px 0">🗑 Video gelöscht (${r.status === "verfallen" ? "verfallen" : "abgelehnt"}, nach 14 Tagen) – Text und Daten bleiben erhalten.</div>`
      : `<video src="/api/reel/${esc(r.id)}/video" controls playsinline preload="metadata" style="width:100%;max-height:60vh;border-radius:12px;background:#000;margin:8px 0"></video>`}
    ${wartet && verfaelltAm(r) ? `<div class="v2-sub">⏳ verfällt am ${esc(datumDe(verfaelltAm(r)))}, wenn du nicht entscheidest</div>` : ""}
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
      const pk = cls === "luna" ? "hoa" : cls === "human" ? "" : (box.key || "");   // A1: Klick -> Agenten-Profil
      return `<g class="v2-mm-b ${cls}${pk ? " klick" : ""}"${pk ? ` data-act="ag-profil" data-id="${esc(pk)}"` : ""}>${tip ? `<title>${esc(tip)}</title>` : ""}<rect x="${cxp - w / 2}" y="${y - bh / 2}" width="${w}" height="${bh}" rx="9"/>${t}</g>`;
    };
    const vlink = (x1, y1, x2, y2, cls) => { const my = (y1 + y2) / 2; return `<path d="M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}" class="v2-mm-link ${cls}"/>`; };
    let links = vlink(centerX, yCEO + bh / 2, centerX, yLUNA - bh / 2, "human"), nodes = "";
    const drawRow = (row, yDEP, ySUB) => row.forEach((d, i) => {
      const cx = rowX(row, i);
      links += vlink(centerX, yLUNA + bh / 2, cx, yDEP - bh / 2, d.status);
      const num = (d.name.split("·")[0] || "").trim(), kuerzel = (d.name.split("·")[1] || d.name).trim();
      box.key = d.key; nodes += box(cx, yDEP, bw, kuerzel, "dep " + d.status, num, d.rolle);
      (d.subs || []).forEach((s, j) => {
        const sy = ySUB + j * subStep, py = j === 0 ? yDEP + bh / 2 : sy - subStep + bh / 2;
        links += vlink(cx, py, cx, sy - bh / 2, s.status);
        box.key = s.key === "risk" ? "risk" : ""; nodes += box(cx, sy, bw, s.name, "sub " + s.status, "", s.name + " · " + stL(s.status));
      });
    });
    drawRow(rowA, yDEPA, ySUBA); drawRow(rowB, yDEPB, ySUBB);
    box.key = ""; nodes += box(centerX, yCEO, 126, ceo.name || "CEO", "human", ceo.rolle);
    nodes += box(centerX, yLUNA, 142, luna.name || "LUNA", "luna", luna.rolle || "Head of Agents");
    svg = `<div class="v2-mm-scroll"><svg viewBox="0 0 ${W} ${H}" class="v2-mm-svg" preserveAspectRatio="xMidYMid meet" style="min-width:${Math.min(W, 900)}px">${links}${nodes}</svg></div>`;
  }
  const u = (await jget("/api/agenten-uebersicht") || {}).agenten || [];
  const liste = u.map(x => `<div class="v2-list-row v2-ag-zeile" data-act="ag-profil" data-id="${esc(x.key)}"><span class="v2-badge ${x.status === "aktiv" ? "aktiv" : "neutral"}">${esc(x.status)}</span><div class="grow"><b>${esc(agTitel(x.titel))}</b><small>${x.skills} Skills · ${x.quellen} Quellen · ${x.watcher} Themen · ${x.funde} Funde · ${x.nutzung30} ${x.nutzung30 === 1 ? "Anfrage" : "Anfragen"}/30 T.</small></div><span class="v2-ag-pfeil">›</span></div>`).join("") || emptyRow("Keine Agenten-Daten.");
  $("#v2-app").innerHTML = secHead("Agenten-Organisation") + tile("Organigramm — Live-Status", legend + svg + `<div class="v2-sub" style="margin-top:6px">Tippe auf einen Agenten für sein Profil.</div>`, "w12")
    + tile("Agenten im Überblick — Skills, Quellen, Watcher-Themen, Nutzung", liste, "w12");
}
const agTitel = (t) => { const p = String(t || "").split(" — "); return p[p.length - 1]; };
async function agentProfil(key) {
  openModal("Agent", `<div class="v2-empty">Lade…</div>`);
  const p = await jget(`/api/agenten/${encodeURIComponent(key)}/profil`);
  if (!p || !p.charta) return openModal("Agent", emptyRow("Profil nicht gefunden."));
  const c = p.charta, n30 = p.nutzung.tage30, n90 = p.nutzung.tage90;
  const kopf = `<div class="v2-kv"><span>Status (Charta)</span><b><span class="v2-badge ${c.status === "aktiv" ? "aktiv" : "neutral"}">${esc(c.status)}</span></b></div>
    <div class="v2-ag-block"><span>Modell (Richtwert laut Charta)</span><b>${esc(c.modell || "—")}</b></div>
    ${c.rolle ? `<div class="v2-ag-rolle">${esc(c.rolle.replace(/\*\*/g, ""))}</div>` : ""}`;
  const nz = `<div class="v2-ag-zahlen"><div><b>${n30.anzahl}</b><small>Anfragen 30 Tage</small></div><div><b>${n90.anzahl}</b><small>Anfragen 90 Tage</small></div><div><b>${n30.median_s == null ? "–" : n30.median_s + " s"}</b><small>Antwortzeit (Median)</small></div><div><b>${n90.fehler}</b><small>Fehler 90 Tage</small></div></div>
    <div class="v2-sub">${n90.zuletzt ? `Zuletzt gefragt: ${esc(zeitKurz(n90.zuletzt))} · 90 Tage: ${n90.direkt || 0} direkt, ${n90.werkzeug || 0} über Werkzeuge` : "Noch nicht gefragt (gemessen wird seit dem 05.10.2026, nur Zeit/Dauer – keine Inhalte)."}</div>`;
  const sk = p.skills.map(x => `<div class="v2-list-row"><span class="v2-badge ${x.geladen ? "aktiv" : "neutral"}">${x.geladen ? "geladen" : esc(x.verdikt)}</span><div class="grow"><b>${esc(x.name)}${x.quellen ? " 📚" : ""}</b><small>${esc(x.beschreibung)}</small></div></div>`).join("") || emptyRow("Noch keine Skills.");
  const qs = p.quellen.map(q => `<div class="v2-list-row"><span>⚖️</span><div class="grow"><b><a href="${esc(q.url)}" target="_blank" rel="noopener">${esc(q.norm)}</a></b><small>${esc(q.skill)} · Stand ${esc(datumDe(q.stand))}${q.pruefen_bis ? " · nächste Prüfung " + esc(datumDe(q.pruefen_bis)) : ""}</small></div></div>`).join("");
  const wt = p.watcher.length ? `<div class="v2-chips">${p.watcher.map(t => `<span class="v2-chip">${esc(t)}</span>`).join("")}</div>` : emptyRow("Keine Watcher-Themen.");
  const fu = p.funde.map(f => `<div class="v2-list-row"><span>🛰</span><div class="grow"><b><a href="${esc(f.url || "#")}" target="_blank" rel="noopener">${esc(f.titel || "")}</a></b><small>${esc(zeitKurz(f.ts))}</small></div></div>`).join("");
  const h = (t) => `<div class="v2-sub" style="margin:16px 0 4px"><b>${t}</b></div>`;
  openModal(agTitel(c.titel), kopf + h("Nutzung") + nz + h(`Skills (${p.skills.length})`) + sk
    + (qs ? h(`Quellen (${p.quellen.length}) – nachts auf Änderungen geprüft`) + qs : "")
    + h("Watcher-Themen") + wt + (fu ? h(`Letzte Funde (${p.funde_gesamt} gesamt)`) + fu : "")
    + `<div class="v2-sub" style="margin-top:14px">Charta: <code>${esc(c.datei)}</code> – ändert nur der Head of Agents auf deine Anweisung.</div>`);
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
  if (w.fachagenten) {
    const top = Object.entries(w.fachagenten.je_agent || {}).slice(0, 5).map(([a, n]) => `${esc(a.toUpperCase())} (${n})`).join(", ");
    h += zeile(null, "Fachagenten — wer wird gefragt", `${w.fachagenten.anfragen} Anfragen (${w.fachagenten.direkt || 0} direkt, ${w.fachagenten.werkzeug || 0} über Werkzeuge)${delta(w.fachagenten.anfragen, (v.fachagenten || {}).anfragen)}${top ? " · " + top : " · niemand gefragt"}${w.fachagenten.fehler ? ` · ${w.fachagenten.fehler} Fehler` : ""}`);
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
RENDER.auftraege = () => { SUBTAB.angebote = "auftraege"; return renderAngebote(); };   // eigener Punkt, gleiche Seite
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
    ${tile("✉️ Textbausteine & Signatur", `<div id="set-tb"><div class="v2-empty">Lade …</div></div>`, "w12")}
    ${tile("🔐 Anmeldung & Geräte", `<div id="set-anmeldung"><div class="v2-empty">Lade …</div></div>`, "w12")}
  </div><div class="v2-sub" style="margin-top:8px">Gilt für Anzeige, Telegram-Hinweise und Briefings. Moduswechsel (advisory→paper→live) und Budget bleiben separat abgesichert.</div>`;
  anmeldungBox(); tbLaden();
}
// TEXTBAUSTEINE T1: Vorlagen je Belegart + Signatur (wirken ab dem naechsten Versand)
let TB = null;
const TB_BEISPIEL = { anrede: "Guten Tag Anna Muster,", anrede_moin: "Moin Anna Muster,", vorname: "Anna", nachname: "Muster", kunde: "Kiez Alm Gastro GmbH",
  nummer: "AN-2026-0012", titel: "Herbstkampagne", titel_zusatz: " – Herbstkampagne", zu_titel: " zu „Herbstkampagne“", titel_quote: " „Herbstkampagne“",
  betrag: "1.600,00 €", gueltig_bis: "19.10.2026", praesentation: "Unsere Präsentation ansehen: https://canva.link/…", angebot: "AN-2026-0012",
  zu_angebot: "zu unserem Angebot AN-2026-0012", faellig: "20.10.2026", rechnungsart: "Rechnung", bezug: "RE-2026-0007", rechnung: "RE-2026-0007",
  stufe: "1. Mahnung", mahnung_im_text: "1. Mahnung", frist: "27.10.2026", version_zusatz: "", titel_oder_vorgang: "Herbstkampagne" };
async function tbLaden(meldung) {
  const d = await jget("/api/crm/textbausteine"); if (!d) { const b = $("#set-tb"); if (b) b.innerHTML = emptyRow("Nicht verfügbar."); return; }
  TB = { d: d.textbausteine, arten: d.arten, ph: d.platzhalter, darf: d.darf_aendern, art: (TB && TB.art) || "angebot", fokus: null };
  tbZeichnen(meldung);
}
function tbVorschau(art, v) {
  const f = (t) => String(t || "").replace(/\{([a-z_]+)\}/g, (_, k) => TB_BEISPIEL[k] ?? "").replace(/[ \t]{2,}/g, " ").replace(/\n{3,}/g, "\n\n").trim();
  return `Betreff: ${f(v.betreff)}\n\n${f(v.text)}\n\n${TB.d.signatur || "(noch keine Signatur – es gilt „Mit freundlichen Grüßen …“)"}`;
}
function tbZeichnen(meldung) {
  const box = $("#set-tb"); if (!box || !TB) return;
  const art = TB.art, liste = TB.d.vorlagen[art] || [], ro = TB.darf ? "" : "disabled";
  box.innerHTML = (meldung ? `<div class="v2-msg ${meldung.ok ? "ok" : "err"}" style="margin-bottom:10px">${esc(meldung.text)}</div>` : "")
    + `<small class="v2-sub">Gilt für jede Mail ab dem nächsten Versand – „Senden …“ über LUNA und „✉️ Im Mail-Programm öffnen“. Vor dem Versand kannst du den Text für die eine Mail noch anpassen. Bereits versendete Mails bleiben unverändert.</small>
    <label class="v2-feld" style="margin-top:10px"><small>Signatur (steht unter jedem Text)</small><textarea id="tb-signatur" class="v2-inp" rows="7" ${ro}>${esc(TB.d.signatur)}</textarea></label>
    <div class="v2-chips v2-tb-arten">${Object.entries(TB.arten).map(([k, l]) => `<button class="v2-chip ${k === art ? "on" : ""}" data-act="tb-art" data-val="${esc(k)}">${esc(l)} <small>${(TB.d.vorlagen[k] || []).length}</small></button>`).join("")}</div>
    ${liste.map((v, i) => `<div class="v2-tb-vorlage" data-i="${i}"><div class="v2-an-zeile"><label class="v2-feld"><small>Name der Vorlage</small><input class="v2-inp tb-name" value="${esc(v.name)}" ${ro}></label>
        <label class="v2-modlbl"><input type="radio" name="tb-std" data-act="tb-standard" data-val="${i}" ${v.standard ? "checked" : ""} ${ro}> Standard</label></div>
      <label class="v2-feld"><small>Betreff</small><input class="v2-inp tb-betreff" value="${esc(v.betreff)}" ${ro}></label>
      <label class="v2-feld"><small>Text (Signatur kommt automatisch darunter)</small><textarea class="v2-inp tb-text" rows="8" ${ro}>${esc(v.text)}</textarea></label>
      <details class="v2-pz"><summary>Vorschau mit Beispielwerten</summary><pre class="v2-mail-text">${esc(tbVorschau(art, v))}</pre></details>
      ${TB.darf && liste.length > 1 ? `<div class="v2-card-actions"><button class="v2-btn sm" data-act="tb-weg" data-val="${i}">Vorlage löschen</button></div>` : ""}</div>`).join("")}
    <small class="v2-sub">Platzhalter (antippen = an der Cursor-Stelle einfügen):</small>
    <div class="v2-chips v2-tb-ph">${Object.entries(TB.ph[art] || {}).map(([k, l]) => `<button class="v2-chip" data-act="tb-ph" data-val="${esc(k)}" title="${esc(l)}">{${esc(k)}}</button>`).join("")}</div>
    ${TB.darf ? `<div class="v2-card-actions" style="margin-top:10px"><button class="v2-btn" data-act="tb-neu">+ Neue Vorlage (${esc(TB.arten[art])})</button><button class="v2-btn pri" data-act="tb-speichern">Textbausteine speichern</button></div>` : `<small class="v2-sub">Nur ansehen – ändern darf der CEO (Modul Finanzen).</small>`}
    <div id="tb-msg" class="v2-msg"></div>`;
  box.querySelectorAll(".tb-betreff, .tb-text, .tb-name").forEach(i => i.addEventListener("focus", () => { TB.fokus = i; }));
}
function tbUebernehmen() {                                    // Formularwerte der aktuellen Belegart in TB.d
  if (!TB || !$("#set-tb")) return;
  const sig = $("#tb-signatur"); if (sig) TB.d.signatur = sig.value;
  const liste = TB.d.vorlagen[TB.art] || [];
  document.querySelectorAll("#set-tb .v2-tb-vorlage").forEach(el => { const v = liste[Number(el.dataset.i)]; if (!v) return;
    v.name = $(".tb-name", el).value; v.betreff = $(".tb-betreff", el).value; v.text = $(".tb-text", el).value; });
}
async function tbAktion(act, id, val, el) {
  if (!TB) return;
  if (act === "tb-ph") { const f = TB.fokus; if (!f) return kundenMsg("tb-msg", "Erst in Betreff oder Text tippen, dann den Platzhalter wählen.", false);
    const p = f.selectionStart ?? f.value.length; f.value = f.value.slice(0, p) + `{${val}}` + f.value.slice(f.selectionEnd ?? p); f.focus(); return; }
  tbUebernehmen();
  const liste = TB.d.vorlagen[TB.art];
  if (act === "tb-art") { TB.art = val; TB.fokus = null; return tbZeichnen(); }
  if (act === "tb-neu") { const std = liste.find(v => v.standard) || liste[0]; liste.push({ id: "", name: "Neue Vorlage", betreff: std.betreff, text: std.text, standard: false }); return tbZeichnen(); }
  if (act === "tb-weg") { if (!confirm("Diese Vorlage löschen?")) return; const [weg] = liste.splice(Number(val), 1); if (weg && weg.standard && liste[0]) liste[0].standard = true; return tbZeichnen(); }
  if (act === "tb-standard") { liste.forEach((v, i) => { v.standard = i === Number(val); }); return; }
  if (act === "tb-speichern") {
    const r = await jpost("/api/crm/textbausteine", { textbausteine: TB.d });
    if (!r || r.ok === false) return kundenMsg("tb-msg", (r && r.hinweis) || "Keine Verbindung.", false);
    return tbLaden({ ok: true, text: r.geaendert === false ? "Keine Änderung." : "Gespeichert – gilt ab dem nächsten Versand." });
  }
}
// Etappe 2 + 6: Passkeys (Face ID) und angemeldete Geraete; Optionen fuer Face ID vorab holen (iOS: Abfrage direkt im Tipp)
let PK_VOR = null;
const pkVorbereiten = () => { PK_VOR = null; if (window.LunaPasskey && LunaPasskey.unterstuetzt()) LunaPasskey.vorbereitenEinrichten().then(v => { PK_VOR = v; }).catch(() => { }); };
async function anmeldungBox(meldung) {
  const box = $("#set-anmeldung"); if (!box) return;
  const d = await jget("/api/sitzungen"); if (!d) { box.innerHTML = emptyRow("Nicht verfügbar."); return; }
  const kann = window.LunaPasskey && LunaPasskey.unterstuetzt();
  const dt = (t) => t ? new Date(t).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" }) : "–";
  box.innerHTML = (meldung ? `<div class="v2-msg ${meldung.ok ? "ok" : "err"}" style="margin-bottom:10px">${esc(meldung.text)}</div>` : "")
    + `<div class="v2-kv"><span><b>Face ID / Passkey</b><br><small class="v2-sub">Anmelden ohne Passwort. Der geheime Schlüssel bleibt auf dem Gerät.</small></span>
      ${kann ? `<button class="v2-btn pri" data-act="pk-einrichten">Auf diesem Gerät einrichten</button>` : `<small class="v2-sub">Einrichten geht in Safari/der WebApp über https://os.hanserautisch.synology.me</small>`}</div>`
    + (d.passkeys.length ? d.passkeys.map(p => `<div class="v2-kv"><span>🔑 ${esc(p.geraet || "Passkey")} <small class="v2-sub">eingerichtet ${esc(dt(p.erstellt))} · zuletzt ${esc(dt(p.zuletzt))}</small></span><button class="v2-btn" data-act="pk-loeschen" data-id="${esc(p.id)}">Entfernen</button></div>`).join("") : `<div class="v2-kv"><span class="v2-sub">Noch kein Passkey eingerichtet.</span></div>`)
    + `<div class="v2-kv" style="margin-top:10px"><span><b>Angemeldete Geräte</b><br><small class="v2-sub">Jede Anmeldung hält 30 Tage und verlängert sich bei Nutzung.</small></span>
      <span style="display:flex;gap:8px;flex-wrap:wrap">${d.sitzungen.length > 1 ? `<button class="v2-btn" data-act="sz-alle">Alle anderen abmelden</button>` : ""}${d.per_cookie ? `<button class="v2-btn" data-act="logout">Abmelden</button>` : ""}</span></div>`
    + (d.sitzungen.length ? d.sitzungen.map(z => `<div class="v2-kv"><span>${z.aktuell ? "📍" : "💻"} ${esc(z.geraet || "Gerät")}${z.aktuell ? " <b>(dieses Gerät)</b>" : ""} <small class="v2-sub">seit ${esc(dt(z.erstellt))} · zuletzt ${esc(dt(z.zuletzt))}</small></span>${z.aktuell ? "" : `<button class="v2-btn" data-act="sz-widerrufen" data-id="${esc(z.id)}">Abmelden</button>`}</div>`).join("")
      : `<div class="v2-kv"><span class="v2-sub">Keine Anmeldung per Login-Seite (dieser Browser nutzt noch das alte Login-Fenster).</span></div>`);
  pkVorbereiten();
}
async function passkeyEinrichten(nachher) {
  try {
    const vor = PK_VOR || await LunaPasskey.vorbereitenEinrichten(); PK_VOR = null;
    await LunaPasskey.einrichten(vor);
    try { localStorage.setItem("luna-pk-gefragt", "1"); } catch { }
    return nachher({ ok: true, text: "Face ID ist eingerichtet. Beim nächsten Login einfach „Mit Face ID anmelden“ tippen." });
  } catch (e) {
    return nachher({ ok: false, text: e && e.name === "NotAllowedError" ? "Abgebrochen." : e && e.name === "InvalidStateError" ? "Auf diesem Gerät ist schon ein Passkey eingerichtet." : ("Hat nicht geklappt: " + (e.message || e)) });
  }
}
// Nach einem Passwort-Login einmal je Geraet anbieten: „Beim naechsten Mal mit Face ID?“
function passkeyAngebot() {
  const hat = document.cookie.split(";").some(c => c.trim().startsWith("luna_pk_anbieten="));
  if (!hat) return;
  document.cookie = "luna_pk_anbieten=; Max-Age=0; path=/";
  let gefragt = false; try { gefragt = localStorage.getItem("luna-pk-gefragt") === "1"; } catch { }
  if (gefragt || !(window.LunaPasskey && LunaPasskey.unterstuetzt())) return;
  pkVorbereiten();
  const el = document.createElement("div"); el.className = "v2-pk-angebot"; el.id = "v2-pk-angebot";
  el.innerHTML = `<b>Beim nächsten Mal mit Face ID anmelden?</b><span>Dann brauchst du auf diesem Gerät kein Passwort mehr.</span>
    <div><button class="v2-btn pri" data-act="pk-angebot-ja">Einrichten</button><button class="v2-btn" data-act="pk-angebot-nein">Nicht jetzt</button></div>`;
  document.body.appendChild(el);
}

/* =========================== Aktionen =========================== */
const reFreig = () => AKTIV === "dash" ? renderDash() : renderFreigaben();  // Antrags-Aktion aus Dashboard ODER Freigaben
async function handleAct(act, el) {
  const id = el.dataset.id, val = el.dataset.val, asset = el.dataset.asset, typ = el.dataset.typ;
  const flash = (m) => { const o = el.textContent; el.textContent = m; return o; };
  if (formUngespeichert() && ["re-festschreiben", "an-senden", "an-versendet", "re-verwerfen", "an-status", "ab-neu", "ab-detail",
      "an-detail", "re-detail", "bv-oeffnen", "konzept", "ma-detail", "re-senden"].includes(act)
      && !confirm("Im Formular gibt es ungespeicherte Änderungen. Ohne Speichern weitermachen?\n(Abbrechen = zurück, dann unten „Speichern“)")) return;
  switch (act) {
    case "pk-einrichten": return passkeyEinrichten(m => anmeldungBox(m));
    case "pk-angebot-ja": return passkeyEinrichten(m => { const b = $("#v2-pk-angebot"); if (b) b.innerHTML = `<b>${esc(m.text)}</b><div><button class="v2-btn" data-act="pk-angebot-nein">Schließen</button></div>`; });
    case "pk-angebot-nein": { try { localStorage.setItem("luna-pk-gefragt", "1"); } catch { } const b = $("#v2-pk-angebot"); if (b) b.remove(); return; }
    case "pk-loeschen": if (!confirm("Diesen Passkey entfernen? Auf dem Gerät klappt Face ID dann nicht mehr (Passwort geht weiter).")) return; await jpost("/api/passkey/loeschen", { id }); return anmeldungBox({ ok: true, text: "Passkey entfernt. Tipp: auch in den iPhone-Einstellungen unter Passwörter löschen." });
    case "sz-widerrufen": { const r = await jpost("/api/sitzungen/widerrufen", { id }); return anmeldungBox({ ok: true, text: `${(r && r.abgemeldet) || 0} Gerät abgemeldet.` }); }
    case "sz-alle": { if (!confirm("Alle anderen Geräte abmelden?")) return; const r = await jpost("/api/sitzungen/widerrufen", { alle: true }); return anmeldungBox({ ok: true, text: `${(r && r.abgemeldet) || 0} Gerät(e) abgemeldet.` }); }
    case "logout": await jpost("/api/logout"); location.href = "/login?abgemeldet=1"; return;
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
    case "an-bearbeiten": return anDetail(id);
    case "bl-ansicht": { const w = el.closest(".v2-ansicht"); if (!w) return; w.dataset.ansicht = val;
      w.querySelectorAll(".v2-ansicht-wahl button").forEach(b => b.classList.toggle("on", b.dataset.val === val));
      try { localStorage.setItem("luna-beleg-ansicht", val); } catch { } return; }
    case "an-pos-neu": { $("#an-pos").insertAdjacentHTML("beforeend", anProduktZeile()); const n = $("#an-pos").lastElementChild; anSumme(); const sel = n && $(".an-p-produkt", n); if (sel) sel.focus(); return; }
    case "an-firma-wahl": return firmaWaehlen(id);
    case "kat-speichern": return katalogSpeichern();
    case "kat-neu": return katalogFormatNeu(Number(id));
    case "pl-pdf": return preislistePdf();
    case "an-pos-weg": { const z = el.closest(".v2-an-pos"); if (z) z.remove(); return anSumme(); }
    case "an-speichern": return anSpeichern(id);
    case "ab-manuell": return anEditor("", "", "auftrag");
    case "ab-manuell-speichern": return abManuellSpeichern();
    case "an-mail": { flash("⏳ erstellt…"); const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/mailentwurf`, {}); return anDetail(id, r && r.ok ? `Gmail-Entwurf an ${r.an} mit PDF angelegt — in Gmail prüfen und selbst senden. Danach hier „Als versendet markieren“.` : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "an-versendet": {
      if (!confirm("Hast du das Angebot auf anderem Weg verschickt (nicht über „Senden“)? Danach ist es nicht mehr änderbar, und die Kalender-Erinnerungen werden angelegt.")) return;
      flash("⏳ …"); const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/versendet`, {});
      if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote();
      return anDetail(id, r && r.ok ? ["Als versendet markiert.", ...(r.termine || []).map(t => `📅 ${t.titel} (${new Date(t.datum).toLocaleDateString("de-DE")})`), ...(r.hinweise || [])].join("\n") : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "bl-detail": return blDetail(id);
    case "bl-buchen": return blBuchen(id);
    case "bl-bezahlt-form": return blBezahltForm(id);
    case "bl-pos-neu": { $("#bl-pos").insertAdjacentHTML("beforeend", blPosZeile({})); return blPosSync(); }
    case "bl-pos-weg": { el.closest(".v2-bl-pos").remove(); return blPosSync(); }
    case "bl-pos-diff": {
      const w = blPosWerte(), diff = feld2cent(($("#bl-betrag") || {}).value) - w.reduce((x, p) => x + feld2cent(p.betrag), 0);
      if (!diff) return;
      $("#bl-pos").insertAdjacentHTML("beforeend", blPosZeile({ text: diff > 0 ? "Versand / Sonstiges" : "Rabatt", betrag: cent2feld(diff), kategorie: (w.find(p => p.kategorie && p.kategorie !== "privat") || {}).kategorie || "" }));
      return blPosSync();
    }
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
    case "hb-filter": HB_FILTER = val || ""; return renderHandlung();
    case "vs-neu": return vsDialog(id || "", val === "nachfassen");
    case "suche-oeffnen": return sucheOeffnen();
    case "suche-treffer": return sucheTreffer(val, id);
    case "impressum-suchen": return impressumSuchen(val, el);
    case "vs-senden": return vsSenden(el);
    case "vs-trotzdem": return vsSenden($("#vs-senden-knopf"), true);
    case "vs-dublette-nehmen": { const s = $("#vs-firma"); if (!s) return; if (![...s.options].some(o => o.value === id)) s.insertAdjacentHTML("beforeend", `<option value="${esc(id)}">${esc(id)}</option>`);
      s.value = id; s.dispatchEvent(new Event("change")); const m = $("#vs-msg"); if (m) { m.className = "v2-msg"; m.textContent = "Vorhandene Firma gewählt – bitte prüfen und senden."; } return; }
    case "vs-erledigt": { if (!confirm("Als „kein Interesse“ abschließen? LUNA erinnert dann nicht mehr ans Nachfassen.")) return;
      const r = await jpost(`/api/crm/vorstellungen/${encodeURIComponent(id)}/erledigt`, {}); if (!r || r.ok === false) return alert((r && r.hinweis) || "Fehler."); return renderKunden(); }
    case "todo-oeffnen": {
      if (val.startsWith("go:")) { const [, s, t] = val.split(":"); return go(s, t); }
      return handleAct(val, el);
    }
    case "todo-erledigen": {
      el.disabled = true; const r = await jpost(val, el.dataset.schluessel ? { schluessel: el.dataset.schluessel } : {});
      if (!r || r.ok === false) { el.disabled = false; return alert((r && r.hinweis) || "Fehler."); }
      glockeAktualisieren();
      return AKTIV === "handlung" ? renderHandlung() : renderDash();
    }
    case "fin-drill": return finDrill(val);
    case "fin-vv": {
      const betrag = prompt(`Verbleibender Verlust aus ${val} in € (z. B. 2.622,59):`, ""); if (betrag === null) return;
      const r = await jpost("/api/finanzen/verlustvortrag", { jahr: Number(val), betrag, notiz: "per LUNA-OS" });
      if (!r || !r.ok) return alert((r && r.hinweis) || "Fehler.");
      return renderFinanzen(`Verlustvortrag ${val}: ${cent2eur(r.betrag_cent)} gespeichert.`);
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
    case "bl-nachweis": { const zu = (prompt("Zu welchem Beleg gehört diese Quittung? (z. B. ER-2026-0033)", "") || "").trim(); if (!zu) return; const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(id)}/als-nachweis`, { zu }); if (AKTIV === "belege") renderBelege(); return blDetail(r && r.ok ? zu.toUpperCase() : id, r && r.ok ? `Als Zahlungsnachweis an ${zu.toUpperCase()} gehängt; ${id} ist verworfen (Datei bleibt archiviert).` : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "bl-verwerfen": { const grund = prompt("Warum ist das kein Beleg? (z. B. versehentlich hochgeladen)", ""); if (!grund) return; const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(id)}/verwerfen`, { grund }); if (AKTIV === "belege") renderBelege(); return blDetail(id, r && r.ok ? "Verworfen — die Datei bleibt archiviert." : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "re-neu": return reEditor("");
    case "re-alt-form": return reAltForm();
    case "fin-kalk": { try { localStorage.setItem("luna-fin-kalk", el.checked ? "an" : "aus"); } catch (e) {} return renderFinanzen(); }
    case "fin-kalk-export": { const box = el.closest(".v2-card-actions"); (box ? box.querySelectorAll("a[data-kalk-link]") : []).forEach(a => {
      const u2 = new URL(a.getAttribute("href"), location.origin); if (el.checked) u2.searchParams.set("kalkulatorisch", "1"); else u2.searchParams.delete("kalkulatorisch");
      a.setAttribute("href", u2.pathname + u2.search); }); return; }
    case "zeit-start": case "zeit-stopp": case "zeit-storno": case "zeit-km": case "zeit-eintragen": case "zeit-satz": { const r = await zeitAktion(act, id, val); zeitLaden(); return r; }
    case "zt-fenster": ladeZu(); ZEIT.ergebnis = null; return zeitFenster();
    case "zt-korr-form": return ztKorrForm(id, val);
    case "zt-korr-speichern": { const r = await jpost(`/api/finanzen/zeit/${encodeURIComponent(id)}/korrigieren`, { datum: $("#zk-datum").value, von: $("#zk-von").value, bis: $("#zk-bis").value, pause_min: $("#zk-pause").value, taetigkeit: $("#zk-taet").value, grund: $("#zk-grund").value.trim() });
      if (!r || r.ok === false) return kundenMsg("zk-msg", (r && r.hinweis) || "Fehler.", false); return abDetail(val, "Zeit korrigiert."); }
    case "zt-start": return zeitStart();
    case "zt-stopp": return zeitStopp();
    case "zt-neu": ZEIT.ergebnis = null; closeModal(); return AKTIV === "dash" ? renderDash() : undefined;
    case "zt-taet-chip": { const f = $("#zt-e-taet"); if (f) f.value = val; return; }
    case "zt-km": { const km = (($("#zt-km") || {}).value || "").trim(), taet = (($("#zt-e-taet") || {}).value || "").trim(), pause = (($("#zt-e-pause") || {}).value || "").trim();
      if (!km && !taet && !pause) return zeitNeuZeichnen("Bitte Tätigkeit, Pause oder km eintragen – oder „Fertig“.", true);
      const teile = [];
      if (taet || pause) { const r = await jpost(`/api/finanzen/zeit/${encodeURIComponent(id)}/details`, { ...(taet ? { taetigkeit: taet } : {}), ...(pause ? { pause_min: pause } : {}) });
        if (!r || r.ok === false) return zeitNeuZeichnen((r && r.hinweis) || "Fehler.", true); teile.push(taet ? `„${taet}“` : "", pause ? `${pause} min Pause` : ""); }
      if (km) { const r = await jpost(`/api/finanzen/zeit/${encodeURIComponent(id)}/fahrt`, { km }); if (!r || r.ok === false) return zeitNeuZeichnen((r && r.hinweis) || "Fehler.", true); teile.push(`${km} km`); }
      ZEIT.ergebnis = null; return zeitNeuZeichnen(`Gespeichert: ${teile.filter(Boolean).join(", ")}.`); }
    case "akte-hochladen": return akteHochladen(id);
    case "akte-zuordnen": return akteZuordnenForm(id);
    case "akte-zuordnen-ok": case "akte-zuordnen-keine": { const r = await jpost(`/api/crm/akte/${encodeURIComponent(id)}/zuordnen`, { firma: act === "akte-zuordnen-ok" ? $("#az-firma").value : "" });
      if (!r || !r.ok) return alert((r && r.hinweis) || "Fehler."); closeModal(); return renderDash(); }
    case "kunde-recherche": { el.disabled = true; el.textContent = "⏳ suche …"; const r = await jpost(`/api/crm/kunden/${encodeURIComponent(id)}/recherche`, {});
      return kundeDetail(id, !r || !r.ok ? ((r && r.hinweis) || "Suche fehlgeschlagen.") : Object.keys(r.vorschlaege || {}).length ? `${Object.keys(r.vorschlaege).length} Vorschlag/Vorschläge gefunden – bitte prüfen.` : "Nichts Passendes gefunden."); }
    case "kunde-vorschlag": { const r = await jpost(`/api/crm/kunden/${encodeURIComponent(id)}/vorschlaege`, val ? { felder: [val] } : {});
      return kundeDetail(id, r && r.ok ? `Übernommen: ${Object.keys(r.uebernommen || {}).join(", ") || "–"}.` : (r && r.hinweis) || "Fehler."); }
    case "kunde-vorschlag-weg": { const r = await jpost(`/api/crm/kunden/${encodeURIComponent(id)}/vorschlaege`, { verwerfen: true });
      return kundeDetail(id, r && r.ok ? "Vorschläge verworfen." : (r && r.hinweis) || "Fehler."); }
    case "lg-buchen": return lagerBuchen();
    case "re-alt-speichern": return reAltSpeichern();
    case "re-altmahn-form": return reAltMahnForm(id);
    case "re-mv-form": return reMvForm(id);
    case "re-mv-speichern": return reMvSpeichern(id);
    case "re-altmahn-speichern": return reAltMahnSpeichern(id);
    case "re-detail": return reDetail(id);
    case "re-bearbeiten": return reDetail(id);
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
    case "re-ware-form": return reWareForm(id);
    case "re-ware-speichern": {
      const dateien = await Promise.all([...(($("#rw-dateien") || {}).files || [])].slice(0, 5).map(blLesen));
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/ware-erhalten`, { datum: $("#rw-datum").value, text: $("#rw-text").value.trim(),
        wert_marke: $("#rw-marke").value.trim(), wert_nachweis: $("#rw-nachweis").value.trim(), verwendung: $("#rw-verw").value,
        kategorie: $("#rw-verw").value === "content" ? $("#rw-kat").value : "", nutzungsdauer_jahre: $("#rw-nd").value, nachweise: dateien });
      if (!r || !r.ok) return kundenMsg("rw-msg", (r && r.hinweis) || "Fehler.", false);
      if (AKTIV === "rechnungen") renderRechnungen(); if (AKTIV === "finanzen") renderFinanzen();
      const text = r.verwendung === "leihgabe" ? "Leihgabe dokumentiert – keine Einnahme, nichts gebucht."
        : `Ware-Eingang gebucht: ${cent2eur(r.wert_cent)} Einnahme` + (r.verwendung === "content" ? ` + gleiche Anschaffung (${BL_KAT[r.kategorie] || r.kategorie})` : " (privat behalten)") + ".";
      return reDetail(id, text);
    }
    case "re-ware-storno": {
      const grund = prompt("Ware-Eingang stornieren — Grund:", ""); if (!grund) return;
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/ware-stornieren`, { grund });
      return reDetail(id, r && r.ok ? "Ware-Eingang storniert — bleibt sichtbar, zählt nicht mehr." : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "an-ware-alles": {
      const t = [...document.querySelectorAll("#an-summe-box .v2-kv b")]; const g = t.length ? t[[...document.querySelectorAll("#an-summe-box .v2-kv span")].findIndex(s => s.textContent.includes("Gesamtbetrag"))] : null;
      if (g) { $("#an-ware-wert").value = g.textContent.replace(/[^\d,.-]/g, ""); anSumme(); } return;
    }
    case "ma-form": return maForm(id);
    case "ma-erstellen": {
      const frist = Number(($("#ma-frist") || {}).value) || 7;
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/mahnung`, { frist_tage: frist, bestaetigt: true });
      if (!r || !r.ok) return kundenMsg("ma-msg", (r && r.hinweis) || "Fehler.", false);
      if (AKTIV === "rechnungen") renderRechnungen();
      await reDetail(id, `${r.nummer} festgeschrieben — jetzt prüfen und senden.`); return maSendenVorschau(r.nummer);
    }
    case "ma-senden": return maSendenVorschau(id, val === "erneut");
    case "ma-senden-jetzt": {
      const r = await jpost(`/api/finanzen/mahnungen/${encodeURIComponent(id)}/senden`, { an: $("#mas-an").value.trim(), betreff: $("#mas-betreff").value.trim(), text: $("#mas-text").value, bestaetigt: true, erneut: val === "erneut" });
      if (!r || !r.ok) return kundenMsg("mas-msg", (r && r.hinweis) || "Fehler.", false);
      if (AKTIV !== "rechnungen" && !RE_DETAIL) return maDetail(id, `Mahnung ${id} an ${r.an} ${val === "erneut" ? "erneut " : ""}gesendet.`);
      return reDetail(RE_DETAIL && RE_DETAIL.rechnung ? RE_DETAIL.rechnung.nummer : id, `Mahnung ${id} an ${r.an} ${val === "erneut" ? "erneut " : ""}gesendet.`);
    }
    case "re-bezahlt": {
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/bezahlt`, { datum: $("#rez-datum").value, betrag: $("#rez-betrag").value.trim() || null, notiz: $("#rez-notiz").value.trim(), zuordnung_jahr: zehnTageWert("rez-zuord"), nebenforderung: ($("#rez-neben") || {}).value || null });
      if (!r || !r.ok) return kundenMsg("rez-msg", (r && r.hinweis) || "Fehler.", false);
      if (AKTIV === "rechnungen") renderRechnungen(); return reDetail(id, [r.rest_cent > 0 ? `Zahlung ${cent2eur(r.betrag_cent)} gebucht — offen: ${cent2eur(r.rest_cent)}.` : "Vollständig bezahlt.", ...(r.hinweise || [])].join("\n"));
    }
    case "re-storno": {
      const grund = prompt("Stornieren — Grund (erscheint auf der Stornorechnung):", ""); if (!grund) return;
      const korrektur = confirm("Direkt einen Korrektur-Entwurf mit denselben Positionen anlegen?");
      const r = await jpost(`/api/finanzen/rechnungen/${encodeURIComponent(id)}/stornieren`, { grund, korrektur });
      if (AKTIV === "rechnungen") renderRechnungen();
      if (!r || !r.ok) return reDetail(id, (r && r.hinweis) || "Fehler.", true);
      return r.korrektur_entwurf ? reDetail(r.korrektur_entwurf, `Stornorechnung ${r.storno} erstellt – der Korrektur-Entwurf ist offen und kann bearbeitet werden.`) : reDetail(r.storno, [`Stornorechnung ${r.storno} erstellt.`, ...(r.hinweise || [])].join("\n"));
    }
    case "re-box-zu": { const bx = $("#re-aktion-box"); if (bx) bx.innerHTML = ""; return; }
    case "bl-posten": { const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(id)}/posten`, { zeilen: ($("#bl-posten") || {}).value || "", zahlungs_id: ($("#bl-posten-id") || {}).value || "", waehrung: ($("#bl-posten-wg") || {}).value || "USD" }); return blDetail(id, r && r.ok ? "Zeiträume gespeichert." : (r && r.hinweis) || "Fehler.", !(r && r.ok)); }
    case "bl-zweck": { const r = await jpost(`/api/finanzen/belege/${encodeURIComponent(id)}/zweck`, { zweck: ($("#bl-zweck") || {}).value || "" }); return blDetail(id, r && r.ok ? "Zweck gespeichert." : (r && r.hinweis) || "Fehler.", !(r && r.ok)); }
    case "ab-vorkasse": { const r = await jpost(`/api/finanzen/rechnungen/aus-auftrag/${encodeURIComponent(id)}`, { vorkasse: true }); if (!r || !r.ok) return abDetail(id, (r && r.hinweis) || "Fehler.", true); return reDetail(r.entwurf_id, r.vorhanden ? "Es gab schon einen Vorkasse-Entwurf — hier ist er." : "Vorkasse-Rechnung als Entwurf angelegt. Prüfen und festschreiben — dann legt LUNA den Payment-Check in den Kalender."); }
    case "ab-rechnung": { const r = await jpost(`/api/finanzen/rechnungen/aus-auftrag/${encodeURIComponent(id)}`, {}); if (!r || !r.ok) return abDetail(id, (r && r.hinweis) || "Fehler.", true); return reEditor(r.entwurf_id); }
    case "ab-neu": return abNeu(id, val === "annehmen");
    case "ab-anlegen": return abAnlegen(id, val === "annehmen");
    case "ab-detail": return abDetail(id);
    case "ab-senden": return abSendenVorschau(id);
    case "ab-senden-jetzt": return abSendenJetzt(id);
    case "ab-senden-abbruch": { const bx = $("#ab-senden-box"); if (bx) bx.innerHTML = ""; return; }
    case "ab-speichern": { const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}`, { auftrag: { leistung_von: $("#abe-von").value, leistung_bis: $("#abe-bis").value, notiz: $("#abe-notiz").value.trim() } }); if (!r || !r.ok) return kundenMsg("abe-msg", (r && r.hinweis) || "Fehler.", false); return abDetail(id, r.geaendert && r.geaendert.length ? "Gespeichert." : "Keine Änderung."); }
    case "ab-geliefert-form": { const box = $("#ab-senden-box"); if (box) { box.innerHTML = `<h3>Als geliefert markieren</h3>${lfFormular(id, true)}`; box.scrollIntoView({ block: "nearest" }); } return; }
    case "ab-geliefert": { el.disabled = true; try { await lfSpeichern(id, false);
        const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}/status`, { status: "erledigt", datum: ($("#lf-datum-st") || {}).value || "" });
        if (!r || r.ok === false) throw new Error((r && r.hinweis) || "Status nicht gesetzt.");
        if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote(); glockeAktualisieren();
        return abDetail(id, "Als geliefert markiert — bereit für die Rechnung. Zeit ist für diesen Auftrag jetzt gesperrt."); }
      catch (e) { el.disabled = false; return kundenMsg("lf-msg", e.message, false); } }
    case "ber-vorschau": { const w = window.open("about:blank", "_blank"); if (await berSpeichern(id)) { if (w) w.location = `/api/crm/auftraege/${encodeURIComponent(id)}/bericht/pdf`; kundenMsg("ber-msg", "Gespeichert.", true); } else if (w) w.close(); return; }
    case "ber-senden-form": return berSendenForm(id);
    case "ber-senden": return berSenden(id);
    case "ber-entfaellt": { const g = prompt("Warum ist kein Bericht nötig? (z. B. reiner Dreh ohne Postings)", ""); if (!g) return;
      const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}/bericht/entfaellt`, { grund: g }); return abDetail(id, r && r.ok ? "Vermerkt: kein Bericht nötig." : (r && r.hinweis) || "Fehler.", !(r && r.ok)); }
    case "zt-pos-speichern": { const r = await jpost(`/api/finanzen/zeit/${encodeURIComponent(id)}/details`, { position: $("#zk-pos").value });
      if (!r || r.ok === false) return kundenMsg("zk-msg", (r && r.hinweis) || "Fehler.", false); return abZeitLaden(val); }
    case "kat-ist": { const z = el.closest(".v2-kat-zeile"), i = z && $(".kat-kontakte", z); if (i) { i.value = val; i.classList.add("v2-erkannt"); i.focus(); } return; }
    case "ab-folge": { const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}/folge-erledigt`, {}); return abDetail(id, r && r.ok ? "Folgeauftrag-Nachfassen erledigt." : (r && r.hinweis) || "Fehler.", !(r && r.ok)); }
    case "ber-stimme": { if (!confirm("Bitte um eine Kundenstimme als Gmail-Entwurf in LUNAs Konto anlegen? (Es wird nichts gesendet.)")) return;
      const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}/kundenstimme-entwurf`, {});
      return kundenMsg("ber-msg2", r && r.ok ? `Entwurf an ${r.an} liegt in Gmail (LUNAs Konto) – dort prüfen und selbst senden.` : (r && r.hinweis) || "Fehler.", !!(r && r.ok)); }
    case "bv-oeffnen": return belegVerfolgung(id);
    case "konzept": return konzeptFenster(id, val);
    case "kz-vid": case "kz-vid-ueb": case "kz-vid-weg": return kzVid(act, id, val);
    case "kz-tab": case "kz-briefing": case "kz-idee": case "kz-idee-status": case "kz-skript": case "kz-szene": case "kz-erledigt": case "kz-szene-weg":
    case "kz-dreh": case "kz-freigabe": case "kz-senden-form": case "kz-senden": case "kz-drehmodus": return kzAktion(act, id, val, el);
    case "dreh-haken": { const v = KZ.d ? KZ.d.kontext.vorgang : ""; const d = v ? null : await jget(`/api/crm/konzept/${encodeURIComponent(val)}`);
      const vg = v || (d && d.kontext.vorgang); await jpost(`/api/crm/konzept/${encodeURIComponent(vg)}/erledigt`, { id, erledigt: !el.dataset.ok }); return drehModus(val); }
    case "vt-clo-version": case "vt-entwuerfe": case "vt-detail": case "vt-status": case "vt-pruef-form": case "vt-pruefen": case "vt-vergleich": case "vt-neu": case "vt-par-neu": case "vt-speichern": return vtAktion(act, id, val);
    case "vt-par-weg": { const z = el.closest(".v2-vt-feld"); if (z) z.remove(); return; }
    case "ma-detail": return maDetail(id);
    case "mp-oeffnen": case "mp-eml": case "mp-adresse": case "mp-versendet": return mpAktion(act, id, val);
    case "tb-art": case "tb-neu": case "tb-weg": case "tb-standard": case "tb-ph": case "tb-speichern": return tbAktion(act, id, val, el);
    case "ag-profil": return agentProfil(id);
    case "bl-reiter": { const w = el.closest(".v2-beleg"); if (!w) return; w.dataset.tab = val; w.querySelectorAll(".v2-beleg-reiter button").forEach(b => b.classList.toggle("on", b.dataset.val === val)); return; }
    case "zt-auswertung": return val === "frei" ? ztAuswertung("frei", $("#aw-von").value, $("#aw-bis").value) : ztAuswertung(val);
    case "pz-speichern": case "pz-aus": return rePzSpeichern(id, act === "pz-aus");
    case "cp-ansicht": CP.ansicht = val; try { localStorage.setItem("luna-cp-ansicht", val); } catch { } return renderContentplan();
    case "cp-blaettern": { const t = CP.tag || heuteIso(), n = Number(val);
      if (!n) CP.tag = heuteIso(); else if (CP.ansicht === "woche") CP.tag = cpPlus(t, 7 * n); else { const d = cpDatum(t.slice(0, 8) + "01"); d.setMonth(d.getMonth() + n); CP.tag = cpIso(d); }
      return renderContentplan(); }
    case "cp-neu": if (val && CP.ansicht === "monat" && innerWidth <= 700) { CP.ansicht = "woche"; CP.tag = val; return renderContentplan(); }   // Handy: Tag antippen = Woche
      return cpForm("", val);
    case "cp-eintrag": return cpEintragOeffnen(id);
    case "cp-speichern": { el.disabled = true; const ok = await cpSpeichern(id, val); if (!ok) el.disabled = false; return; }
    case "cp-serie-auslassen": case "cp-serie-ende": { const [sid, tag] = id.split("@"), ende = act === "cp-serie-ende";
      if (!confirm(ende ? `Serie ab ${datumDe(tag)} beenden? Frühere Termine bleiben.` : `Termin am ${datumDe(tag)} auslassen?`)) return;
      const r = ende ? await jpost(`/api/contentplan/serie/${encodeURIComponent(sid)}/beenden`, { ab: tag })
        : await jpost(`/api/contentplan/serie/${encodeURIComponent(sid)}/termin/${tag}`, { entfaellt: true });
      closeModal(); return renderContentplan(r && r.ok !== false ? (ende ? "Serie beendet." : "Termin ausgelassen.") : ((r && r.hinweis) || "Fehler.")); }
    case "cp-entfernen": { if (!confirm("Diesen Eintrag aus dem Content-Plan entfernen?")) return; const r = await jpost(`/api/contentplan/${encodeURIComponent(id)}/entfernen`); closeModal(); return renderContentplan(r && r.ok !== false ? "Eintrag entfernt." : ""); }
    case "cp-anlaesse": return cpAnlaesse();
    case "cp-anlass-neu": { const f = $("#cp-anl"), daten = Object.fromEntries([...f.querySelectorAll("[name]")].map(i => [i.name, i.value.trim()]));
      const r = await jpost("/api/contentplan/anlass", daten); if (!r || r.ok === false) { const m = $("#cp-anl-msg"); m.className = "v2-msg err"; m.textContent = (r && r.hinweis) || "Keine Verbindung."; return; }
      closeModal(); return renderContentplan("Anlass angelegt."); }
    case "cp-anlass-weg": { if (!confirm("Diesen Anlass entfernen?")) return; await jpost(`/api/contentplan/anlass/${encodeURIComponent(id)}/entfernen`); closeModal(); return renderContentplan("Anlass entfernt."); }
    case "cp-vorschlag": return cpVorschlag(el);
    case "cp-vorschlag-zu": { const b = $("#cp-vorschlag-box"); if (b) b.innerHTML = ""; return; }
    case "cp-v-uebernehmen": { const x = (CP.vorschlaege || [])[Number(val)]; if (!x) return; el.disabled = true;
      const r = await jpost("/api/contentplan", { datum: x.datum, kanal: x.kanal, format: x.format, titel: x.titel, notiz: x.notiz || "", status: "idee" });
      if (!r || r.ok === false) { el.disabled = false; alert((r && r.hinweis) || "Keine Verbindung."); return; }
      el.textContent = "✓ übernommen"; const box = $("#cp-vorschlag-box"), html = box ? box.innerHTML : "";
      await renderContentplan(); const nb = $("#cp-vorschlag-box"); if (nb) nb.innerHTML = html; return; }
    case "po-form-v": case "po-form-k": case "po-form-l": return poForm(id, val, act.slice(-1));
    case "po-speichern-v": case "po-speichern-k": case "po-speichern-l": { el.disabled = true; await poSpeichern(id, val, act.slice(-1)); el.disabled = false; return; }
    case "lf-speichern": { el.disabled = true; try { await lfSpeichern(id, true); return abDetail(id, "Lieferung gespeichert."); }
      catch (e) { el.disabled = false; return kundenMsg("lf-msg", e.message, false); } }
    case "lf-entfernen": { const grund = prompt("Lieferung samt Dateien entfernen – Grund:", ""); if (!grund) return;
      const r = await jpost(`/api/crm/lieferungen/${encodeURIComponent(id)}/entfernen`, { grund }); return abDetail(val, r && r.ok ? "Lieferung entfernt." : (r && r.hinweis) || "Fehler.", !(r && r.ok)); }
    case "ab-wieder-offen": { const grund = prompt("Auftrag wieder öffnen (z. B. Nachlieferung) – Grund:", ""); if (!grund) return;
      const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}/status`, { status: "beauftragt", grund });
      if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote();
      return abDetail(id, r && r.ok ? "Wieder geöffnet — Zeit ist wieder buchbar." : (r && r.hinweis) || "Fehler.", !(r && r.ok)); }
    case "ab-status": {
      const grund = prompt(val === "erledigt" ? "Erledigt — Notiz (optional):" : "Stornieren — Grund:", ""); if (grund === null) return;
      const r = await jpost(`/api/crm/auftraege/${encodeURIComponent(id)}/status`, { status: val, grund });
      if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote();
      return abDetail(id, r && r.ok ? (val === "erledigt" ? "Als erledigt markiert — bereit für die Rechnung." : "Storniert.") : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "an-senden": return anSendenVorschau(id, val === "erneut");
    case "an-senden-jetzt": return anSendenJetzt(id, val === "erneut");
    case "an-senden-abbruch": { const bx = $("#an-senden-box"); if (bx) bx.innerHTML = ""; return; }
    case "an-erinnerungen": {
      flash("⏳ …"); const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/erinnerungen`, {});
      return anDetail(id, r && r.ok ? [...(r.termine || []).map(t => `📅 ${t.titel} (${new Date(t.datum).toLocaleDateString("de-DE")})`), ...(r.hinweise || [])].join("\n") || "Erledigt." : ((r && r.hinweis) || "Fehler."), !(r && r.ok) || !(r.termine || []).length && (r.hinweise || []).some(h => h.startsWith("Kalender") || h.startsWith("Google")));
    }
    case "an-status": {
      const grund = prompt(val === "angenommen" ? "Angenommen — Notiz (optional, z. B. „per Mail vom …“):" : "Abgelehnt — Grund (optional):", ""); if (grund === null) return;
      const r = await jpost(`/api/crm/angebote/${encodeURIComponent(id)}/status`, { status: val, grund });
      if ((AKTIV === "angebote" || AKTIV === "auftraege")) renderAngebote();
      return anDetail(id, r && r.ok ? [val === "angenommen" ? "Angenommen." : "Abgelehnt.", ...(r.hinweise || [])].join("\n") : ((r && r.hinweis) || "Fehler."), !(r && r.ok));
    }
    case "abo-neu": return aboForm("", null);
    case "abo-detail": return aboDetail(id);
    case "abo-bearbeiten": return aboForm(id);
    case "abo-speichern": return aboSpeichern(id);
    case "abo-buchen": { const r = await jpost(`/api/finanzen/abos/${encodeURIComponent(id)}/buchen`, { faellig: val }); if (AKTIV === "finanzen") renderFinanzen(); return aboDetail(id, r && r.ok ? `Gebucht als ${r.eigenbeleg}.` : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "abo-skip": { const grund = prompt("Warum überspringen? (z. B. Gratismonat)", ""); if (!grund) return; const r = await jpost(`/api/finanzen/abos/${encodeURIComponent(id)}/ueberspringen`, { faellig: val, grund }); return aboDetail(id, r && r.ok ? "Übersprungen." : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "abo-beenden": { const ende = prompt("Abo endet zum (JJJJ-MM-TT):", heuteIso()); if (!ende) return; const grund = prompt("Grund (z. B. gekündigt):", "gekündigt") || ""; const r = await jpost(`/api/finanzen/abos/${encodeURIComponent(id)}/beenden`, { ende, grund }); if (AKTIV === "finanzen") renderFinanzen(); return aboDetail(id, r && r.ok ? "Abo beendet – es wird nichts mehr fällig." : ((r && r.hinweis) || "Fehler."), !(r && r.ok)); }
    case "abo-aus-firma": { const d = await jget("/api/crm/kunden/" + encodeURIComponent(id)); const f = d && d.firma, ab = d && d.buchungen && d.buchungen.abo; ABOS = await jget("/api/finanzen/abos") || ABOS; const letzte = ((d && d.buchungen && d.buchungen.belege) || [])[0] || {}; return aboForm("", { bezeichnung: letzte.text || (f && f.name) || "", firma: f && f.nummer, betrag_cent: ab && ab.monatlich_cent, turnus: "monatlich", kategorie: "", zahlungsweg: f && f.zahlungsweg, beleg_per_mail: true }); }
    case "vertrag-neu": { const box = $("#" + id); if (box) box.insertAdjacentHTML("beforeend", vertragZeile()); return; }
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
function connectSSE() { try { const es = new EventSource("/api/events"); es.onmessage = () => { if (AKTIV === "dash" && !EDIT2) renderDash(); clearTimeout(GLOCKE_T); GLOCKE_T = setTimeout(glockeAktualisieren, 10000); }; } catch { } }

/* =========================== Events + Boot =========================== */
document.addEventListener("click", (e) => {
  const at = $("#an-firma-treffer"); if (at && !at.hidden && !e.target.closest(".v2-auto-feld")) at.hidden = true;
  const ed = e.target.closest("[data-editdash]"); if (ed) { EDIT2 = !EDIT2; renderDash(); return; }
  const wh2 = e.target.closest("[data-whide2]"); if (wh2) { hideW2(wh2.dataset.whide2); return; }
  const wa2 = e.target.closest("[data-wadd2]"); if (wa2) { showW2(wa2.dataset.wadd2); return; }
  const ac0 = e.target.closest("[data-act]"); if (ac0) { handleAct(ac0.dataset.act, ac0); return; }  // Aktionen VOR Navigation (Inline-Buttons in klickbaren Kacheln)
  const g = e.target.closest("[data-go]"); if (g) { go(g.dataset.go); return; }
  const tb = e.target.closest("[data-tab]"); if (tb) { const [sec, id] = tb.dataset.tab.split(":"); go(sec, id); return; }
  const tc = e.target.closest("[data-toggle-chat]"); if (tc) { ladeZu(); toggleChat(); return; }
  const orb = e.target.closest("#v2-orb"); if (orb) { toggleVoice(); return; }
  const holo = e.target.closest("#luna-holo"); if (holo) { toggleVoice(); return; }
  const ht = e.target.closest("#v2-holo-toggle"); if (ht) { setAvatarPref(PREFS.avatar === "hologramm" ? "orb" : "hologramm"); return; }
  const th = e.target.closest("#v2-theme"); if (th) { toggleTheme(); return; }
  if (e.target.closest("#v2-burger")) { ladeAuf(); return; }
  if (e.target.closest("#v2-lade-zu") || e.target.closest("#v2-schleier")) { ladeZu(); return; }
  const mc = e.target.closest("[data-modal-close]"); if (mc) { closeModal(); return; }
  const ac = e.target.closest("[data-act]"); if (ac) { handleAct(ac.dataset.act, ac); return; }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { ladeZu(); closeModal(); return; }
  if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey && !(e.target.closest && e.target.closest("input, textarea, select, [contenteditable]"))) {
    e.preventDefault(); return sucheOeffnen(); }                    // GLOBALE_SUCHE: Taste „/“
  if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches('.v2-tile.klick[role="button"]')) {
    e.preventDefault(); const el = e.target;
    if (el.dataset.go) go(el.dataset.go); else if (el.dataset.tab) { const [s, i] = el.dataset.tab.split(":"); go(s, i); }
  }
  if (e.key === "Enter" && e.target.matches && e.target.matches(".v2-todo-titel")) { e.preventDefault(); handleAct(e.target.dataset.act, e.target); }
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
  buildShell(); go("dash"); connectSSE(); applyAvatar(); passkeyAngebot();
  glockeAktualisieren(); setInterval(glockeAktualisieren, 5 * 60 * 1000);
  zeitLaden(); setInterval(zeitLaden, 60 * 1000);                        // auch per Telegram gestartete Zeiten
})();
