"""Start: python -m orchestrator.channels.web  (-> http://HOST:PORT)."""
import os

import uvicorn

if __name__ == "__main__":
    # PORT (vom Preview-Harness gesetzt) hat Vorrang vor LUNA_OS_PORT; sonst Default 8765.
    port = int(os.environ.get("PORT") or os.environ.get("LUNA_OS_PORT") or "8765")
    # PROMPT_INJECTION_SCHUTZ I4: Verdacht/Sperren protokollieren (nur im Betrieb -- Tests schreiben nichts)
    from pathlib import Path
    from orchestrator.core import input_guard
    from orchestrator.core.injection_protokoll import InjectionProtokoll
    input_guard.protokoll_setzen(InjectionProtokoll(Path(__file__).resolve().parents[3] / "sicherheit" / "injection.jsonl"))
    from orchestrator.core import netz_auftraege                    # NETZ_AGENT Q5: Statistik fuer den CISO-Bericht
    netz_auftraege.statistik_setzen(Path(__file__).resolve().parents[3] / "sicherheit" / "netz_agent.jsonl")
    uvicorn.run("orchestrator.channels.web.app:app",
                host=os.environ.get("LUNA_OS_HOST", "127.0.0.1"),
                port=port,
                log_level="info")
