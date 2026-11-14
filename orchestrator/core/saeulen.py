"""Erloes-Saeulen fuer Einnahmen, Ausgaben und Stunden (MONETARISIERUNG_ROADMAP.md, Etappe M1; CEO 2026-11-14:
„immer nach den jeweiligen Saeulen sortieren -- Kooperationen sind eine andere Saeule als Facebook-Monetarisierung").

- **Zuordnung je Beleg** (Rechnung `RE-`/`RG-`, Eingangsbeleg/Gutschrift `ER-`, Eigenbeleg `EB-`, Auftrag `AB-`):
  Ereignis `saeule_zugeordnet` {bezug, saeule} in der Hash-Kette, die letzte Angabe gilt, `saeule=""` nimmt sie zurueck.
  Additiv: ohne Ereignis = „nicht zugeordnet". Die EUeR, der Kleinunternehmer-Waechter und alle bisherigen Zahlen
  bleiben unveraendert -- die Saeule ist nur eine zusaetzliche Sicht.
- **Vorschlag per Regel** (Gegenpartei, Text, Positionen) -- nie automatisch gebucht; ein Mensch bestaetigt. Ist die
  Regel nicht eindeutig, gibt es keinen Vorschlag (lieber „nicht zugeordnet" als falsch).
- **Vererbung:** Rechnung ohne eigene Zuordnung -> Saeule ihres Auftrags; Auftrag ohne eigene -> Saeule seiner
  Rechnung. Projektzeiten erben die Saeule ihres Auftrags.
- **Stunden ohne Auftrag** (eigene Kanaele, App, Merch): Schaetzung je Monat, Person und Saeule, Ereignis
  `saeule_stunden` {jahr, monat, person, saeule, minuten}; die letzte Angabe je Schluessel gilt. Zaehlt zusaetzlich zu
  den Zeiten aus der Zeiterfassung (dort Erfasstes also nicht noch einmal schaetzen).
- **Deckungsbeitrag** je Saeule = Einnahmen minus der Saeule zugeordnete Ausgaben (inkl. Abschreibung); Ausgaben ohne
  Saeule sind Gemeinkosten. Euro je Stunde = Deckungsbeitrag / Stunden.

Keine Weitergabe an Sprachmodelle noetig: alles deterministisch im Code.
"""
from __future__ import annotations

import re

from .beauftragung import AuftragBuch
from .finanzen import MONATE, Finanzen, kennzahlen
from .zeiterfassung import falte_zeiten

SAEULEN = {                     # Code -> (Name, Gruppe). Gruppen-Codes (S2, S3) nur fuer gemeinsame Kosten.
    "S1": ("Kooperationen", "S1"),
    "S2": ("Plattform-Monetarisierung (gemeinsam)", "S2"),
    "S2a": ("Facebook", "S2"),
    "S2b": ("TikTok", "S2"),
    "S2c": ("YouTube", "S2"),
    "S2d": ("Instagram", "S2"),
    "S3": ("Fan-App (gemeinsam)", "S3"),
    "S3a": ("Anker-Crew-Abos", "S3"),
    "S3b": ("Kneipen-Listung", "S3"),
    "S4": ("Affiliates", "S4"),
    "S5": ("Merch", "S5"),
    "S6": ("Auftragsproduktion", "S6"),
}
GRUPPEN = {"S1": "Kooperationen", "S2": "Plattform-Monetarisierung", "S3": "Fan-App", "S4": "Affiliates", "S5": "Merch",
           "S6": "Auftragsproduktion"}
PERSONEN = {"nils": "Nils", "celine": "Celine"}
OHNE = "ohne"                   # Schluessel fuer „nicht zugeordnet" in Auswertungen

# Regeln: (Muster auf Gegenpartei + Text, Saeule, Grund). Reihenfolge egal -- treffen zwei verschiedene Saeulen,
# gibt es keinen Vorschlag.
_PLATTFORM = [
    (r"meta platforms|facebook", "S2a", "Auszahlung von Meta (Facebook)"),
    (r"tiktok|bytedance", "S2b", "Auszahlung von TikTok"),
    (r"youtube|adsense", "S2c", "Auszahlung von YouTube"),
    (r"instagram", "S2d", "Auszahlung von Instagram"),
    (r"app store|apple distribution|google play|google commerce", "S3a", "Store-Auszahlung (App)"),
]
_EINNAHME = [
    (r"affiliate|provision|partnerprogramm", "S4", "Provision/Affiliate"),
    (r"merch|shirt|kalender|tasse|hoodie|printful|spreadshirt", "S5", "Merch-Verkauf"),
    (r"kneipe|listung", "S3b", "Kneipen-Listung"),
    (r"collab|kooperation|gewinnspiel|sponsor|werbepartner|kampagne|story|posting|product placement", "S1",
     "Kooperation/Sponsoring"),
    (r"imagefilm|auftragsproduktion|produktion|schnitt|\bdreh|recruiting|hochzeit|eventvideo", "S6",
     "Video fuer den Kunden"),
]
_AUSGABE = [
    (r"printful|derbe|dias[- ]products|spreadshirt|merch", "S5", "Merch-Einkauf/Produktion"),
    (r"app store connect|apple developer|google play console", "S3", "Kosten der Fan-App"),  # Supabase: auch LUNA
]


def _treffer(regeln, text: str) -> set[tuple[str, str]]:
    return {(s, g) for muster, s, g in regeln if re.search(muster, text, re.I)}


def vorschlag(art: str, gegenpartei: str, text: str, kategorie: str = "", quelle: str = "") -> tuple[str, str]:
    """-> (Saeule, Grund) oder ("", Grund) wenn keine/zweideutige Regel greift. Plattform-Regeln gelten fuer die
    Gegenpartei und -- ausser bei eigenen Rechnungen (dort heisst „Facebook" meist: Reel fuer einen Kunden) -- den Text."""
    t = f"{gegenpartei} {text}"
    if art == "einnahme":
        if kategorie == "barter":
            return "S1", "Sachleistung aus einer Kooperation"
        p = _treffer(_PLATTFORM, gegenpartei if quelle in ("rechnung", "ware") else t)
        if len({s for s, _ in p}) == 1:
            return next(iter(p))
        t_ = _treffer(_EINNAHME, t)
    else:
        t_ = _treffer(_AUSGABE, t)
    saeulen = {s for s, _ in t_}
    if len(saeulen) == 1:
        return next(iter(t_))
    if len(saeulen) > 1:
        return "", "mehrdeutig: " + " oder ".join(sorted(SAEULEN[s][0] for s in saeulen))
    return "", ""


def zuordnungen(eintraege: list[dict]) -> dict[str, dict]:
    """bezug -> {saeule, ts, von} (letzte Angabe; zurueckgenommene fehlen)."""
    out: dict[str, dict] = {}
    for e in eintraege:
        if e["typ"] == "saeule_zugeordnet":
            d = e["daten"]
            if d.get("saeule"):
                out[d["bezug"]] = {"saeule": d["saeule"], "ts": e["ts"], "von": e.get("von", "")}
            else:
                out.pop(d["bezug"], None)
    return out


def stunden_schaetzung(eintraege: list[dict]) -> dict[tuple, int]:
    """(jahr, monat, person, saeule) -> Minuten (letzte Angabe gilt, 0 = geloescht)."""
    out: dict[tuple, int] = {}
    for e in eintraege:
        if e["typ"] == "saeule_stunden":
            d = e["daten"]
            k = (int(d["jahr"]), int(d["monat"]), d["person"], d["saeule"])
            if int(d.get("minuten") or 0):
                out[k] = int(d["minuten"])
            else:
                out.pop(k, None)
    return out


class Saeulen:
    def __init__(self, bh, kunden):
        self.bh, self.kunden = bh, kunden
        self.f = Finanzen(bh, kunden)

    # -- Lesen ----------------------------------------------------------------------------------------------------

    def _wirksam(self, st: dict, auftraege: dict) -> dict[str, dict]:
        """bezug -> {saeule, quelle: mensch|auftrag|rechnung} inkl. Vererbung Rechnung <-> Auftrag."""
        z = zuordnungen(st["e"])
        out = {b: {"saeule": v["saeule"], "quelle": "mensch"} for b, v in z.items()}
        for r in st["rechnungen"].values():
            a = r.get("auftrag")
            if not a:
                continue
            if r["nummer"] not in out and a in z:
                out[r["nummer"]] = {"saeule": z[a]["saeule"], "quelle": "auftrag"}
            if a not in out and r["nummer"] in z:
                out[a] = {"saeule": z[r["nummer"]]["saeule"], "quelle": "rechnung"}
        return out

    def _texte(self, st: dict) -> dict[str, str]:
        """Zusatztext fuer die Regeln: Titel + Positionen einer Rechnung."""
        out = {}
        for r in st["rechnungen"].values():
            pos = " ".join(str(p.get("beschreibung", "")) for p in r.get("positionen") or [])
            out[r["nummer"]] = f"{r.get('titel', '')} {pos}"
        return out

    def auswertung(self, jahr: int) -> dict:
        st = self.f._stand()
        auftraege = AuftragBuch._falte(st["e"])
        wirk = self._wirksam(st, auftraege)
        texte = self._texte(st)
        zeilen = self.f.posten(jahr, st=st)
        leer = lambda: {"einnahmen_cent": 0, "ausgaben_cent": 0, "minuten_erfasst": 0, "minuten_geschaetzt": 0,
                        "monate": [0] * 12, "belege": 0}
        je: dict[str, dict] = {s: leer() for s in SAEULEN} | {OHNE: leer()}
        belege: dict[str, dict] = {}
        for z in zeilen:
            if z["storniert"]:
                continue
            s = (wirk.get(z["bezug"]) or {}).get("saeule") or OHNE
            x = je[s]
            if z["art"] == "einnahme":
                x["einnahmen_cent"] += z["betrag_cent"]
                x["monate"][z["monat"] - 1] += z["betrag_cent"]
            else:
                x["ausgaben_cent"] += z["abziehbar_cent"]
            if z["quelle"] == "afa":                      # Abschreibung erbt die Saeule, ist aber kein eigener Beleg
                continue
            b = belege.setdefault(z["bezug"], {"bezug": z["bezug"], "art": z["art"], "quelle": z["quelle"],
                                               "datum": z["datum"], "gegenpartei": z["gegenpartei"], "text": z["text"],
                                               "kategorie": z["kategorie"], "betrag_cent": 0})
            b["betrag_cent"] += z["betrag_cent"]
        for b in belege.values():
            w = wirk.get(b["bezug"]) or {}
            b["saeule"], b["saeule_quelle"] = w.get("saeule", ""), w.get("quelle", "")
            b["vorschlag"], b["grund"] = vorschlag(b["art"], b["gegenpartei"], f"{b['text']} {texte.get(b['bezug'], '')}",
                                                   b["kategorie"], b["quelle"])
            je[b["saeule"] or OHNE]["belege"] += 1
        # Stunden: Zeiterfassung (ueber den Auftrag) + Schaetzungen ohne Auftrag
        for x in falte_zeiten(st["e"]).values():
            if x["storniert"] or not x.get("minuten") or str(x.get("start", ""))[:4] != str(jahr):
                continue
            s = (wirk.get(x.get("auftrag") or "") or {}).get("saeule") or OHNE
            je[s]["minuten_erfasst"] += int(x["minuten"])
        sch = stunden_schaetzung(st["e"])
        schaetzungen = []
        for (j, m, p, s), minuten in sorted(sch.items()):
            if j != jahr:
                continue
            je[s]["minuten_geschaetzt"] += minuten
            schaetzungen.append({"monat": m, "person": p, "person_name": PERSONEN.get(p, p), "saeule": s,
                                 "saeule_name": SAEULEN.get(s, (s,))[0], "minuten": minuten})
        def zeile(code: str, name: str, gruppe: str, x: dict) -> dict:
            minuten = x["minuten_erfasst"] + x["minuten_geschaetzt"]
            db = x["einnahmen_cent"] - x["ausgaben_cent"]
            return {"code": code, "name": name, "gruppe": gruppe, **{k: x[k] for k in (
                "einnahmen_cent", "ausgaben_cent", "minuten_erfasst", "minuten_geschaetzt", "monate", "belege")},
                    "db_cent": db, "minuten": minuten, "euro_je_stunde_cent": round(db * 60 / minuten) if minuten else None}
        saeulen = [zeile(c, n, g, je[c]) for c, (n, g) in SAEULEN.items()]
        gruppen = []
        for g, name in GRUPPEN.items():
            teile = [s for s in saeulen if s["gruppe"] == g]
            summe = {k: sum(s[k] for s in teile) for k in ("einnahmen_cent", "ausgaben_cent", "minuten_erfasst",
                                                          "minuten_geschaetzt", "belege")}
            summe["monate"] = [sum(s["monate"][i] for s in teile) for i in range(12)]
            gruppen.append(zeile(g, name, g, summe) | {"teile": teile if len(teile) > 1 else []})
        ohne = zeile(OHNE, "nicht zugeordnet", OHNE, je[OHNE])
        k = kennzahlen(zeilen)
        summe_saeulen = sum(g["einnahmen_cent"] for g in gruppen) + ohne["einnahmen_cent"]
        liste = sorted(belege.values(), key=lambda b: b["datum"], reverse=True)
        return {"jahr": jahr, "monate": list(MONATE), "saeulen": [{"code": c, "name": n, "gruppe": g}
                                                                  for c, (n, g) in SAEULEN.items()],
                "personen": PERSONEN, "gruppen": gruppen, "ohne": ohne,
                "summe": {"einnahmen_cent": k["einnahmen_cent"], "ausgaben_cent": k["ausgaben_cent"],
                          "gewinn_cent": k["gewinn_cent"],
                          "minuten": sum(g["minuten"] for g in gruppen) + ohne["minuten"]},
                "stimmig": summe_saeulen == k["einnahmen_cent"],
                "offen": sum(1 for b in liste if not b["saeule"] and b["art"] == "einnahme"),
                "belege": liste, "schaetzungen": schaetzungen,
                "hinweis": "Zusätzliche Sicht: EÜR und Kleinunternehmer-Grenze bleiben unverändert. Ob Auszahlungen "
                           "aus dem Ausland (Meta, Stores) zur Grenze zählen, klärt der Steuerberater (BF-95)."}

    # -- Schreiben ------------------------------------------------------------------------------------------------

    def _bekannt(self) -> set[str]:
        st = self.f._stand()
        return (set(st["rechnungen"]) | set(st["belege"]) | set(st["eigen"])
                | set(AuftragBuch._falte(st["e"])))

    def zuordnen(self, zuordnungen_: list[dict], *, von: str = "") -> dict:
        """[{bezug, saeule}] -- saeule "" nimmt die Zuordnung zurueck. Alles wird erst geprueft, dann geschrieben."""
        if not zuordnungen_:
            raise ValueError("Keine Zuordnung angegeben.")
        bekannt, aktuell = self._bekannt(), zuordnungen(self.bh.eintraege())
        sauber = []
        for z in zuordnungen_:
            b, s = str(z.get("bezug") or "").strip(), str(z.get("saeule") or "").strip()
            if b not in bekannt:
                raise ValueError(f"Beleg {b or '?'} gibt es nicht.")
            if s and s not in SAEULEN:
                raise ValueError(f"Unbekannte Säule: {s}")
            if (aktuell.get(b) or {}).get("saeule", "") != s:
                sauber.append((b, s))
        for b, s in sauber:
            self.bh.erfassen("saeule_zugeordnet", {"bezug": b, "saeule": s}, von=von)
        return {"geaendert": len(sauber)}

    def stunden(self, jahr, monat, person: str, saeule: str, stunden, *, von: str = "") -> dict:
        try:
            j, m = int(jahr), int(monat)
            h = float(str(stunden).replace(",", ".")) if str(stunden).strip() else 0.0
        except (TypeError, ValueError):
            raise ValueError("Jahr, Monat und Stunden als Zahl angeben.") from None
        if not (2020 <= j <= 2100 and 1 <= m <= 12):
            raise ValueError("Monat ungültig.")
        if person not in PERSONEN:
            raise ValueError("Unbekannte Person.")
        if saeule not in SAEULEN:
            raise ValueError(f"Unbekannte Säule: {saeule}")
        if not 0 <= h <= 400:
            raise ValueError("Stunden zwischen 0 und 400 je Monat.")
        minuten = round(h * 60)
        self.bh.erfassen("saeule_stunden", {"jahr": j, "monat": m, "person": person, "saeule": saeule,
                                            "minuten": minuten}, von=von)
        return {"minuten": minuten}
