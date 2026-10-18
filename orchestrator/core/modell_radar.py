"""Modell-Radar des Researchers (MODELL_RADAR R1-R3, CEO 2026-10-13).

- **R1 Hersteller-News:** Feeds bzw. News-Seiten und API-Aenderungsprotokolle der fuehrenden KI-Anbieter, taeglich,
  regelbasiert eingestuft -- 🔴 betrifft ein Modell, das wir nutzen (Abschaltung, Preis, API-Aenderung) -> sofort;
  🟡 neue Modelle/Preissenkungen -> Wochenbericht; ⚪ nur Archiv. Erster Lauf je Quelle = Bestand (keine Flut).
- **R2 Artificial Analysis:** Gratis-Daten-API (Intelligenz-Index, Preis, Tempo; Quellenangabe Pflicht). Abgleich mit
  unseren Modellen -> Vorschlag als **Antrag „Modellwechsel pruefen“** mit Kostenvoranschlag; **nie automatisch wechseln**.
- **R3:** Uebersicht in LUNA-OS und Wochenbericht montags.

Kein LLM, keine Volltexte (nur Titel, Link, Datum, kurzer Anriss). Speicher `radar/` (nur NAS, nicht in der Kette).
"""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import os
import re
import tempfile
import threading
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

AA_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
AA_QUELLE = "Daten: Artificial Analysis (artificialanalysis.ai)"
USER_AGENT = "LUNA-Modell-Radar/1.0 (Hanserautisch; einmal taeglich)"

# Erreichbarkeit geprueft 2026-10-13 (read-only). x.ai blockt Abrufe (403) -> Brave-Suche.
QUELLEN = [
    {"id": "anthropic", "hersteller": "Anthropic", "art": "links", "url": "https://www.anthropic.com/news",
     "muster": r'/news/[a-z0-9-]+', "basis": "https://www.anthropic.com"},
    {"id": "anthropic-api", "hersteller": "Anthropic", "art": "changelog", "url": "https://platform.claude.com/docs/en/release-notes/overview"},
    {"id": "openai", "hersteller": "OpenAI", "art": "feed", "url": "https://openai.com/news/rss.xml"},
    {"id": "openai-api", "hersteller": "OpenAI", "art": "changelog", "url": "https://developers.openai.com/api/docs/changelog"},
    {"id": "deepmind", "hersteller": "Google", "art": "feed", "url": "https://deepmind.google/blog/rss.xml"},
    {"id": "google-ai", "hersteller": "Google", "art": "feed", "url": "https://blog.google/technology/ai/rss/"},
    {"id": "gemini-api", "hersteller": "Google", "art": "changelog", "url": "https://ai.google.dev/gemini-api/docs/changelog"},
    {"id": "meta", "hersteller": "Meta", "art": "links", "url": "https://ai.meta.com/blog/",
     "muster": r'https://ai\.meta\.com/blog/[a-z0-9-]+/?', "basis": ""},
    {"id": "mistral", "hersteller": "Mistral", "art": "feed", "url": "https://mistral.ai/news/rss"},
    {"id": "xai", "hersteller": "xAI", "art": "suche", "url": "xAI Grok neues Modell"},
    {"id": "deepseek", "hersteller": "DeepSeek", "art": "feed", "url": "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"},
    {"id": "deepseek-suche", "hersteller": "DeepSeek", "art": "suche", "url": "DeepSeek new model release"},
    {"id": "qwen", "hersteller": "Qwen (Alibaba)", "art": "feed", "url": "https://qwenlm.github.io/blog/index.xml"},
    {"id": "ollama", "hersteller": "Ollama", "art": "feed", "url": "https://github.com/ollama/ollama/releases.atom", "release": True},
    {"id": "nvidia-dev", "hersteller": "NVIDIA", "art": "feed", "url": "https://developer.nvidia.com/blog/feed/"},
    {"id": "nvidia", "hersteller": "NVIDIA", "art": "feed", "url": "https://blogs.nvidia.com/feed/"},
    {"id": "microsoft", "hersteller": "Microsoft", "art": "feed", "url": "https://azure.microsoft.com/en-us/blog/feed/"},
]
HERSTELLER = sorted({q["hersteller"] for q in QUELLEN})

_KRITISCH = re.compile(r"deprecat|retir|shut ?down|sunset|end of life|end-of-life|discontinu|abschalt|eingestellt|"
                       r"no longer (?:be )?available|removed|breaking change|price|pricing|preis", re.I)
_NEU = re.compile(r"introduc|launch|new model|now available|available today|generally available|open[- ]weight|"
                  r"model card|cheaper|price cut|lower price|vorgestellt|veroeffentlicht|veröffentlicht|"
                  r"\b(?:gpt|gemini|claude|llama|qwen|grok|mistral|deepseek|nemotron|phi|gemma)[- ]?\d", re.I)
_MONATE = ("January|February|March|April|May|June|July|August|September|October|November|December|"
           "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec")
_DATUM = re.compile(rf"^(?:{_MONATE}) \d{{1,2}}(?:, \d{{4}})?$")


# -- Abruf ------------------------------------------------------------------------------------------------------------
def abrufen(url: str, *, kopf: dict | None = None, max_bytes: int = 4_000_000) -> str:
    """Oeffentliche Quelle lesen (eigener User-Agent, gzip, Groessengrenze). Nur feste https-Adressen aus QUELLEN/AA."""
    if not url.startswith("https://"):
        raise ValueError("nur https")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"} | (kopf or {}))
    with urllib.request.urlopen(req, timeout=20) as r:
        roh = r.read(max_bytes + 1)
        if r.headers.get("Content-Encoding", "").lower() == "gzip" or roh[:2] == b"\x1f\x8b":
            roh = gzip.decompress(roh)
    return roh[:max_bytes].decode("utf-8", "replace")


def _text(h: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", h or "")).split())


def _id(*teile) -> str:
    return hashlib.sha1("|".join(str(t) for t in teile).encode()).hexdigest()[:16]


# -- Parser -----------------------------------------------------------------------------------------------------------
def lies_feed(text: str) -> list[dict]:
    """RSS 2.0 oder Atom -> [{titel, link, datum, anriss}] (namensraum-unabhaengig)."""
    try:
        root = ET.fromstring(text.encode("utf-8", "replace"))
    except ET.ParseError:
        return []
    tag = lambda e: e.tag.split("}")[-1]
    out = []
    for e in root.iter():
        if tag(e) not in ("item", "entry"):
            continue
        k = {tag(c): c for c in e}
        link = (k["link"].text or k["link"].get("href", "")) if "link" in k else ""
        if "link" in k and not (link or "").strip():
            link = next((c.get("href") for c in e if tag(c) == "link" and c.get("href")), "")
        datum = next(((k[x].text or "") for x in ("pubDate", "published", "updated", "date") if x in k), "")
        anriss = next(((k[x].text or "") for x in ("description", "summary", "content") if x in k), "")
        titel = _text(k["title"].text if "title" in k else "")
        if titel:
            out.append({"titel": titel[:200], "link": (link or "").strip(), "datum": datum.strip()[:40], "anriss": _text(anriss)[:300]})
    return out


def lies_links(text: str, muster: str, basis: str = "") -> list[dict]:
    """News-Seite ohne Feed: Artikel-Links samt Linktext (erste Fundstelle je Link)."""
    out, gesehen = [], set()
    for m in re.finditer(rf'<a[^>]+href="({muster})"[^>]*>(.*?)</a>', text, re.S | re.I):
        link, inhalt = m.group(1), m.group(2)
        if link in gesehen:
            continue
        k = re.search(r"<h\d[^>]*>(.*?)</h\d>", inhalt, re.S)               # Karte: Ueberschrift = Titel, Rest = Anriss
        titel = _text(k.group(1) if k else inhalt)
        p = re.search(r"<p[^>]*>(.*?)</p>", inhalt, re.S)
        zeit = re.search(r"<time[^>]*>(.*?)</time>", inhalt, re.S)
        gesehen.add(link)
        if len(titel) < 14 or titel.isupper():                     # „FEATURED“, „Read more“ -> Titel aus dem Link
            titel = link.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").capitalize()
        out.append({"titel": titel[:200], "link": (basis + link) if link.startswith("/") else link,
                    "datum": _text(zeit.group(1)) if zeit else "", "anriss": _text(p.group(1))[:300] if (k and p) else ""})
    return out


def lies_changelog(text: str, url: str) -> list[dict]:
    """Aenderungsprotokoll: Zeilen, die nur ein Datum sind („October 8, 2026“), plus der Text bis zum naechsten Datum."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    t = re.sub(r"<(?:br|/p|/h\d|/li|/div|/section|h\d[^>]*|p[^>]*|li[^>]*)>", "\n", t, flags=re.I)
    zeilen = [_text(z).replace("", "").strip() for z in t.split("\n")]
    zeilen = [z for z in zeilen if z]
    out, i = [], 0
    while i < len(zeilen):
        if _DATUM.match(zeilen[i]):
            datum, j, inhalt = zeilen[i], i + 1, []
            while j < len(zeilen) and not _DATUM.match(zeilen[j]) and sum(len(x) for x in inhalt) < 400:
                inhalt.append(zeilen[j])
                j += 1
            anriss = " ".join(inhalt)[:400]
            titel = f"{datum} – {anriss[:90]}"
            if anriss and titel not in {o["titel"] for o in out}:
                out.append({"titel": titel, "link": url, "datum": datum, "anriss": anriss})
            i = j
        else:
            i += 1
    return out


# -- Unsere Modelle --------------------------------------------------------------------------------------------------
def genutzte_modelle(cfg: dict, secrets: dict) -> list[dict]:
    """Welche Modelle LUNA nutzt (nur Namen) -> [{einsatz, modell}] aus config.toml und .env."""
    v, m, s = cfg.get("voice") or {}, cfg.get("models") or {}, secrets or {}
    roh = [("Chat (Hauptmodell)", v.get("llm_model")),
           ("Chat-Rückfall Gemini", v.get("gemini_model", "gemini-2.5-flash") if s.get("GEMINI_API_KEY") else ""),
           ("Chat-Rückfall OpenAI", v.get("openai_model", "gpt-4o-mini") if s.get("OPENAI_API_KEY") else ""),
           ("Fachagenten", m.get("hoa")), ("Routing", m.get("routing")),
           ("Lokal (MACO470)", s.get("LOCAL_LLM_MODEL")), ("Instagram-Analyse", s.get("IG_ANALYSE_MODELL")),
           ("Videograf/Content", "gemini-2.5-flash" if s.get("GEMINI_API_KEY") else "")]
    out, gesehen = [], set()
    for einsatz, modell in roh:
        modell = str(modell or "").strip()
        if modell and (einsatz, modell) not in gesehen:
            gesehen.add((einsatz, modell))
            out.append({"einsatz": einsatz, "modell": modell})
    return out


def _norm(t: str) -> str:
    return " ".join(re.sub(r"[-_:/]", " ", str(t or "").lower()).split())


def modell_schluessel(modell: str) -> list[str]:
    """Suchbegriffe je Modell: „gemini-2.5-flash“ -> ["gemini 2.5 flash"]; „claude-sonnet-5“ -> [..., "sonnet 5"]; „qwen3:14b“ -> [..., "qwen3"]."""
    n = _norm(modell)
    out = [str(modell).lower().strip(), n, n.replace(" ", "-")]
    teile = n.split()
    if teile and teile[0] in ("claude", "gpt", "gemini") and len(teile) > 2:
        out.append(" ".join(teile[1:]))
    if teile and re.match(r"qwen\d|llama\d|phi\d|mistral|deepseek", teile[0]):
        out.append(teile[0])
    return list(dict.fromkeys(out))


def einstufen(item: dict, quelle: dict, unsere: list[dict]) -> tuple[str, list[str]]:
    """-> (stufe rot|gelb|grau, betroffene Modelle)."""
    t = " ".join(f"{item.get('titel', '')} {item.get('anriss', '')}".lower().split())
    # Grenzen ohne „-“: „gpt-4o-mini“ trifft nicht „gpt-4o-mini-tts“, „gemini 2.5 flash“ nicht „Flash-Lite“
    betroffen = sorted({u["modell"] for u in unsere for k in modell_schluessel(u["modell"])
                        if re.search(rf"(?<![\w.-]){re.escape(k)}(?![\w-]|\.\d)", t)})
    if betroffen and (quelle["art"] == "changelog" or _KRITISCH.search(t)):
        return "rot", betroffen
    if quelle.get("release"):
        return ("grau" if re.search(r"rc\d|-rc|beta|alpha", item.get("titel", ""), re.I) else "gelb"), betroffen
    if _NEU.search(t):
        return "gelb", betroffen
    return "grau", betroffen


# -- R2: Artificial Analysis --------------------------------------------------------------------------------------------
def aa_modelle(roh: dict) -> list[dict]:
    """Antwort der Gratis-API -> [{name, slug, hersteller, iq, preis, preis_in, preis_out, tempo}] (fehlende Werte None)."""
    out = []
    for d in (roh or {}).get("data") or []:
        ev, pr = d.get("evaluations") or {}, d.get("pricing") or {}
        zahl = lambda x: float(x) if isinstance(x, (int, float)) else None
        out.append({"name": d.get("name", ""), "slug": d.get("slug", ""), "hersteller": (d.get("model_creator") or {}).get("name", ""),
                    "iq": zahl(ev.get("artificial_analysis_intelligence_index")), "preis": zahl(pr.get("price_1m_blended_3_to_1")),
                    "preis_in": zahl(pr.get("price_1m_input_tokens")), "preis_out": zahl(pr.get("price_1m_output_tokens")),
                    "tempo": zahl(d.get("median_output_tokens_per_second"))})
    return out


def aa_finden(modell: str, aa: list[dict]) -> dict | None:
    """Unser Modellname -> passender Eintrag (Slug-Vergleich ohne Satzzeichen, kuerzester Treffer)."""
    k = re.sub(r"[^a-z0-9]", "", modell.lower().split(":")[0] + (modell.lower().split(":")[1] if ":" in modell else ""))
    treffer = [a for a in aa if re.sub(r"[^a-z0-9]", "", (a["slug"] or a["name"]).lower()) == k]
    if not treffer:
        treffer = [a for a in aa if re.sub(r"[^a-z0-9]", "", (a["slug"] or a["name"]).lower()).startswith(k)]
    if not treffer:                                   # gleiche Teile, andere Reihenfolge: „claude-haiku-4-5“ ~ „claude-4-5-haiku“
        teile = set(re.findall(r"[a-z]+|\d+", modell.lower().replace(":", "-")))
        treffer = [a for a in aa if teile and teile <= set(re.findall(r"[a-z]+|\d+", (a["slug"] or "").lower()))
                   and len(set(re.findall(r"[a-z]+|\d+", (a["slug"] or "").lower())) - teile) <= 2]
    return min(treffer, key=lambda a: len(a["slug"] or a["name"])) if treffer else None


def vorschlaege(unsere: list[dict], aa: list[dict], *, hersteller: list[str] | None = None) -> list[dict]:
    """Je unserem Modell hoechstens zwei Vorschlaege: „guenstiger“ (gleiche Qualitaet, >= 30 % billiger) und „besser“
    (>= 5 Punkte mehr bei hoechstens +10 % Preis). Nur Modelle bekannter Hersteller, nur mit vollstaendigen Werten."""
    erlaubt = {h.lower().split(" ")[0] for h in (hersteller or HERSTELLER)} | {"alibaba", "google", "meta", "microsoft"}
    kandidaten = [a for a in aa if a["iq"] is not None and a["preis"]                 # Preis 0 = unbekannt/nicht buchbar
                  and any(e in (a["hersteller"] or "").lower() for e in erlaubt)]
    out = []
    je_modell: dict[str, list[str]] = {}                          # ein Vorschlag je Modell, Einsaetze zusammengefasst
    for u in unsere:
        if u["einsatz"].startswith("Lokal"):                       # lokales Modell: kostet nichts, Daten bleiben im Haus --
            continue                                               # Preisvergleich mit Cloud-Modellen waere sinnlos
        je_modell.setdefault(u["modell"], []).append(u["einsatz"])
    for modell, einsaetze in je_modell.items():
        u = {"modell": modell, "einsatz": ", ".join(dict.fromkeys(einsaetze))}
        m = aa_finden(u["modell"], aa)
        if not m or m["iq"] is None or m["preis"] is None:
            continue
        billiger = [a for a in kandidaten if a["slug"] != m["slug"] and a["iq"] >= m["iq"] and m["preis"] > 0 and a["preis"] <= 0.7 * m["preis"]]
        besser = [a for a in kandidaten if a["slug"] != m["slug"] and a["iq"] >= m["iq"] + 5 and a["preis"] <= m["preis"] * 1.1]
        if billiger:
            c = min(billiger, key=lambda a: (a["preis"], -a["iq"]))
            out.append({"regel": "guenstiger", "einsatz": u["einsatz"], "modell": u["modell"], "alt": m, "neu": c})
        if besser:
            c = max(besser, key=lambda a: (a["iq"], -a["preis"]))
            if not billiger or c["slug"] != out[-1]["neu"]["slug"]:
                out.append({"regel": "besser", "einsatz": u["einsatz"], "modell": u["modell"], "alt": m, "neu": c})
    return out


def kostenvoranschlag(v: dict, nutzung: dict | None) -> str:
    """CFO-Kostenvoranschlag (AGENTS.md 5.9) aus Nutzung der letzten 30 Tage (Token) und den Preisen laut Artificial Analysis."""
    a, n = v["alt"], v["neu"]
    zeilen = [f"Preis je 1 Mio. Token (gemischt 3:1): {a['preis']:.2f} $ → {n['preis']:.2f} $"]
    if nutzung and nutzung.get("in", 0) + nutzung.get("out", 0) > 0 and None not in (a["preis_in"], a["preis_out"], n["preis_in"], n["preis_out"]):
        alt = (nutzung["in"] * a["preis_in"] + nutzung["out"] * a["preis_out"]) / 1e6
        neu = (nutzung["in"] * n["preis_in"] + nutzung["out"] * n["preis_out"]) / 1e6
        zeilen.append(f"Bei unserer Nutzung der letzten 30 Tage ({nutzung['in']:,} Token rein, {nutzung['out']:,} raus): "
                      f"ca. {alt:.2f} $ → {neu:.2f} $ im Monat (Listenpreise, ohne Gratis-Kontingente)".replace(",", "."))
    else:
        zeilen.append("Nutzung dieses Modells in den letzten 30 Tagen nicht erfasst – Monatskosten bitte vom CFO schätzen lassen.")
    zeilen.append("Einmalige Kosten: keine (Umstellung in der Konfiguration); laufend: siehe oben.")
    return "\n".join(zeilen)


# -- Speicher ---------------------------------------------------------------------------------------------------------
_LOCK = threading.Lock()


class Radar:
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

    def news(self) -> dict:
        return self._lesen("news.json")

    def stand(self) -> dict:
        return self._lesen("stand.json")

    def aa(self) -> dict:
        return self._lesen("aa.json")

    def vorschlaege_gemerkt(self) -> dict:
        return self._lesen("vorschlaege.json")

    def merken(self, quelle: dict, items: list[dict], unsere: list[dict], jetzt: str) -> list[dict]:
        """Neue Beitraege speichern -> die neuen (beim ersten Lauf der Quelle: Bestand, Rueckgabe leer)."""
        with _LOCK:
            n, st = self._lesen("news.json"), self._lesen("stand.json")
            erster = quelle["id"] not in (st.get("quellen") or {})
            neu = []
            for it in items[:60]:
                iid = _id(quelle["id"], it["link"], it["titel"])
                if iid in n:
                    continue
                stufe, betroffen = einstufen(it, quelle, unsere)
                x = it | {"id": iid, "quelle": quelle["id"], "hersteller": quelle["hersteller"], "stufe": stufe,
                          "betroffen": betroffen, "gesehen": jetzt, "bestand": erster}
                n[iid] = x
                if not erster:
                    neu.append(x)
            st.setdefault("quellen", {})[quelle["id"]] = {"ts": jetzt, "anzahl": len(items), "fehler": ""}
            grenze = (datetime.fromisoformat(jetzt) - timedelta(days=400)).isoformat()
            n = {k: v for k, v in n.items() if v.get("gesehen", "") >= grenze}
            self._schreiben("news.json", n)
            self._schreiben("stand.json", st)
        return neu

    def fehler_merken(self, quelle_id: str, fehler: str, jetzt: str) -> None:
        with _LOCK:
            st = self._lesen("stand.json")
            q = st.setdefault("quellen", {}).setdefault(quelle_id, {})
            q |= {"fehler": fehler[:120], "fehler_ts": jetzt}
            self._schreiben("stand.json", st)

    def aa_speichern(self, modelle: list[dict], jetzt: str) -> None:
        self._schreiben("aa.json", {"ts": jetzt, "modelle": modelle})

    def vorschlag_neu(self, v: dict, jetzt: str) -> bool:
        """True, wenn dieser Vorschlag (Modell -> Kandidat, Regel) noch nie gemacht wurde (dann gemerkt)."""
        k = f"{v['einsatz']}|{v['modell']}|{v['neu']['slug']}|{v['regel']}"
        with _LOCK:
            d = self._lesen("vorschlaege.json")
            if k in d:
                return False
            d[k] = {"ts": jetzt, "einsatz": v["einsatz"], "modell": v["modell"], "neu": v["neu"]["name"], "regel": v["regel"],
                    "antrag": v.get("antrag", "")}
            self._schreiben("vorschlaege.json", d)
        return True

    def wochenbericht_faellig(self, jetzt: datetime) -> list[dict] | None:
        """🟡-Beitraege seit dem letzten Wochenbericht (montags ab 09:00, einmal je Woche)."""
        st = self.stand()
        woche = jetzt.strftime("%G-W%V")
        if jetzt.weekday() != 0 or jetzt.hour < 9 or st.get("wochenbericht") == woche:
            return None                                              # nicht faellig
        seit = st.get("wochenbericht_ts", "")
        return sorted([x for x in self.news().values() if x["stufe"] == "gelb" and not x.get("bestand") and x["gesehen"] > seit],
                      key=lambda x: x["gesehen"], reverse=True)

    def wochenbericht_erledigt(self, jetzt: datetime) -> None:
        with _LOCK:
            st = self._lesen("stand.json")
            st |= {"wochenbericht": jetzt.strftime("%G-W%V"), "wochenbericht_ts": jetzt.isoformat(timespec="seconds")}
            self._schreiben("stand.json", st)


# -- Laeufe -------------------------------------------------------------------------------------------------------------
def lauf_news(radar: Radar, unsere: list[dict], *, jetzt: datetime, abruf=abrufen, suche=None,
              quellen: list[dict] | None = None) -> list[dict]:
    """Taeglich: alle Quellen lesen -> neue 🔴-Beitraege (fuer die Sofortmeldung). Fehler je Quelle stoppen nichts."""
    ts, rot = jetzt.isoformat(timespec="seconds"), []
    for q in quellen or QUELLEN:
        try:
            if q["art"] == "suche":
                if suche is None:
                    continue
                items = [{"titel": t, "link": u, "datum": "", "anriss": a} for t, u, a in suche(q["url"])]
            else:
                text = abruf(q["url"])
                items = (lies_feed(text) if q["art"] == "feed" else lies_links(text, q["muster"], q.get("basis", ""))
                         if q["art"] == "links" else lies_changelog(text, q["url"]))
            if not items:
                raise ValueError("keine Beitraege erkannt (Seitenaufbau geaendert?)")
            rot += [x for x in radar.merken(q, items, unsere, ts) if x["stufe"] == "rot"]
        except Exception as exc:
            radar.fehler_merken(q["id"], f"{exc.__class__.__name__}: {exc}"[:120], ts)
    return rot


def lauf_aa(radar: Radar, unsere: list[dict], *, schluessel: str, jetzt: datetime, abruf=abrufen) -> list[dict]:
    """Taeglich: Artificial-Analysis-Liste holen (ein Abruf), cachen -> neue Vorschlaege (je einmal)."""
    roh = json.loads(abruf(AA_URL, kopf={"x-api-key": schluessel, "Accept": "application/json"}))
    aa = aa_modelle(roh)
    radar.aa_speichern(aa, jetzt.isoformat(timespec="seconds"))
    return [v for v in vorschlaege(unsere, aa) if radar.vorschlag_neu(v, jetzt.isoformat(timespec="seconds"))]


def vorschlag_text(v: dict, nutzung: dict | None = None) -> tuple[str, str]:
    a, n = v["alt"], v["neu"]
    warum = (f"gleiche oder bessere Qualität ({n['iq']:.0f} statt {a['iq']:.0f} Punkte), deutlich günstiger" if v["regel"] == "guenstiger"
             else f"deutlich besser ({n['iq']:.0f} statt {a['iq']:.0f} Punkte) bei etwa gleichem Preis")
    titel = f"Modellwechsel prüfen: {v['einsatz']} – {v['modell']} → {n['name']}"
    text = (f"Der Researcher (Modell-Radar) schlägt vor, fuer „{v['einsatz']}“ statt {v['modell']} ({a['name']}) das Modell "
            f"{n['name']} ({n['hersteller']}) zu prüfen: {warum}."
            + (f" Tempo: {n['tempo']:.0f} statt {a['tempo']:.0f} Token/s." if n.get("tempo") and a.get("tempo") else "")
            + "\n\nKostenvoranschlag (CFO):\n" + kostenvoranschlag(v, nutzung)
            + "\n\nNichts wird automatisch umgestellt – neues Modell = CEO-Freigabe; vorher die Qualität an echten Aufgaben testen."
            + f"\n\n{AA_QUELLE}")
    return titel, text


def meldung_rot(items: list[dict]) -> str:
    return "🔴 Modell-Radar – betrifft unsere Modelle:\n" + "\n".join(
        f"• {x['hersteller']}: {x['titel']}" + (f" ({', '.join(x['betroffen'])})" if x.get("betroffen") else "")
        + f"\n  {x['link']}" for x in items[:8])


def wochenbericht_text(items: list[dict], offene_vorschlaege: int) -> str:
    kopf = f"🧭 Modell-Radar – Woche: {len(items)} Neuigkeit{'en' if len(items) != 1 else ''} der Hersteller"
    zeilen = [f"• {x['hersteller']}: {x['titel']}\n  {x['link']}" for x in items[:12]]
    fuss = (f"\n{offene_vorschlaege} Vorschlag/Vorschläge zum Modellwechsel liegen als Antrag bereit." if offene_vorschlaege else "")
    return kopf + ("\n" + "\n".join(zeilen) if zeilen else "\nNichts Wichtiges diese Woche.") + fuss + \
        "\nMehr in LUNA-OS → LUNA & System → 🧭 Modell-Radar."


# -- R4: bessere lokale Modelle (MODELL_RADAR R4, CEO 2026-10-16) -------------------------------------------------------
OLLAMA_BIBLIOTHEK = "https://ollama.com/library?sort=newest"
_GROESSE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)b(?![\w])", re.I)
# Allgemeine Pruffaelle fuer den Modellvergleich (ergaenzt um die Pruffaelle aktiver Werkstatt-Skills)
STANDARD_PRUEFFAELLE = [
    {"eingabe": "Schreibe eine kurze, freundliche Mail an Kiez Burger: Wir bieten ein Reel (Preis 450 EUR netto) fuer ihr neues "
                "Smash-Burger-Menue an, Drehtermin naechste Woche. Hoechstens 8 Saetze.",
     "kriterien": ["nennt den Preis 450 EUR", "nennt den Drehtermin naechste Woche", "hoechstens 8 Saetze", "hoefliche Anrede und Gruss"]},
    {"eingabe": "Fasse in 3 Stichpunkten zusammen: Der Kunde will 3 Reels im November, Budget 1.200 EUR, Freigabe ueber die "
                "Marketingleiterin Frau Sommer, Drehort Hafen, keine Musik mit Text.",
     "kriterien": ["genau 3 Stichpunkte", "nennt Budget 1.200 EUR", "nennt Frau Sommer", "erwaehnt keine Musik mit Text"]},
    {"eingabe": "Ein Kunde zahlt eine Rechnung ueber 714 EUR seit 20 Tagen nicht. Formuliere eine hoefliche erste Zahlungserinnerung "
                "mit neuer Frist von 7 Tagen.",
     "kriterien": ["nennt 714 EUR", "nennt Frist 7 Tage", "hoeflicher Ton ohne Drohung", "fordert zur Zahlung auf"]},
    {"eingabe": "Nenne drei Ideen fuer Instagram-Reels fuer eine Hamburger Bar zum HSV-Heimspiel. Je Idee ein Satz.",
     "kriterien": ["genau drei Ideen", "Bezug zum HSV oder Heimspiel", "je Idee hoechstens zwei Saetze"]},
    {"eingabe": "Antworte nur mit JSON: {\"kunde\": <Name>, \"betrag\": <Zahl>} fuer den Satz: Hafenbar GmbH bestellt fuer 980 Euro.",
     "kriterien": ["gueltiges JSON", "kunde = Hafenbar GmbH", "betrag = 980"]},
]


def groesse_b(modell: str) -> float | None:
    """„qwen3:30b-a3b“ -> 30.0, „gemma3:4b“ -> 4.0; ohne Angabe None."""
    m = _GROESSE.search(str(modell or "").replace("-", " ").replace(":", " "))
    return float(m.group(1)) if m else None


def lies_ollama(text: str) -> list[dict]:
    """Ollama-Bibliothek (oeffentliche Liste) -> [{name, kurz, faehigkeiten, groessen, pulls, aktualisiert}]."""
    out = []
    teile = re.split(r'(?=<a href="/library/[a-z0-9._-]+")', text or "")
    for t in teile[1:]:
        m = re.match(r'<a href="/library/([a-z0-9._-]+)"', t)
        if not m:
            continue
        stuecke = [s for s in (_text(x) for x in re.split(r"<[^>]+>", t[:6000])) if s]
        name = m.group(1)
        kurz = next((s for s in stuecke if len(s) > 30), "")[:140]
        faehig = [s for s in stuecke if s.lower() in ("tools", "thinking", "vision", "embedding", "audio", "cloud")]
        groessen = sorted({float(g[:-1]) for g in stuecke if re.fullmatch(r"\d+(?:\.\d+)?b", g, re.I)})
        akt = next((stuecke[i + 1] for i, s in enumerate(stuecke) if s.startswith("Updated") and i + 1 < len(stuecke)), "")
        pulls = next((stuecke[i - 1] for i, s in enumerate(stuecke) if s.endswith("Pulls") and i), "")
        if not any(x["name"] == name for x in out):
            out.append({"name": name, "kurz": kurz, "faehigkeiten": faehig, "groessen": groessen, "pulls": pulls, "aktualisiert": akt})
    return out


def _familie(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).split(":")[0].lower())


def lokale_kandidaten(lokal: str, bibliothek: list[dict], aa: list[dict], *, max_b: float | None = None) -> dict:
    """Kandidaten fuer das lokale Modell: Werkzeuge noetig (LUNA arbeitet mit Tools), kein reines Embedding/Cloud,
    groesste Variante bis `max_b` (Standard: Groesse des heutigen Modells, damit es auf den MACO470 passt).
    Qualitaet aus Artificial Analysis, wenn vorhanden -> {unser, kandidaten: [...], vorschlaege: [...]}."""
    grenze = max_b or groesse_b(lokal) or 14.0
    unser_aa = aa_finden(lokal, aa) if aa else None
    kandidaten = []
    for m in bibliothek:
        f = set(m["faehigkeiten"])
        if "tools" not in f or {"embedding", "cloud"} & f or _familie(m["name"]) == _familie(lokal):
            continue
        passend = [g for g in m["groessen"] if g <= grenze]
        if not passend:
            continue
        g = max(passend)
        tag = f"{m['name']}:{g:g}b"
        q = aa_finden(f"{m['name']}-{g:g}b", aa) if aa else None
        kandidaten.append({"modell": tag, "familie": m["name"], "groesse_b": g, "faehigkeiten": sorted(f), "kurz": m["kurz"],
                           "aktualisiert": m["aktualisiert"], "pulls": m["pulls"], "iq": (q or {}).get("iq"), "aa_name": (q or {}).get("name", "")})
    vorschlaege = []
    if unser_aa and unser_aa.get("iq") is not None:
        for k in kandidaten:
            if k["iq"] is not None and k["iq"] >= unser_aa["iq"] + 3:
                vorschlaege.append(k | {"unser_iq": unser_aa["iq"]})
        vorschlaege.sort(key=lambda k: -k["iq"])
    return {"unser": {"modell": lokal, "groesse_b": groesse_b(lokal), "iq": (unser_aa or {}).get("iq"), "grenze_b": grenze},
            "kandidaten": kandidaten[:30], "vorschlaege": vorschlaege[:3]}


def lokal_vorschlag_text(lokal: str, k: dict) -> tuple[str, str]:
    titel = f"Lokales Modell testen: {lokal} → {k['modell']}"
    text = (f"Der Researcher (Modell-Radar) schlägt vor, auf dem MACO470 statt {lokal} das offene Modell {k['modell']} zu testen: "
            f"Qualität {k['iq']:.0f} statt {k['unser_iq']:.0f} Punkte, Größe {k['groesse_b']:g} Mrd. Parameter (passt in die bisherige "
            f"Grenze), kann Werkzeuge nutzen.\n\nKosten: keine (lokal, Strom); einmalig ein Download von einigen GB.\n\n"
            "Nächster Schritt: in LUNA-OS → Modell-Radar → „🧪 Probelauf“ starten. Der MACO470 lädt das Modell dann nachts und "
            "vergleicht es mit dem heutigen an festen Prüffällen. Umgestellt wird erst nach deiner Entscheidung.\n\n" + AA_QUELLE)
    return titel, text


class LokalTests:
    """Probelaeufe altes gegen neues lokales Modell ueber das Backoffice (`radar/lokal_tests.json`)."""
    def __init__(self, radar: Radar):
        self.r = radar

    def alle(self) -> dict:
        return self.r._lesen("lokal_tests.json")

    def _speichern(self, d: dict) -> None:
        self.r._schreiben("lokal_tests.json", d)

    def starten(self, bo, *, alt: str, neu: str, faelle: list[dict], jetzt: str) -> dict:
        if not re.fullmatch(r"[a-z0-9._-]+(:[a-z0-9._-]+)?", neu or ""):
            raise ValueError("Ungueltiger Modellname.")
        with _LOCK:
            d = self.alle()
            if any(t["neu"] == neu and t["status"] in ("laeuft", "urteil") for t in d.values()):
                raise ValueError("Fuer dieses Modell laeuft schon ein Probelauf.")
            tid = "LT-" + hashlib.sha1(f"{neu}{jetzt}".encode()).hexdigest()[:6].upper()
            jobs = {}
            for i, f in enumerate(faelle):
                # ausdruecklich das heutige Modell -- der Worker hat ein eigenes Standardmodell (2026-10-16: qwen3:14b statt 30b-a3b)
                jobs[f"alt{i}"] = bo.anlegen(f["eingabe"], art="roh", von="Modell-Radar", stumm=True, zweck=f"lokaltest:{tid}:alt{i}",
                                             system="Du bist ein hilfreicher Assistent von Hanserautisch. Antworte auf Deutsch.",
                                             lokal_modell=alt)
                jobs[f"neu{i}"] = bo.anlegen(f["eingabe"], art="roh", von="Modell-Radar", stumm=True, zweck=f"lokaltest:{tid}:neu{i}",
                                             system="Du bist ein hilfreicher Assistent von Hanserautisch. Antworte auf Deutsch.",
                                             lokal_modell=neu)
            d[tid] = {"id": tid, "alt": alt, "neu": neu, "faelle": faelle, "jobs": jobs, "status": "laeuft", "start": jetzt}
            self._speichern(d)
        return d[tid]

    def tick(self, bo) -> list[str]:
        from .skill_werkstatt import SYSTEM_URTEIL, _reihenfolge, urteil_lesen
        meldungen = []
        with _LOCK:
            d = self.alle()
            for tid, t in d.items():
                jobs = {k: bo.get(v) for k, v in t["jobs"].items()}
                if t["status"] == "laeuft":
                    if any((j or {}).get("status") == "fehlgeschlagen" for j in jobs.values()):
                        t |= {"status": "fehler", "grund": next((j.get("grund", "") for j in jobs.values() if (j or {}).get("status") == "fehlgeschlagen"), "")[:200]}
                        meldungen.append(f"🧪 Probelauf {t['neu']} fehlgeschlagen: {t['grund']}")
                    elif all((j or {}).get("status") == "fertig" for j in jobs.values()):
                        for i, f in enumerate(t["faelle"]):
                            neu_a, alt_a = jobs[f"neu{i}"]["ergebnis"], jobs[f"alt{i}"]["ergebnis"]
                            a, b = (neu_a, alt_a) if _reihenfolge(tid, i) else (alt_a, neu_a)
                            t["jobs"][f"urteil{i}"] = bo.anlegen(
                                f"Aufgabe: {f['eingabe']}\nKriterien:\n" + "\n".join(f"- {k}" for k in f["kriterien"])
                                + f"\n\nAntwort A:\n{a[:3500]}\n\nAntwort B:\n{b[:3500]}", art="roh", von="Modell-Radar", stumm=True,
                                system=SYSTEM_URTEIL, zweck=f"lokaltest:{tid}:urteil{i}")
                        dauer = lambda p: round(sum(float(jobs[k].get("dauer_s") or 0) for k in jobs if k.startswith(p)) / max(1, len(t["faelle"])), 1)
                        t |= {"status": "urteil", "dauer_alt": dauer("alt"), "dauer_neu": dauer("neu")}
                elif t["status"] == "urteil":
                    urteile = {k: v for k, v in jobs.items() if k.startswith("urteil")}
                    if any((j or {}).get("status") == "fehlgeschlagen" for j in urteile.values()):
                        t |= {"status": "fehler", "grund": "Bewertung fehlgeschlagen"}
                    elif urteile and all((j or {}).get("status") == "fertig" for j in urteile.values()):
                        neu_p = alt_p = 0
                        for i in range(len(t["faelle"])):
                            u = urteil_lesen(urteile[f"urteil{i}"]["ergebnis"])
                            vorne = _reihenfolge(tid, i)
                            neu_p += u["A"] if vorne else u["B"]
                            alt_p += u["B"] if vorne else u["A"]
                        mx = sum(len(f["kriterien"]) for f in t["faelle"])
                        besser = neu_p > alt_p
                        t |= {"status": "fertig", "punkte_neu": neu_p, "punkte_alt": alt_p, "max": mx, "besser": besser}
                        meldungen.append(f"🧪 Probelauf lokales Modell: {t['neu']} {neu_p}/{mx} gegen {t['alt']} {alt_p}/{mx} Kriterien, "
                                         f"Zeit je Aufgabe {t['dauer_neu']} s gegen {t['dauer_alt']} s. "
                                         + ("Das neue Modell war besser – Umstellen entscheidest du (LOCAL_LLM_MODEL in der .env)."
                                            if besser else "Das heutige Modell bleibt besser oder gleich gut."))
            self._speichern(d)
        return meldungen


def pruffaelle_fuer_modelltest(repo_eigen: Path) -> list[dict]:
    """Standard-Pruffaelle + bis zu 5 aus aktiven Werkstatt-Skills (`skills_eigen/*/*/pruffaelle.json`)."""
    out = list(STANDARD_PRUEFFAELLE)
    for p in sorted(Path(repo_eigen).glob("*/*/pruffaelle.json"))[:5]:
        try:
            out += [f for f in json.loads(p.read_text(encoding="utf-8"))[:1] if f.get("eingabe") and f.get("kriterien")]
        except (OSError, ValueError):
            continue
    return out[:10]
