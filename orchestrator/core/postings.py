"""Postings je Auftragsposition mit Kennzahlen (PROJEKTBERICHT_ROADMAP P1/P2, CEO 2026-10-02).

Aus jeder Position, die eine Veroeffentlichung ist (Reel, Story, Bild-Post ...), werden so viele **Postings** wie die
Menge („2 x Reel“ = Reel 1, Reel 2). Jedes Posting traegt die **festgeschriebenen Plan-Werte seiner Position** je Stueck
(geplante Kontakte, TKP, Produktion, Preis -- Kopie aus dem Auftrag, Katalog-Aenderungen wirken nie zurueck), das
Veroeffentlichungsdatum mit Link und die **Kennzahlen als Zahlen** (Ereignisse in der Hash-Kette, mit Quelle und Verlauf).

Kontakt je Format (CEO 2026-10-02): Reel und Story = Aufrufe, Bild-Post/Karussell = Impressionen.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from pathlib import Path

from .buchhaltung import Buchhaltung, jetzt

ERINNERN_TAGE = 7
MESSPUNKT_LANG = 30                                     # P4: optionaler zweiter Messpunkt (Reels laufen lange)
FORMATE = {"reel": "Reel", "story": "Story", "feed": "Bild-Post"}
KONTAKT = {"reel": "aufrufe", "story": "aufrufe", "feed": "impressionen"}
FELDER = {
    "reel": [("aufrufe", "Aufrufe"), ("reichweite", "Erreichte Konten"), ("likes", "Likes"), ("kommentare", "Kommentare"),
             ("geteilt", "Geteilt"), ("gespeichert", "Gespeichert"), ("wiedergabe_s", "Ø Wiedergabezeit (Sek.)")],
    "feed": [("impressionen", "Impressionen"), ("reichweite", "Erreichte Konten"), ("likes", "Likes"),
             ("kommentare", "Kommentare"), ("geteilt", "Geteilt"), ("gespeichert", "Gespeichert"),
             ("profilaufrufe", "Profilaufrufe")],
    "story": [("aufrufe", "Aufrufe"), ("reichweite", "Erreichte Konten"), ("antworten", "Antworten"),
              ("link_klicks", "Link-Klicks"), ("sticker_taps", "Sticker-Taps"), ("weiter", "Weiter-Tipps"),
              ("zurueck", "Zurueck-Tipps")],
}
# Katalog-Artikel -> (Format, Plattform); Pakete, App, WhatsApp, Stadion, Affiliate sind keine einzelnen Postings
KATALOG = {"reel_solo": ("reel", "Instagram"), "reel_int": ("reel", "Instagram"), "feed": ("feed", "Instagram"),
           "story": ("story", "Instagram"), "fb_post": ("feed", "Facebook"), "x_post": ("feed", "X"),
           "tt_video": ("reel", "TikTok"), "yt_short": ("reel", "YouTube")}
KEIN_POSTING = {"wa", "push", "banner", "spieltag", "saison", "stadion", "affiliate", "twitch"}
PLATTFORMEN = ("Instagram", "Facebook", "TikTok", "YouTube", "X")
BILD_ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def format_von(p: dict) -> tuple[str, str] | None:
    """Position -> (Format, Plattform) oder None (keine Veroeffentlichung)."""
    kid = str(p.get("katalog_id") or "").lower()
    if kid in KATALOG:
        return KATALOG[kid]
    if kid in KEIN_POSTING or kid.startswith("pk_"):
        return None
    t = f"{p.get('beschreibung', '')} {p.get('gruppe', '')}".lower()
    plattform = next((n for n in PLATTFORMEN if n.lower() in t), "TikTok" if "tiktok" in t else "Instagram")
    if re.search(r"\breels?\b|tiktok|short", t):
        return "reel", plattform
    if re.search(r"\bstor(y|ies)\b", t):
        return "story", plattform
    if re.search(r"\b(post|feed|karussell|carousel)\b", t):
        return "feed", plattform
    return ("feed", plattform) if p.get("kontakte") else None


def postings_aus(auftrag: dict) -> list[dict]:
    """Postings aus den (festgeschriebenen) Positionen eines Auftrags -- stabile IDs `<Auftrag>-P<Pos>-<Nr>`."""
    out = []
    for i, p in enumerate(auftrag.get("positionen") or []):
        f = format_von(p)
        if not f:
            continue
        try:
            menge = float(str(p.get("menge") or 1).replace(",", "."))
        except ValueError:
            menge = 1
        n = int(menge) if menge == int(menge) and 1 <= menge <= 50 else 1
        name = FORMATE[f[0]]
        for k in range(1, n + 1):
            out.append({"id": f"{auftrag['nummer']}-P{i + 1}-{k}", "auftrag": auftrag["nummer"], "position": i + 1,
                        "nr": k, "titel": f"{name} {k}" if n > 1 else name, "beschreibung": p.get("beschreibung", ""),
                        "format": f[0], "plattform": f[1], "kontakt_feld": KONTAKT[f[0]],
                        "plan": {"kontakte": int(p.get("kontakte") or 0), "tkp_cent": int(p.get("tkp_cent") or 0),
                                 "produktion_cent": int(p.get("produktion_cent") or 0),
                                 "preis_cent": int(p.get("einzelpreis_cent") or 0)}})
    return out


class Postings:
    def __init__(self, bh: Buchhaltung, auftraege, ordner: Path | str | None = None):
        self.bh, self.auftraege = bh, auftraege
        self.ordner = Path(ordner) if ordner else bh.dir.parent / "lieferungen"

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if not str(t).startswith("posting_"):
                continue
            x = out.setdefault(d["id"], {"bilder": [], "verlauf": []})
            spur = {"ts": e["ts"], "von": e.get("von", ""), "typ": t}
            if t == "posting_veroeffentlicht":
                x |= {k: d.get(k) for k in ("datum", "link", "plattform")}
            elif t == "posting_kennzahlen" and d.get("messpunkt") == MESSPUNKT_LANG:
                x["kennzahlen_30"] = d["werte"]
                x["kennzahlen_30_am"] = e["ts"]
            elif t == "posting_kennzahlen":
                x["kennzahlen"] = d["werte"]
                x["kennzahlen_quelle"] = d.get("quelle", "")
                x["kennzahlen_am"] = e["ts"]
            elif t == "posting_bild":
                x["bilder"].append({k: d.get(k) for k in ("pfad", "name", "sha256")} | {"ts": e["ts"]})
            elif t == "posting_erinnert":
                x["erinnert"] = e["ts"]
            x["verlauf"].append(spur)
        return out

    def liste(self, auftrag: str, eintraege: list[dict] | None = None) -> list[dict]:
        e = self.bh.eintraege() if eintraege is None else eintraege
        a = self.auftraege.auftrag(auftrag) if self.auftraege else None
        if not a:
            raise KeyError(auftrag)
        st = self._falte(e)
        return [p | st.get(p["id"], {"bilder": [], "verlauf": []}) | {"kennzahl_faellig": _faellig(st.get(p["id"], {}))}
                for p in postings_aus(a)]

    def get(self, pid: str) -> dict | None:
        nr = _auftrag_von(pid)
        try:
            return next((p for p in self.liste(nr) if p["id"] == pid), None)
        except KeyError:
            return None

    def _pruefe(self, pid: str) -> dict:
        p = self.get(pid)
        if not p:
            raise KeyError(pid)
        a = self.auftraege.auftrag(p["auftrag"])
        if a["status"] == "storniert":
            raise ValueError(f"{p['auftrag']} ist storniert.")
        return p

    def veroeffentlichen(self, pid: str, *, datum: str, link: str = "", plattform: str = "", von: str = "") -> dict:
        p = self._pruefe(pid)
        try:
            tag = date.fromisoformat(str(datum)[:10])
        except ValueError:
            raise ValueError("Datum der Veroeffentlichung fehlt oder ist ungueltig.") from None
        if tag > jetzt().date():
            raise ValueError("Das Datum liegt in der Zukunft.")
        link = (link or "").strip()
        if link and not re.match(r"^https?://[^\s/]+\.[^\s]+$", link):
            raise ValueError("Kein gueltiger Link (https://…).")
        pl = (plattform or p["plattform"]).strip()
        if pl not in PLATTFORMEN:
            raise ValueError(f"Plattform: {', '.join(PLATTFORMEN)}.")
        d = {"id": pid, "datum": tag.isoformat(), "link": link[:500], "plattform": pl}
        self.bh.erfassen("posting_veroeffentlicht", d, von=von)
        return d

    def kennzahlen_setzen(self, pid: str, werte: dict, *, quelle: str = "formular", messpunkt: int = ERINNERN_TAGE,
                          von: str = "") -> dict:
        """Kennzahlen als ganze Zahlen (Pflicht: die Kontakt-Kennzahl des Formats). Erneut = Korrektur mit Verlauf.
        `messpunkt=30` = zweiter Messpunkt (P4); Bericht und TKP-Vergleich rechnen mit dem 7-Tage-Wert."""
        p = self._pruefe(pid)
        if messpunkt not in (ERINNERN_TAGE, MESSPUNKT_LANG):
            raise ValueError("Messpunkt: 7 oder 30 Tage.")
        if messpunkt == MESSPUNKT_LANG and not p.get("kennzahlen"):
            raise ValueError("Erst die Zahlen nach 7 Tagen eintragen, dann den 30-Tage-Wert.")
        erlaubt = dict(FELDER[p["format"]])
        out = {}
        for k, v in (werte or {}).items():
            if k not in erlaubt or v in (None, ""):
                continue
            try:
                n = int(round(float(str(v).replace(".", "").replace(" ", "").replace(",", "."))))
            except ValueError:
                raise ValueError(f"{erlaubt[k]}: bitte eine Zahl.") from None
            if not 0 <= n <= 2_000_000_000:
                raise ValueError(f"{erlaubt[k]}: Zahl ausserhalb des Bereichs.")
            out[k] = n
        if p["kontakt_feld"] not in out:
            raise ValueError(f"{erlaubt[p['kontakt_feld']]} fehlt -- das ist die Kontakt-Kennzahl fuer {FORMATE[p['format']]}s.")
        d = {"id": pid, "werte": out, "quelle": quelle[:40]} | ({"messpunkt": messpunkt} if messpunkt != ERINNERN_TAGE else {})
        self.bh.erfassen("posting_kennzahlen", d, von=von)
        return {"id": pid, "werte": out, "messpunkt": messpunkt}

    def bild_ablegen(self, pid: str, daten: bytes, name: str, *, von: str = "") -> dict:
        """Screenshot der Insights am Posting ablegen (`lieferungen/<Auftrag>/kennzahlen/`, wie Lieferungen nur NAS)."""
        p = self._pruefe(pid)
        endung = Path(name or "bild.jpg").suffix.lower() or ".jpg"
        if endung not in BILD_ENDUNGEN:
            raise ValueError("Bitte ein Bild (JPG, PNG, WEBP, HEIC).")
        if not daten or len(daten) > 20 * 1024 * 1024:
            raise ValueError("Bild leer oder groesser als 20 MB.")
        sha = hashlib.sha256(daten).hexdigest()
        ziel = self.ordner / p["auftrag"] / "kennzahlen"
        ziel.mkdir(parents=True, exist_ok=True)
        datei = ziel / f"{pid}-{sha[:10]}{endung}"
        datei.write_bytes(daten)
        d = {"id": pid, "pfad": str(datei.relative_to(self.ordner)), "name": datei.name, "sha256": sha}
        self.bh.erfassen("posting_bild", d, von=von)
        return d

    def bild_datei(self, pid: str, i: int) -> Path | None:
        p = self.get(pid)
        if not p or not 0 <= i < len(p["bilder"]):
            return None
        f = (self.ordner / p["bilder"][i]["pfad"]).resolve()
        return f if f.is_file() and self.ordner.resolve() in f.parents else None

    def auslesen(self, pid: str, *, key: str = "", client=None) -> dict:
        """Alle Screenshots des Postings an Gemini -> Vorschlag {feld: zahl} (gespeichert wird erst nach Bestaetigung)."""
        from .kennzahlen_lesen import lesen
        p = self._pruefe(pid)
        bilder = [(f.read_bytes(), f.name) for i in range(len(p["bilder"])) if (f := self.bild_datei(pid, i))]
        if not bilder:
            raise ValueError("Noch kein Screenshot an diesem Posting.")
        return lesen(bilder[-4:], FELDER[p["format"]], FORMATE[p["format"]], key=key, client=client)

    def erinnert(self, pid: str) -> None:
        self.bh.erfassen("posting_erinnert", {"id": pid}, von="LUNA-Kennzahlen")

    def faellige(self, heute: date | None = None) -> list[dict]:
        """Postings, deren Kennzahlen faellig sind (veroeffentlicht + 7 Tage, noch keine Kennzahlen), mit Auftrag/Firma."""
        from .beauftragung import AuftragBuch
        e = self.bh.eintraege()
        st = self._falte(e)
        out = []
        for a in AuftragBuch._falte(e).values():
            if a["status"] == "storniert":
                continue
            for p in postings_aus(a):
                x = p | st.get(p["id"], {"bilder": [], "verlauf": []})
                if _faellig(x, heute):
                    out.append(x | {"firma": a["firma"], "auftrag_titel": a.get("titel", "")})
        return out


def _auftrag_von(pid: str) -> str:
    return str(pid or "").rsplit("-P", 1)[0]


def _faellig(p: dict, heute: date | None = None) -> bool:
    if not p.get("datum") or p.get("kennzahlen"):
        return False
    return date.fromisoformat(p["datum"]) + timedelta(days=ERINNERN_TAGE) <= (heute or jetzt().date())


def konditionen(auftrag: dict) -> dict:
    """Die beim Anlegen festgeschriebenen Konditionen je Position (Kopie im Auftrag, nie aus dem Katalog nachgeladen)."""
    zeilen = [{"position": i + 1, "beschreibung": p.get("beschreibung", ""), "menge": p.get("menge"),
               "einheit": p.get("einheit", ""), "kontakte": int(p.get("kontakte") or 0),
               "tkp_cent": int(p.get("tkp_cent") or 0), "produktion_cent": int(p.get("produktion_cent") or 0),
               "einzelpreis_cent": int(p.get("einzelpreis_cent") or 0), "gesamt_cent": p.get("gesamt_cent")}
              for i, p in enumerate(auftrag.get("positionen") or [])]
    return {"festgeschrieben_am": str(auftrag.get("angelegt") or "")[:10], "angebot": auftrag.get("angebot", ""),
            "positionen": zeilen}


def vergleich(postings: list[dict]) -> dict:
    """TKP-Vergleich je Posting und als Summe (CEO 2026-10-02).

    Gegenwert Ist = Kontakte_Ist x TKP / 1.000 + Produktion; Mehrleistung = Gegenwert - Preis;
    effektiver TKP = (Preis - Produktion) / Kontakte_Ist x 1.000. Pauschalen (ohne TKP): nur Reichweite.
    """
    zeilen, s = [], {"kontakte_plan": 0, "kontakte_ist": 0, "preis_cent": 0, "gegenwert_cent": 0, "mehrleistung_cent": 0,
                     "gemessen": 0, "anzahl": len(postings)}
    for p in postings:
        pl = p["plan"]
        ist = (p.get("kennzahlen") or {}).get(p["kontakt_feld"])
        z = {"id": p["id"], "titel": p["titel"], "format": p["format"], "kontakte_plan": pl["kontakte"], "kontakte_ist": ist,
             "preis_cent": pl["preis_cent"], "tkp_cent": pl["tkp_cent"], "erfuellung_pct": None, "gegenwert_cent": None,
             "mehrleistung_cent": None, "tkp_eff_cent": None}
        if ist is not None:
            s["gemessen"] += 1
            if pl["kontakte"]:
                z["erfuellung_pct"] = round(ist / pl["kontakte"] * 100, 1)
            if pl["tkp_cent"]:
                z["gegenwert_cent"] = round(ist * pl["tkp_cent"] / 1000) + pl["produktion_cent"]
                z["mehrleistung_cent"] = z["gegenwert_cent"] - pl["preis_cent"]
                if ist:
                    z["tkp_eff_cent"] = round((pl["preis_cent"] - pl["produktion_cent"]) / ist * 1000)
                s["kontakte_plan"] += pl["kontakte"]
                s["kontakte_ist"] += ist
                s["preis_cent"] += pl["preis_cent"]
                s["gegenwert_cent"] += z["gegenwert_cent"]
                s["mehrleistung_cent"] += z["mehrleistung_cent"]
        zeilen.append(z)
    s["mehrleistung_pct"] = round(s["mehrleistung_cent"] / s["preis_cent"] * 100, 1) if s["preis_cent"] else None
    s["erfuellung_pct"] = round(s["kontakte_ist"] / s["kontakte_plan"] * 100, 1) if s["kontakte_plan"] else None
    return {"zeilen": zeilen, "summe": s}


def lang_faellig(p: dict, heute: date | None = None) -> bool:
    """P4: Reel mit 7-Tage-Zahlen, aber ohne 30-Tage-Wert, 30 Tage nach der Veroeffentlichung."""
    if p.get("format") != "reel" or not p.get("datum") or not p.get("kennzahlen") or p.get("kennzahlen_30"):
        return False
    return date.fromisoformat(p["datum"]) + timedelta(days=MESSPUNKT_LANG) <= (heute or jetzt().date())


def ist_kontakte(eintraege: list[dict]) -> dict[str, dict]:
    """P4: gemessene Kontakte (7 Tage) je Katalog-Artikel -> Median als Vorschlag fuer die Katalog-Kontakte."""
    from statistics import median
    from .beauftragung import AuftragBuch
    st = Postings._falte(eintraege)
    werte: dict[str, list[int]] = {}
    for a in AuftragBuch._falte(eintraege).values():
        if a["status"] == "storniert":
            continue
        for i, pos in enumerate(a.get("positionen") or []):
            kid = str(pos.get("katalog_id") or "")
            for p in postings_aus(a):
                if not kid or p["position"] != i + 1:
                    continue
                v = (st.get(p["id"], {}).get("kennzahlen") or {}).get(p["kontakt_feld"])
                if v is not None:
                    werte.setdefault(kid, []).append(int(v))
    return {k: {"median": int(median(v)), "anzahl": len(v), "min": min(v), "max": max(v)} for k, v in werte.items()}


def kampagnen(eintraege: list[dict], firma: str) -> list[dict]:
    """P4: Kampagnen-Historie je Kunde fuer die Firmenakte (neueste zuerst)."""
    from .beauftragung import AuftragBuch, abschluss
    st = Postings._falte(eintraege)
    out = []
    for a in abschluss(AuftragBuch._falte(eintraege), eintraege).values():
        if a["firma"] != firma or a["status"] == "storniert":
            continue
        ps = [p | st.get(p["id"], {}) for p in postings_aus(a)]
        v = vergleich(ps)["summe"] if ps else {}
        out.append({"nummer": a["nummer"], "titel": a.get("titel", ""), "datum": a.get("datum", ""), "status": a["status"],
                    "abgeschlossen": a.get("abgeschlossen", False), "postings": len(ps),
                    "gemessen": v.get("gemessen", 0), "kontakte_ist": sum(((p.get("kennzahlen") or {}).get(p["kontakt_feld"]) or 0)
                                                                          for p in ps),
                    "mehrleistung_cent": v.get("mehrleistung_cent") if v.get("preis_cent") else None,
                    "bericht": bool(a.get("berichte"))})
    return sorted(out, key=lambda x: x["nummer"], reverse=True)
