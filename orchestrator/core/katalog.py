"""Leistungskatalog (KUNDEN_FINANZEN_ROADMAP.md, Etappe 3b): Formate, Pakete, Zuschlaege und Textbausteine fuer
Angebote und Preisliste -- uebernommen aus dem Preislisten-Generator des CEO (Stand 2026-09-27).

Liegt nur auf der NAS (`buchhaltung/katalog.json`, nie im oeffentlichen Git); fehlt die Datei, gilt `STANDARD`.
Jede Aenderung in LUNA-OS wird als Eintrag `katalog_geaendert` in der Buchhaltungs-Kette protokolliert (wer, wann,
welche Preise). Angebote kopieren Preise und Texte beim Anlegen -- spaetere Katalogaenderungen aendern nichts an
bestehenden Angeboten. Betraege in Cent.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re

from .buchhaltung import Buchhaltung


def _p(id_, name, basis, euro, hinweis="", einheit=""):
    return {"id": id_, "name": name, "basis": basis, "preis_cent": int(euro * 100), "hinweis": hinweis,
            "einheit": einheit, "aktiv": True}


# Datenbasis laut Generator: Instagram/Facebook/Stories = Median der letzten 90 Tage aus den Meta-Suite-Exporten;
# Kanaele ohne Export (X, TikTok, YouTube, Twitch, WhatsApp, App) = Stand laut Media-Kit, konservativ bepreist.
STANDARD = {
    "gruppen": [
        {"name": "Instagram", "farbe": "blau", "items": [
            _p("reel_solo", "Reel, Standalone", "Ø 37.000 Aufrufe je Reel", 1600,
               "Eigenes Reel, exklusiv für Ihre Marke konzipiert und produziert"),
            _p("reel_int", "Reel, Integration", "Ø 37.000 Aufrufe je Reel", 1050,
               "Ihre Marke wird nativ in ein redaktionelles Reel eingebunden"),
            _p("feed", "Feed-Post oder Karussell", "Ø 52.000 Aufrufe je Beitrag", 1300, "Bleibt dauerhaft im Profil sichtbar"),
            _p("story", "Story-Serie, 3 Frames", "Ø 34.000 Kontakte je Serie", 600, "Mit Link-Sticker direkt zu Ihrer Zielseite"),
        ]},
        {"name": "Facebook", "farbe": "blau", "items": [
            _p("fb_post", "Facebook-Post", "Ø 12.000 Aufrufe je Beitrag", 200, "26.100 Follower – stark als Ergänzung im Paket"),
        ]},
        {"name": "Weitere Kanäle", "farbe": "blau", "items": [
            _p("x_post", "X-Post", "7.300 Follower", 150, "Schnelle Matchday-Kommunikation"),
            _p("tt_video", "TikTok-Video", "5.500 Follower · Kanal im Wachstum", 250, "Adaption Ihres Reels für TikTok inklusive"),
            _p("yt_short", "YouTube Short", "Kanal im Aufbau · Einführungspreis", 250),
            _p("twitch", "Twitch Stream-Integration", "Kanal im Aufbau · Einführungspreis", 250,
               "Live-Erwähnung und Einblendung im Stream"),
        ]},
        {"name": "Direktkanäle & App", "farbe": "blau", "items": [
            _p("wa", "WhatsApp-Broadcast", "3.600 Abonnenten", 150, "Maximal 1× pro Monat und Partner – bewusst knapp gehalten"),
            _p("push", "App Push-Notification", "1.000 aktive Nutzer", 150,
               "Direkt auf den Sperrbildschirm, max. 1× pro Monat und Partner"),
            _p("banner", "App-Banner Home-Tab, 1 Woche", "Sichtbar bei jedem App-Start", 250),
            _p("spieltag", "App-Sponsoring Spieltag", "Tippspiel oder Startelf-Voting", 350,
               "„Präsentiert von“ über den gesamten Spieltag"),
            _p("saison", "App Saison-Sponsoring Tippspiel", "Namensrecht und Branding", 1200,
               "Abrechnung monatlich, Laufzeit Saison", "Monat"),
        ]},
        {"name": "Vor Ort", "farbe": "blau", "items": [
            _p("stadion", "Stadion-Aktivierung, Tagespauschale", "Produktion vor Ort inkl. Team", 750,
               "Ausspielung über die gebuchten Formate"),
        ]},
        {"name": "Pakete", "farbe": "rot", "items": [
            _p("pk_test", "Paket Testlauf", "1× Reel-Integration + 1× Story-Serie", 1650,
               "Der Einstieg, um Zusammenarbeit und Wirkung zu prüfen"),
            _p("pk_match", "Paket Matchday", "Reel Standalone + Story-Serie + App-Push + X-Post", 2250,
               "Volle Präsenz rund um einen Spieltag, 10 % Paketvorteil"),
            _p("pk_saison", "Paket Saison-Partner", "App-Saison-Sponsoring + 2 Reel-Integrationen + 2 Story-Serien", 3600,
               "Monatliche Dauerpräsenz, 20 % Paketvorteil", "Monat"),
        ]},
    ],
    "zuschlaege": [
        {"id": "rechte", "name": "Nutzungsrechte Social, 6 Monate", "prozent": 25, "info": "Repost des Contents auf Ihren eigenen Kanälen"},
        {"id": "whitelist", "name": "Whitelisting / Paid Ads", "prozent": 60, "info": "Schaltung unseres Contents als Anzeige über unser Handle"},
        {"id": "offsocial", "name": "Nutzung außerhalb Social", "prozent": 50, "info": "Website, Out-of-Home, TV – Umfang nach Absprache"},
        {"id": "exklusiv", "name": "Branchenexklusivität, 3 Monate", "prozent": 20, "info": "Wir sagen Wettbewerbern Ihrer Branche ab"},
        {"id": "express", "name": "Express-Umsetzung, unter 7 Tagen", "prozent": 25, "info": ""},
        {"id": "skript", "name": "Vorgegebenes Skript", "prozent": 20, "info": "Gebundener Wortlaut statt redaktioneller Freiheit"},
    ],
    "rabatt_max": 30,
    "texte": {
        "untertitel": "Saison 2026/27",
        "intro": ("vielen Dank für Ihr Interesse an einer Zusammenarbeit mit Hanserautisch. Auf dieser Seite finden Sie "
                  "unsere Formate, die zugehörigen Preise und – weil wir finden, dass ein Angebot nachvollziehbar sein "
                  "muss – die vollständige Herleitung unserer Kalkulation."),
        "kalkulation_titel": "So kalkulieren wir – die Rechnung offen",
        "kalkulation": [
            "1. Reichweite: Grundlage ist der Median der letzten 90 Tage aus der Meta Business Suite – die Reichweite, "
            "die ein Format verlässlich erreicht. Nicht die Follower-Zahl, nicht der Bestwert. Virale Ausreißer (unser "
            "stärkstes Reel 2026: 469.000 Aufrufe) sind Ihr Bonus, nie unser Versprechen.",
            "2. TKP: Wie klassische Medien rechnen wir mit einem Preis pro 1.000 Kontakte, je nach Format 12–30 €. Zur "
            "Einordnung: OMR nennt für den deutschen Markt 25–50 € TKP für Reels und 20–50 € für Stories – wir liegen "
            "bewusst am unteren Rand dieser Spannen.",
            "3. Produktion: Konzept, Dreh, Schnitt und Abstimmung durch unser Team sind als Pauschale enthalten. Kanäle "
            "im Aufbau bepreisen wir mit ehrlichen Einführungspreisen statt geschätzter Reichweiten.",
        ],
        "kalkulation_beispiel": "Beispiel Reel: 37.000 Kontakte × 30 € TKP = 1.110 € Media-Wert + 450 € Produktion ≈ 1.600 €",
        "kennzahlen": [["120.000+", "Follower gesamt"], ["45,5 Mio.", "Aufrufe 2026 (Meta)"],
                       ["6 %", "Interaktionen auf Reichweite"], ["Ø 302", "Shares je Reel"]],
        "kennzahlen_quelle": ("Datenbasis: Meta Business Suite, 01.01.–14.09.2026. Unsere Community ist geografisch "
                              "konzentriert in Hamburg und der Metropolregion – eine Zielgruppe, die über Streuwerbung nur "
                              "mit hohem Verlust erreichbar ist. Exporte zeigen wir auf Wunsch im Original."),
        "zuschlaege_info": ("Die Preise oben gelten für die organische Ausspielung auf unseren Kanälen mit bis zu zwei "
                            "Freigabeschleifen. Erweiterte Nutzung kalkulieren wir transparent als Aufschlag auf den "
                            "Formatpreis:"),
        "fuss": ("Alle Preise sind Endpreise – gemäß § 19 UStG wird keine Umsatzsteuer berechnet (umsatzsteuerbefreiter "
                 "Kleinunternehmer). Jede Kooperation wird gemäß den gesetzlichen Vorgaben als Werbung gekennzeichnet – das "
                 "schützt Sie und uns. Nach jeder Kampagne erhalten Sie ein Reporting mit den tatsächlich erreichten Zahlen."),
        "kontakt": "nils@hanserautisch.de",
    },
}

_TEXT_FELDER = ("untertitel", "intro", "kalkulation_titel", "kalkulation_beispiel", "kennzahlen_quelle",
                "zuschlaege_info", "fuss", "kontakt")
_ID = re.compile(r"[a-z0-9_]{1,30}")


def _txt(v, n=1500) -> str:
    return str(v if v is not None else "").strip()[:n]


def pruefe(k: dict) -> dict:
    """Validiert und normalisiert einen Katalog. ValueError mit verstaendlichem Grund."""
    if not isinstance(k, dict):
        raise ValueError("Ungueltiger Katalog.")
    ids, gruppen = set(), []
    for g in k.get("gruppen") or []:
        name = _txt(g.get("name"), 60)
        if not name:
            raise ValueError("Gruppe ohne Namen.")
        items = []
        for it in g.get("items") or []:
            iid = _txt(it.get("id"), 30).lower()
            if not _ID.fullmatch(iid) or iid in ids:
                raise ValueError(f"Ungueltige oder doppelte Format-ID: {iid!r}")
            ids.add(iid)
            try:
                preis = int(it.get("preis_cent"))
            except (TypeError, ValueError):
                raise ValueError(f"{iid}: Preis fehlt.") from None
            if not 0 <= preis <= 100_000_000:
                raise ValueError(f"{iid}: Preis ausserhalb des Rahmens.")
            if not _txt(it.get("name"), 120):
                raise ValueError(f"{iid}: Name fehlt.")
            items.append({"id": iid, "name": _txt(it.get("name"), 120), "basis": _txt(it.get("basis"), 200),
                          "hinweis": _txt(it.get("hinweis"), 300), "preis_cent": preis,
                          "einheit": _txt(it.get("einheit"), 20), "aktiv": it.get("aktiv", True) is not False})
        gruppen.append({"name": name, "farbe": "rot" if g.get("farbe") == "rot" else "blau", "items": items})
    if not ids:
        raise ValueError("Katalog ohne Formate.")
    zuschlaege, zids = [], set()
    for z in k.get("zuschlaege") or []:
        zid = _txt(z.get("id"), 30).lower()
        if not _ID.fullmatch(zid) or zid in zids:
            raise ValueError(f"Ungueltige oder doppelte Zuschlag-ID: {zid!r}")
        zids.add(zid)
        try:
            pr = float(z.get("prozent"))
        except (TypeError, ValueError):
            raise ValueError(f"{zid}: Prozent fehlt.") from None
        if not 0 < pr <= 200:
            raise ValueError(f"{zid}: Prozent zwischen 0 und 200.")
        zuschlaege.append({"id": zid, "name": _txt(z.get("name"), 120) or zid, "prozent": round(pr, 2),
                           "info": _txt(z.get("info"), 300)})
    t = k.get("texte") or {}
    texte = {f: _txt(t.get(f), 2000) for f in _TEXT_FELDER}
    texte["kalkulation"] = [_txt(x, 1500) for x in (t.get("kalkulation") or []) if _txt(x)][:6]
    texte["kennzahlen"] = [[_txt(a, 20), _txt(b, 60)] for a, b in (t.get("kennzahlen") or []) if _txt(a)][:6]
    try:
        rmax = int(k.get("rabatt_max", 30))
    except (TypeError, ValueError):
        rmax = 30
    return {"gruppen": gruppen, "zuschlaege": zuschlaege, "rabatt_max": max(0, min(rmax, 90)), "texte": texte}


class Katalog:
    def __init__(self, bh: Buchhaltung):
        self.bh = bh
        self.pfad = bh.dir / "katalog.json"

    def laden(self) -> dict:
        try:
            return pruefe(json.loads(self.pfad.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return pruefe(copy.deepcopy(STANDARD))

    def format(self, iid: str) -> tuple[dict, str] | None:
        for g in self.laden()["gruppen"]:
            for it in g["items"]:
                if it["id"] == iid:
                    return it, g["name"]
        return None

    def speichern(self, neu: dict, *, von: str = "") -> dict:
        """Validiert, schreibt atomar und protokolliert die Aenderung (Preise vorher/nachher) in der Kette."""
        alt = self.laden()
        k = pruefe(neu)
        alt_preise = {it["id"]: it["preis_cent"] for g in alt["gruppen"] for it in g["items"]}
        neu_preise = {it["id"]: it["preis_cent"] for g in k["gruppen"] for it in g["items"]}
        preise = {i: [alt_preise.get(i), p] for i, p in neu_preise.items() if alt_preise.get(i) != p}
        entfernt = sorted(set(alt_preise) - set(neu_preise))
        roh = json.dumps(k, ensure_ascii=False, indent=1, sort_keys=True)
        if roh == json.dumps(alt, ensure_ascii=False, indent=1, sort_keys=True) and self.pfad.exists():
            return {"geaendert": False}
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(roh, encoding="utf-8")
        os.replace(tmp, self.pfad)
        self.bh.erfassen("katalog_geaendert", {"sha256": hashlib.sha256(roh.encode()).hexdigest(), "preise": preise,
                                               "entfernt": entfernt,
                                               "zuschlaege": {z["id"]: z["prozent"] for z in k["zuschlaege"]}}, von=von)
        return {"geaendert": True, "preise": preise, "entfernt": entfernt}
