"""Akquise-Ideen: Merkzettel fuer Firmen, die wir als Kunde oder Partner ansprechen koennten (PARTNERLISTE P1-P3,
CEO 2026-10-09).

- **Getrennt vom Kundenstamm:** liegt in `akquise/ideen.json` auf der NAS -- **nicht** in der Buchhaltungs-Kette, damit
  Ideen wieder geloescht werden koennen (Kundenstamm ist unveraenderbar). Im Backup, vom Deploy ausgenommen.
- Erst beim Anschreiben (Vorstellungs-Mail, P3) wird daraus eine Firma (Interessent) im Kundenstamm.
- Status: idee -> angeschrieben -> (interessent | kunde | kein_interesse); nach dem Anschreiben leitet die Liste den
  Stand aus der Vorstellung ab (Antwort, „Kein Interesse“, Interessent -> Kunde).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

ARTEN = {"kunde": "potenzieller Kunde", "partner": "potenzieller Partner"}
STATUS = {"idee": "Idee", "angeschrieben": "angeschrieben", "antwort": "Antwort erhalten", "interessent": "Interessent",
          "kunde": "Kunde", "kein_interesse": "kein Interesse"}
FELDER = {"name": 200, "branche": 80, "ort": 80, "web": 200, "mail": 200, "ansprechpartner": 120, "notiz": 1000}
_MAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LOCK = threading.Lock()


def _jetzt() -> str:
    from .buchhaltung import jetzt
    return jetzt().isoformat(timespec="seconds")


def _schluessel(name: str) -> str:
    """Name ohne Rechtsform/Satzzeichen fuer den Dubletten-Vergleich."""
    n = re.sub(r"(?i)\b(gmbh|ug|ag|kg|ohg|gbr|e\.?\s?k|mbh|co|haftungsbeschraenkt|&)\b", " ", str(name or "").lower())
    return " ".join(re.findall(r"[a-z0-9äöüß]+", n))


def _domain(web_oder_mail: str) -> str:
    s = str(web_oder_mail or "").strip().lower()
    if "@" in s and "/" not in s:
        s = s.rsplit("@", 1)[-1]
    s = re.sub(r"^https?://", "", s).split("/")[0]
    return s[4:] if s.startswith("www.") else s


class IdeenStore:
    def __init__(self, ordner: Path):
        self.dir = Path(ordner)
        self.datei = self.dir / "ideen.json"

    # -- Speicher ---------------------------------------------------------------------------------------------------
    def _laden(self) -> dict:
        try:
            return json.loads(self.datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _schreiben(self, d: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".ideen-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.datei)

    # -- Lesen ------------------------------------------------------------------------------------------------------
    def get(self, iid: str) -> dict | None:
        return self._laden().get(str(iid or "").strip().upper())

    def liste(self) -> list[dict]:
        return sorted(self._laden().values(), key=lambda x: x["erstellt"], reverse=True)

    def dubletten(self, name: str, web: str = "", mail: str = "", kunden=None, ohne: str = "") -> list[dict]:
        """Gleicher Name (ohne Rechtsform) oder gleiche Website-/Mail-Domain -- in den Ideen und im Kundenstamm."""
        from .vorstellung import FREEMAIL
        k, doms = _schluessel(name), {d for d in (_domain(web), _domain(mail)) if d and d not in FREEMAIL}
        out = []
        for x in self._laden().values():
            if x["id"] != ohne and ((k and _schluessel(x["name"]) == k) or doms & {_domain(x.get("web")), _domain(x.get("mail"))}):
                out.append({"art": "idee", "id": x["id"], "name": x["name"]})
        for f in (kunden.firmen() if kunden else []):
            voll = kunden.firma(f["nummer"]) or f
            adressen = [voll.get("website") or "", voll.get("rechnungsmail") or ""] + \
                [a.get("mail") or "" for a in voll.get("ansprechpartner_liste") or []]
            if (k and _schluessel(f["name"]) == k) or (doms and doms & {_domain(a) for a in adressen if a}):
                out.append({"art": "firma", "id": f["nummer"], "name": f["name"]})
        return out

    # -- Schreiben --------------------------------------------------------------------------------------------------
    @staticmethod
    def _bereinigt(daten: dict, *, neu: bool) -> dict:
        d = {k: " ".join(str(daten[k] or "").split())[:n] if k != "notiz" else str(daten[k] or "").strip()[:n]
             for k, n in FELDER.items() if k in daten}
        if "art" in daten or neu:
            a = str(daten.get("art") or "partner").strip().lower()
            if a not in ARTEN:
                raise ValueError("Art: potenzieller Kunde oder Partner.")
            d["art"] = a
        if neu and not d.get("name"):
            raise ValueError("Bitte den Namen der Firma eintragen.")
        if "name" in d and not d["name"]:
            raise ValueError("Der Name darf nicht leer sein.")
        if d.get("mail") and not _MAIL.match(d["mail"]):
            raise ValueError("Mailadresse ungueltig.")
        return d

    def anlegen(self, daten: dict, *, quelle: str = "LUNA-OS", von: str = "", kunden=None, trotz_dublette: bool = False) -> dict:
        d = self._bereinigt(daten, neu=True)
        gleich = self.dubletten(d["name"], d.get("web", ""), d.get("mail", ""), kunden)
        if gleich and not trotz_dublette:
            from .kunden import DubletteFehler
            raise DubletteFehler("Gibt es vermutlich schon: " + ", ".join(f"{g['name']} ({g['id']})" for g in gleich),
                                 [g["id"] for g in gleich])
        with _LOCK:
            alle = self._laden()
            iid = "I-" + uuid.uuid4().hex[:6].upper()
            ts = _jetzt()
            alle[iid] = {"id": iid, **{k: "" for k in FELDER}, **d, "quelle": str(quelle)[:40], "status": "idee",
                         "erstellt": ts, "geaendert": ts, "von": von, "firma": "", "verlauf": [{"ts": ts, "text": f"angelegt ({quelle})"}]}
            self._schreiben(alle)
        return alle[iid]

    def aendern(self, iid: str, daten: dict, *, von: str = "") -> dict:
        d = self._bereinigt(daten, neu=False)
        st = str(daten.get("status") or "").strip()
        if st and st not in ("idee", "kein_interesse", "angeschrieben"):
            raise ValueError("Status von Hand: Idee, angeschrieben oder kein Interesse.")
        with _LOCK:
            alle = self._laden()
            x = alle.get(str(iid or "").strip().upper())
            if not x:
                raise KeyError(iid)
            x |= d | ({"status": st} if st else {}) | {"geaendert": _jetzt()}
            if st:
                x["verlauf"].append({"ts": x["geaendert"], "text": f"Status: {STATUS[st]}" + (f" ({von})" if von else "")})
            self._schreiben(alle)
        return x

    def angeschrieben(self, iid: str, firma: str, an: str) -> dict:
        """P3: nach erfolgreicher Vorstellungs-Mail -- Idee mit der (neuen oder vorhandenen) Firma verknuepfen."""
        with _LOCK:
            alle = self._laden()
            x = alle.get(str(iid or "").strip().upper())
            if not x:
                raise KeyError(iid)
            ts = _jetzt()
            x |= {"status": "angeschrieben", "firma": firma, "geaendert": ts}
            x["verlauf"].append({"ts": ts, "text": f"Vorstellungs-Mail an {an} ({firma})"})
            self._schreiben(alle)
        return x

    def loeschen(self, iid: str) -> dict:
        """Wirklich loeschen (nicht nur markieren) -- Ideen sind kein Geschaeftsbrief und keine Buchung."""
        with _LOCK:
            alle = self._laden()
            x = alle.pop(str(iid or "").strip().upper(), None)
            if not x:
                raise KeyError(iid)
            self._schreiben(alle)
        return {"id": x["id"], "name": x["name"]}


def mit_stand(ideen: list[dict], vorstellungen: list[dict], kunden) -> list[dict]:
    """Status angeschriebener Ideen aus Vorstellung und Kundenstamm ableiten (Antwort, kein Interesse, Interessent -> Kunde)."""
    vs = {v["firma"]: v for v in vorstellungen}
    out = []
    for x in ideen:
        y = dict(x)
        if x.get("firma") and x["status"] != "kein_interesse":
            v, f = vs.get(x["firma"]) or {}, (kunden.firma(x["firma"]) or {}) if kunden else {}
            if f.get("typ") == "kunde":
                y["status"] = "kunde"
            elif v.get("erledigt"):
                y["status"] = "kein_interesse"
            elif v.get("antwort"):
                y["status"] = "antwort"
            y["nachfassen_faellig"] = bool(v.get("nachfassen_faellig"))
            y["firma_name"] = f.get("name", "")
        out.append(y)
    return out


# -- P2: Ideen per Telegram („Idee: Kiez Burger – passt fuer Food-Reels“, „Merk dir … als moeglichen Partner“) --------
_TG = re.compile(r"(?is)^\s*(?:(partner|kunden|firmen|akquise)[- ]?idee|akquise|merke?\s+dir|notiere?(?:\s+dir)?)\s*[:\-–]?\s*(.+)$")
_ART_PARTNER = re.compile(r"(?i)\bals\s+(?:m[öo]glichen|potenziellen|neuen)?\s*(partner|kunden?)\b")

def telegram_idee(text: str) -> dict | None:
    """-> {name, notiz, art} oder None. Eindeutige Ausloeser: „Partner-Idee: …“, „Kunden-Idee: …“, „Akquise: …“ oder
    „Merk dir <Firma> als moeglichen Partner/Kunden …“. Ein blosses „Idee: …“ ist oft Content -> das entscheidet LUNA im
    Chat (Werkzeug `akquise_idee_merken`)."""
    t = " ".join(str(text or "").split())
    if not t or "?" in t or len(t) > 400:
        return None
    m = _TG.match(t)
    if not m:
        return None
    rest, vorne = m.group(2).strip(), (m.group(1) or "").lower()
    a = _ART_PARTNER.search(rest)
    kopf = t[:m.start(2)].lower()
    if ("merk" in kopf or "notier" in kopf) and not a:
        return None                                              # „merk dir den Termin“ = normaler Chat
    art = ("kunde" if a.group(1).lower().startswith("kunde") else "partner") if a else ("kunde" if vorne == "kunden" else "partner")
    if a:
        name, notiz = rest[:a.start()], rest[a.end():]
    else:
        teile = re.split(r"\s+[–—-]\s+|:\s+|,\s*", rest, maxsplit=1)
        name, notiz = teile[0], (teile[1] if len(teile) > 1 else "")
    name, notiz = name.strip(" ,.;:\"„“"), notiz.strip(" ,.;:–—-")
    if not name or len(name) > 120:
        return None
    return {"name": name, "notiz": notiz, "art": art}
