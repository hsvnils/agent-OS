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
    "Du bist LUNA, der Head of Agents des Hanserautisch Agenten-Unternehmens, und sprichst direkt mit dem "
    "CEO (Nils) per Sprache. Sprich Deutsch, natuerlich, knapp und gesprochen -- kurze Saetze, keine "
    "Aufzaehlungen oder Markdown, keine Vorrede wie 'Konsolidierte Antwort'. "
    "Beantworte normale Konversation und einfache Fragen SELBST und kurz. "
    "Du hast Fachagenten unter dir und kannst jeden per Tool 'delegate' konsultieren (an=cto Technik, "
    "berater Strategie, cfo Finanzen, cro Umsatz, ciso Sicherheit, cbo Marke, cpo Produkt, cxo UX, "
    "cco Content, cdo Daten, chro Personal, clo Recht, cko Wissen, cao Administration). Nutze 'delegate' "
    "nur fuer echte Fachfragen/Aufgaben; kuendige kurz an ('Einen Moment, ich frage den ... ') und fasse "
    "das Ergebnis danach in 1-3 Saetzen gesprochen zusammen. "
    "Wenn der CEO dir ein Monatsbudget nennt, bestaetige die Zahl kurz und trage sie dann mit 'set_budget' "
    "ueber den CFO in finance/budget.md ein. "
    "Aenderungen/Beschaffungen/Ideen laufen ueber Antraege: Will eine Abteilung oder du selbst etwas "
    "aendern, stelle einen Antrag ('antrag_stellen') -- er wird NICHT ausgefuehrt, sondern dem CEO zur "
    "Freigabe vorgelegt. Auf 'zeig mir die Antraege' nutze 'antraege_zeigen'. Einen Antrag gibst du nur "
    "frei ('antrag_freigeben'), wenn der CEO es ausdruecklich sagt -- bestaetige vorher kurz ('Ich gebe "
    "Antrag X frei, richtig?'); ablehnen via 'antrag_ablehnen'. "
    "Umsetzung (Phase 7): Stammt der Auftrag vom CEO, genuegt eine kurze Rueckfrage 'Soll ich das machen?'; "
    "bei einer Idee aus einer Abteilung legst du dem CEO ZUERST den Plan dar (was + wie), dann erst Freigabe. "
    "Einen freigegebenen Antrag setzt du mit 'antrag_umsetzen' real um (Branch + Tests, kein Merge) und fasst "
    "den Bericht gesprochen zusammen (Status, Tests, was zu pruefen). Nach main bringst du ihn nur mit "
    "'antrag_mergen' nach ausdruecklicher CEO-Bestaetigung -- oder der CEO merged selbst in Git. "
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
    antrag_stellen = FunctionSchema(
        name="antrag_stellen",
        description="Reicht einen Antrag (Aenderungs-/Beschaffungs-/Idee-Vorschlag) ein -- auch "
                    "stellvertretend fuer eine Abteilung. Wird NICHT ausgefuehrt, nur dem CEO zur Freigabe "
                    "vorgelegt.",
        properties={
            "titel": {"type": "string", "description": "Kurztitel des Antrags."},
            "beschreibung": {"type": "string", "description": "Was und warum, in 1-2 Saetzen."},
            "von": {"type": "string", "description": "Welche Abteilung/Rolle (z. B. cto, cfo, HoA)."},
            "kategorie": {"type": "string",
                          "description": "Falls CEO-Tor beruehrt: geld|recht|oeffentlichkeit|tools|mandat|daten."},
        },
        required=["titel", "beschreibung"],
    )
    antraege_zeigen = FunctionSchema(
        name="antraege_zeigen",
        description="Zeigt die Antraege als Panel und nennt sie kurz. status optional (z. B. 'eingereicht').",
        properties={"status": {"type": "string", "description": "Optionaler Status-Filter."}},
        required=[],
    )
    antrag_freigeben = FunctionSchema(
        name="antrag_freigeben",
        description="Gibt einen Antrag frei -- NUR nach ausdruecklicher CEO-Bestaetigung. Bestaetige vorher "
                    "gesprochen ('Ich gebe Antrag X frei, richtig?'). Fuehrt noch nichts aus (das ist Phase 7).",
        properties={"antrag_id": {"type": "string", "description": "Die Antrag-ID."}},
        required=["antrag_id"],
    )
    antrag_ablehnen = FunctionSchema(
        name="antrag_ablehnen",
        description="Lehnt einen Antrag ab -- nach CEO-Entscheidung. Mit kurzer Begruendung.",
        properties={
            "antrag_id": {"type": "string", "description": "Die Antrag-ID."},
            "grund": {"type": "string", "description": "Kurze Begruendung."},
        },
        required=["antrag_id"],
    )
    antrag_umsetzen = FunctionSchema(
        name="antrag_umsetzen",
        description="Setzt einen FREIGEGEBENEN Antrag real um (Phase 7): isolierter Git-Branch, ein "
                    "Ausfuehrungs-Agent aendert die Dateien, Self-Checks laufen. Kuendige kurz an ('Ich setze "
                    "das jetzt um, einen Moment') -- dauert ggf. ~1 Minute. Es wird NICHT nach main gemergt.",
        properties={"antrag_id": {"type": "string", "description": "Die Antrag-ID (Status freigegeben)."}},
        required=["antrag_id"],
    )
    antrag_mergen = FunctionSchema(
        name="antrag_mergen",
        description="Mergt den Branch eines ERLEDIGTEN Antrags nach main -- NUR nach ausdruecklicher "
                    "CEO-Bestaetigung. Bestaetige vorher kurz gesprochen.",
        properties={"antrag_id": {"type": "string", "description": "Die Antrag-ID (Status erledigt)."}},
        required=["antrag_id"],
    )
    return ToolsSchema(standard_tools=[
        show_panel, frage_finance, delegate, set_budget,
        antrag_stellen, antraege_zeigen, antrag_freigeben, antrag_ablehnen,
        antrag_umsetzen, antrag_mergen,
    ])


def build_pipeline(transport, core, cfg: dict, secrets: dict, *, finance_dir, leak_secrets,
                   antraege_path, repo_root):
    """Baut die Conversation-Pipeline + Task. `core` ist der HoA-Kern (fuer delegate/Changelog/CEO-Tor)."""
    from ...core.antraege import Antraege
    from ...core.execution import ExecutionEngine
    from ...core import execution_live as live
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
    antraege = Antraege(antraege_path, secrets=leak_secrets, changelog=core.changelog)
    engine = ExecutionEngine(
        antraege,
        make_workspace=live.real_make_workspace(repo_root),
        run_agent=live.real_run_agent(model=cfg.get("exec_model", "claude-opus-4-8")),
        run_tests=live.real_run_tests(),
        diff=live.real_diff(),
        secrets=leak_secrets, changelog=core.changelog,
    )

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
        # Bis Phase 7 (Execution-Engine) koennen Fachagenten nur BERATEN, nicht handeln/Dateien aendern.
        # Diese Vorgabe verhindert, dass der Agent eine Aktion zu erzwingen versucht und das Turn-Budget
        # aufbraucht ("Reached maximum number of turns").
        beratungs_aufgabe = (
            "Beantworte als zustaendiger Fachagent KNAPP in Text. Du kannst derzeit NICHT selbst handeln, "
            "ausfuehren oder Dateien/Code aendern (das laeuft spaeter ueber den Freigabe-Workflow); liefere "
            "nur Rat bzw. den gewuenschten Inhalt als Text.\n\nAufgabe: " + aufgabe
        )
        loop = asyncio.get_running_loop()
        await emit_activity(an, "start")  # Live-Anzeige: HoA spricht mit diesem Agenten
        try:
            result = await loop.run_in_executor(
                None, core.backend.respond, an, spec.system_prompt, beratungs_aufgabe, {}
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

    async def on_antrag_stellen(params):
        a = params.arguments or {}
        aid = antraege.stellen(
            (a.get("titel") or "").strip(), (a.get("beschreibung") or "").strip(),
            von=(a.get("von") or "Head of Agents").strip(), kategorie=(a.get("kategorie") or "").strip(),
        )
        await params.result_callback({"antrag_id": aid, "status": "eingereicht"})

    async def on_antraege_zeigen(params):
        status = (params.arguments or {}).get("status") or None
        items = antraege.list(status)
        panel = {"type": "antraege", "title": "Antraege",
                 "antraege": [{"id": x["antrag_id"], "titel": x.get("titel", ""),
                               "von": x.get("von", ""), "status": x.get("status", ""),
                               "kategorie": x.get("kategorie", "")} for x in items]}
        await rtvi.push_frame(RTVIServerMessageFrame(data={"kind": "panel", "panel": panel}))
        await params.result_callback({"anzahl": len(items), "antraege": panel["antraege"]})

    async def on_antrag_freigeben(params):
        aid = str((params.arguments or {}).get("antrag_id", "")).strip()
        ok = antraege.freigeben(aid)
        await params.result_callback({"ok": ok, "antrag_id": aid, "status": "freigegeben" if ok else None,
                                      "hinweis": "" if ok else "Antrag-ID nicht gefunden."})

    async def on_antrag_ablehnen(params):
        a = params.arguments or {}
        aid = str(a.get("antrag_id", "")).strip()
        ok = antraege.ablehnen(aid, grund=(a.get("grund") or "").strip())
        await params.result_callback({"ok": ok, "antrag_id": aid, "status": "abgelehnt" if ok else None})

    async def on_antrag_umsetzen(params):
        aid = str((params.arguments or {}).get("antrag_id", "")).strip()
        loop = asyncio.get_running_loop()
        try:
            res = await loop.run_in_executor(None, engine.umsetzen, aid)
        except Exception as exc:
            await params.result_callback({"ok": False, "fehler": str(exc)[:200]})
            return
        # Bei Erfolg den Branch committen, damit er mergebar ist.
        if res.ok and res.status == "erledigt":
            ws = str(repo_root / ".worktrees" / f"antrag-{aid}")
            await loop.run_in_executor(None, live.commit_branch, ws, f"Antrag {aid}: umgesetzt")
        await params.result_callback(
            {"ok": res.ok, "status": res.status, "branch": res.branch,
             "bericht": redact(res.bericht, leak_secrets)}
        )

    async def on_antrag_mergen(params):
        aid = str((params.arguments or {}).get("antrag_id", "")).strip()
        a = antraege.get(aid)
        if not a or a.get("status") != "erledigt":
            await params.result_callback(
                {"ok": False, "hinweis": "Nur erledigte Antraege koennen gemergt werden."})
            return
        loop = asyncio.get_running_loop()
        ok, out = await loop.run_in_executor(
            None, live.merge_branch, repo_root, f"antrag/{aid}", f"Merge Antrag {aid}")
        if ok and core.changelog:
            core.changelog("CEO", f"Antrag {aid} nach main gemergt", "CEO-Bestaetigung", f"antrag/{aid}")
        await params.result_callback({"ok": ok, "ausgabe": redact(out, leak_secrets)})

    llm.register_function("show_panel", on_show_panel)
    llm.register_function("frage_finance", on_frage_finance)
    llm.register_function("delegate", on_delegate, cancel_on_interruption=False)
    llm.register_function("set_budget", on_set_budget, cancel_on_interruption=False)
    llm.register_function("antrag_stellen", on_antrag_stellen, cancel_on_interruption=False)
    llm.register_function("antraege_zeigen", on_antraege_zeigen)
    llm.register_function("antrag_freigeben", on_antrag_freigeben, cancel_on_interruption=False)
    llm.register_function("antrag_ablehnen", on_antrag_ablehnen, cancel_on_interruption=False)
    llm.register_function("antrag_umsetzen", on_antrag_umsetzen, cancel_on_interruption=False)
    llm.register_function("antrag_mergen", on_antrag_mergen, cancel_on_interruption=False)

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
