"""Freigabe-Links fuer Kundenordner (KUNDENORDNER_FREIGABE F2, Weg A, CEO 2026-10-19).

Ein Link `/teilen/<schluessel>` zeigt genau einen Kundenordner zum Ansehen und Herunterladen -- ohne LUNA-OS-Anmeldung,
mit Ablauf (Standard 30 Tage), optional Passwort, jederzeit widerrufbar; jeder Abruf wird protokolliert.

Sicherheit:
- Schluessel: 32 zufaellige Bytes (`secrets.token_urlsafe`); in der Hash-Kette steht nur die SHA-256-Pruefsumme. Der Link
  selbst liegt zum erneuten Anzeigen/Versenden in `orchestrator/state/` (NAS, nicht im Git, nicht gesynct).
- Passwort: PBKDF2 wie bei den Team-Konten (`team_auth.hash_passwort`), nie im Klartext gespeichert.
- Nur Dateien, die laut Kette im Ordner liegen und deren Pfad innerhalb des Ordners bleibt (`Kundenordner.datei`).
- Fehlversuche (unbekannter Schluessel, falsches Passwort) laufen ueber die Login-Bremse in der Web-App.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path

from .buchhaltung import Buchhaltung, jetzt

ABLAUF_TAGE = (7, 30, 90)
STANDARD_TAGE = 30
PW_MIN = 6


def _hash(schluessel: str) -> str:
    return hashlib.sha256((schluessel or "").encode("utf-8")).hexdigest()


def ip_kurz(ip: str) -> str:
    """Abruf-Protokoll ohne volle IP (Datensparsamkeit): letzter Block genullt."""
    ip = (ip or "?").strip()
    if ip.count(".") == 3:
        return ip.rsplit(".", 1)[0] + ".0"
    if ":" in ip:
        return ":".join(ip.split(":")[:3]) + "::"
    return ip[:20]


class Freigaben:
    def __init__(self, bh: Buchhaltung, links_datei: Path | str, ordner=None):
        self.bh, self.links_datei, self.ordner = bh, Path(links_datei), ordner
        self._lock = threading.Lock()

    # -- Link-Ablage (nur NAS) ---------------------------------------------------------------------------------------
    def _links(self) -> dict:
        try:
            return json.loads(self.links_datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _link_merken(self, fid: str, schluessel: str) -> None:
        with self._lock:
            d = self._links()
            d[fid] = schluessel
            self.links_datei.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.links_datei.with_suffix(".tmp")
            tmp.write_text(json.dumps(d), encoding="utf-8")
            tmp.replace(self.links_datei)

    def link(self, fid: str) -> str:
        """Pfad `/teilen/<schluessel>` einer Freigabe ('' wenn unbekannt)."""
        s = self._links().get(fid, "")
        return f"/teilen/{s}" if s else ""

    # -- Lesen -------------------------------------------------------------------------------------------------------
    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "ordner_freigabe_angelegt":
                out[d["fid"]] = dict(d) | {"angelegt": e["ts"], "von": e.get("von", ""), "abrufe": [], "widerrufen": ""}
            elif t == "ordner_freigabe_widerrufen" and d.get("fid") in out:
                out[d["fid"]]["widerrufen"] = e["ts"]
            elif t == "ordner_freigabe_versendet" and d.get("fid") in out:
                out[d["fid"]].setdefault("versendet", []).append({"an": d.get("an", ""), "ts": e["ts"]})
            elif t == "ordner_freigabe_abruf" and d.get("fid") in out:
                out[d["fid"]]["abrufe"].append({k: d.get(k) for k in ("art", "datei", "ip")} | {"ts": e["ts"]})
        return out

    @staticmethod
    def aktiv(f: dict, heute: date | None = None) -> bool:
        heute = heute or jetzt().date()
        return not f.get("widerrufen") and date.fromisoformat(f["ablauf"]) >= heute

    def fuer_ordner(self, oid: str) -> list[dict]:
        return [f for f in self.fuer_ordner_alle() if f["oid"] == oid]

    def fuer_ordner_alle(self) -> list[dict]:
        out = []
        for f in self._falte(self.bh.eintraege()).values():
            x = {k: v for k, v in f.items() if k not in ("schluessel_hash", "passwort_hash")}
            out.append(x | {"aktiv": self.aktiv(f), "mit_passwort": bool(f.get("passwort_hash")), "link": self.link(f["fid"]),
                            "versendet": f.get("versendet", []),
                            "abrufe_anzahl": len(f["abrufe"]), "abrufe": f["abrufe"][-10:][::-1]})
        return sorted(out, key=lambda x: x["angelegt"], reverse=True)

    def finde(self, schluessel: str) -> dict | None:
        """Gueltige Freigabe zum Schluessel (aktiv, Ordner existiert) oder None -- keine Unterscheidung nach aussen."""
        if not schluessel or len(schluessel) < 20:
            return None
        h = _hash(schluessel)
        for f in self._falte(self.bh.eintraege()).values():
            if secrets.compare_digest(f["schluessel_hash"], h):
                if not self.aktiv(f):
                    return None
                o = self.ordner.get(f["oid"]) if self.ordner else None
                return f | {"ordner": o} if o else None
        return None

    # -- Schreiben ---------------------------------------------------------------------------------------------------
    def anlegen(self, oid: str, *, tage: int = STANDARD_TAGE, passwort: str = "", von: str = "") -> dict:
        from .team_auth import hash_passwort
        o = self.ordner.get(oid) if self.ordner else None
        if not o:
            raise KeyError(oid)
        tage = int(tage or STANDARD_TAGE)
        if tage not in ABLAUF_TAGE:
            raise ValueError(f"Gueltigkeit nur {', '.join(map(str, ABLAUF_TAGE))} Tage (kein Link ohne Ablauf).")
        pw = str(passwort or "")
        if pw and len(pw) < PW_MIN:
            raise ValueError(f"Passwort zu kurz (mindestens {PW_MIN} Zeichen) -- oder leer lassen.")
        schluessel = secrets.token_urlsafe(32)
        daten = {"fid": "FG-" + uuid.uuid4().hex[:8], "oid": oid, "firma": o["firma"], "ordner_name": o["name"],
                 "schluessel_hash": _hash(schluessel), "ablauf": (jetzt().date() + timedelta(days=tage)).isoformat(),
                 "passwort_hash": hash_passwort(pw) if pw else ""}
        self._link_merken(daten["fid"], schluessel)
        self.bh.erfassen("ordner_freigabe_angelegt", daten, von=von)
        return {"fid": daten["fid"], "link": f"/teilen/{schluessel}", "ablauf": daten["ablauf"], "mit_passwort": bool(pw)}

    def widerrufen(self, fid: str, *, von: str = "") -> dict:
        f = self._falte(self.bh.eintraege()).get(fid)
        if not f or f.get("widerrufen"):
            raise KeyError(fid)
        self.bh.erfassen("ordner_freigabe_widerrufen", {"fid": fid, "oid": f["oid"]}, von=von)
        return {"fid": fid}

    def passwort_ok(self, f: dict, passwort: str) -> bool:
        from .team_auth import pruefe_passwort
        return not f.get("passwort_hash") or pruefe_passwort(passwort or "", f["passwort_hash"])

    def abruf(self, f: dict, art: str, *, datei: str = "", ip: str = "") -> None:
        self.bh.erfassen("ordner_freigabe_abruf", {"fid": f["fid"], "oid": f["oid"], "art": art, "datei": datei[:120],
                                                   "ip": ip_kurz(ip)}, von="Freigabe-Link")


# -- Link per Mail (KUNDENORDNER_FREIGABE F3) -------------------------------------------------------------------------
OEFFENTLICH = "https://os.hanserautisch.synology.me"     # Kunden erreichen nur diese Adresse (nie die LAN-IP)


def basis_url(secrets_dict: dict | None) -> str:
    return str((secrets_dict or {}).get("LUNA_OS_OEFFENTLICH") or OEFFENTLICH).rstrip("/")


def _datum_de(iso: str) -> str:
    return ".".join(reversed(iso[:10].split("-")))


def mail_vorschau(freigaben: Freigaben, kunden, fid: str, *, basis: str, firmendaten: dict, vorlage: dict | None = None,
                  signatur: str = "") -> dict:
    """Betreff/Text aus der Vorlage „Dateifreigabe“ + Empfaenger-Vorschlaege der Firma. Das Passwort steht nie im Text."""
    from .empfaenger import vorschlaege
    from .textbausteine import anrede_werte, rendern
    f = next((x for x in freigaben.fuer_ordner_alle() if x["fid"] == fid), None)
    if not f:
        raise KeyError(fid)
    if not f["aktiv"]:
        raise ValueError("Dieser Link ist abgelaufen oder zurueckgezogen -- bitte einen neuen erstellen.")
    if not f["link"]:
        raise ValueError("Der Link liegt nicht mehr vor (nur die Pruefsumme) -- bitte einen neuen erstellen.")
    firma = kunden.firma(f["firma"]) or {}
    aps = [a for a in firma.get("ansprechpartner_liste") or [] if a.get("aktiv", True) and a.get("mail")]
    o = freigaben.ordner.get(f["oid"]) if freigaben.ordner else None
    werte = anrede_werte(aps[0] if aps else None) | {
        "kunde": firma.get("name", ""), "ordner": f["ordner_name"], "link": basis + f["link"], "ablauf": _datum_de(f["ablauf"]),
        "anzahl": str(len((o or {}).get("dateien") or [])),
        "passwort_hinweis": "Das Passwort erhalten Sie separat." if f["mit_passwort"] else ""}
    betreff, text = rendern("dateifreigabe", werte, firmendaten, vorlage=vorlage, signatur=signatur)
    return {"fid": fid, "firma": f["firma"], "an": (aps[0]["mail"] if aps else firma.get("rechnungsmail") or ""),
            "adressen": vorschlaege(kunden, f["firma"]), "betreff": betreff, "text": text, "link": werte["link"],
            "ablauf": f["ablauf"], "mit_passwort": f["mit_passwort"]}


def _enthaelt_passwort(f_roh: dict, texte: list[str], bekannt: str) -> bool:
    """Steht das Passwort im Mailtext? Es liegt nur als PBKDF2 vor -> nur die Woerter pruefen, die der CEO selbst
    ergaenzt hat (nicht im vorbereiteten Text), hoechstens 30 (jede Pruefung kostet Rechenzeit)."""
    import re
    from .team_auth import pruefe_passwort
    if not f_roh.get("passwort_hash"):
        return False
    alt = set(re.split(r"\s+", bekannt or ""))
    kandidaten = []
    for t in texte:
        for w in re.split(r"\s+", t or ""):
            for x in {w, w.strip(".,;:!?()[]{}\"'„“»«")}:
                if PW_MIN <= len(x) <= 64 and x not in alt and x not in kandidaten:
                    kandidaten.append(x)
    return any(pruefe_passwort(x, f_roh["passwort_hash"]) for x in kandidaten[:30])


def mail_senden(freigaben: Freigaben, kunden, versand, fid: str, daten: dict, *, basis: str, firmendaten: dict,
                vorlage: dict | None = None, signatur: str = "", absender_name: str, eigene: list[str], von: str = "") -> dict:
    """Link per Mail an die Firma -- nur mit ausdruecklicher Bestaetigung (Mail an Kunden = CEO-Tor). Der Text muss den
    Link enthalten und darf das Passwort nicht enthalten. Die Mail landet in der Firmenakte."""
    from .empfaenger import aus_body
    from .firmenakte import Firmenakte
    if (daten or {}).get("bestaetigt") is not True:
        raise ValueError("Senden braucht die ausdrueckliche Bestaetigung.")
    v = mail_vorschau(freigaben, kunden, fid, basis=basis, firmendaten=firmendaten, vorlage=vorlage, signatur=signatur)
    betreff = str(daten.get("betreff") or v["betreff"]).strip()
    text = str(daten.get("text") or v["text"]).strip()
    if v["link"] not in text:
        raise ValueError("Der Freigabe-Link fehlt im Text -- bitte nicht entfernen.")
    roh = freigaben._falte(freigaben.bh.eintraege())[fid]
    if _enthaelt_passwort(roh, [betreff, text], v["text"] + " " + v["betreff"]):
        raise ValueError("Das Passwort steht im Text -- bitte entfernen und getrennt mitteilen (z. B. Telefon oder SMS).")
    an = aus_body(daten if any(str(daten.get(k) or "").strip() for k in ("an", "cc", "bcc")) else {"an": v["an"]})
    s = versand.mail_senden(an, betreff, text, bestaetigt=True, absender_name=absender_name)
    if not s.get("ok"):
        raise ValueError(s.get("hinweis") or "Senden fehlgeschlagen.")
    akte = ""
    r = versand.mail_roh(s["id"]) if s.get("id") and hasattr(versand, "mail_roh") else {}
    if r.get("ok"):
        akte = Firmenakte(freigaben.bh, kunden).mail_aufnehmen(r["roh"], s["id"], eigene=eigene, weitergeleitet=False,
                                                               von=von, firma=v["firma"])["id"]
    freigaben.bh.erfassen("ordner_freigabe_versendet", {"fid": fid, "oid": roh["oid"], "firma": v["firma"], "an": an,
                                                        "betreff": betreff[:200], "message_id": s.get("id", ""),
                                                        "kanal": s.get("kanal", ""), "akte_id": akte}, von=von)
    return {"fid": fid, "an": an, "akte_id": akte}
