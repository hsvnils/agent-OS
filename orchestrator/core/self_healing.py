"""IT-Selbstheilung -- LUNA gibt technische, KOSTENFREIE Fixes selbst frei (CEO-Delegation 2026-06-25).

Eng begrenzte Autonomie: Ausschliesslich Antraege der Kategorie **technisch & kostenfrei** (nur Strom)
duerfen ohne CEO freigegeben, umgesetzt (Branch + Tests) und -- bei gruenen Tests -- nach main gemergt
werden. Der CEO wird ueber jede Selbstheilung informiert. Alles andere (Geld/Recht/Oeffentlichkeit/neue
Kosten/Secrets/Charta/Governance/Loeschungen) bleibt **hart** CEO-Tor.

Verteidigung in der Tiefe: (1) Kategorie muss 'technisch-kostenfrei' sein; (2) Stichwort-Scan auf
Kosten-/Risiko-Begriffe; (3) Tests muessen gruen sein (sonst kein Merge); (4) Notbremse stoppt; (5) alles
auf Git -> reversibel; (6) CEO-Meldung mit Bericht.
"""
from __future__ import annotations

# Stichwoerter, die eine reine technische, kostenfreie Aenderung ausschliessen -> dann immer CEO.
_VERBOTEN = (
    "euro", "kosten", "geld", "bezahl", "zahlung", "kauf", "abo", "miete", "lizenz", "preis",
    "vertrag", "recht", "anwalt", "steuer", "oeffentlich", "presse", "veroeffentlich", "posting",
    "secret", "api-key", "api key", "token-key", "passwort", "charta", "governance", "mandat",
    "loesch", "delete", "entfernen der daten", "datenloeschung", "twilio", "bezahldienst",
)


def ist_technisch_kostenfrei(antrag: dict) -> tuple[bool, str]:
    """True nur, wenn der Antrag als technisch-kostenfrei markiert ist UND kein Kosten-/Risiko-Stichwort traegt."""
    kat = (antrag.get("kategorie") or "").lower()
    if "technisch" not in kat or "kostenfrei" not in kat:
        return False, "Antrag ist nicht als 'technisch-kostenfrei' kategorisiert -- CEO-Freigabe noetig."
    text = f"{antrag.get('titel', '')} {antrag.get('beschreibung', '')}".lower()
    for w in _VERBOTEN:
        if w in text:
            return False, f"Stichwort '{w}' deutet auf Kosten/Recht/Risiko -- CEO-Freigabe noetig."
    return True, ""


class SelfHealing:
    def __init__(self, antraege, engine, *, repo_root, notify=None, watch=None,
                 secrets: list[str] | None = None):
        self.antraege = antraege
        self.engine = engine
        self.repo_root = repo_root
        self.notify = notify
        self.watch = watch
        self.secrets = secrets or []

    def heilen(self, antrag_id: str) -> dict:
        a = self.antraege.get(antrag_id)
        if not a:
            return {"ok": False, "fehler": "Antrag nicht gefunden."}
        if self.watch is not None and getattr(self.watch.store, "paused", lambda: False)():
            return {"ok": False, "hinweis": "Autonomie pausiert (Notbremse)."}
        erlaubt, grund = ist_technisch_kostenfrei(a)
        if not erlaubt:
            return {"ok": False, "abgelehnt": True, "hinweis": grund}
        if self.engine is None:
            return {"ok": False, "fehler": "Execution-Engine nicht verfuegbar."}

        # 1. Selbst freigeben (technische Delegation) + 2. umsetzen (Branch + Tests)
        self.antraege.freigeben(antrag_id, akteur="LUNA (technische Selbstfreigabe)")
        res = self.engine.umsetzen(antrag_id)
        if not (res.ok and res.status == "erledigt"):
            self._melde(f"IT-Selbstheilung fehlgeschlagen (Tests/Umsetzung) -- NICHT gemergt: "
                        f"{a.get('titel', '')[:50]} ({antrag_id}).",
                        detail=getattr(res, "bericht", "")[:500])
            return {"ok": False, "status": getattr(res, "status", "fehlgeschlagen"),
                    "bericht": getattr(res, "bericht", "")}

        # 3. Branch committen + nach main mergen (nur bei gruenen Tests, s. o.)
        from .execution_live import commit_branch, merge_branch
        commit_branch(str(self.repo_root / ".worktrees" / f"antrag-{antrag_id}"),
                      f"Antrag {antrag_id}: IT-Selbstheilung")
        ok, out = merge_branch(self.repo_root, f"antrag/{antrag_id}",
                               f"Merge IT-Selbstheilung {antrag_id}")
        self._melde(f"IT-Selbstheilung umgesetzt{' + gemergt' if ok else ''}: "
                    f"{a.get('titel', '')[:60]} ({antrag_id}).",
                    detail=getattr(res, "bericht", "")[:500])
        return {"ok": ok, "gemergt": ok, "status": "erledigt", "bericht": getattr(res, "bericht", "")}

    def _melde(self, text: str, *, detail: str = "") -> None:
        if self.notify is not None:
            try:
                self.notify(text, abteilung="IT/Self-Healing", kategorie="selbstheilung",
                            quelle="self-healing", detail=detail)
            except Exception:
                pass
