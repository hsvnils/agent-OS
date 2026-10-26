"""NETZ_AGENT Q4: Heimnetz-Sperre -- Sperrprobe (alle Heimnetz-Ziele zu, Internet offen), Zustandsdatei fuer LUNAs
Systemcheck, eigenes Docker-Netz und Sperr-Skript."""
import json
import re
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from netz_agent import sperrprobe
from netz_agent.agent import Agent

ROOT = Path(__file__).resolve().parents[2]


def verbinden_mit(offen: set):
    return lambda host, port, timeout: (host, port) in offen


class TestSperrprobe(unittest.TestCase):
    def test_1_gesperrt_und_gegenprobe(self):
        e = sperrprobe.pruefen(verbinden_mit({("api.search.brave.com", 443)}))
        self.assertEqual((e["heimnetz_gesperrt"], e["heimnetz_offen"], e["internet"]), (True, [], True))
        e = sperrprobe.pruefen(verbinden_mit({("api.search.brave.com", 443), ("192.168.178.129", 8765)}))
        self.assertEqual((e["heimnetz_gesperrt"], e["heimnetz_offen"]), (False, ["NAS LUNA-OS"]))
        self.assertFalse(sperrprobe.pruefen(verbinden_mit(set()))["internet"])           # sperrt zu viel
        ziele = {h for _, h, _ in sperrprobe.HEIMNETZ}
        self.assertTrue({"192.168.178.1", "192.168.178.129", "192.168.178.184", "luna-os"} <= ziele)

    def test_2_zustand_fuer_luna(self):
        from orchestrator.core.netz_auftraege import NetzAuftraege, sperre, zustand
        with tempfile.TemporaryDirectory() as d:
            a = Agent(d, "k")
            n = NetzAuftraege(d)
            self.assertEqual(sperre(n), (True, ""))                                      # noch keine Probe -> kein Alarm
            a.sperrprobe(lambda: sperrprobe.pruefen(verbinden_mit({("api.search.brave.com", 443)})))
            self.assertEqual(zustand(n), (True, ""))
            a.sperrprobe(lambda: sperrprobe.pruefen(verbinden_mit({("192.168.178.1", 80)})))
            ok, text = zustand(n)
            self.assertFalse(ok)
            self.assertIn("Heimnetz", text)
            alt = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            (Path(d) / "zustand.json").write_text(json.dumps({"heimnetz_gesperrt": True, "zeit": alt}))
            self.assertIn("aelter", sperre(n)[1])
            (Path(d) / "zustand.json").write_text("kaputt")
            self.assertFalse(sperre(n)[0])


class TestFailClosed(unittest.TestCase):
    def test_5_ohne_sperre_keine_auftraege(self):
        zu = lambda: sperrprobe.pruefen(verbinden_mit({("api.search.brave.com", 443)}))
        auf = lambda: sperrprobe.pruefen(verbinden_mit({("api.search.brave.com", 443), ("192.168.178.184", 22)}))
        with tempfile.TemporaryDirectory() as d:
            a = Agent(d, "k")
            self.assertFalse(a.bereit(jetzt=0, pruefen=auf))                           # Luecke -> pausiert
            self.assertFalse(a.bereit(jetzt=10, pruefen=zu))                           # erst nach 30 s neu geprueft
            self.assertTrue(a.bereit(jetzt=31, pruefen=zu))
            self.assertTrue(a.bereit(jetzt=200, pruefen=auf))                          # 5 min nicht neu geprueft
            self.assertFalse(a.bereit(jetzt=332, pruefen=auf))
        src = (ROOT / "netz_agent" / "agent.py").read_text(encoding="utf-8")
        self.assertIn("if not args.dry_run and not agent.bereit():", src)


class TestNetzUndSkript(unittest.TestCase):
    def test_3_eigenes_netz(self):
        compose = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
        block = re.search(r"\n  luna-netz:\n(.*?)(?=\n\S|\Z)", compose, re.S).group(1)
        self.assertIn("- netz_isoliert", block)
        self.assertNotIn("network_mode", block)
        self.assertIn("subnet: 172.30.99.0/24", compose)
        dns = re.search(r"dns:.*?\n((?:\s+- \S+\n)+)", block, re.S)                    # BF-77: kein Namensserver im Heimnetz
        self.assertIsNotNone(dns)
        self.assertFalse([z for z in re.findall(r"- (\S+)", dns.group(1)) if z.startswith(("192.168.", "10.", "172."))])
        for dienst in ("luna-telegram", "luna-os"):                                   # die anderen bleiben draussen
            b = re.search(rf"\n  {dienst}:\n(.*?)(?=\n  [a-z]|\n\S|\Z)", compose, re.S).group(1)
            self.assertNotIn("netz_isoliert", b)

    def test_4_skript(self):
        skript = ROOT / "deploy" / "netz_sperre.sh"
        self.assertEqual(subprocess.run(["bash", "-n", str(skript)]).returncode, 0)
        s = skript.read_text(encoding="utf-8")
        self.assertIn("NETZ=172.30.99.0/24", s)
        for z in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "127.0.0.0/8"):
            self.assertIn(z, s)
        self.assertIn('M="$IPT -t mangle"', s)                                        # BF-79: Sperre in mangle/PREROUTING
        self.assertIn("$M -I PREROUTING 1 -s $NETZ -j $KETTE", s)
        self.assertIn("weg mangle PREROUTING", s)                                     # Rueckweg
        self.assertNotIn("while", s)                                                  # BF-78: keine offene Schleife
        self.assertIn("aus()", s)
        self.assertIn('if aktiv; then', s)                                            # BF-80: Wiederholung ohne Luecke
        self.assertNotIn("-j REJECT", s)                                              # BF-75: Synology hat kein REJECT
        self.assertIn('-j DROP || exit 1', s)                                         # Fehler nicht verschlucken                                                     # Rueckweg vorhanden


if __name__ == "__main__":
    unittest.main()
