"""Offene To-dos fuer die Hauptseite von LUNA-OS (CEO 2026-09-28): der Tagesbetrieb an einer Stelle -- Antraege/Freigaben
(Weiterentwicklung) bewusst nicht.

Die Geschaefts-To-dos werden **abgeleitet** (aus der Hash-Kette gefaltet), nicht gespeichert: ein To-do verschwindet,
sobald die eigentliche Arbeit getan ist (Beleg gebucht, Rechnung bezahlt, Angebot angenommen ...). Dabei raeumt
`erinnerungen.erledigte_entfernen` die zugehoerigen Kalendertermine ab. Wo keine Dateneingabe noetig ist, gibt es einen
direkten Erledigt-Knopf (`erledigen`: POST-Pfad), z. B. „Nachgefasst“ beim Angebot.
Weitere Quellen (CRM-To-dos, Antraege, Reels) haengt die Web-App an (`channels/web/app.py`, `/api/todos`).
"""
from __future__ import annotations

from datetime import date, timedelta

from .angebote import AngebotStore
from .beauftragung import AuftragBuch
from .beleg_pdf import eur
from .buchhaltung import Buchhaltung, jetzt
from .eingangsbelege import EingangStore
from .rechnungen import RechnungStore


def cfo_meldung(todos: list[dict]) -> str:
    """Tages-Meldung des CFO (Telegram): nur Finanz-Punkte, die faellig sind; leer = nichts zu melden."""
    f = [t for t in todos if t["dringend"] and t["bereich"] in ("Belege", "Rechnungen", "Aufträge", "Finanzen")]
    if not f:
        return ""
    zeilen = [f"• {t['titel']}" for t in f[:8]] + ([f"• … und {len(f) - 8} weitere"] if len(f) > 8 else [])
    return f"📊 CFO-Finanzcheck: {len(f)} Punkt(e) brauchen dich\n" + "\n".join(zeilen) + "\n→ LUNA-OS, Hauptseite „Zu erledigen“"


def _todo(id_, bereich, icon, titel, detail, act, act_id="", faellig="", heute="", erledigen=None) -> dict:
    return {"id": id_, "bereich": bereich, "icon": icon, "titel": titel, "detail": detail, "act": act, "act_id": act_id,
            "faellig": faellig, "dringend": bool(faellig) and faellig <= heute, "erledigen": erledigen}


QUITTUNG = "finanz_hinweis_quittiert"          # „✓ Abgeglichen“ / „✓ Kommt diesen Monat nicht“


def _monat(d: date, minus: int = 0) -> str:
    j, m = d.year, d.month - minus
    while m < 1:
        j, m = j - 1, m + 12
    return f"{j}-{m:02d}"


def beginn_buchhaltung(e: list[dict]) -> str:
    """Erster Monat mit Finanzdaten (JJJJ-MM): fruehestes Beleg-/Zahlungsdatum, nicht der Erfassungszeitpunkt --
    nachgetragene Belege frueherer Monate sollen den Monatsabgleich fuer diese Monate ausloesen."""
    monate = []
    for x in e:
        if not str(x["typ"]).startswith(("rechnung_", "eingang_", "eigenbeleg_")):
            continue
        d = x["daten"]
        monate.append(x["ts"][:7])
        for k in ("datum", "rechnungsdatum"):
            if len(str(d.get(k) or "")) >= 7:
                monate.append(str(d[k])[:7])
        if len(str((d.get("felder") or {}).get("rechnungsdatum") or "")) >= 7:
            monate.append(d["felder"]["rechnungsdatum"][:7])
    return min(monate) if monate else ""


def finanzcheck(e: list[dict], heute: date, *, rechnungen: dict | None = None) -> list[dict]:
    """CFO-Finanzcheck (Vollstaendigkeit): Monatsabgleich mit dem Kontoauszug, fehlende wiederkehrende Posten,
    Kleinunternehmer-Grenze. Nur melden -- nie buchen."""
    from .eigenbelege import EigenbelegStore
    h = heute.isoformat()
    quittiert = {x["daten"].get("schluessel") for x in e if x["typ"] == QUITTUNG}
    out: list[dict] = []
    finanz = [x for x in e if str(x["typ"]).startswith(("rechnung_", "eingang_", "eigenbeleg_"))]
    # 1) Monatsabgleich: jeder abgeschlossene Monat seit Beginn der Buchhaltung (hoechstens die letzten 3)
    if finanz:
        start = beginn_buchhaltung(e)
        for i in (3, 2, 1):
            mon = _monat(heute, i)
            if mon < start or f"monat:{mon}" in quittiert:
                continue
            anz = {"ein": 0, "aus": 0}
            for x in finanz:
                d = x["daten"]
                if x["typ"] == "rechnung_bezahlt" and d.get("datum", "")[:7] == mon:
                    anz["ein"] += 1
                elif x["typ"] == "eingang_bezahlt" and d.get("datum", "")[:7] == mon:
                    anz["aus"] += 1
                elif x["typ"] == "eigenbeleg_angelegt" and d.get("datum", "")[:7] == mon:
                    anz["ein" if d.get("art") == "einnahme" else "aus"] += 1
            out.append(_todo(f"monat:{mon}", "Finanzen", "🏦", f"Kontoauszug {mon[5:]}/{mon[:4]} abgleichen",
                             f"erfasst: {anz['ein']} Zahlungseingang/-eingänge, {anz['aus']} Zahlung(en) · fehlt etwas? "
                             "Fehlendes als Beleg hochladen oder ohne Beleg buchen", "go:finanzen:journal", "",
                             f"{_monat(heute, i - 1)}-03", h, {"pfad": "/api/finanzen/hinweis-quittieren",
                                                               "schluessel": f"monat:{mon}", "label": "✓ Abgeglichen"}))
    # 2) wiederkehrende Posten: in beiden Vormonaten da, in diesem Monat (ab dem 10.) nicht
    if heute.day >= 10:
        je_monat: dict[str, set] = {}
        for x in EingangStore._falte(e).values():
            f = x.get("felder") or {}
            if x["status"] == "gebucht" and f.get("lieferant"):
                je_monat.setdefault(str(f.get("rechnungsdatum", ""))[:7], set()).add(
                    ("einnahme" if f.get("art") == "einnahme" else "ausgabe", f["lieferant"].strip()))
        for x in EigenbelegStore._falte(e).values():
            if x["status"] == "gebucht" and x.get("gegenpartei"):
                je_monat.setdefault(x["datum"][:7], set()).add((x["art"], x["gegenpartei"].strip()))
        m0, m1, m2 = _monat(heute), _monat(heute, 1), _monat(heute, 2)
        dieser = {w.lower() for _, w in je_monat.get(m0, set())}
        for art, wer in sorted(je_monat.get(m1, set())):
            if wer.lower() in {w.lower() for _, w in je_monat.get(m2, set())} and wer.lower() not in dieser:
                sl = f"fehlt:{wer.lower()}:{m0}"
                if sl not in quittiert:
                    out.append(_todo(sl, "Finanzen", "🔁", f"{wer}: {'Einnahme' if art == 'einnahme' else 'Rechnung'} "
                                     f"für {m0[5:]}/{m0[:4]} fehlt?", "kam in den beiden Vormonaten jeweils · hochladen, an "
                                     "LUNA weiterleiten oder bestätigen, dass diesen Monat nichts kommt", "go:belege:alle",
                                     "", f"{m0}-10", h, {"pfad": "/api/finanzen/hinweis-quittieren", "schluessel": sl,
                                                          "label": "✓ Kommt diesen Monat nicht"}))
    # 2b) Basiszinssatz fuer das naechste Halbjahr fehlt -> Mahnungen wuerden sonst nicht rechnen (Etappe 10)
    from .mahnungen import BASISZINS_BEKANNT_BIS
    grenze = date.fromisoformat(BASISZINS_BEKANNT_BIS)
    if heute >= grenze - timedelta(days=10):
        out.append(_todo(f"basiszins:{BASISZINS_BEKANNT_BIS}", "Finanzen", "📈",
                         f"Basiszinssatz ab {(grenze + timedelta(days=1)).strftime('%d.%m.%Y')} nachtragen",
                         "die Bundesbank veröffentlicht ihn Ende Dezember/Juni -- ohne ihn rechnet LUNA keine Verzugszinsen "
                         "(Mahnungen gesperrt); Claude Code/HoA trägt ihn in core/mahnungen.py ein", "go:finanzen", "",
                         (grenze + timedelta(days=1)).isoformat(), h))
    # 3) Kleinunternehmer-Grenze ab 80 %
    from .eigenbelege import einnahmen_cent
    rechnungen = rechnungen if rechnungen is not None else RechnungStore._falte(e)[1]
    ums = einnahmen_cent(e, heute.year) + sum(r["summe_cent"] for r in rechnungen.values()
                                              if str(r.get("rechnungsdatum", ""))[:4] == str(heute.year))
    from .rechnungen import GRENZE_LAUFEND, WARNSCHWELLE
    if ums >= GRENZE_LAUFEND * WARNSCHWELLE:
        out.append(_todo(f"ku-grenze:{heute.year}", "Finanzen", "⚠️",
                         f"Kleinunternehmer-Grenze: {round(ums / GRENZE_LAUFEND * 100)} % erreicht",
                         f"{eur(ums)} von 100.000 € · über der Grenze wird sofort Umsatzsteuer fällig; Steuerberater "
                         "einbinden", "go:finanzen", "", h, h))
    return out


def geschaefts_todos(bh: Buchhaltung, kunden, *, finanzen: bool = True, crm: bool = True,
                     heute: date | None = None) -> list[dict]:
    heute = heute or jetzt().date()
    h = heute.isoformat()
    e = bh.eintraege()
    firmen = {f["nummer"]: f["name"] for f in kunden.firmen()}
    out: list[dict] = []
    if crm:
        for a in AngebotStore._falte(e).values():
            if a["status"] != "versendet":
                continue
            name = firmen.get(a["firma"], a["firma"])
            if a.get("gueltig_bis") and a["gueltig_bis"] < h:
                out.append(_todo(f"an-ablauf:{a['nummer']}", "Angebote", "⌛", f"Angebot {a['nummer']} abgelaufen",
                                 f"{name} · angenommen, abgelehnt oder neu anbieten?", "an-detail", a["nummer"],
                                 a["gueltig_bis"], h))
                continue
            if a.get("nachgefasst_am"):
                continue
            nf = next((t.get("datum") for t in a.get("versendet_termine") or [] if "nachfassen" in str(t.get("titel", ""))), "")
            if not nf and a.get("versendet_am"):
                nf = (date.fromisoformat(a["versendet_am"][:10]) + timedelta(days=int(a.get("nachfassen_tage") or 7))).isoformat()
            if nf and nf <= h:
                out.append(_todo(f"an-nachfassen:{a['nummer']}", "Angebote", "📞", f"Angebot {a['nummer']} nachfassen",
                                 f"{name} · {a.get('titel') or ''}".strip(" ·"), "an-detail", a["nummer"], nf, h,
                                 {"pfad": f"/api/crm/angebote/{a['nummer']}/nachgefasst", "label": "✓ Nachgefasst"}))
    if finanzen:
        for x in EingangStore._falte(e).values():
            v, f = x.get("vorschlag") or {}, x.get("felder") or {}
            wer = f.get("lieferant") or v.get("lieferant") or x.get("dateiname", "")
            if x["status"] == "zu_pruefen":
                if v.get("waehrung") and v["waehrung"] != "EUR":
                    out.append(_todo(f"bl-euro:{x['nummer']}", "Belege", "💶", f"Euro-Betrag eintragen: {x['nummer']}",
                                     f"{wer} · {v.get('betrag_fremd', '?')} {v['waehrung']} laut Beleg, Euro-Betrag vom "
                                     "Kontoauszug eintragen und buchen", "bl-detail", x["nummer"],
                                     (x.get("erinnerung") or {}).get("datum", ""), h))
                else:
                    out.append(_todo(f"bl-pruefen:{x['nummer']}", "Belege", "📥", f"Beleg {x['nummer']} prüfen und buchen",
                                     wer, "bl-detail", x["nummer"],
                                     (date.fromisoformat(x["eingegangen"][:10]) + timedelta(days=3)).isoformat(), h))
            elif x["status"] == "gebucht" and f.get("betrag_cent") and x.get("bezahlt_cent", 0) != f["betrag_cent"]:
                ein = f.get("art") == "einnahme"
                rd = f.get("rechnungsdatum") or x["eingegangen"][:10]
                # CFO-Finanzcheck: Gutschrift nach 14 Tagen ohne Geldeingang, Ausgabe ohne Faelligkeit nach 30 Tagen
                fae = f.get("faellig_am") or (date.fromisoformat(rd) + timedelta(days=14 if ein else 30)).isoformat()
                if ein or fae <= (heute + timedelta(days=3)).isoformat():
                    out.append(_todo(f"bl-zahlung:{x['nummer']}", "Belege", "💸" if not ein else "💶",
                                     f"{'Geldeingang prüfen' if ein else 'Eingangsrechnung bezahlen'}: {x['nummer']}",
                                     f"{wer} · {eur(abs(f['betrag_cent'] - x.get('bezahlt_cent', 0)))} offen",
                                     "bl-detail", x["nummer"], fae, h))
        entwuerfe, rechnungen = RechnungStore._falte(e)
        from .mahnungen import MahnStore, STUFEN
        mahn: dict[str, list] = {}
        for m in MahnStore._falte(e).values():
            mahn.setdefault(m["rechnung"], []).append(m)
        for r in rechnungen.values():
            if (r["status"] == "offen" and r.get("art") != "storno" and r.get("ware_cent")   # Etappe 12: Barter-Ware
                    and not r.get("ware_erhalten")):
                out.append(_todo(f"re-ware:{r['nummer']}", "Rechnungen", "📦",
                                 f"Ware zu {r['nummer']} erhalten?", f"{firmen.get(r['firma'], r['firma'])} · "
                                 f"{(r.get('ware') or {}).get('text', '')} ({eur(r['ware_cent'])}) · „Ware erhalten“ "
                                 "erfassen oder nachfordern", "re-detail", r["nummer"], r.get("faellig_am", ""), h))
            if (r["status"] == "offen" and r.get("art") != "storno" and r.get("faellig_am", "9") < h
                    and r["geld_cent"] - r["bezahlt_cent"] > 0):
                wer = f"{firmen.get(r['firma'], r['firma'])} · {eur(r['geld_cent'] - r['bezahlt_cent'])} offen"
                ms = sorted(mahn.get(r["nummer"], []), key=lambda m: m["stufe"])
                if not ms:                                   # Etappe 10: naechster Schritt im Mahnverfahren
                    t = (f"Rechnung {r['nummer']} überfällig", f"{wer}; 1. Mahnung erstellen oder Zahlung erfassen", r["faellig_am"])
                elif not ms[-1].get("versendet_am"):
                    t = (f"{STUFEN[ms[-1]['stufe']]} {ms[-1]['nummer']} senden", wer, h)
                elif ms[-1]["frist"] >= h:
                    t = (f"{STUFEN[ms[-1]['stufe']]} zu {r['nummer']} läuft", f"{wer}; Frist bis {ms[-1]['frist'][8:10]}."
                         f"{ms[-1]['frist'][5:7]}.", ms[-1]["frist"])
                elif ms[-1]["stufe"] < 3:
                    t = (f"Frist der {STUFEN[ms[-1]['stufe']]} zu {r['nummer']} abgelaufen",
                         f"{wer}; LUNA fragt per Telegram nach der {STUFEN[ms[-1]['stufe'] + 1]}", h)
                else:
                    t = (f"Letzte Mahnung zu {r['nummer']} abgelaufen", f"{wer}; Mahnbescheid oder Inkasso prüfen", h)
                out.append(_todo(f"re-ueber:{r['nummer']}", "Rechnungen", "⚠️", t[0], t[1], "re-detail", r["nummer"], t[2], h))
        for eid, x in entwuerfe.items():
            out.append(_todo(f"re-entwurf:{eid}", "Rechnungen", "✎", "Rechnungsentwurf festschreiben",
                             f"{firmen.get(x.get('firma'), x.get('firma', ''))} · {x.get('titel') or eid}", "re-detail", eid,
                             (date.fromisoformat(x["angelegt"][:10]) + timedelta(days=7)).isoformat(), h))
        berechnet = {r.get("auftrag") for r in rechnungen.values()
                     if r.get("auftrag") and r["status"] != "storniert" and r.get("art") != "storno"}
        berechnet |= {x.get("auftrag") for x in entwuerfe.values() if x.get("auftrag")}
        for a in AuftragBuch._falte(e).values():
            if a["status"] == "erledigt" and a["nummer"] not in berechnet:
                out.append(_todo(f"ab-rechnung:{a['nummer']}", "Aufträge", "🧾", f"Rechnung schreiben: {a['nummer']}",
                                 f"{firmen.get(a['firma'], a['firma'])} · Leistung erledigt, noch keine Rechnung",
                                 "ab-detail", a["nummer"],
                                 (date.fromisoformat(str(a.get("erledigt_am") or h)[:10]) + timedelta(days=7)).isoformat(), h))
        out += finanzcheck(e, heute, rechnungen=rechnungen)
    return sorted(out, key=lambda t: (not t["dringend"], t["faellig"] or "9999", t["titel"]))
