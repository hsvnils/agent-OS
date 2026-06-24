// Browser-Client fuer den Live-Voice-Kanal.
// Verbindet per WebRTC mit dem lokalen Server, zeigt Zustaende (hoert zu / denkt / spricht)
// und rendert Panel-Einblendungen (show_panel) aus Server-Nachrichten.
//
// API: Pipecat JS SDK -- Hauptklasse PipecatClient (@pipecat-ai/client-js),
// Transport SmallWebRTCTransport (@pipecat-ai/small-webrtc-transport).

import { PipecatClient } from "https://esm.sh/@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "https://esm.sh/@pipecat-ai/small-webrtc-transport";

const orb = document.getElementById("orb");
const stateEl = document.getElementById("state");
const connectBtn = document.getElementById("connect");
const panels = document.getElementById("panels");
const voiceSel = document.getElementById("voice");
const voiceDesc = document.getElementById("voice-desc");
const voiceHint = document.getElementById("voice-hint");
let voiceList = [];

function showVoiceDesc(id) {
  const v = voiceList.find((x) => x.id === id);
  voiceDesc.textContent = v ? v.beschreibung : "";
}

async function initVoices() {
  try {
    const d = await (await fetch("/api/voices")).json();
    voiceList = d.voices || [];
    voiceSel.innerHTML = "";
    for (const v of voiceList) {
      const opt = document.createElement("option");
      opt.value = v.id;
      opt.textContent = v.name;
      if (v.id === d.selected) opt.selected = true;
      voiceSel.appendChild(opt);
    }
    showVoiceDesc(d.selected);
  } catch (e) {
    voiceDesc.textContent = "Stimmen konnten nicht geladen werden.";
  }
}

voiceSel.addEventListener("change", async () => {
  const id = voiceSel.value;
  showVoiceDesc(id);
  try {
    await fetch("/api/voice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voice_id: id }),
    });
    voiceHint.textContent = "Gespeichert — wird beim nächsten Gespräch aktiv.";
  } catch (e) {
    voiceHint.textContent = "Speichern fehlgeschlagen.";
  }
});

initVoices();

let client = null;
let connected = false;

function setState(s, label) {
  orb.className = "orb" + (s ? " " + s : "");
  stateEl.textContent = label;
}

function renderPanel(panel) {
  const el = document.createElement("div");
  el.className = "panel";
  const h = document.createElement("h2");
  h.textContent = panel.title || "Panel";
  el.appendChild(h);

  if (panel.type === "kostenuebersicht") {
    el.appendChild(kv("Monatsbudget", panel.monatsbudget || "unbekannt"));
    if (panel.soll_ist && panel.soll_ist.columns?.length) {
      el.appendChild(makeTable(panel.soll_ist.columns, panel.soll_ist.rows || []));
    }
    if (panel.hinweis) el.appendChild(small(panel.hinweis));
    if (panel.quellen) el.appendChild(small("Quellen: " + panel.quellen.join(", ")));
  } else if (panel.type === "tabelle") {
    el.appendChild(makeTable(panel.columns || [], panel.rows || []));
  } else { // markdown / text
    const p = document.createElement("div");
    p.textContent = panel.markdown || "";
    el.appendChild(p);
  }
  panels.prepend(el);
}

function kv(k, v) {
  const d = document.createElement("div"); d.className = "kv";
  const b = document.createElement("b"); b.textContent = k;
  const s = document.createElement("span"); s.textContent = v;
  d.append(b, s); return d;
}
function makeTable(cols, rows) {
  const t = document.createElement("table");
  const thead = document.createElement("tr");
  cols.forEach(c => { const th = document.createElement("th"); th.textContent = c; thead.appendChild(th); });
  t.appendChild(thead);
  rows.forEach(r => {
    const tr = document.createElement("tr");
    r.forEach(c => { const td = document.createElement("td"); td.textContent = c; tr.appendChild(td); });
    t.appendChild(tr);
  });
  return t;
}
function small(text) {
  const s = document.createElement("small"); s.textContent = text;
  s.style.display = "block"; s.style.marginTop = "8px"; return s;
}

function handleServerMessage(data) {
  // Panel-Anweisung vom Head of Agents (show_panel). Robust gegen Verschachtelung.
  const msg = data?.data ?? data?.message ?? data;
  if (msg && msg.kind === "panel" && msg.panel) renderPanel(msg.panel);
}

async function connect() {
  client = new PipecatClient({
    transport: new SmallWebRTCTransport({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    }),
    enableMic: true,
    enableCam: false,
    callbacks: {
      onConnected: () => { connected = true; connectBtn.textContent = "Beenden"; connectBtn.classList.add("stop"); setState("listening", "verbunden — hört zu"); },
      onDisconnected: () => { connected = false; connectBtn.textContent = "Gespräch starten"; connectBtn.classList.remove("stop"); setState("", "getrennt"); },
      onBotReady: () => setState("listening", "bereit — hört zu"),
      onUserStartedSpeaking: () => setState("listening", "hört zu …"),
      onUserStoppedSpeaking: () => setState("thinking", "denkt nach …"),
      onBotStartedSpeaking: () => setState("speaking", "spricht …"),
      onBotStoppedSpeaking: () => setState("listening", "hört zu"),
      onTrackStarted: (track, participant) => {
        // Bot-Audiospur abspielen (der Client spielt sie nicht automatisch ab).
        if (track.kind !== "audio") return;
        if (participant && participant.local) return;  // eigenes Mikrofon nicht zurueckspielen
        let el = document.getElementById("bot-audio");
        if (!el) {
          el = document.createElement("audio");
          el.id = "bot-audio";
          el.autoplay = true;
          document.body.appendChild(el);
        }
        el.srcObject = new MediaStream([track]);
        el.play?.().catch((err) => console.warn("Audio-Wiedergabe blockiert:", err));
      },
      onServerMessage: handleServerMessage,
      onError: (e) => {
        const msg = e?.message || e?.data?.message || e?.data?.error ||
                    (e?.data ? JSON.stringify(e.data) : String(e));
        console.error("Pipecat-Fehler:", e);
        setState("", "Fehler: " + msg);
      },
    },
  });
  setState("thinking", "verbinde …");
  try {
    await client.connect({ webrtcUrl: window.location.origin + "/api/offer" });
  } catch (e) {
    setState("", "Verbindung fehlgeschlagen: " + (e?.message || e));
    console.error("connect() fehlgeschlagen:", e);
  }
}

async function disconnect() { if (client) await client.disconnect(); }

connectBtn.addEventListener("click", () => (connected ? disconnect() : connect()));
