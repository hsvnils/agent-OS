"""Cutter-Pipeline: Ordner mit Clips -> automatisches 9:16-Instagram-Reel.

Vollautomatisch, lokal, kostenlos. Pro Clip wird erkannt, ob Sprache enthalten ist:
- **Sprech-Clip:** Stille am Rand wird getrimmt, der Inhalt bekommt eingebrannte Untertitel.
- **B-Roll-Clip:** ein praegnanter Ausschnitt wird gewaehlt, Ton leise (Musik kommt in Instagram dazu).
Optional ordnet Gemini (gratis) die Clips zu einer stimmigen Reihenfolge. Ausgabe: ein MP4 + Bericht.

Liefert KEINE Veroeffentlichung -- nur die fertige Datei (Instagram-Posten bleibt CEO-Tor).
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import ffmpeg_ops as fo
from . import qualitaet
from . import transkription as tr

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Auswahl:
    clip: fo.ClipInfo
    typ: str            # "sprache" | "broll"
    start: float
    dauer: float
    transkript: list = field(default_factory=list)   # [{start,ende,text}] (lokal, nur Sprache)
    pegel: float | None = None                       # v2: Pegel der lautesten Stelle (nur B-Roll)


def schneide_ordner(ordner, ausgabe=None, *, ziel_dauer: float = 45.0,
                    max_sprache: float = 14.0, broll_dauer: float = 3.2,
                    transkribieren: bool = True, gemini: bool = True,
                    untertitel: bool = False, sprache: str = "de", stil: str | None = None,
                    uebergang: str | None = None) -> dict:
    """Schneidet alle Clips eines Ordners zu einem Reel. Gibt einen Bericht (dict) zurueck.

    `stil` v1/v2 und `uebergang` weich/hart: Ohne Angabe gelten `CUTTER_STIL` (Standard v1) und `CUTTER_UEBERGANG`
    (Standard weich, CEO-Vorgabe 2026-06-27)."""
    ordner = Path(ordner)
    if not fo.ffmpeg_vorhanden():
        return {"ok": False, "fehler": "ffmpeg/ffprobe nicht gefunden (brew install ffmpeg)."}
    clips = fo.clips_im_ordner(ordner)
    if not clips:
        return {"ok": False, "fehler": f"Keine Video-Clips in {ordner} gefunden."}

    env = _lade_env()
    stil = _wahl(stil or env.get("CUTTER_STIL"), ("v1", "v2"), "v1")
    weich = _wahl(uebergang or env.get("CUTTER_UEBERGANG"), ("weich", "hart"), "weich") == "weich"
    weg = tr.verfuegbar() if transkribieren else ""

    auswahlen: list[Auswahl] = []
    for pfad in clips:
        info = fo.probe(pfad)
        if info is None or info.dauer <= 0:
            continue
        auswahlen.append(_clip_auswaehlen(info, weg, max_sprache, broll_dauer, sprache, env, stil))

    if not auswahlen:
        return {"ok": False, "fehler": "Keine lesbaren Clips."}

    reihenfolge_methode = "dateiname"
    if gemini and env.get("GEMINI_API_KEY") and len(auswahlen) > 1:
        order = None
        # OPT-IN Video-Verstaendnis (CUTTER_VIDEO_KI=1): Clips werden zu Gemini hochgeladen (CEO-Tor, Paid-Tier).
        if str(env.get("CUTTER_VIDEO_KI", "")).strip().lower() in ("1", "true", "yes", "on"):
            try:
                from .gemini_video import GeminiVideoClient, reihenfolge_via_video
                order = reihenfolge_via_video(
                    auswahlen, GeminiVideoClient(env["GEMINI_API_KEY"],
                                                 env.get("CUTTER_VIDEO_MODEL", "gemini-2.5-flash-lite")))
                if order:
                    reihenfolge_methode = "gemini-video"
            except Exception:
                order = None
        if order is None:                                  # Fallback: Text-Reihenfolge (nur Transkript)
            order = _gemini_reihenfolge(auswahlen, env["GEMINI_API_KEY"])
            if order:
                reihenfolge_methode = "gemini-text"
        if order:
            auswahlen = [auswahlen[i] for i in order if 0 <= i < len(auswahlen)] or auswahlen

    if stil == "v2" and reihenfolge_methode == "dateiname":
        auswahlen, verschoben = _staerkster_nach_vorn(auswahlen)
        if verschoben:
            reihenfolge_methode = "staerkster-clip-vorn"

    auswahlen = _auf_budget(auswahlen, ziel_dauer)

    # Segmente normalisieren + Untertitel-Zeiten global aufbauen.
    arbeit = Path(tempfile.mkdtemp(prefix="cutter_"))
    segmente, ass_events, cursor = [], [], 0.0
    for i, a in enumerate(auswahlen):
        seg = arbeit / f"seg_{i:03d}.mp4"
        if not fo.segment_normalisieren(a.clip.pfad, seg, start=a.start, dauer=a.dauer,
                                        hat_audio=a.clip.hat_audio, zoom=(a.typ == "broll"),
                                        stil=stil, ton_blende=(stil == "v2" and not weich)):
            continue
        if a.typ == "sprache":
            for t in a.transkript:
                gs = cursor + max(0.0, t["start"] - a.start)
                ge = cursor + min(a.dauer, t["ende"] - a.start)
                if ge > gs and t.get("text"):
                    ass_events.append((gs, ge, t["text"]))
        segmente.append(seg)
        cursor += a.dauer
    if not segmente:
        return {"ok": False, "fehler": "Segment-Erzeugung fehlgeschlagen."}

    if ausgabe is None:
        ausgabe = ordner / f"{ordner.name}_reel.mp4"
    ausgabe = Path(ausgabe)

    # Untertitel nur auf Wunsch (Default aus). Einbrennen braucht ffmpeg mit libass -- sonst .srt daneben.
    ass = srt = None
    if untertitel and ass_events:
        srt = ausgabe.with_suffix(".srt")
        _schreibe_srt(ass_events, srt)
        if fo.hat_filter("subtitles"):
            ass = arbeit / "untertitel.ass"
            _schreibe_ass(ass_events, ass)

    nur_broll = all(a.typ == "broll" for a in auswahlen)
    schnitt_weg, uebergang_fehler = "weich", None
    ton_ziel = fo.ZIEL_LUFS_BROLL if nur_broll else fo.ZIEL_LUFS_V2
    if stil == "v2":
        schnitt_weg = "weich" if (weich and not ass and len(segmente) > 1) else "hart"
        ok = fo.zusammenfuegen_v2(segmente, ausgabe, weich=(schnitt_weg == "weich"), ziel_lufs=ton_ziel, untertitel_ass=ass)
        if not ok and schnitt_weg == "weich":
            schnitt_weg, uebergang_fehler = "hart_notweg", fo.letzter_fehler
            ok = fo.zusammenfuegen_v2(segmente, ausgabe, weich=False, ziel_lufs=ton_ziel)
    elif untertitel and ass:                       # Untertitel-Einbrennen nur im Hart-Schnitt-Pfad
        schnitt_weg = "hart"
        ok = fo.zusammenfuegen(segmente, ausgabe, untertitel_ass=ass, leiser_ton=nur_broll)
    else:                                          # Standard: weiche Uebergaenge + Effekte
        ok = fo.zusammenfuegen_xfade(segmente, ausgabe, leiser_ton=nur_broll)
        if not ok:                                 # Fallback: harte Schnitte, falls Uebergaenge scheitern
            schnitt_weg, uebergang_fehler = "hart_notweg", fo.letzter_fehler
            ok = fo.zusammenfuegen(segmente, ausgabe, leiser_ton=nur_broll)
    if ok:                                         # Unter Telegram-Limit (50 MB) halten
        fo.auf_groesse_begrenzen(ausgabe, max_mb=48)

    if ok:                                         # CUTTER_AUSBAU C1: fertiges Video messen (meldet nur, sperrt nicht)
        try:
            kontroll_ziel = ton_ziel if stil == "v2" else (None if nur_broll else qualitaet.ZIEL_LUFS)
            qualitaets_bericht = qualitaet.pruefe_video(ausgabe, ziel_lufs=kontroll_ziel)
        except Exception as exc:
            qualitaets_bericht = {"gemessen": False, "ok": None, "fehler": str(exc)[:300], "befunde": []}
    else:
        qualitaets_bericht = None

    if untertitel and ass_events:
        untertitel_status = "eingebrannt" if (ok and ass) else (f"als .srt ({srt.name})" if srt else False)
    else:
        untertitel_status = False
    return {
        "ok": ok,
        "ausgabe": str(ausgabe) if ok else None,
        "transkriptions_weg": weg or "keiner (keine Untertitel)",
        "reihenfolge": reihenfolge_methode,
        "clips_gesamt": len(clips),
        "verwendet": len(segmente),
        "dauer_sek": round(sum(a.dauer for a in auswahlen[:len(segmente)]), 1),
        "untertitel": untertitel_status,
        "srt": str(srt) if (srt and not ass) else None,
        "details": [{"datei": a.clip.pfad.name, "typ": a.typ,
                     "ausschnitt": f"{a.start:.1f}-{a.start + a.dauer:.1f}s"}
                    for a in auswahlen[:len(segmente)]],
        "qualitaet": qualitaets_bericht,
        "stil": stil,
        "schnitt_weg": schnitt_weg,
        "uebergang_fehler": uebergang_fehler,
        "hinweis": "Fertiges Reel als Datei. Instagram-Posten + Musik machst du in der App (CEO-Tor).",
    }


def _wahl(wert, erlaubt: tuple, standard: str) -> str:
    wert = str(wert or "").strip().lower()
    return wert if wert in erlaubt else standard


def _dauer_bis_grenze(info, transkript: list, start: float, max_sprache: float) -> float:
    """v2: Laenge eines Sprech-Clips, die nicht mitten im Satz endet (Satzende, sonst laengste Sprechpause)."""
    ende = min(info.dauer, transkript[-1]["ende"] + 0.2)
    if ende - start <= max_sprache:
        return max(1.0, ende - start)
    grenze = start + max_sprache
    passend = [t["ende"] + 0.2 for t in transkript if t["ende"] + 0.2 <= grenze and t["ende"] - start >= 1.0]
    if passend:
        return max(passend) - start
    pausen = [(a + b) / 2 for a, b in fo.stille_spannen(info.pfad, mindest_stille=0.25) if start + 1.0 <= (a + b) / 2 <= grenze]
    return (max(pausen) - start) if pausen else max_sprache


def _staerkster_nach_vorn(auswahlen: list) -> tuple[list, bool]:
    """v2: Bei reiner B-Roll kommt der Clip mit der lautesten Stelle als Hook an den Anfang, Rest bleibt in Reihenfolge."""
    if not auswahlen or not all(a.typ == "broll" for a in auswahlen):
        return auswahlen, False
    mit_pegel = [a for a in auswahlen if a.pegel is not None]
    if not mit_pegel:
        return auswahlen, False
    bester = max(mit_pegel, key=lambda a: a.pegel)
    if bester is auswahlen[0]:
        return auswahlen, False
    return [bester] + [a for a in auswahlen if a is not bester], True


def _clip_auswaehlen(info, weg, max_sprache, broll_dauer, sprache, env, stil: str = "v1") -> Auswahl:
    """Erkennt Sprache und waehlt den besten Ausschnitt des Clips."""
    transkript = []
    if weg and info.hat_audio and info.dauer >= 0.8:
        transkript = tr.transkribiere(info.pfad, sprache=sprache,
                                      deepgram_key=env.get("DEEPGRAM_API_KEY", ""))
    if transkript and sum(len(t["text"]) for t in transkript) >= 8:
        start = max(0.0, transkript[0]["start"] - 0.2)
        ende = min(info.dauer, transkript[-1]["ende"] + 0.2)
        dauer = min(max_sprache, max(1.0, ende - start))
        if stil == "v2":
            dauer = _dauer_bis_grenze(info, transkript, start, max_sprache)
        return Auswahl(info, "sprache", start, dauer, transkript)
    # B-Roll: szenenbewusst den praegnantesten Ausschnitt waehlen (Fallback: ab ~20 %).
    moment = fo.lautester_moment(info.pfad) if (stil == "v2" and info.hat_audio) else None
    if moment:                                     # v2: lauteste Stelle (Tor, Jubel) liegt bei 40 % des Ausschnitts
        reserve = max(0.0, info.dauer - broll_dauer)   # nicht in die ersten Wackler nach dem Aufnahmestart
        start = max(min(0.5, reserve), min(moment[0] - 0.4 * broll_dauer, reserve))
    else:
        start = _broll_start(info, broll_dauer, env)
    dauer = min(broll_dauer, max(0.8, info.dauer - start))
    return Auswahl(info, "broll", start, dauer, [], pegel=moment[1] if moment else None)


def _broll_start(info, broll_dauer: float, env: dict) -> float:
    """Waehlt den B-Roll-Start szenenbewusst: laengste zusammenhaengende Szene, kurz nach dem Schnitt.

    Fallback (zu kurz / abgeschaltet / keine Szenen erkannt): der bisherige ~20-%-Start. Rein lokal/gratis
    ueber ffmpeg. Abschaltbar per `CUTTER_SZENEN=0` bzw. CLI `--ohne-szenen`.
    """
    default = min(max(0.0, info.dauer * 0.2), max(0.0, info.dauer - 0.5))
    if str(env.get("CUTTER_SZENEN", "1")).strip().lower() in ("0", "false", "no", "off"):
        return default
    if info.dauer < max(2.0, broll_dauer + 0.5):          # zu kurz -> nichts zu suchen
        return default
    cuts = fo.szenen_zeiten(info.pfad)
    if not cuts:
        return default
    grenzen = [0.0] + [c for c in cuts if 0.0 < c < info.dauer] + [info.dauer]
    bestes, best_len = None, 0.0
    for a, b in zip(grenzen, grenzen[1:]):
        if (b - a) > best_len:
            best_len, bestes = (b - a), (a, b)
    if bestes is None:
        return default
    a, b = bestes
    start = min(a + 0.3, max(a, b - broll_dauer))         # Uebergang ueberspringen, Platz fuer broll_dauer lassen
    return max(0.0, min(start, max(0.0, info.dauer - 0.5)))


def _auf_budget(auswahlen: list, ziel_dauer: float) -> list:
    """Begrenzt die Gesamtlaenge: verwirft am Ende, bis das Reel unter der Ziel-Dauer liegt."""
    out, summe = [], 0.0
    for a in auswahlen:
        if summe + a.dauer > ziel_dauer and out:
            break
        out.append(a)
        summe += a.dauer
    return out


def _lade_env() -> dict:
    env = {}
    p = ROOT / "orchestrator" / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    # Cutter-Schalter duerfen per Prozess-Umgebung (CLI / launchd) gesetzt werden.
    for k in ("CUTTER_VIDEO_KI", "CUTTER_VIDEO_MODEL", "CUTTER_SZENEN", "CUTTER_STIL", "CUTTER_UEBERGANG"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _gemini_reihenfolge(auswahlen: list, key: str) -> list | None:
    """Fragt Gemini (gratis) nach einer stimmigen Reihenfolge -> Liste von Indizes. None bei Fehler."""
    try:
        import json as _json

        import openai
        from orchestrator.core.model_router import GEMINI_BASE_URL
        liste = []
        for i, a in enumerate(auswahlen):
            txt = " ".join(t["text"] for t in a.transkript)[:160] if a.transkript else "(ohne Sprache)"
            liste.append(f"{i}: [{a.typ}] {a.clip.pfad.name} -- {txt}")
        prompt = (
            "Du bist Profi-Video-Cutter fuer Instagram-Reels. Ordne die folgenden Clips zu einer "
            "spannenden Reihenfolge (Hook zuerst, dann Aufbau). Antworte NUR mit einer JSON-Liste von "
            "Indizes, z. B. [2,0,1,3].\n\n" + "\n".join(liste))
        client = openai.OpenAI(api_key=key, base_url=GEMINI_BASE_URL)
        r = client.chat.completions.create(model="gemini-2.5-flash",
                                           messages=[{"role": "user", "content": prompt}])
        txt = (r.choices[0].message.content or "").strip()
        i, j = txt.find("["), txt.rfind("]")
        order = _json.loads(txt[i:j + 1]) if i >= 0 and j > i else None
        if isinstance(order, list) and all(isinstance(x, int) for x in order):
            return order
    except Exception:
        return None
    return None


def _ass_zeit(s: float) -> str:
    s = max(0.0, s)
    h = int(s // 3600); m = int((s % 3600) // 60); sek = s % 60
    return f"{h:d}:{m:02d}:{sek:05.2f}"


def _srt_zeit(s: float) -> str:
    s = max(0.0, s)
    h = int(s // 3600); m = int((s % 3600) // 60); sek = int(s % 60); ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sek:02d},{ms:03d}"


def _schreibe_srt(events: list, pfad: Path) -> None:
    """Schreibt eine .srt-Untertiteldatei (Sidecar, falls Einbrennen nicht moeglich)."""
    bloecke = []
    for i, (gs, ge, text) in enumerate(events, 1):
        text = (text or "").replace("\n", " ").strip()
        bloecke.append(f"{i}\n{_srt_zeit(gs)} --> {_srt_zeit(ge)}\n{text}\n")
    pfad.write_text("\n".join(bloecke), encoding="utf-8")


def _schreibe_ass(events: list, pfad: Path) -> None:
    """Schreibt eine .ass-Untertiteldatei (gross, zentriert, gut lesbar -- Reel-Stil)."""
    kopf = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV\n"
        "Style: Reel,Arial,64,&H00FFFFFF,&H00000000,&H64000000,1,1,4,2,2,60,60,300\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    zeilen = []
    for gs, ge, text in events:
        text = text.replace("\n", " ").replace("{", "(").replace("}", ")").strip()
        zeilen.append(f"Dialogue: 0,{_ass_zeit(gs)},{_ass_zeit(ge)},Reel,,0,0,0,,{text}")
    pfad.write_text(kopf + "\n".join(zeilen) + "\n", encoding="utf-8")
