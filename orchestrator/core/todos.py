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


def _todo(id_, bereich, icon, titel, detail, act, act_id="", faellig="", heute="", erledigen=None) -> dict:
    return {"id": id_, "bereich": bereich, "icon": icon, "titel": titel, "detail": detail, "act": act, "act_id": act_id,
            "faellig": faellig, "dringend": bool(faellig) and faellig <= heute, "erledigen": erledigen}


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
                fae = f.get("faellig_am") or ""
                if ein or (fae and fae <= (heute + timedelta(days=3)).isoformat()):
                    out.append(_todo(f"bl-zahlung:{x['nummer']}", "Belege", "💸" if not ein else "💶",
                                     f"{'Geldeingang prüfen' if ein else 'Eingangsrechnung bezahlen'}: {x['nummer']}",
                                     f"{wer} · {eur(abs(f['betrag_cent'] - x.get('bezahlt_cent', 0)))} offen",
                                     "bl-detail", x["nummer"], fae, h))
        entwuerfe, rechnungen = RechnungStore._falte(e)
        for r in rechnungen.values():
            if r["status"] == "offen" and r.get("art") != "storno" and r.get("faellig_am", "9") < h:
                out.append(_todo(f"re-ueber:{r['nummer']}", "Rechnungen", "⚠️", f"Rechnung {r['nummer']} überfällig",
                                 f"{firmen.get(r['firma'], r['firma'])} · {eur(r['summe_cent'] - r['bezahlt_cent'])} offen; "
                                 "nachfassen oder Zahlung erfassen", "re-detail", r["nummer"], r["faellig_am"], h))
        for eid, x in entwuerfe.items():
            out.append(_todo(f"re-entwurf:{eid}", "Rechnungen", "✎", "Rechnungsentwurf festschreiben",
                             f"{firmen.get(x.get('firma'), x.get('firma', ''))} · {x.get('titel') or eid}", "re-detail", eid))
        berechnet = {r.get("auftrag") for r in rechnungen.values()
                     if r.get("auftrag") and r["status"] != "storniert" and r.get("art") != "storno"}
        berechnet |= {x.get("auftrag") for x in entwuerfe.values() if x.get("auftrag")}
        for a in AuftragBuch._falte(e).values():
            if a["status"] == "erledigt" and a["nummer"] not in berechnet:
                out.append(_todo(f"ab-rechnung:{a['nummer']}", "Aufträge", "🧾", f"Rechnung schreiben: {a['nummer']}",
                                 f"{firmen.get(a['firma'], a['firma'])} · Leistung erledigt, noch keine Rechnung",
                                 "ab-detail", a["nummer"]))
    return sorted(out, key=lambda t: (not t["dringend"], t["faellig"] or "9999", t["titel"]))
