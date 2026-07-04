import unittest

from orchestrator.investment.auto_trader import AutoTrader, ist_nacht_chance
from orchestrator.investment.autonomy_policy import AutonomyPolicy, Leitplanken


def _trade(**kw):
    t = {"symbol": "AAPL", "asset": "aktie", "side": "buy", "betrag_eur": 40.0,
         "konfidenz": 0.75, "risiko_label": "konservativ", "signale": 2}
    t.update(kw)
    return t


def _kontext(**kw):
    k = {"equity": 100000.0, "nacht_budget_genutzt": 0.0, "trades_im_fenster": 0,
         "tagesverlust_pct": 0.0, "kill_switch": False, "autonomie_freigeschaltet": True}
    k.update(kw)
    return k


class TestAutoTrader(unittest.TestCase):
    def setUp(self):
        self.a = AutoTrader()

    def test_sauber_und_freigeschaltet_ist_auto(self):
        self.assertEqual(self.a.entscheide(_trade(), _kontext())["aktion"], "auto")

    def test_nicht_freigeschaltet_fragt_um_freigabe(self):
        d = self.a.entscheide(_trade(), _kontext(autonomie_freigeschaltet=False))
        self.assertEqual(d["aktion"], "freigabe")

    def test_schwache_konfidenz_fragt_um_freigabe(self):
        d = self.a.entscheide(_trade(konfidenz=0.5), _kontext())
        self.assertEqual(d["aktion"], "freigabe")

    def test_kill_switch_ueberspringt(self):
        d = self.a.entscheide(_trade(), _kontext(kill_switch=True))
        self.assertEqual(d["aktion"], "skip")

    def test_tagesverlust_ueberspringt(self):
        d = self.a.entscheide(_trade(), _kontext(tagesverlust_pct=3.5))
        self.assertEqual(d["aktion"], "skip")

    def test_nicht_whitelist_fragt_um_freigabe_nicht_auto(self):
        d = self.a.entscheide(_trade(symbol="MEME"), _kontext())
        self.assertEqual(d["aktion"], "freigabe")


class TestNachtChance(unittest.TestCase):
    def _c(self, **kw):
        c = {"konfidenz": 0.85, "signale_zahl": 3, "ziel_return_pct": 9.0, "asset": "krypto"}
        c.update(kw)
        return c

    def test_top_chance_besteht(self):
        self.assertTrue(ist_nacht_chance(self._c()))

    def test_zu_niedrige_konfidenz_faellt_durch(self):
        self.assertFalse(ist_nacht_chance(self._c(konfidenz=0.75)))

    def test_nicht_alle_signale_faellt_durch(self):
        self.assertFalse(ist_nacht_chance(self._c(signale_zahl=2)))

    def test_zu_kleines_ziel_faellt_durch(self):
        self.assertFalse(ist_nacht_chance(self._c(ziel_return_pct=4.0)))


class TestNachtKryptoLeitplanke(unittest.TestCase):
    def test_krypto_kann_autonom_werden_wenn_freigeschaltet(self):
        # spekulativ + nur_konservativ=False (Nacht) -> nach Track-Record autonom
        trader = AutoTrader(AutonomyPolicy(lp=Leitplanken.nacht_krypto(), whitelist=set()))
        trade = {"symbol": "BTC/USD", "asset": "krypto", "side": "buy", "betrag_eur": 20.0,
                 "konfidenz": 0.85, "risiko_label": "spekulativ", "signale": 3}
        kontext = {"equity": 100000.0, "nacht_budget_genutzt": 0.0, "trades_im_fenster": 0,
                   "tagesverlust_pct": 0.0, "kill_switch": False, "autonomie_freigeschaltet": True}
        self.assertEqual(trader.entscheide(trade, kontext)["aktion"], "auto")

    def test_krypto_ohne_track_record_fragt(self):
        trader = AutoTrader(AutonomyPolicy(lp=Leitplanken.nacht_krypto(), whitelist=set()))
        trade = {"symbol": "BTC/USD", "asset": "krypto", "side": "buy", "betrag_eur": 20.0,
                 "konfidenz": 0.85, "risiko_label": "spekulativ", "signale": 3}
        kontext = {"equity": 100000.0, "nacht_budget_genutzt": 0.0, "trades_im_fenster": 0,
                   "tagesverlust_pct": 0.0, "kill_switch": False, "autonomie_freigeschaltet": False}
        self.assertEqual(trader.entscheide(trade, kontext)["aktion"], "freigabe")


if __name__ == "__main__":
    unittest.main()
