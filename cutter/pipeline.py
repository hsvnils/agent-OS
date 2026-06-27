"""Cutter-Pipeline: Ordner mit Clips -> automatisches 9:16-Instagram-Reel.

Vollautomatisch, lokal, kostenlos. Pro Clip wird erkannt, ob Sprache enthalten ist:
- **Sprech-Clip:** Stille am Rand wird getrimmt, der Inhalt bekommt eingebrannte Untertitel.
- **B-Roll-Clip:** ein praegnanter Ausschnitt wird gewaehlt, Ton leise (Musik kommt in Instagram dazu).
Optional ordnet Gemini (gratis) die Clips zu einer stimmigen Reihenfolge. Ausgabe: ein MP4 + Bericht.

Liefert KEINE Veroeffentlichung -- nur die fertige Datei (Instagram-Posten bleibt CEO-Tor).
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import ffmpeg_ops as fo
from . import transkription as tr

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Auswahl:
    clip: fo.ClipInfo
    typ: str            # "sprache" | "broll"
    start: float
    dauer: float
    transkript: list = field(default_factory=list)   # [{start,ende,text}] (lokal, nur Sprache)


def schneide_ordner(ordner, ausgabe=None, *, ziel_dauer: float = 45.0,
                    max_sprache: float = 14.0, broll_dauer: float = 3.2,
                    transkribieren: bool = True, gemini: bool = True,
                    untertitel: bool = False, sprache: str = "de") -> dict:
    """Schneidet alle Clips eines Ordners zu einem Reel. Gibt einen Bericht (dict) zurueck."""
    ordner = Path(ordner)
    if not fo.ffmpeg_vorhanden():
        return {"ok": False, "fehler": "ffmpeg/ffprobe nicht gefunden (brew install ffmpeg)."}
    clips = fo.clips_im_ordner(ordner)
    if not clips:
        return {"ok": False, "fehler": f"Keine Video-Clips in {ordner} gefunden."}

    env = _lade_env()
    weg = tr.verfuegbar() if transkribieren else ""

    auswahlen: list[Auswahl] = []
    for pfad in clips:
        info = fo.probe(pfad)
        if info is None or info.dauer <= 0:
            continue
        auswahlen.append(_clip_auswaehlen(info, weg, max_sprache, broll_dauer, sprache, env))

    if not auswahlen:
        return {"ok": False, "fehler": "Keine lesbaren Clips."}

    if gemini and env.get("GEMINI_API_KEY") and len(auswahlen) > 1:
        order = _gemini_reihenfolge(auswahlen, env["GEMINI_API_KEY"])
        if order:
            auswahlen = [auswahlen[i] for i in order if 0 <= i < len(auswahlen)] or auswahlen

    auswahlen = _auf_budget(auswahlen, ziel_dauer)

    # Segmente normalisieren + Untertitel-Zeiten global aufbauen.
    arbeit = Path(tempfile.mkdtemp(prefix="cutter_"))
    segmente, ass_events, cursor = [], [], 0.0
    for i, a in enumerate(auswahlen):
        seg = arbeit / f"seg_{i:03d}.mp4"
        if not fo.segment_normalisieren(a.clip.pfad, seg, start=a.start, dauer=a.dauer,
                                        hat_audio=a.clip.hat_audio, zoom=(a.typ == "broll")):
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
    if untertitel and ass:                         # Untertitel-Einbrennen nur im Hart-Schnitt-Pfad
        ok = fo.zusammenfuegen(segmente, ausgabe, untertitel_ass=ass, leiser_ton=nur_broll)
    else:                                          # Standard: weiche Uebergaenge + Effekte
        ok = fo.zusammenfuegen_xfade(segmente, ausgabe, leiser_ton=nur_broll)
        if not ok:                                 # Fallback: harte Schnitte, falls Uebergaenge scheitern
            ok = fo.zusammenfuegen(segmente, ausgabe, leiser_ton=nur_broll)
    if ok:                                         # Unter Telegram-Limit (50 MB) halten
        fo.auf_groesse_begrenzen(ausgabe, max_mb=48)

    if untertitel and ass_events:
        untertitel_status = "eingebrannt" if (ok and ass) else (f"als .srt ({srt.name})" if srt else False)
    else:
        untertitel_status = False
    return {
        "ok": ok,
        "ausgabe": str(ausgabe) if ok else None,
        "transkriptions_weg": weg or "keiner (keine Untertitel)",
        "clips_gesamt": len(clips),
        "verwendet": len(segmente),
        "dauer_sek": round(sum(a.dauer for a in auswahlen[:len(segmente)]), 1),
        "untertitel": untertitel_status,
        "srt": str(srt) if (srt and not ass) else None,
        "details": [{"datei": a.clip.pfad.name, "typ": a.typ,
                     "ausschnitt": f"{a.start:.1f}-{a.start + a.dauer:.1f}s"}
                    for a in auswahlen[:len(segmente)]],
        "hinweis": "Fertiges Reel als Datei. Instagram-Posten + Musik machst du in der App (CEO-Tor).",
    }


def _clip_auswaehlen(info, weg, max_sprache, broll_dauer, sprache, env) -> Auswahl:
    """Erkennt Sprache und waehlt den besten Ausschnitt des Clips."""
    transkript = []
    if weg and info.hat_audio and info.dauer >= 0.8:
        transkript = tr.transkribiere(info.pfad, sprache=sprache,
                                      deepgram_key=env.get("DEEPGRAM_API_KEY", ""))
    if transkript and sum(len(t["text"]) for t in transkript) >= 8:
        start = max(0.0, transkript[0]["start"] - 0.2)
        ende = min(info.dauer, transkript[-1]["ende"] + 0.2)
        dauer = min(max_sprache, max(1.0, ende - start))
        return Auswahl(info, "sprache", start, dauer, transkript)
    # B-Roll: praegnanter Ausschnitt ab ~20 % (wackelige Anfaenge ueberspringen).
    start = min(max(0.0, info.dauer * 0.2), max(0.0, info.dauer - 0.5))
    dauer = min(broll_dauer, max(0.8, info.dauer - start))
    return Auswahl(info, "broll", start, dauer, [])


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
