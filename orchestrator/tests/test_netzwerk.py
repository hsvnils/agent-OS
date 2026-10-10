"""NETZWERK_WACHE N1-N3 (CEO 2026-10-10): Fritz!Box (TR-064, nur Lese-Allowlist), NAS (DSM-API), Aussensicht --
nur lesen und melden, jeder Befund einmal, neue Geraete mit Knoepfen, Uebersicht nur fuer Administratoren."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from orchestrator.core import netzwerk as nw

HOSTS = """<List><Item><Index>1</Index><IPAddress>192.168.178.129</IPAddress><MACAddress>00:11:32:aa:bb:cc</MACAddress>
<Active>1</Active><HostName>NAS</HostName><InterfaceType>Ethernet</InterfaceType><X_AVM-DE_Guest>0</X_AVM-DE_Guest></Item>
<Item><Index>2</Index><IPAddress>192.168.178.30</IPAddress><MACAddress>AA:BB:CC:00:00:01</MACAddress><Active>1</Active>
<HostName>iPhone</HostName><InterfaceType>802.11</InterfaceType><X_AVM-DE_Guest>0</X_AVM-DE_Guest></Item></List>"""


class FakeFritz:
    """Antwortet wie die Fritz!Box 7530 AX auf die erlaubten Lese-Aktionen; merkt sich jede Anfrage."""
    def __init__(self, hosts=HOSTS, ports=(("TCP", "443", "192.168.178.129", "443", "LUNA-OS"),), update="0", verbunden=True):
        self.hosts, self.ports, self.update, self.verbunden, self.anfragen = hosts, list(ports), update, verbunden, []

    def __call__(self, url, body=None, headers=None):
        aktion = (headers or {}).get("SOAPAction", "").strip('"').split("#")[-1]
        self.anfragen.append(aktion or url)
        if not aktion:
            return self.hosts
        werte = {"X_AVM-DE_GetHostListPath": {"NewX_AVM-DE_HostListPath": "/devicehostlist.lua?sid=1"},
                 "GetInfo": {"NewModelName": "FRITZ!Box 7530 AX", "NewSoftwareVersion": "256.08.25", "NewUpgradeAvailable": self.update,
                             "NewX_AVM-DE_Version": "256.08.30", "NewEnabled": "0", "NewPort": "", "NewEnable": "1", "NewSSID": "Heim"},
                 "GetStatusInfo": {"NewConnectionStatus": "Connected" if self.verbunden else "Disconnected", "NewUptime": "3600"},
                 "GetExternalIPAddress": {"NewExternalIPAddress": "203.0.113.7"},
                 "GetPortMappingNumberOfEntries": {"NewPortMappingNumberOfEntries": str(len(self.ports))}}
        if aktion == "GetGenericPortMappingEntry":
            i = int(body.decode().split("<NewPortMappingIndex>")[1].split("<")[0])
            p = self.ports[i]
            w = {"NewProtocol": p[0], "NewExternalPort": p[1], "NewInternalClient": p[2], "NewInternalPort": p[3],
                 "NewEnabled": "1", "NewPortMappingDescription": p[4]}
        else:
            w = werte[aktion]
        inner = "".join(f"<{k}>{v}</{k}>" for k, v in w.items())
        return (f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
                f'<u:{aktion}Response xmlns:u="urn:x">{inner}</u:{aktion}Response></s:Body></s:Envelope>')


class FakeDsm:
    def __init__(self, frei=40.0, rechte=True):
        self.frei, self.rechte, self.anfragen = frei, rechte, []

    def __call__(self, url, body=None, headers=None):
        p = dict(x.split("=", 1) for x in body.decode().split("&"))
        self.anfragen.append((p["api"], p["method"]))
        ok = lambda d: json.dumps({"success": True, "data": d})
        if p["api"] == "SYNO.API.Auth":
            return ok({"sid": "S1"} if p["method"] == "login" else {})
        if p["api"] == "SYNO.Core.SecurityScan.Status" and not self.rechte:
            return json.dumps({"success": False, "error": {"code": 105}})
        gross = 1000
        return ok({"SYNO.Core.System": {"model": "DS923+", "firmware_ver": "DSM 7.2.2"},
                   "SYNO.Storage.CGI.Storage": {"disks": [{"name": "Laufwerk 1", "overview_status": "normal", "smart_status": "normal"}],
                                                "volumes": [{"id": "volume_1", "status": "normal",
                                                             "size": {"total": gross, "used": int(gross * (100 - self.frei) / 100)}}]},
                   "SYNO.Core.Upgrade.Server": {"available": False},
                   "SYNO.Core.SecurityScan.Status": {"sysStatus": "safe"},
                   "SYNO.Core.Security.AutoBlock.Rules": {"rules": []},
                   "SYNO.Core.SyslogClient.Log": {"items": []}}[p["api"]])


class TestNurLesen(unittest.TestCase):
    def test_1_allowlist(self):
        for svc, aktion in nw.FRITZ_LESEN:
            self.assertTrue(aktion.startswith(("Get", "X_AVM-DE_Get")), aktion)
        for api, methode in nw.DSM_LESEN:
            self.assertIn(methode, ("login", "logout", "info", "load_info", "check", "system_get", "list"))
        fake = FakeFritz()
        f = nw.FritzBox("http://fritz:49000", "u", "p", http=fake)
        for svc, aktion in (("Hosts:1", "X_AVM-DE_SetHostNameByMACAddress"), ("WANPPPConnection:1", "AddPortMapping"),
                            ("DeviceConfig:1", "Reboot"), ("WLANConfiguration:1", "SetEnable")):
            with self.assertRaises(nw.NurLesen):
                f.aufruf(svc, aktion)
        self.assertEqual(fake.anfragen, [])                                     # nie gesendet
        with self.assertRaises(nw.NurLesen):
            nw.Dsm("http://nas:5000", "u", "p", http=FakeDsm()).aufruf("SYNO.Core.Upgrade", "start")

    def test_2_fritz_zustand(self):
        z = nw.FritzBox("http://fritz:49000", "u", "p", http=FakeFritz(update="1")).zustand()
        self.assertEqual(z["fehler"], [])
        self.assertEqual([(g["mac"], g["name"], g["schnittstelle"]) for g in z["geraete"]],
                         [("00:11:32:AA:BB:CC", "NAS", "Ethernet"), ("AA:BB:CC:00:00:01", "iPhone", "802.11")])
        self.assertEqual((z["internet"]["ip"], z["update"], z["ports"][0]["extern"]), ("203.0.113.7", {"verfuegbar": True, "version": "256.08.30"}, "443"))


class TestRegeln(unittest.TestCase):
    def test_3_befunde(self):
        z = nw.FritzBox("http://f:49000", "u", "p", http=FakeFritz(update="1", ports=(
            ("TCP", "443", "192.168.178.129", "443", "LUNA-OS"), ("TCP", "22", "192.168.178.30", "22", "ssh")))).zustand()
        b = nw.befunde_fritz(z, ports_soll={"443"})
        self.assertEqual(sorted((x["stufe"], x["schluessel"]) for x in b),
                         [("alarm", "port-TCP-22"), ("info", "fritz-upnp"), ("warn", "fritz-update-256.08.30")])
        d = nw.Dsm("http://nas:5000", "u", "p", http=FakeDsm(frei=9.0, rechte=False)).zustand()
        self.assertEqual(d["ohne_rechte"], ["sicherheitsberater"])
        b = nw.befunde_dsm(d)
        self.assertEqual(sorted(x["stufe"] for x in b), ["info", "warn"])          # Volume fast voll + fehlende Rechte
        a = nw.befunde_aussen(zert_tage=5, dns="203.0.113.9", wan_ip="203.0.113.7", host="os.example")
        self.assertEqual(sorted(x["stufe"] for x in a), ["alarm", "warn"])
        self.assertEqual(nw.befunde_aussen(zert_tage=60, dns="1.2.3.4", wan_ip="1.2.3.4", host="x"), [])

    def test_4_einmal_melden_und_geraete(self):
        w = nw.Wache(Path(tempfile.mkdtemp()) / "netzwerk")
        g1 = [{"mac": "AA:00:00:00:00:01", "ip": "1", "name": "A", "aktiv": True, "schnittstelle": "802.11", "gast": False}]
        self.assertEqual(w.geraete_abgleichen(g1, "t1"), [])                    # erster Lauf = Bestand, keine Flut
        self.assertTrue(w.geraete()["AA:00:00:00:00:01"]["bekannt"])
        neu = w.geraete_abgleichen(g1 + [dict(g1[0], mac="AA:00:00:00:00:02", name="B")], "t2")
        self.assertEqual([x["name"] for x in neu], ["B"])
        self.assertEqual(w.geraete_abgleichen(g1 + [dict(g1[0], mac="AA:00:00:00:00:02", name="B")], "t3"), [])
        w.geraet_setzen("aa0000000002", name="Tablet", bekannt=True)
        self.assertEqual(w.geraete()["AA:00:00:00:00:02"]["name"], "Tablet")
        b = [nw._b("x", "warn", "NAS", "X")]
        self.assertEqual(len(w.befunde_merken("nas", b, "t1")), 1)
        self.assertEqual(w.befunde_merken("nas", b, "t2"), [])                    # nicht doppelt
        w.befunde_merken("nas", [], "t3")
        self.assertEqual(len(w.befunde_merken("nas", b, "t4")), 1)                 # wieder da -> wieder melden
        t = datetime(2026, 10, 10, 12, 0)
        self.assertIsNone(w.internet_merken(False, t))
        self.assertIsNone(w.internet_merken(False, t + timedelta(minutes=5)))
        self.assertEqual(w.internet_merken(True, t + timedelta(minutes=25))["minuten"], 25)
        w.internet_merken(False, t + timedelta(hours=1))
        self.assertIsNone(w.internet_merken(True, t + timedelta(hours=1, minutes=3)))   # kurzer Aussetzer: still


class TestBot(unittest.TestCase):
    def test_5_lauf_und_knoepfe(self):
        from orchestrator.channels.telegram import bot
        w = nw.Wache(Path(tempfile.mkdtemp()) / "netzwerk")
        gesendet = []
        sec = {"NETZWERK_WACHE": "1"}
        fake = FakeFritz()
        with mock.patch.object(bot, "_api", side_effect=lambda t, m, p: gesendet.append((m, p))), \
                mock.patch.object(bot, "_netzwerk_wache", return_value=w), \
                mock.patch.object(nw, "zertifikat_tage", return_value=60), mock.patch.object(nw, "dns_ip", return_value="203.0.113.7"):
            f = nw.FritzBox("http://f:49000", "u", "p", http=fake)
            bot.netzwerk_lauf("T", "1", sec, taeglich=False, fritz=f)
            self.assertIn("2 Geräte als Bestand", gesendet[-1][1]["text"])
            n = len(gesendet)
            bot.netzwerk_lauf("T", "1", sec, taeglich=False, fritz=f)
            self.assertEqual(len(gesendet), n)                                   # nichts Neues -> still
            fake.hosts = HOSTS.replace("</List>", "<Item><IPAddress>192.168.178.77</IPAddress><MACAddress>DE:AD:BE:EF:00:01</MACAddress>"
                                                  "<Active>1</Active><HostName>unbekannt</HostName><InterfaceType>802.11</InterfaceType></Item></List>")
            fake.ports.append(("TCP", "8080", "192.168.178.77", "80", "x"))
            bot.netzwerk_lauf("T", "1", sec, taeglich=False, fritz=f)
            texte = [p["text"] for m, p in gesendet[n:]]
            self.assertTrue(any("Unerwartete Portfreigabe: TCP 8080" in t for t in texte), texte)
            kb = json.loads(gesendet[-1][1]["reply_markup"])["inline_keyboard"][0]
            self.assertEqual([b["callback_data"] for b in kb], ["nwg:DEADBEEF0001:ok", "nwg:DEADBEEF0001:no"])
            self.assertEqual(bot._netzwerk_klick("T", "1", "nwg:DEADBEEF0001:no", 9), "OK")
            self.assertFalse(w.geraete()["DE:AD:BE:EF:00:01"]["bekannt"])
            n = len(gesendet)
            bot.netzwerk_lauf("T", "1", sec, taeglich=True, fritz=f, dsm=nw.Dsm("http://nas:5000", "u", "p", http=FakeDsm(frei=9.0)))
            self.assertTrue(any("nur noch 9.0 % frei" in p.get("text", "") for m, p in gesendet[n:]), [p.get("text") for m, p in gesendet[n:]])
        self.assertTrue(all(a.startswith(("Get", "X_AVM-DE_Get", "http://f:49000/devicehostlist")) for a in fake.anfragen) and not any(a.startswith(("Set", "Add", "Delete", "X_AVM-DE_Set")) for a in fake.anfragen), fake.anfragen)


class TestApi(unittest.TestCase):
    def test_6_uebersicht_rechte_und_ciso(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.security_agent import SecurityAgent
        from orchestrator.core.team_auth import modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("GET", "/api/netzwerk"), "administration")
        root = Path(tempfile.mkdtemp())
        w = nw.Wache(root / "netzwerk")
        w.geraete_abgleichen([{"mac": "AA:00:00:00:00:01", "ip": "1", "name": "A", "aktiv": True, "schnittstelle": "", "gast": False}], "t")
        w.befunde_merken("fritz", [nw._b("port-TCP-22", "alarm", "Fritz!Box", "Unerwartete Portfreigabe: TCP 22")], "t")
        c = TestClient(webapp.app)
        with mock.patch.object(webapp, "_netzwerk", return_value=w), mock.patch.object(webapp, "_google_secrets", return_value={}):
            d = c.get("/api/netzwerk").json()
            self.assertEqual((d["ampel"], len(d["geraete"]), d["einstellungen"]["aktiv"]), ({"fritz": "alarm"}, 1, False))
            self.assertNotIn("FRITZBOX_PASSWORD", json.dumps(d))
            self.assertTrue(c.post("/api/netzwerk/geraete/AA:00:00:00:00:01", json={"name": "Router-Test"}).json()["ok"])
            self.assertFalse(c.post("/api/netzwerk/geraete/AA:00:00:00:00:01", json={"name": "  "}).json()["ok"])
        self.assertEqual(w.geraete()["AA:00:00:00:00:01"]["name"], "Router-Test")
        f = SecurityAgent(repo_root=root, env={}, run=lambda c: "")._check_netzwerk()
        self.assertEqual([(x.kategorie, x.schwere) for x in f], [("netzwerk", "hoch")])


if __name__ == "__main__":
    unittest.main()
