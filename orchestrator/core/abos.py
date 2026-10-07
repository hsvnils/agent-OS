"""KUNDEN_FINANZEN Etappe 15: wiederkehrende Zahlungen / Abos (CEO 2026-09-29).

Ein Abo `ABO-00001` ist eine Vorlage (Firma, Betrag, Kategorie, Turnus, erste Faelligkeit, optional Ende und
Kuendigungsfrist). Aus ihr ergeben sich Faelligkeiten; jede Faelligkeit wird genau einmal erledigt:

- **gebucht** -- LUNA legt einen Eigenbeleg an (per Klick des CEO oder, wenn beim Abo angehakt, automatisch),
- **Beleg** -- fuer die Firma kam im Zeitraum ein gebuchter Eingangsbeleg mit aehnlichem Betrag (±25 %) -> nichts doppelt,
- **uebersprungen** -- mit Grund (z. B. Gratismonat).

Kommt der Beleg per Mail (Haken „Beleg kommt per Mail“), bucht LUNA nie selbst, sondern wartet auf den Beleg und meldet
erst nach der Karenz, dass er fehlt. Alles liegt als Ereignis in der Hash-Kette; Aenderungen gelten fuer kuenftige
Faelligkeiten, beenden stoppt sie -- geloescht wird nichts.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from .beleg_pdf import cent
from .buchhaltung import Buchhaltung, jetzt
from .eigenbelege import EigenbelegStore, datum_pruefen
from .eingangsbelege import EINNAHME_KATEGORIEN, KATEGORIEN, EingangStore

TURNUS = {"woechentlich": ("wöchentlich", 0), "monatlich": ("monatlich", 1), "zweimonatlich": ("alle 2 Monate", 2),
          "vierteljaehrlich": ("vierteljährlich", 3), "halbjaehrlich": ("halbjährlich", 6), "jaehrlich": ("jährlich", 12)}
FELDER = ("bezeichnung", "firma", "art", "betrag_cent", "kategorie", "turnus", "start", "ende", "kuendigungsfrist_tage",
          "zahlungsweg", "vertragsnummer", "beleg_per_mail", "auto_buchen", "notiz",
          "rechnung_von")                 # abweichender Rechnungssteller (z. B. Apple App Store fuer Meta Verified)
KARENZ_TAGE = 10                  # Beleg per Mail: so lange nach Faelligkeit warten, bevor „fehlt“ gemeldet wird
ABGLEICH_TAGE = {"woechentlich": 3, "jaehrlich": 30, "halbjaehrlich": 20}   # Fenster fuer den Beleg-Abgleich (sonst 10)


def plus_monate(d: date, n: int, tag: int) -> date:
    """d + n Monate am Wunschtag `tag`, im kurzen Monat auf den letzten Tag gekuerzt (31.01. -> 28./29.02. -> 31.03.)."""
    j, m = divmod(d.month - 1 + n, 12)
    jahr, monat = d.year + j, m + 1
    return date(jahr, monat, min(tag, calendar.monthrange(jahr, monat)[1]))


def faelligkeiten(abo: dict, bis: date) -> list[str]:
    """Alle Faelligkeiten von `start` bis einschliesslich `bis` (und hoechstens bis `ende`)."""
    start = date.fromisoformat(abo["start"])
    ende = date.fromisoformat(abo["ende"]) if abo.get("ende") else None
    grenze = min(bis, ende) if ende else bis
    schritt = TURNUS[abo["turnus"]][1]
    out, i = [], 0
    while True:
        d = start + timedelta(weeks=i) if schritt == 0 else plus_monate(start, i * schritt, start.day)
        if d > grenze or i > 2000:
            return out
        out.append(d.isoformat())
        i += 1


def naechste(abo: dict, heute: date) -> str:
    kommend = [d for d in faelligkeiten(abo, heute + timedelta(days=400)) if d > heute.isoformat()]
    return kommend[0] if kommend else ""


def monatlich_cent(abo: dict) -> int:
    """Kosten je Monat (jaehrlich / 12, woechentlich x 52 / 12)."""
    schritt = TURNUS[abo["turnus"]][1]
    return round(abo["betrag_cent"] * 52 / 12) if schritt == 0 else round(abo["betrag_cent"] / schritt)


def pruefen(daten: dict, kunden=None) -> dict:
    """Eingaben pruefen und bereinigen (ValueError mit Grund). `firma` muss eine Stammdaten-Nummer sein."""
    d: dict = {}
    d["bezeichnung"] = str(daten.get("bezeichnung") or "").strip()[:120]
    if len(d["bezeichnung"]) < 2:
        raise ValueError("Bitte eine Bezeichnung angeben (z. B. iCloud+ 2 TB).")
    d["art"] = str(daten.get("art") or "ausgabe").strip()
    if d["art"] not in ("ausgabe", "einnahme"):
        raise ValueError("Art muss Ausgabe oder Einnahme sein.")
    roh = daten.get("betrag")
    if roh in (None, "") and daten.get("betrag_cent") is not None:
        roh = int(daten["betrag_cent"]) / 100
    try:
        d["betrag_cent"] = abs(cent(roh))
    except (ValueError, TypeError):
        raise ValueError("Betrag fehlt oder ist ungueltig.") from None
    if d["betrag_cent"] <= 0:
        raise ValueError("Betrag muss groesser als 0 sein.")
    d["kategorie"] = str(daten.get("kategorie") or ("umsatz" if d["art"] == "einnahme" else "")).strip()
    erlaubt = EINNAHME_KATEGORIEN if d["art"] == "einnahme" else {k: v for k, v in KATEGORIEN.items() if k != "anlage"}
    if d["kategorie"] not in erlaubt:
        raise ValueError("Bitte eine Kategorie waehlen (Anlagegueter nicht als Abo).")
    d["turnus"] = str(daten.get("turnus") or "monatlich").strip()
    if d["turnus"] not in TURNUS:
        raise ValueError("Unbekannter Turnus.")
    d["start"] = datum_pruefen(daten.get("start"), "Erste Faelligkeit", zukunft=True)
    d["ende"] = datum_pruefen(daten["ende"], "Ende", zukunft=True) if daten.get("ende") else ""
    if d["ende"] and d["ende"] < d["start"]:
        raise ValueError("Das Ende liegt vor der ersten Faelligkeit.")
    frist = daten.get("kuendigungsfrist_tage")
    try:
        d["kuendigungsfrist_tage"] = int(frist) if frist not in (None, "") else None
    except (TypeError, ValueError):
        raise ValueError("Kuendigungsfrist in Tagen angeben.") from None
    if d["kuendigungsfrist_tage"] is not None and not 0 <= d["kuendigungsfrist_tage"] <= 730:
        raise ValueError("Kuendigungsfrist zwischen 0 und 730 Tagen.")
    for k, n in (("zahlungsweg", 120), ("vertragsnummer", 80), ("notiz", 300)):
        d[k] = str(daten.get(k) or "").strip()[:n]
    d["beleg_per_mail"] = daten.get("beleg_per_mail") in (True, "true", "1", "ja", "on", 1)
    d["auto_buchen"] = daten.get("auto_buchen") in (True, "true", "1", "ja", "on", 1)
    firma = str(daten.get("firma") or "").strip().upper()
    if kunden is not None:
        f = kunden.firma(firma) if firma else None
        if not f:
            raise ValueError("Bitte die Firma aus den Stammdaten waehlen (L-/P-Nummer).")
        firma = f["nummer"]
    d["firma"] = firma
    rv = str(daten.get("rechnung_von") or "").strip().upper()
    if rv and kunden is not None:
        f = kunden.firma(rv)
        if not f:
            raise ValueError("„Rechnung von“: bitte die Firma aus den Stammdaten waehlen (z. B. Apple).")
        rv = f["nummer"]
    d["rechnung_von"] = "" if rv == firma else rv
    return d


class AboStore:
    def __init__(self, bh: Buchhaltung):
        self.bh = bh

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "abo_angelegt":
                out[d["nummer"]] = {k: d.get(k) for k in FELDER} | {"nummer": d["nummer"], "status": "aktiv",
                                                                    "angelegt": e["ts"], "erledigt": {}, "verlauf": []}
                out[d["nummer"]]["verlauf"].append({"ts": e["ts"], "von": e.get("von", ""), "typ": "angelegt"})
            elif d.get("nummer") not in out:
                continue
            elif t == "abo_geaendert":
                out[d["nummer"]].update(d.get("felder") or {})
                out[d["nummer"]]["verlauf"].append({"ts": e["ts"], "von": e.get("von", ""), "typ": "geaendert",
                                                    "felder": sorted(d.get("felder") or {})})
            elif t == "abo_beendet":
                a = out[d["nummer"]]
                a["status"], a["ende"] = "beendet", d.get("ende") or a.get("ende")
                a["verlauf"].append({"ts": e["ts"], "von": e.get("von", ""), "typ": "beendet", "grund": d.get("grund", "")})
            elif t == "abo_faelligkeit":
                out[d["nummer"]]["erledigt"][d["faellig"]] = {k: d.get(k) for k in ("wie", "beleg", "grund")} | {"ts": e["ts"]}
        return out

    def liste(self, heute: date | None = None) -> list[dict]:
        heute = heute or jetzt().date()
        e = self.bh.eintraege()
        out = []
        for a in sorted(self._falte(e).values(), key=lambda x: x["nummer"]):
            a = dict(a) | {"monatlich_cent": monatlich_cent(a), "naechste": naechste(a, heute) if a["status"] == "aktiv" else "",
                           "turnus_text": TURNUS[a["turnus"]][0], "offen": [o["faellig"] for o in offene(e, heute, nur=a["nummer"])]}
            out.append(a)
        return out

    def get(self, nummer: str) -> dict | None:
        return self._falte(self.bh.eintraege()).get((nummer or "").strip().upper())

    def anlegen(self, daten: dict, kunden, *, von: str = "") -> dict:
        d = pruefen(daten, kunden)
        ev = self.bh.mit_nummer("ABO", "abo_angelegt", d, bezug=d["bezeichnung"], von=von)
        return {"nummer": ev["daten"]["nummer"]}

    def aendern(self, nummer: str, daten: dict, kunden, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        alt = self.get(nummer)
        if not alt:
            raise KeyError(nummer)
        if alt["status"] != "aktiv":
            raise ValueError(f"{nummer} ist beendet.")
        voll = {k: alt.get(k) for k in FELDER} | {"betrag": alt["betrag_cent"] / 100} | dict(daten)
        if "betrag" in daten:
            voll.pop("betrag_cent", None)
        neu = pruefen(voll, kunden)
        diff = {k: v for k, v in neu.items() if alt.get(k) != v}
        if diff:
            self.bh.erfassen("abo_geaendert", {"nummer": nummer, "felder": diff}, von=von)
        return {"geaendert": diff}

    def beenden(self, nummer: str, ende: str, grund: str, *, von: str = "") -> dict:
        nummer = (nummer or "").strip().upper()
        tag = datum_pruefen(ende, "Ende", zukunft=True)

        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if a["status"] == "beendet":
                raise ValueError(f"{nummer} ist schon beendet.")
        self.bh.erfassen_geprueft("abo_beendet", {"nummer": nummer, "ende": tag, "grund": str(grund or "").strip()[:300]},
                                  von=von, pruefe=pruefe)
        return {"status": "beendet", "ende": tag}

    def _erledigen(self, nummer: str, faellig: str, daten: dict, *, von: str) -> None:
        def pruefe(eintraege):
            a = self._falte(eintraege).get(nummer)
            if not a:
                raise KeyError(nummer)
            if faellig not in faelligkeiten(a, date.fromisoformat(faellig)):
                raise ValueError(f"{faellig} ist keine Faelligkeit von {nummer}.")
            if faellig in a["erledigt"]:
                raise ValueError(f"{nummer} zum {faellig} ist schon erledigt.")
        self.bh.erfassen_geprueft("abo_faelligkeit", {"nummer": nummer, "faellig": faellig} | daten, von=von, pruefe=pruefe)

    def buchen(self, nummer: str, faellig: str, kunden, *, datum: str = "", betrag=None, von: str = "") -> dict:
        """Faelligkeit als Eigenbeleg buchen (Datum = Faelligkeit, sonst angegeben; nie in der Zukunft)."""
        nummer = (nummer or "").strip().upper()
        a = self.get(nummer)
        if not a:
            raise KeyError(nummer)
        faellig = datum_pruefen(faellig, "Faelligkeit", zukunft=True)
        if faellig > jetzt().date().isoformat():
            raise ValueError("Diese Faelligkeit liegt noch in der Zukunft.")
        if faellig not in faelligkeiten(a, date.fromisoformat(faellig)):
            raise ValueError(f"{faellig} ist keine Faelligkeit von {nummer}.")
        if faellig in a["erledigt"]:
            raise ValueError(f"{nummer} zum {faellig} ist schon erledigt.")
        f = kunden.firma(a["firma"]) if kunden is not None else None
        eb = EigenbelegStore(self.bh).anlegen({
            "art": a["art"], "datum": datum or faellig, "betrag": betrag if betrag not in (None, "") else a["betrag_cent"] / 100,
            "kategorie": a["kategorie"], "text": f"{a['bezeichnung']} ({TURNUS[a['turnus']][0]}, fällig {faellig})",
            "gegenpartei": (f or {}).get("name", ""), "firma": a["firma"],
            "referenz": " ".join(x for x in (nummer, a.get("vertragsnummer") or "") if x)}, von=von)
        self._erledigen(nummer, faellig, {"wie": "gebucht", "beleg": eb["nummer"]}, von=von)
        return {"nummer": nummer, "faellig": faellig, "eigenbeleg": eb["nummer"]}

    def ueberspringen(self, nummer: str, faellig: str, grund: str, *, von: str = "") -> dict:
        grund = str(grund or "").strip()[:300]
        if not grund:
            raise ValueError("Bitte einen Grund angeben (z. B. Gratismonat, schon anders gebucht).")
        nummer = (nummer or "").strip().upper()
        self._erledigen(nummer, datum_pruefen(faellig, "Faelligkeit", zukunft=True), {"wie": "uebersprungen", "grund": grund},
                        von=von)
        return {"nummer": nummer, "faellig": faellig, "status": "uebersprungen"}


def _passender_beleg(e: list[dict], a: dict, faellig: str, vergeben: set) -> str:
    """Gebuchter Eingangsbeleg/Eigenbeleg derselben Firma im Fenster um die Faelligkeit mit aehnlichem Betrag (±25 %).
    Mehrere Kandidaten (z. B. Abo 21,42 € und Guthaben-Aufladung 20,49 € in derselben Woche): der naechstliegende Betrag,
    dann das naechstliegende Datum gewinnt (VORSCHLAGSPAUSE_ANBIETER P3, CEO: Abo und Credits nie mischen)."""
    tage = ABGLEICH_TAGE.get(a["turnus"], 10)
    f0 = date.fromisoformat(faellig)
    von, bis = (f0 - timedelta(days=tage)).isoformat(), (f0 + timedelta(days=tage)).isoformat()
    aehnlich = lambda c: abs(abs(int(c or 0)) - a["betrag_cent"]) <= 0.25 * a["betrag_cent"]
    kandidaten = []
    steller = a.get("rechnung_von") or a["firma"]        # Rechnung kommt ggf. von einem anderen (App Store)
    for x in EingangStore._falte(e).values():
        fe = x.get("felder") or {}
        d = str(fe.get("rechnungsdatum", ""))
        if (x["status"] == "gebucht" and fe.get("lieferant_firma") == steller and von <= d <= bis
                and aehnlich(fe.get("betrag_cent")) and x["nummer"] not in vergeben):
            kandidaten.append((abs(abs(int(fe.get("betrag_cent") or 0)) - a["betrag_cent"]), abs((date.fromisoformat(d) - f0).days), x["nummer"]))
    for x in EigenbelegStore._falte(e).values():
        if (x["status"] == "gebucht" and x.get("firma") in (a["firma"], steller) and von <= x["datum"] <= bis and aehnlich(x["betrag_cent"])
                and x["nummer"] not in vergeben):
            kandidaten.append((abs(abs(int(x["betrag_cent"] or 0)) - a["betrag_cent"]), abs((date.fromisoformat(x["datum"]) - f0).days), x["nummer"]))
    return min(kandidaten)[2] if kandidaten else ""


def offene(e: list[dict], heute: date, *, nur: str = "") -> list[dict]:
    """Faellige, noch nicht erledigte Faelligkeiten aktiver und beendeter Abos (bis heute)."""
    abos = AboStore._falte(e)
    vergeben = {v["beleg"] for a in abos.values() for v in a["erledigt"].values() if v.get("beleg")}
    out = []
    for a in abos.values():
        if nur and a["nummer"] != nur:
            continue
        for d in faelligkeiten(a, heute):
            if d in a["erledigt"]:
                continue
            beleg = _passender_beleg(e, a, d, vergeben)
            out.append({"abo": a["nummer"], "bezeichnung": a["bezeichnung"], "faellig": d, "betrag_cent": a["betrag_cent"],
                        "beleg": beleg, "auto": a["auto_buchen"] and not a["beleg_per_mail"],
                        "beleg_per_mail": a["beleg_per_mail"], "firma": a["firma"]})
            if beleg:
                vergeben.add(beleg)
    return sorted(out, key=lambda o: (o["faellig"], o["abo"]))


def lauf(bh: Buchhaltung, kunden, *, heute: date | None = None, notify=None) -> dict:
    """Taeglicher Abo-Lauf (CFO 05:00): passende Belege als Erfuellung vermerken, angehakte Abos automatisch buchen.
    Alles andere bleibt als To-do fuer den CEO. Rueckgabe: {erfuellt, gebucht, fehler}."""
    heute = heute or jetzt().date()
    st, erg = AboStore(bh), {"erfuellt": [], "gebucht": [], "fehler": []}
    for o in offene(bh.eintraege(), heute):
        try:
            if o["beleg"]:
                st._erledigen(o["abo"], o["faellig"], {"wie": "beleg", "beleg": o["beleg"]}, von="LUNA-Abo")
                erg["erfuellt"].append(f"{o['abo']} {o['faellig']} -> {o['beleg']}")
            elif o["auto"]:
                r = st.buchen(o["abo"], o["faellig"], kunden, von="LUNA-Abo (automatisch)")
                erg["gebucht"].append(f"{o['bezeichnung']} {o['faellig']} -> {r['eigenbeleg']}")
        except (KeyError, ValueError) as exc:
            erg["fehler"].append(f"{o['abo']} {o['faellig']}: {exc}")
    if notify and erg["gebucht"]:
        try:
            notify("🔁 Abos automatisch gebucht: " + "; ".join(erg["gebucht"]), abteilung="CFO", kategorie="finanzen",
                   quelle="abos", detail="LUNA-OS -> Finanzen -> Abos")
        except Exception:
            pass
    return erg


def kuendigung_faellig(a: dict, heute: date, vorlauf: int = 14) -> str:
    """Datum, bis zu dem gekuendigt werden muss, wenn es in den naechsten `vorlauf` Tagen liegt (sonst '')."""
    if a.get("status") != "aktiv" or not a.get("ende") or a.get("kuendigungsfrist_tage") is None:
        return ""
    stichtag = date.fromisoformat(a["ende"]) - timedelta(days=int(a["kuendigungsfrist_tage"]))
    return stichtag.isoformat() if heute <= stichtag <= heute + timedelta(days=vorlauf) else ""
