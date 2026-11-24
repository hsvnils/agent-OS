"""OFC_ROADMAP O0: Fanclub HSVInside -- Rechnungen/Tickets lesen und Analyse (nur lesend, nichts speichern).

- **HSV-Rechnung** (`Rechnung.pdf`): Rechnungsnr, Auftrags-/Kunden-Nr, Datum, Spiel (Titel, Tag, Uhrzeit, Ort), je Ticket
  Position/Ticketnummer/Block/Preisgruppe/Reihe/Sitz/Preis, Summe, Anzahl, Zahlart (`rechnung_aus_text`).
- **Ticket-PDF**: Ticketnummer `<Rechnungsnr>-<Pos>` -> eindeutige Zuordnung zur Rechnungsposition (`ticket_aus_text`).
- **Ordner-Analyse** (`ordner_analyse`): je Spielordner der Saison (auch `Abgeschlossen/*`) erkannt ja/nein und Zahlen --
  **ohne Namen** (Namen der Mitglieder stehen in den Dateinamen und bleiben im Bericht aussen vor).
- **Postfach-Analyse** (`mail_analyse`): Mails aus `HsvInsideMail.posteingang` nach Typ (PayPal erhalten/gesendet,
  Eventim, HSV) mit gefundenen Feldern und maskierten Musterzeilen (Ziffern -> 9, Mail -> <MAIL>, Eigennamen -> <W>).
- Keine KI: alles regelbasiert (Mitgliederdaten, Grundsatz der Roadmap). Getrennt von der Buchhaltung.
"""
from __future__ import annotations

import email
import os
import re
from email import policy
from email.utils import parseaddr
from pathlib import Path

ABGESCHLOSSEN = "Abgeschlossen"


def nas_ordner() -> Path:
    """Mount im Container (deploy/docker-compose.yml) + Saison-Ordner (E3, einstellbar)."""
    return Path(os.environ.get("OFC_NAS_ORDNER", "/fanclub_nas")) / os.environ.get("OFC_SAISON", "Tickets 26-27")


def _cent(betrag: str) -> int:
    b = betrag.strip().replace(".", "").replace(",", ".")
    return int(round(float(b) * 100))


def pdf_text(pfad: Path) -> str:
    import pypdf
    r = pypdf.PdfReader(str(pfad))
    return "\n".join(p.extract_text() or "" for p in r.pages)


def pdf_bytes_text(daten: bytes) -> str:
    """O3: Text eines PDF-Anhangs (ohne ihn auf Platte zu legen)."""
    import io
    import pypdf
    r = pypdf.PdfReader(io.BytesIO(daten))
    return "\n".join(p.extract_text() or "" for p in r.pages)


def mail_pdfs(roh: bytes) -> tuple[dict, list[tuple[str, bytes]]]:
    """O3: Kopf (Absender-Domain, Message-ID, Datum) und alle PDF-Anhaenge einer Mail."""
    m = email.message_from_bytes(roh, policy=policy.default)
    dom = parseaddr(str(m.get("From", "")))[1].lower().rpartition("@")[2]
    pdfs = []
    for a in m.iter_attachments():
        name = a.get_filename() or ""
        if a.get_content_type() == "application/pdf" or name.lower().endswith(".pdf"):
            pdfs.append((Path(name).name, a.get_payload(decode=True) or b""))
    return {"domain": dom, "message_id": str(m.get("Message-ID", "")).strip(), "datum": str(m.get("Date", ""))}, pdfs


# Pos  Ticketnummer  Block  Preisgruppe (auch zwei Woerter, z. B. Gaestebereich)  Reihe  Sitz  Preis
_RE_TICKET = re.compile(r"^\s*(\d+)\s+(\d{9,14})-(\d+)\s+(\S+)\s+(.+?)\s+(\S+)\s+(\S+)\s+([\d.]*\d,\d\d)\s*EUR", re.M)
# „[Wettbewerb ][26-27 ]<Titel> / 28.11.2026 / 15:30 (Ort)“ -- z. B. „26-27 Hamburger SV - FC Bayern …“, „Auswaerts 26-27
# Dortmund …“, „DFB-Pokal 26-27 Eintracht Frankfurt …“, ohne Saison bei Freundschafts-/Europapokalspielen. Die Zeile danach
# enthaelt die Paarung „Heim-Gast“ (z. B. „Borussia Dortmund-Hamburger SV“).
_RE_SPIEL = re.compile(r"^[ \t]*()()([^\n/]+?)[ \t]*/[ \t]*(\d\d)\.(\d\d)\.(\d{4})\s*/\s*(\d\d:\d\d)\s*\((.+?)\)[ \t]*$"
                       r"(?:\n[ \t]*([^\n]+))?", re.M)
HSV = "Hamburger SV"


def _paarung(titel: str, folgezeile: str) -> tuple[str, str]:
    """-> (heim, gast). Folgezeile „Heim-Gast“ bevorzugt (Bindestrich ohne Leerzeichen), sonst Titel „Heim - Gast“."""
    for kandidat, trenner in ((folgezeile or "", r"(?<=\S)-(?=\S)"), (titel, r"\s+-\s+")):
        if HSV in kandidat:
            teile = [t.strip() for t in re.split(trenner, kandidat, maxsplit=1)]
            if len(teile) == 2 and all(teile) and HSV in teile:
                return teile[0], teile[1]
    return "", ""


def _feld(text: str, label: str, muster: str = r"\d{5,14}") -> str:
    """HSV-PDFs liefern Label und Wert teils vertauscht („262236181415Rechnungsnr:“) -- beide Reihenfolgen pruefen."""
    m = re.search(rf"{label}\s*:?\s*({muster})", text) or re.search(rf"({muster})\s*{label}", text)
    return m.group(1) if m else ""


def rechnung_aus_text(text: str) -> dict:
    tickets = [{"pos": int(m[1]), "ticketnr": f"{m[2]}-{m[3]}", "block": m[4], "preisgruppe": m[5], "reihe": m[6],
                "sitz": m[7], "preis_cent": _cent(m[8])} for m in _RE_TICKET.finditer(text)]
    sp = _RE_SPIEL.search(text)
    summe = re.search(r"Gesamtsumme f\S*r\s+(\d+)\s+Ticket\(s\):\s*([\d.]*\d,\d\d)\s*EUR", text)
    datum = re.search(r"Datum\s+(\d\d)\.(\d\d)\.(\d{4})", text)
    za = re.search(r"Zahlart:\s*(\S+)", text)
    r = {"rechnungsnr": _feld(text, "Rechnungsnr"), "auftragsnr": _feld(text, "Auftrags-Nr\\."),
         "kundennr": _feld(text, "Kunden-Nr\\."),
         "datum": f"{datum[3]}-{datum[2]}-{datum[1]}" if datum else "",
         "wettbewerb": "", "saison": "", "spiel": sp[3].strip() if sp else "",
         "spieltag": f"{sp[6]}-{sp[5]}-{sp[4]}" if sp else "", "uhrzeit": sp[7] if sp else "", "ort": sp[8] if sp else "",
         "tickets": tickets, "anzahl": int(summe[1]) if summe else len(tickets),
         "summe_cent": _cent(summe[2]) if summe else sum(t["preis_cent"] for t in tickets),
         "zahlart": za[1] if za else ""}
    ws = re.match(r"(.*?)[ \t]*(\d\d-\d\d)[ \t]+(.+)$", r["spiel"])       # „Auswaerts 26-27 Dortmund“ -> Wettbewerb, Saison
    if ws:
        r |= {"wettbewerb": ws[1].strip(), "saison": ws[2], "spiel": ws[3].strip()}
    heim, gast = _paarung(r["spiel"], (sp[9] or "") if sp else "")
    r |= {"heim": heim, "gast": gast, "heimspiel": heim == HSV if heim else None,
          "gegner": (gast if heim == HSV else heim) if heim else ""}
    if heim:
        r["spiel"] = f"{heim} - {gast}"
    if not r["rechnungsnr"] and tickets:
        r["rechnungsnr"] = tickets[0]["ticketnr"].split("-")[0]
    r["erkannt"] = bool(r["rechnungsnr"] and r["spiel"] and tickets)
    return r


def ticket_aus_text(text: str) -> dict:
    # HSV „Ticketnummer:“, BVB/Werder „Ticket Nummer:“/„Ticket-Nr.:“, Eintracht „Bestellnummer:“ -- immer <Rechnungsnr>-<Pos>
    m = re.search(r"(?:Ticket\s*-?\s*(?:nummer|nr\.?|number|[A-Za-z]+)?|Bestellnummer)\s*:\s*(\d{9,14})-(\d+)", text, re.I)
    return {"ticketnr": f"{m[1]}-{m[2]}", "rechnungsnr": m[1], "pos": int(m[2])} if m else {}


_RE_DATEI = re.compile(r"^(\d{9,14})-(\d+)([A-Z]?)(?:\s*-\s*|-)?(.*)\.pdf$", re.I)


def datei_name(name: str) -> dict:
    """`<Rechnungsnr>-<Pos>[A|B]-<Name>.pdf` -> Teile; Name leer, wenn keiner vergeben ist."""
    m = _RE_DATEI.match(name)
    if not m:
        return {}
    return {"rechnungsnr": m[1], "pos": int(m[2]), "zusatz": m[3], "name": m[4].strip()}


def _spielordner(saison: Path) -> list[tuple[Path, bool]]:
    out = []
    for p in sorted(saison.iterdir()) if saison.is_dir() else []:
        if not p.is_dir() or p.name.startswith(("@", ".", "#")):
            continue
        if p.name == ABGESCHLOSSEN:
            out += [(q, True) for q in sorted(p.iterdir()) if q.is_dir() and not q.name.startswith(("@", ".", "#"))]
        else:
            out.append((p, False))
    return out


def ordner_lesen(ordner: Path) -> dict:
    """Ein Spielordner -> Rechnung + Tickets (mit Namen aus dem Dateinamen). Intern; der Bericht zeigt keine Namen."""
    rgs = [rechnung_aus_text(pdf_text(f)) | {"datei": f.name} for f in sorted(ordner.glob("Rechnung*.pdf"))]
    rechnung = rgs[0] if rgs else {"erkannt": False, "tickets": []}
    for weitere in rgs[1:]:                                   # mehrere Bestellungen fuer ein Spiel
        rechnung = rechnung | {"tickets": rechnung["tickets"] + weitere["tickets"],
                               "anzahl": rechnung.get("anzahl", 0) + weitere.get("anzahl", 0),
                               "summe_cent": rechnung.get("summe_cent", 0) + weitere.get("summe_cent", 0)}
    dateien = []
    for f in sorted(ordner.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".pdf" or not f.name[:1].isdigit():
            continue
        t = {}
        try:
            t = ticket_aus_text(pdf_text(f))
        except Exception:
            pass
        dateien.append({"datei": f.name, "ticketnr": t.get("ticketnr", ""), **{k: v for k, v in datei_name(f.name).items()
                                                                              if k in ("name", "zusatz")}})
    return {"ordner": ordner.name, "rechnung": rechnung, "rechnungen": len(rgs), "rechnungs_liste": rgs, "tickets": dateien}


def ordner_analyse(saison: Path | None = None) -> dict:
    """O0 Dry-Run: je Spielordner Zahlen und Abweichungen -- keine Namen, nichts gespeichert."""
    saison = saison or nas_ordner()
    if not saison.is_dir():
        return {"ok": False, "hinweis": f"Saison-Ordner nicht gefunden ({saison.name}) -- Mount pruefen (E2)."}
    try:
        liste = _spielordner(saison)
    except PermissionError:                                  # BF-101: Freigabe erlaubt den Container-Benutzer nicht
        return {"ok": False, "hinweis": "Keine Leseberechtigung auf den Fanclub-Ordner (DSM: Benutzer nilskrueger berechtigen)."}
    spiele = []
    for ordner, fertig in liste:
        try:
            d = ordner_lesen(ordner)
        except Exception as exc:
            spiele.append({"ordner": ordner.name, "abgeschlossen": fertig, "fehler": exc.__class__.__name__})
            continue
        r, td = d["rechnung"], d["tickets"]
        soll = {t["ticketnr"] for t in r.get("tickets", [])}
        ist = {t["ticketnr"] for t in td if t["ticketnr"]}
        bekannt = {x.split("-")[0] for x in soll} | ({r["rechnungsnr"]} if r.get("rechnungsnr") else set())
        ohne_rg = {x.split("-")[0] for x in ist} - bekannt               # Tickets einer Bestellung ohne Rechnung im Ordner
        spiele.append({"ordner": ordner.name, "abgeschlossen": fertig, "rechnung_erkannt": r.get("erkannt", False),
                       "spiel": r.get("spiel", ""), "spieltag": r.get("spieltag", ""), "rechnungsnr": r.get("rechnungsnr", ""),
                       "karten_rechnung": r.get("anzahl", 0), "summe_cent": r.get("summe_cent", 0),
                       "ticket_dateien": len(td), "dateien_zugeordnet": len(ist & soll),
                       "dateien_ohne_ticketnr": sum(1 for t in td if not t["ticketnr"]),
                       "fehlende_tickets": len(soll - ist), "rechnungen": d.get("rechnungen", 0),
                       "bestellungen_ohne_rechnung": len(ohne_rg), "mit_name": sum(1 for t in td if t.get("name")),
                       "ohne_name": sum(1 for t in td if not t.get("name"))})
    return {"ok": True, "saison": saison.name, "spiele": spiele,
            "summe": {"spiele": len(spiele), "erkannt": sum(1 for s in spiele if s.get("rechnung_erkannt")),
                      "karten": sum(s.get("karten_rechnung", 0) for s in spiele),
                      "dateien": sum(s.get("ticket_dateien", 0) for s in spiele)}}


# -- Postfach-Analyse -------------------------------------------------------------------------------------------------
TYPEN = ("paypal_erhalten", "paypal_gesendet", "paypal_sonstiges", "eventim", "hsv", "sonstiges")
_BEHALTEN = {w.lower() for w in (
    "PayPal Sie Ihre Ihnen Zahlung Zahlungen Betrag Gesamtbetrag Transaktionscode Transaktions-ID Transaktion Mitteilung "
    "Nachricht Rechnung Rechnungsnr Rechnungsnummer Bestellung Bestellnummer Auftrag Auftragsnummer Kundennummer Ticket "
    "Tickets Eintrittskarte Eintrittskarten EUR Euro Datum Hallo Guten Tag Geld Empfänger Verkäufer Händler Eventim "
    "CTS HSV Hamburger SV Volksparkstadion Spiel Saison Block Reihe Platz Sitz Gebühr Gebühren Versand Mobile-Ticket "
    "Zahlungsdetails Belegnummer Status Abgeschlossen Rückerstattung Erstattung Gutschrift Zahlungsquelle Guthaben "
    "Bankkonto Kreditkarte Lastschrift Kauf Käufer Absender Von An Bestellbestätigung Buchungsbestätigung").split()}


def maske(zeile: str) -> str:
    """Musterzeile ohne personenbezogene Daten: Mailadressen, Ziffern und Eigennamen (gross geschrieben, nicht in der
    Liste bekannter Fachwoerter) werden ersetzt."""
    z = re.sub(r"[\w.+-]+@[\w.-]+", "<MAIL>", zeile)
    z = re.sub(r"https?://\S+", "<LINK>", z)
    z = re.sub(r"\d", "9", z)
    return re.sub(r"\b[A-ZÄÖÜ][\wÄÖÜäöüß'-]*", lambda m: m.group(0) if m.group(0).lower() in _BEHALTEN else "<W>", z)


def _text(m) -> str:
    teil = m.get_body(preferencelist=("plain", "html"))
    t = teil.get_content() if teil else ""
    if teil is not None and teil.get_content_type() == "text/html":
        t = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", t))
        t = re.sub(r"&nbsp;", " ", t)
    return re.sub(r"[ \t]+", " ", t)


def mail_typ(roh: bytes) -> tuple[str, dict]:
    m = email.message_from_bytes(roh, policy=policy.default)
    von = parseaddr(str(m.get("From", "")))[1].lower()
    dom = von.rpartition("@")[2]
    betreff = str(m.get("Subject", ""))
    text = _text(m)
    alles = f"{betreff}\n{text}"
    if "paypal" in dom:
        if re.search(r"(Zahlung|Geld)\s+(erhalten|empfangen)|haben .{0,60}erhalten|You.ve got money|received", alles, re.I):
            typ = "paypal_erhalten"
        elif re.search(r"(Zahlung|Geld).{0,60}gesendet|Zahlung an|Beleg f\S*r Ihre Zahlung|You sent|bezahlt", alles, re.I):
            typ = "paypal_gesendet"
        else:
            typ = "paypal_sonstiges"
    elif "eventim" in dom:
        typ = "eventim"
    elif dom == "hsv.de" or dom.endswith(".hsv.de"):
        typ = "hsv"
    else:
        typ = "sonstiges"
    anh = [(t.get_filename() or "", t.get_content_type()) for t in m.iter_attachments()]
    felder = {"betrag": bool(re.search(r"\d[\d.]*,\d\d\s*(€|EUR)|€\s*\d", alles)),
              "transaktionscode": bool(re.search(r"Transaktions(code|-ID|nummer)", alles, re.I)),
              "mitteilung": bool(re.search(r"Mitteilung|Nachricht\s+(von|an)", alles, re.I)),
              "rechnungsnr": bool(re.search(r"Rechnungsn(r|ummer)", alles, re.I)),
              "bestellnr": bool(re.search(r"Bestell(nummer|-Nr|nr)|Auftrags(nummer|-Nr)", alles, re.I)),
              "spiel": bool(re.search(r"Hamburger SV|HSV\s*-|-\s*Hamburger", alles))}
    return typ, {"domain": dom, "betreff": betreff, "text": text, "anhaenge": anh, "felder": felder,
                 "datum": str(m.get("Date", ""))}


def mail_analyse(postfach, *, tage: int = 90, muster_zeilen: int = 25) -> dict:
    """O0 Dry-Run des Postfachs: je Typ Anzahl, Absender-Domains, gefundene Felder, Anhaenge und maskierte Musterzeilen
    einer Beispiel-Mail. Nichts wird gespeichert; Namen/Betraege erscheinen nicht."""
    out = {t: {"anzahl": 0, "domains": {}, "felder": {}, "anhaenge": {}, "betreff_muster": [], "muster": []} for t in TYPEN}
    mails = postfach.posteingang(tage=tage)
    for x in mails:
        typ, info = mail_typ(x["roh"])
        o = out[typ]
        o["anzahl"] += 1
        o["domains"][info["domain"]] = o["domains"].get(info["domain"], 0) + 1
        for k, v in info["felder"].items():
            o["felder"][k] = o["felder"].get(k, 0) + int(v)
        for name, ct in info["anhaenge"]:
            schluessel = f"{ct} ({maske(Path(name).stem)[:40]})" if name else ct
            o["anhaenge"][schluessel] = o["anhaenge"].get(schluessel, 0) + 1
        bm = maske(info["betreff"])[:120]
        if bm not in o["betreff_muster"] and len(o["betreff_muster"]) < 8:
            o["betreff_muster"].append(bm)
        if not o["muster"]:
            zeilen = [maske(z.strip())[:140] for z in info["text"].splitlines() if z.strip()]
            o["muster"] = [z for z in zeilen if re.search(r"9|<MAIL>|[A-Za-zÄÖÜäöü]{4}", z)][:muster_zeilen]
    return {"ok": True, "tage": tage, "mails": len(mails), "typen": {k: v for k, v in out.items() if v["anzahl"]}}
