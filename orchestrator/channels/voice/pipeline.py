"""Pipecat-Pipeline fuer den Live-Voice-Kanal (Laufzeit, Conversation-Loop).

Architektur (Jarvis-Stil, Pipecat-nativ):

    transport.input -> RTVI -> STT -> context.user -> LLM(HoA) -> TTS -> transport.output -> context.assistant

- Der HoA ist ein **streamendes Anthropic-LLM** (schnelles Modell) mit Function-Calling.
  Streaming + Barge-in (Reinreden) + Gespraechsgedaechtnis sind dadurch Pipecat-nativ.
- Der HoA antwortet **normale Konversation direkt und knapp**; fuer echte Fachaufgaben ruft er das
  Tool `delegate` (CTO=Technik, berater=Strategie), fuer Einblendungen `show_panel` (Kostenuebersicht
  aus finance/). Delegation nutzt den schweren Orchestrator-Kern (Opus) nur bei Bedarf.
- CEO-Tore: bei Geld/Recht/Oeffentlichkeit/neuen Kosten/Mandat/Loeschung NICHT ausfuehren, sondern
  CEO-Freigabe ankuendigen (im delegate-Tool zusaetzlich technisch geprueft).

Lazy imports -- Pipecat/anthropic erst am GATE noetig.
"""
from __future__ import annotations

import asyncio

from ...governance.leak_guard import redact
from .directory import bereich_map, label as agent_label
from .panels import build_panel, finance_summary, set_monatsbudget
from .voices import get_selected_voice_id

# Konsultierbare Fachagenten (Kurzname -> Kurzbeschreibung) aus dem zentralen Verzeichnis.
_AGENTS = bereich_map()

VOICE_SYSTEM_PROMPT = (
    "Du bist der Head of Agents des Hanserautisch Agenten-Unternehmens und sprichst direkt mit dem CEO "
    "(Nils) per Sprache. Sprich Deutsch, natuerlich, knapp und gesprochen -- kurze Saetze, keine "
    "Aufzaehlungen oder Markdown, keine Vorrede wie 'Konsolidierte Antwort'. "
    "Beantworte normale Konversation und einfache Fragen SELBST und kurz. "
    "Du hast Fachagenten unter dir und kannst jeden per Tool 'delegate' konsultieren (an=cto Technik, "
    "berater Strategie, cfo Finanzen, cro Umsatz, ciso Sicherheit, cbo Marke, cpo Produkt, cxo UX, "
    "cco Content, cdo Daten, chro Personal, clo Recht, cko Wissen, cao Administration). Nutze 'delegate' "
    "nur fuer echte Fachfragen/Aufgaben; kuendige kurz an ('Einen Moment, ich frage den ... ') und fasse "
    "das Ergebnis danach in 1-3 Saetzen gesprochen zusammen. "
    "Wenn der CEO dir ein Monatsbudget nennt, bestaetige die Zahl kurz und trage sie dann mit 'set_budget' "
    "ueber den CFO in finance/budget.md ein. "
    "Fuer Geld-/Budget-/Kostenfragen hast du Zugriff auf Finance (CFO): nutze 'frage_finance', um die echten "
    "Zahlen aus finance/ zu holen, und antworte INHALTLICH (nenne konkrete Werte/Status), nicht nur 'es gibt "
    "eine Uebersicht'. Sag dabei kurz etwas wie 'Einen Moment, ich schaue bei Finance nach.', bevor du "
    "nachschlaegst. Wenn der CEO die Uebersicht sehen will, nutze zusaetzlich 'show_panel' "
    "(typ='kostenuebersicht') und sag, dass du sie einblendest -- fasse den Inhalt dann gesprochen zusammen. "
    "Will der CEO die Unternehmensstruktur sehen, nutze show_panel mit typ='organigramm'. "
    "CEO-Tore: Bei allem mit Geld, Recht, Vertraegen, Oeffentlichkeit, neuen kostenpflichtigen Diensten, "
    "Mandats-/Charta-Aenderungen oder Datenloeschung fuehrst du NICHTS aus, sondern sagst, dass du dafuer "
    "die Freigabe des CEO brauchst. Du hast Spezialisten unter dir; du bist der einzige, der mit dem CEO spricht."
)


def build_stt(cfg: dict, secrets: dict):
    """STT-Service aus Config (Default: Deepgram). Key kommt aus .env (Capability-Muster)."""
    provider = cfg.get("stt_provider", "deepgram").lower()
    if provider == "deepgram":
        from pipecat.services.deepgram.stt import DeepgramSTTService
        return DeepgramSTTService(
            api_key=secrets["DEEPGRAM_API_KEY"],
            settings=DeepgramSTTService.Settings(
                model="nova-2", language=cfg.get("language", "de"), smart_format=True
            ),
        )
    raise ValueError(f"Unbekannter STT-Provider: {provider}")


def build_tts(cfg: dict, secrets: dict):
    """TTS-Service aus Config (Cartesia ODER ElevenLabs). Key kommt aus .env."""
    provider = cfg.get("tts_provider", "cartesia").lower()
    if provider == "cartesia":
        from pipecat.services.cartesia.tts import CartesiaTTSService
        return CartesiaTTSService(api_key=secrets["CARTESIA_API_KEY"],
                                  voice_id=cfg.get("tts_voice_id", ""))
    if provider == "elevenlabs":
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        return ElevenLabsTTSService(
            api_key=secrets["ELEVENLABS_API_KEY"],
            settings=ElevenLabsTTSService.Settings(
                # Auswahl aus dem UI-Dropdown (gespeichert); Config-Override moeglich.
                voice=cfg.get("tts_voice_id") or get_selected_voice_id(),
                model="eleven_turbo_v2_5",
                language=cfg.get("language", "de"),
            ),
        )
    raise ValueError(f"Unbekannter TTS-Provider: {provider}")


def _build_tools():
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.adapters.schemas.tools_schema import ToolsSchema

    show_panel = FunctionSchema(
        name="show_panel",
        description="Blendet dem CEO ein Panel im Browser ein und liefert dir dessen Inhalt zurueck. "
                    "typ='kostenuebersicht' zeigt Budget und Kostenstatistik aus finance/; "
                    "typ='organigramm' zeigt die Unternehmensstruktur (CEO -> HoA -> Abteilungen).",
        properties={"typ": {"type": "string", "enum": ["kostenuebersicht", "organigramm"]}},
        required=["typ"],
    )
    frage_finance = FunctionSchema(
        name="frage_finance",
        description="Fragt Finance (CFO) nach den echten Zahlen aus finance/ (Budget, Ist-Kosten, "
                    "Schaetzungen). Nutze dies fuer alle Geld-/Budget-/Kostenfragen, um inhaltlich zu antworten.",
        properties={"frage": {"type": "string", "description": "Die Finanzfrage in einem Satz."}},
        required=["frage"],
    )
    delegate = FunctionSchema(
        name="delegate",
        description="Delegiert eine echte Fachaufgabe an einen Spezialisten und liefert dessen Ergebnis "
                    "zurueck (du fasst es danach gesprochen zusammen). Nur fuer echte Aufgaben/Fachfragen, "
                    "nicht fuer normale Konversation. Spezialisten: "
                    + "; ".join(f"{k}={v}" for k, v in _AGENTS.items()) + ".",
        properties={
            "aufgabe": {"type": "string", "description": "Die Aufgabe/Frage in einem Satz."},
            "an": {"type": "string", "enum": list(_AGENTS.keys()),
                   "description": "Kuerzel des zustaendigen Spezialisten."},
        },
        required=["aufgabe", "an"],
    )
    set_budget = FunctionSchema(
        name="set_budget",
        description="Traegt das vom CEO genannte Monatsbudget ueber den CFO in finance/budget.md ein. "
                    "Nur nutzen, wenn der CEO einen konkreten Betrag nennt -- bestaetige die Zahl vorher "
                    "gesprochen ('Ich trage X Euro als Monatsbudget ein, richtig?').",
        properties={"betrag_eur": {"type": "string",
                                   "description": "Monatsbudget in Euro, nur Zahl, z. B. '500'."}},
        required=["betrag_eur"],
    )
    return ToolsSchema(standard_tools=[show_panel, frage_finance, delegate, set_budget])


def build_pipeline(transport, core, cfg: dict, secrets: dict, *, finance_dir, leak_secrets):
    """Baut die Conversation-Pipeline + Task. `core` ist der HoA-Kern (fuer delegate/Changelog/CEO-Tor)."""
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
    from pipecat.processors.frameworks.rtvi import (
        RTVIObserver,
        RTVIProcessor,
        RTVIServerMessageFrame,
    )
    from pipecat.services.anthropic.llm import AnthropicLLMService

    stt = build_stt(cfg, secrets)
    tts = build_tts(cfg, secrets)
    llm = AnthropicLLMService(
        api_key=secrets["ANTHROPIC_API_KEY"],
        model=cfg.get("llm_model", "claude-haiku-4-5"),
    )

    context = LLMContext(
        messages=[{"role": "system", "content": VOICE_SYSTEM_PROMPT}],
        tools=_build_tools(),
    )
    aggregator = LLMContextAggregatorPair(context)
    rtvi = RTVIProcessor()

    async def emit_activity(agent_key: str, state: str):
        # Live-Anzeige in der Oberflaeche: mit wem der HoA gerade spricht.
        await rtvi.push_frame(RTVIServerMessageFrame(data={
            "kind": "agent_activity", "agent": agent_key,
            "label": agent_label(agent_key), "state": state,
        }))

    async def on_show_panel(params):
        typ = (params.arguments or {}).get("typ", "kostenuebersicht")
        panel = build_panel(typ, finance_dir=finance_dir, secrets=leak_secrets)
        # Panel ueber den RTVI-Datenkanal an die Browser-Seite (parallel zur Sprache).
        await rtvi.push_frame(RTVIServerMessageFrame(data={"kind": "panel", "panel": panel}))
        # Inhalt zurueckgeben, damit der HoA gesprochen darueber sprechen kann.
        inhalt = finance_summary(finance_dir, leak_secrets) if typ == "kostenuebersicht" else ""
        await params.result_callback({"eingeblendet": True, "typ": typ, "inhalt": inhalt})

    async def on_frage_finance(params):
        frage = (params.arguments or {}).get("frage", "")
        await emit_activity("cfo", "start")
        try:
            return await params.result_callback(
                {"frage": frage, "finance": finance_summary(finance_dir, leak_secrets)}
            )
        finally:
            await emit_activity("cfo", "end")

    async def on_delegate(params):
        args = params.arguments or {}
        aufgabe = (args.get("aufgabe") or "").strip()
        an = (args.get("an") or "berater").strip()
        # CEO-Tor: keine autonome Ausfuehrung bei Tor-Kategorien.
        gate = core.gate.check(aufgabe)
        if gate.blocked:
            await params.result_callback(
                {"blockiert": True, "kategorie": gate.category,
                 "hinweis": "CEO-Freigabe noetig -- nicht ausfuehren, dem CEO mitteilen."}
            )
            return
        spec = core.subagents.get(an)
        if spec is None:
            await params.result_callback({"fehler": f"Unbekannter Spezialist '{an}'."})
            return
        loop = asyncio.get_running_loop()
        await emit_activity(an, "start")  # Live-Anzeige: HoA spricht mit diesem Agenten
        try:
            result = await loop.run_in_executor(
                None, core.backend.respond, an, spec.system_prompt, aufgabe, {}
            )
        except Exception as exc:  # Backend-/API-Fehler nicht die Pipeline reissen lassen
            await params.result_callback({"fehler": str(exc)})
            return
        finally:
            await emit_activity(an, "end")
        if core.changelog:
            core.changelog("Head of Agents", f"Voice-Delegation an {an}: {aufgabe}",
                           "CEO-Sprachkanal", f"Subagent: {an}")
        await params.result_callback({"ergebnis": redact(result, leak_secrets)})

    async def on_set_budget(params):
        betrag = str((params.arguments or {}).get("betrag_eur", "")).strip()
        res = set_monatsbudget(betrag, finance_dir)
        if core.changelog and res.get("ok"):
            core.changelog("CFO", f"Monatsbudget gesetzt: {res['betrag']} EUR/Monat (CEO-Ansage)",
                           "CEO-Ansage ueber Sprachkanal", "finance/budget.md")
        await params.result_callback(res)

    llm.register_function("show_panel", on_show_panel)
    llm.register_function("frage_finance", on_frage_finance)
    llm.register_function("delegate", on_delegate, cancel_on_interruption=False)
    llm.register_function("set_budget", on_set_budget, cancel_on_interruption=False)

    pipeline = Pipeline([
        transport.input(),
        rtvi,
        stt,
        aggregator.user(),
        llm,
        tts,
        transport.output(),
        aggregator.assistant(),
    ])
    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
        observers=[RTVIObserver(rtvi)],
    )
    runner = PipelineRunner(handle_sigint=False)
    return task, runner
