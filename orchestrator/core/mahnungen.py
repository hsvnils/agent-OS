"""KUNDEN_FINANZEN Etappe 10: Mahnwesen (CEO 2026-09-28).

Ablauf: Rechnung ueberfaellig -> **1. Mahnung** stoesst der CEO in LUNA-OS an (Frist waehlbar) und sendet sie ->
laeuft die Frist ohne Zahlung ab, bereitet LUNA die **2.** bzw. **3. (letzte) Mahnung** vor und fragt per Telegram
(✅ Senden / ❌ Nicht senden) -- verschickt wird nur nach dem Tipp des CEO (Geld/Recht nie autonom, AGENTS.md 4).

Forderung je Mahnung (CEO-Entscheidung 2026-09-28):
- **Verzugszinsen ab Faelligkeit** (Tag nach dem Faelligkeitsdatum) bis zum Mahnungsdatum, taggenau (365/366) auf den jeweils
  offenen Betrag (Teilzahlungen mindern ihn ab dem Zahlungstag); Satz = Basiszinssatz (§ 247 BGB, halbjaehrlich)
  + **9 Prozentpunkte** bei Unternehmern (§ 288 Abs. 2 BGB) bzw. **5** bei Verbrauchern (§ 288 Abs. 1 BGB).
- **Unternehmer:** Verzugspauschale **40 EUR** einmal je Rechnung (§ 288 Abs. 5 BGB).
  **Verbraucher:** tatsaechliche Mahnkosten pauschal **2,50 EUR je Mahnung**.
- Zinsen und Pauschalen sind Schadensersatz -- keine Umsatzsteuer, zaehlen nicht zum § 19-Umsatz.

Nummern `MA-JJJJ-NNNN`, PDF als Geschaeftsbrief (6 Jahre), alles unveraenderbar in der Hash-Kette.
"""
from __future__ import annotations

from datetime import date, timedelta

from .beleg_pdf import beleg_pdf, datum_de, eur
from .buchhaltung import Buchhaltung, jetzt
from .rechnungen import RechnungStore, _empfaenger
from .angebote import anrede_moin

# Basiszinssatz nach § 247 BGB in Prozent, gueltig ab -- Quelle: Deutsche Bundesbank, Seite „Basiszinssatz“
# (bundesbank.de/.../basiszinssatz-607820, abgerufen 2026-09-28; Pressemitteilung zum 01.07.2026: 1,27 -> 1,52 %).
# Nur belegte Werte eintragen! Naechste Aenderung 01.01.2027 -> dann nachtragen (sonst rechnet LUNA nicht).
BASISZINS: list[tuple[str, float]] = [
    ("2023-01-01", 1.62), ("2023-07-01", 3.12), ("2024-01-01", 3.62), ("2024-07-01", 3.37),
    ("2025-01-01", 2.27), ("2025-07-01", 1.27), ("2026-01-01", 1.27), ("2026-07-01", 1.52),
]
BASISZINS_BEKANNT_BIS = "2026-12-31"       # danach ist der Satz noch nicht veroeffentlicht
AUFSCHLAG_UNTERNEHMER = 9.0
AUFSCHLAG_VERBRAUCHER = 5.0
PAUSCHALE_UNTERNEHMER_CENT = 4000
KOSTEN_VERBRAUCHER_CENT = 250
def tage_jahr(tag: date) -> int:
    """Taggenau (act/act): 365 Tage, im Schaltjahr 366 -- gaengige Praxis bei Verzugszinsen."""
    return 366 if tag.year % 4 == 0 and (tag.year % 100 != 0 or tag.year % 400 == 0) else 365


STUFEN = {1: "1. Mahnung", 2: "2. Mahnung", 3: "Letzte Mahnung"}
FRIST_TAGE = 7


def basiszins(tag: date) -> float:
    gueltig = [z for ab, z in BASISZINS if ab <= tag.isoformat()]
    if not gueltig or tag.isoformat() > BASISZINS_BEKANNT_BIS:
        raise ValueError(f"Basiszinssatz fuer {datum_de(tag.isoformat())} ist nicht hinterlegt -- bitte in "
                         "core/mahnungen.py (BASISZINS) aus der Veroeffentlichung der Bundesbank nachtragen.")
    return gueltig[-1]


def verzugszinsen(summe_cent: int, zahlungen: list[tuple[str, int]], faellig: str, bis: str, aufschlag: float) -> dict:
    """Taggenaue Verzugszinsen vom Tag nach `faellig` bis einschliesslich `bis`. `zahlungen`: [(datum, cent)] mindern
    den offenen Betrag ab ihrem Zahlungstag. -> {zinsen_cent, tage, abschnitte: [{von, bis, satz, offen_cent, cent}]}"""
    start = date.fromisoformat(faellig) + timedelta(days=1)
    ende = date.fromisoformat(bis)
    abschnitte: list[dict] = []
    gesamt = 0.0
    tag = start
    while tag <= ende:
        offen = summe_cent - sum(c for d, c in zahlungen if d <= tag.isoformat())
        satz = round(basiszins(tag) + aufschlag, 2)
        betrag = max(offen, 0) * satz / 100 / tage_jahr(tag)
        gesamt += betrag
        if abschnitte and abschnitte[-1]["satz"] == satz and abschnitte[-1]["offen_cent"] == offen:
            abschnitte[-1]["bis"] = tag.isoformat()
            abschnitte[-1]["tage"] += 1
            abschnitte[-1]["roh"] += betrag
        else:
            abschnitte.append({"von": tag.isoformat(), "bis": tag.isoformat(), "tage": 1, "satz": satz,
                               "offen_cent": offen, "roh": betrag})
        tag += timedelta(days=1)
    for a in abschnitte:
        a["cent"] = round(a.pop("roh"))
    return {"zinsen_cent": round(gesamt), "tage": max((ende - start).days + 1, 0), "abschnitte": abschnitte}


class MahnStore:
    def __init__(self, bh: Buchhaltung, kunden):
        self.bh, self.kunden = bh, kunden

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "mahnung_erstellt":
                out[d["nummer"]] = dict(d) | {"erstellt": e["ts"], "von": e.get("von", "")}
            elif t == "mahnung_versendet" and d.get("nummer") in out:
                out[d["nummer"]] |= {"versendet_am": e["ts"], "mail": d.get("mail")}
        return out

    @staticmethod
    def ausgesetzt(eintraege: list[dict]) -> set[tuple[str, int]]:
        return {(e["daten"]["rechnung"], int(e["daten"]["stufe"])) for e in eintraege if e["typ"] == "mahnung_ausgesetzt"}

    def fuer_rechnung(self, rechnung: str, eintraege: list[dict] | None = None) -> list[dict]:
        e = self.bh.eintraege() if eintraege is None else eintraege
        return sorted((m for m in self._falte(e).values() if m["rechnung"] == rechnung), key=lambda m: m["stufe"])

    def get(self, nummer: str) -> dict | None:
        return self._falte(self.bh.eintraege()).get((nummer or "").strip().upper())

    # -- Berechnen --------------------------------------------------------------------------------------------------

    def berechnen(self, rechnung: str, *, stichtag: str | None = None, frist_tage: int = FRIST_TAGE,
                  eintraege: list[dict] | None = None) -> dict:
        """Vorschau der naechsten Mahnung (ohne etwas zu schreiben). ValueError, wenn nicht mahnbar."""
        e = self.bh.eintraege() if eintraege is None else eintraege
        rechnung = (rechnung or "").strip().upper()
        r = RechnungStore._falte(e)[1].get(rechnung)
        if not r:
            raise KeyError(rechnung)
        heute = date.fromisoformat(stichtag) if stichtag else jetzt().date()
        if r.get("art") == "storno" or r["status"] != "offen":
            raise ValueError(f"{rechnung} ist {r['status']} -- keine Mahnung moeglich.")
        if not r.get("faellig_am") or r["faellig_am"] >= heute.isoformat():
            raise ValueError(f"{rechnung} ist noch nicht ueberfaellig (faellig am {datum_de(r.get('faellig_am', ''))}).")
        bisher = self.fuer_rechnung(rechnung, e)
        if bisher and not bisher[-1].get("versendet_am"):
            raise ValueError(f"{bisher[-1]['nummer']} ist noch nicht versendet -- erst senden, dann die naechste Stufe.")
        stufe = len(bisher) + 1
        if stufe > 3:
            raise ValueError("Die letzte Mahnung ist verschickt -- weiter nur ueber Mahnbescheid/Inkasso (CEO).")
        if not 1 <= int(frist_tage) <= 60:
            raise ValueError("Frist zwischen 1 und 60 Tagen.")
        if r["geld_cent"] - r["bezahlt_cent"] <= 0:
            raise ValueError(f"Der Geldteil von {rechnung} ist bezahlt -- offen ist nur die Ware (nicht mahnbar, nachfordern).")
        f = self.kunden.firma(r["firma"]) or {}
        verbraucher = bool(f.get("verbraucher"))
        zahlungen = [(z["datum"], int(z.get("betrag_cent") or 0)) for z in r.get("zahlungen", []) if not z.get("storniert")]
        z = verzugszinsen(r["geld_cent"], zahlungen, r["faellig_am"], heute.isoformat(),
                          AUFSCHLAG_VERBRAUCHER if verbraucher else AUFSCHLAG_UNTERNEHMER)
        gebuehr = KOSTEN_VERBRAUCHER_CENT * stufe if verbraucher else PAUSCHALE_UNTERNEHMER_CENT
        offen = r["geld_cent"] - r["bezahlt_cent"]         # Barter: nur der Geldteil
        tageszins = round(offen * z["abschnitte"][-1]["satz"] / 100 / tage_jahr(heute)) if z["abschnitte"] else 0
        return {"rechnung": rechnung, "stufe": stufe, "titel": STUFEN[stufe], "datum": heute.isoformat(),
                "frist": (heute + timedelta(days=int(frist_tage))).isoformat(), "faellig_am": r["faellig_am"],
                "rechnungsdatum": r.get("rechnungsdatum", ""), "firma": r["firma"], "verbraucher": verbraucher,
                "offen_cent": offen, "zinsen_cent": z["zinsen_cent"], "zins_abschnitte": z["abschnitte"],
                "zins_tage": z["tage"], "tageszins_cent": tageszins, "gebuehr_cent": gebuehr,
                "gebuehr_text": (f"Mahnkosten ({stufe} × {eur(KOSTEN_VERBRAUCHER_CENT)})" if verbraucher
                                 else "Verzugspauschale nach § 288 Abs. 5 BGB"),
                "summe_cent": offen + z["zinsen_cent"] + gebuehr,
                "vorige": [{"nummer": m["nummer"], "datum": m["datum"]} for m in bisher]}

    # -- Schreiben --------------------------------------------------------------------------------------------------

    def erstellen(self, rechnung: str, firmendaten: dict, *, frist_tage: int = FRIST_TAGE, von: str = "") -> dict:
        """Mahnung festschreiben: Nummer MA-, PDF (Geschaeftsbrief) und Eintrag in einem Schritt."""
        heute = jetzt().date()

        def erzeuge(nummer, eintraege):
            m = self.berechnen(rechnung, stichtag=heute.isoformat(), frist_tage=frist_tage, eintraege=eintraege)
            return m, [(self.pdf(m | {"nummer": nummer}, firmendaten), f"Mahnung_{nummer}.pdf", "geschaeftsbrief")]

        ev = self.bh.festschreiben("MA", "mahnung_erstellt", erzeuge, jahr=heute.year, bezug=rechnung, von=von)
        return {k: ev["daten"][k] for k in ("nummer", "stufe", "summe_cent", "frist")}

    def alt_erfassen(self, rechnung: str, *, datum: str, frist: str = "", summe=None, pdf: bytes | None = None,
                     dateiname: str = "", von: str = "") -> dict:
        """Etappe 19: Mahnung, die vor LUNA verschickt wurde, als erreichte Stufe erfassen (Nummer `<Rechnung>-M<Stufe>`,
        kein `MA-`-Kreis). Danach macht das Mahnwesen bei der naechsten Stufe weiter."""
        from .beleg_pdf import cent
        rechnung = (rechnung or "").strip().upper()
        tag = date.fromisoformat(str(datum or "")[:10]).isoformat() if datum else ""
        if not tag or tag > jetzt().date().isoformat():
            raise ValueError("Mahnungsdatum fehlt oder liegt in der Zukunft.")
        fr = date.fromisoformat(str(frist)[:10]).isoformat() if frist else (date.fromisoformat(tag) + timedelta(days=FRIST_TAGE)).isoformat()
        if fr < tag:
            raise ValueError("Frist liegt vor dem Mahnungsdatum.")
        if pdf is not None and pdf and not pdf.startswith(b"%PDF"):
            raise ValueError("Die Mahnung bitte als PDF anhaengen.")
        with self.bh._gesperrt():
            e = self.bh._eintraege()
            r = RechnungStore._falte(e)[1].get(rechnung)
            if not r:
                raise KeyError(rechnung)
            if r.get("art") == "storno" or r["status"] != "offen":
                raise ValueError(f"{rechnung} ist {r['status']} -- keine Mahnung erfassbar.")
            bisher = self.fuer_rechnung(rechnung, e)
            stufe = len(bisher) + 1
            if stufe > 3:
                raise ValueError("Es sind schon drei Mahnungen erfasst.")
            if tag < r["rechnungsdatum"] or (bisher and tag < bisher[-1]["datum"]):
                raise ValueError("Mahnungsdatum liegt vor der Rechnung bzw. vor der vorigen Mahnung.")
            offen = r["geld_cent"] - r["bezahlt_cent"]
            betrag = cent(summe) if summe not in (None, "") else offen
            nummer = f"{rechnung}-M{stufe}"
            belege = []
            if pdf:
                b = self.bh._beleg_schreiben(pdf, dateiname or f"Mahnung_{nummer}.pdf", jahr=int(tag[:4]),
                                             art="geschaeftsbrief", bezug=rechnung, von=von)["daten"]
                belege = [{"pfad": b["pfad"], "sha256": b["sha256"]}]
            self.bh._anhaengen("mahnung_erstellt", {"nummer": nummer, "rechnung": rechnung, "stufe": stufe,
                                                    "titel": STUFEN[stufe], "datum": tag, "frist": fr, "firma": r["firma"],
                                                    "faellig_am": r["faellig_am"], "offen_cent": offen, "summe_cent": betrag,
                                                    "zinsen_cent": 0, "gebuehr_cent": max(betrag - offen, 0), "alt": True,
                                                    "belege": belege}, von=von)
            self.bh._anhaengen("mahnung_versendet", {"nummer": nummer, "mail": {"an": "vor LUNA verschickt"}}, von=von)
        return {"nummer": nummer, "stufe": stufe, "frist": fr}

    def versendet(self, nummer: str, mail: dict, *, von: str = "") -> None:
        nummer = (nummer or "").strip().upper()

        def pruefe(eintraege):
            m = self._falte(eintraege).get(nummer)
            if not m:
                raise KeyError(nummer)
            if m.get("versendet_am"):
                raise ValueError(f"{nummer} ist bereits versendet.")
        self.bh.erfassen_geprueft("mahnung_versendet", {"nummer": nummer, "mail": mail}, von=von, pruefe=pruefe)

    def aussetzen(self, rechnung: str, stufe: int, grund: str = "", *, von: str = "") -> None:
        """CEO hat die vorgeschlagene Folgemahnung abgelehnt -> LUNA fragt fuer diese Stufe nicht mehr."""
        self.bh.erfassen("mahnung_ausgesetzt", {"rechnung": rechnung, "stufe": int(stufe), "grund": str(grund)[:300]},
                         von=von)

    def faellige_folgemahnungen(self, heute: date | None = None) -> list[dict]:
        """Rechnungen, deren letzte Mahnung versendet ist, deren Frist abgelaufen ist und die noch offen sind."""
        heute = heute or jetzt().date()
        e = self.bh.eintraege()
        rechnungen = RechnungStore._falte(e)[1]
        aus = self.ausgesetzt(e)
        je: dict[str, list] = {}
        for m in self._falte(e).values():
            je.setdefault(m["rechnung"], []).append(m)
        out = []
        for re_nr, ms in je.items():
            ms.sort(key=lambda m: m["stufe"])
            letzte = ms[-1]
            r = rechnungen.get(re_nr)
            if (not r or r["status"] != "offen" or not letzte.get("versendet_am") or letzte["frist"] >= heute.isoformat()
                    or letzte["stufe"] >= 3 or (re_nr, letzte["stufe"] + 1) in aus):
                continue
            out.append({"rechnung": re_nr, "stufe": letzte["stufe"] + 1, "letzte": letzte["nummer"],
                        "frist_abgelaufen": letzte["frist"]})
        return out

    # -- Dokument ---------------------------------------------------------------------------------------------------

    def pdf(self, m: dict, firmendaten: dict) -> bytes:
        f = self.kunden.firma(m["firma"]) or {}
        aps = [a for a in f.get("ansprechpartner_liste", []) if a.get("aktiv")]
        ap = aps[0] if aps else None
        vorige = ", ".join(f"{datum_de(v['datum'])}" for v in m["vorige"])
        einl = {1: f"sicher ist es Ihrer Aufmerksamkeit entgangen: Unsere Rechnung {m['rechnung']} vom "
                   f"{datum_de(m['rechnungsdatum'])} war am {datum_de(m['faellig_am'])} fällig und ist noch nicht "
                   "(vollständig) bezahlt.",
                2: f"leider konnten wir trotz unserer Mahnung vom {vorige} noch keinen Zahlungseingang zu unserer Rechnung "
                   f"{m['rechnung']} feststellen.",
                3: f"trotz unserer Mahnungen vom {vorige} ist unsere Rechnung {m['rechnung']} weiterhin nicht bezahlt. "
                   "Dies ist unsere letzte Mahnung."}[m["stufe"]]
        pos = [{"beschreibung": f"Rechnung {m['rechnung']} vom {datum_de(m['rechnungsdatum'])}, fällig am "
                                f"{datum_de(m['faellig_am'])} – offener Betrag", "menge": "1", "einheit": "",
                "einzelpreis_cent": m["offen_cent"], "gesamt_cent": m["offen_cent"]}]
        for a in m["zins_abschnitte"]:
            if a["cent"]:
                pos.append({"beschreibung": f"Verzugszinsen {str(a['satz']).replace('.', ',')} % p. a. auf "
                                            f"{eur(a['offen_cent'])} vom {datum_de(a['von'])} bis {datum_de(a['bis'])} "
                                            f"({a['tage']} Tage)", "menge": "1", "einheit": "",
                            "einzelpreis_cent": a["cent"], "gesamt_cent": a["cent"]})
        if m["zinsen_cent"] != sum(a["cent"] for a in m["zins_abschnitte"]):          # Rundung ausgleichen
            diff = m["zinsen_cent"] - sum(a["cent"] for a in m["zins_abschnitte"])
            pos.append({"beschreibung": "Rundung Verzugszinsen", "menge": "1", "einheit": "", "einzelpreis_cent": diff,
                        "gesamt_cent": diff})
        pos.append({"beschreibung": m["gebuehr_text"], "menge": "1", "einheit": "", "einzelpreis_cent": m["gebuehr_cent"],
                    "gesamt_cent": m["gebuehr_cent"]})
        grundlage = ("5 Prozentpunkte (§ 288 Abs. 1 BGB)" if m["verbraucher"] else "9 Prozentpunkte (§ 288 Abs. 2 BGB)")
        hinweise = [f"Bitte überweisen Sie den Gesamtbetrag von {eur(m['summe_cent'])} bis spätestens "
                    f"{datum_de(m['frist'])} unter Angabe der Rechnungsnummer {m['rechnung']} auf das unten genannte Konto.",
                    f"Verzugszinsen: Basiszinssatz (§ 247 BGB) zuzüglich {grundlage}; ab dem "
                    f"{datum_de((date.fromisoformat(m['datum']) + timedelta(days=1)).isoformat())} fallen weitere "
                    f"{eur(m['tageszins_cent'])} pro Tag an.",
                    "Zinsen und Pauschale sind Schadensersatz und unterliegen nicht der Umsatzsteuer.",
                    "Sollten Sie die Zahlung inzwischen veranlasst haben, betrachten Sie dieses Schreiben bitte als "
                    "gegenstandslos."]
        if m["stufe"] == 3:
            hinweise.insert(1, "Nach Ablauf dieser Frist behalten wir uns vor, ohne weitere Ankündigung das gerichtliche "
                               "Mahnverfahren einzuleiten; die dadurch entstehenden Kosten gehen zu Ihren Lasten.")
        return beleg_pdf(art=STUFEN[m["stufe"]], nummer=m["nummer"], firma=firmendaten, empfaenger=_empfaenger(f, ap),
                         infos=[("Datum", datum_de(m["datum"])), ("Mahnung", m["nummer"]), ("Rechnung", m["rechnung"]),
                                ("Kundennummer", m["firma"]), ("Zahlbar bis", datum_de(m["frist"]))],
                         einleitung=anrede_moin(ap, f.get("name", "")) + "\n\n" + einl, positionen=pos,
                         summe_cent=m["summe_cent"], hinweise=hinweise, schluss="")


def mahnung_mail_text(m: dict, ap: dict | None, firmendaten: dict) -> tuple[str, str]:
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    anrede = f"Guten Tag {name}," if name else "Sehr geehrte Damen und Herren,"
    betreff = f"{STUFEN[m['stufe']]} zu Rechnung {m['rechnung']}"
    text = (f"{anrede}\n\nunsere Rechnung {m['rechnung']} war am {datum_de(m['faellig_am'])} fällig und ist noch offen. "
            f"Anbei erhalten Sie unsere {STUFEN[m['stufe']].lower() if m['stufe'] < 3 else 'letzte Mahnung'} "
            f"({m['nummer']}). Bitte überweisen Sie den Gesamtbetrag von {eur(m['summe_cent'])} bis zum "
            f"{datum_de(m['frist'])}.\n\nSollte sich Ihre Zahlung mit dieser Nachricht überschnitten haben, betrachten "
            "Sie sie bitte als gegenstandslos.\n\nMit freundlichen Grüßen\n"
            + "\n".join(x for x in (firmendaten.get("inhaber"), firmendaten.get("firma")) if x))
    return betreff, text


ABSENDER_NAME = "Hanserautisch – LUNA"


def folgemahnung_frage(m: dict, firma_name: str) -> str:
    """Telegram-Vorschau fuer die naechste Mahnstufe (aus `MahnStore.berechnen`)."""
    return (f"⚠️ {firma_name}: Frist der {STUFEN[m['stufe'] - 1]} zu {m['rechnung']} ist abgelaufen, noch kein "
            f"Zahlungseingang.\n\n{m['titel']} jetzt senden?\n"
            f"Offen {eur(m['offen_cent'])} + Verzugszinsen {eur(m['zinsen_cent'])} + {m['gebuehr_text']} "
            f"{eur(m['gebuehr_cent'])} = {eur(m['summe_cent'])}\nNeue Frist: {datum_de(m['frist'])}")


def folgemahnung_senden(bh, kunden, google, rechnung: str, stufe: int, firmendaten: dict, *, von: str) -> dict:
    """Nach ✅ des CEO (Telegram): Mahnung der erwarteten Stufe festschreiben und sofort senden."""
    ms = MahnStore(bh, kunden)
    vorschau = ms.berechnen(rechnung)
    if vorschau["stufe"] != int(stufe):
        raise ValueError(f"Stand hat sich geaendert (naechste Stufe waere {vorschau['stufe']}) -- bitte in LUNA-OS pruefen.")
    an, ap = empfaenger(kunden, vorschau["firma"])
    if not an:
        raise ValueError("Keine Rechnungs-Mail beim Kunden hinterlegt -- bitte in LUNA-OS senden.")
    m = ms.erstellen(rechnung, firmendaten, von=von)
    voll = ms.get(m["nummer"])
    betreff, text = mahnung_mail_text(voll, ap, firmendaten)
    senden(ms, google, m["nummer"], an=an, betreff=betreff, text=text, von=von, absender_name=ABSENDER_NAME)
    return {"nummer": m["nummer"], "an": an, "summe_cent": m["summe_cent"], "frist": m["frist"]}


def empfaenger(kunden, firma_nr: str) -> tuple[str, dict | None]:
    """-> (Mail-Adresse fuer Mahnungen, erster aktiver Ansprechpartner)."""
    f = kunden.firma(firma_nr) or {}
    aps = [a for a in f.get("ansprechpartner_liste", []) if a.get("aktiv")]
    ap = aps[0] if aps else None
    return f.get("rechnungsmail") or (ap or {}).get("mail") or "", ap


def senden(ms: MahnStore, google, nummer: str, *, an: str, betreff: str, text: str, von: str,
           absender_name: str = "") -> dict:
    """Festgeschriebene Mahnung (genau das archivierte PDF) aus LUNAs Konto senden, protokollieren, Mail archivieren.
    Aufruf nur nach ausdruecklicher Bestaetigung des CEO (LUNA-OS-Knopf bzw. Telegram ✅)."""
    from pathlib import Path
    m = ms.get(nummer)
    if not m:
        raise KeyError(nummer)
    if m.get("versendet_am"):
        raise ValueError(f"{m['nummer']} ist bereits versendet.")
    if not an or "@" not in an or not betreff or not text:
        raise ValueError("Empfaenger, Betreff und Text sind Pflicht.")
    if google is None or not google.verfuegbar():
        raise ValueError("Google ist nicht verbunden -- Senden nicht moeglich.")
    pfad = m["belege"][0]["pfad"]
    pdf = (ms.bh.dir / pfad).read_bytes()
    s = google.mail_senden(an, betreff, text, bestaetigt=True, absender_name=absender_name,
                           anhaenge=[(f"Mahnung_{m['nummer']}.pdf", pdf, "application/pdf")])
    if not s.get("ok"):
        raise ValueError(s.get("hinweis") or "Senden fehlgeschlagen.")
    ms.versendet(m["nummer"], {"an": an, "message_id": s.get("id", ""), "thread_id": s.get("thread_id", ""),
                               "betreff": betreff}, von=von)
    roh = google.mail_roh(s["id"]) if s.get("id") and hasattr(google, "mail_roh") else {}
    if roh.get("ok"):
        ms.bh.beleg_ablegen(roh["roh"], f"Mail_{m['nummer']}_aus_{s['id']}.eml", jahr=int(m["datum"][:4]),
                            art="geschaeftsbrief", bezug=m["nummer"], von=von)
    return {"nummer": m["nummer"], "an": an}
