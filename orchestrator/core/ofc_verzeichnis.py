"""OFC_MITGLIEDER MV0/MV1: eigenes Mitgliederverzeichnis in LUNA (CEO 2026-11-26: „weg vom Google-Formular“).

- MV0 `import_vorschau`: was aus der Google-Tabelle uebernommen wuerde, mit Konflikten (doppelte Nummern, doppelte Namen,
  unklare Mitgliedschaft) -- schreibt nichts.
- MV1 `import_anwenden`: einmaliger Import nach Bestaetigung; doppelte Nummern loest der CEO (wer behaelt sie), die anderen
  bekommen die naechste freie Nummer (E3/E5). Ereignis `ofc_verzeichnis` je Person im Fanclub-Speicher (NAS, Backup).
  Bis zum Umschalten (MV3) lesen alle OFC-Funktionen weiter die Tabelle.
- `abgleich`: Tabelle <-> LUNA je Zeile und Feld, nur Zaehlungen und Feldnamen.
Keine KI; nur der CEO sieht die Daten.
"""
from __future__ import annotations

import re
import uuid
from collections import Counter

FELDER = ("nummer", "anrede", "vorname", "nachname", "email", "handy", "adresse", "geburtstag", "hsv_mitglied", "hsv_nr",
          "anderer_fanclub", "mitgliedschaft", "foerder_betrag", "vorstand", "beitrag", "seit", "naechste_zahlung", "kommentar",
          "anfrage_am")
MITGLIEDSCHAFTEN = {"gold": "Gold", "standard": "Standard", "foerder": "Förder"}
ABGLEICH_FELDER = ("nummer", "vorname", "nachname", "email", "mitgliedschaft")


def mitgliedschaft_aus_text(text: str) -> tuple[str, bool]:
    """Formulartext -> (gold|standard|foerder|'', vorstand). Beide Gold-Schreibweisen = gold (E2)."""
    t = (text or "").lower()
    vorstand = "vorstand" in t
    if "gold" in t:
        return "gold", vorstand
    if "standard" in t or "kostenfrei" in t:
        return "standard", vorstand
    if "förder" in t or "foerder" in t:
        return "foerder", vorstand
    return "", vorstand


def _person(p: dict) -> dict:
    """Zeile aus `ofc_mitglieder.lesen` -> Datensatz des Verzeichnisses (E1: alle Felder, aufgeraeumt)."""
    w = p.get("werte") or {}
    art, vorstand = mitgliedschaft_aus_text(w.get("mitgliedschaft") or p.get("mitgliedschaft", ""))
    d = {"nummer": (p.get("nummer") or "").strip(), "anrede": w.get("anrede", ""), "vorname": p.get("vorname", ""),
         "nachname": p.get("nachname", ""), "email": (w.get("email") or w.get("email_absender") or p.get("email") or "").strip(),
         "handy": w.get("handy", ""), "adresse": w.get("adresse", ""), "geburtstag": w.get("geburtstag", ""),
         "hsv_mitglied": w.get("hsv_mitglied", ""), "hsv_nr": w.get("hsv_nr", ""), "anderer_fanclub": w.get("anderer_fanclub", ""),
         "mitgliedschaft": art, "foerder_betrag": "", "vorstand": vorstand, "beitrag": p.get("beitrag", ""), "seit": p.get("seit", ""),
         "naechste_zahlung": p.get("naechste_zahlung", ""), "kommentar": p.get("kommentar", ""), "anfrage_am": p.get("eingang", "")}
    d["status"] = "mitglied" if d["nummer"] else "anfrage"
    d["zeile"] = p.get("zeile")
    return d


def _schluessel(d: dict) -> str:
    return re.sub(r"\s+", " ", f"{d.get('vorname', '')} {d.get('nachname', '')}".strip().casefold())


def import_vorschau(daten: dict | None, st: dict) -> dict:
    """MV0 Dry-Run: Personen aus der Tabelle, Mitgliedschaften nach E2, Konflikte. Schreibt nichts."""
    if not daten or not daten.get("ok"):
        return {"ok": False, "hinweis": "Mitgliederliste nicht lesbar."}
    personen = [_person(p) for p in (daten.get("mitglieder") or []) + (daten.get("anfragen") or [])]
    nrn = Counter(p["nummer"] for p in personen if p["nummer"])
    doppelt = {n: [{"zeile": p["zeile"], "name": f"{p['vorname']} {p['nachname']}".strip(), "email": p["email"]}
                   for p in personen if p["nummer"] == n] for n, c in nrn.items() if c > 1}
    namen = Counter(_schluessel(p) for p in personen)
    return {"ok": True, "schon_importiert": bool(st.get("verzeichnis")),
            "personen": len(personen), "mitglieder": sum(1 for p in personen if p["status"] == "mitglied"),
            "anfragen": sum(1 for p in personen if p["status"] == "anfrage"),
            "mitgliedschaften": dict(Counter(MITGLIEDSCHAFTEN.get(p["mitgliedschaft"], "unklar") for p in personen if p["status"] == "mitglied")),
            "vorstand": sum(1 for p in personen if p["vorstand"]),
            "ohne_email": sum(1 for p in personen if "@" not in p["email"]),
            "doppelte_nummern": doppelt,
            "doppelte_namen": sorted({f"{p['vorname']} {p['nachname']}".strip() for p in personen if namen[_schluessel(p)] > 1}),
            "unklar": [{"zeile": p["zeile"], "name": f"{p['vorname']} {p['nachname']}".strip()} for p in personen
                       if p["status"] == "mitglied" and not p["mitgliedschaft"]],
            "naechste_nummer": naechste_nummer([p["nummer"] for p in personen])}


def naechste_nummer(nummern) -> str:
    """Hoechste numerische Nummer + 1, vierstellig (E5)."""
    zahlen = [int(n) for n in nummern if str(n).strip().isdigit()]
    return str(max(zahlen, default=0) + 1).zfill(4)


def import_anwenden(store, daten: dict | None, behalten: dict | None, *, von: str = "") -> dict:
    """MV1: einmaliger Import. `behalten` = {doppelte Nummer: Zeile, die sie behaelt}. Nie doppelt."""
    st = store.stand()
    v = import_vorschau(daten, st)
    if not v["ok"]:
        return v
    if v["schon_importiert"]:
        return {"ok": False, "hinweis": "Das Verzeichnis ist schon übernommen – Änderungen jetzt direkt in LUNA (MV2)."}
    behalten = {str(k): int(z) for k, z in (behalten or {}).items() if str(z).lstrip("-").isdigit()}
    offen = [n for n, zeilen in v["doppelte_nummern"].items() if behalten.get(n) not in {z["zeile"] for z in zeilen}]
    if offen:
        return {"ok": False, "hinweis": "Bitte für jede doppelte Nummer wählen, wer sie behält: " + ", ".join(offen) + "."}
    personen = [_person(p) for p in (daten.get("mitglieder") or []) + (daten.get("anfragen") or [])]
    vergeben = {p["nummer"] for p in personen if p["nummer"]}
    neu_nr = {}
    for p in sorted(personen, key=lambda x: x["zeile"] or 0):
        if p["nummer"] in v["doppelte_nummern"] and behalten[p["nummer"]] != p["zeile"]:
            alt = p["nummer"]
            p["nummer"] = naechste_nummer(vergeben)
            vergeben.add(p["nummer"])
            neu_nr[p["zeile"]] = (alt, p["nummer"])
            p["nummer_alt"] = alt
            p["kommentar"] = (p["kommentar"] + " " if p["kommentar"] else "") + f"[LUNA-Import: Nummer {alt} war doppelt, neu {p['nummer']}]"
    for p in personen:
        store.erfassen("ofc_verzeichnis", {"id": "P-" + uuid.uuid4().hex[:10], **{k: p.get(k, "") for k in FELDER},
                                           "status": p["status"], "zeile": p["zeile"], "nummer_alt": p.get("nummer_alt", ""),
                                           "quelle": "import"}, von=von)
    return {"ok": True, "uebernommen": len(personen), "neue_nummern": [{"zeile": z, "alt": a, "neu": n} for z, (a, n) in neu_nr.items()]}


def abgleich(daten: dict | None, st: dict) -> dict:
    """Tabelle <-> LUNA je Tabellenzeile: Abweichungen je Feld (nur Zaehlungen + Zeilen)."""
    if not daten or not daten.get("ok"):
        return {"ok": False, "hinweis": "Mitgliederliste nicht lesbar."}
    luna = {p.get("zeile"): p for p in (st.get("verzeichnis") or {}).values() if p.get("quelle") == "import"}
    if not luna:
        return {"ok": True, "importiert": False}
    tab = {p["zeile"]: _person(p) for p in (daten.get("mitglieder") or []) + (daten.get("anfragen") or [])}
    je_feld: Counter = Counter()
    zeilen = []
    for z in sorted(set(tab) | set(luna), key=lambda x: x or 0):
        a, b = tab.get(z), luna.get(z)
        if not a or not b:
            je_feld["nur in " + ("LUNA" if b else "Tabelle")] += 1
            zeilen.append({"zeile": z, "felder": ["fehlt"]})
            continue
        diff = [f for f in ABGLEICH_FELDER if str(a.get(f) or "").strip() != str(b.get(f) or "").strip()
                and not (f == "nummer" and b.get("nummer_alt") and b["nummer_alt"] == a.get("nummer"))]   # bewusst geloester Konflikt
        if diff:
            je_feld.update(diff)
            zeilen.append({"zeile": z, "felder": diff})
    return {"ok": True, "importiert": True, "abweichungen": len(zeilen), "je_feld": dict(je_feld), "zeilen": zeilen[:50],
            "luna": len(luna), "tabelle": len(tab)}
