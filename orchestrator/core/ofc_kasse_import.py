"""OFC_KASSE_ROADMAP KA4: Abgleich mit dem PayPal-Kontoauszug (CSV-Upload durch den CEO, E-K7) -- kein API-Zugang, keine KI.

- Liest den PayPal-Aktivitaeten-Export (CSV, deutsch/englisch; Spalten werden am Namen erkannt) und den
  „Balance Reconciliation Report“ (Zeilen RH/RD/RF).
- Abgleich je Zeile: Transaktionscode schon bekannt (PayPal-Eingang O5, eigene Zahlung O4, frueherer Import) -> „bekannt“;
  sonst gleicher Betrag +-3 Tage mit einer Buchung ohne Code -> „passt“; sonst „neu“ mit Kategorie-Vorschlag. PayPal-
  Gebuehren werden als eigene Buchung „Gebuehren“ vorgeschlagen. Nicht-EUR, ausstehende/abgelehnte und Memo-Zeilen zaehlen nicht.
- Guthaben-Spalte: Vergleich „PayPal-Guthaben laut Auszug“ gegen den Kassenstand in LUNA; ohne Anfangsbestand kann er
  aus der ersten Zeile uebernommen werden.
- KA4b (echter Aktivitaeten-Export): zaehlt, was das Guthaben bewegt (Spalte „Auswirkung auf Guthaben“ Soll/Haben, auch
  „Ausstehend“); interne Verrechnungen (Verbindlichkeiten/Forderungen, Einbehaltungen) heben sich je Tag auf ->
  „technisch“; Kauf ueber „Spaeter bezahlen“ (Zahlung + Kaeuferkredit-Gutschrift) -> „finanziert“, die Ausgabe zaehlt bei der
  Abbuchung; Bank-Lastschriften -> Einzahlung, zurueckgegebene Lastschriften -> Einzahlung negativ, eine „Rueckbuchung“
  erbt die Kategorie der zurueckgebuchten Zahlung. Abbuchungen aufs Bankkonto (Privatkonto des CEO) -> Auszahlung.
- Uebernehmen nur nach Vorschau + Bestaetigung; die Datei wird unveraendert in `fanclub/importe/` abgelegt (nur neu);
  ein Importlauf ist als Ganzes stornierbar (Buchungen bleiben sichtbar). Nichts wird geloescht.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date, datetime

from .ofc_kasse import buchung_anlegen, buchungen, anfangsbestand, anfangsbestand_setzen
from .ofc_store import OfcStore

MAX_BYTES = 5 * 1024 * 1024
_SPALTEN = [                                       # (Schluessel, exakte Namen, Teilstrings) -- Reihenfolge = Vorrang
    ("datum", ("datum", "erstellt am", "date"), ("datum",)),
    ("uhrzeit", ("uhrzeit", "time"), ()),
    ("gebuehr", ("gebühr", "gebuehr", "entgelt", "bruttogebühren gesamt", "fee"), ("gebühr", "entgelt")),
    ("brutto", ("brutto", "bruttotransaktionsbetrag", "gross"), ("brutto",)),
    ("netto", ("netto", "nettotransaktionsbetrag", "net"), ()),
    ("guthaben", ("guthaben", "balance"), ()),
    ("tc", ("transaktionscode", "transaction id", "datensatznummer"), ("transaktionscode",)),
    ("bezug", ("zugehöriger transaktionscode", "reference txn id", "zugehörige datensatznummer"), ("zugehörige",)),
    ("name", ("name", "kundenname"), ()),
    ("beschreibung", ("beschreibung", "typ", "type", "description", "art des datensatzes"), ()),
    ("status", ("status",), ()),
    ("waehrung", ("währung", "transaktionswährung", "currency"), ()),
    ("auswirkung", ("auswirkung auf guthaben", "balance impact"), ()),
    ("hinweis", ("hinweis", "memo", "note", "betreff"), ()),
]
_WIRKUNG = {"soll": True, "haben": True, "debit": True, "credit": True, "memo": False}
_TECHNISCH = ("verbindlichkeiten", "forderungen", "einbehaltung für offene autorisierung", "rückbuchung allgemeiner einbehaltung")
_NICHT = re.compile(r"ausstehend|storniert|abgelehnt|pending|denied|reversed|vorläufig", re.I)


def _cent(s: str) -> int | None:
    t = (s or "").strip().replace("\xa0", "").replace(" ", "")
    if not t:
        return None
    t = re.sub(r"[^\d,.\-]", "", t)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return round(float(t) * 100)
    except ValueError:
        return None


def _datum(s: str) -> str:
    s = (s or "").strip()
    for muster, fmt in ((r"^\d{1,2}\.\d{1,2}\.\d{4}", "%d.%m.%Y"), (r"^\d{4}/\d{1,2}/\d{1,2}", "%Y/%m/%d"),
                        (r"^\d{4}-\d{1,2}-\d{1,2}", "%Y-%m-%d"), (r"^\d{1,2}/\d{1,2}/\d{4}", "%d/%m/%Y")):
        m = re.match(muster, s)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt).date().isoformat()
            except ValueError:
                return ""
    return ""


def _spalten(kopf: list[str]) -> dict[str, int]:
    k = [(x or "").strip().lstrip("﻿").strip('"').casefold() for x in kopf]
    out: dict[str, int] = {}
    belegt: set[int] = set()
    for key, exakt, _ in _SPALTEN:
        for i, name in enumerate(k):
            if i not in belegt and name in exakt:
                out[key] = i; belegt.add(i); break
    for key, _, teil in _SPALTEN:
        if key in out:
            continue
        for i, name in enumerate(k):
            if i not in belegt and any(t in name for t in teil):
                out[key] = i; belegt.add(i); break
    return out


def csv_lesen(roh: bytes) -> dict:
    """CSV-Bytes -> {ok, format, zeilen: [{nr, datum, name, beschreibung, brutto_cent, gebuehr_cent, guthaben_cent, tc, ...}]}."""
    if not roh:
        return {"ok": False, "hinweis": "Die Datei ist leer."}
    if len(roh) > MAX_BYTES:
        return {"ok": False, "hinweis": "Die Datei ist größer als 5 MB."}
    try:
        text = roh.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = roh.decode("latin-1")
    erste = text.splitlines()[0] if text.splitlines() else ""
    trenner = ";" if erste.count(";") > erste.count(",") else ("\t" if erste.count("\t") > erste.count(",") else ",")
    reihen = [r for r in csv.reader(io.StringIO(text), delimiter=trenner) if any(c.strip() for c in r)]
    fmt = "aktivitaeten"
    if reihen and reihen[0] and reihen[0][0].strip().lstrip("﻿") in ("RH", "FH", "SH"):
        fmt = "abgleichsbericht"
        rd = [r for r in reihen if r and r[0] == "RD"]
        if len(rd) <= 1:
            return {"ok": True, "format": fmt, "zeilen": [], "hinweis": "Der Bericht enthält keine Buchungszeilen (0 Einträge). "
                    "Bitte in PayPal unter Aktivitäten → Kontoauszüge den Aktivitäten-Export als CSV herunterladen."}
        kopf, daten = rd[0][1:], [r[1:] for r in rd[1:]]
    else:
        kopf_i = next((i for i, r in enumerate(reihen[:10]) if any(c.strip().casefold() in ("datum", "date", "transaktionscode",
                                                                                         "transaction id") for c in r)), None)
        if kopf_i is None:
            return {"ok": False, "hinweis": "Keine PayPal-CSV erkannt (Spalte „Datum“ / „Transaktionscode“ fehlt)."}
        kopf, daten = reihen[kopf_i], reihen[kopf_i + 1:]
    sp = _spalten(kopf)
    if "datum" not in sp or "brutto" not in sp:
        return {"ok": False, "hinweis": "Spalten „Datum“ und „Brutto“ nicht gefunden."}
    zeilen = []
    for n, r in enumerate(daten, start=1):
        g = lambda k: (r[sp[k]].strip() if k in sp and sp[k] < len(r) else "")  # noqa: E731
        brutto, dat = _cent(g("brutto")), _datum(g("datum"))
        if brutto is None or not dat:
            continue
        z = {"nr": n, "datum": dat, "uhrzeit": g("uhrzeit"), "name": g("name")[:80], "beschreibung": g("beschreibung")[:80],
             "brutto_cent": brutto, "gebuehr_cent": _cent(g("gebuehr")) or 0, "guthaben_cent": _cent(g("guthaben")),
             "tc": g("tc")[:40], "bezug": g("bezug")[:40], "status": g("status")[:30], "waehrung": (g("waehrung") or "EUR").upper()[:5],
             "auswirkung": g("auswirkung")[:20], "hinweis": g("hinweis")[:120]}
        wirkung = z["auswirkung"].casefold()
        if wirkung in _WIRKUNG:                                   # KA4b: was das Guthaben bewegt, zaehlt -- auch „Ausstehend“
            z["zaehlt"] = z["waehrung"] == "EUR" and _WIRKUNG[wirkung]
        else:
            z["zaehlt"] = z["waehrung"] == "EUR" and not _NICHT.search(z["status"]) and wirkung != "memo"
        zeilen.append(z)
    return {"ok": True, "format": fmt, "zeilen": zeilen}


def _kategorie(z: dict) -> str:
    t = f"{z['beschreibung']} {z['name']} {z['hinweis']}".casefold()
    typ = z["beschreibung"].casefold()
    if re.search(r"gebühr|gebuehr|fee", t) and not z["name"]:
        return "gebuehren"
    if re.search(r"ach-gutschrift|ach-überweisung|bankgutschrift", typ):          # Lastschrift vom Bankkonto (+) bzw. zurueckgegeben (-)
        return "einzahlung"
    if re.search(r"bankkonto|auszahlung|abbuchung|überweisung auf|withdraw", t) and z["brutto_cent"] < 0:
        return "auszahlung"
    if re.search(r"einzahlung|aufladung|bank deposit|von bankkonto", t) and z["brutto_cent"] > 0:
        return "einzahlung"
    if typ == "allgemeine zahlung" and "paypal" in z["name"].casefold() and z["brutto_cent"] < 0:
        return "tickets"                                                          # Abbuchung „Spaeter bezahlen“ (Tickets)
    if re.search(r"eventim|hamburger sport|hsv", t):
        return "tickets"
    if re.search(r"beitrag|mitglied", t):
        return "beitraege"
    if re.search(r"spende", t):
        return "spenden"
    if re.search(r"trikot|merch|schal", t):
        return "merch"
    return "offen" if z["brutto_cent"] > 0 else "sonstiges"                     # Geld von Personen ohne Hinweis: zuordnen


def _vorab(zeilen: list[dict]) -> dict[int, str]:
    """KA4b: Zeilen, die sich innerhalb der Datei aufheben -> {nr: "technisch"|"finanziert"}."""
    out: dict[int, str] = {}
    gruppen: dict[tuple, list[dict]] = {}
    for z in zeilen:
        if z["zaehlt"]:
            gruppen.setdefault(z["datum"], []).append(z)          # je Tag (Sekunden weichen ab)
    je_tc = {z["tc"]: z for z in zeilen if z["zaehlt"] and z["tc"]}
    for g in gruppen.values():
        tech = [z for z in g if z["beschreibung"].casefold() in _TECHNISCH]
        if tech and sum(z["brutto_cent"] for z in tech) == 0:
            out.update({z["nr"]: "technisch" for z in tech})
    for z in zeilen:
        if z["zaehlt"] and "käuferkredit" in z["beschreibung"].casefold() and z["brutto_cent"] > 0:
            kauf = je_tc.get(z["bezug"])
            if kauf and kauf["brutto_cent"] == -z["brutto_cent"] and kauf["nr"] not in out:
                out[z["nr"]] = out[kauf["nr"]] = "finanziert"
    return out


def import_plan(st: dict, zeilen: list[dict]) -> dict:
    """Dry-Run: je Zeile bekannt / passt / neu, Gebuehren, Guthaben-Vergleich -- schreibt nichts."""
    alle = buchungen(st)
    codes = {b["transaktionscode"] for b in alle if b.get("transaktionscode") and b["status"] != "storniert"}
    codes |= {e["id"][2:] for e in st.get("eingaenge", {}).values() if e["id"].startswith("e-")}
    ohne_code = [b for b in alle if not b.get("transaktionscode") and b["status"] != "storniert" and b["quelle"] in ("eingang", "zahlung")]
    je_id = {b["id"]: b for b in alle}
    benutzt: set[str] = set()
    vorab = _vorab(zeilen)
    out = []
    for z in zeilen:
        x = dict(z)
        k = _kategorie(z)
        if not z["zaehlt"]:
            x["ergebnis"] = "uebersprungen"
        elif z["nr"] in vorab:
            x["ergebnis"] = vorab[z["nr"]]
        elif z["tc"] and z["tc"] in codes:
            x["ergebnis"] = "bekannt"
        else:
            umkehr = z["beschreibung"].casefold() == "rückbuchung" or "ach-" in z["beschreibung"].casefold()
            treffer = None if umkehr else next((b for b in ohne_code if b["id"] not in benutzt and b["betrag_cent"] == z["brutto_cent"] and b["datum"]
                            and abs((date.fromisoformat(b["datum"]) - date.fromisoformat(z["datum"])).days) <= 3
                            and (b["kategorie"] == k or {b["kategorie"], k}.isdisjoint(("auszahlung", "einzahlung")))), None)
            if treffer:
                benutzt.add(treffer["id"])
                x.update(ergebnis="passt", buchung=treffer["id"])
            else:
                x.update(ergebnis="neu", kategorie=k)
        if z["zaehlt"] and z["gebuehr_cent"] and f"{z['tc']}:gebuehr" not in codes:
            x["gebuehr_neu"] = True
        out.append(x)
    je_tc = {x["tc"]: x for x in out if x["tc"]}
    for x in out:                                         # „Rueckbuchung“ erbt die Kategorie der zurueckgebuchten Zahlung
        if x["ergebnis"] == "neu" and x["beschreibung"].casefold() == "rückbuchung":
            ziel = je_tc.get(x["bezug"])
            if ziel:
                x["kategorie"] = (je_id.get(ziel.get("buchung", ""), {}).get("kategorie") or ziel.get("kategorie")
                                  or _kategorie(ziel))
    rueck = [x for x in out if x["zaehlt"] and "rückbuchung von ach-gutschrift" in x["beschreibung"].casefold()]
    neu = [x for x in out if x["ergebnis"] == "neu"]
    geb = [x for x in out if x.get("gebuehr_neu")]
    vergleich = None
    mit_g = [x for x in out if x["zaehlt"] and x.get("guthaben_cent") is not None]
    if mit_g:
        letzte = max(mit_g, key=lambda x: (x["datum"], x["uhrzeit"], x["nr"]))
        erste = min(mit_g, key=lambda x: (x["datum"], x["uhrzeit"], x["nr"]))
        start = anfangsbestand(st)
        vergleich = {"datum": letzte["datum"], "paypal_cent": letzte["guthaben_cent"],
                     "start_vorschlag": {"datum": erste["datum"],
                                         "betrag_cent": erste["guthaben_cent"] - erste["brutto_cent"] - erste["gebuehr_cent"]}}
        if start:
            bis = letzte["datum"]
            luna = int(start["betrag_cent"]) + sum(b["betrag_cent"] for b in alle if b["status"] == "gebucht"
                                                    and start["datum"] <= b["datum"] <= bis)
            luna += sum(x["brutto_cent"] for x in neu if start["datum"] <= x["datum"] <= bis)
            luna += sum(x["gebuehr_cent"] for x in geb if start["datum"] <= x["datum"] <= bis)
            vergleich.update(luna_cent=luna, abweichung_cent=letzte["guthaben_cent"] - luna)
    return {"ok": True, "zeilen": out, "anzahl": len(out), "bekannt": sum(1 for x in out if x["ergebnis"] == "bekannt"),
            "passt": sum(1 for x in out if x["ergebnis"] == "passt"), "neu": len(neu), "gebuehren": len(geb),
            "uebersprungen": sum(1 for x in out if x["ergebnis"] == "uebersprungen"),
            "neu_cent": sum(x["brutto_cent"] for x in neu), "gebuehren_cent": sum(x["gebuehr_cent"] for x in geb),
            "technisch": sum(1 for x in out if x["ergebnis"] == "technisch"),
            "finanziert": sum(1 for x in out if x["ergebnis"] == "finanziert"),
            "lastschrift_zurueck": len(rueck), "lastschrift_zurueck_cent": sum(x["brutto_cent"] for x in rueck),
            "vergleich": vergleich, "hat_anfangsbestand": bool(anfangsbestand(st))}


def import_anwenden(store: OfcStore, roh: bytes, dateiname: str, *, anfangsbestand_uebernehmen: bool = False,
                    von: str = "") -> dict:
    """Vorschau erneut rechnen, Datei unveraendert ablegen (nur neu), neue Zeilen + Gebuehren buchen."""
    gel = csv_lesen(roh)
    if not gel.get("ok"):
        return gel
    plan = import_plan(store.stand(), gel["zeilen"])
    if not plan["neu"] and not plan["gebuehren"] and not anfangsbestand_uebernehmen:
        return plan | {"ok": True, "gebucht": 0, "hinweis": "Nichts Neues in der Datei."}
    iid = "i-" + hashlib.sha1(roh).hexdigest()[:10] + "-" + datetime.now().strftime("%H%M%S")
    ordner = store.dir / "importe"
    ordner.mkdir(parents=True, exist_ok=True)
    with open(ordner / f"{iid}.csv", "xb") as f:                         # Original nur neu ablegen
        f.write(roh)
    n, fehler = 0, []
    for x in plan["zeilen"]:
        text = " – ".join(t for t in (x["beschreibung"], x["name"], x["hinweis"]) if t) or "PayPal"
        if x["ergebnis"] == "neu":
            r = buchung_anlegen(store, datum=x["datum"], betrag_cent=x["brutto_cent"], kategorie=x["kategorie"], text=text,
                                von=von, import_id=iid, transaktionscode=x["tc"])
            n += bool(r.get("ok"))
            if not r.get("ok"):
                fehler.append(f"{x['datum']} {text[:40]}: {r.get('hinweis')}")
        if x.get("gebuehr_neu"):
            r = buchung_anlegen(store, datum=x["datum"], betrag_cent=x["gebuehr_cent"], kategorie="gebuehren",
                                text=f"PayPal-Gebühr – {text}", von=von, import_id=iid,
                                transaktionscode=f"{x['tc']}:gebuehr" if x["tc"] else "")
            n += bool(r.get("ok"))
    if anfangsbestand_uebernehmen and plan["vergleich"] and not plan["hat_anfangsbestand"]:
        sv = plan["vergleich"]["start_vorschlag"]
        anfangsbestand_setzen(store, sv["datum"], sv["betrag_cent"], von=von)
    store.erfassen("ofc_kasse_import", {"id": iid, "datei": dateiname[:120], "format": gel["format"], "zeilen": plan["anzahl"],
                                        "gebucht": n, "von_datum": min((x["datum"] for x in plan["zeilen"]), default=""),
                                        "bis_datum": max((x["datum"] for x in plan["zeilen"]), default="")}, von=von)
    return plan | {"ok": True, "import_id": iid, "gebucht": n, "nicht_gebucht": fehler,
                   **({"hinweis": f"{n} Buchung(en) übernommen, {len(fehler)} nicht: " + "; ".join(fehler[:3])} if fehler else {})}


def import_storno(store: OfcStore, iid: str, *, von: str = "") -> dict:
    st = store.stand()
    if iid not in (st.get("kasse_importe") or {}):
        return {"ok": False, "hinweis": "Import nicht gefunden."}
    n = 0
    for b in (st.get("kasse") or {}).values():
        if b.get("import_id") == iid and not b.get("storniert"):
            store.erfassen("ofc_kasse", {"id": b["id"], "storniert": True}, von=von)
            n += 1
    store.erfassen("ofc_kasse_import", {"id": iid, "storniert": True}, von=von)
    return {"ok": True, "import_id": iid, "storniert": n}


def importe(st: dict) -> list[dict]:
    return sorted((st.get("kasse_importe") or {}).values(), key=lambda x: x.get("ts", ""), reverse=True)

