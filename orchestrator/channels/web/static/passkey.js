// Passkey/Face ID fuer LUNA-OS (LUNA_OS_UI_ROADMAP Etappe 6) -- gemeinsam fuer Login-Seite und Einstellungen.
// Der Server liefert die WebAuthn-Optionen als JSON (base64url); hier werden sie in Binaerdaten umgewandelt und die
// Antwort des Geraets wieder als JSON zurueckgeschickt. iOS verlangt die Face-ID-Abfrage direkt im Tipp -- deshalb
// werden die Optionen vorab geholt ("vorbereiten...") und beim Tipp sofort verwendet.
window.LunaPasskey = (() => {
  const b2a = (s) => { s = String(s).replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "=";
    const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u.buffer; };
  const a2b = (buf) => { const u = new Uint8Array(buf); let s = ""; for (const c of u) s += String.fromCharCode(c);
    return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); };
  const unterstuetzt = () => !!(window.PublicKeyCredential && navigator.credentials && location.protocol === "https:");
  const erstellOpt = (o) => ({ ...o, challenge: b2a(o.challenge), user: { ...o.user, id: b2a(o.user.id) },
    excludeCredentials: (o.excludeCredentials || []).map(c => ({ ...c, id: b2a(c.id) })) });
  const holOpt = (o) => ({ ...o, challenge: b2a(o.challenge), allowCredentials: (o.allowCredentials || []).map(c => ({ ...c, id: b2a(c.id) })) });
  function alsJson(cred) {
    const r = cred.response;
    const out = { id: cred.id, rawId: a2b(cred.rawId), type: cred.type,
      clientExtensionResults: cred.getClientExtensionResults ? cred.getClientExtensionResults() : {},
      authenticatorAttachment: cred.authenticatorAttachment || undefined,
      response: { clientDataJSON: a2b(r.clientDataJSON) } };
    if (r.attestationObject) { out.response.attestationObject = a2b(r.attestationObject); if (r.getTransports) out.response.transports = r.getTransports(); }
    if (r.authenticatorData) { out.response.authenticatorData = a2b(r.authenticatorData); out.response.signature = a2b(r.signature);
      if (r.userHandle) out.response.userHandle = a2b(r.userHandle); }
    return out;
  }
  async function post(u, body) {
    const r = await fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}), credentials: "same-origin" });
    let d = {}; try { d = await r.json(); } catch { }
    if (!r.ok || d.ok === false) throw new Error(d.hinweis || d.detail || ("Fehler " + r.status));
    return d;
  }
  const vorbereitenEinrichten = () => post("/api/passkey/registrieren/start");
  async function einrichten(vor) {
    const cred = await navigator.credentials.create({ publicKey: erstellOpt(vor.optionen) });
    return post("/api/passkey/registrieren/ende", { challenge_id: vor.challenge_id, credential: alsJson(cred) });
  }
  const vorbereitenLogin = () => post("/api/passkey/login/start");
  async function anmelden(vor, weiter, bedingt, signal) {
    const opt = { publicKey: holOpt(vor.optionen) };
    if (bedingt) { opt.mediation = "conditional"; opt.signal = signal; }
    const cred = await navigator.credentials.get(opt);
    return post("/api/passkey/login/ende", { challenge_id: vor.challenge_id, credential: alsJson(cred), weiter });
  }
  return { unterstuetzt, vorbereitenEinrichten, einrichten, vorbereitenLogin, anmelden };
})();
