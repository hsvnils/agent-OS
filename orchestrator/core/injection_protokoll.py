"""Protokoll des Prompt-Injection-Schutzes (PROMPT_INJECTION_SCHUTZ I4, CEO 2026-10-19).

Jeder Verdacht (I1/I2), jede Handlungs-Sperre und jeder entfernte Link (I3) wird festgehalten -- **ohne Inhalt**: Zeit,
Art, Quelle (Werkzeug/Kanal), erkannte Muster und eine kurze Pruefsumme des Textes (damit dieselbe Mail beim
wiederholten Lesen nicht jedes Mal neu zaehlt). Datei `sicherheit/injection.jsonl` (nur NAS, nicht im Git, im Backup).

Leser: naechtlicher CISO-Bericht (`security_agent._check_injection`), Leistungsbericht (`performance_agent`), Telegram-
Hinweis bei Verdacht in Mails/Belegen (Bot-Poll, `hinweise`). Das Protokoll wird nur im Betrieb eingeschaltet
(`input_guard.protokoll_setzen`), Tests schreiben nichts.
"""
from __future__ import annotations

import hashlib
import json
import threading
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ARTEN = ("verdacht", "gesperrt", "link_entfernt")
DOPPELT_STUNDEN = 24
# Quellen, bei denen der CEO sofort per Telegram hoert (Mails und Belege -- dort kommen Angriffe von aussen an)
HINWEIS_QUELLEN = ("mail_", "posteingang", "eingangsbeleg")   # „mail“ (CRM-Mail-Poll) meldet schon selbst


def pruefsumme(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", "replace")).hexdigest()[:16]


class InjectionProtokoll:
    def __init__(self, pfad: Path | str):
        self.pfad = Path(pfad)
        self._lock = threading.Lock()

    def eintraege(self) -> list[dict]:
        try:
            zeilen = self.pfad.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for z in zeilen:
            try:
                out.append(json.loads(z))
            except ValueError:
                continue
        return out

    def erfassen(self, art: str, quelle: str, muster: list[str] | None = None, *, text: str = "",
                 jetzt: datetime | None = None) -> bool:
        """-> True, wenn neu eingetragen (gleicher Text aus gleicher Quelle binnen 24 h zaehlt nur einmal)."""
        jetzt = jetzt or datetime.now()
        e = {"ts": jetzt.isoformat(timespec="seconds"), "art": art if art in ARTEN else "verdacht",
             "quelle": str(quelle or "?")[:60], "muster": sorted(set(muster or []))[:12],
             "pruefsumme": pruefsumme(text) if text else ""}
        with self._lock:
            if e["pruefsumme"]:
                grenze = (jetzt - timedelta(hours=DOPPELT_STUNDEN)).isoformat(timespec="seconds")
                for alt in self.eintraege()[-500:]:
                    if (alt.get("pruefsumme") == e["pruefsumme"] and alt.get("quelle") == e["quelle"]
                            and alt.get("art") == e["art"] and alt.get("ts", "") >= grenze):
                        return False
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return True

    def zaehlen(self, start: datetime, ende: datetime) -> dict:
        """Kennzahlen eines Zeitfensters (fuer CISO- und Leistungsbericht)."""
        s, en = start.isoformat(timespec="seconds"), ende.isoformat(timespec="seconds")
        evs = [e for e in self.eintraege() if s <= e.get("ts", "") <= en]
        arten = Counter(e.get("art") for e in evs)
        verdacht = [e for e in evs if e.get("art") == "verdacht"]
        return {"verdacht": arten.get("verdacht", 0), "gesperrt": arten.get("gesperrt", 0),
                "links_entfernt": arten.get("link_entfernt", 0),
                "je_quelle": dict(Counter(e.get("quelle", "?") for e in verdacht).most_common(5)),
                "je_muster": dict(Counter(m for e in verdacht for m in e.get("muster") or []).most_common(5))}

    def hinweise(self, stand_datei: Path | str) -> list[dict]:
        """Neue Verdachtsfaelle aus Mails/Belegen seit dem letzten Aufruf (fuer den Telegram-Hinweis im Bot-Poll)."""
        stand_datei = Path(stand_datei)
        try:
            bis = json.loads(stand_datei.read_text(encoding="utf-8")).get("bis", "")
        except (OSError, ValueError):
            bis = ""
        evs = self.eintraege()
        neu = [e for e in evs if e.get("ts", "") > bis and e.get("art") == "verdacht"
               and any(str(e.get("quelle", "")).startswith(q) for q in HINWEIS_QUELLEN)]
        if evs:
            stand_datei.parent.mkdir(parents=True, exist_ok=True)
            stand_datei.write_text(json.dumps({"bis": max(e.get("ts", "") for e in evs)}), encoding="utf-8")
        return neu if bis else []          # erster Lauf: nur den Stand setzen, keine Altfaelle melden


def hinweis_text(neu: list[dict]) -> str:
    quellen = Counter(e.get("quelle", "?") for e in neu)
    muster = Counter(m for e in neu for m in e.get("muster") or [])
    return (f"🛡️ Möglicher Prompt-Injection-Versuch in {len(neu)} Eingang/Eingängen "
            f"({', '.join(f'{q} {n}×' for q, n in quellen.most_common(3))}). Erkannt: "
            f"{', '.join(m for m, _ in muster.most_common(4))}. LUNA hat den Inhalt nur als Daten behandelt; "
            "Aktionen mit Außenwirkung waren im selben Zug gesperrt.")
