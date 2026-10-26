"""Sicherer Seitenabruf des Netz-Agenten (NETZ_AGENT Q1).

Nur http/https, nur Port 80/443, nur oeffentliche Adressen (jede aufgeloeste IP wird geprueft, und verbunden wird genau mit
der gepruefen IP -- kein zweiter DNS-Lookup, gegen DNS-Rebinding), Weiterleitungen werden einzeln neu geprueft (hoechstens
3), hoechstens `MAX_BYTES` und `TIMEOUT` Sekunden je Seite. HTML wird zu reinem Text (ohne Skripte/Stile).
Nur Standardbibliothek; importiert nichts aus LUNA.
"""
from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 1024 * 1024
MAX_ROH = 4 * 1024 * 1024            # Q3: Rohinhalt fuer regelbasierte Auswertung (Feeds, Gesetzestexte, Impressum)
ROH_TYPEN = ("text/", "application/xhtml", "application/xml", "application/rss+xml", "application/atom+xml")
TIMEOUT = 15
MAX_WEITER = 3
MAX_TEXT = 20000
AGENT = "LUNA-Netz-Agent/1.0 (+nur lesend)"


class Abgelehnt(ValueError):
    """Adresse oder Antwort verletzt eine Regel (privat, falscher Port/Schema, zu gross ...)."""


def _oeffentlich(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return a.is_global and not a.is_multicast


def pruefe_url(url: str, aufloesen=socket.getaddrinfo) -> tuple[str, str, int, str, str]:
    """-> (schema, host, port, pfad, gepruefte_ip). Wirft `Abgelehnt` bei jeder Regelverletzung."""
    t = urlsplit(url or "")
    if t.scheme not in ("http", "https"):
        raise Abgelehnt(f"Schema nicht erlaubt: {t.scheme or '-'}")
    if not t.hostname or t.username or t.password:
        raise Abgelehnt("Adresse ohne Host oder mit Zugangsdaten")
    port = t.port or (443 if t.scheme == "https" else 80)
    if port not in (80, 443):
        raise Abgelehnt(f"Port nicht erlaubt: {port}")
    try:
        ips = {x[4][0] for x in aufloesen(t.hostname, port, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise Abgelehnt(f"Host nicht aufloesbar: {t.hostname}") from exc
    if not ips or not all(_oeffentlich(ip) for ip in ips):
        raise Abgelehnt(f"Keine oeffentliche Adresse: {t.hostname}")
    pfad = (t.path or "/") + (f"?{t.query}" if t.query else "")
    bevorzugt = sorted(ips, key=lambda ip: (ipaddress.ip_address(ip).version, ip))[0]   # IPv4 zuerst (NAS/MACO ohne IPv6-Route)
    return t.scheme, t.hostname, port, pfad, bevorzugt


class _Http(http.client.HTTPConnection):
    def __init__(self, host, ip, port, timeout):
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _Https(http.client.HTTPSConnection):
    def __init__(self, host, ip, port, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self):
        roh = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(roh, server_hostname=self.host)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.teile, self.titel, self._weg, self._im_titel = [], "", 0, False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template", "svg"):
            self._weg += 1
        elif tag == "title":
            self._im_titel = True
        elif tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div"):
            self.teile.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template", "svg") and self._weg:
            self._weg -= 1
        elif tag == "title":
            self._im_titel = False

    def handle_data(self, data):
        if self._im_titel:
            self.titel += data
        elif not self._weg:
            self.teile.append(data)


def html_zu_text(html: str) -> tuple[str, str]:
    p = _Text()
    p.feed(html or "")
    zeilen = [" ".join(z.split()) for z in "".join(p.teile).splitlines()]
    return " ".join(p.titel.split()), "\n".join(z for z in zeilen if z)[:MAX_TEXT]


_META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?([A-Za-z0-9_.:-]+)""", re.I)
_XML_ENCODING = re.compile(rb"""<\?xml[^>]+encoding\s*=\s*["']([A-Za-z0-9_.:-]+)""", re.I)


def zeichensatz_von(art: str, koerper: bytes) -> str:
    """Zeichensatz: aus dem Content-Type, sonst aus <meta charset>/<?xml encoding> der ersten 4 KB, sonst UTF-8 (Q3: die
    Gesetzesseiten melden „text/html“ ohne Zeichensatz, sind aber ISO-8859-1 -- sonst wuerden Umlaute verfaelscht)."""
    if "charset=" in art:
        z = art.split("charset=", 1)[1].split(";")[0].strip().strip('"')
        if z:
            return z
    kopf = koerper[:4096]
    m = _META_CHARSET.search(kopf) or _XML_ENCODING.search(kopf)
    return m.group(1).decode("ascii", "replace") if m else "utf-8"


def hole(url: str, *, aufloesen=socket.getaddrinfo, verbindung=None, roh: bool = False) -> dict:
    """Seite holen -> {url, titel, text, status}. `roh=True` (Q3): unveraenderter Inhalt bis `MAX_ROH` (auch RSS/XML) fuer
    LUNAs regelbasierte Auswertung -- sonst reiner Text. Wirft `Abgelehnt` bei Regelverletzung."""
    for _ in range(MAX_WEITER + 1):
        schema, host, port, pfad, ip = pruefe_url(url, aufloesen)
        con = (verbindung or (_Https if schema == "https" else _Http))(host, ip, port, TIMEOUT)
        try:
            con.request("GET", pfad, headers={"User-Agent": AGENT, "Accept": "text/html,text/plain;q=0.9",
                                             "Accept-Encoding": "identity"})
            r = con.getresponse()
            if r.status in (301, 302, 303, 307, 308):
                ziel = r.getheader("Location") or ""
                url = urljoin(url, ziel)
                continue
            art = (r.getheader("Content-Type") or "").lower()
            erlaubt = art.startswith(ROH_TYPEN) if roh else (
                art.startswith("text/html") or art.startswith("text/plain") or art.startswith("application/xhtml"))
            if not erlaubt:
                raise Abgelehnt(f"Inhaltstyp nicht erlaubt: {art or '-'}")
            grenze = MAX_ROH if roh else MAX_BYTES
            koerper = r.read(grenze + 1)[:grenze]
            zeichensatz = zeichensatz_von(art, koerper)
            try:
                inhalt = koerper.decode(zeichensatz, "replace")
            except LookupError:
                inhalt = koerper.decode("utf-8", "replace")
            if roh:
                return {"url": url, "titel": "", "text": inhalt, "status": r.status, "typ": art.split(";")[0]}
            titel, text = html_zu_text(inhalt) if "html" in art else ("", inhalt[:MAX_TEXT])
            return {"url": url, "titel": titel[:300], "text": text, "status": r.status}
        finally:
            con.close()
    raise Abgelehnt("Zu viele Weiterleitungen")
