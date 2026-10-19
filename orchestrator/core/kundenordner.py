"""Kundenordner (KUNDENORDNER_FREIGABE F1, CEO 2026-10-19: „LUNA legt einen Ordner fuer Kunden auf der NAS an, um darueber
Dateien freizugeben“).

Je Firma und Projekt ein Ordner `kundenordner/<Firmennummer>/<projekt>/` -- nur auf der NAS, nicht im Git, gespiegelt ins
Backup. Welche Ordner und Dateien es gibt, steht als Ereignis in der (gesicherten) Hash-Kette, wie bei den Lieferungen.
Grosse Videos kommen in Stuecken (gleicher Weg wie `lieferungen.py`); Lieferungen eines Auftrags lassen sich mit einem Klick
uebernehmen. Freigabe-Links nach aussen folgen in F2.
"""
from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path

from .buchhaltung import Buchhaltung
from .lieferungen import ENDUNGEN as _LIEFER_ENDUNGEN, STUECK, Lieferungen, _name

# Fuer Kunden: zusaetzlich Office-, Text- und Audio-Dateien (keine ausfuehrbaren Dateien, kein HTML).
ENDUNGEN = _LIEFER_ENDUNGEN | {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain", ".csv": "text/csv", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".svg": "image/svg+xml", ".psd": "image/vnd.adobe.photoshop", ".ai": "application/postscript",
}


def _slug(name: str) -> str:
    t = name.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "ordner"


class Kundenordner:
    def __init__(self, bh: Buchhaltung, ordner: Path | str, kunden=None, lieferungen: Lieferungen | None = None):
        self.bh, self.ordner, self.kunden, self.lieferungen = bh, Path(ordner), kunden, lieferungen
        self._upload = Lieferungen(bh, self.ordner)        # nur fuer den Stueck-Upload (`.upload/` in diesem Ordner)

    # -- Lesen -----------------------------------------------------------------------------------------------------
    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "kundenordner_angelegt":
                out[d["id"]] = dict(d) | {"dateien": [], "angelegt": e["ts"], "von": e.get("von", "")}
            elif t == "kundenordner_datei" and d.get("id") in out:
                out[d["id"]]["dateien"].append({k: d.get(k) for k in ("name", "pfad", "groesse", "sha256", "mime", "quelle")}
                                               | {"ts": e["ts"]})
            elif t == "kundenordner_datei_entfernt" and d.get("id") in out:
                out[d["id"]]["dateien"] = [x for x in out[d["id"]]["dateien"] if x["pfad"] != d.get("pfad")]
        return out

    def alle(self) -> dict[str, dict]:
        return self._falte(self.bh.eintraege())

    def fuer_firma(self, firma: str) -> list[dict]:
        f = (firma or "").strip().upper()
        return sorted((x for x in self.alle().values() if x["firma"] == f), key=lambda x: x["angelegt"], reverse=True)

    def get(self, oid: str) -> dict | None:
        return self.alle().get(oid)

    def datei(self, oid: str, i: int) -> tuple[Path, dict] | None:
        x = self.get(oid)
        if not x or i < 0 or i >= len(x["dateien"]):
            return None
        d = x["dateien"][i]
        p = (self.ordner / d["pfad"]).resolve()
        return (p, d) if p.is_file() and (self.ordner.resolve() / x["pfad"]) in p.parents else None

    # -- Schreiben -------------------------------------------------------------------------------------------------
    def anlegen(self, firma: str, name: str, *, auftrag: str = "", von: str = "") -> dict:
        f = self.kunden.firma(firma) if self.kunden else None
        if not f:
            raise KeyError(firma)
        name = re.sub(r"\s+", " ", str(name or "")).strip()[:120]
        if not name:
            raise ValueError("Name des Ordners fehlt (z. B. „Herbstkampagne 2026“).")
        slug = _slug(name)
        if any(x["slug"] == slug for x in self.fuer_firma(f["nummer"])):
            raise ValueError(f"Fuer {f['name']} gibt es schon einen Ordner „{name}“.")
        daten = {"id": "KO-" + uuid.uuid4().hex[:8], "firma": f["nummer"], "firma_name": f.get("name", ""), "name": name,
                 "slug": slug, "pfad": f"{f['nummer']}/{slug}", "auftrag": str(auftrag or "").strip().upper()[:30]}
        (self.ordner / daten["pfad"]).mkdir(parents=True, exist_ok=True)
        self.bh.erfassen("kundenordner_angelegt", daten, von=von)
        return daten | {"dateien": []}

    def _eintragen(self, x: dict, quelle_pfad: Path, name: str, sha: str, *, quelle: str = "", von: str = "",
                   verschieben: bool = True) -> dict:
        n = _name(name)
        endung = Path(n).suffix.lower()
        if endung not in ENDUNGEN:
            raise ValueError(f"{n}: Dateityp nicht erlaubt (Videos, Bilder, Audio, PDF, ZIP, Office, Text).")
        ziel_dir = self.ordner / x["pfad"]
        ziel_dir.mkdir(parents=True, exist_ok=True)
        ziel = ziel_dir / f"{sha[:12]}-{n}"
        if any(d["pfad"] == f"{x['pfad']}/{ziel.name}" for d in x["dateien"]):
            raise ValueError(f"{n} liegt schon in diesem Ordner.")
        if verschieben:
            shutil.move(str(quelle_pfad), ziel)
        else:
            try:
                os.link(quelle_pfad, ziel)                 # gleiche Platte: kein doppelter Platz fuer grosse Videos
            except OSError:
                shutil.copy2(quelle_pfad, ziel)
        daten = {"id": x["id"], "name": n, "pfad": f"{x['pfad']}/{ziel.name}", "groesse": ziel.stat().st_size,
                 "sha256": sha, "mime": ENDUNGEN[endung], "quelle": quelle}
        self.bh.erfassen("kundenordner_datei", daten, von=von)
        return daten

    def stueck(self, upload_id: str, teil: int, daten: bytes) -> dict:
        return self._upload.stueck(upload_id, teil, daten)

    def fertig(self, oid: str, upload_id: str, name: str, *, groesse: int, von: str = "") -> dict:
        """Letztes Stueck angekommen -> pruefen, in den Kundenordner verschieben, eintragen."""
        import hashlib
        x = self.get(oid)
        if not x:
            raise KeyError(oid)
        p = self._upload._tmp(upload_id)
        if not p.exists():
            raise ValueError("Upload nicht gefunden -- bitte neu starten.")
        if p.stat().st_size != int(groesse or -1):
            p.unlink(missing_ok=True)
            raise ValueError(f"{_name(name)}: unvollstaendig angekommen -- bitte neu hochladen.")
        h = hashlib.sha256()
        with p.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        try:
            return self._eintragen(x, p, name, h.hexdigest(), von=von)
        finally:
            p.unlink(missing_ok=True)

    def datei_ablegen(self, oid: str, daten: bytes, name: str, *, von: str = "") -> dict:
        """Kleine Datei in einem Rutsch (LUNA selbst, Tests) -- gleicher Weg wie der Upload."""
        uid = uuid.uuid4().hex[:16]
        for i in range(0, max(len(daten), 1), STUECK):
            self.stueck(uid, i // STUECK, daten[i:i + STUECK])
        return self.fertig(oid, uid, name, groesse=len(daten), von=von)

    def lieferung_uebernehmen(self, oid: str, lid: str, *, von: str = "") -> dict:
        """Alle Dateien einer Lieferung in den Ordner uebernehmen (Original bleibt bei der Lieferung)."""
        x = self.get(oid)
        if not x:
            raise KeyError(oid)
        lf = self.lieferungen.get(lid) if self.lieferungen else None
        if not lf or lf.get("entfernt"):
            raise KeyError(lid)
        if lf.get("firma") and lf["firma"] != x["firma"]:
            raise ValueError(f"Die Lieferung gehoert zu {lf['firma']}, der Ordner zu {x['firma']}.")
        neu, schon = [], 0
        for i, d in enumerate(lf["dateien"]):
            r = self.lieferungen.datei(lid, i)
            if not r:
                continue
            if any(f["sha256"] == d["sha256"] for f in x["dateien"]):
                schon += 1
                continue
            neu.append(self._eintragen(x, r[0], d["name"], d["sha256"], quelle=lid, von=von, verschieben=False))
            x["dateien"].append(neu[-1])
        return {"id": oid, "uebernommen": len(neu), "schon_da": schon}

    def datei_entfernen(self, oid: str, i: int, *, von: str = "") -> dict:
        r = self.datei(oid, i)
        if not r:
            raise KeyError(f"{oid}/{i}")
        pfad, d = r
        pfad.unlink(missing_ok=True)
        self.bh.erfassen("kundenordner_datei_entfernt", {"id": oid, "pfad": d["pfad"], "name": d["name"]}, von=von)
        return {"id": oid, "entfernt": d["name"]}
