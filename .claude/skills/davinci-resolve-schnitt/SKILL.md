---
name: davinci-resolve-schnitt
description: Schnittwissen fuer Claude Code - welcher Effekt, welcher Uebergang, wie Keyframes, Ton, Export fuer Reels, Shorts und YouTube sowie alle Funktionen von DaVinci Resolve 21. Laden bei Arbeit am Cutter (cutter/, CUTTER_AUSBAU_ROADMAP.md), bei Schnittplaenen, Video-Effekten, ffmpeg-Filtern fuer Video und bei jeder Frage zu DaVinci Resolve.
---

# Schnittwissen (Claude Code)

Eine Quelle: Dieser Skill ist nur der Einstieg, der Inhalt steht einmal im Repo.

1. Zuerst `skills/cco/davinci-resolve-schnitt/SKILL.md` lesen (Rangfolge, Keyframes, Uebergaenge, Effekte, Ton, Genres, Pruefliste).
2. Details gezielt aus `skills/cco/davinci-resolve-schnitt/referenz/` nachlesen, nur die passende Datei und per grep. Der Ordner ist nicht im Git, er liegt auf dem MACO470 und der NAS.

| Datei | Inhalt |
|---|---|
| `01_setup_media_photo_cut.md` | Projekt, Media Pool, Proxies, Cut Page, 9:16, Quick Export |
| `02_edit_effekte_keyframes.md` | Edit Page, Keyframes, Transform, Speed, alle Uebergaenge und Titel, Rezepte |
| `03_fusion.md` | Fusion, alle Nodes und Modifier, Rezepte fuer Grafik |
| `04_color_resolvefx.md` | Color Page, Scopes, Nodes, alle Resolve FX, Rezepte |
| `05_fairlight_deliver_rest.md` | Ton-Rezepte, alle Fairlight FX, Deliver, Menues |
| `06_scripting_automatisierung.md` | Skript-API, Faehigkeits-Matrix, Free gegen Studio |
| `07_best_practices_social.md` | Short-Form: Hook, Rhythmus, Untertitel, Safe Zones, Export |
| `08_best_practices_youtube.md` | Longform: Retention, Schnitt-Handwerk, Export |
| `09_techniken_wann_was.md` | Entscheidungstabellen: Situation, Technik, Werte, wann nicht |

Dazu passend: `skills/cco/reel-dramaturgie/SKILL.md`, `skills/cco/hook-und-skript/SKILL.md`, `skills/vid/b-roll-und-schnittdenken/SKILL.md`.

## Beim Bauen am Cutter
- Auf dem MACO470 laeuft Resolve Free (keine externe Steuerung, kein MCP). Techniken daher in ffmpeg umsetzen.
- Werte aus dem Skill sind Startwerte: nach dem Rendern mit `cutter/qualitaet.py` messen und am echten Video pruefen.
- CEO-Vorgaben zum Cutter gehen vor Skill-Regeln (`docs/entscheidungs-register.md`, Changelog). Abweichungen vorher vorlegen.
