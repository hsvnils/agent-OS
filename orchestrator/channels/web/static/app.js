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
  finance: { icon: "💶", titel: "Finanzen", badge: () => 0, render: renderFinance },
};

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

function renderAuftraege() {
  if (!STATE.antraege.length) return `<div class="app"><div class="leer">Keine offenen Aufträge. 🎉<br>LUNA meldet sich, wenn etwas ansteht.</div></div>`;
  const cards = STATE.antraege.map(a => {
    const lang = a.beschreibung.length > 240;
    const freigeben = a.status === "eingereicht"
      ? `<button class="btn ok" data-act="freigeben" data-id="${esc(a.id)}">✓ Freigeben</button>` : "";
    const ablehnen = (a.status === "eingereicht" || a.status === "freigegeben")
      ? `<button class="btn warn" data-act="ablehnen" data-id="${esc(a.id)}">✕ Ablehnen</button>` : "";
    return `<div class="card">
      <div class="head"><span class="badge ${esc(a.status)}">${esc(a.status)}</span><b class="titel" data-detail="${esc(a.id)}" title="Details anzeigen">${esc(a.titel)}</b></div>
      <div class="meta">von ${esc(a.von)}${a.kategorie ? " · " + esc(a.kategorie) : ""} · ${esc(a.id)}</div>
      <div class="desc">${esc(a.beschreibung) || "<i>keine Beschreibung</i>"}</div>
      ${lang ? `<div class="mehr" data-mehr>mehr anzeigen ▾</div>` : ""}
      <div class="actions">
        ${freigeben}${ablehnen}
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
async function aktion(id, akt, btn) {
  let body = {};
  if (akt === "ablehnen") { const g = prompt("Grund der Ablehnung?", ""); if (g === null) return; body = { grund: g }; }
  if (akt === "loeschen" && !confirm("Antrag wirklich löschen?")) return;
  // Mehr-Info ist jetzt agentisch (CTO/CFO + ggf. Recherche) -> kann ein paar Sekunden dauern.
  let alt;
  if (btn) { alt = btn.textContent; btn.disabled = true; if (akt === "mehr-info") btn.textContent = "⏳ Agenten arbeiten..."; }
  try {
    const r = await fetch(`/api/antraege/${encodeURIComponent(id)}/${akt}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const d = await r.json();
    if (akt === "mehr-info" && d.bewertung) alert("LUNA-Bewertung:\n\n" + d.bewertung);
    if (d.state) { STATE = d.state; renderOffene(); updateBadges(); }
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
  const det = e.target.closest("[data-detail]");
  if (det) { openDetail(det.dataset.detail); return; }
  const btn = e.target.closest("[data-act]");
  if (btn) { aktion(btn.dataset.id, btn.dataset.act, btn); return; }
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

// ---- Live-Gespraech mit LUNA (Browser-Ohren + ElevenLabs-Stimme) -----------
// Der Orb ist die SPRECHENDE Live-LUNA: antippen -> freihaendiges Gespraech (du sprichst,
// die echte LUNA mit Tools/Persona antwortet gesprochen). Der Tipp-Chat ist die Rueckfallebene.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const SPEECH = { canListen: !!SR, canSpeak: "speechSynthesis" in window };
const VOICE = { active: false, rec: null, audio: null };
const LUNA_HISTORY = [];

function setOrb(s) { const o = document.getElementById("luna-orb"); if (o) o.className = s; }
function voiceStatus(t) { const el = document.getElementById("voice-status"); if (el) el.textContent = t; }
function voiceToggleUI() { const b = document.getElementById("voice-toggle");
  if (b) { b.classList.toggle("on", VOICE.active); b.textContent = VOICE.active ? "⏹ Gespräch beenden" : "🎙️ Gespräch starten"; } }

function stopAudio() {
  try { if (VOICE.audio) { VOICE.audio.pause(); VOICE.audio = null; } } catch {}
  try { window.speechSynthesis && window.speechSynthesis.cancel(); } catch {}
}

// LUNA spricht: erst ElevenLabs (/api/tts) probieren, sonst Browser-Stimme. Danach im Gespraech weiter zuhoeren.
async function lunaSpeak(text) {
  setOrb("speaking"); voiceStatus("LUNA spricht…");
  let gesprochen = false;
  try {
    const r = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }) });
    if (r.ok && (r.headers.get("content-type") || "").includes("audio")) {
      const url = URL.createObjectURL(await r.blob());
      await new Promise((res) => {
        const a = new Audio(url); VOICE.audio = a;
        a.onended = a.onerror = () => { URL.revokeObjectURL(url); if (VOICE.audio === a) VOICE.audio = null; res(); };
        a.play().catch(() => res());
      });
      gesprochen = true;
    }
  } catch { /* Netz/Fehler -> Browser-Stimme */ }
  if (!gesprochen && SPEECH.canSpeak) {
    await new Promise((res) => {
      try { window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text); u.lang = "de-DE"; u.rate = 1.04;
        const v = window.speechSynthesis.getVoices().find(x => x.lang && x.lang.startsWith("de"));
        if (v) u.voice = v; u.onend = u.onerror = res; window.speechSynthesis.speak(u);
      } catch { res(); }
    });
  }
  if (VOICE.active) startListening(); else setOrb(WINS.luna ? "listening" : "idle");
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
  if (!WINS.luna) openLuna(); else WINS.luna.focus();
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
    : `<span class="voice-status">Sprache braucht HTTPS + Chrome/Safari</span>`;
  win.body.innerHTML = `<div class="chat">
    <div class="voice-bar">${voiceBtn}<span id="voice-status" class="voice-status">${VOICE.active ? "Ich höre…" : "Sprich mit LUNA oder tippe."}</span></div>
    <div class="chat-msgs" id="chat-msgs">${begruessung}${msgs}</div>
    <form class="chat-form" id="chat-form"><input id="chat-in" placeholder="Schreib LUNA..." autocomplete="off"><button type="submit">➤</button></form></div>`;
  const form = win.body.querySelector("#chat-form"), inp = win.body.querySelector("#chat-in");
  const vt = win.body.querySelector("#voice-toggle"); if (vt) vt.onclick = toggleVoice;
  form.onsubmit = (e) => {
    e.preventDefault();
    const t = inp.value.trim(); if (!t) return;
    inp.value = "";
    sendeAnLuna(t, VOICE.active);  // getippt: nur sprechen, wenn Gespraech aktiv
    inp.focus();
  };
  if (!VOICE.active) setOrb("idle");
  setTimeout(() => inp.focus(), 50);
}

// Schickt eine Nutzer-Aeusserung an LUNA. sprich=true -> Antwort wird gesprochen (+ Gespraech laeuft weiter).
async function sendeAnLuna(text, sprich) {
  addMsg("user", text);
  // Kontext-Befehl? ("zeig mir die Aufträge") -> App einblenden, auch per Sprache.
  const app = versucheKontextBefehl(text);
  if (app) { const s = `Zeige dir „${app}".`; typeLunaText(s); if (sprich) lunaSpeak(s); else setOrb(WINS.luna ? "listening" : "idle"); return; }
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
buildDock(); clock(); setInterval(clock, 1000);
document.getElementById("luna-orb").onclick = toggleVoice;  // Orb antippen = Live-Gespraech starten/stoppen
refresh().then(() => { openApp("auftraege"); });
connectSSE();
