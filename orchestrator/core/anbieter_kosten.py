"""Kosten je Anbieter (VORSCHLAGSPAUSE_ANBIETER P3, CEO 2026-10-07).

Vorgabe CEO: „Abo-Kosten duerfen nicht mit zusaetzlichen Kosten fuer Credits oder so gemischt werden.“ Deshalb je
Anbieter **zwei getrennte Werte, nie zusammengerechnet**:

- **Abo** -- laufender Monatswert der aktiven Abos und die im Jahr gebuchten Belege, die einer Abo-Faelligkeit
  zugeordnet sind (vom taeglichen Abo-Lauf vermerkt oder -- noch nicht vermerkt -- nach derselben Regel gefunden);
- **Einzelkosten** -- alle anderen gebuchten Ausgaben desselben Anbieters im Jahr (Credits, Aufladungen, Nutzung).

Welche Lieferanten zu einem Anbieter gehoeren, steht als Namensmuster im Register (`dienste_register.ANBIETER`).
Rein lesend -- keine Buchung, keine Aenderung.
"""
from __future__ import annotations

from datetime import date

from .abos import AboStore, monatlich_cent, naechste, offene
from .eigenbelege import EigenbelegStore
from .eingangsbelege import EingangStore


def _abo_laeuft(a: dict, heute: date) -> bool:
    """Laeuft = es steht noch eine Zahlung an (gekuendigt mit Ende vor der naechsten Faelligkeit zaehlt nicht mehr)."""
    return a.get("status") == "aktiv" and bool(naechste(a, heute))


def kosten(eintraege: list[dict], firmen: dict[str, str], anbieter: list[dict], *, heute: date) -> dict:
    """firmen = {Firmennummer: Name}. -> {anbieter_id: {abo_monat_cent, abo_jahr_cent, einzel_jahr_cent, abos[], ...}}
    plus Summen `abos_monat_cent` und `einzel_jahr_cent` -- getrennt, ohne gemeinsame Summe."""
    jahr = str(heute.year)
    abos = AboStore._falte(eintraege)
    abo_beleg = {v["beleg"]: a["nummer"] for a in abos.values() for v in a["erledigt"].values() if v.get("beleg")}
    abo_beleg |= {o["beleg"]: o["abo"] for o in offene(eintraege, heute) if o["beleg"]}     # noch nicht vermerkt
    ausgaben = []                                                  # (firma, nummer, datum, betrag_cent)
    for x in EingangStore._falte(eintraege).values():
        f = x.get("felder") or {}
        if x["status"] == "gebucht" and f.get("art", "ausgabe") == "ausgabe":
            ausgaben.append((f.get("lieferant_firma") or "", x["nummer"], str(f.get("rechnungsdatum") or ""), abs(int(f.get("betrag_cent") or 0))))
    for x in EigenbelegStore._falte(eintraege).values():
        if x["status"] == "gebucht" and x.get("art") == "ausgabe":
            ausgaben.append((x.get("firma") or "", x["nummer"], str(x.get("datum") or ""), abs(int(x.get("betrag_cent") or 0))))
    out, summe_abo, summe_einzel = {}, 0, 0
    for an in anbieter:
        muster = [m.lower() for m in an.get("lieferant") or []]
        nummern = {n for n, name in firmen.items() if muster and any(m in (name or "").lower() for m in muster)}
        if not nummern:
            continue
        eigene_abos = [a for a in abos.values() if a.get("firma") in nummern and a.get("art", "ausgabe") == "ausgabe"]
        abo_monat = sum(monatlich_cent(a) for a in eigene_abos if _abo_laeuft(a, heute))
        im_jahr = [b for b in ausgaben if b[0] in nummern and b[2][:4] == jahr]
        abo_jahr = sum(b[3] for b in im_jahr if b[1] in abo_beleg)
        einzel = [b for b in im_jahr if b[1] not in abo_beleg]
        if not (eigene_abos or im_jahr):
            continue
        out[an["id"]] = {"abo_monat_cent": abo_monat, "abo_jahr_cent": abo_jahr,
                         "einzel_jahr_cent": sum(b[3] for b in einzel), "einzel_anzahl": len(einzel),
                         "abos": [{k: a.get(k) for k in ("nummer", "bezeichnung", "betrag_cent", "turnus", "start", "ende")}
                                  | {"laeuft": _abo_laeuft(a, heute), "monatlich_cent": monatlich_cent(a)}
                                  for a in sorted(eigene_abos, key=lambda a: a["start"])]}
        summe_abo += abo_monat
        summe_einzel += out[an["id"]]["einzel_jahr_cent"]
    return {"jahr": heute.year, "anbieter": out, "abos_monat_cent": summe_abo, "einzel_jahr_cent": summe_einzel}
