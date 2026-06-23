"""Head-of-Agents-Kern (kanal-agnostisch).

Nachricht rein -> EINE konsolidierte Antwort als Stream raus. Kennt keinen Kanal.
Setzt Autonomie-zuerst + Eskalation, CEO-Tor-Hook, Changelog und Leck-Schutz um.
"""
from __future__ import annotations

import uuid
from typing import Callable, Iterator

from ..governance.leak_guard import redact
from .backends import Backend, BackendError
from .charter_loader import SubagentSpec, compose_hoa_system_prompt
from .memory import Memory, MemoryRecord
from .routing import decide_delegation


class HeadOfAgents:
    def __init__(
        self,
        backend: Backend,
        subagents: dict[str, SubagentSpec],
        *,
        gate,
        leak_secrets: list[str] | None = None,
        changelog: Callable[..., None] | None = None,
        logger=None,
        memory: Memory | None = None,
        session_id: str | None = None,
    ):
        self.backend = backend
        self.subagents = subagents
        self.gate = gate
        self.leak_secrets = leak_secrets or []
        self.changelog = changelog
        self.logger = logger
        self.memory = memory
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._system_prompt: str | None = None

    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = compose_hoa_system_prompt()
        return self._system_prompt

    def handle(self, message: str) -> Iterator[str]:
        """Auftrags-Lebenszyklus (verkuerzt): Tor -> delegieren -> buendeln -> EINE Antwort."""
        # 1. CEO-Tor-Vorpruefung auf den eingehenden Auftrag
        gate = self.gate.check(message)
        if gate.blocked:
            self._log("ceo_gate_block", "hoa", gate.category)
            answer = (
                f"CEO-Tor beruehrt ({gate.category}). Keine autonome Ausfuehrung.\n\n"
                + gate.freigabe_anfrage
            )
            yield from self._stream(self._redact(answer))
            return

        # 2. Gedaechtnis-Kontext laden (frueheres Wissen) und dem Auftrag voranstellen.
        # Tor-/Routing-Entscheidung nutzen den ORIGINAL-Auftrag; nur die Subagenten
        # bekommen den angereicherten Text, damit Memory-Inhalt keine Tore/Routing faelscht.
        mem_ctx = self.memory.render_context(message) if self.memory else ""
        agent_message = (
            mem_ctx + "\n\n---\nAktueller Auftrag:\n" + message if mem_ctx else message
        )

        # 3. Delegation an Subagenten (Autonomie zuerst, Eskalation als Ausnahme)
        targets = decide_delegation(message)
        results: dict[str, str] = {}
        eskalationen: list[str] = []
        for key in targets:
            spec = self.subagents.get(key)
            sysp = spec.system_prompt if spec else ""
            try:
                out = self.backend.respond(key, sysp, agent_message, {})
            except BackendError as err:
                # Echter Backend-/API-Fehler (keine Mandats-Blockade): sauber melden,
                # nicht abstuerzen, keinen CTO-Workaround starten.
                self._log("backend_error", key, str(err))
                results[key] = "FEHLER: " + str(err)
                continue
            self._log("delegate", key, out)
            if out.startswith("BLOCKED"):
                # Blockade -> zuerst CTO (Workaround), bevor der CEO behelligt wird
                cto = self.subagents.get("cto")
                try:
                    cto_out = self.backend.respond(
                        "cto", cto.system_prompt if cto else "", "WORKAROUND fuer: " + message, {}
                    )
                except BackendError as err:
                    self._log("backend_error", "cto", str(err))
                    results[key] = "FEHLER: " + str(err)
                    continue
                self._log("escalate_cto", key, cto_out)
                if cto_out.startswith("BLOCKED"):
                    results[key] = "ESKALATION an CEO noetig: " + out
                    eskalationen.append(key)
                else:
                    results[key] = "Via CTO geloest: " + cto_out
            else:
                results[key] = out

        # 4. Buendeln zu EINER Antwort
        consolidated = self._bundle(message, results, eskalationen)

        # 5. Status fuer Changelog und Gedaechtnis bestimmen
        had_error = any(v.startswith("FEHLER") for v in results.values())
        if eskalationen:
            mem_status = "eskalation"
        elif had_error:
            mem_status = "mit_fehler"
        else:
            mem_status = "ok"

        # 6. Changelog-Pflicht (wahrheitsgemaess: Fehler nicht als Erfolg protokollieren)
        if self.changelog:
            status = "mit Fehler(n)" if had_error else "erfolgreich"
            self.changelog(
                "Head of Agents",
                f"Auftrag {status} bearbeitet: " + message,
                "CEO-Anweisung ueber Kanal-Adapter",
                "Subagenten: " + ", ".join(targets),
            )

        # 7. Gedaechtnis fortschreiben (Aufgaben-/Entscheidungs-Erinnerung, leck-geschuetzt)
        if self.memory:
            self.memory.append(
                MemoryRecord.build(
                    session_id=self.session_id,
                    instruction=message,
                    delegated_to=targets,
                    status=mem_status,
                    result=self._redact(consolidated),
                    eskalationen=eskalationen,
                )
            )

        yield from self._stream(self._redact(consolidated))

    # -- intern --
    def _bundle(self, message: str, results: dict[str, str], eskalationen: list[str]) -> str:
        lines = ["Konsolidierte Antwort an den CEO:", "Auftrag: " + message, ""]
        for key, val in results.items():
            lines.append(f"- {key}: {val}")
        if eskalationen:
            lines.append("")
            lines.append(
                "Hinweis: Offene Eskalation(en) erfordern eine CEO-Entscheidung: "
                + ", ".join(eskalationen)
            )
        return "\n".join(lines)

    def _stream(self, text: str) -> Iterator[str]:
        for line in text.splitlines(keepends=True):
            yield line

    def _redact(self, text: str) -> str:
        return redact(text, self.leak_secrets)

    def _log(self, kind: str, key: str, detail: str = "") -> None:
        if self.logger:
            self.logger.log(kind, key, detail)
