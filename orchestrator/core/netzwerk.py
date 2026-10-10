"""Netzwerk-Wache (NETZWERK_WACHE N1-N3, CEO 2026-10-10): Fritz!Box, NAS und Aussensicht -- **nur lesen und melden**.

- **Fritz!Box (N1):** TR-064 (SOAP, Digest-Anmeldung) mit **fester Allowlist von Lese-Aktionen** -- die Fritz!Box kennt kein
  reines Lese-Konto, deshalb verweigert `FritzBox.aufruf` jede Aktion ausserhalb der Liste (Test prueft das).
  Neue Geraete, Portfreigaben gegen die Soll-Liste, Firmware-Update, Internet-Ausfaelle, Fernzugang/UPnP, WLAN.
- **NAS (N2):** DSM-Web-API mit eigenem Konto (kein Admin ohne CEO-Entscheidung). Werte, die das Konto nicht lesen darf
  (DSM-Fehler 105), werden als „in DSM ansehen“ gezeigt statt zu fehlen.
- **Aussensicht (N3):** Zertifikat von LUNA-OS (Ablauf), DDNS zeigt auf die aktuelle oeffentliche IP.

Alles regelbasiert, kein LLM. Zustand in `netzwerk/` (nur NAS, nicht in der Kette, loeschbar, im Backup). Gemeldet wird
jeder Befund **einmal** (bis er verschwindet und wiederkommt).
"""
from __future__ import annotations

import json
import os
import re
import socket
import ssl
import tempfile
import threading
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

# -- Fritz!Box (TR-064) --------------------------------------------------------------------------------------------
_STEUER = {"Hosts:1": "/upnp/control/hosts", "DeviceInfo:1": "/upnp/control/deviceinfo", "UserInterface:1": "/upnp/control/userif",
           "WANIPConnection:1": "/upnp/control/wanipconnection1", "WANPPPConnection:1": "/upnp/control/wanpppconn1",
           "X_AVM-DE_RemoteAccess:1": "/upnp/control/x_remote", "X_AVM-DE_UPnP:1": "/upnp/control/x_upnp",
           "WLANConfiguration:1": "/upnp/control/wlanconfig1", "WLANConfiguration:2": "/upnp/control/wlanconfig2",
           "WLANConfiguration:3": "/upnp/control/wlanconfig3"}
# NUR diese Aktionen -- alle lesen nur (FRITZ!Box 7530 AX, FRITZ!OS 8.25; geprueft an /tr64desc.xml am 2026-10-10).
FRITZ_LESEN = frozenset({
    ("Hosts:1", "X_AVM-DE_GetHostListPath"), ("Hosts:1", "GetHostNumberOfEntries"), ("Hosts:1", "GetGenericHostEntry"),
    ("DeviceInfo:1", "GetInfo"), ("UserInterface:1", "GetInfo"),
    ("X_AVM-DE_RemoteAccess:1", "GetInfo"), ("X_AVM-DE_UPnP:1", "GetInfo"),
    ("WLANConfiguration:1", "GetInfo"), ("WLANConfiguration:2", "GetInfo"), ("WLANConfiguration:3", "GetInfo"),
} | {(w, a) for w in ("WANIPConnection:1", "WANPPPConnection:1")
     for a in ("GetStatusInfo", "GetExternalIPAddress", "GetPortMappingNumberOfEntries", "GetGenericPortMappingEntry")})


class NurLesen(PermissionError):
    """Aktion steht nicht auf der Lese-Liste -- wird nie gesendet."""


def _digest_opener(basis: str, user: str, passwort: str):
    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, basis, user, passwort)
    return urllib.request.build_opener(urllib.request.HTTPDigestAuthHandler(mgr))


class FritzBox:
    def __init__(self, url: str, user: str, passwort: str, *, http=None):
        """`http(url, body: bytes|None, headers) -> str` austauschbar (Tests ohne Netz)."""
        self.basis = (url or "http://192.168.178.1:49000").rstrip("/")
        self._http = http or self._echt(user, passwort)

    def _echt(self, user, passwort):
        opener = _digest_opener(self.basis, user, passwort)

        def call(url, body=None, headers=None):
            if not url.startswith(self.basis + "/"):                     # nie eine fremde Adresse
                raise NurLesen(url)
            with opener.open(urllib.request.Request(url, data=body, headers=headers or {}), timeout=15) as r:
                return r.read().decode("utf-8", "replace")
        return call

    def aufruf(self, service: str, aktion: str, **args) -> dict:
        if (service, aktion) not in FRITZ_LESEN:
            raise NurLesen(f"{service}#{aktion} ist keine erlaubte Lese-Aktion")
        typ = f"urn:dslforum-org:service:{service}"
        argumente = "".join(f"<{k}>{v}</{k}>" for k, v in args.items())
        body = (f'<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
                f's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:{aktion} xmlns:u="{typ}">{argumente}'
                f'</u:{aktion}></s:Body></s:Envelope>').encode()
        text = self._http(self.basis + _STEUER[service], body,
                          {"Content-Type": 'text/xml; charset="utf-8"', "SOAPAction": f'"{typ}#{aktion}"'})
        root = ET.fromstring(text)
        antwort = next((e for e in root.iter() if e.tag.endswith(aktion + "Response")), None)
        if antwort is None:
            raise ValueError(f"Fritz!Box: keine Antwort auf {aktion}")
        return {c.tag.split("}")[-1]: (c.text or "") for c in antwort}

    def geraete(self) -> list[dict]:
        pfad = self.aufruf("Hosts:1", "X_AVM-DE_GetHostListPath").get("NewX_AVM-DE_HostListPath", "")
        if not pfad.startswith("/"):
            raise ValueError("Fritz!Box: Geraeteliste nicht verfuegbar")
        root = ET.fromstring(self._http(self.basis + pfad, None, {}))
        out = []
        for item in root.iter("Item"):
            f = {c.tag: (c.text or "") for c in item}
            mac = (f.get("MACAddress") or "").upper()
            if not mac:
                continue
            out.append({"mac": mac, "ip": f.get("IPAddress", ""), "name": f.get("HostName", ""), "aktiv": f.get("Active") == "1",
                        "schnittstelle": f.get("InterfaceType", ""), "gast": f.get("X_AVM-DE_Guest") == "1"})
        return out

    def portfreigaben(self) -> list[dict]:
        out, gesehen = [], set()
        for svc in ("WANPPPConnection:1", "WANIPConnection:1"):
            try:
                n = int(self.aufruf(svc, "GetPortMappingNumberOfEntries").get("NewPortMappingNumberOfEntries") or 0)
            except Exception:
                continue
            for i in range(min(n, 64)):
                e = self.aufruf(svc, "GetGenericPortMappingEntry", NewPortMappingIndex=i)
                schluessel = (e.get("NewProtocol"), e.get("NewExternalPort"))
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                out.append({"protokoll": e.get("NewProtocol", ""), "extern": e.get("NewExternalPort", ""),
                            "ziel": e.get("NewInternalClient", ""), "intern": e.get("NewInternalPort", ""),
                            "aktiv": e.get("NewEnabled") == "1", "name": e.get("NewPortMappingDescription", "")})
        return out

    def zustand(self) -> dict:
        z: dict = {"fehler": []}

        def teil(name, fn):
            try:
                z[name] = fn()
            except NurLesen:
                raise
            except Exception as exc:
                z["fehler"].append(f"{name}: {exc.__class__.__name__}")

        teil("geraet", lambda: {k: v for k, v in self.aufruf("DeviceInfo:1", "GetInfo").items()
                                if k in ("NewModelName", "NewSoftwareVersion", "NewUpTime")})
        teil("update", lambda: (lambda d: {"verfuegbar": d.get("NewUpgradeAvailable") == "1",
                                           "version": d.get("NewX_AVM-DE_Version", "")})(self.aufruf("UserInterface:1", "GetInfo")))
        teil("internet", self._internet)
        teil("fernzugang", lambda: (lambda d: {"an": d.get("NewEnabled") == "1", "port": d.get("NewPort", "")})(
            self.aufruf("X_AVM-DE_RemoteAccess:1", "GetInfo")))
        teil("upnp", lambda: {"an": self.aufruf("X_AVM-DE_UPnP:1", "GetInfo").get("NewEnable") == "1"})
        teil("wlan", lambda: [{"nr": i, "ssid": d.get("NewSSID", ""), "an": d.get("NewEnable") == "1"}
                              for i in (1, 2, 3) for d in [self.aufruf(f"WLANConfiguration:{i}", "GetInfo")]])
        teil("geraete", self.geraete)
        teil("ports", self.portfreigaben)
        return z

    def _internet(self) -> dict:
        for svc in ("WANPPPConnection:1", "WANIPConnection:1"):
            try:
                s = self.aufruf(svc, "GetStatusInfo")
                ip = self.aufruf(svc, "GetExternalIPAddress").get("NewExternalIPAddress", "")
            except Exception:
                continue
            if s.get("NewConnectionStatus") == "Connected" or svc == "WANIPConnection:1":
                return {"verbunden": s.get("NewConnectionStatus") == "Connected", "seit_s": int(s.get("NewUptime") or 0), "ip": ip}
        raise ValueError("Internet-Status nicht lesbar")


# -- NAS (Synology DSM) ---------------------------------------------------------------------------------------------
DSM_LESEN = frozenset({("SYNO.API.Auth", "login"), ("SYNO.API.Auth", "logout"), ("SYNO.Core.System", "info"),
                       ("SYNO.Storage.CGI.Storage", "load_info"), ("SYNO.Core.Upgrade.Server", "check"),
                       ("SYNO.Core.SecurityScan.Status", "system_get"), ("SYNO.Core.Security.AutoBlock.Rules", "list"),
                       ("SYNO.Core.SyslogClient.Log", "list")})


class DsmFehler(Exception):
    def __init__(self, code):
        super().__init__(f"DSM-Fehler {code}")
        self.code = code


class Dsm:
    def __init__(self, url: str, user: str, passwort: str, *, http=None):
        self.basis = (url or "http://192.168.178.129:5000").rstrip("/")
        self.user, self.passwort, self.sid = user, passwort, ""
        self._http = http or self._echt

    def _echt(self, url, body=None, headers=None):
        if not url.startswith(self.basis + "/"):
            raise NurLesen(url)
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE               # nur NAS im LAN (eigene Adresse)
        with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers or {}), timeout=20,
                                    context=ctx if url.startswith("https") else None) as r:
            return r.read().decode("utf-8", "replace")

    def aufruf(self, api: str, methode: str, version: int = 1, **params) -> dict:
        if (api, methode) not in DSM_LESEN:
            raise NurLesen(f"{api}.{methode} ist keine erlaubte Lese-Abfrage")
        p = {"api": api, "method": methode, "version": version, **params} | ({"_sid": self.sid} if self.sid else {})
        body = urllib.parse.urlencode(p).encode()                             # Passwort im Body, nie in der URL
        d = json.loads(self._http(self.basis + "/webapi/entry.cgi", body, {"Content-Type": "application/x-www-form-urlencoded"}))
        if not d.get("success"):
            raise DsmFehler((d.get("error") or {}).get("code"))
        return d.get("data") or {}

    def anmelden(self) -> None:
        self.sid = self.aufruf("SYNO.API.Auth", "login", 6, account=self.user, passwd=self.passwort, session="LUNAWache",
                               format="sid")["sid"]

    def abmelden(self) -> None:
        try:
            self.aufruf("SYNO.API.Auth", "logout", 6, session="LUNAWache")
        except Exception:
            pass
        self.sid = ""

    def zustand(self) -> dict:
        z: dict = {"fehler": [], "ohne_rechte": []}
        self.anmelden()
        try:
            def teil(name, fn):
                try:
                    z[name] = fn()
                except DsmFehler as exc:
                    (z["ohne_rechte"] if exc.code in (105, 119) else z["fehler"]).append(name)
                except Exception as exc:
                    z["fehler"].append(f"{name}: {exc.__class__.__name__}")
            teil("system", lambda: {k: v for k, v in self.aufruf("SYNO.Core.System", "info", 3).items()
                                    if k in ("model", "firmware_ver", "up_time", "sys_temp")})
            teil("speicher", self._speicher)
            teil("update", lambda: (lambda d: {"verfuegbar": bool(d.get("available")), "version": (d.get("version") or "")})(
                self.aufruf("SYNO.Core.Upgrade.Server", "check", 1)))
            teil("sicherheitsberater", lambda: (lambda d: {"stufe": str(d.get("sysStatus") or d.get("status") or ""),
                                                           "zuletzt": d.get("lastScanTime", "")})(
                self.aufruf("SYNO.Core.SecurityScan.Status", "system_get", 1)))
            teil("gesperrt", lambda: [r.get("ip") or r.get("ip4") or "" for r in
                                      (self.aufruf("SYNO.Core.Security.AutoBlock.Rules", "list", 1, type="deny").get("rules") or [])])
            teil("anmeldefehler", self._anmeldefehler)
        finally:
            self.abmelden()
        return z

    def _speicher(self) -> dict:
        d = self.aufruf("SYNO.Storage.CGI.Storage", "load_info", 1)
        platten = [{"name": p.get("name") or p.get("id", ""), "zustand": p.get("overview_status") or p.get("status", ""),
                    "smart": p.get("smart_status", ""), "temp": p.get("temp")} for p in d.get("disks") or []]
        volumes = []
        for v in d.get("volumes") or []:
            gross = int(((v.get("size") or {}).get("total")) or 0)
            belegt = int(((v.get("size") or {}).get("used")) or 0)
            volumes.append({"name": v.get("id") or v.get("vol_path", ""), "zustand": v.get("status", ""),
                            "frei_prozent": round(100 * (gross - belegt) / gross, 1) if gross else None})
        return {"platten": platten, "volumes": volumes}

    def _anmeldefehler(self) -> int:
        d = self.aufruf("SYNO.Core.SyslogClient.Log", "list", 1, logtype="connection", start=0, limit=200)
        grenze = datetime.now() - timedelta(hours=24)
        n = 0
        for e in d.get("items") or []:
            text = str(e.get("descr") or e.get("msg") or "").lower()
            try:
                t = datetime.fromtimestamp(int(e.get("time"))) if str(e.get("time", "")).isdigit() \
                    else datetime.fromisoformat(str(e.get("time"))[:19].replace("/", "-"))
            except (ValueError, TypeError):
                t = datetime.now()
            if t >= grenze and ("failed to log" in text or "fehlgeschlagen" in text or "failed to sign" in text):
                n += 1
        return n


# -- Aussensicht (N3) -----------------------------------------------------------------------------------------------
def zertifikat_tage(host: str, *, adresse: str = "", port: int = 443, verbinden=None) -> int:
    """Resttage des Zertifikats von `host` (SNI). `adresse` = direkt die NAS ansprechen (kein Umweg ueber den Router)."""
    if verbinden is not None:
        cert = verbinden(host, adresse, port)
    else:
        ctx = ssl.create_default_context()
        with socket.create_connection((adresse or host, port), timeout=10) as s, ctx.wrap_socket(s, server_hostname=host) as t:
            cert = t.getpeercert()
    ablauf = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), tz=timezone.utc)
    return (ablauf - datetime.now(timezone.utc)).days


def dns_ip(host: str, *, aufloesen=None) -> str:
    return (aufloesen or socket.gethostbyname)(host)


# -- Regeln: Befunde ------------------------------------------------------------------------------------------------
STUFEN = {"ok": 0, "info": 1, "warn": 2, "alarm": 3}


def _b(schluessel, stufe, bereich, text, **details) -> dict:
    return {"schluessel": schluessel, "stufe": stufe, "bereich": bereich, "text": text, "details": details}


def befunde_fritz(z: dict, *, ports_soll: set[str]) -> list[dict]:
    out = []
    u = z.get("update") or {}
    if u.get("verfuegbar"):
        out.append(_b(f"fritz-update-{u.get('version')}", "warn", "Fritz!Box",
                      f"Fritz!Box: Update auf FRITZ!OS {u.get('version') or 'neu'} verfügbar – bitte in der Fritz!Box installieren."))
    for p in z.get("ports") or []:
        if p["aktiv"] and str(p["extern"]) not in ports_soll:
            out.append(_b(f"port-{p['protokoll']}-{p['extern']}", "alarm", "Fritz!Box",
                          f"Unerwartete Portfreigabe: {p['protokoll']} {p['extern']} → {p['ziel']}:{p['intern']}"
                          + (f" ({p['name']})" if p["name"] else "") + " – gewollt?", **p))
    f = z.get("fernzugang") or {}
    if f.get("an"):
        out.append(_b("fritz-fernzugang", "warn", "Fritz!Box", f"Fernzugang zur Fritz!Box aus dem Internet ist an (Port {f.get('port')})."))
    if (z.get("upnp") or {}).get("an"):
        out.append(_b("fritz-upnp", "info", "Fritz!Box", "UPnP ist an (Geräte können sich selbst Freigaben holen)."))
    for e in z.get("fehler") or []:
        out.append(_b(f"fritz-fehler-{e.split(':')[0]}", "info", "Fritz!Box", f"Fritz!Box: {e} nicht lesbar."))
    return out


def befunde_dsm(z: dict, *, frei_min: float = 15.0, fehlversuche_max: int = 5) -> list[dict]:
    out = []
    u = z.get("update") or {}
    if u.get("verfuegbar"):
        out.append(_b(f"dsm-update-{u.get('version')}", "warn", "NAS", f"NAS: DSM-Update {u.get('version') or ''} verfügbar.".replace("  ", " ")))
    sp = z.get("speicher") or {}
    for p in sp.get("platten") or []:
        if str(p.get("zustand")).lower() not in ("normal", "") or str(p.get("smart")).lower() not in ("normal", "", "safe"):
            out.append(_b(f"platte-{p['name']}-{p.get('zustand')}", "alarm", "NAS",
                          f"NAS-Platte {p['name']}: Zustand {p.get('zustand')}, SMART {p.get('smart') or '–'}."))
    for v in sp.get("volumes") or []:
        if str(v.get("zustand")).lower() not in ("normal", ""):
            out.append(_b(f"volume-{v['name']}-{v.get('zustand')}", "alarm", "NAS", f"NAS-Volume {v['name']}: {v.get('zustand')}."))
        if v.get("frei_prozent") is not None and v["frei_prozent"] < frei_min:
            out.append(_b(f"volume-{v['name']}-voll", "warn", "NAS", f"NAS-Volume {v['name']}: nur noch {v['frei_prozent']} % frei."))
    for ip in z.get("gesperrt") or []:
        out.append(_b(f"gesperrt-{ip}", "info", "NAS", f"NAS hat die Adresse {ip} nach Fehlversuchen gesperrt."))
    if (z.get("anmeldefehler") or 0) >= fehlversuche_max:
        out.append(_b(f"anmeldefehler-{datetime.now():%Y-%m-%d}", "warn", "NAS",
                      f"NAS: {z['anmeldefehler']} fehlgeschlagene Anmeldungen in 24 Stunden."))
    sb = z.get("sicherheitsberater") or {}
    if str(sb.get("stufe")).lower() in ("danger", "risk", "warning", "outofdate"):
        out.append(_b(f"sicherheitsberater-{sb.get('stufe')}", "warn", "NAS", f"Sicherheitsberater meldet: {sb.get('stufe')} – in DSM ansehen."))
    if z.get("ohne_rechte"):
        out.append(_b("dsm-rechte-" + "-".join(sorted(z["ohne_rechte"])), "info", "NAS",
                      "Für diese NAS-Werte fehlen dem Konto die Rechte (in DSM ansehen): " + ", ".join(sorted(z["ohne_rechte"]))))
    for e in z.get("fehler") or []:
        out.append(_b(f"dsm-fehler-{e.split(':')[0]}", "info", "NAS", f"NAS: {e} nicht lesbar."))
    return out


def befunde_aussen(*, zert_tage: int | None, dns: str, wan_ip: str, host: str, tage_min: int = 21) -> list[dict]:
    out = []
    if zert_tage is not None and zert_tage < tage_min:
        out.append(_b(f"zertifikat-{zert_tage // 7}", "alarm" if zert_tage < 7 else "warn", "Aussen",
                      f"Zertifikat von {host} läuft in {zert_tage} Tagen ab – Erneuerung in DSM prüfen."))
    if dns and wan_ip and dns != wan_ip:
        out.append(_b(f"ddns-{wan_ip}", "warn", "Aussen", f"{host} zeigt auf {dns}, die Fritz!Box hat aber {wan_ip} – DDNS prüfen."))
    return out


# -- Zustand (netzwerk/) ----------------------------------------------------------------------------------------------
_LOCK = threading.Lock()


class Wache:
    def __init__(self, ordner: Path):
        self.dir = Path(ordner)

    def _lesen(self, name: str) -> dict:
        try:
            return json.loads((self.dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _schreiben(self, name: str, d: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix="." + name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.dir / name)

    def geraete(self) -> dict:
        return self._lesen("geraete.json")

    def zustand(self) -> dict:
        return self._lesen("zustand.json")

    def geraete_abgleichen(self, liste: list[dict], jetzt: str) -> list[dict]:
        """Neue MACs eintragen; beim allerersten Lauf alles als Bestand (bekannt), danach neue = unbekannt -> Rueckgabe."""
        with _LOCK:
            g = self._lesen("geraete.json")
            erster = not g
            neu = []
            for x in liste:
                alt = g.get(x["mac"])
                if alt:
                    alt |= {"ip": x["ip"], "schnittstelle": x["schnittstelle"], "gast": x["gast"]} | (
                        {"zuletzt": jetzt, "fritz_name": x["name"]} if x["aktiv"] else {})
                    continue
                g[x["mac"]] = {"mac": x["mac"], "name": x["name"], "fritz_name": x["name"], "ip": x["ip"],
                               "schnittstelle": x["schnittstelle"], "gast": x["gast"], "erst": jetzt,
                               "zuletzt": jetzt if x["aktiv"] else "", "bekannt": True if erster else None,
                               "quelle": "Bestand beim Start" if erster else ""}
                if not erster and x["aktiv"]:
                    neu.append(g[x["mac"]])
            self._schreiben("geraete.json", g)
        return [] if erster else neu

    def geraet_setzen(self, mac: str, *, bekannt: bool | None = None, name: str | None = None) -> dict:
        mac = _mac(mac)
        with _LOCK:
            g = self._lesen("geraete.json")
            if mac not in g:
                raise KeyError(mac)
            if bekannt is not None:
                g[mac]["bekannt"] = bool(bekannt)
            if name is not None:
                n = " ".join(str(name).split())[:60]
                if not n:
                    raise ValueError("Name darf nicht leer sein.")
                g[mac]["name"] = n
            self._schreiben("geraete.json", g)
        return g[mac]

    def geraet_loeschen(self, mac: str) -> None:
        with _LOCK:
            g = self._lesen("geraete.json")
            if g.pop(_mac(mac), None) is None:
                raise KeyError(mac)
            self._schreiben("geraete.json", g)

    def befunde_merken(self, bereich: str, befunde: list[dict], jetzt: str, *, roh: dict | None = None) -> list[dict]:
        """Befunde eines Bereichs speichern -> nur die **neuen** (seit dem letzten Lauf nicht offen) zurueckgeben."""
        with _LOCK:
            z = self._lesen("zustand.json")
            alt = {b["schluessel"] for b in (z.get("bereiche", {}).get(bereich, {}).get("befunde") or [])}
            z.setdefault("bereiche", {})[bereich] = {"ts": jetzt, "befunde": befunde} | ({"roh": roh} if roh is not None else {})
            self._schreiben("zustand.json", z)
        return [b for b in befunde if b["schluessel"] not in alt]

    def internet_merken(self, verbunden: bool, jetzt: datetime) -> dict | None:
        """Ausfall erkennen: gibt nach der Rueckkehr {von, bis, minuten} zurueck, wenn er >= 10 min dauerte."""
        with _LOCK:
            z = self._lesen("zustand.json")
            weg = z.get("internet_weg_seit")
            ergebnis = None
            if not verbunden and not weg:
                z["internet_weg_seit"] = jetzt.isoformat(timespec="seconds")
            elif verbunden and weg:
                von = datetime.fromisoformat(weg)
                minuten = int((jetzt - von).total_seconds() // 60)
                z.pop("internet_weg_seit")
                if minuten >= 10:
                    ergebnis = {"von": weg, "bis": jetzt.isoformat(timespec="seconds"), "minuten": minuten}
            self._schreiben("zustand.json", z)
        return ergebnis


def _mac(m: str) -> str:
    h = re.sub(r"[^0-9A-Fa-f]", "", str(m or "")).upper()
    if len(h) != 12:
        raise KeyError(m)
    return ":".join(h[i:i + 2] for i in range(0, 12, 2))


def mac_kurz(m: str) -> str:
    return re.sub(r"[^0-9A-F]", "", str(m).upper())


def ampel(zustand: dict) -> dict:
    """Je Bereich die hoechste offene Stufe (fuer die Kachel)."""
    out = {}
    for bereich, d in (zustand.get("bereiche") or {}).items():
        stufen = [STUFEN[b["stufe"]] for b in d.get("befunde") or []]
        out[bereich] = next((k for k, v in STUFEN.items() if v == max(stufen)), "ok") if stufen else "ok"
    return out


def einstellungen(sec: dict) -> dict:
    """Schalter und Adressen aus der .env (ohne Passwoerter)."""
    an = lambda k: str(sec.get(k, "")).strip().lower() in ("1", "true", "yes", "on", "ja")
    return {"aktiv": an("NETZWERK_WACHE"),
            "fritz": bool(sec.get("FRITZBOX_USER") and sec.get("FRITZBOX_PASSWORD")),
            "dsm": bool(sec.get("DSM_USER") and sec.get("DSM_PASSWORD")),
            "fritz_url": sec.get("FRITZBOX_URL") or "http://192.168.178.1:49000",
            "dsm_url": sec.get("DSM_URL") or "http://192.168.178.129:5000",
            "host": sec.get("NETZWERK_ZERT_HOST") or "os.hanserautisch.synology.me",
            "zert_adresse": sec.get("NETZWERK_ZERT_ADRESSE") or "192.168.178.129",
            "ports_soll": {p.strip() for p in str(sec.get("NETZWERK_PORTS_SOLL") or "443").split(",") if p.strip()}}


# -- Laeufe (vom Bot aufgerufen) --------------------------------------------------------------------------------------
def _melden(befunde: list[dict]) -> list[str]:
    return [("🚨 " if b["stufe"] == "alarm" else "⚠️ ") + b["text"] for b in befunde if STUFEN[b["stufe"]] >= STUFEN["warn"]]


def lauf_fritz(wache: Wache, fritz: FritzBox, *, ports_soll: set[str], jetzt: datetime) -> dict:
    """15-min-Lauf: -> {meldungen: [text], neue_geraete: [geraet], bestand: n|None, wan_ip}."""
    ts = jetzt.isoformat(timespec="seconds")
    z = fritz.zustand()
    out: dict = {"meldungen": [], "neue_geraete": [], "bestand": None, "wan_ip": (z.get("internet") or {}).get("ip", "")}
    if "geraete" in z:
        vorher = bool(wache.geraete())
        out["neue_geraete"] = wache.geraete_abgleichen(z["geraete"], ts)
        if not vorher:
            out["bestand"] = len(z["geraete"])
    if "internet" in z:
        a = wache.internet_merken(bool(z["internet"]["verbunden"]), jetzt)
        if a:
            out["meldungen"].append(f"🌐 Internet war weg: {a['von'][11:16]}–{a['bis'][11:16]} Uhr ({a['minuten']} min).")
    roh = {k: z.get(k) for k in ("geraet", "update", "internet", "fernzugang", "upnp", "wlan", "ports")}
    out["meldungen"] += _melden(wache.befunde_merken("fritz", befunde_fritz(z, ports_soll=ports_soll), ts, roh=roh))
    return out


def lauf_taeglich(wache: Wache, *, dsm: Dsm | None, host: str, zert_adresse: str, wan_ip: str, jetzt: datetime,
                  zert=None, dns=None) -> list[str]:
    """Taeglich 06:00: NAS (N2) und Aussensicht (N3) -> neue Meldungen."""
    ts, meldungen = jetzt.isoformat(timespec="seconds"), []
    zert, dns = zert or zertifikat_tage, dns or dns_ip
    if dsm is not None:
        try:
            z = dsm.zustand()
            b = befunde_dsm(z)
        except DsmFehler as exc:
            z, b = {}, [_b(f"dsm-anmeldung-{exc.code}", "warn", "NAS", f"NAS: Anmeldung der Netzwerk-Wache klappt nicht ({exc}).")]
        except Exception as exc:
            z, b = {}, [_b("dsm-nicht-erreichbar", "warn", "NAS", f"NAS-Abfrage nicht erreichbar ({exc.__class__.__name__}).")]
        meldungen += _melden(wache.befunde_merken("nas", b, ts, roh={k: z.get(k) for k in ("system", "speicher", "update",
                                                                                              "sicherheitsberater", "ohne_rechte")}))
    try:
        tage = zert(host, adresse=zert_adresse)
    except Exception:
        tage = None
    try:
        d = dns(host)
    except Exception:
        d = ""
    b = befunde_aussen(zert_tage=tage, dns=d, wan_ip=wan_ip, host=host)
    if tage is None:
        b.append(_b("zertifikat-nicht-lesbar", "info", "Aussen", f"Zertifikat von {host} nicht lesbar."))
    meldungen += _melden(wache.befunde_merken("aussen", b, ts, roh={"zert_tage": tage, "dns": d, "wan_ip": wan_ip}))
    return meldungen


def geraet_text(g: dict) -> str:
    wo = "Gastnetz" if g.get("gast") else (g.get("schnittstelle") or "Netz")
    return f"🆕 Neues Gerät im Netz: {g.get('name') or 'ohne Namen'} ({g.get('ip') or '–'}, {wo}, {g['mac']})."
