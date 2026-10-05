"""Routing-Probelauf (FACHAGENTEN_ROUTING R4 Teil 2): Sachfragen ohne Abteilungsnamen an das Chat-Modell schicken und
pruefen, welches Werkzeug bzw. welchen Fachagenten LUNA waehlt.

Es wird **nichts ausgefuehrt**: Das Modell bekommt LUNAs System-Prompt und die Werkzeuge der Werkzeugauswahl, gewertet
wird nur sein erster Werkzeugaufruf. An Gemini gehen nur die Testfragen, der System-Prompt und die Werkzeug-
Beschreibungen (keine Kunden-, Mail- oder Rechnungsdaten). Schluessel nur ueber `_load_secrets()`, nie ausgegeben.

    .venv/bin/python scripts/routing_probelauf.py [--modell gemini-2.5-flash] [--pause 4]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from openai import OpenAI

    from orchestrator.channels.telegram.bot import _load_secrets
    from orchestrator.core import werkzeugauswahl as w
    from orchestrator.core.hoa_conversation import TEXT_SYSTEM_PROMPT
    from orchestrator.core.hoa_tools import tool_specs
    from orchestrator.core.model_router import GEMINI_BASE_URL, _zu_openai_tools
    from orchestrator.core.zustaendigkeit import bereich_von
    from orchestrator.tests.test_fachagenten_routing import SACHFRAGEN

    ap = argparse.ArgumentParser()
    ap.add_argument("--modell", default="gemini-2.5-flash")
    ap.add_argument("--pause", type=float, default=4.0)
    a = ap.parse_args()
    client = OpenAI(api_key=_load_secrets().get("GEMINI_API_KEY", ""), base_url=GEMINI_BASE_URL)
    specs = tool_specs()
    richtig, zeilen = 0, []
    for frage, werkzeug, bereich in SACHFRAGEN:
        namen, _ = w.auswahl(frage)
        tools = _zu_openai_tools(w.filtere(specs, namen))
        try:
            r = client.chat.completions.create(model=a.modell, tools=tools, messages=[
                {"role": "system", "content": TEXT_SYSTEM_PROMPT}, {"role": "user", "content": frage}])
            calls = r.choices[0].message.tool_calls or []
            name = calls[0].function.name if calls else "(keins)"
            arg = json.loads(calls[0].function.arguments or "{}") if calls else {}
        except Exception as exc:                             # Kontingent/Netz: als Fehler zaehlen, weiter
            name, arg = f"FEHLER {exc.__class__.__name__}", {}
        an = (arg.get("an") or "").strip().lower()
        # richtig: erwartetes Werkzeug (bei delegate mit richtigem Agenten) ODER ein Werkzeug/Agent desselben Bereichs
        # (z. B. brain_suchen gehoert dem CKO); Rechtsfragen zu Geschaeftsregeln duerfen auch an den CLO gehen.
        ist_bereich = an if name == "delegate" else bereich_von(name)
        ok = ist_bereich == bereich or (name == werkzeug and werkzeug != "delegate") or (
            werkzeug == "geschaeftsregeln" and name == "delegate" and an == "clo" and "duerfen" in frage)
        richtig += ok
        zeilen.append((ok, frage, f"{werkzeug}{'->' + bereich if werkzeug == 'delegate' else ''}",
                       f"{name}{'->' + an if an else ''}"))
        time.sleep(a.pause)
    for ok, frage, soll, ist in zeilen:
        print(f"{'OK ' if ok else 'XX '} {frage[:58]:58} soll {soll:22} ist {ist}")
    quote = richtig / len(SACHFRAGEN)
    print(f"\nTrefferquote {richtig}/{len(SACHFRAGEN)} = {quote:.0%} (Gate 85 %, Modell {a.modell})")
    return 0 if quote >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
