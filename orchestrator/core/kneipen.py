"""Kneipen als Kunden: Listung „Spieltags-Partner" in der Fan-App (MONETARISIERUNG_ROADMAP.md, Etappe M8, Saeule S3b).

- **Verkauf** ausserhalb der App ueber den normalen Weg Angebot -> Auftrag -> Rechnung mit den Katalogpositionen
  `kneipe_monat` (je Monat, Menge = Monate) und `kneipe_saison` (Saisonpaket). Der Grundeintrag in der App ist gratis und
  wird nicht berechnet. In der App gibt es keinen Kaufknopf (Apple 3.1.3(g)).
- **Listungen** werden nicht gesondert gespeichert, sondern aus den festgeschriebenen Rechnungen abgeleitet (eine Quelle der
  Wahrheit; Storno nimmt die Listung automatisch heraus). Zeitraum = Leistungszeitraum der Rechnung; fehlt „Leistung bis",
  gilt Leistung von (sonst Rechnungsdatum) + Monate bzw. beim Saisonpaket der 30.06. am Saisonende.
- **Erinnerungen** (To-dos mit Telegram): nach dem Festschreiben „Enddatum in der App eintragen" (LUNA aendert die App nie,
  `listed_until` setzt der Betreiber im Admin-Bereich) und 14 Tage vor Ablauf „Verlaengerung anbieten". Je Rechnung genau
  einmal (Quelle `Kneipe:<Nummer>:app|verlaengern`).
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

KATALOG = {"kneipe_monat": "monat", "kneipe_saison": "saison"}
TEXT = re.compile(r"spieltags-partner|kneipen-listung", re.I)
SAISON_ENDE = (6, 30)
VORLAUF_TAGE = 14            # Verlaengerung anbieten
AUSLAUFEND_TAGE = 21         # Anzeige „laeuft aus"


def _plus_monate(d: date, n: int) -> date:
    m = d.month - 1 + n
    j, m = d.year + m // 12, m % 12 + 1
    return date(j, m, min(d.day, calendar.monthrange(j, m)[1]))


def _menge(p: dict) -> int:
    try:
        return max(1, int(float(str(p.get("menge") or "1").replace(",", "."))))
    except ValueError:
        return 1


def art(p: dict) -> str:
    """Kneipen-Position? -> 'monat' | 'saison' | ''."""
    if p.get("spaeter_am"):
        return ""
    a = KATALOG.get(str(p.get("katalog_id") or ""))
    if a:
        return a
    if TEXT.search(str(p.get("beschreibung") or "")):
        return "saison" if re.search(r"saison", str(p.get("beschreibung") or ""), re.I) else "monat"
    return ""


def listung(r: dict) -> dict | None:
    """Listung aus einer festgeschriebenen Rechnung (None, wenn keine Kneipen-Position, Storno oder storniert)."""
    if r.get("art") == "storno" or r.get("status") in ("storniert", "storno"):
        return None
    pos = [(art(p), p) for p in r.get("positionen") or []]
    pos = [(a, p) for a, p in pos if a]
    if not pos:
        return None
    von = date.fromisoformat((r.get("leistung_von") or r.get("rechnungsdatum"))[:10])
    if r.get("leistung_bis"):
        bis = date.fromisoformat(r["leistung_bis"][:10])
    else:
        enden = []
        for a, p in pos:
            if a == "saison":
                j = von.year if (von.month, von.day) <= SAISON_ENDE else von.year + 1
                enden.append(date(j, *SAISON_ENDE))
            else:
                enden.append(_plus_monate(von, _menge(p)) - timedelta(days=1))
        bis = max(enden)
    return {"rechnung": r["nummer"], "firma": r.get("firma", ""), "von": von.isoformat(), "bis": bis.isoformat(),
            "pakete": sorted({a for a, _ in pos}), "summe_cent": r.get("summe_cent", 0),
            "bezahlt": r.get("status") == "bezahlt", "leistung_bis_fehlte": not r.get("leistung_bis")}


def uebersicht(rechnungen: dict, firmen: dict[str, str], heute: date) -> dict:
    """Je Kneipe die juengste Listung mit Status aktiv / laeuft aus / kommend / abgelaufen, dazu alle Listungen."""
    alle = [x for r in rechnungen.values() if (x := listung(r))]
    je_firma: dict[str, list] = {}
    for x in sorted(alle, key=lambda x: (x["bis"], x["rechnung"])):
        je_firma.setdefault(x["firma"], []).append(x)
    kneipen = []
    h = heute.isoformat()
    for f, xs in je_firma.items():
        letzte = xs[-1]
        rest = (date.fromisoformat(letzte["bis"]) - heute).days
        if letzte["bis"] < h:
            status = "abgelaufen"
        elif all(x["von"] > h for x in xs):
            status = "kommend"
        else:
            status = "laeuft_aus" if rest <= AUSLAUFEND_TAGE else "aktiv"
        kneipen.append({"firma": f, "name": firmen.get(f, f), "status": status, "bis": letzte["bis"], "tage_rest": rest,
                        "listungen": list(reversed(xs))})
    rang = {"laeuft_aus": 0, "aktiv": 1, "kommend": 2, "abgelaufen": 3}
    kneipen.sort(key=lambda k: (rang[k["status"]], k["bis"]))
    return {"heute": h, "kneipen": kneipen,
            "aktiv": sum(k["status"] in ("aktiv", "laeuft_aus") for k in kneipen),
            "laeuft_aus": sum(k["status"] == "laeuft_aus" for k in kneipen),
            "hinweis": "Grundeintrag in der App ist gratis; hier stehen nur bezahlte Listungen (Spieltags-Partner). "
                       "Das Enddatum trägt der Betreiber im Admin-Bereich der App ein – LUNA ändert die App nicht."}


def aufgaben(store, r: dict, name: str, heute: date, *, von: str = "") -> list[dict]:
    """To-dos zur Listung einer gerade festgeschriebenen Rechnung (je Rechnung genau einmal)."""
    x = listung(r)
    if not x:
        return []
    schon = {a.get("quelle") for liste in store.liste().values() for a in liste}
    bis_de = f"{x['bis'][8:10]}.{x['bis'][5:7]}.{x['bis'][:4]}"
    neu = []
    q = f"Kneipe:{x['rechnung']}:app"
    if q not in schon:
        neu.append(store.anlegen(
            f"Kneipe in der App bis {bis_de} listen: {name}", faellig=max(heute.isoformat(), x["von"]), kunde=x["firma"],
            notiz=(f"Rechnung {x['rechnung']} ({', '.join('Saisonpaket' if p == 'saison' else 'Monat' for p in x['pakete'])}). "
                   f"Im Admin-Bereich der App bei der Kneipe „Spieltags-Partner“ mit Enddatum {bis_de} setzen."),
            quelle=q, von=von))
    q = f"Kneipe:{x['rechnung']}:verlaengern"
    if q not in schon:
        faellig = max(heute, date.fromisoformat(x["bis"]) - timedelta(days=VORLAUF_TAGE))
        neu.append(store.anlegen(
            f"Verlängerung anbieten: {name} (Listung bis {bis_de})", faellig=faellig.isoformat(), kunde=x["firma"],
            notiz=f"Die bezahlte Listung aus {x['rechnung']} endet am {bis_de}. Verlängerung (Monat oder Saisonpaket) "
                  "anbieten – sonst bleibt nur der Gratis-Grundeintrag.",
            quelle=q, von=von))
    return neu
