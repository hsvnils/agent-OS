"""Einwilligungen in Bild-/Video-/Tonaufnahmen je Auftrag (EINWILLIGUNG_AUFNAHMEN E2/E3, CEO 2026-10-08).

Vor dem Dreh traegt sich jede Person am iPad ein (Tastatur) und unterschreibt mit dem Apple Pencil; LUNA erzeugt daraus
eine **PDF A4 hochkant** mit dem Text der verwendeten Vorlagenversion (Vertragswerk, Art `einwilligung`), den Daten, den
angekreuzten Zwecken und der Unterschrift (bei unter 16 Jahren zusaetzlich die der Erziehungsberechtigten).

Ablage bewusst **nur auf der NAS** (CEO-Entscheidung 2026-10-08): eigener Ordner `einwilligungen/` (Log + PDFs), mit
Backup, aber **nicht** in der Buchhaltungs-Kette und **nicht** in LUNAs Google Drive -- personenbezogene Daten Dritter so
wenig wie moeglich verteilen. Das Log enthaelt die Personendaten, nie das Unterschriftsbild (das steckt nur in der PDF).
Nachweis (Art. 7 Abs. 1 DSGVO): Zeitstempel, Vorlagenversion, SHA-256 der PDF.

Ereignisse (append-only, `einwilligungen/log.jsonl`): `erteilt`, `versendet` (Kopie an die Person), `widerrufen`.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path

ZWECKE = {
    "eigene_kanaele": "Social-Media-Kanäle von {Auftragnehmer} (z. B. Instagram, TikTok, YouTube, Facebook)",
    "kunde_kanaele": "Social-Media-Kanäle und Website von {Kunde}",
    "werbung": "Bezahlte Werbeanzeigen mit den Aufnahmen auf diesen Kanälen",
    "website": "Website und Referenzen von {Auftragnehmer}",
    "print": "Druck und Präsentationen (z. B. Plakate, Flyer)",
    "name": "Nennung meines Namens bzw. Profils (z. B. @-Markierung)",
}
STANDARD_ZWECKE = ("eigene_kanaele", "kunde_kanaele")
KONTAKT_STANDARD = "nils@hanserautisch.de"
MAX_PNG = 600_000                       # Unterschriftsbild (Data-URL) -- reicht fuer 1600x500 px


def _jetzt() -> datetime:
    return datetime.now().astimezone()


def alter(geburtsdatum: str, am: date) -> int | None:
    try:
        g = date.fromisoformat(str(geburtsdatum)[:10])
    except ValueError:
        return None
    return am.year - g.year - ((am.month, am.day) < (g.month, g.day))


def _png(data_url: str, was: str) -> bytes:
    """Data-URL eines PNG (Canvas) -> Bytes; leere oder zu kleine Unterschrift wird abgelehnt."""
    m = re.match(r"^data:image/png;base64,([A-Za-z0-9+/=]+)$", str(data_url or "").strip())
    if not m or len(m.group(1)) > MAX_PNG:
        raise ValueError(f"Bitte {was} unterschreiben.")
    roh = base64.b64decode(m.group(1))
    if not roh.startswith(b"\x89PNG") or len(roh) < 300:
        raise ValueError(f"Bitte {was} unterschreiben.")
    return roh


def _text(v, n: int = 120) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


class EinwilligungStore:
    def __init__(self, root: str | Path):
        self.dir = Path(root)
        self.log = self.dir / "log.jsonl"

    # -- Lesen ---------------------------------------------------------------------------------------------------
    def _events(self) -> list[dict]:
        if not self.log.exists():
            return []
        out = []
        for z in self.log.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(z))
            except ValueError:
                continue
        return out

    def _falte(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in self._events():
            t, i = e.get("typ"), e.get("id")
            if t == "erteilt":
                out[i] = dict(e) | {"versendet": [], "widerruf": None}
            elif i in out and t == "versendet":
                out[i]["versendet"].append({"an": e.get("an", ""), "ts": e.get("ts")})
            elif i in out and t == "widerrufen":
                out[i]["widerruf"] = {k: e.get(k) for k in ("datum", "weg", "notiz", "ts", "von")}
        return out

    def get(self, eid: str) -> dict | None:
        return self._falte().get(str(eid or ""))

    def liste(self, auftrag: str = "") -> list[dict]:
        a = str(auftrag or "").strip().upper()
        return sorted((x for x in self._falte().values() if not a or x.get("auftrag") == a), key=lambda x: x["ts"])

    def letzte_person(self, *, vorname: str = "", nachname: str = "", mail: str = "") -> dict | None:
        """Angaben aus der juengsten, nicht widerrufenen Einwilligung derselben Person (gleicher Vor- und Nachname oder
        gleiche Mail) -- damit nichts doppelt getippt wird, ohne Geburtsdatum/Anschrift im Kundenstamm (CEO 2026-10-08)."""
        n = (str(vorname or "").strip().lower(), str(nachname or "").strip().lower())
        m = str(mail or "").strip().lower()
        for x in reversed(self.liste()):
            p = x.get("person") or {}
            gleich = (all(n) and (p.get("vorname", "").lower(), p.get("nachname", "").lower()) == n) or \
                     (m and p.get("mail", "").lower() == m)
            if gleich and not x.get("widerruf"):
                return dict(p) | {"aus": x["id"], "datum": x.get("datum", "")}
        return None

    def pdf(self, eid: str) -> bytes:
        x = self.get(eid)
        if not x:
            raise KeyError(eid)
        return (self.dir / x["pfad"]).read_bytes()

    # -- Schreiben -----------------------------------------------------------------------------------------------
    def _append(self, ev: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def erteilen(self, auftrag: dict, eingabe: dict, *, vorlage: dict, firmendaten: dict, kunde: str,
                 von: str = "", heute: date | None = None, logo: Path | None = None) -> dict:
        """Person + Unterschrift(en) -> PDF + Ereignis. `vorlage` = Version der Vorlage `einwilligung` (titel, paragraphen, version)."""
        heute = heute or _jetzt().date()
        p = eingabe.get("person") or {}
        person = {k: _text(p.get(k), 160 if k == "strasse" else 120) for k in ("vorname", "nachname", "strasse", "plz", "ort",
                                                                               "geburtsdatum", "mail", "telefon")}
        if not person["vorname"] or not person["nachname"]:
            raise ValueError("Bitte Vor- und Nachnamen eintragen.")
        if not (person["strasse"] and person["plz"] and person["ort"]):
            raise ValueError("Bitte die Anschrift eintragen (Straße, PLZ, Ort).")
        jahre = alter(person["geburtsdatum"], heute) if person["geburtsdatum"] else None
        if person["geburtsdatum"] and (jahre is None or not 0 <= jahre <= 120):
            raise ValueError("Geburtsdatum ungültig.")
        zwecke = [z for z in (eingabe.get("zwecke") or []) if z in ZWECKE]
        if not [z for z in zwecke if z != "name"]:
            raise ValueError("Bitte mindestens einen Zweck ankreuzen.")
        minderjaehrig = jahre is not None and jahre < 16
        unterschrift = None if minderjaehrig and jahre < 14 else _png(eingabe.get("unterschrift_person"), "die Person")
        eltern = None
        if minderjaehrig:
            name = _text(eingabe.get("eltern_name"))
            if not name:
                raise ValueError("Unter 16 Jahren: Bitte Name der/des Erziehungsberechtigten eintragen.")
            eltern = {"name": name, "png": _png(eingabe.get("unterschrift_eltern"), "die/den Erziehungsberechtigte(n)")}
        verguetung = _text(eingabe.get("verguetung"), 80)
        eid = "EW-" + heute.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6]
        ts = _jetzt().isoformat(timespec="seconds")
        ort = _text(eingabe.get("ort") or firmendaten.get("ort") or "", 80)
        werte = {"Auftragnehmer": firmendaten.get("firma") or "Hanserautisch", "Kunde": kunde or "dem Auftraggeber",
                 "Projekt": auftrag.get("titel") or auftrag["nummer"], "Datum": heute.strftime("%d.%m.%Y"), "Ort": ort or "–",
                 "Kontakt": firmendaten.get("mail") or KONTAKT_STANDARD,
                 "Anschrift": firmen_anschrift(firmendaten)}
        pdf = _pdf(eid, vorlage, werte, person, zwecke, verguetung, unterschrift, eltern, jahre, ts, firmendaten=firmendaten, logo=logo)
        rel = Path("pdf") / str(heute.year) / f"{eid}.pdf"
        (self.dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.dir / rel).write_bytes(pdf)
        ev = {"typ": "erteilt", "id": eid, "ts": ts, "von": von, "auftrag": auftrag["nummer"], "firma": auftrag.get("firma", ""),
              "person": person, "alter": jahre, "minderjaehrig": minderjaehrig, "eltern_name": (eltern or {}).get("name", ""),
              "zwecke": zwecke, "verguetung": verguetung, "datum": heute.isoformat(), "ort": ort,
              "vorlage_version": vorlage.get("version"), "pfad": str(rel), "sha256": hashlib.sha256(pdf).hexdigest()}
        self._append(ev)
        return {"id": eid, "pfad": str(rel)}

    def versendet(self, eid: str, an: str, *, von: str = "") -> None:
        if not self.get(eid):
            raise KeyError(eid)
        self._append({"typ": "versendet", "id": eid, "ts": _jetzt().isoformat(timespec="seconds"), "von": von, "an": an})

    def widerrufen(self, eid: str, *, datum: str = "", weg: str = "", notiz: str = "", von: str = "") -> dict:
        x = self.get(eid)
        if not x:
            raise KeyError(eid)
        if x["widerruf"]:
            raise ValueError("Der Widerruf ist schon vermerkt.")
        try:
            d = date.fromisoformat(str(datum or _jetzt().date().isoformat())[:10])
        except ValueError:
            raise ValueError("Datum ungültig.") from None
        if not _text(weg, 60):
            raise ValueError("Bitte angeben, wie widerrufen wurde (z. B. Mail, Anruf, persönlich).")
        self._append({"typ": "widerrufen", "id": eid, "ts": _jetzt().isoformat(timespec="seconds"), "von": von,
                      "datum": d.isoformat(), "weg": _text(weg, 60), "notiz": _text(notiz, 300)})
        return {"id": eid, "widerrufen": d.isoformat()}


def _fuellen(text: str, werte: dict) -> str:
    return re.sub(r"\{([A-Za-zÄÖÜäöüß_]+)\}", lambda m: str(werte.get(m.group(1), m.group(0))), text)


def firmen_anschrift(fd: dict) -> str:
    """Eigene Anschrift fuer Texte, inkl. c/o-Zusatz (CEO 2026-10-08: „c/o Hanserautisch“ fehlte)."""
    return ", ".join(x for x in (fd.get("zusatz"), fd.get("strasse"), " ".join(x for x in (fd.get("plz"), fd.get("ort")) if x)) if x)


def _pdf(eid, vorlage, werte, person, zwecke, verguetung, unterschrift, eltern, jahre, ts, *, firmendaten=None, logo=None) -> bytes:
    """A4 hochkant: Hanserautisch-Kopf, Titel, Projektzeile, Paragraphen, Zwecke (angekreuzt), Personendaten, Unterschrift(en), Nachweis-Fuss."""
    from fpdf import FPDF
    from .beleg_pdf import DEJAVU, _latin1, absender_zeile, hanserautisch_kopf
    uni = (DEJAVU / "DejaVuSans.ttf").exists() and (DEJAVU / "DejaVuSans-Bold.ttf").exists()
    T = (lambda x: str(x or "")) if uni else _latin1

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-13)
            self.set_font(S, size=7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 4, T(f"Erklärung {eid} · Vorlage „{vorlage.get('titel', '')}“ Version {vorlage.get('version', '–')} · "
                              f"erfasst {ts} · Seite {self.page_no()}/{{nb}}"), align="C")

    p = _Pdf(format="A4")                                   # hochkant (CEO 2026-10-08: PDFs immer hochkant)
    S = "Helvetica"
    if uni:
        p.add_font("DejaVu", "", str(DEJAVU / "DejaVuSans.ttf"))
        p.add_font("DejaVu", "B", str(DEJAVU / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    p.set_margins(18, 14, 18)
    p.set_auto_page_break(True, margin=18)
    p.alias_nb_pages()
    p.add_page()
    y = hanserautisch_kopf(p, logo=logo, x=18, y=12, logo_breite=50)  # wie Angebot/Rechnung (CEO 2026-10-08)
    p.set_xy(18, y + 4)
    p.set_font(S, "", 6.8)
    p.set_text_color(136, 136, 136)
    p.cell(0, 3.2, T(absender_zeile(firmendaten or {})), new_x="LMARGIN", new_y="NEXT")
    p.ln(4)
    p.set_text_color(0, 64, 135)
    p.set_font(S, "B", 15)
    p.multi_cell(0, 7, T(vorlage.get("titel") or "Einwilligung in Bild- und Videoaufnahmen"), new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(40, 40, 40)
    p.set_font(S, "", 9)
    p.multi_cell(0, 5, T(f"Projekt: {werte['Projekt']} · Auftraggeber: {werte['Kunde']} · Aufnahmen durch {werte['Auftragnehmer']} · "
                         f"{werte['Ort']}, {werte['Datum']}"), new_x="LMARGIN", new_y="NEXT")
    p.ln(2)
    for par in vorlage.get("paragraphen") or []:
        p.set_font(S, "B", 9.5)
        p.multi_cell(0, 5, T(par.get("titel", "")), new_x="LMARGIN", new_y="NEXT")
        p.set_font(S, "", 9)
        p.multi_cell(0, 4.5, T(_fuellen(par.get("text", ""), werte)), new_x="LMARGIN", new_y="NEXT")
        p.ln(1.2)
    p.ln(1)
    p.set_font(S, "B", 10)
    p.cell(0, 6, T("Ich willige ein in folgende Zwecke:"), new_x="LMARGIN", new_y="NEXT")
    p.set_font(S, "", 9.5)
    for k, txt in ZWECKE.items():
        p.multi_cell(0, 5, T(("☒ " if uni else "[x] ") if k in zwecke else ("☐ " if uni else "[ ] ")) + T(_fuellen(txt, werte)),
                     new_x="LMARGIN", new_y="NEXT")
    p.multi_cell(0, 5, T(f"Vergütung: {verguetung or 'keine (unentgeltlich)'}"), new_x="LMARGIN", new_y="NEXT")
    p.ln(2)
    if p.get_y() > (190 if eltern else 215):              # Person + Unterschrift(en) immer zusammen auf einer Seite
        p.add_page()
    p.set_font(S, "B", 10)
    p.cell(0, 6, T("Person"), new_x="LMARGIN", new_y="NEXT")
    p.set_font(S, "", 9.5)
    zeilen = [f"{person['vorname']} {person['nachname']}", f"{person['strasse']}, {person['plz']} {person['ort']}"]
    if person["geburtsdatum"]:
        zeilen.append("Geburtsdatum: " + date.fromisoformat(person["geburtsdatum"][:10]).strftime("%d.%m.%Y")
                      + (f" ({jahre} Jahre)" if jahre is not None and jahre < 18 else ""))
    if person["mail"] or person["telefon"]:
        zeilen.append(" · ".join(x for x in (person["mail"], person["telefon"]) if x))
    for z in zeilen:
        p.multi_cell(0, 5, T(z), new_x="LMARGIN", new_y="NEXT")
    p.ln(3)

    def feld(png: bytes | None, unter: str):
        if p.get_y() > 245:
            p.add_page()
        y = p.get_y()
        if png:
            p.image(io.BytesIO(png), x=18, y=y, w=70, h=22)
        p.set_draw_color(120, 120, 120)
        p.line(18, y + 23, 98, y + 23)
        p.set_xy(18, y + 24)
        p.set_font(S, "", 8)
        p.cell(0, 4, T(unter), new_x="LMARGIN", new_y="NEXT")
        p.ln(3)
    datum_ort = f"{werte['Ort']}, {werte['Datum']}"
    if unterschrift is not None:
        feld(unterschrift, f"{datum_ort} · Unterschrift {person['vorname']} {person['nachname']}")
    if eltern:
        feld(eltern["png"], f"{datum_ort} · Unterschrift Erziehungsberechtigte(r): {eltern['name']}")
    return bytes(p.output())
