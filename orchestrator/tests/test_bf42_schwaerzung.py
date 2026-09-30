"""BF-42: Schalterwerte aus der .env (0/1) duerfen nicht als Geheimnis geschwaerzt werden; verstuemmelte
Altzeilen im Investment-Loop gelten als unbrauchbar; CIO-Statusmeldungen gehen nicht mehr per Telegram."""
import json
from pathlib import Path

from orchestrator.governance.leak_guard import REDACTED, redact
from orchestrator.investment.loop_store import LoopStore

ECHT = "sk-live-abcdefghijklmnop"
ENV_WERTE = ["0", "1", "true", "hsvnils@icloud.com", "8594240885", ECHT]


def test_redact_ignoriert_schalter_und_kurze_werte():
    text = f"datum 2026-09-30 close 101.0 key {ECHT} mail hsvnils@icloud.com"
    aus = redact(text, ENV_WERTE)
    assert "2026-09-30" in aus and "101.0" in aus and "hsvnils@icloud.com" in aus
    assert ECHT not in aus and REDACTED in aus


def test_loop_store_schreibt_mit_ungefilterten_env_werten_sauber(tmp_path):
    st = LoopStore(tmp_path / "f.jsonl", secrets=ENV_WERTE)
    st.feature_add("AAPL", "aktie", "2026-09-30", 101.0, 1.0, {"ret_1d": 0.1})
    assert st.has_feature("AAPL", "2026-09-30")
    assert st.last_datum("inv_features") == "2026-09-30"
    assert REDACTED not in (tmp_path / "f.jsonl").read_text()


def test_verstuemmelte_altzeilen_werden_uebersprungen_und_gezaehlt(tmp_path):
    pfad = tmp_path / "f.jsonl"
    kaputt = {"ts": "2026-09-29T05:00:00", "tabelle": "inv_features", "symbol": "AAPL", "asset": "aktie",
              "datum": f"2{REDACTED}26-{REDACTED}9-29", "close": 3.5}
    heil = {"ts": "2026-09-28T05:00:00", "tabelle": "inv_features", "symbol": "AAPL", "asset": "aktie",
            "datum": "2026-09-28", "close": 3.5}
    pfad.write_text(json.dumps(heil) + "\n" + json.dumps(kaputt) + "\n"
                    + '{"close": 4.8' + REDACTED + '}\n', encoding="utf-8")
    st = LoopStore(pfad)
    assert [e["datum"] for e in st.list("inv_features")] == ["2026-09-28"]
    assert st.last_datum("inv_features") == "2026-09-28"
    assert st.verstuemmelt() == 2


def test_cio_statusmeldungen_nicht_mehr_per_telegram():
    quelle = (Path(__file__).resolve().parents[1] / "channels" / "telegram" / "bot.py").read_text(encoding="utf-8")
    for q in ("feature-loop", "loop-insider", "loop-abgleich", "loop-prognose", "Markt-Screen erledigt"):
        assert q not in quelle, q
    assert "_feature_datum != datum" in quelle
