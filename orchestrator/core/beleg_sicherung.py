"""Belege ausser Haus (LUNA_GOOGLE_KONTO_ROADMAP.md, Etappe 6): Kopie der Buchhaltungs-Belege in LUNAs Google Drive.

NAS (Original) und MACO470 (naechtliches Backup) stehen im selben Haus. Dieses Modul kopiert jeden Beleg aus
`buchhaltung/belege/<jahr>/` zusaetzlich nach `LUNA-Buchhaltung/Belege/<jahr>/` in LUNAs Drive:
- **idempotent:** jede erfolgreiche Kopie steht als Eintrag `beleg_extern_kopiert` (Pfad, SHA-256, Drive-ID, MD5) in der
  Buchhaltungs-Kette; schon kopierte Belege werden uebersprungen, eine vorhandene Drive-Datei mit gleicher Pruefsumme wird
  uebernommen statt doppelt hochgeladen;
- **gegengeprueft:** vor dem Hochladen muss die lokale Datei noch zum SHA-256 aus der Kette passen (sonst Alarm statt
  Kopie einer manipulierten Datei), nach dem Hochladen muss Googles MD5 zur lokalen Datei passen;
- **nie loeschen:** Drive-Kopien werden nicht automatisch entfernt (CEO-Tor);
- **Stand:** einmal pro Tag Kette, Katalog und Firmendaten nach `LUNA-Buchhaltung/Stand/<datum>/` (Wiederherstellung).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .buchhaltung import Buchhaltung, jetzt

WURZEL = "LUNA-Buchhaltung"
_MIME = {".pdf": "application/pdf", ".eml": "message/rfc822", ".xml": "application/xml", ".json": "application/json",
         ".jsonl": "application/json", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _mime(name: str) -> str:
    return _MIME.get(Path(name).suffix.lower(), "application/octet-stream")


def belege_sichern(bh: Buchhaltung, google, *, notify=None, max_dateien: int = 50) -> dict:
    """Noch nicht kopierte Belege nach Drive bringen. Rueckgabe {kopiert, uebernommen, fehler: [..]}."""
    if google is None or not google.verfuegbar():
        return {"kopiert": 0, "uebernommen": 0, "fehler": ["Google nicht verbunden"]}
    erledigt = {(e["daten"]["pfad"], e["daten"]["sha256"]) for e in bh.eintraege("beleg_extern_kopiert")}
    offen, gesehen = [], set()
    for e in bh.eintraege("beleg"):
        d = e["daten"]
        schluessel = (d["pfad"], d["sha256"])
        if schluessel in erledigt or schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        offen.append(d)
    ergebnis = {"kopiert": 0, "uebernommen": 0, "fehler": []}
    ordner: dict[str, str] = {}
    for d in offen[:max_dateien]:
        pfad = bh.dir / d["pfad"]
        name = Path(d["pfad"]).name
        try:
            inhalt = pfad.read_bytes()
        except OSError:
            ergebnis["fehler"].append(f"{d['pfad']}: Datei fehlt auf der NAS")
            continue
        if hashlib.sha256(inhalt).hexdigest() != d["sha256"]:
            ergebnis["fehler"].append(f"{d['pfad']}: Pruefsumme passt nicht zur Buchhaltung -- nicht kopiert")
            continue
        jahr = str(d.get("jahr") or name[:4])
        if jahr not in ordner:
            r = google.drive_ordner([WURZEL, "Belege", jahr])
            if not r.get("ok"):
                ergebnis["fehler"].append(r.get("hinweis") or "Drive-Ordner fehlgeschlagen")
                break
            ordner[jahr] = r["ordner_id"]
        md5 = hashlib.md5(inhalt).hexdigest()
        vorhanden = google.drive_datei_vorhanden(name, ordner[jahr])
        datei = vorhanden.get("datei") if vorhanden.get("ok") else None
        if datei and datei.get("md5Checksum") == md5:
            fid, art = datei["id"], "uebernommen"                   # z. B. nach Abbruch zwischen Upload und Eintrag
        else:
            r = google.drive_datei_hochladen(inhalt, name, ordner[jahr], _mime(name))
            if not r.get("ok"):
                ergebnis["fehler"].append(f"{d['pfad']}: {r.get('hinweis') or 'Upload fehlgeschlagen'}")
                continue
            if r.get("md5") and r["md5"] != md5:
                ergebnis["fehler"].append(f"{d['pfad']}: Drive-Pruefsumme weicht ab")
                continue
            fid, art = r.get("datei_id", ""), "kopiert"
        bh.erfassen("beleg_extern_kopiert", {"pfad": d["pfad"], "sha256": d["sha256"], "drive_id": fid, "md5": md5,
                                             "ziel": f"{WURZEL}/Belege/{jahr}/{name}"}, von="LUNA-Sicherung")
        ergebnis[art] += 1
    if ergebnis["fehler"] and notify:
        try:
            notify(f"⚠️ Beleg-Sicherung in LUNAs Drive: {len(ergebnis['fehler'])} Problem(e).",
                   abteilung="IT/Self-Maintenance", kategorie="fehler", quelle="beleg-sicherung",
                   detail="\n".join(ergebnis["fehler"][:10]))
        except Exception:
            pass
    return ergebnis


def stand_sichern(bh: Buchhaltung, google, *, heute: str | None = None) -> dict:
    """Einmal pro Tag: Kette, Katalog, Firmendaten nach `LUNA-Buchhaltung/Stand/<datum>/` (Wiederherstellung)."""
    if google is None or not google.verfuegbar():
        return {"ok": False, "hinweis": "Google nicht verbunden"}
    heute = heute or jetzt().date().isoformat()
    r = google.drive_ordner([WURZEL, "Stand", heute])
    if not r.get("ok"):
        return r
    hochgeladen = []
    for datei in ("log.jsonl", "katalog.json", "firmendaten.json", "textbausteine.json"):
        pfad = bh.dir / datei
        if not pfad.exists():
            continue
        v = google.drive_datei_vorhanden(datei, r["ordner_id"])
        if v.get("ok") and v.get("datei"):
            continue                                                  # heute schon gesichert
        inhalt = pfad.read_bytes()
        u = google.drive_datei_hochladen(inhalt, datei, r["ordner_id"], _mime(datei))
        if not u.get("ok") or (u.get("md5") and u["md5"] != hashlib.md5(inhalt).hexdigest()):
            return {"ok": False, "hinweis": f"{datei}: {u.get('hinweis') or 'Pruefsumme weicht ab'}"}
        hochgeladen.append(datei)
    return {"ok": True, "hochgeladen": hochgeladen}
