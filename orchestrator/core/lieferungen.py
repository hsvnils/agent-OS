"""Lieferungen je Auftrag (KUNDEN_FINANZEN Etappe 30, CEO 2026-10-01: „Auftrag als geliefert markieren, die Videos/Bilder
reinhaengen, sodass wir immer wissen, was wir wo geliefert haben“).

Eine Lieferung hat Titel, Datum, Notiz und beliebig viele **Dateien und Links zugleich** (CEO). Dateien liegen auf der
NAS unter `lieferungen/<Auftrag>/` -- nicht im Kassenbuch (`buchhaltung/belege/`), nicht in Google Drive, nicht im Git
und laut CEO **ohne zusaetzliches Backup**; die Liste der Lieferungen steht als Ereignis in der (gesicherten) Hash-Kette.
Grosse Videos kommen vom iPhone in Stuecken (`STUECK` Bytes) und werden erst nach dem letzten Stueck eingetragen.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from datetime import date
from pathlib import Path

from .buchhaltung import Buchhaltung, jetzt

STUECK = 8 * 1024 * 1024
MAX_BYTES = 4 * 1024 ** 3                         # 4 GB je Datei
ENDUNGEN = {".mp4": "video/mp4", ".mov": "video/quicktime", ".m4v": "video/x-m4v", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".png": "image/png", ".heic": "image/heic", ".webp": "image/webp",
            ".gif": "image/gif", ".pdf": "application/pdf", ".zip": "application/zip"}


def _name(n: str) -> str:
    n = re.sub(r"[^\w.\- ]+", "_", Path(n or "datei").name, flags=re.UNICODE).strip(" .") or "datei"
    return n[:120]


def _link(u: str) -> str:
    u = (u or "").strip()
    if not re.match(r"^https?://[^\s/]+\.[^\s]+$", u):
        raise ValueError(f"Kein gueltiger Link: {u[:60]}")
    return u[:500]


class Lieferungen:
    def __init__(self, bh: Buchhaltung, ordner: Path | str, auftraege=None):
        self.bh, self.ordner, self.auftraege = bh, Path(ordner), auftraege

    # -- Lesen -----------------------------------------------------------------------------------------------------
    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "lieferung_angelegt":
                out[d["id"]] = dict(d) | {"dateien": [], "angelegt": e["ts"], "von": e.get("von", "")}
            elif t == "lieferung_datei" and d.get("id") in out:
                out[d["id"]]["dateien"].append({k: d.get(k) for k in ("name", "pfad", "groesse", "sha256", "mime")}
                                               | {"ts": e["ts"]})
            elif t == "lieferung_entfernt" and d.get("id") in out:
                out[d["id"]] |= {"entfernt": e["ts"], "grund": d.get("grund", "")}
        return out

    def fuer_auftrag(self, auftrag: str) -> list[dict]:
        a = (auftrag or "").strip().upper()
        return sorted((x for x in self._falte(self.bh.eintraege()).values() if x["auftrag"] == a and not x.get("entfernt")),
                      key=lambda x: (x["datum"], x["angelegt"]), reverse=True)

    def fuer_auftraege(self, nummern: set[str]) -> list[dict]:
        return sorted((x for x in self._falte(self.bh.eintraege()).values() if x["auftrag"] in nummern and not x.get("entfernt")),
                      key=lambda x: (x["datum"], x["angelegt"]), reverse=True)

    def get(self, lid: str) -> dict | None:
        return self._falte(self.bh.eintraege()).get(lid)

    def datei(self, lid: str, i: int) -> tuple[Path, dict] | None:
        x = self.get(lid)
        if not x or i < 0 or i >= len(x["dateien"]):
            return None
        d = x["dateien"][i]
        p = (self.ordner / d["pfad"]).resolve()
        return (p, d) if p.is_file() and self.ordner.resolve() in p.parents else None

    # -- Schreiben -------------------------------------------------------------------------------------------------
    def anlegen(self, auftrag: str, *, titel: str, datum: str = "", links: list[str] | None = None, notiz: str = "",
                von: str = "") -> dict:
        a = self.auftraege.auftrag(auftrag) if self.auftraege else None
        if not a:
            raise KeyError(auftrag)
        if a["status"] == "storniert":
            raise ValueError(f"{a['nummer']} ist storniert.")
        titel = str(titel or "").strip()[:200]
        if not titel:
            raise ValueError("Titel fehlt (z. B. „Reel Herbstkampagne, finale Version“).")
        try:
            tag = date.fromisoformat(str(datum)[:10]).isoformat() if datum else jetzt().date().isoformat()
        except ValueError:
            raise ValueError("Datum ungueltig.") from None
        daten = {"id": "L-" + uuid.uuid4().hex[:8], "auftrag": a["nummer"], "firma": a["firma"], "titel": titel,
                 "datum": tag, "links": [_link(u) for u in (links or []) if str(u).strip()],
                 "notiz": str(notiz or "").strip()[:500]}
        self.bh.erfassen("lieferung_angelegt", daten, von=von)
        return daten | {"dateien": []}

    def entfernen(self, lid: str, grund: str, *, von: str = "") -> dict:
        """Falsch angelegte Lieferung ausblenden; ihre Dateien werden geloescht (Liste bleibt im Verlauf)."""
        x = self.get(lid)
        if not x or x.get("entfernt"):
            raise KeyError(lid)
        if not str(grund or "").strip():
            raise ValueError("Bitte kurz begruenden.")
        for d in x["dateien"]:
            p = (self.ordner / d["pfad"]).resolve()
            if self.ordner.resolve() in p.parents:
                p.unlink(missing_ok=True)
        self.bh.erfassen("lieferung_entfernt", {"id": lid, "grund": str(grund).strip()[:300]}, von=von)
        return {"id": lid}

    # -- Upload in Stuecken ----------------------------------------------------------------------------------------
    def _tmp(self, upload_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,40}", upload_id or ""):
            raise ValueError("Ungueltige Upload-Kennung.")
        return self.ordner / ".upload" / f"{upload_id}.part"

    def stueck(self, upload_id: str, teil: int, daten: bytes) -> dict:
        """Stueck Nr. `teil` (ab 0) anhaengen. Nur der Reihe nach; ein wiederholtes Stueck ist ok (Netz-Wackler)."""
        p = self._tmp(upload_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        groesse = p.stat().st_size if p.exists() else 0
        if teil * STUECK == groesse - len(daten) and groesse:      # gleiches Stueck noch einmal -> nichts tun
            return {"bytes": groesse}
        if teil * STUECK != groesse:
            raise ValueError(f"Stueck {teil} passt nicht (bisher {groesse} Bytes) -- Upload neu starten.")
        if len(daten) > STUECK or groesse + len(daten) > MAX_BYTES:
            raise ValueError("Datei zu gross (max. 4 GB).")
        with p.open("ab") as f:
            f.write(daten)
        return {"bytes": groesse + len(daten)}

    def fertig(self, lid: str, upload_id: str, name: str, *, groesse: int, von: str = "") -> dict:
        """Letztes Stueck angekommen -> Datei pruefen, in `lieferungen/<Auftrag>/` verschieben, eintragen."""
        x = self.get(lid)
        if not x or x.get("entfernt"):
            raise KeyError(lid)
        p = self._tmp(upload_id)
        if not p.exists():
            raise ValueError("Upload nicht gefunden -- bitte neu starten.")
        n = _name(name)
        endung = Path(n).suffix.lower()
        if endung not in ENDUNGEN:
            p.unlink(missing_ok=True)
            raise ValueError(f"{n}: Dateityp nicht erlaubt (Videos, Bilder, PDF, ZIP).")
        if p.stat().st_size != int(groesse or -1):
            p.unlink(missing_ok=True)
            raise ValueError(f"{n}: unvollstaendig angekommen -- bitte neu hochladen.")
        h = hashlib.sha256()
        with p.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        ziel_dir = self.ordner / x["auftrag"]
        ziel_dir.mkdir(parents=True, exist_ok=True)
        ziel = ziel_dir / f"{h.hexdigest()[:12]}-{n}"
        shutil.move(str(p), ziel)
        daten = {"id": lid, "name": n, "pfad": f"{x['auftrag']}/{ziel.name}", "groesse": ziel.stat().st_size,
                 "sha256": h.hexdigest(), "mime": ENDUNGEN[endung]}
        self.bh.erfassen("lieferung_datei", daten, von=von)
        return daten

    def datei_ablegen(self, lid: str, daten: bytes, name: str, *, von: str = "") -> dict:
        """Kleine Datei in einem Rutsch (LUNA selbst, Tests) -- nutzt denselben Weg wie der Upload."""
        uid = uuid.uuid4().hex[:16]
        for i in range(0, max(len(daten), 1), STUECK):
            self.stueck(uid, i // STUECK, daten[i:i + STUECK])
        return self.fertig(lid, uid, name, groesse=len(daten), von=von)
