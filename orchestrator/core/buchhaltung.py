"""Buchhaltungs-Speicher (KUNDEN_FINANZEN_ROADMAP.md, Etappe 1) -- GoBD-faehiges Fundament fuer Kunden, Angebote,
Auftraege, Rechnungen, Belege und das EUeR-Journal.

Grundsaetze (Rechtsrahmen siehe Roadmap):
- **Append-only mit Hash-Kette:** Jeder Eintrag traegt eine fortlaufende `seq`, den Hash des Vorgaengers (`prev`) und
  seinen eigenen `hash` = SHA-256 ueber (prev + kanonisches JSON des Eintrags ohne `hash`). Jede nachtraegliche Aenderung,
  Loeschung oder Einfuegung bricht die Kette -> `pruefe_kette()` meldet sie (GoBD: Unveraenderbarkeit, Rz. 107 ff.).
  Korrekturen sind neue Eintraege (Storno/Korrektur mit Bezug), nie Ueberschreiben.
- **Kein Leck-Schutz-Schwaerzen** beim Schreiben: Buchhaltungsdaten muessen unveraendert bleiben (der Leck-Schutz koennte
  Inhalte ersetzen, BF-20); in diesen Speicher gehoeren keine Geheimnisse.
- **Nummernkreise** (CEO 2026-09-27): Firmen `K-00001`, Ansprechpartner `AP-00001`, Angebote/Auftraege/Rechnungen/
  Eingangsbelege `AN-/AB-/RE-/ER-JJJJ-NNNN` -- lueckenlos, nie wiederverwendet, unter Dateisperre vergeben (Bot und Web-App
  schreiben in dieselbe Datei).
- **Belege** liegen unter `belege/<jahr>/` neben dem Log; ihr SHA-256 steht im Eintrag, `pruefe_belege()` erkennt
  veraenderte oder fehlende Dateien.
- **Aufbewahrung** (BEG IV): Belege 8 Jahre, Aufzeichnungen/Journal 10 Jahre, Geschaeftsbriefe 6 Jahre, jeweils ab Ende des
  Kalenderjahres. Loeschen ist nicht vorgesehen (CEO-Tor).
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import re
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

GENESIS = "0" * 64
KREISE_OHNE_JAHR = {"K": 5, "AP": 5}                      # Stammdaten: fortlaufend ueber alle Jahre
KREISE_MIT_JAHR = ("AN", "AB", "RE", "ER")                # Belege: je Jahr neu, 4-stellig
AUFBEWAHRUNG_JAHRE = {"beleg": 8, "aufzeichnung": 10, "geschaeftsbrief": 6}


def _kanonisch(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(prev: str, eintrag_ohne_hash: dict) -> str:
    return hashlib.sha256((prev + _kanonisch(eintrag_ohne_hash)).encode("utf-8")).hexdigest()


def sha256_datei(pfad: Path) -> str:
    h = hashlib.sha256()
    with Path(pfad).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def aufbewahren_bis(art: str, jahr: int) -> date:
    """Ende der Aufbewahrungsfrist: 31.12. des Jahres (jahr + Frist) -- Frist beginnt mit Ende des Kalenderjahres."""
    return date(int(jahr) + AUFBEWAHRUNG_JAHRE[art], 12, 31)


class Buchhaltung:
    def __init__(self, verzeichnis: str | Path):
        self.dir = Path(verzeichnis)
        self.log = self.dir / "log.jsonl"
        self.belege = self.dir / "belege"
        self._sperre = self.dir / ".sperre"

    # -- Schreiben -------------------------------------------------------------------------------------------------

    @contextmanager
    def _gesperrt(self):
        """Exklusive Dateisperre ueber Prozesse/Container hinweg (gleiche Datei auf der NAS)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        with self._sperre.open("a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def _anhaengen(self, typ: str, daten: dict, *, von: str = "") -> dict:
        """Neuen Eintrag an die Kette haengen (nur innerhalb der Sperre aufrufen)."""
        eintraege = self._eintraege()
        prev = eintraege[-1]["hash"] if eintraege else GENESIS
        ev = {"seq": len(eintraege) + 1, "ts": datetime.now().isoformat(timespec="seconds"), "typ": typ,
              "von": von, "daten": daten, "prev": prev}
        ev["hash"] = _hash(prev, ev)
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write(_kanonisch(ev) + "\n")
            fh.flush()
        return ev

    def erfassen(self, typ: str, daten: dict, *, von: str = "") -> dict:
        """Beliebigen fachlichen Eintrag erfassen (Kunde angelegt, Angebot, Rechnung festgeschrieben, Zahlung ...)."""
        if not re.fullmatch(r"[a-z_]+", typ or ""):
            raise ValueError(f"Ungueltiger Eintragstyp: {typ!r}")
        with self._gesperrt():
            return self._anhaengen(typ, daten, von=von)

    def vergebe_nummer(self, kreis: str, *, jahr: int | None = None, bezug: str = "", von: str = "") -> str:
        """Naechste Nummer eines Nummernkreises -- atomar, lueckenlos, als eigener Eintrag protokolliert."""
        kreis = (kreis or "").upper()
        if kreis not in KREISE_OHNE_JAHR and kreis not in KREISE_MIT_JAHR:
            raise ValueError(f"Unbekannter Nummernkreis: {kreis}")
        with self._gesperrt():
            if kreis in KREISE_OHNE_JAHR:
                n = 1 + sum(1 for e in self._eintraege() if e["typ"] == "nummer" and e["daten"]["kreis"] == kreis)
                nummer = f"{kreis}-{n:0{KREISE_OHNE_JAHR[kreis]}d}"
            else:
                jahr = int(jahr or datetime.now().year)
                n = 1 + sum(1 for e in self._eintraege() if e["typ"] == "nummer" and e["daten"]["kreis"] == kreis
                            and e["daten"].get("jahr") == jahr)
                nummer = f"{kreis}-{jahr}-{n:04d}"
            self._anhaengen("nummer", {"kreis": kreis, "jahr": jahr, "nummer": nummer, "bezug": bezug}, von=von)
            return nummer

    def beleg_ablegen(self, inhalt: bytes, dateiname: str, *, jahr: int | None = None, art: str = "beleg",
                      bezug: str = "", von: str = "") -> dict:
        """Datei unveraendert ablegen (PDF, Foto, XRechnung ...), Hash + Aufbewahrungsfrist protokollieren."""
        if art not in AUFBEWAHRUNG_JAHRE:
            raise ValueError(f"Unbekannte Aufbewahrungsart: {art}")
        jahr = int(jahr or datetime.now().year)
        sha = hashlib.sha256(inhalt).hexdigest()
        sicher = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(dateiname).name)[-80:] or "beleg"
        rel = Path("belege") / str(jahr) / f"{sha[:16]}-{sicher}"
        with self._gesperrt():
            ziel = self.dir / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            if not ziel.exists():
                ziel.write_bytes(inhalt)
            return self._anhaengen("beleg", {"pfad": str(rel), "sha256": sha, "groesse": len(inhalt),
                                             "name": dateiname, "art": art, "jahr": jahr, "bezug": bezug,
                                             "aufbewahren_bis": aufbewahren_bis(art, jahr).isoformat()}, von=von)

    # -- Lesen und Pruefen -----------------------------------------------------------------------------------------

    def _eintraege(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(z) for z in self.log.read_text(encoding="utf-8").splitlines() if z.strip()]

    def eintraege(self, typ: str | None = None) -> list[dict]:
        alle = self._eintraege()
        return [e for e in alle if e["typ"] == typ] if typ else alle

    def pruefe_kette(self) -> list[str]:
        """Leere Liste = Kette intakt. Sonst Befunde (veraendert, geloescht, eingefuegt, unlesbar)."""
        befunde, prev = [], GENESIS
        if not self.log.exists():
            return []
        for nr, zeile in enumerate(self.log.read_text(encoding="utf-8").splitlines(), start=1):
            if not zeile.strip():
                befunde.append(f"Zeile {nr}: leer")
                continue
            try:
                e = json.loads(zeile)
            except json.JSONDecodeError:
                befunde.append(f"Zeile {nr}: unlesbar")
                continue
            if e.get("seq") != nr:
                befunde.append(f"Zeile {nr}: seq {e.get('seq')} statt {nr} (Eintrag geloescht oder eingefuegt?)")
            if e.get("prev") != prev:
                befunde.append(f"Zeile {nr}: Verweis auf Vorgaenger passt nicht (Kette unterbrochen)")
            ohne = {k: v for k, v in e.items() if k != "hash"}
            if _hash(e.get("prev", ""), ohne) != e.get("hash"):
                befunde.append(f"Zeile {nr}: Inhalt veraendert (Hash passt nicht)")
            prev = e.get("hash", "")
        return befunde

    def pruefe_belege(self) -> list[str]:
        """Jede protokollierte Beleg-Datei vorhanden und unveraendert?"""
        befunde = []
        for e in self.eintraege("beleg"):
            d = e["daten"]
            pfad = self.dir / d["pfad"]
            if not pfad.exists():
                befunde.append(f"Beleg fehlt: {d['pfad']} (seq {e['seq']})")
            elif sha256_datei(pfad) != d["sha256"]:
                befunde.append(f"Beleg veraendert: {d['pfad']} (seq {e['seq']})")
        return befunde


def tagespruefung(bh: Buchhaltung) -> str | None:
    """Taegliche Integritaetspruefung (Kette + Belege). None = alles in Ordnung, sonst Alarmtext fuer den CEO."""
    befunde = bh.pruefe_kette() + bh.pruefe_belege()
    if not befunde:
        return None
    rest = f" (+{len(befunde) - 5} weitere)" if len(befunde) > 5 else ""
    return ("🚨 Buchhaltung: Integritaetspruefung fehlgeschlagen -- Aufzeichnungen wurden veraendert, geloescht "
            "oder Belege fehlen. Nichts reparieren, Backup-Stand vergleichen.\n- " + "\n- ".join(befunde[:5]) + rest)
