"""show_panel -- UI-Anweisungen fuer die Browser-Oberflaeche (Einblendungen).

Erzeugt JSON-faehige dicts, die ueber den WebRTC-Datenkanal an die Browser-Seite gehen
und dort als Panel gerendert werden. Datenherkunft fuer Kosten: `finance/` (read-only).
Jeder Panel-Inhalt laeuft durch den Leck-Schutz (keine .env-Werte in Panels).

Bewusst schlank/erweiterbar: weitere Panel-Typen koennen ergaenzt werden.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...governance.leak_guard import redact

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FINANCE = ROOT / "finance"

# Anzeige-Verben -> nur reine Anzeige-Wuensche loesen ein Panel aus (lesend, kein CEO-Tor).
_DISPLAY_VERBS = ("zeig", "zeige", "anzeig", "einblend", "blende", "uebersicht", "darstell")


def detect_panel_intent(text: str):
    """Erkennt reine Anzeige-Wuensche. Gibt (typ, daten) zurueck oder None.

    Bewusst eng: nur wenn ein Anzeige-Verb vorkommt (bzw. das Wort 'kostenuebersicht'),
    damit handlungsbezogene Anweisungen ('neues kostenpflichtiges Tool beschaffen') NICHT
    als Panel missverstanden werden, sondern regulaer durch den HoA-Kern (inkl. Tor) laufen.
    """
    t = (text or "").lower()
    if "kostenuebersicht" in t or (
        ("kosten" in t or "budget" in t) and any(v in t for v in _DISPLAY_VERBS)
    ):
        return ("kostenuebersicht", None)
    return None


def build_panel(typ: str, daten: dict | None = None, *, finance_dir: Path | None = None,
                secrets: list[str] | None = None) -> dict:
    """Baut eine Panel-Anweisung. `typ`: kostenuebersicht | tabelle | text/markdown."""
    secrets = secrets or []
    daten = daten or {}
    if typ == "kostenuebersicht":
        panel = _kostenuebersicht(Path(finance_dir) if finance_dir else DEFAULT_FINANCE)
    elif typ == "tabelle":
        panel = {
            "type": "tabelle",
            "title": daten.get("title", "Tabelle"),
            "columns": daten.get("columns", []),
            "rows": daten.get("rows", []),
        }
    elif typ in ("text", "markdown"):
        panel = {
            "type": "markdown",
            "title": daten.get("title", "Hinweis"),
            "markdown": daten.get("markdown", ""),
        }
    else:
        panel = {"type": "markdown", "title": "Unbekanntes Panel",
                 "markdown": f"Unbekannter Panel-Typ: {typ}"}
    return _redact_obj(panel, secrets)


def finance_summary(finance_dir: Path | None = None, secrets: list[str] | None = None) -> str:
    """Sprechbare Zusammenfassung der echten Finanzdaten aus finance/ (Domaene des CFO).

    Damit der HoA inhaltlich antworten kann (nicht nur 'es gibt eine Uebersicht'). Leck-geschuetzt.
    """
    fd = Path(finance_dir) if finance_dir else DEFAULT_FINANCE
    budget = _extract_monatsbudget(_read(fd / "budget.md"))
    stats_plain = _plain(_read(fd / "kosten-statistik.md"))
    text = (
        f"Monatsbudget laut finance/budget.md: {budget}. "
        f"Aus finance/kosten-statistik.md (CFO): {stats_plain[:900]}"
    )
    return redact(text, secrets or [])


def set_monatsbudget(betrag_eur: str, finance_dir: Path | None = None, when: str = "") -> dict:
    """Traegt das Monatsbudget in finance/budget.md ein (CFO-Aktion auf CEO-Ansage).

    Aktualisiert 'Monatsbudget' + 'Gueltig ab' und ergaenzt eine Historienzeile. .md bleibt ASCII.
    """
    from datetime import date

    fd = Path(finance_dir) if finance_dir else DEFAULT_FINANCE
    path = fd / "budget.md"
    md = _read(path)
    if not md:
        return {"ok": False, "fehler": "finance/budget.md nicht gefunden"}

    # Betrag auf ASCII/Zahl normalisieren (kein Euro-Zeichen in .md).
    betrag = re.sub(r"[^0-9.,]", "", str(betrag_eur)).strip().strip(".,")
    if not betrag:
        return {"ok": False, "fehler": "kein gueltiger Betrag erkannt"}
    when = when or date.today().isoformat()
    alt = _extract_monatsbudget(md)

    out, hist_done, seen_hist = [], False, False
    for line in md.splitlines():
        st = line.strip()
        if st.startswith("- **Monatsbudget:**"):
            out.append(f"- **Monatsbudget:** {betrag} EUR/Monat")
            continue
        if st.startswith("- **Gueltig ab:**"):
            out.append(f"- **Gueltig ab:** {when}")
            continue
        if "Aenderungshistorie" in st:
            seen_hist = True
        out.append(line)
        # Historienzeile direkt nach der Tabellen-Trennzeile einfuegen.
        if seen_hist and not hist_done and set(st) <= set("|-: ") and st.startswith("|") and "-" in st:
            out.append(f"| {when} | {alt} | {betrag} | CFO (CEO-Ansage) | per Sprache gesetzt |")
            hist_done = True

    path.write_text("\n".join(out) + ("\n" if md.endswith("\n") else ""), encoding="utf-8")
    return {"ok": True, "betrag": betrag, "gueltig_ab": when, "alt": alt}


# -- intern --

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _plain(md: str) -> str:
    """Markdown grob zu Fliesstext (fuer sprechbare Finance-Zusammenfassung)."""
    out = []
    for line in md.splitlines():
        s = line.strip()
        if not s or s.startswith(">") or set(s) <= set("-:| "):
            continue
        s = re.sub(r"[#*`>]", "", s)
        s = s.replace("|", " ").strip()
        if s:
            out.append(s)
    return " ".join(" ".join(out).split())


def _kostenuebersicht(finance_dir: Path) -> dict:
    budget_md = _read(finance_dir / "budget.md")
    stats_md = _read(finance_dir / "kosten-statistik.md")
    # 'type' ist ein Protokoll-Key (ASCII); 'title'/'hinweis' sind Anzeigetexte (Umlaute erlaubt).
    return {
        "type": "kostenuebersicht",
        "title": "Kostenübersicht",
        "monatsbudget": _extract_monatsbudget(budget_md),
        "soll_ist": _extract_first_table(stats_md),
        "quellen": ["finance/budget.md", "finance/kosten-statistik.md"],
        "hinweis": "Lesende Anzeige aus finance/. Das Monatsbudget legt der CEO in "
                   "finance/budget.md fest; Ist-Kosten pflegt der CFO.",
    }


def _extract_monatsbudget(budget_md: str) -> str:
    for line in budget_md.splitlines():
        if "Monatsbudget" in line and ":" in line:
            val = line.split(":", 1)[1].strip().strip("*").strip()
            val = val.replace("`", "").strip()
            if val and "festzulegen" not in val and val != "—":
                return val
            return "noch nicht festgelegt (Platzhalter in finance/budget.md)"
    return "unbekannt"


def _extract_first_table(md: str) -> dict:
    """Erste Markdown-Tabelle als {columns, rows} (fuer die Soll-Ist-Uebersicht)."""
    rows: list[list[str]] = []
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):  # Trennzeile ueberspringen
                continue
            rows.append(cells)
    if not rows:
        return {"columns": [], "rows": []}
    return {"columns": rows[0], "rows": rows[1:]}


def _redact_obj(obj, secrets: list[str]):
    if isinstance(obj, str):
        return redact(obj, secrets)
    if isinstance(obj, list):
        return [_redact_obj(x, secrets) for x in obj]
    if isinstance(obj, dict):
        return {k: _redact_obj(v, secrets) for k, v in obj.items()}
    return obj
