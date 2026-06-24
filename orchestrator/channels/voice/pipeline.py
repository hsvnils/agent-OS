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
from .panels import build_panel

# Default-Stimme ElevenLabs (multilingual-faehig), falls keine Voice-ID in config.toml steht.
_DEFAULT_ELEVEN_VOICE = "21m00Tcm4TlvDq8ikWAM"

VOICE_SYSTEM_PROMPT = (
    "Du bist der Head of Agents des Hanserautisch Agenten-Unternehmens und sprichst direkt mit dem CEO "
    "(Nils) per Sprache. Sprich Deutsch, natuerlich, knapp und gesprochen -- kurze Saetze, keine "
    "Aufzaehlungen oder Markdown, keine Vorrede wie 'Konsolidierte Antwort'. "
    "Beantworte normale Konversation und einfache Fragen SELBST und kurz. "
    "Nutze das Tool 'delegate' nur fuer echte Fachaufgaben: an='cto' fuer Technik/Infrastruktur/Code, "
    "an='berater' fuer Strategie/Analyse/Markt. Fasse das Ergebnis danach in 1-3 Saetzen gesprochen zusammen. "
    "Nutze 'show_panel' (typ='kostenuebersicht'), wenn der CEO die Kosten-/Budgetuebersicht sehen will; "
    "sag dazu kurz, dass du sie einblendest. "
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
                voice=cfg.get("tts_voice_id") or _DEFAULT_ELEVEN_VOICE,
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
        description="Blendet dem CEO ein Panel im Browser ein. typ='kostenuebersicht' zeigt Budget und "
                    "Kostenstatistik aus finance/.",
        properties={"typ": {"type": "string", "enum": ["kostenuebersicht"]}},
        required=["typ"],
    )
    delegate = FunctionSchema(
        name="delegate",
        description="Delegiert eine echte Fachaufgabe an einen Spezialisten und liefert dessen Ergebnis. "
                    "Nur fuer echte Aufgaben, nicht fuer normale Konversation.",
        properties={
            "aufgabe": {"type": "string", "description": "Die Aufgabe in einem Satz."},
            "an": {"type": "string", "enum": ["cto", "berater"],
                   "description": "cto=Technik/Infrastruktur, berater=Strategie/Analyse."},
        },
        required=["aufgabe", "an"],
    )
    return ToolsSchema(standard_tools=[show_panel, delegate])


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

    async def on_show_panel(params):
        typ = (params.arguments or {}).get("typ", "kostenuebersicht")
        panel = build_panel(typ, finance_dir=finance_dir, secrets=leak_secrets)
        # Panel ueber den RTVI-Datenkanal an die Browser-Seite (parallel zur Sprache).
        await rtvi.push_frame(RTVIServerMessageFrame(data={"kind": "panel", "panel": panel}))
        await params.result_callback({"status": "eingeblendet", "typ": typ})

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
        sysp = spec.system_prompt if spec else ""
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, core.backend.respond, an, sysp, aufgabe, {})
        except Exception as exc:  # Backend-/API-Fehler nicht die Pipeline reissen lassen
            await params.result_callback({"fehler": str(exc)})
            return
        if core.changelog:
            core.changelog("Head of Agents", f"Voice-Delegation an {an}: {aufgabe}",
                           "CEO-Sprachkanal", f"Subagent: {an}")
        await params.result_callback({"ergebnis": redact(result, leak_secrets)})

    llm.register_function("show_panel", on_show_panel)
    llm.register_function("delegate", on_delegate, cancel_on_interruption=False)

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
