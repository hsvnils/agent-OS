"""Follower und Reichweiten je Plattform mit Verlauf (MONETARISIERUNG_ROADMAP.md, Etappe M3).

- **Speicher** `reichweite/log.jsonl` (NAS, append-only, gesichert): je Eintrag Plattform, Woche (Montag), Werte,
  Quelle (`hand`, `csv`, `api`), wer. Spaetere Werte derselben Woche und Metrik gelten; frueheres bleibt als Verlauf.
  `entfernt` nimmt eine Woche einer Plattform zurueck.
- **Metriken:** Follower (Stand am Wochenende) und Neue Follower (Netto-Zuwachs der Woche), Reichweite, Aufrufe,
  Interaktionen, Shares, Saves, Profilbesuche, Link-Klicks, Beitraege (je Woche); Reichweite 28 Tage (Stand, Instagram
  automatisch).
- **Wege:** Instagram automatisch (Tageslauf montags, eigenes Konto, vorhandener Zugang); Facebook/TikTok/YouTube per
  CSV-Export mit Vorschau und Spaltenzuordnung (erst pruefen, dann speichern) oder von Hand.
- **Bruchmarke Meta:** Seit 15.06.2026 liefert Meta `views` statt `impressions`; Reichweite/Aufrufe von Instagram und
  Facebook vor diesem Datum sind nicht direkt vergleichbar und werden markiert.
- Tageswerte der Reichweite lassen sich nicht zur Woche addieren (dieselbe Person zaehlt an mehreren Tagen) -- aus
  Tages-CSVs wird Reichweite deshalb nicht uebernommen; Wochenwert bitte von Hand.

Keine Zugangsdaten der Plattformen werden hier gespeichert. Neue Schnittstellen (z. B. Facebook-Seite) nur mit
CISO-Freigabe (AGENTS.md 5.7).
"""
from __future__ import annotations

import csv
import io
import json
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

PLATTFORMEN = {"instagram": "Instagram", "facebook": "Facebook", "tiktok": "TikTok", "youtube": "YouTube"}
METRIKEN = {                      # schluessel -> (Anzeige, Art: stand = Stand am Wochenende, woche = Summe der Woche)
    "follower": ("Follower", "stand"),
    "follower_neu": ("Neue Follower (netto)", "woche"),
    "reichweite": ("Reichweite", "woche"),
    "reichweite_28t": ("Reichweite 28 Tage", "stand"),
    "aufrufe": ("Aufrufe", "woche"),
    "interaktionen": ("Interaktionen", "woche"),
    "shares": ("Shares/Sends", "woche"),
    "saves": ("Saves", "woche"),
    "profilbesuche": ("Profilbesuche", "woche"),
    "link_klicks": ("Link-Klicks", "woche"),
    "beitraege": ("Beiträge", "woche"),
    "beitraege_kurz": ("davon Reels/Shorts", "woche"),          # M4 Posting-Rhythmus
    "beitraege_lang": ("davon über 1 Minute/Langvideo", "woche"),
}
META_BRUCH = "2026-06-15"
QUELLEN = ("hand", "csv", "api")

# Spaltennamen in Exporten (Kleinbuchstaben, ohne Sonderzeichen) -> Metrik. Business Suite, TikTok Studio, YouTube Studio
# (de/en). Die Vorschau zeigt die Zuordnung; der Mensch kann sie aendern, bevor gespeichert wird.
SPALTEN = [
    (r"^(datum|date|tag|day|zeitraum)$", "_datum"),
    (r"(neue follower|new followers|abonnenten gewonnen|subscribers gained|follows|netto.?follower|net followers|abonnenten$|subscribers$)", "follower_neu"),
    (r"(follower gesamt|total followers|followers?$|fans$|gesamtzahl.*follower)", "follower"),
    (r"(erreichte konten|accounts reached|^reichweite|^reach)", "reichweite"),
    (r"(profilaufrufe|profilbesuche|profile views|profile visits)", "profilbesuche"),   # vor „views“
    (r"(link.?klicks|link clicks|website.?klicks)", "link_klicks"),
    (r"(aufrufe|views|impressions|impressionen|wiedergaben|video views|videoaufrufe)", "aufrufe"),
    (r"(interaktionen|interactions|engagements?$|beitragsinteraktionen)", "interaktionen"),
    (r"(shares|geteilt|teilen|sends)", "shares"),
    (r"(saves|gespeichert)", "saves"),
]


def montag(d: date | str) -> str:
    d = date.fromisoformat(str(d)[:10]) if not isinstance(d, date) else d
    return (d - timedelta(days=d.weekday())).isoformat()


def _zahl(x) -> int | None:
    s = str(x if x is not None else "").strip().replace(" ", "").replace(" ", "")
    if s in ("", "-", "–", "n/a", "N/A"):
        return None
    s = s.replace("%", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):          # 1.234 oder 1.234,5 (deutsch)
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):        # 1,234 (englisch)
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return round(float(s))
    except ValueError:
        return None


def _datum(x) -> str | None:
    s = str(x or "").strip().strip('"')
    for f in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s[:12].strip(), f).date().isoformat()
        except ValueError:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)                      # ISO mit Uhrzeit
    return m.group(1) if m else None


def _norm(k: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w%. -]", " ", (k or "").lower())).strip()


def spalte_erkennen(name: str) -> str:
    n = _norm(name)
    for muster, metrik in SPALTEN:
        if re.search(muster, n):
            return metrik
    return ""


def _trenner(zeilen: list[str]) -> str:
    """Trennzeichen = das Zeichen, das in den meisten Zeilen gleich oft (und mindestens einmal) vorkommt -- robust gegen
    Titelzeilen ueber der Kopfzeile und Dezimalkommas in Semikolon-Dateien."""
    from collections import Counter
    best, wertung = ",", (0, 0)
    for t in ("\t", ";", ","):
        anz = [z.count(t) for z in zeilen if z.strip()]
        haeufig = Counter(a for a in anz if a > 0).most_common(1)
        if haeufig and (haeufig[0][1], haeufig[0][0]) > wertung:
            best, wertung = t, (haeufig[0][1], haeufig[0][0])
    return best


def csv_lesen(roh: bytes) -> tuple[list[str], list[list[str]]]:
    """CSV beliebiger Herkunft -> (Kopfzeile, Zeilen). Erkennt UTF-8/UTF-16, Trennzeichen und Titelzeilen ueber der
    eigentlichen Kopfzeile (die erste Zeile mit einer Datumsspalte)."""
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = roh.decode(enc)
            if "\x00" in text:
                continue
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Datei nicht lesbar (Kodierung).")
    trenner = _trenner(text.splitlines()[:30])
    zeilen = [z for z in csv.reader(io.StringIO(text), delimiter=trenner) if any(c.strip() for c in z)]
    for i, z in enumerate(zeilen[:15]):
        if any(spalte_erkennen(c) == "_datum" for c in z):
            return [c.strip() for c in z], zeilen[i + 1:]
    raise ValueError("Keine Kopfzeile mit Datum gefunden -- bitte den Export mit Tageswerten (Datum je Zeile) nehmen.")


def import_vorschau(roh: bytes, zuordnung: dict[str, str] | None = None) -> dict:
    """Trockenlauf: CSV -> Wochenwerte, ohne zu speichern. `zuordnung` = {Spaltenname: Metrik oder ""}."""
    kopf, zeilen = csv_lesen(roh)
    auto = {k: spalte_erkennen(k) for k in kopf}
    zu = {k: (zuordnung or {}).get(k, auto[k]) for k in kopf}
    datum_sp = next((k for k, m in zu.items() if m == "_datum"), "")
    if not datum_sp:
        raise ValueError("Bitte eine Datumsspalte zuordnen.")
    for k, m in zu.items():
        if m not in ("", "_datum") and m not in METRIKEN:
            raise ValueError(f"Unbekannte Metrik fuer Spalte „{k}“.")
    tage: dict[str, dict] = {}
    for z in zeilen:
        werte = dict(zip(kopf, z))
        d = _datum(werte.get(datum_sp))
        if not d:
            continue
        t = tage.setdefault(d, {})
        for k, m in zu.items():
            if m and m != "_datum" and _zahl(werte.get(k)) is not None:
                t[m] = t.get(m, 0) + _zahl(werte.get(k))
    if not tage:
        raise ValueError("Keine Zeile mit gueltigem Datum gefunden.")
    daten = sorted(tage)
    abstand = min((date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(daten, daten[1:])) if len(daten) > 1 else 7
    taeglich = abstand < 7
    wochen: dict[str, dict] = {}
    hinweise = []
    for d in daten:
        w = wochen.setdefault(montag(d), {"woche": montag(d), "tage": 0, "werte": {}})
        w["tage"] += 1
        for m, v in tage[d].items():
            if METRIKEN[m][1] == "stand":
                w["werte"][m] = v                                  # letzter Tag der Woche gilt
            elif m == "reichweite" and taeglich:
                continue                                           # Tagesreichweiten nicht addierbar
            else:
                w["werte"][m] = w["werte"].get(m, 0) + v
    if taeglich and "reichweite" in zu.values():
        hinweise.append("Reichweite aus Tageswerten wird nicht uebernommen (nicht addierbar) -- Wochenwert bitte von Hand.")
    liste = sorted(wochen.values(), key=lambda w: w["woche"])
    for w in liste:
        w["vollstaendig"] = not taeglich or w["tage"] >= 7
    if taeglich and liste and not liste[0]["vollstaendig"]:
        hinweise.append("Die erste Woche ist im Export nicht vollstaendig -- Summen gelten nur fuer die enthaltenen Tage.")
    return {"spalten": [{"name": k, "erkannt": auto[k], "zuordnung": zu[k]} for k in kopf],
            "taeglich": taeglich, "von": daten[0], "bis": daten[-1], "wochen": liste, "hinweise": hinweise}


class Reichweite:
    def __init__(self, pfad: Path | str):
        self.pfad = Path(pfad)
        self._lock = threading.Lock()

    def _ereignisse(self) -> list[dict]:
        try:
            return [json.loads(z) for z in self.pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
        except FileNotFoundError:
            return []

    def _schreibe(self, e: dict) -> None:
        e = {"ts": datetime.now().isoformat(timespec="seconds")} | e
        with self._lock:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # -- Schreiben ----------------------------------------------------------------------------------------------------
    def erfassen(self, plattform: str, woche: str, werte: dict, *, quelle: str = "hand", notiz: str = "",
                 von: str = "") -> dict:
        if plattform not in PLATTFORMEN:
            raise ValueError("Unbekannte Plattform.")
        if quelle not in QUELLEN:
            raise ValueError("Unbekannte Quelle.")
        try:
            w = montag(woche)
        except ValueError:
            raise ValueError("Woche bitte als Datum (JJJJ-MM-TT).") from None
        if w > montag(date.today()):
            raise ValueError("Die Woche liegt in der Zukunft.")
        sauber = {}
        for k, v in (werte or {}).items():
            if k not in METRIKEN:
                raise ValueError(f"Unbekannte Metrik: {k}")
            if v in (None, ""):
                continue
            z = _zahl(v)
            if z is None or (k != "follower_neu" and z < 0) or abs(z) > 10_000_000_000:
                raise ValueError(f"{METRIKEN[k][0]}: bitte eine Zahl.")
            sauber[k] = z
        if not sauber:
            raise ValueError("Mindestens einen Wert eintragen.")
        self._schreibe({"typ": "werte", "plattform": plattform, "woche": w, "werte": sauber, "quelle": quelle,
                        "notiz": str(notiz or "")[:200], "von": von})
        return {"plattform": plattform, "woche": w, "werte": sauber}

    def import_speichern(self, plattform: str, vorschau: dict, *, von: str = "") -> int:
        n = 0
        for w in vorschau["wochen"]:
            if w["werte"]:
                self.erfassen(plattform, w["woche"], w["werte"], quelle="csv",
                              notiz=f"CSV {vorschau['von']}–{vorschau['bis']}" + ("" if w["vollstaendig"] else " (Woche unvollstaendig)"),
                              von=von)
                n += 1
        return n

    def entfernen(self, plattform: str, woche: str, *, von: str = "") -> None:
        if plattform not in PLATTFORMEN:
            raise ValueError("Unbekannte Plattform.")
        self._schreibe({"typ": "entfernt", "plattform": plattform, "woche": montag(woche), "von": von})

    # -- Lesen --------------------------------------------------------------------------------------------------------
    def wochen(self) -> dict[str, dict[str, dict]]:
        """plattform -> woche -> {werte, quellen{metrik: quelle}, ts}."""
        out: dict[str, dict[str, dict]] = {p: {} for p in PLATTFORMEN}
        for e in self._ereignisse():
            p, w = e.get("plattform"), e.get("woche")
            if p not in out or not w:
                continue
            if e.get("typ") == "entfernt":
                out[p].pop(w, None)
                continue
            x = out[p].setdefault(w, {"woche": w, "werte": {}, "quellen": {}, "ts": e["ts"]})
            for k, v in (e.get("werte") or {}).items():
                x["werte"][k], x["quellen"][k] = v, e.get("quelle", "")
            x["ts"] = e["ts"]
        return out

    def uebersicht(self, heute: date | None = None, anzahl: int = 26) -> dict:
        heute = heute or date.today()
        aktuelle = montag(heute)
        letzte_volle = montag(heute - timedelta(days=7))
        alle = self.wochen()
        plattformen = []
        for p, name in PLATTFORMEN.items():
            ws = [alle[p][w] for w in sorted(alle[p])][-anzahl:]
            for x in ws:                                            # Bruchmarke Meta
                x["bruch"] = p in ("instagram", "facebook") and x["woche"] < META_BRUCH
            stand = [x for x in ws if "follower" in x["werte"]]
            f = stand[-1]["werte"]["follower"] if stand else None
            def follower_vor(tage):
                grenze = (date.fromisoformat(stand[-1]["woche"]) - timedelta(days=tage)).isoformat() if stand else ""
                alt = [x for x in stand if x["woche"] <= grenze]
                return f - alt[-1]["werte"]["follower"] if alt and f is not None else None
            luecken = [w for w in (montag(heute - timedelta(days=7 * i)) for i in range(1, 5)) if w not in alle[p]]
            plattformen.append({"id": p, "name": name, "follower": f, "stand_woche": stand[-1]["woche"] if stand else "",
                                "delta_4w": follower_vor(28), "delta_12w": follower_vor(84),
                                "letzte": ws[-1] if ws else None, "wochen": ws, "luecken": luecken,
                                "aktuell": aktuelle in alle[p]})
        summe = sum(x["follower"] for x in plattformen if x["follower"] is not None)
        return {"heute": heute.isoformat(), "letzte_volle_woche": letzte_volle, "plattformen": plattformen,
                "follower_summe": summe, "metriken": {k: {"name": v[0], "art": v[1]} for k, v in METRIKEN.items()},
                "plattform_namen": PLATTFORMEN, "meta_bruch": META_BRUCH,
                "hinweis": "Reichweite und Aufrufe von Instagram/Facebook vor dem 15.06.2026 sind mit neueren Werten nicht "
                           "direkt vergleichbar (Meta: views statt impressions)."}


def instagram_uebernehmen(store: Reichweite, snapshot, heute: date | None = None, *, von: str = "LUNA") -> dict | None:
    """Instagram-Snapshot (core/social_kit.MetaInsights.hole) als Wochenwert der laufenden Woche speichern."""
    if snapshot is None or not snapshot.followers:
        return None
    werte = {"follower": snapshot.followers}
    if snapshot.reach:
        werte["reichweite_28t"] = snapshot.reach
    return store.erfassen("instagram", (heute or date.today()).isoformat(), werte, quelle="api",
                          notiz="automatisch (Meta-Schnittstelle, eigenes Konto)", von=von)
