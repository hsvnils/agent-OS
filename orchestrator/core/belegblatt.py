"""Digitaler Beleg (DIGITALER_BELEG_ROADMAP D1-D3, CEO 2026-10-03, Variante A).

Liefert fuer Angebot, Auftragsbestaetigung, Rechnung (alle Arten) und Mahnung ein **Belegblatt** -- dieselben Inhalte
wie das PDF (gleiche Bausteine: `teile()` der Stores, `_empfaenger`, Summen, Zahlungstexte, Firmendaten), aber als
Daten fuer die Ansicht in LUNA-OS. Interne Felder (Nachkalkulation, Zeiten, Kennzahlen, Notizen ausser der
Anmerkung, die auch im PDF steht) kommen nie aufs Blatt.
"""
from __future__ import annotations

from .angebote import _empfaenger, _summen_zeilen, pdf_posten
from .beleg_pdf import _iban_lesbar, datum_de, menge_text
from .buchhaltung import jetzt


def absender(fd: dict) -> str:
    return " · ".join(x for x in (fd.get("firma"), fd.get("inhaber"), fd.get("strasse"),
                                  f"{fd.get('plz', '')} {fd.get('ort', '')}".strip()) if x)


def fuss(fd: dict) -> list[str]:
    b = fd.get("bank") or {}
    return [x for x in (f"Steuernummer {fd['steuernummer']}" if fd.get("steuernummer") else "",
                        f"Bank: {b['bank']}" if b.get("bank") else "", f"IBAN {_iban_lesbar(b['iban'])}" if b.get("iban") else "",
                        f"BIC {b['bic']}" if b.get("bic") else "", f"Kontoinhaber: {b['kontoinhaber']}" if b.get("kontoinhaber") else "")
            if x]


def gruppen(positionen: list[dict]) -> list[dict]:
    """Positionen je Gruppe wie im Hanserautisch-PDF (Reihenfolge der ersten Nennung), fortlaufend nummeriert."""
    out: dict[str, dict] = {}
    for i, p in enumerate(positionen, 1):
        extra = pdf_posten(p)
        name = p.get("gruppe") or ""
        g = out.setdefault(name, {"name": name, "farbe": p.get("gruppe_farbe", "blau"), "posten": []})
        g["posten"].append({"nr": i, "beschreibung": p["beschreibung"], "detail": extra.get("detail", p.get("detail", "")),
                            "menge": menge_text(p["menge"]) if p.get("menge") is not None else "",
                            "einheit": p.get("einheit", ""), "einzel_cent": p.get("einzelpreis_cent"),
                            "gesamt_cent": p.get("gesamt_cent"), "einzel_text": extra.get("einzel_text", ""),
                            "gesamt_text": extra.get("gesamt_text", "")})
    return list(out.values())


def summen_zeilen(sm: dict) -> list[list]:
    return [[n, c] for n, c in (_summen_zeilen(sm) or [])]


def _blatt(*, art, nummer, titel, fd, firma, ap, infos, anrede, einleitung, positionen, summen, gesamt_text, gesamt_cent,
           hinweise, schluss="", stempel=None, extra=None) -> dict:
    return {"art": art, "nummer": nummer, "titel": titel or "", "absender": absender(fd),
            "empfaenger": [x for x in _empfaenger(firma, ap) if x], "infos": [[a, b] for a, b in infos if b],
            "anrede": anrede or "", "einleitung": einleitung or "", "gruppen": gruppen(positionen),
            "summen": summen_zeilen(summen) if summen else [], "gesamt": {"text": gesamt_text, "cent": gesamt_cent},
            "hinweise": [h for h in hinweise if h], "schluss": schluss or "", "fuss": fuss(fd),
            "stempel": stempel, **(extra or {})}


def _stempel(art: str, text: str, unter: str = "") -> dict:
    return {"art": art, "text": text, "unter": unter}


def rechnung(rs, r: dict, fd: dict) -> dict:
    entwurf = r.get("status") == "entwurf"
    heute = jetzt().date().isoformat()
    if entwurf:                                          # wie die PDF-Vorschau: Datum heute, Nummer folgt
        r = r | {"nummer": "ENTWURF", "rechnungsdatum": heute, "faellig_am": rs._faellig(r, jetzt().date()).isoformat()}
    t = rs.teile(r)
    infos = [tuple(i.split(": ", 1)) for i in t["infos"]]
    if entwurf:
        infos = [(a, "wird beim Festschreiben vergeben" if a == t["art"] else b) for a, b in infos]
    if not entwurf and r.get("art") != "storno" and r.get("faellig_am"):
        infos.append(("Fällig am", datum_de(r["faellig_am"])))
    st = r.get("status")
    zahl = [z for z in r.get("zahlungen") or [] if not z.get("storniert")]
    from .mahnungen import MahnStore                    # CEO 2026-10-04: laufendes Mahnverfahren statt „ueberfaellig“
    mv = MahnStore.mahnverfahren(rs.bh.eintraege()).get(r.get("nummer", "")) or {} if not entwurf else {}
    stempel = (_stempel("grau", "ENTWURF") if entwurf
               else _stempel("rot", "STORNO", f"zu {r.get('bezug', '')}") if r.get("art") == "storno"
               else _stempel("rot", "STORNIERT", f"durch {r.get('storniert_durch', '')}") if st == "storniert"
               else _stempel("gruen", "BEZAHLT", datum_de(zahl[-1]["datum"]) if zahl else "") if st == "bezahlt"
               else _stempel("rot", "IM MAHNVERFAHREN", f"seit {datum_de(mv['datum'])}" if mv.get("datum") else "") if mv
               else _stempel("rot", "ÜBERFÄLLIG", f"seit {datum_de(r['faellig_am'])}") if r.get("faellig_am", "9") < heute
               else _stempel("gelb", "OFFEN", f"fällig {datum_de(r['faellig_am'])}" if r.get("faellig_am") else ""))
    from .beleg_pdf import HINWEIS_19
    return _blatt(art=t["art"], nummer="" if entwurf else r["nummer"], titel=r.get("titel"), fd=fd, firma=t["firma"],
                  ap=t["ap"], infos=infos, anrede=t["anrede"], einleitung=t["einleitung"], positionen=r["positionen"],
                  summen=r["summen"], gesamt_text="Betrag" if r.get("art") == "storno" else "Rechnungsbetrag",
                  gesamt_cent=r["summe_cent"], hinweise=[t["zahlung"], HINWEIS_19], stempel=stempel,
                  extra={"original_pdf": bool(r.get("alt")),
                         "anlage": "Stundenzettel" if (r.get("projektzeiten") or {}).get("darstellung") == "zusammen"
                         and (r.get("projektzeiten") or {}).get("zeilen") else ""})


def angebot(st, a: dict, fd: dict) -> dict:
    t = st.teile(a, fd)
    heute = jetzt().date().isoformat()
    s = a["status"]
    stempel = (_stempel("grau", "ENTWURF") if s == "entwurf"
               else _stempel("gruen", "ANGENOMMEN", f"→ {a['auftrag']}" if a.get("auftrag") else "") if s == "angenommen"
               else _stempel("rot", "ABGELEHNT") if s == "abgelehnt"
               else _stempel("grau", "ABGELAUFEN", datum_de(a["gueltig_bis"])) if a.get("gueltig_bis", "9") < heute
               else None)
    return _blatt(art="Angebot", nummer=a["nummer"], titel=t["untertitel"], fd=fd, firma=t["firma"], ap=t["ap"],
                  infos=t["infos"], anrede=t["anrede"], einleitung=t["einleitung"], positionen=a["positionen"],
                  summen=a["summen"], gesamt_text="Gesamtbetrag", gesamt_cent=a["summe_cent"], hinweise=t["hinweise"],
                  schluss=t["schluss"], stempel=stempel, extra={"kalkulation": t["kalkulation"],
                                                                "praesentation": t.get("praesentation") or {}})


def auftrag(ab, a: dict, fd: dict) -> dict:
    t = ab.teile(a)
    stempel = (_stempel("rot", "STORNIERT") if a["status"] == "storniert"
               else _stempel("gruen", "ABGESCHLOSSEN") if a.get("abgeschlossen")
               else _stempel("gruen", "GELIEFERT", datum_de(a.get("geliefert_am") or "")) if a["status"] == "erledigt"
               else None)
    return _blatt(art="Auftragsbestätigung", nummer=a["nummer"], titel=a.get("titel"), fd=fd, firma=t["firma"], ap=t["ap"],
                  infos=t["infos"], anrede=t["anrede"], einleitung=t["einleitung"], positionen=a["positionen"],
                  summen=a["summen"], gesamt_text="Gesamtbetrag", gesamt_cent=a["summe_cent"], hinweise=t["hinweise"],
                  stempel=stempel)


def mahnung(ms, m: dict, fd: dict) -> dict:
    from .mahnungen import BRIEF
    if m.get("alt"):                                    # vor LUNA verschickt: nur die erfassten Eckdaten + Original
        f = ms.kunden.firma(m["firma"]) or {}
        pos = [{"beschreibung": f"Rechnung {m['rechnung']}, fällig am {datum_de(m['faellig_am'])} – offener Betrag",
                "menge": "1", "einheit": "", "einzelpreis_cent": m["offen_cent"], "gesamt_cent": m["offen_cent"]}]
        if m.get("gebuehr_cent"):
            pos.append({"beschreibung": "Zinsen/Kosten laut Mahnung", "menge": "1", "einheit": "",
                        "einzelpreis_cent": m["gebuehr_cent"], "gesamt_cent": m["gebuehr_cent"]})
        return _blatt(art=BRIEF[m["stufe"]], nummer=m["nummer"], titel="vor LUNA verschickt", fd=fd, firma=f, ap=None,
                      infos=[("Datum", datum_de(m["datum"])), ("Rechnung", m["rechnung"]), ("Kundennummer", m["firma"]),
                             ("Zahlbar bis", datum_de(m["frist"]))], anrede="", einleitung="Diese Mahnung wurde vor LUNA "
                      "verschickt; erfasst sind die Eckdaten. Den Wortlaut zeigt das Original-PDF.", positionen=pos, summen=None,
                      gesamt_text="Gesamtbetrag", gesamt_cent=m["summe_cent"], hinweise=[], stempel=None,
                      extra={"original_pdf": bool(m.get("belege"))})
    t = ms.teile(m)
    stempel = (_stempel("blau", "GESENDET", datum_de(m["versendet_am"])) if m.get("versendet_am")
               and (m.get("mail") or {}).get("an") != "vor LUNA verschickt" else None)
    return _blatt(art=BRIEF[m["stufe"]], nummer=m["nummer"], titel="", fd=fd, firma=t["firma"], ap=t["ap"],
                  infos=t["infos"], anrede=t["anrede"], einleitung=t["einleitung"], positionen=t["positionen"],
                  summen=None, gesamt_text="Gesamtbetrag", gesamt_cent=m["summe_cent"], hinweise=t["hinweise"],
                  stempel=stempel)
