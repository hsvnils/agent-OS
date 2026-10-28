"""NETZ_AGENT Q3 -- Wachtest (CEO 2026-10-23: „alle anderen Agenten fuehren keine freien Websuchen durch“): Direkte Netz-
aufrufe im LUNA-Code gibt es nur noch an festgelegten Stellen fuer FESTE Schnittstellen (Telegram, Google-/Meta-/Supabase-
APIs, Boersen, EZB, OSV, Karten, Fritz!Box, ElevenLabs, GitHub-API, Artificial-Analysis-API). Freie Websuche und freie
Seitenabrufe laufen nur ueber den Netz-Agenten. Eine neue Stelle mit `urlopen` & Co. macht diesen Test rot -- dann
bewusst entscheiden: feste Schnittstelle (hier eintragen + docs/datenfluesse.md) oder ueber den Netz-Agenten."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NETZ_AUFRUFE = {"urlopen", "HTTPConnection", "HTTPSConnection", "build_opener", "create_connection"}
# Modul -> Funktionen, die direkt ins Netz duerfen (nur feste Schnittstellen)
ERLAUBT = {
    "channels/telegram/bot.py": {"_api", "_send_document", "_send_audio", "_download_voice", "_transcribe"},  # Telegram, Deepgram
    "channels/web/app.py": {"_elevenlabs_tts"},
    "core/alltag.py": {"elevenlabs_tts"},                 # ElevenLabs (LUNA-OS-Stimme; Briefing seit J2b lokal)
    "core/hoa_tools.py": {"_http"},                       # OSV.dev (CISO)
    "core/lokal_llm.py": {"erreichbar"},                  # Ollama im Heimnetz
    "core/modell_radar.py": {"aa_abrufen"},               # Artificial-Analysis-API (mit Schluessel)
    "core/netzwerk.py": {"_digest_opener", "_echt", "zertifikat_tage"},   # Fritz!Box, DSM, eigenes Zertifikat
    "core/routen.py": {"_json"},                          # Nominatim/OSRM
    "core/social_kit.py": {"_urllib_get"},                # Meta Graph (eigenes Konto)
    "core/wechselkurse.py": {"_http_csv"},                # EZB
    "governance/facebook_reels.py": {"_post"},
    "governance/github_watch.py": {"trending"},           # GitHub-API
    "governance/instagram.py": {"_get"},
    "governance/instagram_token.py": {"_http"},
    "governance/supabase.py": {"_http"},
    "investment/broker.py": {"_urllib"},                  # Alpaca (Papierkonto)
    "investment/providers.py": {"_http_json"},            # Kursdaten-APIs
}
VERBOTEN_TEXT = ("api.search.brave.com",)                 # freie Websuche nur im Netz-Agenten


def netzaufrufe(pfad: Path) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()

    def walk(knoten, fn="<modul>"):
        for k in ast.iter_child_nodes(knoten):
            f = k.name if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            if isinstance(k, ast.Call):
                n = k.func.attr if isinstance(k.func, ast.Attribute) else getattr(k.func, "id", "")
                wer = getattr(getattr(k.func, "value", None), "id", "")
                if n in NETZ_AUFRUFE or (n in ("get", "post", "request", "Client") and wer in ("requests", "httpx")):
                    out.add((f, n))
            walk(k, f)
    walk(ast.parse(pfad.read_text(encoding="utf-8")))
    return out


class TestNetzWache(unittest.TestCase):
    def test_nur_feste_schnittstellen_direkt(self):
        verstoesse = []
        for p in sorted(ROOT.rglob("*.py")):
            rel = p.relative_to(ROOT).as_posix()
            if rel.startswith("tests/"):
                continue
            for fn, n in netzaufrufe(p):
                if fn not in ERLAUBT.get(rel, set()):
                    verstoesse.append(f"{rel}:{fn} ({n})")
            text = p.read_text(encoding="utf-8")
            verstoesse += [f"{rel}: enthaelt {v}" for v in VERBOTEN_TEXT if v in text]
        self.assertEqual(verstoesse, [], "direkter Netzaufruf ausserhalb fester Schnittstellen -> ueber den Netz-Agenten "
                                         "oder bewusst als feste Schnittstelle eintragen")

    def test_freie_wege_laufen_ueber_den_netz_agenten(self):
        from orchestrator.core import firmendaten, modell_radar, rechtsquellen
        from orchestrator.governance.web_research import NetzProvider, WebResearch
        self.assertIsInstance(WebResearch.from_env({}).einfach, NetzProvider)
        for modul, fn in ((firmendaten, "_abruf"), (rechtsquellen, "_holen"), (modell_radar, "abrufen")):
            self.assertIn("NetzAuftraege", Path(modul.__file__).read_text(encoding="utf-8").split(f"def {fn}(", 1)[1][:900], fn)


if __name__ == "__main__":
    unittest.main()
