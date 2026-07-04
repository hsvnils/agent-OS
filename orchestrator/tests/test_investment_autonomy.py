import unittest

from orchestrator.investment.autonomy_policy import AutonomyPolicy, Leitplanken


def _ok_trade():
    return {"symbol": "AAPL", "asset": "aktie", "side": "buy", "betrag_eur": 40.0,
            "konfidenz": 0.75, "risiko_label": "konservativ", "signale": 2}


def _ok_kontext():
    return {"equity": 5000.0, "nacht_budget_genutzt": 0.0, "trades_im_fenster": 0,
            "tagesverlust_pct": 0.0, "kill_switch": False, "autonomie_freigeschaltet": True}


class TestAutonomyPolicy(unittest.TestCase):
    def setUp(self):
        self.p = AutonomyPolicy()

    def _check(self, urteil, name):
        return next(c for c in urteil["checks"] if c["name"] == name)

    def test_sauberer_trade_ist_autonom(self):
        u = self.p.pruefe(_ok_trade(), _ok_kontext())
        self.assertTrue(u["erlaubt_autonom"])
        self.assertFalse(u["benoetigt_freigabe"])

    def test_niedrige_konfidenz_braucht_freigabe(self):
        t = _ok_trade(); t["konfidenz"] = 0.5
        u = self.p.pruefe(t, _ok_kontext())
        self.assertFalse(u["erlaubt_autonom"])
        self.assertFalse(self._check(u, "konfidenz")["ok"])

    def test_ein_signal_reicht_nicht(self):
        t = _ok_trade(); t["signale"] = 1
        self.assertFalse(self.p.pruefe(t, _ok_kontext())["erlaubt_autonom"])

    def test_spekulativ_braucht_freigabe(self):
        t = _ok_trade(); t["risiko_label"] = "spekulativ"
        u = self.p.pruefe(t, _ok_kontext())
        self.assertFalse(u["erlaubt_autonom"])
        self.assertFalse(self._check(u, "risiko_label")["ok"])

    def test_position_zu_gross(self):
        t = _ok_trade(); t["betrag_eur"] = 80.0   # > 50 EUR und > 2% von 5000 (=100? 80<100 ok pct) -> eur-gate
        self.assertFalse(self.p.pruefe(t, _ok_kontext())["erlaubt_autonom"])

    def test_position_pct_gate(self):
        t = _ok_trade(); t["betrag_eur"] = 40.0
        k = _ok_kontext(); k["equity"] = 1000.0   # 40/1000 = 4% > 2%
        u = self.p.pruefe(t, k)
        self.assertFalse(self._check(u, "position_pct")["ok"])

    def test_nicht_auf_whitelist(self):
        t = _ok_trade(); t["symbol"] = "MEMECOIN"
        u = self.p.pruefe(t, _ok_kontext())
        self.assertFalse(u["erlaubt_autonom"])
        self.assertFalse(self._check(u, "whitelist")["ok"])

    def test_nacht_budget_erschoepft(self):
        k = _ok_kontext(); k["nacht_budget_genutzt"] = 180.0  # + 40 = 220 > 200
        self.assertFalse(self.p.pruefe(_ok_trade(), k)["erlaubt_autonom"])

    def test_trade_frequenz_deckel(self):
        k = _ok_kontext(); k["trades_im_fenster"] = 3
        u = self.p.pruefe(_ok_trade(), k)
        self.assertFalse(self._check(u, "trade_frequenz")["ok"])

    def test_kill_switch_blockt_kauf(self):
        k = _ok_kontext(); k["kill_switch"] = True
        self.assertFalse(self.p.pruefe(_ok_trade(), k)["erlaubt_autonom"])

    def test_tagesverlust_stop_blockt(self):
        k = _ok_kontext(); k["tagesverlust_pct"] = 3.5
        u = self.p.pruefe(_ok_trade(), k)
        self.assertFalse(self._check(u, "tagesverlust")["ok"])

    def test_track_record_nicht_freigeschaltet(self):
        k = _ok_kontext(); k["autonomie_freigeschaltet"] = False
        self.assertFalse(self.p.pruefe(_ok_trade(), k)["erlaubt_autonom"])

    def test_verkauf_immer_erlaubt_auch_unter_killswitch(self):
        t = _ok_trade(); t["side"] = "sell"
        k = _ok_kontext(); k["kill_switch"] = True
        u = self.p.pruefe(t, k)
        self.assertTrue(u["erlaubt_autonom"])   # risikoreduzierend

    def test_konfiguration_liste(self):
        cfg = self.p.konfiguration()
        self.assertTrue(any("Nacht-Budget" in c["label"] for c in cfg))

    def test_eigene_leitplanken(self):
        p = AutonomyPolicy(lp=Leitplanken(max_position_eur=100.0))
        t = _ok_trade(); t["betrag_eur"] = 80.0
        self.assertTrue(p.pruefe(t, _ok_kontext())["erlaubt_autonom"])


if __name__ == "__main__":
    unittest.main()
