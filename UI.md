# UI.md — Design-System der LUNA-Oberflaeche (LUNA-OS Command Center)

> **Single Source of Truth fuer das Aussehen von LUNA-OS.** Jede neue Funktion/jedes neue Panel folgt diesen
> Regeln, damit die Oberflaeche EIN konsistentes, futuristisches „Command Center" bleibt (Jarvis-/HUD-Stil).
> Technische Datei (englische Bezeichner/Tokens erlaubt); nutzersichtbare Texte sind **Deutsch mit echten
> Umlauten** (ae/oe/ue/ss vermeiden -- siehe AGENTS.md Abschnitt 6 gilt fuer .md-Fliesstext, aber UI-STRINGS
> im Code nutzen echte Umlaute).

Ort der Oberflaeche: `orchestrator/channels/web/static/` (`index.html`, `style.css`, `app.js`).

---

## 1. Designsprache (Kurz)

Dunkles, holografisches **Command Center**: tiefes Weltraum-Navy, Neon-**Cyan** als Leitfarbe, **Violett**
als Akzent, Status in Gruen/Amber/Rot. Glasmorphismus-Panels mit duennem Neon-Rand und HUD-Eckwinkeln,
Mono-Schrift fuer Zahlen/Labels, sanfte Animationen (Orb pulsiert mit der Stimme, langsamer Scan-Sweep,
rotierender Reaktor-Ring). Wirkung: ruhig, technisch, „lebendig" -- nie verspielt oder bunt.

---

## 2. Farb-Tokens (CSS-Variablen in `:root`)

Immer diese Variablen nutzen, **keine** Hex-Werte direkt im Komponenten-CSS.

```
--bg0 #03060f   --bg1 #060b1c   --bg2 #0a1430        /* Hintergrund-Tiefen          */
--glass rgba(14,24,52,.55)      --glass-hi rgba(22,38,78,.65)   /* Panel-Fuellungen   */
--fg #e6f1ff    --muted #8aa0c8 --line rgba(120,170,255,.18)    /* Text + Trennlinien */
--cyan #2ee6ff  --violet #a874ff --magenta #ff5cc8              /* Leit-/Akzentfarben */
--green #45f0a6 --amber #ffc14d  --red #ff5c7a                  /* Status             */
--accent = --cyan
--glow-cyan / --glow-violet     /* Standard-Leuchtschatten      */
--radius 14px
--font  (System-Sans)           --mono (System-Mono)
```

**Status-Semantik:** Gruen = aktiv/verbunden/ok · Cyan = live/Information/primär · Amber = Standby/Warnung ·
Rot = Fehler/ueberfaellig/dringend · Violett = sekundaerer Akzent/„erledigt".

---

## 3. Typografie

- **Fliesstext/Titel:** `--font` (System-Sans).
- **Zahlen, Labels, Statuszeilen, Uhr, IDs:** `--mono` (wirkt „technisch").
- **Sektion-/Panel-Header:** UPPERCASE, `letter-spacing: 1.2–3px`, klein (11–13px), Farbe `--muted` oder
  `--cyan`, dezenter `text-shadow` in Cyan.
- **Marke „LUNA":** fett, weit gesperrt (`letter-spacing: 3px`), Cyan-Glow.
- Keine externen Web-Fonts/CDNs (Selbst-Genuegsamkeit + Datenschutz).

---

## 4. Layout (Command Center)

Fester Rahmen, scrollender Inhalt:

```
┌───────────────────────────────────────────────────────────────┐
│ TOPBAR  (Orb · Marke · System-Status · Suche · Uhr · Aktionen) │
├───────────┬───────────────────────────────────────────────────┤
│ SIDEBAR   │  MAIN  =  Panel-Grid (responsive)                  │
│ (Nav +    │   - Hero/Core (animierter Globe/Reaktor)           │
│  Voice-   │   - Panels: Overview, Live-Feed, Agents, Timeline, │
│  Status)  │     System/Stats, Memory/Brain, LLM-Status, …      │
├───────────┴───────────────────────────────────────────────────┤
│ VOICE-BAR  „TALK TO LUNA — ich höre …"  (Orb-/Gespraech-Toggle)│
└───────────────────────────────────────────────────────────────┘
```

- **Topbar:** fixe Hoehe, Glas + Blur, untere Neon-Kante.
- **Sidebar:** Navigation; aktiver Eintrag mit Cyan-Balken links + Glas-Highlight; unten Voice-Status
  (Mini-Waveform). Klick auf einen Eintrag oeffnet die jeweilige App (WinBox-Fenster) bzw. das Home-Grid.
- **Main:** CSS-Grid aus Panels (`auto-fit`, min ~280–360px). Reihenfolge nach Wichtigkeit.
- **Voice-Bar:** prominente „TALK TO LUNA"-Leiste; tippen = `toggleVoice` (Live-Gespraech).
- **Hintergrund:** `#starfield` + `#grid` + `#scan` (siehe vorhandenes CSS) -- nie entfernen.
- **App-Fenster:** Detailarbeit laeuft weiter in **WinBox**-Fenstern (Stil `.winbox.modern`), die ueber dem
  Dashboard schweben. Das Dashboard ist die Startseite/Uebersicht, die Fenster sind die Tiefe.

**Responsive:** <=900px -> Sidebar wird zur oberen/aufklappbaren Leiste oder Icons-only; Panel-Grid einspaltig;
WinBox-Fenster vollflaechig (`winGeom()` Mobil-Pfad). <=640px -> Touch-Groessen, Voice-Bar bleibt erreichbar.

---

## 5. Komponenten (Bausteine)

Alle Panels folgen demselben Grundgeruest:

- **Panel:** `.glass`-Card, `border:1px var(--line)`, `border-radius:var(--radius)`, Blur, dezenter
  Innen-Glanz (`inset 0 1px 0 rgba(255,255,255,.06)`), beim Hover Cyan-Rand + `--glow-cyan`.
  Optional **HUD-Eckwinkel** (kleine Cyan-Eckmarkierungen) und ein **Header** (UPPERCASE-Label links,
  optional „● LIVE"-Pille oder „Mehr ›"-Link rechts).
- **Status-Pille:** kleiner runder Farbpunkt + Label (z. B. „● Active", „● Connected", „● Standby") in der
  jeweiligen Status-Farbe, Mono, klein.
- **Feed-/List-Item:** Icon links, Titel (fett) + Unterzeile (muted), rechts Zeit/Badge; Hover dezent
  Cyan-getoent.
- **Stat/Gauge:** runder SVG-Ring (Cyan-Verlauf) mit grosser Mono-Zahl in der Mitte + Label darunter; nutze
  reale LUNA-Zahlen (Antraege, Tickets, Wissens-Items, Meldungen) statt fiktiver Hardware-Werte.
- **Agent-Card:** Name + Status-Pille + dezente Wellenform/Aktivitaet.
- **Quick-Command-Button:** Glas-Button mit Icon + Label, Cyan-Hover-Glow.
- **Orb / Core:** zentrales animiertes Mond-/Reaktor-Symbol (`#luna-orb`, Zustaende idle/listening/speaking,
  audio-reaktiv ueber `--energy`) -- die visuelle Identitaet von LUNA; im Hero gross, in der Topbar klein.
- **Buttons:** `.btn` mit Varianten `ok/warn/info/danger/ghost` (siehe `style.css`); gefuellt = Aktion,
  `ghost` = sekundaer.
- **Badges:** Status-/Kategorie-Badges (`.badge.<status>`), Pillenform, UPPERCASE, Mono.

---

## 6. Bewegung & Effekte

- Subtil und zweckmaessig: Orb-Atmen/Pulsieren, Scan-Sweep, rotierender Reaktor-Ring, „● LIVE"-Blinken.
- Keine harten/schnellen Bewegungen, kein Geblinke ausser Status.
- **`@media (prefers-reduced-motion: reduce)`** schaltet Animationen ab (Pflicht).

---

## 7. Sprache & Inhalt

- Alle nutzersichtbaren Texte **Deutsch mit echten Umlauten** (ä, ö, ü, ß). Code-Bezeichner/IDs/Keys ASCII.
- Labels kurz und praezise; LUNA „spricht" wie ein Teammate, nicht wie ein Debug-Log.
- Echte Daten bevorzugen; wo (noch) keine Daten existieren, klaren leeren Zustand zeigen
  („Keine offenen Aufträge. 🎉"), nicht mit Mock-Zahlen fuellen.

---

## 8. Technische Regeln

- **Theming nur ueber CSS-Variablen** (Abschnitt 2). Neue Farbe noetig? -> zuerst Token definieren.
- **Selbst-genuegsam:** keine externen Fonts/Icon-CDNs/JS-CDNs; vendored Libs unter `static/vendor/`
  (aktuell nur WinBox).
- **Cache-Bust:** bei jeder Frontend-Aenderung `?v=N` in `index.html` erhoehen.
- **Daten ueber die bestehenden Endpunkte** (`/api/state`, `/api/overview`, `/api/lagebild`, `/api/brain`,
  `/api/chat`, `/api/tts`, SSE `/api/events`); Aktionen laufen ueber die echten Store-Methoden (Changelog +
  CEO-Tor bleiben hart -- die UI ist nur der bequeme Weg).
- **Leck-Schutz/Sicherheit:** keine Secrets ins Frontend; Login (HTTP-Basic) bleibt aktiv.
- **Barrierefreiheit:** ausreichender Kontrast, `prefers-reduced-motion`, Touch-Ziele >=40px.

---

## 9. Eine neue Funktion hinzufuegen — Checkliste

1. Braucht sie eine eigene Ansicht? -> als **App** (WinBox-Fenster) UND/ODER als **Panel** im Command Center.
2. Nur vorhandene **Tokens/Komponenten** verwenden (Panel, Header, Status-Pille, Button, Badge, Gauge).
3. Daten ueber einen `/api/...`-Endpunkt; leeren Zustand sauber gestalten.
4. Deutsch mit Umlauten; `?v=N` erhoehen; `prefers-reduced-motion` beachten.
5. Im Preview verifizieren (Desktop + mobil), dann committen + (bei Bedarf) deployen.

---

## 10. Referenz

Inspiriert vom „JARVIS Command Center"-HUD (CEO-Vorlage 2026-06-28): Sidebar-Navigation, zentraler
AI-Core/Globe, Panel-Grid (AI Core Overview, Live Intelligence Feed, Active Agents, Mission Timeline,
System Monitor, Memory Insights, LLM Status, Quick Commands), durchgehende „Talk to …"-Leiste.
LUNA-Umsetzung nutzt **reale** Daten (Antraege, Meldungen, Research, Second Brain, Lagebild, Provider-Status).
