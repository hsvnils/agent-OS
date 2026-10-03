"""Belegverfolgung (BELEGVERFOLGUNG_ROADMAP B1, CEO 2026-10-03).

Von einem Kundenbeleg aus (Angebot, Auftrag, Rechnung inkl. Entwurf/Vorkasse/Storno/Altrechnung, Mahnung) alle damit
verbundenen Belege und Ereignisse sammeln -- nur aus dem, was in der Hash-Kette gespeichert ist (nichts erfunden):

- Auftrag -> Angebot (`angebot`), Rechnung/Entwurf -> Auftrag bzw. Angebot, Storno -> Original (`bezug`),
  Korrektur -> stornierte Rechnung (`korrektur_zu`; aeltere Faelle: naechste Rechnung desselben Auftrags nach dem
  Storno), Schlussrechnung -> Vorkasse (`abzuege`), Mahnung -> Rechnung, Mahnverfahren/Zahlungen an der Rechnung,
  Lieferungen und Projektbericht am Auftrag, Firmenakte-Dokumente mit `bezug`.

Ergebnis: Knoten nach Datum sortiert (Belege `gross`, Ereignisse klein), Kanten mit Beschriftung, Index des
Ausgangsbelegs -- die Oberflaeche zeichnet daraus den Zeitstrahl (vorher / aktuell / nachher).
"""
from __future__ import annotations

from .angebote import AngebotStore, summen
from .beauftragung import AuftragBuch
from .firmenakte import _falte as akte_falte
from .lieferungen import Lieferungen
from .mahnungen import MahnStore
from .rechnungen import RechnungStore

RANG = {"angebot": 0, "auftrag": 1, "lieferung": 2, "entwurf": 3, "vorkasse": 3, "rechnung": 3, "schlussrechnung": 3,
        "storno": 4, "zahlung": 5, "mahnung": 6, "mahnverfahren": 7, "bericht": 8, "dokument": 9}
FINANZ = {"entwurf", "vorkasse", "rechnung", "schlussrechnung", "storno", "zahlung", "mahnung", "mahnverfahren"}
ART_TEXT = {"angebot": "Angebot", "auftrag": "Auftrag", "entwurf": "Rechnungsentwurf", "vorkasse": "Vorkasse-Rechnung",
            "rechnung": "Rechnung", "schlussrechnung": "Schlussrechnung", "storno": "Stornorechnung", "zahlung": "Zahlung",
            "mahnung": "Mahnung", "mahnverfahren": "Mahnverfahren", "lieferung": "Lieferung", "bericht": "Projektbericht",
            "dokument": "Dokument"}


def _d(x) -> str:
    return str(x or "")[:10]


def kette(eintraege: list[dict], kennung: str, *, finanzen: bool = True) -> dict:
    k = (kennung or "").strip()
    # Reihenfolge in der Kette: bei gleichem Datum steht frueher Erfasstes zuerst (z. B. Storno vor Korrektur)
    seq: dict[str, int] = {}
    zahl_seq: dict[str, list] = {}
    for i, e in enumerate(eintraege):
        d = e["daten"]
        for schl in ("nummer", "id", "entwurf_id"):
            if d.get(schl) and e["typ"] not in ("rechnung_bezahlt", "auftrag_bericht_versendet"):
                seq.setdefault(str(d[schl]), i)
        if e["typ"] == "rechnung_bezahlt":
            zahl_seq.setdefault(d["nummer"], []).append(i)
        elif e["typ"] == "auftrag_bericht_versendet":
            seq.setdefault(f"B:{d['nummer']}:{len([x for x in seq if x.startswith('B:' + d['nummer'] + ':')]) + 1}", i)
        elif e["typ"] == "rechnung_mahnverfahren":
            seq.setdefault(f"MV:{d['rechnung']}", i)
    knoten: dict[str, dict] = {}
    kanten: list[dict] = []

    def knoten_neu(kid, art, nummer, datum, *, titel="", betrag=None, status="", oeffnen=None, firma=""):
        knoten[kid] = {"id": kid, "art": art, "art_text": ART_TEXT[art], "nummer": nummer, "datum": _d(datum),
                       "titel": titel or "", "betrag_cent": betrag, "status": status, "firma": firma,
                       "gross": art not in ("zahlung", "lieferung", "mahnverfahren", "dokument"),
                       "oeffnen": oeffnen or {}}

    def kante(von, nach, text):
        if von in knoten and nach in knoten:
            kanten.append({"von": von, "nach": nach, "text": text})

    angebote = AngebotStore._falte(eintraege)
    for a in angebote.values():
        sm = summen(a["positionen"], a.get("zuschlaege") or [], a.get("rabatt_prozent") or 0)
        knoten_neu(a["nummer"], "angebot", a["nummer"], a.get("datum") or a["angelegt"], titel=a.get("titel"),
                   betrag=sm["gesamt_cent"], status=a["status"], firma=a["firma"],
                   oeffnen={"act": "an-detail", "id": a["nummer"]})
    from .beauftragung import abschluss
    auftraege = abschluss(AuftragBuch._falte(eintraege), eintraege)
    for a in auftraege.values():
        sm = summen(a["positionen"], a.get("zuschlaege") or [], a.get("rabatt_prozent") or 0)
        knoten_neu(a["nummer"], "auftrag", a["nummer"], a.get("datum") or a["angelegt"], titel=a.get("titel"),
                   betrag=sm["gesamt_cent"], status="abgeschlossen" if a.get("abgeschlossen") else a["status"],
                   firma=a["firma"], oeffnen={"act": "ab-detail", "id": a["nummer"]})
        if a.get("angebot"):
            kante(a["angebot"], a["nummer"], "beauftragt")
        for i, b in enumerate(a.get("berichte") or [], 1):
            bid = f"B:{a['nummer']}:{i}"
            knoten_neu(bid, "bericht", f"Projektbericht{' v' + str(i) if i > 1 else ''}", b["ts"], firma=a["firma"],
                       titel=f"an {b.get('an', '')}",
                       oeffnen={"url": f"/api/crm/auftraege/{a['nummer']}/bericht/pdf?archiv={i}"})
            kante(a["nummer"], bid, "Bericht gesendet")
    for l in Lieferungen._falte(eintraege).values():
        if l.get("entfernt") or l.get("auftrag") not in auftraege:
            continue
        lid = f"L:{l['id']}"
        knoten_neu(lid, "lieferung", "Lieferung", l.get("datum") or l["angelegt"], titel=l.get("titel"),
                   firma=auftraege[l["auftrag"]]["firma"], oeffnen={"act": "ab-detail", "id": l["auftrag"]})
        kante(l["auftrag"], lid, "geliefert")

    entwuerfe, rechnungen = RechnungStore._falte(eintraege)
    for eid, x in entwuerfe.items():
        knoten_neu(eid, "entwurf", "Entwurf", x["angelegt"], titel=x.get("titel"), status="entwurf", firma=x.get("firma", ""),
                   betrag=RechnungStore._summen(x)["summe_cent"], oeffnen={"act": "re-detail", "id": eid})
    for r in rechnungen.values():
        art = r.get("art") or "rechnung"
        art = {"anzahlung": "vorkasse"}.get(art, art)
        if art == "rechnung" and r.get("abzuege"):
            art = "schlussrechnung"
        knoten_neu(r["nummer"], art, r["nummer"], r.get("rechnungsdatum") or r.get("festgeschrieben_am"),
                   titel=r.get("titel"), betrag=r.get("summe_cent"), status=r["status"], firma=r.get("firma", ""),
                   oeffnen={"act": "re-detail", "id": r["nummer"]})
        for i, z in enumerate(r.get("zahlungen") or []):
            if z.get("storniert"):
                continue
            zid = f"Z:{r['nummer']}:{i}"
            zs = zahl_seq.get(r["nummer"]) or []
            seq.setdefault(zid, zs[i] if i < len(zs) else 0)
            knoten_neu(zid, "zahlung", "Zahlung", z.get("datum"), betrag=z.get("betrag_cent"), firma=r.get("firma", ""),
                       titel=z.get("notiz") or "", oeffnen={"act": "re-detail", "id": r["nummer"]})
            kante(r["nummer"], zid, "bezahlt")
    alle_re = list(entwuerfe.items()) + [(r["nummer"], r) for r in rechnungen.values()]
    for rid, r in alle_re:
        if r.get("art") == "storno":
            kante(r.get("bezug"), rid, "storniert durch")
        elif r.get("auftrag"):
            kante(r["auftrag"], rid, {"anzahlung": "Vorkasse"}.get(r.get("art"), "berechnet"))
        elif r.get("angebot"):
            kante(r["angebot"], rid, "berechnet")
        for ab in (r.get("abzuege") or []) if r.get("art") != "storno" else []:   # Storno kehrt den Abzug nur um
            kante(ab.get("nummer"), rid, "abgezogen in")
        if r.get("korrektur_zu"):
            kante(r["korrektur_zu"], rid, "ersetzt durch")
    # aeltere Korrekturen ohne `korrektur_zu`: naechste Rechnung desselben Auftrags nach der stornierten
    mit_korr = {r.get("korrektur_zu") for _, r in alle_re if r.get("korrektur_zu")}
    for o in rechnungen.values():
        if o["status"] != "storniert" or not o.get("auftrag") or o["nummer"] in mit_korr:
            continue
        spaeter = sorted((r for r in rechnungen.values() if r.get("auftrag") == o["auftrag"] and r.get("art") == o.get("art")
                          and r["nummer"] > o["nummer"] and r["status"] != "storno"), key=lambda r: r["nummer"])
        if spaeter:
            kante(o["nummer"], spaeter[0]["nummer"], "ersetzt durch")

    for m in MahnStore._falte(eintraege).values():
        r = rechnungen.get(m.get("rechnung"))
        knoten_neu(m["nummer"], "mahnung", m["nummer"], m.get("datum") or m.get("erstellt"),
                   titel=f"Mahnstufe {m.get('stufe')}", betrag=m.get("summe_cent"), firma=(r or {}).get("firma", ""),
                   status="gesendet" if m.get("versendet_am") else "",
                   oeffnen={"url": f"/api/finanzen/mahnungen/{m['nummer']}/pdf"})
        kante(m.get("rechnung"), m["nummer"], "gemahnt")
    for re_nr, mv in MahnStore.mahnverfahren(eintraege).items():
        mid = f"MV:{re_nr}"
        knoten_neu(mid, "mahnverfahren", "Mahnverfahren", mv.get("datum") or mv["erfasst"], titel=mv.get("durch") or "",
                   firma=(rechnungen.get(re_nr) or {}).get("firma", ""), oeffnen={"act": "re-detail", "id": re_nr})
        kante(re_nr, mid, "Mahnverfahren")
    berichte = {b.get("akte_id") for a in auftraege.values() for b in a.get("berichte") or []}
    for doc in akte_falte(eintraege)[0].values():
        if not doc.get("bezug") or doc["id"] in berichte or doc.get("bezug") not in knoten:
            continue
        did = f"D:{doc['id']}"
        knoten_neu(did, "dokument", doc.get("titel") or "Dokument", doc.get("datum") or doc["ts"], firma=doc.get("firma", ""),
                   oeffnen={"url": f"/api/crm/akte/{doc['id']}/datei"})
        kante(doc["bezug"], did, "Dokument")

    start = k if k in knoten else k.upper()
    if start not in knoten:
        raise KeyError(kennung)
    if not finanzen and knoten[start]["art"] in FINANZ:
        raise PermissionError("Rechnungen sieht nur, wer das Modul Finanzen hat.")
    nachbarn: dict[str, set] = {}
    for e in kanten:
        nachbarn.setdefault(e["von"], set()).add(e["nach"])
        nachbarn.setdefault(e["nach"], set()).add(e["von"])
    gesehen, offen = {start}, [start]
    while offen:
        n = offen.pop()
        for m in nachbarn.get(n, ()):
            if m not in gesehen:
                gesehen.add(m)
                offen.append(m)
    teil = [knoten[n] for n in gesehen if finanzen or knoten[n]["art"] not in FINANZ]
    for x in teil:
        x["seq"] = seq.get(x["id"], seq.get(x["id"].split(":", 1)[-1], 0))
    teil.sort(key=lambda x: (x["datum"] or "9999", x["seq"], RANG[x["art"]]))
    ids = {x["id"] for x in teil}
    pos = next(i for i, x in enumerate(teil) if x["id"] == start)
    return {"start": start, "position": pos, "knoten": teil,
            "kanten": [e for e in kanten if e["von"] in ids and e["nach"] in ids],
            "vorher": pos, "nachher": len(teil) - pos - 1}
