"""Dateibasiertes Agenten-Gedaechtnis (append-only JSONL).

Abgegrenzt vom Changelog: speichert Aufgaben-/Entscheidungs-Erinnerung (Auftrag,
Delegation, Ergebnis, Eskalation), NICHT Datei-Provenienz. Jeder Eintrag laeuft vor
dem Schreiben durch den Leck-Schutz (keine .env-Werte im Store). Dry-Run schreibt in
einen separaten, per .gitignore ausgeschlossenen Store.

Bewusst schlank: Recall = letzte N Eintraege + stichwort-relevante aeltere
(Substring-Matching, KEINE Embeddings). Semantische Suche/Datenbank sind spaetere,
separat freizugebende Ausbaustufen (siehe MEMORY_PLAN.md).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

_WORD = re.compile(r"[a-z0-9ßäöü]{4,}")


def derive_tags(text: str, max_tags: int = 8) -> list[str]:
    """Einfache Stichwort-Ableitung: kleingeschriebene Woerter >= 4 Zeichen, eindeutig."""
    seen: list[str] = []
    for w in _WORD.findall(text.lower()):
        if w not in seen:
            seen.append(w)
        if len(seen) >= max_tags:
            break
    return seen


def _digest(text: str, limit: int = 200) -> str:
    one_line = " ".join(text.split())
    return one_line[:limit]


@dataclass
class MemoryRecord:
    ts: str
    session_id: str
    instruction: str
    delegated_to: list[str]
    status: str  # ok | mit_fehler | eskalation
    result_digest: str
    eskalationen: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        session_id: str,
        instruction: str,
        delegated_to: list[str],
        status: str,
        result: str,
        eskalationen: list[str] | None = None,
    ) -> "MemoryRecord":
        return cls(
            ts=datetime.now().isoformat(timespec="seconds"),
            session_id=session_id,
            instruction=_digest(instruction, 300),
            delegated_to=list(delegated_to),
            status=status,
            result_digest=_digest(result, 240),
            eskalationen=list(eskalationen or []),
            tags=derive_tags(instruction),
        )


class Memory:
    """Append-only JSONL-Store mit schlankem Recall und Leck-Schutz."""

    def __init__(self, path: str | Path, *, secrets: list[str] | None = None,
                 recall_limit: int = 5):
        self.path = Path(path)
        self.secrets = secrets or []
        self.recall_limit = recall_limit

    def append(self, record: MemoryRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(asdict(record), ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _all(self) -> list[dict]:
        if not self.path.exists():
            return []
        records: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # robuste Lesart: defekte Zeilen ueberspringen
        return records

    def recall(self, query: str, limit: int | None = None) -> list[dict]:
        """Letzte N Eintraege (neueste zuerst) + stichwort-relevante aeltere."""
        limit = self.recall_limit if limit is None else limit
        records = list(reversed(self._all()))  # neueste zuerst
        recent = records[:limit]
        q_tokens = set(derive_tags(query, max_tags=20))
        relevant: list[dict] = []
        for r in records[limit:]:
            hay = (r.get("instruction", "") + " " + " ".join(r.get("tags", []))).lower()
            if any(t in hay for t in q_tokens):
                relevant.append(r)
        return recent + relevant

    def render_context(self, query: str, limit: int | None = None) -> str:
        """Kompakter Gedaechtnis-Block fuer den HoA; leer, wenn nichts vorliegt."""
        recs = self.recall(query, limit)
        if not recs:
            return ""
        lines = ["Gedaechtnis-Kontext (frueheres Wissen, nicht Teil des aktuellen Auftrags):"]
        for r in recs:
            lines.append(
                f"- [{r.get('ts', '?')}] {r.get('instruction', '')[:90]} "
                f"-> {r.get('status', '?')}: {r.get('result_digest', '')[:140]}"
            )
        return "\n".join(lines)
